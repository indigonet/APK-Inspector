# app/tool_manager.py - VERSIÓN COMPLETA CON JDK EMBEBIDO
import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, List

class ToolManager:
    """
    Gestiona TODAS las herramientas embebidas (scrcpy, ADB, aapt, JDK, apksigner) dentro del .exe
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.architecture()[0]
        self.tools_dir = self._get_tools_directory()
        self.tools_dir.mkdir(exist_ok=True)
        self.setup_logging()
        
        # Cache para evitar verificaciones repetidas
        self._scrcpy_cache = None
        self._adb_cache = None
        self._jdk_cache = None
        self._apksigner_cache = None
        self._aapt_cache = None
        
    def setup_logging(self):
        """Configurar logging para herramientas"""
        import logging
        self.logger = logging.getLogger("ToolManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _get_tools_directory(self) -> Path:
        """Obtener directorio de herramientas (compatible con PyInstaller)"""
        if getattr(sys, 'frozen', False):
            # Ejecutando desde .exe - usar directorio temporal
            base_dir = Path(sys._MEIPASS) / "tools"
        else:
            # Ejecutando desde código - usar directorio del proyecto
            base_dir = Path(__file__).parent.parent / "tools"
        
        return base_dir

    # ========== JDK EMBEBIDO ==========
    
    def setup_jdk(self) -> Dict:
        """Configurar JDK embebido para firmar APKs"""
        if self._jdk_cache and self._jdk_cache.get("available", False):
            return self._jdk_cache
            
        jdk_dir = self.tools_dir / "jdk"
        jdk_dir.mkdir(exist_ok=True)
        
        # Primero verificar JDK en sistema
        system_jdk = self._find_system_jdk()
        if system_jdk:
            self._jdk_cache = {
                "available": True, 
                "path": str(system_jdk["java_home"]),
                "source": "system",
                "keytool": system_jdk["keytool"],
                "version": system_jdk["version"]
            }
            return self._jdk_cache
        
        # Verificar si ya tenemos JDK embebido
        embedded_jdk = self._get_embedded_jdk(jdk_dir)
        if embedded_jdk:
            self._jdk_cache = {
                "available": True,
                "path": str(embedded_jdk["java_home"]),
                "source": "embedded", 
                "keytool": embedded_jdk["keytool"],
                "version": embedded_jdk["version"]
            }
            return self._jdk_cache
        
        # Descargar JDK portable
        self._jdk_cache = self._download_portable_jdk()
        return self._jdk_cache
    
    def _find_system_jdk(self) -> Optional[Dict]:
        """Buscar JDK en el sistema"""
        try:
            # Verificar JAVA_HOME
            java_home = os.environ.get('JAVA_HOME')
            if java_home:
                java_home_path = Path(java_home)
                keytool_path = java_home_path / "bin" / "keytool.exe"
                if keytool_path.exists():
                    version = self._get_java_version(java_home_path)
                    return {
                        "java_home": java_home_path,
                        "keytool": str(keytool_path),
                        "version": version
                    }
            
            # Buscar en PATH
            keytool_cmd = shutil.which("keytool")
            if keytool_cmd:
                keytool_path = Path(keytool_cmd)
                java_home = keytool_path.parent.parent  # bin -> JDK home
                version = self._get_java_version(java_home)
                return {
                    "java_home": java_home,
                    "keytool": keytool_cmd,
                    "version": version
                }
                
        except Exception as e:
            self.logger.warning(f"Error buscando JDK del sistema: {e}")
            
        return None
    
    def _get_java_version(self, java_home: Path) -> str:
        """Obtener versión de Java"""
        try:
            java_exe = java_home / "bin" / "java.exe"
            result = subprocess.run(
                [str(java_exe), "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stderr.split('\n'):
                if 'version' in line.lower():
                    return line.strip()
            return "Unknown"
        except:
            return "Unknown"
    
    def _get_embedded_jdk(self, jdk_dir: Path) -> Optional[Dict]:
        """Verificar si ya tenemos JDK embebido"""
        possible_paths = [
            jdk_dir / "jdk-*" / "bin" / "keytool.exe",
            jdk_dir / "bin" / "keytool.exe",
            jdk_dir / "keytool.exe"
        ]
        
        for pattern in possible_paths:
            for keytool_path in jdk_dir.glob(str(pattern).replace('\\', '/')):
                if keytool_path.exists():
                    java_home = keytool_path.parent.parent
                    version = self._get_java_version(java_home)
                    return {
                        "java_home": java_home,
                        "keytool": str(keytool_path),
                        "version": version
                    }
        return None
    
    def _download_portable_jdk(self) -> Dict:
        """Descargar JDK portable para Windows"""
        if self.system != "windows":
            return {"available": False, "error": "JDK portable solo disponible para Windows"}
            
        jdk_dir = self.tools_dir / "jdk"
        jdk_dir.mkdir(exist_ok=True)
        
        # JDK portable más compacto (OpenJDK 11)
        jdk_urls = [
            "https://github.com/AdoptOpenJDK/openjdk11-binaries/releases/download/jdk-11.0.11%2B9/OpenJDK11U-jdk_x64_windows_hotspot_11.0.11_9.zip",
        ]
        
        temp_zip = jdk_dir / "jdk_temp.zip"
        
        for jdk_url in jdk_urls:
            self.logger.info(f"📥 Descargando JDK portable: {jdk_url}")
            
            if self._download_file(jdk_url, temp_zip):
                if self._extract_zip(temp_zip, jdk_dir):
                    embedded_jdk = self._get_embedded_jdk(jdk_dir)
                    if embedded_jdk:
                        if temp_zip.exists():
                            temp_zip.unlink()
                            
                        return {
                            "available": True,
                            "path": str(embedded_jdk["java_home"]),
                            "source": "downloaded",
                            "keytool": embedded_jdk["keytool"],
                            "version": embedded_jdk["version"],
                            "message": "JDK portable descargado exitosamente"
                        }
        
        return {"available": False, "error": "No se pudo descargar JDK portable"}
    
    def get_keytool_path(self) -> Optional[str]:
        """Obtener ruta de keytool para firmar APKs"""
        jdk_status = self.setup_jdk()
        if jdk_status.get("available", False):
            return jdk_status.get("keytool")
        return None
    
    def get_java_home(self) -> Optional[str]:
        """Obtener JAVA_HOME"""
        jdk_status = self.setup_jdk()
        if jdk_status.get("available", False):
            return jdk_status.get("path")
        return None

    # ========== APKSIGNER EMBEBIDO ==========
    
    def setup_apksigner(self) -> Dict:
        """Configurar apksigner embebido"""
        if self._apksigner_cache and self._apksigner_cache.get("available", False):
            return self._apksigner_cache
            
        build_tools_dir = self.tools_dir / "android" / "build-tools"
        build_tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Buscar apksigner en build-tools del sistema
        system_apksigner = self._find_system_apksigner()
        if system_apksigner:
            self._apksigner_cache = {"available": True, "path": str(system_apksigner), "source": "system"}
            return self._apksigner_cache
        
        # Buscar en nuestro build-tools embebido
        embedded_apksigner = self._find_embedded_apksigner(build_tools_dir)
        if embedded_apksigner:
            self._apksigner_cache = {"available": True, "path": str(embedded_apksigner), "source": "embedded"}
            return self._apksigner_cache
        
        # Intentar descargar build-tools completo
        self._apksigner_cache = self._download_build_tools_for_apksigner()
        return self._apksigner_cache
    
    def _find_system_apksigner(self) -> Optional[Path]:
        """Buscar apksigner en el sistema"""
        common_paths = [
            Path.home() / "AppData" / "Local" / "Android" / "Sdk",
            Path("/usr/local/android-sdk"),
            Path("/opt/android-sdk"), 
            Path("C:") / "Android" / "android-sdk"
        ]
        
        for base_path in common_paths:
            if base_path.exists():
                build_tools_dir = base_path / "build-tools"
                if build_tools_dir.exists():
                    versions = sorted([d for d in build_tools_dir.iterdir() if d.is_dir()], reverse=True)
                    for version_dir in versions:
                        apksigner_path = version_dir / "apksigner.bat" if self.system == "windows" else version_dir / "apksigner"
                        if apksigner_path.exists():
                            return apksigner_path
        return None
    
    def _find_embedded_apksigner(self, build_tools_dir: Path) -> Optional[Path]:
        """Buscar apksigner en herramientas embebidas"""
        apksigner_name = "apksigner.bat" if self.system == "windows" else "apksigner"
        
        for apksigner_path in build_tools_dir.rglob(apksigner_name):
            if apksigner_path.exists():
                return apksigner_path
        return None
    
    def _download_build_tools_for_apksigner(self) -> Dict:
        """Descargar build-tools que incluye apksigner"""
        if self.system == "windows":
            build_tools_url = "https://dl.google.com/android/repository/build-tools_r33-windows.zip"
            build_tools_dir = self.tools_dir / "android" / "build-tools"
            
            temp_zip = build_tools_dir / "build-tools.zip"
            
            if self._download_file(build_tools_url, temp_zip):
                if self._extract_zip(temp_zip, build_tools_dir):
                    apksigner_path = self._find_embedded_apksigner(build_tools_dir)
                    if apksigner_path:
                        return {
                            "available": True,
                            "path": str(apksigner_path),
                            "source": "downloaded"
                        }
        
        return {"available": False, "error": "No se pudo obtener apksigner"}

    # ========== AAPT EMBEBIDO ==========
    
    def setup_aapt(self) -> Dict:
        """Configurar AAPT embebido"""
        if self._aapt_cache and self._aapt_cache.get("available", False):
            return self._aapt_cache
            
        build_tools_dir = self.tools_dir / "android" / "build-tools"
        build_tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Primero buscar aapt en el sistema
        system_aapt = self._find_system_aapt()
        if system_aapt:
            self._aapt_cache = {"available": True, "path": str(system_aapt), "source": "system"}
            return self._aapt_cache
        
        # Buscar en build-tools embebido
        embedded_aapt = self._find_embedded_aapt(build_tools_dir)
        if embedded_aapt:
            self._aapt_cache = {"available": True, "path": str(embedded_aapt), "source": "embedded"}
            return self._aapt_cache
        
        # Si no se encuentra, usar el mismo build-tools descargado para apksigner
        self._aapt_cache = self._download_build_tools_for_aapt()
        return self._aapt_cache
    
    def _find_system_aapt(self) -> Optional[Path]:
        """Buscar aapt en el sistema"""
        common_paths = [
            Path.home() / "AppData" / "Local" / "Android" / "Sdk",
            Path("/usr/local/android-sdk"),
            Path("/opt/android-sdk"),
            Path("C:") / "Android" / "android-sdk",
            self.tools_dir / "android" / "build-tools"
        ]
        
        aapt_patterns = [
            "build-tools/*/aapt*",
            "platform-tools/aapt*"
        ]
        
        for base_path in common_paths:
            if base_path.exists():
                for pattern in aapt_patterns:
                    for aapt_file in base_path.glob(pattern):
                        if aapt_file.is_file() and "aapt" in aapt_file.name.lower():
                            return aapt_file
        
        return None
    
    def _find_embedded_aapt(self, build_tools_dir: Path) -> Optional[Path]:
        """Buscar aapt en herramientas embebidas"""
        aapt_name = "aapt.exe" if self.system == "windows" else "aapt"
        
        for aapt_path in build_tools_dir.rglob(aapt_name):
            if aapt_path.exists():
                return aapt_path
        return None
    
    def _download_build_tools_for_aapt(self) -> Dict:
        """Descargar build-tools para aapt"""
        if self.system == "windows":
            build_tools_url = "https://dl.google.com/android/repository/build-tools_r33-windows.zip"
            build_tools_dir = self.tools_dir / "android" / "build-tools"
            
            temp_zip = build_tools_dir / "build-tools.zip"
            
            if self._download_file(build_tools_url, temp_zip):
                if self._extract_zip(temp_zip, build_tools_dir):
                    aapt_path = self._find_embedded_aapt(build_tools_dir)
                    if aapt_path:
                        return {
                            "available": True,
                            "path": str(aapt_path),
                            "source": "downloaded"
                        }
        
        return {"available": False, "error": "No se pudo obtener AAPT"}

    # ========== ADB EMBEBIDO ==========
    
    def setup_adb(self) -> Dict:
        """Configurar ADB embebido (platform-tools)"""
        if self._adb_cache and self._adb_cache.get("available", False):
            return self._adb_cache
            
        platform_tools_dir = self.tools_dir / "android" / "platform-tools"
        platform_tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Primero verificar si ADB está en PATH
        if self._check_adb_in_path():
            self._adb_cache = {"available": True, "path": "adb", "source": "PATH"}
            return self._adb_cache
        
        # Buscar en platform-tools descargados
        adb_path = self._get_adb_executable(platform_tools_dir)
        if adb_path and adb_path.exists():
            self._adb_cache = {"available": True, "path": str(adb_path), "source": "embedded"}
            return self._adb_cache
        
        # Si no se encuentra, descargar platform-tools
        self._adb_cache = self._download_platform_tools()
        return self._adb_cache
    
    def _check_adb_in_path(self) -> bool:
        """Verificar si ADB está disponible en PATH"""
        try:
            result = subprocess.run(
                ["adb", "version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_adb_executable(self, platform_tools_dir: Path) -> Optional[Path]:
        """Obtener ruta del ejecutable ADB"""
        if self.system == "windows":
            adb_exe = platform_tools_dir / "platform-tools" / "adb.exe"
            if adb_exe.exists():
                return adb_exe
            
            adb_exe_direct = platform_tools_dir / "adb.exe"
            if adb_exe_direct.exists():
                return adb_exe_direct
        else:
            adb_bin = platform_tools_dir / "platform-tools" / "adb"
            if adb_bin.exists():
                self._make_executable(adb_bin)
                return adb_bin
            
            adb_bin_direct = platform_tools_dir / "adb"
            if adb_bin_direct.exists():
                self._make_executable(adb_bin_direct)
                return adb_bin_direct
        
        return None
    
    def _download_platform_tools(self) -> Dict:
        """Descargar platform-tools (que incluye ADB)"""
        platform_tools_dir = self.tools_dir / "android" / "platform-tools"
        platform_tools_dir.mkdir(parents=True, exist_ok=True)
        
        download_urls = {
            "windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
            "linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip", 
            "darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
        }
        
        url = download_urls.get(self.system)
        if not url:
            return {"available": False, "error": f"Plataforma no soportada: {self.system}"}
        
        temp_zip = platform_tools_dir / "platform-tools.zip"
        
        if self._download_file(url, temp_zip):
            if self._extract_zip(temp_zip, platform_tools_dir):
                adb_path = self._get_adb_executable(platform_tools_dir)
                if adb_path and adb_path.exists():
                    return {
                        "available": True, 
                        "path": str(adb_path),
                        "source": "downloaded",
                        "dir": str(platform_tools_dir)
                    }
        
        return {"available": False, "error": "No se pudo descargar platform-tools"}

    # ========== SCRCPY EMBEBIDO ==========
    
    def setup_scrcpy(self) -> Dict:
        """Configurar scrcpy embebido - EVITA DESCARGAS REPETIDAS"""
        if self._scrcpy_cache and self._scrcpy_cache.get("available", False):
            return self._scrcpy_cache
            
        scrcpy_dir = self.tools_dir / "scrcpy"
        scrcpy_dir.mkdir(exist_ok=True)
        
        if not self._should_download_scrcpy(scrcpy_dir):
            scrcpy_exe = self._get_scrcpy_executable(scrcpy_dir)
            if scrcpy_exe and scrcpy_exe.exists():
                self._scrcpy_cache = {
                    "available": True, 
                    "path": str(scrcpy_exe),
                    "version": "existing",
                    "message": "Scrcpy ya disponible localmente"
                }
                return self._scrcpy_cache
        
        # Descargar scrcpy
        download_urls = {
            "windows": "https://github.com/Genymobile/scrcpy/releases/download/v1.24/scrcpy-win64-v1.24.zip",
            "linux": "https://github.com/Genymobile/scrcpy/releases/download/v1.24/scrcpy-server-v1.24",
            "darwin": "https://github.com/Genymobile/scrcpy/releases/download/v1.24/scrcpy-osx-v1.24.zip"
        }
        
        url = download_urls.get(self.system)
        if not url:
            self._scrcpy_cache = {"available": False, "error": f"Plataforma no soportada: {self.system}"}
            return self._scrcpy_cache
        
        self.logger.info("📥 Descargando scrcpy v1.24...")
        temp_zip = scrcpy_dir / "scrcpy_temp.zip"
        
        if self._download_file(url, temp_zip):
            if url.endswith('.zip'):
                if self._extract_zip(temp_zip, scrcpy_dir):
                    scrcpy_exe = self._get_scrcpy_executable(scrcpy_dir)
                    if scrcpy_exe and scrcpy_exe.exists():
                        self._scrcpy_cache = {
                            "available": True,
                            "path": str(scrcpy_exe),
                            "version": "v1.24",
                            "message": "Scrcpy descargado exitosamente"
                        }
                        return self._scrcpy_cache
        
        self._scrcpy_cache = {"available": False, "error": "No se pudo descargar scrcpy"}
        return self._scrcpy_cache

    # ========== MÉTODOS AUXILIARES ==========
    
    def _should_download_scrcpy(self, scrcpy_dir: Path) -> bool:
        """Determinar si es necesario descargar scrcpy"""
        if self._check_scrcpy_exists(scrcpy_dir):
            self.logger.info("✅ scrcpy ya existe y es funcional, omitiendo descarga")
            return False
            
        if scrcpy_dir.exists():
            self.logger.info("🔄 scrcpy existe pero no funciona, reinstalando...")
            try:
                shutil.rmtree(scrcpy_dir)
            except:
                pass
                
        return True
    
    def _check_scrcpy_exists(self, scrcpy_dir: Path) -> bool:
        """Verificar si scrcpy ya existe y es funcional"""
        scrcpy_exe = self._get_scrcpy_executable(scrcpy_dir)
        if not scrcpy_exe or not scrcpy_exe.exists():
            return False
            
        try:
            result = subprocess.run(
                [str(scrcpy_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _download_file(self, url: str, destination: Path) -> bool:
        """Descargar archivo desde URL"""
        try:
            self.logger.info(f"📥 Descargando: {url}")
            urllib.request.urlretrieve(url, destination)
            self.logger.info(f"✅ Descargado: {destination.name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error descargando {url}: {e}")
            return False
    
    def _extract_zip(self, zip_path: Path, extract_to: Path) -> bool:
        """Extraer archivo ZIP"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            if zip_path.exists():
                zip_path.unlink()
            self.logger.info(f"✅ Extraído: {zip_path.name} -> {extract_to}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo {zip_path}: {e}")
            return False
    
    def _get_scrcpy_executable(self, scrcpy_dir: Path) -> Optional[Path]:
        """Encontrar el ejecutable de scrcpy"""
        if self.system == "windows":
            exe_path = scrcpy_dir / "scrcpy.exe"
            if exe_path.exists():
                return exe_path
            
            for item in scrcpy_dir.iterdir():
                if item.is_dir():
                    sub_exe = item / "scrcpy.exe"
                    if sub_exe.exists():
                        return sub_exe
        else:
            exe_path = scrcpy_dir / "scrcpy"
            if exe_path.exists():
                self._make_executable(exe_path)
                return exe_path
        
        return None

    def _make_executable(self, file_path: Path):
        """Hacer archivo ejecutable (Linux/Mac)"""
        if self.system != "windows" and file_path.exists():
            os.chmod(file_path, 0o755)

    # ========== GESTIÓN COMPLETA DE HERRAMIENTAS ==========
    
    def check_all_tools(self) -> Dict:
        """Verificar estado de TODAS las herramientas incluyendo JDK"""
        self.logger.info("🛠️ Verificando herramientas embebidas...")
        
        tools_status = {}
        
        # JDK (NUEVO)
        self.logger.info("☕ Verificando JDK...")
        tools_status["jdk"] = self.setup_jdk()
        
        # APKSIGNER (NUEVO)
        self.logger.info("🔐 Verificando apksigner...")
        tools_status["apksigner"] = self.setup_apksigner()
        
        # AAPT
        self.logger.info("📦 Verificando AAPT...")
        tools_status["aapt"] = self.setup_aapt()
        
        # ADB
        self.logger.info("🔧 Verificando ADB...")
        tools_status["adb"] = self.setup_adb()
        
        # SCRCPY
        self.logger.info("📱 Verificando scrcpy...")
        tools_status["scrcpy"] = self.check_scrcpy_availability()
        
        # Resumen
        available_tools = [name for name, status in tools_status.items() if status.get("available", False)]
        self.logger.info(f"✅ Herramientas disponibles: {', '.join(available_tools) if available_tools else 'Ninguna'}")
        
        return tools_status
    
    def check_scrcpy_availability(self) -> Dict:
        """Verificar disponibilidad de scrcpy SIN descargar"""
        if self._scrcpy_cache:
            return self._scrcpy_cache
            
        scrcpy_dir = self.tools_dir / "scrcpy"
        scrcpy_exe = self._get_scrcpy_executable(scrcpy_dir)
        
        if scrcpy_exe and scrcpy_exe.exists() and self._check_scrcpy_exists(scrcpy_dir):
            return {
                "available": True,
                "path": str(scrcpy_exe),
                "exists": True,
                "message": "Scrcpy disponible localmente"
            }
        else:
            return {
                "available": False,
                "path": None,
                "exists": False,
                "message": "Scrcpy no encontrado, necesita descarga"
            }

    # ========== MÉTODOS PARA FIRMAR APKs ==========
    
    def can_sign_apks(self) -> bool:
        """Verificar si podemos firmar APKs (JDK + apksigner)"""
        tools_status = self.check_all_tools()
        
        jdk_ok = tools_status.get("jdk", {}).get("available", False)
        apksigner_ok = tools_status.get("apksigner", {}).get("available", False)
        
        return jdk_ok and apksigner_ok
    
    def get_signing_tools(self) -> Dict:
        """Obtener todas las herramientas necesarias para firmar APKs"""
        return {
            "jdk": self.setup_jdk(),
            "apksigner": self.setup_apksigner(),
            "can_sign": self.can_sign_apks()
        }
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Obtener ruta de una herramienta específica"""
        tools_status = self.check_all_tools()
        tool_status = tools_status.get(tool_name, {})
        
        if tool_status.get("available", False):
            return tool_status.get("path")
        return None
    
    def ensure_tools_available(self, required_tools: List[str]) -> bool:
        """Asegurar que las herramientas requeridas están disponibles"""
        tools_status = self.check_all_tools()
        
        for tool in required_tools:
            if not tools_status.get(tool, {}).get("available", False):
                self.logger.error(f"❌ Herramienta requerida no disponible: {tool}")
                return False
        
        self.logger.info("✅ Todas las herramientas requeridas están disponibles")
        return True

    def cleanup(self):
        """Limpiar archivos temporales"""
        try:
            for pattern in ["*.zip", "*.tar.gz"]:
                for temp_file in self.tools_dir.rglob(pattern):
                    if "temp" in temp_file.name:
                        temp_file.unlink()
        except Exception as e:
            self.logger.warning(f"No se pudieron limpiar archivos temporales: {e}")

# Función de conveniencia para uso rápido
def get_tool_manager() -> ToolManager:
    """Obtener instancia global del ToolManager"""
    if not hasattr(get_tool_manager, 'instance'):
        get_tool_manager.instance = ToolManager()
    return get_tool_manager.instance