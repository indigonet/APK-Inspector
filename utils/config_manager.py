import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".apk_inspector_config.json"
        self._cache = None
        self._default_config = {
            "sdk_root": "",
            "build_tools": "", 
            "platform_tools": "",
            "jdk_bin": "",
            "ui_scale": 1.0,
            "theme": "light",
            "recent_apks": [],
            "max_recent_files": 10
        }
        
    def cargar_config(self) -> Dict[str, Any]:
        """Cargar configuración con cache y valores por defecto"""
        if self._cache is not None:
            return self._cache.copy()
            
        config = self._default_config.copy()
        
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    # Merge con valores por defecto
                    config.update(user_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Advertencia: No se pudo cargar configuración: {e}")
            # Usar configuración por defecto
            
        self._cache = config
        return config.copy()
    
    def guardar_config(self, config: Dict[str, Any]) -> bool:
        """Guardar configuración manteniendo estructura completa"""
        try:
            # Preservar configuración existente y mergear con nueva
            current_config = self.cargar_config()
            current_config.update(config)
            
            # Crear directorio si no existe
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2, ensure_ascii=False)
            
            self._cache = current_config
            return True
            
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False
    
    def obtener_valor(self, clave: str, valor_por_defecto: Any = None) -> Any:
        """Obtener valor específico de configuración"""
        config = self.cargar_config()
        return config.get(clave, valor_por_defecto)
    
    def establecer_valor(self, clave: str, valor: Any) -> bool:
        """Establecer valor específico en configuración"""
        config = self.cargar_config()
        config[clave] = valor
        return self.guardar_config(config)
    
    def agregar_apk_reciente(self, apk_path: str) -> bool:
        """Agregar APK a la lista de archivos recientes"""
        config = self.cargar_config()
        recent_apks = config.get("recent_apks", [])
        
        # Remover si ya existe
        if apk_path in recent_apks:
            recent_apks.remove(apk_path)
        
        # Agregar al inicio
        recent_apks.insert(0, apk_path)
        
        # Limitar tamaño
        max_files = config.get("max_recent_files", 10)
        config["recent_apks"] = recent_apks[:max_files]
        
        return self.guardar_config(config)
    
    def obtener_apks_recientes(self) -> list:
        """Obtener lista de APKs recientes"""
        config = self.cargar_config()
        return config.get("recent_apks", [])
    
    def limpiar_apks_recientes(self) -> bool:
        """Limpiar lista de APKs recientes"""
        config = self.cargar_config()
        config["recent_apks"] = []
        return self.guardar_config(config)
    
    def limpiar_cache(self):
        """Forzar recarga de configuración"""
        self._cache = None