import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import subprocess
import sys
import os
import re
from pathlib import Path
import datetime

class LogcatManager:
    def __init__(self, root, adb_manager, styles, logger, apk_analyzer=None, config_manager=None):
        self.root = root
        self.adb_manager = adb_manager
        self.styles = styles
        self.logger = logger
        self.apk_analyzer = apk_analyzer
        self.config_manager = config_manager
        self.is_monitoring = False
        self.logcat_process = None
        self.current_filter = ""
        self.package_history = []
        self.current_apk_package = ""
        self.components = None
        self.adb_path = self._get_adb_path()
        self.all_packages = []
        self.current_pid = None
        self.current_screen = 0
        self.monitoring_stats = False
        self.stats_process = None
        self.estadisticas_preguntadas = False

    def _get_adb_path(self):
        """Obtener la ruta de ADB desde la configuración"""
        try:
            if self.config_manager:
                config = self.config_manager.cargar_config()
                if config and 'adb_path' in config and config['adb_path']:
                    adb_path = Path(config['adb_path'])
                    if adb_path.exists():
                        return str(adb_path)
            
            if hasattr(self.adb_manager, 'get_adb_path'):
                adb_path = self.adb_manager.get_adb_path()
                if adb_path and Path(adb_path).exists():
                    return adb_path
            
            common_paths = [
                "platform-tools/adb.exe",
                "adb.exe",
                "C:\\Android\\platform-tools\\adb.exe",
                "C:\\Program Files\\Android\\platform-tools\\adb.exe",
                str(Path.home() / "AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe")
            ]
            
            for path in common_paths:
                if Path(path).exists():
                    return path
            
            return "adb"
            
        except Exception as e:
            self.logger.log_warning(f"Error obteniendo ruta ADB: {e}")
            return "adb"
        
  
    def _ejecutar_adb(self, comando, timeout=15):
        """Ejecutar comando ADB de forma segura sin mostrar ventana CMD"""
        try:
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # Oculta la ventana
                
                # Para Python 3.7+ usar CREATE_NO_WINDOW
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    creationflags = subprocess.CREATE_NO_WINDOW
                else:
                    creationflags = 0
            else:
                creationflags = 0

            if isinstance(comando, str):
                if self.adb_path != "adb":
                    full_cmd = f'"{self.adb_path}" {comando}'
                else:
                    full_cmd = f"adb {comando}"
                
                result = subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
            else:
                if self.adb_path != "adb":
                    full_cmd = [self.adb_path] + comando
                else:
                    full_cmd = comando
                
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
            
            return result
            
        except subprocess.TimeoutExpired:
            self.logger.log_warning(f"Timeout ejecutando ADB: {comando}")
            return None
        except Exception as e:
            self.logger.log_error(f"Error ejecutando ADB: {comando}", e)
            return None
        

    def _recargar_packages(self):
        """Recargar manualmente la lista de packages"""
        self.status_label.config(
            text="🔄 Recargando lista de packages...",
            fg="#ff9800"
        )       

        def recargar():
            result = self._ejecutar_adb("shell pm list packages")
            
            if result and result.returncode == 0:
                packages = []
                for line in result.stdout.split('\n'):
                    if line.startswith('package:'):
                        package_name = line.replace('package:', '').strip()
                        if package_name:
                            packages.append(package_name)
                
                packages.sort()
                self.all_packages = packages
                
                self.root.after(0, self._actualizar_packages_ui_recarga, packages)
            else:
                error_msg = "No se pudieron recargar los packages"
                self.root.after(0, lambda: self.status_label.config(
                    text=f"❌ {error_msg}",
                    fg="#f44336"
                ))

        threading.Thread(target=recargar, daemon=True).start()

    def _actualizar_packages_ui_recarga(self, packages):
        """Actualizar UI después de recargar packages"""
        self.package_combo['values'] = packages
        self.status_label.config(
            text=f"✅ {len(packages)} packages recargados correctamente",
            fg="#4caf50"
        )
        
        # Mantener el package seleccionado si aún existe
        current_package = self.package_var.get()
        if current_package and current_package not in packages:
            self.package_var.set("")
            self.filter_info_label.config(text="🎯 Filtro: Ninguno")        

    def _obtener_pid_package(self, package_name):
        """Obtener el PID de un package usando pidof"""
        try:
            result = self._ejecutar_adb(f"shell pidof {package_name}")
            if result and result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip()
                if pid.isdigit():
                    self.current_pid = pid
                    return pid
            return None
        except Exception as e:
            self.logger.log_error(f"Error obteniendo PID para {package_name}", e)
            return None

    def mostrar_logcat(self):
        """Mostrar ventana de Logcat"""
        self.logcat_window = tk.Toplevel(self.root)
        self.logcat_window.title("Logcat - Monitor de Dispositivos Android")
        
        # Configuración de ventana mejorada
        self.logcat_window.geometry("1400x850")
        self.logcat_window.minsize(1200, 700)
        
        # Detectar pantalla actual
        self._detectar_pantalla_actual()
        
        self.logcat_window.configure(bg=self.styles.COLORS['primary_bg'])
        self._posicionar_ventana_inteligente()
        self.logcat_window.bind("<Control-s>", lambda e: self._guardar_log())
        self.logcat_window.bind("<Control-l>", lambda e: self._limpiar_logcat())
        self.logcat_window.bind("<Control-f>", lambda e: self.package_combo.focus())
        
        self._crear_ui_logcat_mejorada()
        self._verificar_y_cargar_automaticamente()

    def _detectar_pantalla_actual(self):
        """Detectar en qué pantalla está la ventana principal de forma más precisa"""
        try:
            # Obtener posición de la ventana principal
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            
            # Obtener dimensiones de la pantalla principal
            screen_width = self.root.winfo_screenwidth()
            
            # Si la ventana principal está centrada o en la segunda mitad de la pantalla principal,
            # asumimos que está en pantalla secundaria
            screen_threshold = screen_width * 0.7  # 70% del ancho de la pantalla principal
            
            if main_x > screen_threshold or (main_x > screen_width // 2 and main_width < screen_width // 2):
                self.current_screen = 1  # Pantalla secundaria
            else:
                self.current_screen = 0  # Pantalla principal
                
        except Exception as e:
            self.logger.log_warning(f"Error detectando pantalla: {e}")
            self.current_screen = 0

    def _posicionar_ventana_inteligente(self):
        """Posicionar ventana de forma inteligente según la pantalla actual"""
        try:
            # Obtener información de todas las pantallas
            total_width = self.logcat_window.winfo_screenwidth()
            total_height = self.logcat_window.winfo_screenheight()
            
            # Obtener posición y tamaño de la ventana principal
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()
            
            if self.current_screen == 1:  # Pantalla secundaria
                # Usar toda la pantalla secundaria (asumiendo que es del mismo tamaño)
                self.logcat_window.geometry(f"{total_width}x{total_height-50}+0+0")
                self.logcat_window.state('zoomed')  # Maximizar en la pantalla secundaria
            else:
                # Posicionar junto a la ventana principal en pantalla principal
                # Calcular posición óptima
                if main_x + main_width + 1000 <= total_width:
                    # Hay espacio a la derecha
                    logcat_x = main_x + main_width + 10
                    logcat_y = main_y
                    logcat_width = min(1000, total_width - logcat_x - 20)
                else:
                    # No hay espacio a la derecha, poner a la izquierda
                    logcat_x = max(10, main_x - 1000 - 10)
                    logcat_y = main_y
                    logcat_width = min(1000, main_x - 20)
                
                logcat_height = total_height - 100
                
                # Asegurar dimensiones mínimas
                if logcat_width < 500:
                    logcat_width = 500
                if logcat_height < 400:
                    logcat_height = 400
                    
                self.logcat_window.geometry(f"{logcat_width}x{logcat_height}+{logcat_x}+{logcat_y}")
            
        except Exception as e:
            self.logger.log_warning(f"No se pudo posicionar ventana inteligente: {e}")
            # Geometría por defecto centrada
            self.logcat_window.geometry("1400x850")
            self._centrar_ventana(self.logcat_window)

    def _centrar_ventana(self, ventana):
        """Centrar ventana en la pantalla"""
        ventana.update_idletasks()
        ancho = ventana.winfo_width()
        alto = ventana.winfo_height()
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _crear_ui_logcat_mejorada(self):
        """Crear interfaz de usuario MEJORADA para Logcat"""
        # Frame principal con mejor diseño
        main_frame = tk.Frame(self.logcat_window, bg=self.styles.COLORS['primary_bg'])
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # Header con título y estado
        header_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        header_frame.pack(fill="x", pady=(0, 15))

        # Título principal
        title_label = tk.Label(
            header_frame,
            text="🐱 LOGCAT",
            font=("Segoe UI", 16, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['accent'],
            pady=8
        )
        title_label.pack(side="left")

        # Información ADB compacta
        adb_info = f"📱 ADB: {Path(self.adb_path).name}" if self.adb_path != "adb" else "📱 ADB: PATH"
        self.adb_info_label = tk.Label(
            header_frame,
            text=adb_info,
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_secondary'],
            cursor="hand2"
        )
        self.adb_info_label.pack(side="right", padx=(0, 10))
        self.adb_info_label.bind("<Button-1>", self._mostrar_info_adb)

        # Panel de control principal
        control_frame = tk.Frame(main_frame, bg=self.styles.COLORS['secondary_bg'], relief="raised", bd=1)
        control_frame.pack(fill="x", pady=(0, 15))

        # Fila 1: Búsqueda y packages
        search_frame = tk.Frame(control_frame, bg=self.styles.COLORS['secondary_bg'])
        search_frame.pack(fill="x", padx=15, pady=12)

        # Selector de packages MEJORADO
        package_selector_frame = tk.Frame(search_frame, bg=self.styles.COLORS['secondary_bg'])
        package_selector_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            package_selector_frame,
            text="🔍 FILTRAR POR PACKAGE:",
            font=("Segoe UI", 10, "bold"),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))

        # ✅ CORREGIDO: Frame para combo y botones - DEFINIDO ANTES DE USAR
        combo_frame = tk.Frame(package_selector_frame, bg=self.styles.COLORS['secondary_bg'])
        combo_frame.pack(side="left", fill="x", expand=True)

        self.package_var = tk.StringVar()
        self.package_combo = ttk.Combobox(
            combo_frame,
            textvariable=self.package_var,
            font=("Segoe UI", 10),
            height=8,
            values=self.all_packages
        )
        self.package_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # ✅ AUTOMATIZACIÓN MEJORADA - Sin bloqueos de escritura
        self.package_combo.bind('<KeyRelease>', self._autocompletar_package_mejorado)
        self.package_combo.bind('<<ComboboxSelected>>', self._on_package_selected)
        self.package_combo.bind('<Return>', lambda e: self._aplicar_filtro_automatico())
        self.package_combo.bind('<FocusIn>', lambda e: self.package_combo.selection_range(0, tk.END))

        # ✅ CORREGIDO: Botones de acción para packages - AHORA DENTRO DEL COMBO_FRAME
        btn_package_frame = tk.Frame(combo_frame, bg=self.styles.COLORS['secondary_bg'])
        btn_package_frame.pack(side="left", padx=(5, 0))

        # Botón para recargar packages
        self.btn_recargar = self._crear_boton_moderno(
            btn_package_frame,
            "🔄 Recargar",
            self._recargar_packages,
            "#ff9800"
        )
        self.btn_recargar.pack(side="left", padx=(0, 5))

        # Botón para estadísticas de la app
        self.btn_estadisticas = self._crear_boton_moderno(
            btn_package_frame,
            "📊 Estadísticas App",
            lambda: self._mostrar_estadisticas_app(self.package_var.get()) if self.package_var.get() else messagebox.showwarning("Advertencia", "Selecciona un package primero"),
            "#9c27b0"
        )
        self.btn_estadisticas.pack(side="left", padx=(0, 5))

        self.btn_limpiar_filtro = self._crear_boton_moderno(
            btn_package_frame,
            "🗑️ Limpiar Filtro",
            self._limpiar_filtro,
            "#6c757d"
        )
        self.btn_limpiar_filtro.pack(side="left")

        # Fila 2: Botones de control principales
        control_btn_frame = tk.Frame(search_frame, bg=self.styles.COLORS['secondary_bg'])
        control_btn_frame.pack(fill="x", pady=(5, 0))

        # Grupo izquierdo: Control de logcat
        left_btn_frame = tk.Frame(control_btn_frame, bg=self.styles.COLORS['secondary_bg'])
        left_btn_frame.pack(side="left")

        self.btn_iniciar = self._crear_boton_moderno(
            left_btn_frame,
            "▶️ Iniciar Monitoreo",
            self._iniciar_logcat,
            "#28a745"
        )
        self.btn_iniciar.pack(side="left", padx=(0, 8))

        self.btn_detener = self._crear_boton_moderno(
            left_btn_frame,
            "⏹️ Detener",
            self._detener_logcat,
            "#dc3545",
            state="disabled"
        )
        self.btn_detener.pack(side="left", padx=(0, 8))

        self.btn_limpiar_log = self._crear_boton_moderno(
            left_btn_frame,
            "🧹 Limpiar Pantalla",
            self._limpiar_logcat,
            "#6c757d"
        )
        self.btn_limpiar_log.pack(side="left", padx=(0, 8))

        self.btn_todos_logs = self._crear_boton_moderno(
            left_btn_frame,
            "📋 Todos los Logs",
            self._mostrar_todos_logs,
            "#607d8b"
        )
        self.btn_todos_logs.pack(side="left", padx=(0, 8))

        # Grupo derecho: Utilidades
        right_btn_frame = tk.Frame(control_btn_frame, bg=self.styles.COLORS['secondary_bg'])
        right_btn_frame.pack(side="right")

        self.btn_guardar = self._crear_boton_moderno(
            right_btn_frame,
            "💾 Guardar Log",
            self._guardar_log,
            "#17a2b8"
        )
        self.btn_guardar.pack(side="left", padx=(0, 8))

        # Panel de información en tiempo real
        info_frame = tk.Frame(control_frame, bg=self.styles.COLORS['secondary_bg'])
        info_frame.pack(fill="x", padx=15, pady=10)

        # Estado del dispositivo
        self.status_label = tk.Label(
            info_frame,
            text="🔍 Verificando dispositivo Android...",
            font=("Segoe UI", 10, "bold"),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            pady=4
        )
        self.status_label.pack(anchor="w")

        # Info del filtro y PID
        info_sub_frame = tk.Frame(info_frame, bg=self.styles.COLORS['secondary_bg'])
        info_sub_frame.pack(fill="x", pady=(5, 0))

        self.filter_info_label = tk.Label(
            info_sub_frame,
            text="🎯 Filtro: Ninguno",
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['accent']
        )
        self.filter_info_label.pack(side="left", padx=(0, 20))

        self.pid_info_label = tk.Label(
            info_sub_frame,
            text="📊 PID: No detectado",
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_secondary']
        )
        self.pid_info_label.pack(side="left")

        # Área de texto MEJORADA con colores optimizados
        text_container = tk.Frame(main_frame, bg="#1e1e1e", relief="sunken", bd=2)
        text_container.pack(fill="both", expand=True)

        # Configurar fuente monoespaciada mejorada
        self.custom_font = ("Consolas", 10)
        
        self.logcat_text = scrolledtext.ScrolledText(
            text_container,
            wrap="word",
            font=self.custom_font,
            bg="#1e1e1e",  # Fondo oscuro profesional
            fg="#e8e8e8",  # Texto claro con buen contraste
            padx=15,
            pady=15,
            state='normal',
            insertbackground='#ffffff',
            cursor="xterm",
            selectbackground="#3c3c3c",
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0
        )
        self.logcat_text.pack(fill="both", expand=True, padx=1, pady=1)

        # Configurar colores MEJORADOS para logs
        self._configurar_tags_colores_profesionales()

        # Barra de estado MEJORADA
        status_bar = tk.Frame(main_frame, bg="#2d2d2d", height=28)
        status_bar.pack(fill="x", pady=(10, 0))
        status_bar.pack_propagate(False)

        # Contadores a la izquierda
        counters_frame = tk.Frame(status_bar, bg="#2d2d2d")
        counters_frame.pack(side="left", padx=12)

        self.line_count_label = tk.Label(
            counters_frame,
            text="📈 Líneas: 0",
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#cccccc"
        )
        self.line_count_label.pack(side="left", padx=(0, 15))

        self.debug_count_label = tk.Label(
            counters_frame,
            text="🐛 DEBUG: 0",
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#4fc3f7"
        )
        self.debug_count_label.pack(side="left", padx=(0, 15))

        self.warn_count_label = tk.Label(
            counters_frame,
            text="⚠️ WARN: 0",
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#ffb74d"
        )
        self.warn_count_label.pack(side="left", padx=(0, 15))

        self.error_count_label = tk.Label(
            status_bar,
            text="❌ ERROR: 0",
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#ff8a80"
        )
        self.error_count_label.pack(side="left", padx=(0, 15))

        # Información de estado a la derecha
        status_info_frame = tk.Frame(status_bar, bg="#2d2d2d")
        status_info_frame.pack(side="right", padx=12)

        self.monitoring_status = tk.Label(
            status_info_frame,
            text="🔴 Monitoreo: INACTIVO",
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#ff8a80"
        )
        self.monitoring_status.pack(side="right", padx=(0, 10))

        # Atajos de teclado
        shortcuts_label = tk.Label(
            status_info_frame,
            text="⌨️ Ctrl+S: Guardar | Ctrl+L: Limpiar | Ctrl+F: Buscar",
            font=("Segoe UI", 8),
            bg="#2d2d2d",
            fg="#888888"
        )
        shortcuts_label.pack(side="right", padx=(0, 15))

        self.logcat_window.protocol("WM_DELETE_WINDOW", self._cerrar_logcat)

        # ✅ NUEVO: Inicializar contadores
        self.log_counters = {
            'DEBUG': 0,
            'INFO': 0,
            'WARN': 0,
            'ERROR': 0,
            'FATAL': 0,
            'VERBOSE': 0
        }

    def _verificar_y_cargar_automaticamente(self):
        """Verificar dispositivo y cargar packages automáticamente"""
        def proceso_automatico():
            # Primero verificar dispositivo
            result = self._ejecutar_adb("devices")
            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = []
                for line in lines[1:]:
                    if line.strip() and '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        devices.append({'device': device_id, 'model': 'Dispositivo Android'})
                
                if devices:
                    # Actualizar estado del dispositivo
                    device_info = devices[0]
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"✅ Dispositivo conectado: {device_info['device']} - Cargando packages...",
                        fg="#4caf50"
                    ))
                    
                    # Cargar packages automáticamente
                    self._cargar_packages_automatico()
                else:
                    self.root.after(0, lambda: self.status_label.config(
                        text="❌ No hay dispositivos Android conectados",
                        fg="#f44336"
                    ))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="❌ Error conectando con ADB",
                    fg="#f44336"
                ))

        threading.Thread(target=proceso_automatico, daemon=True).start()

    def _cargar_packages_automatico(self):
        """Cargar packages automáticamente"""
        def cargar_packages():
            result = self._ejecutar_adb("shell pm list packages")
            
            if result and result.returncode == 0:
                packages = []
                for line in result.stdout.split('\n'):
                    if line.startswith('package:'):
                        package_name = line.replace('package:', '').strip()
                        if package_name:
                            packages.append(package_name)
                
                packages.sort()
                self.all_packages = packages
                
                self.root.after(0, self._actualizar_packages_ui, packages)
            else:
                error_msg = "No se pudieron cargar los packages automáticamente"
                self.root.after(0, lambda: self.status_label.config(
                    text=f"⚠️ {error_msg}",
                    fg="#ff9800"
                ))

        threading.Thread(target=cargar_packages, daemon=True).start()

    def _actualizar_packages_ui(self, packages):
        """Actualizar la UI con la lista de packages"""
        self.package_combo['values'] = packages
        self.status_label.config(
            text=f"✅ {len(packages)} packages cargados - Selecciona o escribe para filtrar",
            fg="#4caf50"
        )
        
        # Detectar package del APK automáticamente
        self._detectar_package_apk_inteligente()

    def _crear_boton_moderno(self, parent, texto, comando, color, state="normal"):
        """Crear botón con diseño moderno"""
        btn = tk.Button(
            parent,
            text=texto,
            command=comando,
            font=("Segoe UI", 9),
            bg=color,
            fg="white",
            relief="flat",
            padx=14,
            pady=6,
            state=state,
            cursor="hand2",
            bd=0,
            highlightthickness=0
        )
        
        # Efectos hover
        btn.bind("<Enter>", lambda e: btn.config(bg=self._aumentar_brillo(color, 20)) if state != "disabled" else None)
        btn.bind("<Leave>", lambda e: btn.config(bg=color) if state != "disabled" else None)
        
        return btn

    def _aumentar_brillo(self, color, incremento):
        """Aumentar brillo de un color hexadecimal"""
        try:
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                
                r = min(255, r + incremento)
                g = min(255, g + incremento)
                b = min(255, b + incremento)
                
                return f"#{r:02x}{g:02x}{b:02x}"
        except:
            pass
        return color

    def _configurar_tags_colores_profesionales(self):
        """Configurar colores PROFESIONALES para diferentes niveles de log"""
        # ✅ COLORES PROFESIONALES MEJORADOS - Esquema oscuro optimizado
        self.logcat_text.tag_configure("VERBOSE", foreground="#6a9955")  # Verde suave
        self.logcat_text.tag_configure("DEBUG", foreground="#4fc3f7")    # Azul claro
        self.logcat_text.tag_configure("INFO", foreground="#e8e8e8")     # Blanco grisáceo (normal)
        self.logcat_text.tag_configure("WARN", foreground="#ffb74d")     # Amarillo anaranjado
        self.logcat_text.tag_configure("ERROR", foreground="#ff8a80")    # Rojo suave
        self.logcat_text.tag_configure("FATAL", foreground="#ff5252", background="#4a1f1f")  # Rojo intenso con fondo oscuro

        # Tags especiales
        self.logcat_text.tag_configure("PACKAGE_HIGHLIGHT", foreground="#ce9178")  # Naranja suave para packages
        self.logcat_text.tag_configure("TIMESTAMP", foreground="#569cd6")  # Azul para timestamps

    def _autocompletar_package_mejorado(self, event):
        """Autocompletado MEJORADO - Permite escribir siempre sin importar coincidencias"""
        # Ignorar teclas de navegación y control
        if event.keysym in ['Return', 'Escape', 'Up', 'Down', 'Control_L', 'Control_R']:
            return
        
        current_text = self.package_var.get()
        
        if not current_text:
            # Si no hay texto, mostrar todos los packages
            self.package_combo['values'] = self.all_packages
            return
        
        # ✅ MEJORADO: Búsqueda que no interfiere con la escritura
        current_lower = current_text.lower()
        
        # Filtrar packages que contengan el texto
        filtered = [pkg for pkg in self.all_packages if current_lower in pkg.lower()]
        
        # Actualizar valores del combobox SIN interferir con la escritura
        self.package_combo['values'] = filtered
        
        # Solo mostrar dropdown si hay coincidencias
        if filtered:
            # Pequeño delay para no ser intrusivo
            self.logcat_window.after(100, lambda: self.package_combo.event_generate('<Down>'))

    def _mostrar_info_adb(self, event=None):
        """Mostrar información sobre ADB"""
        messagebox.showinfo(
            "Información ADB",
            f"Ruta ADB actual: {self.adb_path}\n\n"
            "Atajos de teclado:\n"
            "• Ctrl+S: Guardar log\n"
            "• Ctrl+L: Limpiar pantalla\n"
            "• Ctrl+F: Enfocar búsqueda\n\n"
            "Funcionalidades automáticas:\n"
            "• Carga automática de packages al iniciar\n"
            "• Filtro automático al seleccionar package\n"
            "• Detección automática de dispositivo\n\n"
            "Si ADB no funciona:\n"
            "1. Ve a 'Configurar Herramientas'\n"
            "2. Establece la ruta correcta a adb.exe"
        )

    def _on_package_selected(self, event):
        """Cuando se selecciona un package del combobox - APLICACIÓN AUTOMÁTICA"""
        package = self.package_var.get()
        if package:
            # Aplicar filtro automáticamente
            self._aplicar_filtro_automatico()

    def _aplicar_filtro_automatico(self):
        """Aplicar filtro automáticamente cuando se selecciona o escribe un package"""
        package = self.package_var.get().strip()
        if not package:
            return
        
        self.current_filter = package
        self.filter_info_label.config(text=f"🎯 Filtro: {package}")
        
        # Obtener PID automáticamente
        pid = self._obtener_pid_package(package)
        if pid:
            self.pid_info_label.config(text=f"📊 PID: {pid}")
            self.status_label.config(
                text=f"✅ Filtro aplicado automáticamente: {package} (PID: {pid})",
                fg="#4caf50"
            )
            
            # ✅ NUEVO: Preguntar si quiere ver estadísticas
            self.root.after(1000, lambda: self._preguntar_estadisticas(package))
            
        else:
            self.pid_info_label.config(text="📊 PID: No ejecutándose")
            self.status_label.config(
                text=f"⚠️ Filtro aplicado automáticamente: {package} - App no ejecutándose",
                fg="#ff9800"
            )

    def _detectar_package_apk_inteligente(self):
        """Detección MEJORADA del package name del APK analizado"""
        try:
            package_name = None
            
            # ✅ MEJORADO: Buscar en múltiples ubicaciones
            if self.apk_analyzer:
                # Intentar obtener del analyzer actual
                if hasattr(self.apk_analyzer, 'current_analysis'):
                    analysis = self.apk_analyzer.current_analysis
                    if analysis and 'parsed_info' in analysis:
                        package_name = analysis['parsed_info'].get('package')
                
                # Si no, intentar del parsed_info directo
                if not package_name and hasattr(self.apk_analyzer, 'parsed_info'):
                    package_name = self.apk_analyzer.parsed_info.get('package')
            
            # Buscar en componentes
            if not package_name and self.components:
                if 'current_analysis' in self.components:
                    analysis = self.components['current_analysis']
                    if analysis and 'parsed_info' in analysis:
                        package_name = analysis['parsed_info'].get('package')
                
                # Último intento: buscar en parsed_info directo de componentes
                if not package_name and 'parsed_info' in self.components:
                    package_name = self.components['parsed_info'].get('package')
            
            if package_name and package_name != 'No detectado':
                self.current_apk_package = package_name
                
                # Verificar si el package existe en el dispositivo
                if package_name in self.all_packages:
                    self.package_var.set(package_name)
                    self.package_combo.set(package_name)
                    
                    # Aplicar filtro automáticamente
                    self.root.after(500, lambda: self._aplicar_filtro_automatico())
                    
        except Exception as e:
            self.logger.log_error("Error detectando package automático", e)

    def _preguntar_estadisticas(self, package_name):
        """Preguntar al usuario si quiere ver estadísticas de la app"""
        if hasattr(self, 'estadisticas_preguntadas') and self.estadisticas_preguntadas:
            return
            
        self.estadisticas_preguntadas = True
        
        respuesta = messagebox.askyesno(
            "Estadísticas de la Aplicación",
            f"¿Te gustaría ver las estadísticas de rendimiento de '{package_name}'?\n\n"
            "Esto abrirá la aplicación en el dispositivo y mostrará:\n"
            "• Uso de memoria (RAM)\n"
            "• Uso de CPU\n"
            "• Consumo de datos\n"
            "• Información general de rendimiento"
        )
        
        if respuesta:
            self._mostrar_estadisticas_app(package_name)

    def _limpiar_filtro(self):
        """Limpiar filtro actual"""
        self.current_filter = ""
        self.package_var.set("")
        self.filter_info_label.config(text="🎯 Filtro: Ninguno")
        self.pid_info_label.config(text="📊 PID: No detectado")
        self.status_label.config(
            text="ℹ️ Filtro limpiado - Mostrando todos los logs",
            fg="#17a2b8"
        )

    def _mostrar_todos_logs(self):
        """Mostrar todos los logs sin filtro"""
        self._limpiar_filtro()
        self.status_label.config(
            text="📋 Mostrando todos los logs del sistema",
            fg="#17a2b8"
        )

    def _iniciar_logcat(self):
        """Iniciar monitoreo de logcat"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.btn_iniciar.config(state="disabled")
        self.btn_detener.config(state="normal")
        self.monitoring_status.config(text="🟢 Monitoreo: ACTIVO", fg="#4caf50")
        
        # Limpiar logs anteriores
        self._limpiar_logcat()
        
        # Construir comando logcat
        cmd = ["logcat", "-v", "time", "-T", "50"]  # Mostrar últimos 50 logs
        
        if self.current_filter:
            if self.current_pid:
                cmd.extend(["--pid", self.current_pid])
            else:
                cmd.extend([self.current_filter, "*:S"])
        
        def monitorear_logcat():
            try:
                full_cmd = [self.adb_path] + cmd if self.adb_path != "adb" else cmd
                
                self.logcat_process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    bufsize=1
                )
                
                for linea in iter(self.logcat_process.stdout.readline, ''):
                    if not self.is_monitoring:
                        break
                    if linea.strip():
                        self.root.after(0, self._procesar_linea_logcat, linea)
                
            except Exception as e:
                self.root.after(0, self._manejar_error_logcat, str(e))
            finally:
                self.root.after(0, self._detener_logcat)

        threading.Thread(target=monitorear_logcat, daemon=True).start()
        
        filter_info = f" - Filtro: {self.current_filter}" if self.current_filter else " - Todos los logs"
        self.status_label.config(
            text=f"🔴 Monitoreando Logcat{filter_info}",
            fg="#ff9800"
        )

    def _detener_logcat(self):
        """Detener monitoreo de logcat"""
        self.is_monitoring = False
        
        if self.logcat_process:
            try:
                self.logcat_process.terminate()
                self.logcat_process.wait(timeout=5)
            except:
                try:
                    self.logcat_process.kill()
                except:
                    pass
            finally:
                self.logcat_process = None
        
        self.btn_iniciar.config(state="normal")
        self.btn_detener.config(state="disabled")
        self.monitoring_status.config(text="🔴 Monitoreo: INACTIVO", fg="#ff8a80")
        self.status_label.config(
            text="⏹️ Logcat detenido",
            fg="#6c757d"
        )

    def _manejar_error_logcat(self, error_msg):
        """Manejar errores del logcat"""
        self._detener_logcat()
        messagebox.showerror("Error Logcat", f"Error al ejecutar logcat:\n{error_msg}")

    def _procesar_linea_logcat(self, linea):
        """Procesar y mostrar una línea de logcat - MEJORADO visualmente"""
        if not self.is_monitoring or not linea.strip():
            return

        tag = self._determinar_nivel_log(linea)
        
        # Actualizar contadores
        if tag in self.log_counters:
            self.log_counters[tag] += 1
            self._actualizar_contadores_ui()

        self.logcat_text.config(state='normal')
        
        # ✅ MEJORADO: Procesamiento visual mejorado
        linea_procesada = self._mejorar_visualizacion_linea(linea)
        self.logcat_text.insert(tk.END, linea_procesada, tag)
        self.logcat_text.see(tk.END)
        self.logcat_text.config(state='normal')
        
        # Actualizar contador de líneas periódicamente
        if int(self.logcat_text.index('end-1c').split('.')[0]) % 5 == 0:
            self._actualizar_contador_lineas()

    def _mejorar_visualizacion_linea(self, linea):
        """Mejorar visualización de la línea de log"""
        # Resaltar timestamps
        if re.match(r'\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}', linea[:18]):
            return linea
        return linea

    def _determinar_nivel_log(self, linea):
        """Determinar el nivel del log para colorear - MEJORADO"""
        linea_upper = linea.upper()
        
        # ✅ DETECCIÓN MEJORADA con expresiones regulares
        if re.search(r'\bE\b|\bERROR\b| E/', linea_upper):
            return "ERROR"
        elif re.search(r'\bW\b|\bWARN\b| W/', linea_upper):
            return "WARN"
        elif re.search(r'\bD\b|\bDEBUG\b| D/', linea_upper):
            return "DEBUG"
        elif re.search(r'\bV\b|\bVERBOSE\b| V/', linea_upper):
            return "VERBOSE"
        elif re.search(r'\bF\b|\bFATAL\b| F/', linea_upper):
            return "FATAL"
        elif re.search(r'\bI\b|\bINFO\b| I/', linea_upper):
            return "INFO"
        else:
            return "INFO"

    def _actualizar_contadores_ui(self):
        """Actualizar los contadores de logs en la UI"""
        self.debug_count_label.config(text=f"🐛 DEBUG: {self.log_counters['DEBUG']}")
        self.warn_count_label.config(text=f"⚠️ WARN: {self.log_counters['WARN']}")
        self.error_count_label.config(text=f"❌ ERROR: {self.log_counters['ERROR']}")

    def _actualizar_contador_lineas(self):
        """Actualizar contador de líneas"""
        line_count = self.logcat_text.get('1.0', 'end-1c').count('\n') + 1
        self.line_count_label.config(text=f"📈 Líneas: {line_count}")

    def _limpiar_logcat(self):
        """Limpiar el área de texto del logcat y contadores"""
        self.logcat_text.config(state='normal')
        self.logcat_text.delete(1.0, tk.END)
        self.logcat_text.config(state='normal')
        
        # ✅ NUEVO: Reiniciar contadores
        for key in self.log_counters:
            self.log_counters[key] = 0
        self._actualizar_contadores_ui()
        self._actualizar_contador_lineas()

    def _guardar_log(self):
        """Guardar log actual en archivo con nombre mejorado"""
        try:
            contenido = self.logcat_text.get('1.0', 'end-1c')
            if not contenido.strip():
                messagebox.showwarning("Advertencia", "No hay logs para guardar")
                return
            
            # ✅ MEJORADO: Nombre de archivo con timestamp, package y filtro
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Determinar el nombre base según el filtro aplicado
            if self.current_filter:
                # Limpiar el nombre del filtro para que sea válido como nombre de archivo
                clean_filter = "".join(c for c in self.current_filter if c.isalnum() or c in ('-', '_'))
                base_name = f"logcat_{clean_filter}_{timestamp}"
            else:
                base_name = f"logcat_all_logs_{timestamp}"
            
            # Si hay un package de APK analizado, incluirlo también
            if self.current_apk_package and self.current_apk_package != self.current_filter:
                clean_apk = "".join(c for c in self.current_apk_package if c.isalnum() or c in ('-', '_'))
                base_name = f"logcat_{clean_apk}_{timestamp}"
            
            filename = f"{base_name}.txt"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                initialfile=filename
            )
            
            if filepath:
                # ✅ MEJORADO: Agregar metadatos al inicio del archivo
                metadata = f"""LOGCAT EXPORTADO - METADATOS
================================
Fecha y hora: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Package analizado: {self.current_apk_package or 'No especificado'}
Filtro aplicado: {self.current_filter or 'Todos los logs'}
PID monitorizado: {self.current_pid or 'No aplicable'}
Total líneas: {self.logcat_text.get('1.0', 'end-1c').count(chr(10)) + 1}
================================
LOGS:
================================

"""
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(metadata)
                    f.write(contenido)
                
                # ✅ CORREGIDO: Sin backslash en f-string
                messagebox.showinfo("Éxito", "Log guardado en:\n" + filepath)
                self.status_label.config(
                    text=f"💾 Log guardado: {Path(filepath).name}",
                    fg="#4caf50"
                )
                
        except Exception as e:
            messagebox.showerror("Error", "No se pudo guardar el log:\n" + str(e))

    def _cerrar_logcat(self):
        """Manejar cierre de la ventana"""
        self._detener_logcat()
        self.logcat_window.destroy()

    def set_apk_analyzer(self, apk_analyzer):
        """Establecer referencia al APK analyzer"""
        self.apk_analyzer = apk_analyzer

    def set_components(self, components):
        """Establecer referencia a los componentes"""
        self.components = components

    def set_config_manager(self, config_manager):
        """Establecer referencia al config manager"""
        self.config_manager = config_manager
        self.adb_path = self._get_adb_path()

    # Los métodos de estadísticas que ya estaban implementados
    def _abrir_app_en_dispositivo(self, package_name):
        """Abrir la aplicación en el dispositivo"""
        try:
            result = self._ejecutar_adb(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
            if result and result.returncode == 0:
                return True, f"✅ Aplicación {package_name} abierta en el dispositivo"
            else:
                return False, f"❌ No se pudo abrir la aplicación {package_name}"
        except Exception as e:
            return False, f"❌ Error abriendo aplicación: {str(e)}"

    def _obtener_estadisticas_app(self, package_name):
        """Obtener estadísticas de memoria y datos de la aplicación"""
        try:
            stats = {}
            
            # Obtener uso de memoria
            result = self._ejecutar_adb(f"shell dumpsys meminfo {package_name}")
            if result and result.returncode == 0:
                memoria_info = self._parsear_memoria(result.stdout)
                stats.update(memoria_info)
            
            # Obtener uso de datos
            result = self._ejecutar_adb(f"shell dumpsys package {package_name} | grep -A 20 'Data stats:'")
            if result and result.returncode == 0:
                datos_info = self._parsear_datos(result.stdout)
                stats.update(datos_info)
            
            # Obtener información de CPU
            pid = self._obtener_pid_package(package_name)
            if pid:
                result = self._ejecutar_adb(f"shell top -n 1 -p {pid}")
                if result and result.returncode == 0:
                    cpu_info = self._parsear_cpu(result.stdout, package_name)
                    stats.update(cpu_info)
            
            return True, stats
            
        except Exception as e:
            return False, f"❌ Error obteniendo estadísticas: {str(e)}"

    def _parsear_memoria(self, output):
        """Parsear información de memoria del output de dumpsys meminfo"""
        memoria = {}
        try:
            # Buscar líneas con información de memoria
            lines = output.split('\n')
            for line in lines:
                if 'TOTAL' in line and 'PSS:' in line:
                    # Extraer PSS (Proportional Set Size)
                    pss_match = re.search(r'PSS:\s+(\d+)', line)
                    if pss_match:
                        memoria['pss_kb'] = int(pss_match.group(1))
                        memoria['pss_mb'] = round(int(pss_match.group(1)) / 1024, 2)
                
                elif 'Java Heap:' in line:
                    heap_match = re.search(r'Java Heap:\s+(\d+)', line)
                    if heap_match:
                        memoria['java_heap_kb'] = int(heap_match.group(1))
                        memoria['java_heap_mb'] = round(int(heap_match.group(1)) / 1024, 2)
                
                elif 'Native Heap:' in line:
                    native_match = re.search(r'Native Heap:\s+(\d+)', line)
                    if native_match:
                        memoria['native_heap_kb'] = int(native_match.group(1))
                        memoria['native_heap_mb'] = round(int(native_match.group(1)) / 1024, 2)
            
        except Exception as e:
            self.logger.log_error(f"Error parseando memoria: {e}")
        
        return memoria

    def _parsear_datos(self, output):
        """Parsear información de uso de datos"""
        datos = {}
        try:
            lines = output.split('\n')
            for line in lines:
                if 'Data received:' in line:
                    received_match = re.search(r'Data received:\s+([\d.]+)\s*(\w+)', line)
                    if received_match:
                        datos['datos_recibidos'] = received_match.group(1) + received_match.group(2)
                
                elif 'Data sent:' in line:
                    sent_match = re.search(r'Data sent:\s+([\d.]+)\s*(\w+)', line)
                    if sent_match:
                        datos['datos_enviados'] = sent_match.group(1) + sent_match.group(2)
                
                elif 'Foreground activities:' in line:
                    fg_match = re.search(r'Foreground activities:\s+(\d+)', line)
                    if fg_match:
                        datos['actividades_foreground'] = int(fg_match.group(1))
        
        except Exception as e:
            self.logger.log_error(f"Error parseando datos: {e}")
        
        return datos

    def _parsear_cpu(self, output, package_name):
        """Parsear información de CPU"""
        cpu = {}
        try:
            lines = output.split('\n')
            for line in lines:
                if package_name in line:
                    # Formato típico de top: PID USER PR NI VIRT RES SHR S %CPU %MEM TIME+ COMMAND
                    parts = line.split()
                    if len(parts) >= 9:
                        cpu['cpu_usage'] = parts[8] + '%'
                        cpu['memory_usage'] = parts[9] + '%' if len(parts) > 9 else 'N/A'
                        break
        except Exception as e:
            self.logger.log_error(f"Error parseando CPU: {e}")
        
        return cpu

    def _mostrar_estadisticas_app(self, package_name):
        """Mostrar estadísticas de la aplicación"""
        def obtener_estadisticas():
            progress_dialog = self._mostrar_dialogo_progreso(self.logcat_window, "Obteniendo estadísticas...")
            
            try:
                # Primero abrir la aplicación
                success_open, msg_open = self._abrir_app_en_dispositivo(package_name)
                
                # Luego obtener estadísticas
                success_stats, result_stats = self._obtener_estadisticas_app(package_name)
                
                self.root.after(0, lambda: self._procesar_estadisticas(
                    progress_dialog, package_name, success_open, msg_open, success_stats, result_stats))
                    
            except Exception as e:
                self.root.after(0, lambda: self._procesar_error_estadisticas(progress_dialog, str(e)))

        threading.Thread(target=obtener_estadisticas, daemon=True).start()

    def _procesar_estadisticas(self, progress_dialog, package_name, success_open, msg_open, success_stats, result_stats):
        """Procesar y mostrar estadísticas obtenidas"""
        progress_dialog.destroy()
        
        dialog = tk.Toplevel(self.logcat_window)
        dialog.title(f"Estadísticas - {package_name}")
        dialog.geometry("500x600")
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(self.logcat_window)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Título
        tk.Label(
            main_frame,
            text=f"📊 Estadísticas de {package_name}",
            font=("Segoe UI", 14, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['accent'],
            pady=10
        ).pack()

        # Resultado de apertura
        open_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        open_frame.pack(fill="x", pady=10)
        
        open_icon = "✅" if success_open else "❌"
        open_color = "#4caf50" if success_open else "#f44336"
        
        tk.Label(
            open_frame,
            text=f"{open_icon} Estado: {msg_open}",
            font=("Segoe UI", 10),
            bg=self.styles.COLORS['primary_bg'],
            fg=open_color,
            justify="left"
        ).pack(anchor="w")

        if success_stats and isinstance(result_stats, dict):
            # Mostrar estadísticas en un frame con scroll
            stats_frame = tk.Frame(main_frame)
            stats_frame.pack(fill="both", expand=True, pady=10)

            stats_text = scrolledtext.ScrolledText(
                stats_frame,
                wrap="word",
                font=("Consolas", 9),
                bg=self.styles.COLORS['secondary_bg'],
                fg=self.styles.COLORS['text_primary'],
                height=15,
                padx=10,
                pady=10
            )
            stats_text.pack(fill="both", expand=True)

            # Formatear estadísticas
            stats_text.insert("1.0", "📈 ESTADÍSTICAS DETALLADAS\n")
            stats_text.insert("2.0", "=" * 50 + "\n\n")
            
            # Memoria
            stats_text.insert("end", "🧠 USO DE MEMORIA:\n")
            stats_text.insert("end", "-" * 30 + "\n")
            if 'pss_mb' in result_stats:
                stats_text.insert("end", f"• Memoria total (PSS): {result_stats['pss_mb']} MB\n")
            if 'java_heap_mb' in result_stats:
                stats_text.insert("end", f"• Java Heap: {result_stats['java_heap_mb']} MB\n")
            if 'native_heap_mb' in result_stats:
                stats_text.insert("end", f"• Native Heap: {result_stats['native_heap_mb']} MB\n")
            stats_text.insert("end", "\n")
            
            # CPU
            stats_text.insert("end", "⚡ USO DE CPU:\n")
            stats_text.insert("end", "-" * 30 + "\n")
            if 'cpu_usage' in result_stats:
                stats_text.insert("end", f"• Uso de CPU: {result_stats['cpu_usage']}\n")
            if 'memory_usage' in result_stats:
                stats_text.insert("end", f"• Uso de Memoria: {result_stats['memory_usage']}\n")
            stats_text.insert("end", "\n")
            
            # Datos
            stats_text.insert("end", "📡 USO DE DATOS:\n")
            stats_text.insert("end", "-" * 30 + "\n")
            if 'datos_recibidos' in result_stats:
                stats_text.insert("end", f"• Datos recibidos: {result_stats['datos_recibidos']}\n")
            if 'datos_enviados' in result_stats:
                stats_text.insert("end", f"• Datos enviados: {result_stats['datos_enviados']}\n")
            if 'actividades_foreground' in result_stats:
                stats_text.insert("end", f"• Actividades en foreground: {result_stats['actividades_foreground']}\n")
            
            stats_text.config(state='disabled')
        else:
            # Mostrar error
            error_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
            error_frame.pack(fill="both", expand=True, pady=10)
            
            tk.Label(
                error_frame,
                text="❌ No se pudieron obtener estadísticas detalladas",
                font=("Segoe UI", 10),
                bg=self.styles.COLORS['primary_bg'],
                fg="#f44336",
                pady=10
            ).pack()
            
            if isinstance(result_stats, str):
                error_text = scrolledtext.ScrolledText(
                    error_frame,
                    wrap="word",
                    font=("Consolas", 8),
                    bg=self.styles.COLORS['secondary_bg'],
                    fg=self.styles.COLORS['text_primary'],
                    height=5
                )
                error_text.pack(fill="x", pady=5)
                error_text.insert("1.0", result_stats)
                error_text.config(state='disabled')

        # Botón cerrar
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=10)

        tk.Button(
            btn_frame,
            text="Cerrar",
            command=dialog.destroy,
            font=("Segoe UI", 9),
            bg="#6c757d",
            fg="white",
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side="right")

        self._centrar_dialogo(dialog, self.logcat_window)

    def _procesar_error_estadisticas(self, progress_dialog, error):
        """Procesar error al obtener estadísticas"""
        progress_dialog.destroy()
        messagebox.showerror("Error", f"No se pudieron obtener las estadísticas:\n{error}")

    def _mostrar_dialogo_progreso(self, parent, mensaje):
        """Mostrar diálogo de progreso"""
        dialog = tk.Toplevel(parent)
        dialog.title("Procesando")
        dialog.geometry("300x100")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.resizable(False, False)

        self._centrar_dialogo(dialog, parent)

        tk.Label(
            dialog,
            text=mensaje,
            font=("Segoe UI", 10),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            pady=20
        ).pack()

        progress = ttk.Progressbar(
            dialog,
            mode='indeterminate',
            length=200
        )
        progress.pack(pady=10)
        progress.start()

        return dialog

    def _centrar_dialogo(self, dialog, parent):
        """Centrar diálogo en la pantalla"""
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")