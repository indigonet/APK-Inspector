import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ToolDetector:
    def __init__(self):
        self.cache = {}
        self.system = platform.system().lower()
        
    def log(self, message: str):
        """Logging para diagnóstico"""
        print(f"[ToolDetector] {message}")
        
    def env_paths(self) -> Dict[str, List[Path]]:
        """Obtener paths del entorno - CACHEADO Y MEJORADO"""
        if 'env_paths' in self.cache:
            return self.cache['env_paths']
            
        candidatos = {"sdk": [], "jdk": []}
        
        # SDK paths
        sdk_envs = ["ANDROID_SDK_ROOT", "ANDROID_HOME"]
        for env_var in sdk_envs:
            env_val = os.environ.get(env_var)
            if env_val:
                env_path = Path(env_val)
                if env_path.exists():
                    candidatos["sdk"].append(env_path.resolve())
                    self.log(f"SDK encontrado en {env_var}: {env_path}")

        home = Path.home()
        
        # SDK paths comunes en Windows
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            android_sdk = Path(localappdata) / "Android" / "Sdk"
            if android_sdk.exists():
                candidatos["sdk"].append(android_sdk.resolve())
        else:
            default_android = home / "AppData" / "Local" / "Android" / "Sdk"
            if default_android.exists():
                candidatos["sdk"].append(default_android.resolve())

        # JDK paths - MEJORADO
        java_envs = ["JAVA_HOME", "JDK_HOME", "JRE_HOME"]
        for env_var in java_envs:
            env_val = os.environ.get(env_var)
            if env_val:
                java_path = Path(env_val)
                if java_path.exists():
                    candidatos["jdk"].append(java_path.resolve())
                    self.log(f"JDK encontrado en {env_var}: {java_path}")

        # Directorios comunes de Java - EXPANDIDOS
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        
        java_dirs = [
            Path(program_files) / "Java",
            Path(program_files_x86) / "Java",
            home / "AppData" / "Local" / "Programs" / "Java",
            # Rutas adicionales para mejor cobertura
            Path("C:") / "Java",
            home / "java"
        ]
        
        for java_dir in java_dirs:
            if java_dir.exists():
                resolved_path = java_dir.resolve()
                if resolved_path not in candidatos["jdk"]:
                    candidatos["jdk"].append(resolved_path)
                    self.log(f"JDK encontrado en ubicación común: {java_dir}")

        # Buscar en ubicaciones específicas del sistema operativo
        self._buscar_jdk_sistema_operativo(candidatos, home)

        self.cache['env_paths'] = candidatos
        return candidatos

    def _buscar_jdk_sistema_operativo(self, candidatos: Dict[str, List[Path]], home: Path):
        """Búsqueda específica por sistema operativo"""
        if self.system == "windows":
            # Buscar en el registro de Windows
            jdk_registry_paths = self._buscar_jdk_registro_windows()
            for jdk_path in jdk_registry_paths:
                if jdk_path not in candidatos["jdk"]:
                    candidatos["jdk"].append(jdk_path)
        elif self.system == "darwin":  # macOS
            mac_java_paths = [
                Path("/Library/Java/JavaVirtualMachines"),
                Path("/usr/local/opt/openjdk"),
                home / "Library" / "Java"
            ]
            for java_path in mac_java_paths:
                if java_path.exists():
                    if java_path not in candidatos["jdk"]:
                        candidatos["jdk"].append(java_path.resolve())
        else:  # Linux/Unix
            linux_java_paths = [
                Path("/usr/lib/jvm"),
                Path("/usr/java"),
                Path("/opt/java"),
                home / "java"
            ]
            for java_path in linux_java_paths:
                if java_path.exists():
                    if java_path not in candidatos["jdk"]:
                        candidatos["jdk"].append(java_path.resolve())

    def _buscar_jdk_registro_windows(self) -> List[Path]:
        """Buscar JDK en el registro de Windows"""
        try:
            import winreg
            
            jdk_paths = []
            registry_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JDK"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Development Kit"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\JavaSoft\JDK"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\JavaSoft\Java Development Kit")
            ]
            
            for hive, key_path in registry_keys:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        try:
                            i = 0
                            while True:
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, subkey_name) as subkey:
                                        try:
                                            java_home, _ = winreg.QueryValueEx(subkey, "JavaHome")
                                            java_path = Path(java_home)
                                            if java_path.exists():
                                                jdk_paths.append(java_path.resolve())
                                                self.log(f"JDK encontrado en registro: {java_path}")
                                        except FileNotFoundError:
                                            pass
                                    i += 1
                                except OSError:
                                    break
                        except OSError:
                            pass
                except FileNotFoundError:
                    continue
                    
            return jdk_paths
        except ImportError:
            self.log("No se puede acceder al registro de Windows (módulo winreg no disponible)")
            return []

    def _buscar_jdk_por_comando(self) -> Optional[Path]:
        """Buscar JDK usando comandos del sistema"""
        try:
            if self.system == "windows":
                result = subprocess.run(
                    ["where", "java.exe"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                result = subprocess.run(
                    ["which", "java"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
            
            if result.returncode == 0:
                java_path = Path(result.stdout.split('\n')[0].strip())
                if java_path.exists():
                    # Navegar hacia JDK_HOME: bin -> parent -> bin
                    jdk_bin = java_path.parent
                    jdk_home = jdk_bin.parent
                    
                    if (jdk_home / "bin").exists():
                        return jdk_home / "bin"
                    elif jdk_bin.exists():
                        return jdk_bin
                        
        except (subprocess.TimeoutExpired, Exception) as e:
            self.log(f"Búsqueda por comando falló: {e}")
        
        return None

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
            self.log(f"Error buscando build-tools: {e}")
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
        """Encontrar bin del JDK - MEJORADO SIGNIFICATIVAMENTE"""
        cache_key = f"jdk_bin_{jdk_root}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        self.log(f"Buscando JDK bin en: {jdk_root}")
        
        # Estrategia 1: Verificar si es directamente el directorio bin
        if (jdk_root / "bin").exists():
            resultado = jdk_root / "bin"
            self.log(f"JDK bin encontrado directamente: {resultado}")
            self.cache[cache_key] = resultado
            return resultado
            
        # Estrategia 2: Buscar en subdirectorios con patrones expandidos
        try:
            jdk_patterns = ["jdk*", "java*", "*jdk*", "*java*", "jre*", "*jre*", "openjdk*", "oracle*"]
            
            for pattern in jdk_patterns:
                for item in jdk_root.glob(pattern):
                    if item.is_dir():
                        bin_path = item / "bin"
                        if bin_path.exists():
                            self.log(f"JDK bin encontrado en subdirectorio: {bin_path}")
                            self.cache[cache_key] = bin_path
                            return bin_path
        except Exception as e:
            self.log(f"Error en búsqueda con patrones: {e}")

        # Estrategia 3: Búsqueda recursiva limitada
        try:
            for item in jdk_root.iterdir():
                if item.is_dir():
                    dir_name_lower = item.name.lower()
                    # Patrones más flexibles para JDK
                    if any(keyword in dir_name_lower for keyword in 
                          ["jdk", "java", "jre", "openjdk", "oracle", "adoptopenjdk", "amazon", "corretto"]):
                        
                        # Buscar bin directamente
                        bin_path = item / "bin"
                        if bin_path.exists():
                            self.log(f"JDK bin encontrado recursivamente: {bin_path}")
                            self.cache[cache_key] = bin_path
                            return bin_path
                        
                        # Buscar en sub-subdirectorios (para estructuras anidadas)
                        for sub_item in item.iterdir():
                            if sub_item.is_dir():
                                sub_bin = sub_item / "bin"
                                if sub_bin.exists():
                                    self.log(f"JDK bin encontrado en sub-subdirectorio: {sub_bin}")
                                    self.cache[cache_key] = sub_bin
                                    return sub_bin
        except (PermissionError, OSError) as e:
            self.log(f"Error en búsqueda recursiva: {e}")
            
        self.log(f"No se pudo encontrar JDK bin en: {jdk_root}")
        self.cache[cache_key] = None
        return None

    def detectar_herramientas(self) -> Dict:
        """Detección principal de todas las herramientas - MEJORADA"""
        if 'herramientas' in self.cache:
            return self.cache['herramientas']
            
        paths = self.env_paths()
        resultado = {
            "sdk_root": None,
            "platform_tools": None, 
            "build_tools": None,
            "jdk_bin": None
        }
        
        self.log("Iniciando detección de herramientas...")
        
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
                self.log(f"SDK completo encontrado: {sdk_path}")
                break
            elif platform and not resultado["platform_tools"]:
                resultado["platform_tools"] = platform
            elif build and not resultado["build_tools"]:
                resultado["build_tools"] = build
                
            if not resultado["sdk_root"] and (platform or build):
                resultado["sdk_root"] = sdk_path

        # Buscar JDK - ESTRATEGIA MEJORADA
        jdk_encontrado = False
        for jdk_path in paths["jdk"]:
            if not jdk_path.exists():
                continue
                
            jdk_bin = self.encontrar_jdk_bin(jdk_path)
            if jdk_bin:
                resultado["jdk_bin"] = jdk_bin
                jdk_encontrado = True
                self.log(f"JDK encontrado: {jdk_bin}")
                break

        # Si no encontramos JDK con métodos normales, intentar con comandos
        if not jdk_encontrado:
            self.log("Intentando búsqueda alternativa de JDK...")
            jdk_alternativo = self._buscar_jdk_por_comando()
            if jdk_alternativo:
                resultado["jdk_bin"] = jdk_alternativo
                self.log(f"JDK encontrado alternativamente: {jdk_alternativo}")

        # Verificar variables de entorno específicas como fallback
        android_root = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        if android_root and not resultado["sdk_root"]:
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
            "jdk": {"instalado": False, "ruta": None, "jarsigner": False, "java": False, "javac": False}
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
        
        # Verificar JDK - MÁS DETALLADO
        if detectado["jdk_bin"] and detectado["jdk_bin"].exists():
            resultados["jdk"]["instalado"] = True
            resultados["jdk"]["ruta"] = str(detectado["jdk_bin"])
            jarsigner_bin = detectado["jdk_bin"] / ("jarsigner.exe" if sys.platform.startswith("win") else "jarsigner")
            resultados["jdk"]["jarsigner"] = jarsigner_bin.exists()
            java_bin = detectado["jdk_bin"] / ("java.exe" if sys.platform.startswith("win") else "java")
            resultados["jdk"]["java"] = java_bin.exists()
            javac_bin = detectado["jdk_bin"] / ("javac.exe" if sys.platform.startswith("win") else "javac")
            resultados["jdk"]["javac"] = javac_bin.exists()
        
        return resultados

    def generar_diagnostico(self) -> str:
        """Generar diagnóstico legible"""
        diagnostico = []
        diagnostico.append("=== DIAGNÓSTICO HERRAMIENTAS ANDROID/JDK ===")
        
        # Variables de entorno
        diagnostico.append("\n--- VARIABLES DE ENTORNO ---")
        java_home = os.environ.get("JAVA_HOME")
        android_home = os.environ.get("ANDROID_HOME")
        android_sdk_root = os.environ.get("ANDROID_SDK_ROOT")
        
        diagnostico.append(f"JAVA_HOME: {java_home or 'No configurada'}")
        diagnostico.append(f"ANDROID_HOME: {android_home or 'No configurada'}")
        diagnostico.append(f"ANDROID_SDK_ROOT: {android_sdk_root or 'No configurada'}")
        
        # Rutas detectadas
        paths = self.env_paths()
        diagnostico.append(f"\n--- RUTAS SDK DETECTADAS ({len(paths['sdk'])}) ---")
        for sdk_path in paths["sdk"]:
            diagnostico.append(f"  {sdk_path}")
            
        diagnostico.append(f"\n--- RUTAS JDK DETECTADAS ({len(paths['jdk'])}) ---")
        for jdk_path in paths["jdk"]:
            diagnostico.append(f"  {jdk_path}")
        
        # Herramientas detectadas
        herramientas = self.detectar_herramientas()
        diagnostico.append("\n--- HERRAMIENTAS DETECTADAS ---")
        for nombre, ruta in herramientas.items():
            estado = "✓ ENCONTRADO" if ruta and ruta.exists() else "✗ NO ENCONTRADO"
            diagnostico.append(f"  {nombre}: {estado}")
            if ruta:
                diagnostico.append(f"    Ruta: {ruta}")
        
        # Verificación detallada
        estado = self.verificar_herramientas_instaladas()
        diagnostico.append("\n--- VERIFICACIÓN DETALLADA ---")
        for herramienta, detalles in estado.items():
            icon = "✓" if detalles["instalado"] else "✗"
            diagnostico.append(f"{icon} {herramienta}:")
            for key, value in detalles.items():
                if key not in ['instalado', 'ruta'] and isinstance(value, bool):
                    icon_bin = "✓" if value else "✗"
                    diagnostico.append(f"  {icon_bin} {key}")
        
        return "\n".join(diagnostico)

    def limpiar_cache(self):
        """Limpiar cache para forzar nueva detección"""
        self.cache.clear()
        self.log("Cache limpiado")


# Ejemplo de uso
if __name__ == "__main__":
    detector = ToolDetector()
    
    print("Detectando herramientas Android/JDK...\n")
    
    # Generar diagnóstico
    diagnostico = detector.generar_diagnostico()
    print(diagnostico)
    
    # Mostrar estado resumido
    print("\n" + "="*50)
    estado = detector.verificar_herramientas_instaladas()
    
    for herramienta, detalles in estado.items():
        icon = "✅" if detalles["instalado"] else "❌"
        print(f"{icon} {herramienta.replace('_', ' ').title()}: {'INSTALADO' if detalles['instalado'] else 'NO ENCONTRADO'}")