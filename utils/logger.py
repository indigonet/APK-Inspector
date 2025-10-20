import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class APKLogger:
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path.home() / ".apk_inspector" / "logs"
        self.log_file = self.log_dir / f"apk_inspector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.setup_logging()
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Configurar logger
            self.logger = logging.getLogger('APKInspector')
            self.logger.setLevel(logging.INFO)
            
            # Evitar handlers duplicados
            if self.logger.handlers:
                return
                
            # Formato del log
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Handler para archivo
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            
            # Handler para consola
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Error configurando logger: {e}")
    
    def log_analisis_inicio(self, apk_path: str):
        """Loggear inicio de análisis"""
        self.logger.info(f"INICIO ANÁLISIS - APK: {apk_path}")
    
    def log_analisis_fin(self, apk_path: str, exito: bool):
        """Loggear fin de análisis"""
        estado = "EXITOSO" if exito else "FALLIDO"
        self.logger.info(f"FIN ANÁLISIS - APK: {apk_path} - ESTADO: {estado}")
    
    def log_herramienta_ejecutada(self, herramienta: str, comando: str, exito: bool):
        """Loggear ejecución de herramienta"""
        estado = "EXITOSO" if exito else "FALLIDO"
        self.logger.info(f"HERRAMIENTA: {herramienta} - COMANDO: {comando} - ESTADO: {estado}")
    
    def log_error(self, mensaje: str, excepcion: Optional[Exception] = None):
        """Loggear error"""
        if excepcion:
            self.logger.error(f"{mensaje} - EXCEPCIÓN: {str(excepcion)}")
        else:
            self.logger.error(mensaje)
    
    def log_advertencia(self, mensaje: str):
        """Loggear advertencia"""
        self.logger.warning(mensaje)
    
    def log_warning(self, mensaje: str):
        """Loggear warning (alias para compatibilidad)"""
        self.log_advertencia(mensaje)
    
    def log_info(self, mensaje: str):
        """Loggear información"""
        self.logger.info(mensaje)
    
    def obtener_ruta_log(self) -> Path:
        """Obtener ruta del archivo de log actual"""
        return self.log_file
    
    def limpiar_logs_antiguos(self, dias_retencion: int = 7):
        """Limpiar logs más antiguos que días_retencion"""
        try:
            ahora = datetime.now()
            for log_file in self.log_dir.glob("apk_inspector_*.log"):
                # Extraer fecha del nombre del archivo
                try:
                    fecha_str = log_file.stem.replace("apk_inspector_", "")
                    fecha_log = datetime.strptime(fecha_str, "%Y%m%d_%H%M%S")
                    
                    if (ahora - fecha_log).days > dias_retencion:
                        log_file.unlink()
                except ValueError:
                    continue
                    
        except Exception as e:
            self.log_error("Error limpiando logs antiguos", e)