import subprocess
from pathlib import Path
from typing import Dict, Tuple, List
import sys
import re
import os
import zipfile

class APKAnalyzer:
    def __init__(self, tool_detector, logger=None):
        self.tool_detector = tool_detector
        self.logger = logger
        
        # Inicializar componentes
        self._initialize_components()

    def _initialize_components(self):
        """Inicializar componentes de forma robusta"""
        try:
            from core.apk_signer import APKSigner
            self.apk_signer = APKSigner(self.logger)
        except ImportError:
            self.apk_signer = None
            
        try:
            from core.signature_verifier import SignatureVerifier
            self.signature_verifier = SignatureVerifier()
        except ImportError:
            self.signature_verifier = None
            
        try:
            from core.pci_dss_analyzer import PCI_DSS_Analyzer
            self.pci_analyzer = PCI_DSS_Analyzer()
        except ImportError:
            self.pci_analyzer = None

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            if level == "info":
                self.logger.log_info(message)
            elif level == "error":
                self.logger.log_error(message)
            elif level == "warning":
                self.logger.log_warning(message)

    def analizar_apk_completo(self, apk_path: Path, config: Dict = None) -> Dict[str, str]:
        """Analizar APK con múltiples métodos - MÉTODO PRINCIPAL"""
        self._log(f"🔍 INICIANDO ANÁLISIS COMPLETO: {apk_path.name}")
        resultados = {}
        
        if config is None:
            config = {}

        # Guardar ruta del APK para análisis posterior
        resultados["apk_path"] = str(apk_path)

        build_tools_path = config.get("build_tools")
        jdk_bin_path = config.get("jdk_bin")

        # ✅ PRIMERO: Verificar si las herramientas están disponibles
        herramientas_disponibles = self._verificar_herramientas_disponibles(build_tools_path)
        
        # ✅ SOLO EJECUTAR HERRAMIENTAS DISPONIBLES
        if herramientas_disponibles.get("aapt"):
            resultados["aapt"] = self._analizar_con_aapt(apk_path, build_tools_path)
        else:
            resultados["aapt"] = "aapt no disponible"
            
        if herramientas_disponibles.get("aapt2"):
            resultados["aapt2"] = self._analizar_con_aapt2(apk_path, build_tools_path)
        else:
            resultados["aapt2"] = "aapt2 no disponible"
            
        if herramientas_disponibles.get("apksigner"):
            resultados["apksigner"] = self._analizar_con_apksigner(apk_path, build_tools_path)
        else:
            resultados["apksigner"] = "apksigner no disponible"
            
        if herramientas_disponibles.get("jarsigner"):
            resultados["jarsigner"] = self._analizar_con_jarsigner(apk_path, jdk_bin_path)
        else:
            resultados["jarsigner"] = "jarsigner no disponible"

        # Siempre intentar análisis de archivos
        resultados["xmltree"] = self._analizar_con_xmltree(apk_path, build_tools_path)

        self._log("✅ Análisis completo finalizado")
        return resultados

    def parsear_informacion_apk(self, resultados_analisis: Dict) -> Dict:
        """Parsear información del APK usando múltiples fuentes - MEJORADO"""
        parsed_info = {
            "package": None, "version_name": None, "version_code": None,
            "target_sdk": None, "min_sdk": None, "permissions": [],
            "app_label": None, "debug_mode": False, "debuggable": False,
            "package_name": "", "app_name": "", "build_type": "Release",
            "file_path": resultados_analisis.get("apk_path", ""),
            "metodo_analisis": "standard",
            "native_libs": False,
            "architectures": []
        }

        # ✅ ESTRATEGIA 1: Intentar con aapt primero
        if resultados_analisis.get("aapt") and "error" not in resultados_analisis["aapt"].lower():
            aapt_info = self._parsear_aapt_badging_mejorado(resultados_analisis["aapt"])
            if aapt_info.get("package") or aapt_info.get("app_name"):
                parsed_info.update(aapt_info)
                parsed_info["metodo_analisis"] = "aapt"
                print(f"✅ Info extraída con aapt: {aapt_info.get('package')}")

        # ✅ ESTRATEGIA 2: Si aapt falla, usar aapt2
        if (not parsed_info.get("package") and not parsed_info.get("app_name") and 
            resultados_analisis.get("aapt2") and "error" not in resultados_analisis["aapt2"].lower()):
            aapt2_info = self._parsear_aapt_badging_mejorado(resultados_analisis["aapt2"])
            if aapt2_info.get("package") or aapt2_info.get("app_name"):
                parsed_info.update(aapt2_info)
                parsed_info["metodo_analisis"] = "aapt2"
                print(f"✅ Info extraída con aapt2: {aapt2_info.get('package')}")

        # ✅ ESTRATEGIA 3: Si aún no hay información, usar análisis de archivos
        if (not parsed_info.get("package") and not parsed_info.get("app_name") and 
            resultados_analisis.get("apk_path")):
            file_analysis = self._analizar_por_archivos_mejorado(Path(resultados_analisis["apk_path"]))
            if file_analysis.get("package") or file_analysis.get("app_name"):
                parsed_info.update(file_analysis)
                parsed_info["metodo_analisis"] = "fallback"
                print(f"✅ Info extraída con análisis de archivos: {file_analysis.get('app_name')}")

        # ✅ ESTRATEGIA 4: Extraer información del nombre del archivo como último recurso
        if (not parsed_info.get("package") and not parsed_info.get("app_name") and 
            resultados_analisis.get("apk_path")):
            filename_info = self._extraer_info_desde_nombre_archivo(Path(resultados_analisis["apk_path"]))
            if filename_info.get("app_name"):
                parsed_info.update(filename_info)
                parsed_info["metodo_analisis"] = "filename"
                print(f"✅ Info extraída desde nombre: {filename_info.get('app_name')}")

        # ✅ CORREGIR: Determinar build_type basado en debuggable
        if parsed_info.get("debuggable"):
            parsed_info["build_type"] = "Debug"
        else:
            parsed_info["build_type"] = "Release"

        # ✅ Asegurar que package_name esté sincronizado
        if parsed_info.get("package"):
            parsed_info["package_name"] = parsed_info["package"]

        # ✅ DEBUG: Mostrar qué información se encontró
        print(f"🔍 RESUMEN ANÁLISIS:")
        print(f"   Package: {parsed_info.get('package')}")
        print(f"   App: {parsed_info.get('app_name')}")
        print(f"   Versión: {parsed_info.get('version_name')}")
        print(f"   Target SDK: {parsed_info.get('target_sdk')}")
        print(f"   Min SDK: {parsed_info.get('min_sdk')}")
        print(f"   Método: {parsed_info.get('metodo_analisis')}")
        print(f"   Build Type: {parsed_info.get('build_type')}")

        return parsed_info

    def _parsear_aapt_badging_mejorado(self, aapt_output: str) -> Dict:
        """Parsear salida de aapt badging - MEJORADO para APKs problemáticos"""
        parsed = {
            "package": None, "version_name": None, "version_code": None,
            "target_sdk": None, "min_sdk": None, "permissions": [],
            "app_label": None, "debug_mode": False, "debuggable": False,
            "package_name": "", "app_name": ""
        }

        if not aapt_output or "error" in aapt_output.lower():
            return parsed

        lines = aapt_output.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # ✅ BUSCAR INFORMACIÓN INCLUSO EN LÍNEAS CON ERRORES
            try:
                if line.startswith("package:"):
                    self._parse_package_line_mejorado(line, parsed)
                elif line.startswith("targetSdkVersion:"):
                    parsed["target_sdk"] = self._extract_value_mejorado(line, "targetSdkVersion:")
                elif line.startswith("sdkVersion:"):
                    parsed["min_sdk"] = self._extract_value_mejorado(line, "sdkVersion:")
                elif line.startswith("uses-permission:"):
                    self._parse_permission_line_mejorado(line, parsed)
                elif line.startswith("application-label:") and not parsed["app_label"]:
                    parsed["app_label"] = self._extract_value_mejorado(line, "application-label:")
                    parsed["app_name"] = self._extract_value_mejorado(line, "application-label:")
                elif line.startswith("application-label-") and not parsed["app_label"]:
                    # Tomar cualquier application-label como fallback
                    parsed["app_label"] = self._extract_value_mejorado(line.split(':', 1)[1])
                    parsed["app_name"] = self._extract_value_mejorado(line.split(':', 1)[1])
                
                # ✅ DETECTAR DEBUGGABLE INCLUSO CON ERRORES
                if 'application-debuggable' in line.lower():
                    parsed["debug_mode"] = True
                    parsed["debuggable"] = True
                elif 'android:debuggable' in line.lower():
                    if '="true"' in line.lower() or '(0xffffffff)' in line:
                        parsed["debug_mode"] = True
                        parsed["debuggable"] = True
                
            except Exception as e:
                # Continuar incluso si hay errores en una línea
                continue

        parsed["package_name"] = parsed["package"]
        return parsed

    def _parse_package_line_mejorado(self, line: str, parsed: Dict):
        """Parsear línea de package - MEJORADO para errores"""
        try:
            # Método 1: Buscar con comillas simples
            name_match = re.search(r"name='([^']*)'", line)
            if name_match:
                parsed["package"] = name_match.group(1)
                parsed["package_name"] = name_match.group(1)

            # Método 2: Buscar con comillas dobles
            if not parsed["package"]:
                name_match = re.search(r'name="([^"]*)"', line)
                if name_match:
                    parsed["package"] = name_match.group(1)
                    parsed["package_name"] = name_match.group(1)

            # Buscar versionCode
            vc_match = re.search(r"versionCode='([^']*)'", line)
            if vc_match:
                parsed["version_code"] = vc_match.group(1)
            else:
                vc_match = re.search(r'versionCode="([^"]*)"', line)
                if vc_match:
                    parsed["version_code"] = vc_match.group(1)

            # Buscar versionName
            vn_match = re.search(r"versionName='([^']*)'", line)
            if vn_match:
                parsed["version_name"] = vn_match.group(1)
            else:
                vn_match = re.search(r'versionName="([^"]*)"', line)
                if vn_match:
                    parsed["version_name"] = vn_match.group(1)
                    
        except Exception:
            pass

    def _analizar_por_archivos_mejorado(self, apk_path: Path) -> Dict:
        """Análisis mejorado basado en archivos del APK"""
        info = {}
        
        try:
            if not apk_path.exists():
                return info
                
            with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                archivos = apk_zip.namelist()
                
                # ✅ DETECTAR LIBRERÍAS NATIVAS
                so_files = [f for f in archivos if f.endswith('.so')]
                if so_files:
                    info['native_libs'] = True
                    architectures = list(set([f.split('/')[-2] for f in so_files if 'lib/' in f and len(f.split('/')) > 2]))
                    info['architectures'] = architectures if architectures else ['arm64-v8a', 'armeabi-v7a']  # Valores por defecto comunes
                
                # ✅ BUSCAR APP_NAME EN STRINGS.XML
                for archivo in archivos:
                    if 'res/values/' in archivo and archivo.endswith('strings.xml'):
                        try:
                            with apk_zip.open(archivo) as f:
                                contenido = f.read().decode('utf-8', errors='ignore')
                                
                                # Buscar app_name
                                app_name_match = re.search(r'<string name="app_name">([^<]+)</string>', contenido)
                                if app_name_match and not info.get('app_name'):
                                    info['app_name'] = app_name_match.group(1).strip()
                                    info['app_label'] = app_name_match.group(1).strip()
                                
                                # Buscar nombre del paquete en strings
                                package_match = re.search(r'<string name="package_name">([^<]+)</string>', contenido)
                                if package_match and not info.get('package'):
                                    info['package'] = package_match.group(1).strip()
                                    info['package_name'] = package_match.group(1).strip()
                                    
                        except Exception:
                            continue
                
                # ✅ INTENTAR EXTRAER INFORMACIÓN DEL MANIFEST DIRECTAMENTE
                if 'AndroidManifest.xml' in archivos:
                    info['manifest_present'] = True
                    # Si tenemos manifest pero no package, intentar deducir del nombre del archivo
                    if not info.get('package'):
                        package_from_name = self._deducir_package_desde_nombre(apk_path.name)
                        if package_from_name:
                            info['package'] = package_from_name
                            info['package_name'] = package_from_name
                
                # ✅ DETECTAR MODO DEBUG POR ARCHIVOS
                debug_indicators = [
                    any('debug' in f.lower() for f in archivos),
                    any('dev' in f.lower() for f in archivos),
                    any('test' in f.lower() for f in archivos),
                ]
                
                release_indicators = [
                    any('release' in f.lower() for f in archivos),
                    any('prod' in f.lower() for f in archivos),
                ]
                
                if sum(debug_indicators) > sum(release_indicators):
                    info['build_type'] = 'Debug'
                    info['debuggable'] = True
                else:
                    info['build_type'] = 'Release'
                    
        except Exception as e:
            print(f"⚠️ Error en análisis de archivos: {e}")
        
        return info

    def _extraer_info_desde_nombre_archivo(self, apk_path: Path) -> Dict:
        """Extraer información básica desde el nombre del archivo"""
        info = {}
        filename = apk_path.stem  # Sin extensión
        
        # Patrones comunes en nombres de APK
        patterns = [
            r'([a-zA-Z0-9._-]+)-debug-(\d+\.\d+[a-z]*)\.?(\d*)',  # app-debug-1.0json.36
            r'([a-zA-Z0-9._-]+)-release-(\d+\.\d+[a-z]*)\.?(\d*)', # app-release-1.0.0
            r'([a-zA-Z0-9._-]+)-(\d+\.\d+[a-z]*)\.?(\d*)',        # app-1.0.0
            r'([a-zA-Z0-9._-]+)_v?(\d+\.\d+[a-z]*)',              # app_v1.0
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                app_name = match.group(1)
                version = match.group(2)
                
                # Limpiar el nombre de la app
                app_name = app_name.replace('-', ' ').replace('_', ' ').title()
                
                info['app_name'] = app_name
                info['app_label'] = app_name
                info['version_name'] = version
                
                # Si el nombre parece un package (contiene puntos)
                if '.' in app_name and len(app_name) > 5:
                    info['package'] = app_name
                    info['package_name'] = app_name
                    
                break
        
        # Si no se encontró patrón, usar el nombre del archivo como app_name
        if not info.get('app_name'):
            app_name = filename.replace('-debug', '').replace('-release', '').replace('-unsigned', '')
            app_name = app_name.replace('-', ' ').replace('_', ' ').title()
            info['app_name'] = app_name
            info['app_label'] = app_name
        
        return info

    def _deducir_package_desde_nombre(self, filename: str) -> str:
        """Intentar deducir el package name desde el nombre del archivo"""
        # Remover extensiones y palabras comunes
        clean_name = filename.replace('.apk', '').replace('-debug', '').replace('-release', '').replace('-unsigned', '')
        
        # Si el nombre tiene estructura de package (contiene puntos)
        if '.' in clean_name and len(clean_name) > 5:
            return clean_name
        
        # Intentar convertir a formato de package
        words = re.findall(r'[a-zA-Z0-9]+', clean_name)
        if len(words) >= 2:
            # Tomar las últimas 2-3 palabras como package
            package_parts = words[-3:] if len(words) >= 3 else words[-2:]
            return '.'.join(package_parts).lower()
        
        return None

    def _extract_value_mejorado(self, line: str, prefix: str = "") -> str:
        """Extraer valor - MEJORADO para manejar errores"""
        try:
            if prefix:
                # Buscar después del prefix
                if prefix in line:
                    parts = line.split(prefix, 1)
                    if len(parts) > 1:
                        value = parts[1].strip()
                        # Limpiar comillas y espacios
                        value = value.strip("'\" \t")
                        return value
            return line.strip().strip("'\"")
        except Exception:
            return ""

    # Los métodos existentes se mantienen igual...
    def _verificar_herramientas_disponibles(self, build_tools_path: str = None) -> Dict[str, bool]:
        """Verificar qué herramientas están disponibles"""
        herramientas = {
            "aapt": False,
            "aapt2": False, 
            "apksigner": False,
            "jarsigner": False
        }
        
        # Verificar aapt
        aapt_path = self._encontrar_aapt(build_tools_path)
        herramientas["aapt"] = aapt_path is not None
        
        # Verificar aapt2
        aapt2_path = self._encontrar_aapt2(build_tools_path)
        herramientas["aapt2"] = aapt2_path is not None
        
        # Verificar apksigner
        apksigner_path = self._encontrar_apksigner(build_tools_path)
        herramientas["apksigner"] = apksigner_path is not None
        
        # Verificar jarsigner
        jarsigner_path = self._encontrar_jarsigner()
        herramientas["jarsigner"] = jarsigner_path is not None
        
        self._log(f"🔧 Herramientas disponibles: {[k for k, v in herramientas.items() if v]}")
        return herramientas

    def _encontrar_aapt(self, build_tools_path: str = None) -> Path:
        """Encontrar ruta de aapt"""
        # 1. Buscar en build_tools_path especificado
        if build_tools_path:
            build_path = Path(build_tools_path)
            aapt_bin = build_path / ("aapt.exe" if sys.platform.startswith("win") else "aapt")
            if aapt_bin.exists():
                return aapt_bin
        
        # 2. Buscar en build-tools automáticamente
        build_tools_dirs = self._encontrar_build_tools_dirs()
        for build_dir in build_tools_dirs:
            aapt_bin = build_dir / ("aapt.exe" if sys.platform.startswith("win") else "aapt")
            if aapt_bin.exists():
                return aapt_bin
                
        # 3. Buscar en PATH
        return self._buscar_herramienta_en_path("aapt")

    def _encontrar_aapt2(self, build_tools_path: str = None) -> Path:
        """Encontrar ruta de aapt2"""
        if build_tools_path:
            build_path = Path(build_tools_path)
            aapt2_bin = build_path / ("aapt2.exe" if sys.platform.startswith("win") else "aapt2")
            if aapt2_bin.exists():
                return aapt2_bin
                
        build_tools_dirs = self._encontrar_build_tools_dirs()
        for build_dir in build_tools_dirs:
            aapt2_bin = build_dir / ("aapt2.exe" if sys.platform.startswith("win") else "aapt2")
            if aapt2_bin.exists():
                return aapt2_bin
                
        return self._buscar_herramienta_en_path("aapt2")

    def _encontrar_apksigner(self, build_tools_path: str = None) -> Path:
        """Encontrar ruta de apksigner"""
        if build_tools_path:
            build_path = Path(build_tools_path)
            candidates = [
                build_path / "apksigner.bat",
                build_path / "apksigner",
                build_path / "apksigner.jar",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
                    
        build_tools_dirs = self._encontrar_build_tools_dirs()
        for build_dir in build_tools_dirs:
            candidates = [
                build_dir / "apksigner.bat",
                build_dir / "apksigner", 
                build_dir / "apksigner.jar",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
                    
        return self._buscar_herramienta_en_path("apksigner")

    def _encontrar_jarsigner(self) -> Path:
        """Encontrar ruta de jarsigner"""
        # Buscar en JAVA_HOME primero
        java_home = os.environ.get('JAVA_HOME')
        if java_home:
            java_bin = Path(java_home) / "bin"
            jarsigner_bin = java_bin / ("jarsigner.exe" if sys.platform.startswith("win") else "jarsigner")
            if jarsigner_bin.exists():
                return jarsigner_bin
                
        return self._buscar_herramienta_en_path("jarsigner")

    def _encontrar_build_tools_dirs(self) -> List[Path]:
        """Encontrar directorios de build-tools automáticamente"""
        sdk_locations = [
            Path.home() / "AppData/Local/Android/Sdk/build-tools",
            Path.home() / "Android/Sdk/build-tools",
            Path("/usr/lib/android-sdk/build-tools"),
            Path("/opt/android-sdk/build-tools"),
        ]
        
        build_tools_dirs = []
        for sdk_location in sdk_locations:
            if sdk_location.exists():
                # Obtener todas las versiones de build-tools
                for item in sdk_location.iterdir():
                    if item.is_dir():
                        build_tools_dirs.append(item)
                        
        return build_tools_dirs

    def _buscar_herramienta_en_path(self, nombre_herramienta: str) -> Path:
        """Buscar herramienta en el PATH del sistema"""
        try:
            if sys.platform.startswith("win"):
                nombre_herramienta += ".exe"
            
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                tool_path = Path(path_dir) / nombre_herramienta
                if tool_path.exists():
                    return tool_path
            return None
        except Exception:
            return None

    def _ejecutar_herramienta(self, command_path: Path, args: list, cwd: Path = None, timeout: int = 30) -> Tuple[int, str]:
        try:
            if not command_path or not command_path.exists():
                return 1, f"Herramienta no encontrada: {command_path}"
                
            cmd = [str(command_path)] + args
            
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="ignore",
            )
            
            return proc.returncode, proc.stdout + proc.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"Tiempo de espera agotado ({timeout}s) ejecutando: {command_path.name}"
            self._log(error_msg, "error")
            return 1, error_msg
            
        except FileNotFoundError:
            error_msg = f"No se encontró el binario: {command_path}"
            self._log(error_msg, "error")
            return 1, error_msg
            
        except Exception as e:
            error_msg = f"Error ejecutando {command_path.name}: {str(e)}"
            self._log(error_msg, "error")
            return 1, error_msg

    def _analizar_con_aapt(self, apk_path: Path, build_tools_path: str = None) -> str:
        """Analizar con aapt"""
        aapt_bin = self._encontrar_aapt(build_tools_path)
        
        if not aapt_bin:
            return "❌ ERROR: 'aapt' no encontrado en el sistema"
        
        self._log(f"Analizando APK con aapt: {apk_path.name}")
        rc, output = self._ejecutar_herramienta(aapt_bin, ["dump", "badging", str(apk_path)])
        
        if rc != 0:
            return f"❌ ERROR ejecutando aapt: {output}"
            
        return output

    def _analizar_con_aapt2(self, apk_path: Path, build_tools_path: str = None) -> str:
        """Analizar con aapt2"""
        aapt2_bin = self._encontrar_aapt2(build_tools_path)
        
        if not aapt2_bin:
            return "aapt2 no encontrado en el sistema"
        
        self._log(f"Analizando APK con aapt2: {apk_path.name}")
        rc, output = self._ejecutar_herramienta(aapt2_bin, ["dump", "badging", str(apk_path)])
        
        if rc != 0:
            return f"Error ejecutando aapt2: {output}"
            
        return output

    def _analizar_con_xmltree(self, apk_path: Path, build_tools_path: str = None) -> str:
        """Analizar AndroidManifest.xml"""
        aapt2_bin = self._encontrar_aapt2(build_tools_path)
        
        if aapt2_bin:
            self._log(f"Analizando AndroidManifest.xml con aapt2: {apk_path.name}")
            rc, output = self._ejecutar_herramienta(aapt2_bin, ["dump", "xmltree", str(apk_path), "AndroidManifest.xml"])
            if rc == 0:
                return output
        
        return self._extraer_manifest_manualmente(apk_path)

    def _extraer_manifest_manualmente(self, apk_path: Path) -> str:
        """Extraer AndroidManifest.xml manualmente"""
        try:
            with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                if 'AndroidManifest.xml' in apk_zip.namelist():
                    return "AndroidManifest.xml encontrado en el APK"
                else:
                    return "AndroidManifest.xml no encontrado en el APK"
        except Exception as e:
            return f"Error extrayendo manifest: {str(e)}"

    def _analizar_con_apksigner(self, apk_path: Path, build_tools_path: str = None) -> str:
        """Analizar firma con apksigner"""
        apksigner_bin = self._encontrar_apksigner(build_tools_path)
        
        if not apksigner_bin:
            return "apksigner no encontrado en el sistema"
        
        self._log(f"Verificando firma con apksigner: {apk_path.name}")
        
        if apksigner_bin.name.endswith('.jar'):
            rc, output = self._ejecutar_herramienta(
                Path("java"), ["-jar", str(apksigner_bin), "verify", "--verbose", "--print-certs", str(apk_path)]
            )
        else:
            rc, output = self._ejecutar_herramienta(
                apksigner_bin, ["verify", "--verbose", "--print-certs", str(apk_path)]
            )
        
        if rc != 0:
            return f"Error ejecutando apksigner: {output}"
            
        return output

    def _analizar_con_jarsigner(self, apk_path: Path, jdk_bin_path: str = None) -> str:
        """Analizar firma con jarsigner"""
        jarsigner_bin = self._encontrar_jarsigner()
        
        if not jarsigner_bin:
            return "jarsigner no encontrado en el sistema"
        
        self._log(f"Verificando firma con jarsigner: {apk_path.name}")
        rc, output = self._ejecutar_herramienta(
            jarsigner_bin, ["-verify", "-verbose", "-certs", str(apk_path)]
        )
        
        if rc != 0:
            return f"Error ejecutando jarsigner: {output}"
            
        return output

    def parsear_informacion_firma(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        """Parsear información de firma"""
        if self.signature_verifier:
            return self.signature_verifier.parsear_info_firma(apksigner_output, jarsigner_output)
        else:
            return {
                "company": "Desconocida", "is_valid": False,
                "signature_versions": [], "integrity_ok": False,
                "cert_hash": "No disponible", "certificate_info": "",
                "signature_type": "No firmado",
            }

    def firmar_apk(self, apk_path: Path, jks_path: Path, password: str, build_tools_path: str, alias: str = None) -> Tuple[bool, str]:
        """Firmar APK"""
        if self.apk_signer:
            return self.apk_signer.firmar_apk(apk_path, jks_path, password, build_tools_path, alias)
        else:
            return False, "APKSigner no disponible"

    def verificar_firma_apk(self, apk_path: Path, build_tools_path: str) -> Tuple[bool, str]:
        """Verificar firma APK"""
        if self.apk_signer:
            return self.apk_signer.verificar_firma(apk_path, build_tools_path)
        else:
            return False, "APKSigner no disponible"

    def ejecutar_analisis_pci_dss(self, parsed_info: Dict, signature_info: Dict) -> Dict:
        """Ejecutar análisis PCI DSS"""
        if self.pci_analyzer:
            return self.pci_analyzer.analizar_apk(parsed_info, signature_info)
        else:
            return {"error": "PCI DSS Analyzer no disponible"}