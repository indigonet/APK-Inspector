import subprocess
from pathlib import Path
from typing import Dict, Tuple, List
import sys
import re
import os

print("🔄 Iniciando carga de APKAnalyzer...")

# DIAGNÓSTICO: Verificar estructura de archivos
current_dir = Path(__file__).parent
print(f"📁 Directorio actual: {current_dir}")

# Listar archivos en core/
try:
    archivos_core = list(current_dir.glob("*.py"))
    print(f"📄 Archivos en core/: {[f.name for f in archivos_core]}")
except Exception as e:
    print(f"❌ Error listando archivos: {e}")

# ESTRATEGIA DEFINITIVA: Importación robusta
APK_SIGNER_IMPORTADO = False
RealAPKSigner = None
RealSignatureVerifier = None

# Intentar importación directa del APKSigner real
try:
    # Verificar si el archivo existe físicamente
    apk_signer_path = current_dir / "apk_signer.py"
    if apk_signer_path.exists():
        print(f"✅ apk_signer.py encontrado en: {apk_signer_path}")
        
        # Importar directamente
        import importlib.util
        spec = importlib.util.spec_from_file_location("apk_signer", apk_signer_path)
        apk_signer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(apk_signer_module)
        RealAPKSigner = apk_signer_module.APKSigner
        APK_SIGNER_IMPORTADO = True
        print("🎉 APKSigner REAL importado directamente desde archivo")
    else:
        print(f"❌ apk_signer.py NO encontrado en: {apk_signer_path}")
        
except Exception as e:
    print(f"❌ Error importando APKSigner directo: {e}")

# Si falla la importación directa, intentar métodos convencionales
if not APK_SIGNER_IMPORTADO:
    try:
        from core.apk_signer import APKSigner as RealAPKSigner
        APK_SIGNER_IMPORTADO = True
        print("✅ APKSigner importado via core.apk_signer")
    except ImportError as e:
        print(f"❌ Error importando via core.apk_signer: {e}")

if not APK_SIGNER_IMPORTADO:
    try:
        from .apk_signer import APKSigner as RealAPKSigner
        APK_SIGNER_IMPORTADO = True
        print("✅ APKSigner importado via .apk_signer")
    except ImportError as e:
        print(f"❌ Error importando via .apk_signer: {e}")

# Importar SignatureVerifier
try:
    from core.signature_verifier import SignatureVerifier as RealSignatureVerifier
    print("✅ SignatureVerifier importado")
except ImportError:
    try:
        from .signature_verifier import SignatureVerifier as RealSignatureVerifier
        print("✅ SignatureVerifier importado (relativo)")
    except ImportError:
        print("❌ SignatureVerifier no disponible")
        class RealSignatureVerifier:
            def parsear_info_firma(self, apksigner_output, jarsigner_output):
                return {
                    "company": "Desconocida", "is_valid": False,
                    "signature_versions": [], "integrity_ok": False,
                    "cert_hash": "No disponible", "certificate_info": "",
                    "signature_type": "No firmado",
                }

# Importar PCI_DSS_Analyzer
try:
    from core.pci_dss_analyzer import PCI_DSS_Analyzer
    print("✅ PCI_DSS_Analyzer importado")
except ImportError:
    print("❌ PCI_DSS_Analyzer no disponible")
    class PCI_DSS_Analyzer:
        def analizar_apk(self, parsed_info, signature_info):
            return {"error": "PCI DSS Analyzer no disponible"}

# CLASE FALLBACK SOLO SI ES NECESARIO
if not APK_SIGNER_IMPORTADO or RealAPKSigner is None:
    print("🚨 CREANDO CLASE FALLBACK PARA APKSigner")
    
    class FallbackAPKSigner:
        def __init__(self, logger=None):
            self.logger = logger
            print("🚨 APKSigner FALLBACK inicializado - EL REAL NO SE PUDO IMPORTAR")
        
        # En APKAnalyzer, modificar el método firmar_apk:
        def firmar_apk(self, apk_path: Path, jks_path: Path, password: str, build_tools_path: str, alias: str = None, parent_window=None) -> Tuple[bool, str]:
            self._log(f"Iniciando proceso de firma para: {apk_path.name}")
            return self.apk_signer.firmar_apk(apk_path, jks_path, password, build_tools_path, alias, parent_window)
        
        def verificar_firma(self, apk_path, build_tools_path):
            return False, "APKSigner no disponible"
    
    RealAPKSigner = FallbackAPKSigner

print(f"🎯 ESTADO FINAL: APK_SIGNER_IMPORTADO={APK_SIGNER_IMPORTADO}, RealAPKSigner={RealAPKSigner}")

class APKAnalyzer:
    def __init__(self, tool_detector, logger=None):
        self.tool_detector = tool_detector
        self.logger = logger
        
        print(f"🔧 Inicializando APKAnalyzer...")
        print(f"🔧 Logger disponible: {logger is not None}")
        print(f"🔧 APKSigner a usar: {RealAPKSigner}")
        
        # Inicializar componentes
        self.signature_verifier = RealSignatureVerifier()
        self.apk_signer = RealAPKSigner(logger)
        self.pci_analyzer = PCI_DSS_Analyzer()
        
        print(f"✅ APKAnalyzer inicializado COMPLETAMENTE")
        print(f"✅ APKSigner instanciado: {type(self.apk_signer)}")
        print(f"✅ Tiene método firmar_apk: {hasattr(self.apk_signer, 'firmar_apk')}")

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            if level == "info":
                self.logger.log_info(message)
            elif level == "error":
                self.logger.log_error(message)
            elif level == "warning":
                self.logger.log_warning(message)
        else:
            print(f"[APKAnalyzer {level.upper()}] {message}")

    def ejecutar_herramienta(self, command_path: Path, args: list, cwd: Path = None, timeout: int = 30) -> Tuple[int, str]:
        try:
            cmd = [str(command_path)] + args
            self._log(f"Ejecutando: {' '.join(cmd)}")
            
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="ignore",
            )
            
            self._log(f"Comando completado con código: {proc.returncode}")
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

    def analizar_con_aapt(self, apk_path: Path, build_tools_path: str) -> str:
        if not build_tools_path:
            return "build-tools no configurado"

        build_path = Path(build_tools_path)
        aapt_bin = build_path / ("aapt.exe" if sys.platform.startswith("win") else "aapt")

        if not aapt_bin.exists():
            return f"aapt no encontrado en: {build_path}"

        self._log(f"Analizando APK con aapt: {apk_path.name}")
        rc, output = self.ejecutar_herramienta(aapt_bin, ["dump", "badging", str(apk_path)])
        return output

    def analizar_con_apksigner(self, apk_path: Path, build_tools_path: str) -> str:
        if not build_tools_path:
            return "build-tools no configurado"

        build_path = Path(build_tools_path)
        apksigner_candidates = [
            build_path / "apksigner.bat",
            build_path / "apksigner",
            build_path / "apksigner.jar",
        ]

        apksigner_bin = None
        for candidate in apksigner_candidates:
            if candidate.exists():
                apksigner_bin = candidate
                break

        if not apksigner_bin:
            return "apksigner no encontrado en build-tools"

        self._log(f"Verificando firma con apksigner: {apk_path.name}")
        rc, output = self.ejecutar_herramienta(
            apksigner_bin, ["verify", "--verbose", "--print-certs", str(apk_path)]
        )
        return output

    def analizar_con_jarsigner(self, apk_path: Path, jdk_bin_path: str) -> str:
        if not jdk_bin_path:
            return "JDK bin no configurado"

        jdk_bin = Path(jdk_bin_path)
        jarsigner_bin = jdk_bin / ("jarsigner.exe" if sys.platform.startswith("win") else "jarsigner")

        if not jarsigner_bin.exists():
            return f"jarsigner no encontrado en: {jdk_bin}"

        self._log(f"Verificando firma con jarsigner: {apk_path.name}")
        rc, output = self.ejecutar_herramienta(
            jarsigner_bin, ["-verify", "-verbose", "-certs", str(apk_path)]
        )
        return output

    def analizar_apk_completo(self, apk_path: Path, config: Dict) -> Dict[str, str]:
        self._log(f"Iniciando análisis completo del APK: {apk_path.name}")
        resultados = {}

        resultados["aapt"] = self.analizar_con_aapt(apk_path, config.get("build_tools"))
        resultados["apksigner"] = self.analizar_con_apksigner(apk_path, config.get("build_tools"))
        resultados["jarsigner"] = self.analizar_con_jarsigner(apk_path, config.get("jdk_bin"))

        self._log("Análisis completo finalizado")
        return resultados

    def parsear_aapt_badging(self, aapt_output: str) -> Dict:
        parsed = {
            "package": None, "version_name": None, "version_code": None,
            "target_sdk": None, "native_codes": None, "permissions": [],
            "app_label": None, "debug_mode": False, "debuggable": False,
            "package_name": "", "app_name": "", "features": [],
            "sdk_versions": {}, "allow_backup": True
        }
    
        if not aapt_output or "error" in aapt_output.lower():
            self._log("AAPT output vacío o con error", "warning")
            return parsed
            
        lines = aapt_output.splitlines()
    
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("package:"):
                self._parse_package_line(line, parsed)
            elif line.startswith("targetSdkVersion:"):
                parsed["target_sdk"] = self._extract_value(line, "targetSdkVersion:")
                parsed["sdk_versions"]["target"] = self._extract_value(line, "targetSdkVersion:")
            elif line.startswith("sdkVersion:"):
                parsed["sdk_versions"]["min"] = self._extract_value(line, "sdkVersion:")
            elif line.startswith("native-code:"):
                parsed["native_codes"] = self._extract_value(line, "native-code:")
            elif line.startswith("uses-permission:"):
                self._parse_permission_line(line, parsed)
            elif line.startswith("uses-feature:"):
                self._parse_feature_line(line, parsed)
            elif line.startswith("application-label:") and not parsed["app_label"]:
                parsed["app_label"] = self._extract_value(line, "application-label:")
                parsed["app_name"] = self._extract_value(line, "application-label:")
            elif line.startswith("application-label-") and not parsed["app_label"]:
                parsed["app_label"] = self._extract_value(line.split(':', 1)[1])
                parsed["app_name"] = self._extract_value(line.split(':', 1)[1])
            
            if 'application-debuggable' in line.lower():
                parsed["debug_mode"] = True
                parsed["debuggable"] = True
            
            elif 'android:debuggable' in line.lower():
                if '="true"' in line.lower():
                    parsed["debug_mode"] = True
                    parsed["debuggable"] = True
                elif '="false"' in line.lower():
                    parsed["debug_mode"] = False
                    parsed["debuggable"] = False
            
            elif 'debuggable(0x' in line.lower():
                if '0xffffffff' in line:
                    parsed["debug_mode"] = True
                    parsed["debuggable"] = True
            
            elif "allowbackup" in line.lower():
                allow_backup_match = re.search(r'allowBackup="(true|false)"', line)
                if allow_backup_match:
                    parsed["allow_backup"] = allow_backup_match.group(1).lower() == 'true'
    
        parsed["package_name"] = parsed["package"]
        
        self._log(f"APK parseado - Package: {parsed['package']}, Debug: {parsed['debug_mode']}")
        return parsed

    def _parse_package_line(self, line: str, parsed: Dict):
        try:
            name_start = line.find("name='")
            if name_start != -1:
                name_end = line.find("'", name_start + 6)
                if name_end != -1:
                    parsed["package"] = line[name_start + 6 : name_end]
                    parsed["package_name"] = line[name_start + 6 : name_end]

            vc_start = line.find("versionCode='")
            if vc_start != -1:
                vc_end = line.find("'", vc_start + 13)
                if vc_end != -1:
                    parsed["version_code"] = line[vc_start + 13 : vc_end]

            vn_start = line.find("versionName='")
            if vn_start != -1:
                vn_end = line.find("'", vn_start + 13)
                if vn_end != -1:
                    parsed["version_name"] = line[vn_start + 13 : vn_end]

        except Exception:
            pass

    def _parse_permission_line(self, line: str, parsed: Dict):
        try:
            perm_start = line.find("name='")
            if perm_start != -1:
                perm_end = line.find("'", perm_start + 6)
                if perm_end != -1:
                    permission = line[perm_start + 6 : perm_end]
                    parsed["permissions"].append(permission)
        except Exception:
            pass

    def _parse_feature_line(self, line: str, parsed: Dict):
        try:
            feat_start = line.find("name='")
            if feat_start != -1:
                feat_end = line.find("'", feat_start + 6)
                if feat_end != -1:
                    feature = line[feat_start + 6 : feat_end]
                    parsed["features"].append(feature)
        except Exception:
            pass

    def _extract_value(self, line: str, prefix: str = "") -> str:
        try:
            if prefix:
                line = line.split(prefix, 1)[1].strip()
            return line.strip().strip("'\"")
        except Exception:
            return ""

    def parsear_informacion_firma(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        self._log("Parseando información de firma")
        signature_info = self.signature_verifier.parsear_info_firma(apksigner_output, jarsigner_output)
        
        if signature_info.get('cert_hash') == 'No disponible':
            signature_info = self._parsear_apksigner_manual(apksigner_output, signature_info)
            
        return signature_info

    def _parsear_apksigner_manual(self, apksigner_output: str, base_info: Dict) -> Dict:
        lines = apksigner_output.split('\n')
        
        cert_hash = base_info.get('cert_hash', 'No disponible')
        company = base_info.get('company', 'Desconocida')
        cert_info = base_info.get('certificate_info', '')
        
        for line in lines:
            line = line.strip()
            
            if 'SHA-256 digest:' in line and cert_hash == 'No disponible':
                parts = line.split('SHA-256 digest:')
                if len(parts) > 1:
                    cert_hash = parts[1].strip()
            
            elif 'certificate DN:' in line:
                parts = line.split('certificate DN:')
                if len(parts) > 1:
                    dn = parts[1].strip()
                    cert_info = dn
                    if 'O=' in dn:
                        org_parts = dn.split('O=')
                        if len(org_parts) > 1:
                            company = org_parts[1].split(',')[0].strip()
            
            elif 'key algorithm:' in line and not cert_info:
                parts = line.split('key algorithm:')
                if len(parts) > 1:
                    key_algo = parts[1].strip()
                    cert_info = f"Algoritmo: {key_algo}"
            
            elif 'key size (bits):' in line and cert_info:
                parts = line.split('key size (bits):')
                if len(parts) > 1:
                    key_size = parts[1].strip()
                    cert_info += f" | Tamaño clave: {key_size} bits"
        
        if cert_hash != 'No disponible':
            base_info['cert_hash'] = cert_hash
        if company != 'Desconocida':
            base_info['company'] = company
        if cert_info:
            base_info['certificate_info'] = cert_info
            
        return base_info

    def firmar_apk(self, apk_path: Path, jks_path: Path, password: str, build_tools_path: str, alias: str = None) -> Tuple[bool, str]:
        self._log(f"🎯 LLAMANDO A FIRMAR APK - APKSigner tipo: {type(self.apk_signer)}")
        return self.apk_signer.firmar_apk(apk_path, jks_path, password, build_tools_path, alias)

    def verificar_firma_apk(self, apk_path: Path, build_tools_path: str) -> Tuple[bool, str]:
        self._log(f"Verificando firma de: {apk_path.name}")
        return self.apk_signer.verificar_firma(apk_path, build_tools_path)

    def _es_informacion_faltante(self, parsed_info):
        campos = ['package', 'app_label', 'version_name', 'version_code', 'target_sdk']
        vacios = 0
        
        for campo in campos:
            valor = parsed_info.get(campo)
            if not valor or valor in ['N/A', 'None', 'None (None)', '']:
                vacios += 1
        
        return vacios >= 2

    def ejecutar_analisis_pci_dss(self, parsed_info: Dict, signature_info: Dict) -> Dict:
        try:
            self._log("Ejecutando análisis PCI DSS")
            pci_analysis = self.pci_analyzer.analizar_apk(parsed_info, signature_info)
            return pci_analysis
        except Exception as e:
            error_msg = f"Error en análisis PCI DSS: {str(e)}"
            self._log(error_msg, "error")
            return {"error": error_msg}