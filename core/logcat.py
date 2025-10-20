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
        self.is_fullscreen = False
        self.current_screen = 0

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
        """Ejecutar comando ADB de forma segura"""
        try:
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
                    errors='ignore'
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
                    errors='ignore'
                )
            
            return result
            
        except subprocess.TimeoutExpired:
            self.logger.log_warning(f"Timeout ejecutando ADB: {comando}")
            return None
        except Exception as e:
            self.logger.log_error(f"Error ejecutando ADB: {comando}", e)
            return None

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
        self.logcat_window.title("Logcat")
        
        # Configuración de ventana mejorada
        self.logcat_window.geometry("1400x850")
        self.logcat_window.minsize(1200, 700)
        
        # Detectar pantalla actual
        self._detectar_pantalla_actual()
        
        self.logcat_window.configure(bg=self.styles.COLORS['primary_bg'])
        self._posicionar_ventana_inteligente()
        self.logcat_window.bind("<F11>", self._toggle_pantalla_completa)
        self.logcat_window.bind("<Escape>", self._salir_pantalla_completa)
        self.logcat_window.bind("<Control-s>", lambda e: self._guardar_log())
        self.logcat_window.bind("<Control-l>", lambda e: self._limpiar_logcat())
        self.logcat_window.bind("<Control-f>", lambda e: self.package_combo.focus())
        
        self._crear_ui_logcat_mejorada()
        self._verificar_dispositivo()

    def _detectar_pantalla_actual(self):
        """Detectar en qué pantalla está la ventana principal"""
        try:
            # Obtener información de la pantalla principal
            main_x = self.root.winfo_x()
            main_width = self.root.winfo_screenwidth()
            
            # Si la ventana principal está en la segunda mitad de la pantalla principal,
            # asumimos que está en pantalla secundaria
            if main_x > main_width // 2:
                self.current_screen = 1  # Pantalla secundaria
            else:
                self.current_screen = 0  # Pantalla principal
                
        except Exception as e:
            self.logger.log_warning(f"Error detectando pantalla: {e}")
            self.current_screen = 0

    def _posicionar_ventana_inteligente(self):
        """Posicionar ventana de forma inteligente según la pantalla"""
        try:
            if self.current_screen == 1:  # Pantalla secundaria
                # Usar toda la pantalla secundaria
                screen_width = self.logcat_window.winfo_screenwidth()
                screen_height = self.logcat_window.winfo_screenheight()
                self.logcat_window.geometry(f"{screen_width}x{screen_height-50}+0+0")
            else:
                # Posicionar junto a la ventana principal en pantalla principal
                main_x = self.root.winfo_x()
                main_y = self.root.winfo_y()
                main_width = self.root.winfo_width()
                
                logcat_x = main_x + main_width + 10
                logcat_y = main_y
                
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                
                logcat_width = screen_width - main_width - 50
                if logcat_width < 1000:
                    logcat_width = 1000
                    
                self.logcat_window.geometry(f"{logcat_width}x{screen_height-100}+{logcat_x}+{logcat_y}")
            
        except Exception as e:
            self.logger.log_warning(f"No se pudo posicionar ventana inteligente: {e}")
            self.logcat_window.geometry("1400x850")

    def _toggle_pantalla_completa(self, event=None):
        """Alternar modo pantalla completa - MEJORADO para múltiples pantallas"""
        self.is_fullscreen = not self.is_fullscreen
        self.logcat_window.attributes("-fullscreen", self.is_fullscreen)
        
        if self.is_fullscreen:
            self.btn_pantalla_completa.config(
                text="⛶ Salir Pantalla Completa",
                bg="#ff5722",
                fg="white"
            )
            # Asegurarse de que está en la pantalla correcta
            if self.current_screen == 1:
                self.logcat_window.geometry(f"{self.logcat_window.winfo_screenwidth()}x{self.logcat_window.winfo_screenheight()}+0+0")
        else:
            self.btn_pantalla_completa.config(
                text="⛶ Pantalla Completa", 
                bg="#9c27b0",
                fg="white"
            )
            self._posicionar_ventana_inteligente()

    def _salir_pantalla_completa(self, event=None):
        """Salir del modo pantalla completa"""
        if self.is_fullscreen:
            self._toggle_pantalla_completa()

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

        # Panel de control principal - DISEÑO MEJORADO
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

        self.package_var = tk.StringVar()
        self.package_combo = ttk.Combobox(
            combo_frame,
            textvariable=self.package_var,
            font=("Segoe UI", 10),
            height=8,  # Altura del dropdown
            values=self.all_packages
        )
        self.package_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # ✅ AUTOMATIZACIÓN MEJORADA - Sin bloqueos de escritura
        self.package_combo.bind('<KeyRelease>', self._autocompletar_package_mejorado)
        self.package_combo.bind('<<ComboboxSelected>>', self._on_package_selected)
        self.package_combo.bind('<Return>', lambda e: self._aplicar_filtro_package())
        self.package_combo.bind('<FocusIn>', lambda e: self.package_combo.selection_range(0, tk.END))

        # Botones de acción para packages
        btn_package_frame = tk.Frame(combo_frame, bg=self.styles.COLORS['secondary_bg'])
        btn_package_frame.pack(side="left", padx=(5, 0))

        self.btn_cargar_packages = self._crear_boton_moderno(
            btn_package_frame,
            "📦 Cargar Packages",
            self._cargar_packages_dispositivo,
            "#2196f3"
        )
        self.btn_cargar_packages.pack(side="left", padx=(0, 5))

        self.btn_aplicar_filtro = self._crear_boton_moderno(
            btn_package_frame,
            "🎯 Aplicar Filtro",
            self._aplicar_filtro_package,
            "#17a2b8"
        )
        self.btn_aplicar_filtro.pack(side="left", padx=(0, 5))

        self.btn_limpiar_filtro = self._crear_boton_moderno(
            btn_package_frame,
            "🗑️ Limpiar",
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

        # Grupo derecho: Utilidades (con pantalla completa a la derecha)
        right_btn_frame = tk.Frame(control_btn_frame, bg=self.styles.COLORS['secondary_bg'])
        right_btn_frame.pack(side="right")

        self.btn_guardar = self._crear_boton_moderno(
            right_btn_frame,
            "💾 Guardar Log",
            self._guardar_log,
            "#17a2b8"
        )
        self.btn_guardar.pack(side="left", padx=(0, 8))

        # ✅ PANTALLA COMPLETA A LA DERECHA DEL TODO
        self.btn_pantalla_completa = self._crear_boton_moderno(
            right_btn_frame,
            "⛶ Pantalla Completa",
            self._toggle_pantalla_completa,
            "#9c27b0"
        )
        self.btn_pantalla_completa.pack(side="left")

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
            text="⌨️ F11: Pantalla Completa | Ctrl+S: Guardar | Ctrl+L: Limpiar",
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
        """Autocompletado MEJORADO - Sin bloquear la escritura"""
        # Ignorar teclas de navegación y control
        if event.keysym in ['Return', 'Escape', 'Up', 'Down', 'Control_L', 'Control_R']:
            return
        
        current_text = self.package_var.get()
        
        if not current_text:
            self.package_combo['values'] = self.all_packages[:50]  # Mostrar solo primeros 50
            return
        
        # ✅ MEJORADO: Búsqueda inteligente sin bloquear escritura
        filtered = []
        current_lower = current_text.lower()
        
        # Priorizar coincidencias que empiecen con el texto
        starts_with = [pkg for pkg in self.all_packages if pkg.lower().startswith(current_lower)]
        
        # Luego coincidencias que contengan el texto
        contains = [pkg for pkg in self.all_packages if current_lower in pkg.lower() and pkg not in starts_with]
        
        filtered = starts_with + contains
        
        # Limitar a 30 resultados para mejor rendimiento
        filtered = filtered[:30]
        
        # Actualizar valores del combobox SIN interferir con la escritura
        self.package_combo['values'] = filtered
        
        # Solo mostrar dropdown si hay coincidencias y el usuario está escribiendo
        if filtered and len(current_text) > 1:
            # Pequeño delay para no ser intrusivo
            self.logcat_window.after(100, lambda: self.package_combo.event_generate('<Down>'))

    def _mostrar_info_adb(self, event=None):
        """Mostrar información sobre ADB"""
        messagebox.showinfo(
            "Información ADB",
            f"Ruta ADB actual: {self.adb_path}\n\n"
            "Atajos de teclado:\n"
            "• F11: Pantalla completa\n"
            "• ESC: Salir pantalla completa\n"
            "• Ctrl+S: Guardar log\n"
            "• Ctrl+L: Limpiar pantalla\n"
            "• Ctrl+F: Enfocar búsqueda\n\n"
            "Si ADB no funciona:\n"
            "1. Ve a 'Configurar Herramientas'\n"
            "2. Establece la ruta correcta a adb.exe"
        )

    def _verificar_dispositivo(self):
        """Verificar si hay dispositivos conectados"""
        def verificar():
            result = self._ejecutar_adb("devices")
            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = []
                for line in lines[1:]:
                    if line.strip() and '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        devices.append({'device': device_id, 'model': 'Dispositivo Android'})
                
                self.root.after(0, self._actualizar_estado_dispositivo, devices)
            else:
                error_msg = "No se pudo ejecutar ADB. Verifica la configuración."
                if result and result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                self.root.after(0, self._mostrar_error_estado, error_msg)

        threading.Thread(target=verificar, daemon=True).start()

    def _actualizar_estado_dispositivo(self, devices):
        """Actualizar estado del dispositivo en la UI"""
        if devices:
            device_info = devices[0]
            self.status_label.config(
                text=f"✅ Dispositivo conectado: {device_info['device']}",
                fg="#4caf50"
            )
            self.monitoring_status.config(text="🟢 Monitoreo: LISTO", fg="#4caf50")
        else:
            self.status_label.config(
                text="❌ No hay dispositivos Android conectados",
                fg="#f44336"
            )
            self.monitoring_status.config(text="🔴 Monitoreo: SIN DISPOSITIVO", fg="#f44336")

    def _mostrar_error_estado(self, error_msg):
        """Mostrar error en el estado"""
        self.status_label.config(text=f"❌ {error_msg}", fg="#f44336")
        self.monitoring_status.config(text="🔴 Monitoreo: ERROR ADB", fg="#f44336")

    def _cargar_packages_dispositivo(self):
        """Cargar todos los packages instalados en el dispositivo"""
        def cargar_packages():
            self.root.after(0, lambda: self.status_label.config(
                text="📦 Cargando packages del dispositivo...", 
                fg="#ff9800"
            ))
            
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
                error_msg = "No se pudieron cargar los packages"
                if result and result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                self.root.after(0, self._mostrar_error_estado, error_msg)

        threading.Thread(target=cargar_packages, daemon=True).start()

    def _actualizar_packages_ui(self, packages):
        """Actualizar la UI con la lista de packages"""
        self.package_combo['values'] = packages[:50]  # Mostrar primeros 50 por defecto
        self.status_label.config(
            text=f"✅ {len(packages)} packages cargados - Escribe para buscar",
            fg="#4caf50"
        )
        
        # Detectar package del APK automáticamente
        self._detectar_package_apk_inteligente()

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
                    
                    # Obtener PID
                    pid = self._obtener_pid_package(package_name)
                    status_text = f"✅ Package detectado: {package_name}"
                    
                    if pid:
                        status_text += f" (PID: {pid}) - Listo para iniciar Logcat"
                        self.pid_info_label.config(text=f"📊 PID: {pid}")
                    else:
                        status_text += " - App no está ejecutándose"
                        self.pid_info_label.config(text="📊 PID: No ejecutándose")
                    
                    self.status_label.config(text=status_text, fg="#4caf50")
                    
                else:
                    self.status_label.config(
                        text=f"⚠️ Package '{package_name}' no encontrado en el dispositivo",
                        fg="#ff9800"
                    )
                    self.pid_info_label.config(text="📊 PID: No instalado")
            else:
                self.status_label.config(
                    text="ℹ️ No hay APK analizado o no se detectó package. Usa autocompletado ↑",
                    fg="#17a2b8"
                )
            
        except Exception as e:
            self.logger.log_error("Error detectando package automático", e)
            self.status_label.config(
                text="❌ Error detectando package. Usa búsqueda manual ↑",
                fg="#f44336"
            )

    def _on_package_selected(self, event):
        """Cuando se selecciona un package del combobox"""
        package = self.package_var.get()
        if package:
            self.current_filter = package
            self.filter_info_label.config(text=f"🎯 Filtro: {package}")
            
            # Obtener PID del package seleccionado
            pid = self._obtener_pid_package(package)
            if pid:
                self.pid_info_label.config(text=f"📊 PID: {pid}")
                self.status_label.config(
                    text=f"✅ Filtro aplicado: {package} (PID: {pid})",
                    fg="#4caf50"
                )
            else:
                self.pid_info_label.config(text="📊 PID: No ejecutándose")
                self.status_label.config(
                    text=f"⚠️ Filtro aplicado: {package} - App no ejecutándose",
                    fg="#ff9800"
                )

    def _aplicar_filtro_package(self):
        """Aplicar filtro por package"""
        package = self.package_var.get().strip()
        if not package:
            messagebox.showwarning("Advertencia", "Por favor, ingresa un package name")
            return
        
        self.current_filter = package
        self.filter_info_label.config(text=f"🎯 Filtro: {package}")
        
        # Obtener PID
        pid = self._obtener_pid_package(package)
        if pid:
            self.pid_info_label.config(text=f"📊 PID: {pid}")
            self.status_label.config(
                text=f"✅ Filtro aplicado: {package} (PID: {pid})",
                fg="#4caf50"
            )
        else:
            self.pid_info_label.config(text="📊 PID: No ejecutándose")
            self.status_label.config(
                text=f"⚠️ Filtro aplicado: {package} - App no ejecutándose",
                fg="#ff9800"
            )

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
        """Guardar log actual en archivo"""
        try:
            contenido = self.logcat_text.get('1.0', 'end-1c')
            if not contenido.strip():
                messagebox.showwarning("Advertencia", "No hay logs para guardar")
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logcat_{timestamp}.txt"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                initialfile=filename
            )
            
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                
                messagebox.showinfo("Éxito", f"Log guardado en:\n{filepath}")
                self.status_label.config(
                    text=f"💾 Log guardado: {Path(filepath).name}",
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