import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

class ToolDetector:
    def __init__(self):
        self.cache = {}
        
    def env_paths(self) -> Dict[str, List[Path]]:
        """Obtener paths del entorno - CACHEADO"""
        if 'env_paths' in self.cache:
            return self.cache['env_paths']
            
        candidatos = {"sdk": [], "jdk": []}
        
        # SDK paths
        sdk_envs = ["ANDROID_SDK_ROOT", "ANDROID_HOME"]
        for env_var in sdk_envs:
            env_val = os.environ.get(env_var)
            if env_val and Path(env_val).exists():
                candidatos["sdk"].append(Path(env_val))

        home = Path.home()
        
        # SDK paths comunes en Windows
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            android_sdk = Path(localappdata) / "Android" / "Sdk"
            if android_sdk.exists():
                candidatos["sdk"].append(android_sdk)
        else:
            default_android = home / "AppData" / "Local" / "Android" / "Sdk"
            if default_android.exists():
                candidatos["sdk"].append(default_android)

        # JDK paths
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_path = Path(java_home)
            if java_path.exists():
                candidatos["jdk"].append(java_path)

        # Directorios comunes de Java
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        
        java_dirs = [
            Path(program_files) / "Java",
            Path(program_files_x86) / "Java",
            home / "AppData" / "Local" / "Programs" / "Java"
        ]
        
        for java_dir in java_dirs:
            if java_dir.exists():
                candidatos["jdk"].append(java_dir)

        self.cache['env_paths'] = candidatos
        return candidatos

    def encontrar_build_tools(self, sdk_path: Path) -> Optional[Path]:
        """Encontrar build-tools más reciente"""
        cache_key = f"build_tools_{sdk_path}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            build_root = sdk_path / "build-tools"
            if not build_root.exists():
                self.cache[cache_key] = None
                return None
                
            # Buscar versiones y ordenar semánticamente
            versiones = []
            for item in build_root.iterdir():
                if item.is_dir():
                    try:
                        # Convertir versión a tupla para ordenar correctamente
                        version_parts = []
                        for part in item.name.split('.'):
                            version_parts.append(int(part) if part.isdigit() else part)
                        versiones.append((tuple(version_parts), item))
                    except (ValueError, AttributeError):
                        versiones.append((item.name, item))
            
            # Ordenar por versión (más reciente primero)
            versiones.sort(key=lambda x: x[0], reverse=True)
            resultado = versiones[0][1] if versiones else None
            
            self.cache[cache_key] = resultado
            return resultado
            
        except Exception as e:
            print(f"Error buscando build-tools: {e}")
            return None

    def encontrar_platform_tools(self, sdk_path: Path) -> Optional[Path]:
        """Encontrar platform-tools"""
        cache_key = f"platform_tools_{sdk_path}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        platform_path = sdk_path / "platform-tools"
        resultado = platform_path if platform_path.exists() else None
        self.cache[cache_key] = resultado
        return resultado

    def encontrar_jdk_bin(self, jdk_root: Path) -> Optional[Path]:
        """Encontrar bin del JDK"""
        cache_key = f"jdk_bin_{jdk_root}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Verificar si es directamente el bin
        if (jdk_root / "bin").exists():
            resultado = jdk_root / "bin"
            self.cache[cache_key] = resultado
            return resultado
            
        # Buscar en subdirectorios
        try:
            for item in jdk_root.iterdir():
                if item.is_dir() and item.name.lower().startswith(("jdk", "java")):
                    bin_path = item / "bin"
                    if bin_path.exists():
                        self.cache[cache_key] = bin_path
                        return bin_path
        except Exception:
            pass
            
        self.cache[cache_key] = None
        return None

    def detectar_herramientas(self) -> Dict:
        """Detección principal de todas las herramientas"""
        if 'herramientas' in self.cache:
            return self.cache['herramientas']
            
        paths = self.env_paths()
        resultado = {
            "sdk_root": None,
            "platform_tools": None, 
            "build_tools": None,
            "jdk_bin": None
        }
        
        # Buscar SDK completo
        for sdk_path in paths["sdk"]:
            if not sdk_path.exists():
                continue
                
            platform = self.encontrar_platform_tools(sdk_path)
            build = self.encontrar_build_tools(sdk_path)
            
            if platform and build:
                resultado["sdk_root"] = sdk_path
                resultado["platform_tools"] = platform
                resultado["build_tools"] = build
                break
            elif platform and not resultado["platform_tools"]:
                resultado["platform_tools"] = platform
            elif build and not resultado["build_tools"]:
                resultado["build_tools"] = build
                
            if not resultado["sdk_root"] and (platform or build):
                resultado["sdk_root"] = sdk_path

        # Buscar JDK
        for jdk_path in paths["jdk"]:
            if not jdk_path.exists():
                continue
                
            jdk_bin = self.encontrar_jdk_bin(jdk_path)
            if jdk_bin:
                resultado["jdk_bin"] = jdk_bin
                break

        # Verificar variables de entorno específicas
        android_root = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        if android_root:
            android_path = Path(android_root)
            if android_path.exists():
                resultado["sdk_root"] = android_path
                if not resultado["platform_tools"]:
                    resultado["platform_tools"] = self.encontrar_platform_tools(android_path)
                if not resultado["build_tools"]:
                    resultado["build_tools"] = self.encontrar_build_tools(android_path)

        java_home = os.environ.get("JAVA_HOME")
        if java_home and not resultado["jdk_bin"]:
            java_path = Path(java_home)
            if java_path.exists():
                jdk_bin = self.encontrar_jdk_bin(java_path)
                if jdk_bin:
                    resultado["jdk_bin"] = jdk_bin

        self.cache['herramientas'] = resultado
        return resultado

    def verificar_herramientas_instaladas(self) -> Dict:
        """Verificar estado de instalación de herramientas"""
        detectado = self.detectar_herramientas()
        
        resultados = {
            "platform_tools": {"instalado": False, "ruta": None, "adb": False},
            "build_tools": {"instalado": False, "ruta": None, "aapt": False, "apksigner": False},
            "jdk": {"instalado": False, "ruta": None, "jarsigner": False}
        }
        
        # Verificar platform-tools
        if detectado["platform_tools"] and detectado["platform_tools"].exists():
            resultados["platform_tools"]["instalado"] = True
            resultados["platform_tools"]["ruta"] = str(detectado["platform_tools"])
            adb_bin = detectado["platform_tools"] / ("adb.exe" if sys.platform.startswith("win") else "adb")
            resultados["platform_tools"]["adb"] = adb_bin.exists()
        
        # Verificar build-tools
        if detectado["build_tools"] and detectado["build_tools"].exists():
            resultados["build_tools"]["instalado"] = True
            resultados["build_tools"]["ruta"] = str(detectado["build_tools"])
            aapt_bin = detectado["build_tools"] / ("aapt.exe" if sys.platform.startswith("win") else "aapt")
            resultados["build_tools"]["aapt"] = aapt_bin.exists()
            apksigner_bin = detectado["build_tools"] / ("apksigner.bat" if sys.platform.startswith("win") else "apksigner")
            resultados["build_tools"]["apksigner"] = apksigner_bin.exists()
        
        # Verificar JDK
        if detectado["jdk_bin"] and detectado["jdk_bin"].exists():
            resultados["jdk"]["instalado"] = True
            resultados["jdk"]["ruta"] = str(detectado["jdk_bin"])
            jarsigner_bin = detectado["jdk_bin"] / ("jarsigner.exe" if sys.platform.startswith("win") else "jarsigner")
            resultados["jdk"]["jarsigner"] = jarsigner_bin.exists()
        
        return resultados

    def limpiar_cache(self):
        """Limpiar cache para forzar nueva detección"""
        self.cache.clear()