import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import subprocess
import sys
import os
import re
from pathlib import Path
import datetime

try:
    from components.custom_combobox import CustomCombobox
except ImportError:
    CustomCombobox = None

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
        if hasattr(self, 'package_combobox') and self.package_combobox:
            self.package_combobox.set_items(packages)
        
        self.status_label.config(
            text=f"✅ {len(packages)} packages recargados correctamente",
            fg="#4caf50"
        )

    def _obtener_pid_package(self, package_name):
        """Obtener el PID de un package usando pidof de forma robusta"""
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
        self.logcat_window.minsize(800, 400)
        
        # Detectar pantalla actual
        self._detectar_pantalla_actual()
        
        self.logcat_window.configure(bg=self.styles.COLORS['primary_bg'])
        self._posicionar_ventana_inteligente()
        self.logcat_window.bind("<Control-s>", lambda e: self._guardar_log())
        self.logcat_window.bind("<Control-l>", lambda e: self._limpiar_logcat())
        self.logcat_window.bind("<Control-f>", lambda e: self.package_combobox.focus() if hasattr(self, 'package_combobox') else None)

        self.logcat_window.bind("<Button-1>", self._cerrar_dropdown_al_clic_exterior)
        
        self._crear_ui_logcat_mejorada()
        self._verificar_y_cargar_automaticamente()

    def _cerrar_dropdown_al_clic_exterior(self, event):
        """Cerrar el dropdown del combobox al hacer clic fuera"""
        if hasattr(self, 'package_combobox') and self.package_combobox:
            # Verificar si el clic fue fuera del combobox
            combobox_widget = self.package_combobox.main_frame
            if (event.widget != combobox_widget and 
                not combobox_widget.winfo_containing(event.x_root, event.y_root)):
                
                # Ocultar dropdown si está visible
                if hasattr(self.package_combobox, 'dropdown_visible') and self.package_combobox.dropdown_visible:
                    self.package_combobox._hide_dropdown()

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
            text="🐈 LOGCAT",
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

        # Frame para combo y botones
        combo_frame = tk.Frame(package_selector_frame, bg=self.styles.COLORS['secondary_bg'])
        combo_frame.pack(side="left", fill="x", expand=True)

        if CustomCombobox:
            self.package_combobox = CustomCombobox(
                parent=combo_frame,
                all_items=self.all_packages,
                styles=self.styles,
                on_select_callback=self._on_package_selected,
                width=40
            )
            self.package_combobox.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            # ✅ NUEVO: Binding para cerrar dropdown al hacer clic en la ventana
            self.package_combobox.main_frame.bind("<Button-1>", lambda e: "break")  # Prevenir propagación
        else:
            # Fallback a combobox tradicional
            self.package_var = tk.StringVar()
            self.package_combo = ttk.Combobox(
                combo_frame,
                textvariable=self.package_var,
                font=("Segoe UI", 10),
                height=8,
                values=self.all_packages
            )
            self.package_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
            self.package_combo.bind('<<ComboboxSelected>>', self._on_package_selected)

        # Botones de acción para packages
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
            lambda: self._mostrar_estadisticas_app(self._get_current_package()),
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

        # Inicializar contadores
        self.log_counters = {
            'DEBUG': 0,
            'INFO': 0,
            'WARN': 0,
            'ERROR': 0,
            'FATAL': 0,
            'VERBOSE': 0
        }

    def _get_current_package(self):
        """Obtener el package actual del combobox"""
        if hasattr(self, 'package_combobox'):
            return self.package_combobox.get()
        elif hasattr(self, 'package_var'):
            return self.package_var.get()
        return ""

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
        if hasattr(self, 'package_combobox'):
            self.package_combobox.set_items(packages)
        
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
        # COLORES PROFESIONALES MEJORADOS - Esquema oscuro optimizado
        self.logcat_text.tag_configure("VERBOSE", foreground="#6a9955")  # Verde suave
        self.logcat_text.tag_configure("DEBUG", foreground="#4fc3f7")    # Azul claro
        self.logcat_text.tag_configure("INFO", foreground="#e8e8e8")     # Blanco grisáceo (normal)
        self.logcat_text.tag_configure("WARN", foreground="#ffb74d")     # Amarillo anaranjado
        self.logcat_text.tag_configure("ERROR", foreground="#ff8a80")    # Rojo suave
        self.logcat_text.tag_configure("FATAL", foreground="#ff5252", background="#4a1f1f")  # Rojo intenso con fondo oscuro

        # Tags especiales
        self.logcat_text.tag_configure("PACKAGE_HIGHLIGHT", foreground="#ce9178")  # Naranja suave para packages
        self.logcat_text.tag_configure("TIMESTAMP", foreground="#569cd6")  # Azul para timestamps

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

    def _on_package_selected(self, package_name):
        """Cuando se selecciona un package del combobox - SIN APERTURA AUTOMÁTICA"""
        if package_name:
            self.current_filter = package_name
            self.filter_info_label.config(text=f"🎯 Filtro: {package_name}")
            
            # Obtener PID automáticamente
            pid = self._obtener_pid_package(package_name)
            if pid:
                self.pid_info_label.config(text=f"📊 PID: {pid}")
                self.status_label.config(
                    text=f"✅ Filtro aplicado automáticamente: {package_name} (PID: {pid})",
                    fg="#4caf50"
                )
            else:
                self.pid_info_label.config(text="📊 PID: No ejecutándose")
                self.status_label.config(
                    text=f"⚠️ Filtro aplicado automáticamente: {package_name} - App no ejecutándose",
                    fg="#ff9800"
                )

    def _detectar_package_apk_inteligente(self):
        """Detección MEJORADA del package name del APK analizado"""
        try:
            package_name = None
            
            # MEJORADO: Buscar en múltiples ubicaciones
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
                    if hasattr(self, 'package_combobox'):
                        self.package_combobox.set(package_name)
                    elif hasattr(self, 'package_var'):
                        self.package_var.set(package_name)
                    
                    # Aplicar filtro automáticamente
                    self.root.after(500, lambda: self._on_package_selected(package_name))
                    
        except Exception as e:
            self.logger.log_error("Error detectando package automático", e)

    def _limpiar_filtro(self):
        """Limpiar filtro actual"""
        self.current_filter = ""
        if hasattr(self, 'package_combobox'):
            self.package_combobox.set("")
        elif hasattr(self, 'package_var'):
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
        """Iniciar monitoreo de logcat MEJORADO - SIN ABRIR APP AUTOMÁTICAMENTE"""
        if self.is_monitoring:
            return

        # Verificar conexión antes de iniciar
        def verificar_conexion():
            result = self._ejecutar_adb("devices")
            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = [line for line in lines[1:] if line.strip() and '\tdevice' in line]
                return len(devices) > 0
            return False

        if not verificar_conexion():
            respuesta = messagebox.askyesno(
                "Dispositivo no detectado", 
                "No se detecta un dispositivo Android conectado.\n\n"
                "¿Quieres intentar reconectar automáticamente?"
            )
            if respuesta:
                self._reconectar_dispositivo()
            return

        self.is_monitoring = True
        self.btn_iniciar.config(state="disabled")
        self.btn_detener.config(state="normal")
        self.monitoring_status.config(text="🟢 Monitoreo: ACTIVO", fg="#4caf50")
        
        # Limpiar logs anteriores
        self._limpiar_logcat()
        
        # Construir comando logcat mejorado
        cmd = ["logcat", "-v", "time", "-T", "100"]  # Mostrar últimos 100 logs
        
        if self.current_filter:
            if self.current_pid:
                cmd.extend(["--pid", self.current_pid])
            else:
                # Usar filtro por tag/package
                cmd.extend(["-s", self.current_filter])

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
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Leer líneas continuamente
                while self.is_monitoring:
                    linea = self.logcat_process.stdout.readline()
                    if not linea and self.is_monitoring:
                        # Si no hay línea pero seguimos monitoreando, esperar un poco
                        import time
                        time.sleep(0.1)
                        continue
                    
                    if linea.strip() and self.is_monitoring:
                        self.root.after(0, self._procesar_linea_logcat, linea)
                    
                    # Verificar si el proceso terminó inesperadamente
                    if self.logcat_process.poll() is not None and self.is_monitoring:
                        self.root.after(0, self._manejar_desconexion_logcat)
                        break
                        
            except Exception as e:
                self.root.after(0, self._manejar_error_logcat, str(e))
            finally:
                if self.is_monitoring:
                    self.root.after(0, self._detener_logcat)

        threading.Thread(target=monitorear_logcat, daemon=True).start()
        
        filter_info = f" - Filtro: {self.current_filter}" if self.current_filter else " - Todos los logs"
        self.status_label.config(
            text=f"🔴 Monitoreando Logcat{filter_info}",
            fg="#ff9800"
        )

    def _reconectar_dispositivo(self):
        """Intentar reconectar el dispositivo"""
        self.status_label.config(text="🔄 Reconectando dispositivo...", fg="#ff9800")
        
        def reconectar():
            # Reiniciar servidor ADB
            self._ejecutar_adb("kill-server")
            import time
            time.sleep(2)
            self._ejecutar_adb("start-server")
            time.sleep(3)
            
            # Verificar si se reconectó
            result = self._ejecutar_adb("devices")
            if result and any('\tdevice' in line for line in result.stdout.split('\n')):
                self.root.after(0, lambda: self.status_label.config(
                    text="✅ Dispositivo reconectado - Puedes iniciar Logcat",
                    fg="#4caf50"
                ))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="❌ No se pudo reconectar - Verifica conexión USB",
                    fg="#f44336"
                ))
        
        threading.Thread(target=reconectar, daemon=True).start()

    def _manejar_desconexion_logcat(self):
        """Manejar desconexión inesperada del logcat"""
        if self.is_monitoring:
            self.is_monitoring = False
            self.logcat_process = None
            
            self.btn_iniciar.config(state="normal")
            self.btn_detener.config(state="disabled")
            self.monitoring_status.config(text="🔴 Monitoreo: DESCONECTADO", fg="#ff8a80")
            
            self.status_label.config(
                text="❌ Logcat se desconectó inesperadamente - Verifica conexión del dispositivo",
                fg="#f44336"
            )
            
            # Preguntar si quiere reconectar
            self.root.after(1000, lambda: self._preguntar_reconexion())

    def _preguntar_reconexion(self):
        """Preguntar al usuario si quiere reconectar"""
        if not self.is_monitoring:
            respuesta = messagebox.askyesno(
                "Conexión perdida",
                "El monitoreo de Logcat se ha detenido inesperadamente.\n\n"
                "¿Quieres intentar reconectar automáticamente?"
            )
            if respuesta:
                self._reconectar_y_reiniciar()

    def _reconectar_y_reiniciar(self):
        """Reconectar y reiniciar logcat"""
        self.status_label.config(text="🔄 Reconectando y reiniciando Logcat...", fg="#ff9800")
        
        def proceso_reconexion():
            self._reconectar_dispositivo()
            import time
            time.sleep(3)
            
            # Verificar si se reconectó
            result = self._ejecutar_adb("devices")
            if result and any('\tdevice' in line for line in result.stdout.split('\n')):
                self.root.after(0, self._iniciar_logcat)
        
        threading.Thread(target=proceso_reconexion, daemon=True).start()

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
        
        # MEJORADO: Procesamiento visual mejorado
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
        
        # DETECCIÓN MEJORADA con expresiones regulares
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
        
        # Reiniciar contadores
        for key in self.log_counters:
            self.log_counters[key] = 0
        self._actualizar_contadores_ui()
        self._actualizar_contador_lineas()

    def _guardar_log(self):
        """Guardar log actual SIN detener el monitoreo"""
        try:
            # Obtener contenido actual SIN interferir con el monitoreo
            self.logcat_text.config(state='normal')
            contenido = self.logcat_text.get('1.0', 'end-1c')
            self.logcat_text.config(state='normal')
            
            if not contenido.strip():
                messagebox.showwarning("Advertencia", "No hay logs para guardar")
                return
            
            # Nombre de archivo con timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if self.current_filter:
                clean_filter = "".join(c for c in self.current_filter if c.isalnum() or c in ('-', '_'))
                base_name = f"logcat_{clean_filter}_{timestamp}"
            else:
                base_name = f"logcat_all_logs_{timestamp}"
            
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
                # Agregar metadatos
                estado_monitoreo = "ACTIVO" if self.is_monitoring else "INACTIVO"
                metadata = f"""LOGCAT EXPORTADO - METADATOS
================================
Fecha y hora: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Package analizado: {self.current_apk_package or 'No especificado'}
Filtro aplicado: {self.current_filter or 'Todos los logs'}
PID monitorizado: {self.current_pid or 'No aplicable'}
Monitoreo activo: {estado_monitoreo}
Total líneas: {contenido.count(chr(10)) + 1}
================================
LOGS:
================================

"""
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(metadata)
                    f.write(contenido)
                
                messagebox.showinfo("Éxito", f"Log guardado en:\n{filepath}\n\nMonitoreo: {estado_monitoreo}")
                self.status_label.config(
                    text=f"💾 Log guardado: {Path(filepath).name} (Monitoreo: {estado_monitoreo})",
                    fg="#4caf50"
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el log:\n{str(e)}")

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

    # ========== MÉTODOS DE ESTADÍSTICAS MEJORADOS ==========

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

    def _obtener_uid_package(self, package_name):
        """Obtener UID del package de forma robusta"""
        try:
            result = self._ejecutar_adb(f"shell dumpsys package {package_name} | grep userId")
            if result and result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if "userId=" in line:
                        match = re.search(r'userId=(\d+)', line)
                        if match:
                            return match.group(1)
            return None
        except Exception as e:
            self.logger.log_error(f"Error obteniendo UID para {package_name}: {e}")
            return None

    def _obtener_info_package(self, package_name):
        """Obtener información general del package de forma robusta"""
        info = {}
        try:
            result = self._ejecutar_adb(f"shell dumpsys package {package_name}")
            if result and result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if "versionName" in line:
                        match = re.search(r'versionName=([^\s]+)', line)
                        if match:
                            info['version'] = match.group(1)
                    elif "versionCode" in line:
                        match = re.search(r'versionCode=(\d+)', line)
                        if match:
                            info['version_code'] = match.group(1)
            
            uid = self._obtener_uid_package(package_name)
            if uid:
                info['uid'] = uid
            
        except Exception as e:
            self.logger.log_error(f"Error obteniendo info package: {e}")
        
        return info

    def _obtener_uso_memoria(self, package_name):
        """Obtener uso de memoria de forma robusta"""
        memoria = {}
        try:
            result = self._ejecutar_adb(f"shell dumpsys meminfo {package_name}")
            if result and result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'TOTAL' in line and 'PSS:' in line:
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
            
            # Si no se encontraron datos, establecer valores por defecto
            if not memoria:
                memoria['pss_mb'] = 0.0
                memoria['java_heap_mb'] = 0.0
                memoria['native_heap_mb'] = 0.0
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo memoria: {e}")
            memoria['pss_mb'] = 'Error'
            memoria['java_heap_mb'] = 'Error'
            memoria['native_heap_mb'] = 'Error'
        
        return memoria

    def _obtener_uso_cpu_mejorado(self, package_name):
        """Obtener uso de CPU de forma MÁS ROBUSTA"""
        cpu_stats = {}
        try:
            # Obtener UID del package primero
            uid = self._obtener_uid_package(package_name)
            
            # MÉTODO 1: Usar dumpsys cpuinfo con UID
            if uid:
                result = self._ejecutar_adb("shell dumpsys cpuinfo")
                if result and result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if f"{uid}:" in line or f"/{package_name}" in line:
                            match = re.search(r'(\d+\.?\d*)%\s+' + re.escape(f"{uid}:") + r'.*', line)
                            if not match:
                                match = re.search(r'(\d+\.?\d*)%\s+' + re.escape(f"/{package_name}"), line)
                            
                            if match:
                                cpu_stats['cpu_usage'] = f"{match.group(1)}%"
                                cpu_stats['cpu_detalle'] = line.strip()
                                break
            
            # MÉTODO 2: Usar top si el primer método falla
            if 'cpu_usage' not in cpu_stats:
                pid = self._obtener_pid_package(package_name)
                if pid:
                    result = self._ejecutar_adb(f"shell top -n 1 -b")
                    if result and result.returncode == 0 and result.stdout:
                        for line in result.stdout.split('\n'):
                            if pid in line:
                                parts = line.split()
                                if len(parts) >= 9:
                                    for part in parts:
                                        if '%' in part and part.replace('%', '').replace('.', '').isdigit():
                                            cpu_stats['cpu_usage'] = part
                                            break
                                    else:
                                        if parts[8].replace('.', '').isdigit():
                                            cpu_stats['cpu_usage'] = f"{parts[8]}%"
            
            # MÉTODO 3: Método simplificado con ps
            if 'cpu_usage' not in cpu_stats:
                pid = self._obtener_pid_package(package_name)
                if pid:
                    result = self._ejecutar_adb(f"shell ps -p {pid} -o %cpu")
                    if result and result.returncode == 0 and result.stdout:
                        lines = result.stdout.split('\n')
                        if len(lines) >= 2:
                            cpu_value = lines[1].strip()
                            if cpu_value and cpu_value.replace('.', '').isdigit():
                                cpu_stats['cpu_usage'] = f"{cpu_value}%"
            
            # Si aún no tenemos datos
            if 'cpu_usage' not in cpu_stats:
                cpu_stats['cpu_usage'] = '0% (App puede no estar ejecutándose)'
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo CPU mejorado: {e}")
            cpu_stats['cpu_usage'] = f'Error: {str(e)}'
        
        return cpu_stats

    def _obtener_consumo_datos_mejorado(self, package_name):
        """Obtener consumo de datos de forma MÁS ROBUSTA"""
        datos_stats = {}
        try:
            # Obtener UID del package
            uid = self._obtener_uid_package(package_name)
            
            # MÉTODO 1: Usar dumpsys netstats
            if uid:
                result = self._ejecutar_adb("shell dumpsys netstats detail")
                if result and result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    uid_found = False
                    total_rx = 0
                    total_tx = 0
                    
                    for line in lines:
                        if f"uid={uid}" in line:
                            uid_found = True
                            continue
                        
                        if uid_found:
                            if "rb=" in line and "tb=" in line:
                                rx_match = re.search(r'rb=(\d+)', line)
                                tx_match = re.search(r'tb=(\d+)', line)
                                if rx_match:
                                    total_rx += int(rx_match.group(1))
                                if tx_match:
                                    total_tx += int(tx_match.group(1))
                            elif line.strip() == "":
                                break
                    
                    if total_rx > 0 or total_tx > 0:
                        datos_stats['datos_recibidos'] = self._bytes_a_human(total_rx)
                        datos_stats['datos_enviados'] = self._bytes_a_human(total_tx)
                        datos_stats['datos_total'] = self._bytes_a_human(total_rx + total_tx)
            
            # MÉTODO 2: Usar /proc/net/xt_qtaguid/stats
            if not datos_stats and uid:
                result = self._ejecutar_adb(f"shell cat /proc/net/xt_qtaguid/stats 2>/dev/null")
                if result and result.returncode == 0 and result.stdout:
                    total_rx = 0
                    total_tx = 0
                    for line in result.stdout.split('\n'):
                        if line.strip() and uid in line:
                            parts = line.split()
                            if len(parts) >= 8:
                                try:
                                    total_rx += int(parts[5])
                                    total_tx += int(parts[7])
                                except (ValueError, IndexError):
                                    continue
                    
                    if total_rx > 0 or total_tx > 0:
                        datos_stats['datos_recibidos'] = self._bytes_a_human(total_rx)
                        datos_stats['datos_enviados'] = self._bytes_a_human(total_tx)
                        datos_stats['datos_total'] = self._bytes_a_human(total_rx + total_tx)
            
            # MÉTODO 3: Método simplificado
            if not datos_stats:
                result = self._ejecutar_adb(f"shell dumpsys package {package_name}")
                if result and result.returncode == 0 and result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Data received' in line:
                            match = re.search(r'Data received:\s*([\d.]+)\s*(\w+)', line)
                            if match:
                                datos_stats['datos_recibidos'] = f"{match.group(1)} {match.group(2)}"
                        elif 'Data sent' in line:
                            match = re.search(r'Data sent:\s*([\d.]+)\s*(\w+)', line)
                            if match:
                                datos_stats['datos_enviados'] = f"{match.group(1)} {match.group(2)}"
            
            # Si no se encontraron datos
            if not datos_stats:
                datos_stats['datos_info'] = 'No se detectó actividad de red reciente'
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo datos mejorado: {e}")
            datos_stats['datos_info'] = f'Error al obtener datos: {str(e)}'
        
        return datos_stats

    def _obtener_info_bateria_mejorado(self, package_name):
        """Obtener información de batería más detallada"""
        battery_stats = {}
        try:
            # Método 1: dumpsys batterystats
            result = self._ejecutar_adb(f"shell dumpsys batterystats {package_name}")
            if result and result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                
                wake_locks = 0
                
                for line in lines:
                    line_lower = line.lower()
                    
                    # Wake locks
                    if 'partial wakelock' in line_lower:
                        wake_match = re.search(r'(\d+)\s+times', line)
                        if wake_match:
                            wake_locks = int(wake_match.group(1))
                            break
                
                battery_stats['wake_locks'] = str(wake_locks) if wake_locks > 0 else 'No detectados'
            
            # Método 2: Información general de batería
            result = self._ejecutar_adb("shell dumpsys battery")
            if result and result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if 'level' in line.lower():
                        battery_stats['battery_level'] = line.split(':')[-1].strip()
                    elif 'health' in line.lower():
                        battery_stats['battery_health'] = line.split(':')[-1].strip()
                        
        except Exception as e:
            self.logger.log_error(f"Error obteniendo batería mejorado: {e}")
            battery_stats['wake_locks'] = 'Error al obtener datos'
        
        return battery_stats

    def _bytes_a_human(self, bytes_size):
        """Convertir bytes a formato legible"""
        try:
            if bytes_size == 0:
                return "0 B"
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.2f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.2f} TB"
        except:
            return "N/A"

    def _obtener_estadisticas_app(self, package_name):
        """Obtener estadísticas COMPLETAS de forma más robusta"""
        try:
            stats = {}
            
            # 1. Obtener información básica del package
            package_info = self._obtener_info_package(package_name)
            if package_info:
                stats.update(package_info)
            
            # 2. Obtener uso de memoria
            memoria_info = self._obtener_uso_memoria(package_name)
            if memoria_info:
                stats.update(memoria_info)
            
            # 3. Obtener uso de CPU MEJORADO
            cpu_info = self._obtener_uso_cpu_mejorado(package_name)
            if cpu_info:
                stats.update(cpu_info)
            
            # 4. Obtener consumo de datos MEJORADO
            datos_info = self._obtener_consumo_datos_mejorado(package_name)
            if datos_info:
                stats.update(datos_info)
            
            # 5. Obtener información de batería MEJORADO
            battery_info = self._obtener_info_bateria_mejorado(package_name)
            if battery_info:
                stats.update(battery_info)
            
            return True, stats
            
        except Exception as e:
            self.logger.log_error(f"Error en _obtener_estadisticas_app: {e}")
            return False, f"❌ Error obteniendo estadísticas: {str(e)}"

    def _mostrar_estadisticas_app(self, package_name):
        """Mostrar estadísticas de la aplicación - CON MANEJO MEJORADO DE ERRORES"""
        if not package_name:
            messagebox.showwarning("Advertencia", "Selecciona un package primero")
            return
            
        def obtener_estadisticas():
            try:
                progress_dialog = self._mostrar_dialogo_progreso(self.logcat_window, "Obteniendo estadísticas...")
                
                # Obtener estadísticas
                success_stats, result_stats = self._obtener_estadisticas_app(package_name)
                
                self.root.after(0, lambda: self._procesar_estadisticas(
                    progress_dialog, package_name, success_stats, result_stats))
                    
            except Exception as e:
                self.root.after(0, lambda: self._procesar_error_estadisticas(progress_dialog, str(e)))

        threading.Thread(target=obtener_estadisticas, daemon=True).start()

    def _procesar_estadisticas(self, progress_dialog, package_name, success_stats, result_stats):
        """Procesar y mostrar estadísticas obtenidas - MEJORADO"""
        if progress_dialog and progress_dialog.winfo_exists():
            progress_dialog.destroy()
        
        # Crear diálogo de estadísticas
        dialog = tk.Toplevel(self.logcat_window)
        dialog.title(f"Estadísticas - {package_name}")
        dialog.geometry("800x900")
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

        # Frame con scroll para estadísticas
        stats_container = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        stats_container.pack(fill="both", expand=True, pady=10)

        stats_text = scrolledtext.ScrolledText(
            stats_container,
            wrap="word",
            font=("Consolas", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            height=35,
            padx=15,
            pady=15
        )
        stats_text.pack(fill="both", expand=True)

        if success_stats and isinstance(result_stats, dict):
            # Formatear estadísticas MEJORADO
            self._formatear_estadisticas_en_texto(stats_text, result_stats)
        else:
            # Mostrar error
            self._mostrar_error_estadisticas(stats_text, result_stats)

        stats_text.config(state='disabled')

        # Botones
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=10)

        tk.Button(
            btn_frame,
            text="🔄 Actualizar",
            command=lambda: self._actualizar_estadisticas(dialog, package_name, stats_text),
            font=("Segoe UI", 9),
            bg="#2196f3",
            fg="white",
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))

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

    def _formatear_estadisticas_en_texto(self, stats_text, result_stats):
        """Formatear las estadísticas en el widget de texto"""
        stats_text.insert("1.0", "📈 ESTADÍSTICAS DETALLADAS\n")
        stats_text.insert("2.0", "=" * 55 + "\n\n")
        
        # Información general
        stats_text.insert("end", "📱 INFORMACIÓN GENERAL:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        stats_text.insert("end", f"• UID: {result_stats.get('uid', 'No disponible')}\n")
        if 'version' in result_stats:
            stats_text.insert("end", f"• Versión: {result_stats['version']}\n")
        if 'version_code' in result_stats:
            stats_text.insert("end", f"• Código de versión: {result_stats['version_code']}\n")
        stats_text.insert("end", "\n")
        
        # Memoria
        stats_text.insert("end", "🧠 USO DE MEMORIA:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        stats_text.insert("end", f"• Memoria total (PSS): {result_stats.get('pss_mb', 'N/A')} MB\n")
        stats_text.insert("end", f"• Java Heap: {result_stats.get('java_heap_mb', 'N/A')} MB\n")
        stats_text.insert("end", f"• Native Heap: {result_stats.get('native_heap_mb', 'N/A')} MB\n")
        stats_text.insert("end", "\n")
        
        # CPU
        stats_text.insert("end", "⚡ USO DE CPU:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        stats_text.insert("end", f"• Uso de CPU: {result_stats.get('cpu_usage', 'No disponible')}\n")
        stats_text.insert("end", "\n")
        
        # Datos de red
        stats_text.insert("end", "📡 CONSUMO DE DATOS:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        
        if 'datos_recibidos' in result_stats:
            stats_text.insert("end", f"• 📥 Datos recibidos: {result_stats['datos_recibidos']}\n")
        if 'datos_enviados' in result_stats:
            stats_text.insert("end", f"• 📤 Datos enviados: {result_stats['datos_enviados']}\n")
        if 'datos_total' in result_stats:
            stats_text.insert("end", f"• 📊 Total transferido: {result_stats['datos_total']}\n")
        
        if not any(key in result_stats for key in ['datos_recibidos', 'datos_enviados', 'datos_total']):
            stats_text.insert("end", f"• {result_stats.get('datos_info', 'No se detectó actividad de red')}\n")
        
        stats_text.insert("end", "\n")
        
        # Batería
        stats_text.insert("end", "🔋 CONSUMO DE BATERÍA:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        stats_text.insert("end", f"• Wake locks: {result_stats.get('wake_locks', 'No disponible')}\n")
        stats_text.insert("end", "\n")
        
        # Información adicional
        stats_text.insert("end", "💡 INFORMACIÓN ADICIONAL:\n")
        stats_text.insert("end", "-" * 35 + "\n")
        stats_text.insert("end", "• Los datos se obtienen del sistema Android en tiempo real\n")
        stats_text.insert("end", "• Para datos más precisos, ejecuta la aplicación\n")

    def _mostrar_error_estadisticas(self, stats_text, result_stats):
        """Mostrar mensaje de error en las estadísticas"""
        stats_text.insert("1.0", "❌ ERROR AL OBTENER ESTADÍSTICAS\n")
        stats_text.insert("end", "=" * 45 + "\n\n")
        
        if isinstance(result_stats, str):
            stats_text.insert("end", f"Error: {result_stats}\n\n")
        
        stats_text.insert("end", "🔧 POSIBLES SOLUCIONES:\n")
        stats_text.insert("end", "-" * 25 + "\n")
        stats_text.insert("end", "• Verifica que el dispositivo esté conectado\n")
        stats_text.insert("end", "• Asegúrate de que la aplicación esté instalada\n")
        stats_text.insert("end", "• Intenta reiniciar el servidor ADB\n")

    def _actualizar_estadisticas(self, dialog, package_name, stats_text):
        """Actualizar las estadísticas en tiempo real"""
        def actualizar():
            success_stats, result_stats = self._obtener_estadisticas_app(package_name)
            self.root.after(0, lambda: self._refrescar_estadisticas(dialog, stats_text, success_stats, result_stats))
        
        threading.Thread(target=actualizar, daemon=True).start()

    def _refrescar_estadisticas(self, dialog, stats_text, success_stats, result_stats):
        """Refrescar el contenido de las estadísticas"""
        stats_text.config(state='normal')
        stats_text.delete(1.0, tk.END)
        
        if success_stats and isinstance(result_stats, dict):
            self._formatear_estadisticas_en_texto(stats_text, result_stats)
        else:
            self._mostrar_error_estadisticas(stats_text, result_stats)
        
        stats_text.config(state='disabled')

    def _procesar_error_estadisticas(self, progress_dialog, error):
        """Procesar error al obtener estadísticas"""
        if progress_dialog and progress_dialog.winfo_exists():
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