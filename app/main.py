import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

try:
    from app_services import AppServices
    from app_initializer import AppInitializer
    from apk_manager import APKManager
    from utils.APKParser import APKParser  
except ImportError as e:
    try:
        from app.app_services import AppServices
        from app.app_initializer import AppInitializer
        from app.apk_manager import APKManager
        from utils.APKParser import APKParser  
    except ImportError:
        print("No se pudieron cargar los módulos necesarios")
        sys.exit(1)


class APKInspectorApp:
    def __init__(self, root, loading_screen=None):
        self.root = root
        self.loading_screen = loading_screen
        self.initializer = AppInitializer(root, loading_screen)
        self.initializer.initialize_with_loading()
        self._wait_for_initialization()

    def _wait_for_initialization(self):
        if self.initializer.loading_complete:
            self._setup_application()
        else:
            self.root.after(100, self._wait_for_initialization)

    def _setup_application(self):
        try:
            self.components = self.initializer.get_all_components()
            
            # ✅ VERIFICAR QUE EL ANALYZER ESTÉ CORRECTO
            if 'apk_analyzer' not in self.components or self.components['apk_analyzer'] is None:
                print("❌ APK Analyzer no encontrado en componentes, creando uno...")
                from core.apk_analyzer import APKAnalyzer
                self.components['apk_analyzer'] = APKAnalyzer(
                    self.components['tool_detector'], 
                    self.components['logger']
                )
            
            # ✅ VERIFICAR MÉTODOS DISPONIBLES
            analyzer = self.components['apk_analyzer']
            print(f"🔍 APK Analyzer tipo: {type(analyzer)}")
            print(f"🔍 Tiene analizar_apk_completo: {hasattr(analyzer, 'analizar_apk_completo')}")
            print(f"🔍 Tiene parsear_informacion_apk: {hasattr(analyzer, 'parsear_informacion_apk')}")
            
            self.services = AppServices(self.components)
            self.styles = self.components['styles']
            self.logger = self.components['logger']
            self.format_utils = self.components['format_utils']
            self.config_manager = self.components['config_manager']
            self.tool_detector = self.components['tool_detector']
            self.file_utils = self.components['file_utils']
            self.adb_manager = self.components['adb_manager']
            self.apk_analyzer = self.components['apk_analyzer']
            self.apk_path = self.components['apk_path']
            self.apk_name = self.components['apk_name']
            self.current_log = self.components['current_log']
            self.current_analysis = self.components['current_analysis']
            self.botones_apk = self.components['apk_buttons']
            self.apk_manager = APKManager(
                self.services, 
                self.styles, 
                self.logger, 
                self.adb_manager
            )

            # Verificar que el analyzer tenga los métodos necesarios
            if not hasattr(self.apk_analyzer, 'analizar_apk_completo'):
                self.logger.log_error("APKAnalyzer no tiene método analizar_apk_completo")
                # Crear un analyzer de respaldo
                from core.apk_analyzer import APKAnalyzer
                self.apk_analyzer = APKAnalyzer(self.tool_detector, self.logger)
                self.components['apk_analyzer'] = self.apk_analyzer

            # NUEVO: Inicializar LogcatManager con config_manager
            try:
                from core.logcat import LogcatManager
                self.logcat_manager = LogcatManager(
                    self.root,
                    self.adb_manager,
                    self.styles,
                    self.logger,
                    self.apk_analyzer,
                    self.config_manager  
                )
                self.logcat_manager.set_components(self.components)
            except ImportError as e:
                self.logger.log_warning("No se pudo cargar LogcatManager", e)
                self.logcat_manager = None

            self.setup_ui()
            self.mostrar_estado_inicial()
            self.actualizar_estado_botones()

            self.logger.log_info("Aplicación iniciada correctamente")

            if self.loading_screen:
                self.loading_screen.cerrar()

        except Exception as e:
            self._manejar_error_inicializacion(e)
            
    def _manejar_error_inicializacion(self, error):
        if self.loading_screen:
            self.loading_screen.cerrar()
        messagebox.showerror(
            "Error de Inicialización",
            f"No se pudo iniciar la aplicación:\n\n{str(error)}"
        )
        self.root.quit()

    def get_resource_path(self, relative_path):
        try:
            base_path = getattr(sys, '_MEIPASS', Path(__file__).parent.parent)
            return Path(base_path) / relative_path
        except Exception:
            return Path(relative_path)

    def setup_ui(self):
        from utils.version import get_version_string
        self.root.title(get_version_string())
        self.root.geometry("950x650")
        self.root.minsize(900, 550)
        self.root.configure(bg=self.styles.COLORS['primary_bg'])

        self.establecer_icono_ventana()
        self.crear_header()
        self.crear_botones_principales()
        self.crear_area_resumen()

    def establecer_icono_ventana(self):
        try:
            icono_rutas = [
                "assets/logoAPP.png",
                "assets/logoAPP.ico",
                "assets/icon.png",
                "assets/icon.ico",
            ]

            icono_encontrado = None
            for ruta_relativa in icono_rutas:
                ruta_absoluta = self.get_resource_path(ruta_relativa)
                if ruta_absoluta.exists():
                    icono_encontrado = ruta_absoluta
                    break

            if icono_encontrado:
                if str(icono_encontrado).lower().endswith('.ico'):
                    self.root.iconbitmap(str(icono_encontrado))
                else:
                    from PIL import Image, ImageTk
                    image = Image.open(str(icono_encontrado))
                    if image.mode != 'RGBA':
                        image = image.convert('RGBA')
                    photo = ImageTk.PhotoImage(image)
                    self.root.iconphoto(True, photo)
                    self.icono_ventana = photo

        except Exception as e:
            self.logger.log_error("Error estableciendo icono", e)

    def crear_header(self):
        from utils.version import get_short_version
        from ui.components import BotonRedondeado

        header_frame = tk.Frame(self.root, bg=self.styles.COLORS['primary_bg'])
        header_frame.pack(fill="x", padx=15, pady=10)

        self.logo_img = None
        try:
            from PIL import Image, ImageTk
            logo_rutas = ["assets/logo.png", "assets/logoAPP.png"]
            logo_encontrado = None
            for ruta_relativa in logo_rutas:
                ruta_absoluta = self.get_resource_path(ruta_relativa)
                if ruta_absoluta.exists():
                    logo_encontrado = ruta_absoluta
                    break

            if logo_encontrado:
                original_image = Image.open(str(logo_encontrado))
                resized_image = original_image.resize((120, 35), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(resized_image)
                logo_label = tk.Label(header_frame, image=self.logo_img, bg=self.styles.COLORS['primary_bg'])
                logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))
        except Exception:
            logo_label = tk.Label(header_frame, text="APK Inspector", font=("Segoe UI", 10, "bold"),
                                  bg=self.styles.COLORS['primary_bg'], fg=self.styles.COLORS['accent'])
            logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))

        title_frame = tk.Frame(header_frame, bg=self.styles.COLORS['primary_bg'])
        title_frame.grid(row=0, column=1, sticky="w")

        app_name = self.initializer.get_component('app_name')
        version = self.initializer.get_component('version')

        title_label = tk.Label(
            title_frame,
            text=f"{app_name} {get_short_version()}",
            font=("Segoe UI", 12, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        )
        title_label.pack(anchor="w")

        self.btn_config = BotonRedondeado(
            header_frame,
            "Configurar Herramientas",
            self.abrir_config_herramientas,
            width=180,
            height=32,
            style='secondary',
            tooltip_text="Configurar rutas de herramientas Android"
        )
        self.btn_config.grid(row=1, column=1, sticky="w", pady=(3, 0))

        version_text = f"Version {version}"
        self.version_label = tk.Label(
            header_frame,
            text=version_text,
            font=("Segoe UI", 9),
            fg=self.styles.COLORS['text_primary'],
            cursor="hand2"
        )
        self.version_label.grid(row=0, column=2, sticky="e", rowspan=2)

        self.version_label.bind("<Button-1>", lambda e: self.mostrar_acerca_de())
        self.version_label.bind("<Enter>", self._on_version_enter)
        self.version_label.bind("<Leave>", self._on_version_leave)

        header_frame.columnconfigure(1, weight=1)

    def _on_version_enter(self, event):
        self.version_label.config(fg=self.styles.COLORS['accent'])

    def _on_version_leave(self, event):
        self.version_label.config(fg=self.styles.COLORS['text_primary'])

    def abrir_config_herramientas(self):
        from ui.dialogs import ToolsDialog
        dialog = ToolsDialog(self.root, self.config_manager, self.tool_detector)
        resultado = dialog.mostrar()

        if resultado:
            if self.config_manager.guardar_config(resultado):
                messagebox.showinfo("Configuración", "Configuración guardada correctamente")
                self.tool_detector.limpiar_cache()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración")

    def crear_botones_principales(self):
        from ui.components import BotonRedondeado

        button_frame = tk.Frame(self.root, bg=self.styles.COLORS['primary_bg'])
        button_frame.pack(fill="x", padx=15, pady=10)

        left_btn_frame = tk.Frame(button_frame, bg=self.styles.COLORS['primary_bg'])
        left_btn_frame.pack(side="left")

        right_btn_frame = tk.Frame(button_frame, bg=self.styles.COLORS['primary_bg'])
        right_btn_frame.pack(side="right")

        # Botones principales (izquierda)
        BotonRedondeado(
            left_btn_frame,
            "📁 Seleccionar APK",
            self.seleccionar_apk,
            tooltip_text="Seleccionar archivo APK para analizar",
            width=140,
            height=40,
            style='APK',
        ).pack(side="left", padx=3)

        self.btn_ver_log = BotonRedondeado(
            left_btn_frame,
            "📊 Comandos",
            self.mostrar_log_completo,
            tooltip_text="Ver Comandos detallados del análisis",
            width=120,
            height=40,
            style='primary'
        )
        self.btn_ver_log.pack(side="left", padx=3)
        self.botones_apk.append(self.btn_ver_log)

        self.btn_gestionar = BotonRedondeado(
            left_btn_frame,
            "📱 Gestionar APK",
            self.mostrar_opciones_gestion,
            width=130,
            height=40,
            style='primary'
        )
        self.btn_gestionar.pack(side="left", padx=3)
        self.botones_apk.append(self.btn_gestionar)

        # NUEVO: Botón Logcat
        self.btn_logcat = BotonRedondeado(
            right_btn_frame,
            "🐱 Logcat",
            self.mostrar_logcat,
            tooltip_text="Monitor de logs de dispositivos Android",
            width=100,
            height=40,
            style='logcat'
        )
        self.btn_logcat.pack(side="left", padx=3)

        # Botones de la derecha - SOLO LIMPIAR Y GESTIONAR FIRMA
        self.btn_limpiar = BotonRedondeado(
            right_btn_frame,
            "🔄 Limpiar",
            self.limpiar_todo,
            width=100,
            height=40,
            style='danger'
        )
        self.btn_limpiar.pack(side="right", padx=3)
        self.botones_apk.append(self.btn_limpiar)

        # NUEVO: Botón unificado de Gestionar Firma con submenú
        self.btn_gestionar_firma = BotonRedondeado(
            right_btn_frame,
            "🔐 Gestionar Firma",
            self.mostrar_opciones_firma,
            width=130,
            height=40,
            style='sign'
        )
        self.btn_gestionar_firma.pack(side="right", padx=3)

    def mostrar_opciones_firma(self):
        """Mostrar menú de opciones de firma"""
        menu_firma = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        
        menu_firma.add_command(
            label="🔑 Crear Nueva Firma",
            command=self.crear_nueva_firma
        )
        
        menu_firma.add_command(
            label="📝 Firmar APK",
            command=self.firmar_apk
        )
        
        menu_firma.add_separator()
        
        menu_firma.add_command(
            label="ℹ️  Ayuda sobre Firma",
            command=self.mostrar_ayuda_firma
        )
        
        # Mostrar menú en la posición del botón
        try:
            x = self.btn_gestionar_firma.winfo_rootx()
            y = self.btn_gestionar_firma.winfo_rooty() + self.btn_gestionar_firma.winfo_height()
            menu_firma.post(x, y)
        except Exception as e:
            self.logger.log_error("Error mostrando menú firma", e)
            # Fallback: mostrar en centro
            menu_firma.post(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def mostrar_ayuda_firma(self):
        """Mostrar información de ayuda sobre firma"""
        ayuda_texto = """
    🔐 **GESTIÓN DE FIRMAS DIGITALES**

    **Crear Firma:**
    - Genera un nuevo certificado JKS (Java Keystore)
    - Necesario para firmar APKs para distribución
    - Guarda la contraseña de forma segura

    **Firmar APK:**
    - Firma un APK con un certificado existente
    - Requiere un archivo JKS y su contraseña
    - Genera APK

    **Nota:** La firma es necesaria para publicar en store de aplicaciones.
    """
        messagebox.showinfo("Ayuda - Gestión de Firmas", ayuda_texto)

    def mostrar_logcat(self):
        """Mostrar ventana de Logcat"""
        try:
            # Importar y crear instancia de LogcatManager
            from core.logcat import LogcatManager
            
            logcat_manager = LogcatManager(
                self.root,
                self.adb_manager,
                self.styles,
                self.logger
            )
            logcat_manager.mostrar_logcat()
            
        except Exception as e:
            self.logger.log_error("Error abriendo Logcat", e)
            messagebox.showerror(
                "Error", 
                f"No se pudo abrir el monitor Logcat:\n{str(e)}"
            )

    def crear_area_resumen(self):
        main_frame = tk.Frame(self.root, bg=self.styles.COLORS['primary_bg'])
        main_frame.pack(fill="both", expand=True, padx=15, pady=5)

        title_label = tk.Label(
            main_frame,
            text="Resumen del Análisis",
            font=("Segoe UI", 10, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        )
        title_label.pack(anchor="w", pady=(0, 8))

        text_frame = tk.Frame(main_frame, relief="solid", bd=1)
        text_frame.pack(fill="both", expand=True)

        self.summary_text = scrolledtext.ScrolledText(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=8,
            pady=8,
            state='disabled'
        )
        self.summary_text.pack(fill="both", expand=True)

    def actualizar_estado_botones(self):
        tiene_apk = self.apk_path is not None
        for boton in self.botones_apk:
            if tiene_apk:
                boton.habilitar()
            else:
                boton.deshabilitar()

    def mostrar_estado_inicial(self):
        self.actualizar_texto_resumen(self._generar_estado_inicial())

    def _generar_estado_inicial(self):
        from utils.version import get_version_string

        estado_herramientas = self.tool_detector.verificar_herramientas_instaladas()

        contenido = f"=== {self.initializer.get_component('app_name').upper()} ===\n"
        contenido += f"{get_version_string()}\n\n"

        contenido += self.format_utils.crear_mensaje_estado_herramientas(estado_herramientas)

        contenido += "\n=== INSTRUCCIONES ===\n"
        contenido += "1. Selecciona un archivo APK para analizar\n"
        contenido += "2. Revisa la información técnica y de seguridad\n"
        contenido += "3. Instala en dispositivos conectados (opcional)\n"
        contenido += "4. Exporta logs para análisis detallado\n\n"

        contenido += "💡 Configura las herramientas Android si no se detectan automáticamente\n"

        return contenido

    def actualizar_texto_resumen(self, contenido):
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, contenido)
        self.summary_text.config(state='disabled')

    def seleccionar_apk(self):
        from tkinter import filedialog

        apk_path = filedialog.askopenfilename(
            title="Seleccionar archivo APK",
            filetypes=[("APK files", "*.apk")]
        )

        if not apk_path:
            return

        if not self.file_utils.es_archivo_apk_valido(apk_path):
            messagebox.showerror("Error", "El archivo seleccionado no es un APK válido")
            return

        self.actualizar_texto_resumen(f"Analizando: {Path(apk_path).name}\n\nPor favor espera...")
        self.root.update()
        self.actualizar_estado_botones()

        self.root.after(100, lambda: self._ejecutar_analisis(apk_path))

    def _ejecutar_analisis(self, apk_path):
        print(f"🔍 INICIANDO ANÁLISIS: {apk_path}")
        
        # ✅ VERIFICAR QUE EL APK ANALYZER ESTÉ CONFIGURADO CORRECTAMENTE
        if not hasattr(self.apk_analyzer, 'analizar_apk_completo'):
            print("❌ ERROR: APK Analyzer no tiene el método analizar_apk_completo")
            messagebox.showerror("Error", "El analizador de APK no está configurado correctamente")
            return
            
        success, message = self.services.analyze_apk(apk_path)

        if success:
            # ✅ DEBUG: Mostrar información parseada
            current_analysis = self.components['current_analysis']
            parsed_info = current_analysis['parsed_info']
            print(f"✅ ANÁLISIS COMPLETADO:")
            print(f"   Package: {parsed_info.get('package')}")
            print(f"   App: {parsed_info.get('app_name')}")
            print(f"   Versión: {parsed_info.get('version_name')}")
            print(f"   Target SDK: {parsed_info.get('target_sdk')}")
            print(f"   Método: {parsed_info.get('metodo_analisis')}")

        if success:
            self.apk_path = self.components['apk_path']
            self.apk_name = self.components['apk_name']
            self.current_analysis = self.components['current_analysis']
            self.current_log = self.components['current_log']

            self.actualizar_estado_botones()

            parsed_info = self.current_analysis['parsed_info']
            signature_info = self.current_analysis['signature_info']
            apk_size_mb = self.format_utils.get_apk_size_mb(Path(apk_path))
            pci_analysis = self.current_analysis.get('pci_analysis')

            resumen = self.format_utils.formatear_resumen_apk(
                parsed_info, signature_info, self.apk_name, apk_size_mb, pci_analysis
            )

            self.actualizar_texto_resumen(resumen)
            self.logger.log_info(f"Análisis completado: {self.apk_name}")

        else:
            self.actualizar_texto_resumen(f"❌ {message}")
            messagebox.showerror("Error", message)
            self.actualizar_estado_botones()

    def mostrar_log_completo(self):
        if not self.current_log:
            messagebox.showinfo("Información", "No hay Comandos para mostrar. Analiza un APK primero.")
            return

        from ui.dialogs import LogDialog
        log_dialog = LogDialog(self.root, self.current_log, self.current_analysis)
        log_dialog.mostrar()

    def mostrar_opciones_gestion(self):
        if not self.apk_path:
            messagebox.showerror("Error", "No hay APK seleccionado para gestionar")
            return
            
        self.apk_manager.mostrar_opciones_gestion(
            self.root, 
            self.apk_path, 
            self.apk_name, 
            self.current_analysis
        )

    def crear_nueva_firma(self):
        """Crear un nuevo certificado de firma JKS usando el diálogo"""
        try:
            from ui.dialogFirmaCreate import FirmaCreateDialog
            
            # Crear y mostrar el diálogo - SIN usar SimpleInputDialog
            firma_dialog = FirmaCreateDialog(
                self.root,
                styles=self.styles,
                logger=self.logger,
                config_manager=self.config_manager
            )
            
            self.logger.log_info("Diálogo de creación de firma abierto")
            
        except Exception as e:
            self.logger.log_error("Error abriendo diálogo de firma", e)
            messagebox.showerror(
                "Error", 
                f"Error al abrir el diálogo de creación de firma:\n{str(e)}"
            )
            
            """Crear un nuevo certificado de firma JKS"""
            try:
                from tkinter import filedialog
                from ui.dialogs import SimpleInputDialog
                
                # Dialogo para seleccionar donde guardar el keystore
                archivo_destino = filedialog.asksaveasfilename(
                    title="Guardar nuevo keystore como...",
                    defaultextension=".jks",
                    filetypes=[("Java Keystore", "*.jks"), ("Todos los archivos", "*.*")],
                    initialfile="my-release-key.jks"
                )
                
                if not archivo_destino:
                    return  # Usuario canceló
                
                destino = Path(archivo_destino)
                
                # Dialogo para contraseña
                dialog_pass = SimpleInputDialog(
                    self.root,
                    "Contraseña del Keystore",
                    "Ingresa la contraseña para el nuevo keystore:",
                    masked=True
                )
                password = dialog_pass.mostrar()
                
                if not password:
                    return  # Usuario canceló
                
                # Dialogo para alias
                dialog_alias = SimpleInputDialog(
                    self.root,
                    "Alias del Certificado", 
                    "Ingresa el alias para el certificado:",
                    initial_value="my-key-alias"
                )
                alias = dialog_alias.mostrar()
                
                if not alias:
                    return  # Usuario canceló
                
                # Dialogo para validez
                dialog_days = SimpleInputDialog(
                    self.root,
                    "Validez del Certificado",
                    "Ingresa los días de validez del certificado:",
                    initial_value="365"
                )
                days_str = dialog_days.mostrar()
                
                if not days_str or not days_str.isdigit():
                    messagebox.showerror("Error", "Los días de validez deben ser un número")
                    return
                
                validity_days = int(days_str)
                
                # Crear el keystore
                progress_dialog = self._mostrar_dialogo_progreso("Creando keystore...")
                self.root.update()
                
                try:
                    exito, mensaje = self.apk_analyzer.apk_signer.crear_keystore(
                        destino, password, alias, validity_days, self.root
                    )
                    
                    progress_dialog.destroy()
                    
                    if exito:
                        messagebox.showinfo("Éxito", 
                            f"✅ Keystore creado correctamente!\n\n"
                            f"Archivo: {destino.name}\n"
                            f"Alias: {alias}\n"
                            f"Validez: {validity_days} días\n\n"
                            f"Guarda esta contraseña de forma segura."
                        )
                        self.logger.log_info(f"Keystore creado: {destino}")
                    else:
                        messagebox.showerror("Error", 
                            f"❌ Error creando keystore:\n\n{mensaje}"
                        )
                        self.logger.log_error(f"Error creando keystore: {mensaje}")
                        
                except Exception as e:
                    progress_dialog.destroy()
                    messagebox.showerror("Error", f"Error durante la creación: {str(e)}")
                    self.logger.log_error(f"Excepción creando keystore: {e}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error iniciando creación de firma: {str(e)}")
                self.logger.log_error(f"Error en crear_nueva_firma: {e}")

    def firmar_apk(self):
        if not self.apk_path:
            messagebox.showerror("Error", "No hay APK seleccionado para firmar")
            return

        config = self.services._get_tools_config()
        build_tools = config.get("build_tools")

        if not build_tools:
            messagebox.showerror("Error", "Build-tools no configurado")
            return

        from ui.signing_dialog import SigningDialog
        signing_dialog = SigningDialog(self.root, self.apk_path, build_tools)
        resultado = signing_dialog.mostrar()

        if resultado:
            progress_dialog = self._mostrar_dialogo_progreso("Firmando APK...")
            self.root.update()

            try:
                # ✅ VERIFICAR QUE EL MÉTODO EXISTA
                if not hasattr(self.apk_analyzer, 'firmar_apk'):
                    messagebox.showerror("Error", "El analizador no soporta firma de APKs")
                    progress_dialog.destroy()
                    return

                # ✅ CORREGIR: Pasar solo los argumentos que espera firmar_apk
                exito, output = self.apk_analyzer.firmar_apk(
                    Path(resultado['apk_path']),
                    Path(resultado['jks_path']),
                    resultado['password'],
                    build_tools,
                    resultado.get('alias')  # Este es opcional (6to argumento)
                )

                progress_dialog.destroy()

                if exito:
                    messagebox.showinfo("Éxito", 
                        f"✅ APK firmada correctamente!\n\n"
                        f"{output}"
                    )
                    self.logger.log_info(f"APK firmada: {output}")
                else:
                    messagebox.showerror("Error", 
                        f"❌ Error al firmar APK:\n\n{output}"
                    )
                    self.logger.log_error(f"Error firmando APK: {output}")

            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror("Error", 
                    f"❌ Error durante la firma:\n\n{str(e)}"
                )
                self.logger.log_error(f"Excepción firmando APK: {e}")

    def limpiar_todo(self):
        if not self.apk_path:
            messagebox.showinfo("Información", "No hay nada que limpiar.")
            return

        resultado = messagebox.askyesno(
            "Limpiar Todo",
            "¿Estás seguro de que quieres limpiar todo?\n\n"
            "Esto reseteará:\n"
            "- APK seleccionado\n"
            "- Análisis actual\n"
            "- Logs en memoria"
        )

        if resultado:
            self.services.clear_analysis()
            self.apk_path = None
            self.apk_name = None
            self.current_log = ""
            self.current_analysis = {}

            self.mostrar_estado_inicial()
            self.actualizar_estado_botones()
            self.logger.log_info("Aplicación limpiada")
            messagebox.showinfo("Listo", "Todo ha sido restablecido correctamente")

    def mostrar_acerca_de(self):
        info = self.initializer.get_component('version_info')
        message = f"""
{info['app_name']}

Versión: {info['version']}
Build: {info['version_code']}
Fecha: {info['release_date']}
Desarrollado por: {info['author']}

Una herramienta para análisis y verificación
de aplicaciones Android APK.
"""
        messagebox.showinfo("Acerca de", message)

    def _mostrar_dialogo_progreso(self, mensaje: str):
        dialog = tk.Toplevel(self.root)
        dialog.title("Procesando")
        dialog.geometry("280x100")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text=mensaje, font=("Segoe UI", 9), bg=self.styles.COLORS['primary_bg'],
                 fg=self.styles.COLORS['text_primary'], pady=15).pack()

        progress = ttk.Progressbar(dialog, mode='indeterminate', length=180)
        progress.pack(pady=8)
        progress.start(10)

        return dialog


def main():
    from utils.format_utils import check_single_instance
    if not check_single_instance():
        sys.exit(1)

    try:
        root = tk.Tk()

        from ui.loading_screen import LoadingScreen
        loading_screen = LoadingScreen(root)
        loading_window = loading_screen.mostrar()

        app = APKInspectorApp(root, loading_screen)

        def on_closing():
            root.destroy()
            sys.exit(0)

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

    except Exception as e:
        print(f"Error crítico iniciando la aplicación: {e}")
        try:
            from utils.logger import APKLogger
            logger = APKLogger()
            logger.log_error("Error crítico iniciando aplicación", e)
        except:
            pass


if __name__ == "__main__":
    main()