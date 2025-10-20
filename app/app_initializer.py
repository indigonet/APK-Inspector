"""
APK Inspector & Verifier - Inicializador de la aplicación
Maneja la inicialización de componentes y dependencias
"""

import sys
from pathlib import Path
import threading
from tkinter import messagebox

class AppInitializer:
    """Clase para manejar la inicialización de la aplicación"""
    
    def __init__(self, root, loading_screen=None):
        self.root = root
        self.loading_screen = loading_screen
        self.components = {}
        self.loading_complete = False
    
    def initialize_with_loading(self):
        """Inicialización con pantalla de carga"""
        def initialization_task():
            try:
                self._load_phase_1_basic_components()
                self._load_phase_2_core_components() 
                self._load_phase_3_utils_components()
                self._load_phase_4_setup_components()
                self.root.after(0, self._finalize_initialization)
                
            except Exception as e:
                self.root.after(0, lambda: self._handle_initialization_error(e))
        
        threading.Thread(target=initialization_task, daemon=True).start()
    
    def _load_phase_1_basic_components(self):
        """Fase 1: Componentes básicos"""
        self.loading_screen.actualizar_progreso(10, "Cargando estilos...")
        from ui.components import AppStyles
        self.components['styles'] = AppStyles()
        
        self.loading_screen.actualizar_progreso(20, "Cargando información de versión...")
        from utils.version import get_version_info, __version__, __app_name__
        self.components['version_info'] = get_version_info()
        self.components['app_name'] = __app_name__
        self.components['version'] = __version__
    
    def _load_phase_2_core_components(self):
        """Fase 2: Componentes core"""
        self.loading_screen.actualizar_progreso(30, "Inicializando componentes core...")
        from core.tool_detector import ToolDetector
        from core.apk_analyzer import APKAnalyzer
        from core.signature_verifier import SignatureVerifier
        from core.adb_manager import ADBManager
        
        self.components['tool_detector'] = ToolDetector()
        
        # ✅ CORREGIDO: Pasar el logger a APKAnalyzer si ya está disponible
        logger = self.components.get('logger')
        self.components['apk_analyzer'] = APKAnalyzer(
            self.components['tool_detector'], 
            logger=logger  # ✅ Pasar el logger si existe
        )
        
        self.components['signature_verifier'] = SignatureVerifier()
        self.components['adb_manager'] = ADBManager()
    
    def _load_phase_3_utils_components(self):
        """Fase 3: Componentes utils"""
        self.loading_screen.actualizar_progreso(50, "Inicializando componentes utils...")
        from utils.config_manager import ConfigManager
        from utils.file_utils import FileUtils
        from utils.logger import APKLogger
        from utils.format_utils import FormatUtils
        
        self.components['config_manager'] = ConfigManager()
        self.components['file_utils'] = FileUtils()
        self.components['logger'] = APKLogger()  # ✅ Logger se crea aquí
        self.components['format_utils'] = FormatUtils()
        
        # ✅ ACTUALIZAR APKAnalyzer con el logger ahora que está disponible
        if 'apk_analyzer' in self.components:
            self.components['apk_analyzer'].logger = self.components['logger']
        
        # Inicializar PCIDSSAnalyzer si está disponible
        self._initialize_pci_analyzer()
    
    def _initialize_pci_analyzer(self):
        """Inicializar el analizador PCI DSS dinámicamente"""
        try:
            from core.pci_dss_analyzer import PCIDSSAnalyzer
            self.components['pci_analyzer'] = PCIDSSAnalyzer()
        except ImportError:
            # Si no está disponible, establecer como None
            self.components['pci_analyzer'] = None
    
    def _load_phase_4_setup_components(self):
        """Fase 4: Configuración final"""
        self.loading_screen.actualizar_progreso(60, "Configurando estado de la aplicación...")
        # Estado de la aplicación
        self.components['apk_path'] = None
        self.components['apk_name'] = None
        self.components['current_log'] = ""
        self.components['current_analysis'] = {}
        self.components['apk_buttons'] = []
    
    def _finalize_initialization(self):
        """Finalizar inicialización en hilo principal"""
        try:
            self.loading_screen.actualizar_progreso(90, "Finalizando configuración...")
            
            # ✅ VERIFICACIÓN FINAL: Asegurar que todos los componentes tengan el logger
            if 'apk_analyzer' in self.components and 'logger' in self.components:
                self.components['apk_analyzer'].logger = self.components['logger']
            
            self.loading_complete = True
            self.loading_screen.actualizar_progreso(100, "¡Listo!")
            
        except Exception as e:
            self._handle_initialization_error(e)
    
    def _handle_initialization_error(self, error):
        """Manejar errores durante la inicialización"""
        if self.loading_screen:
            self.loading_screen.cerrar()
        messagebox.showerror(
            "Error de Inicialización", 
            f"No se pudo iniciar la aplicación:\n\n{str(error)}"
        )
        self.root.quit()
    
    def get_component(self, component_name):
        """Obtener un componente por nombre"""
        return self.components.get(component_name)
    
    def get_all_components(self):
        """Obtener todos los componentes"""
        return self.components