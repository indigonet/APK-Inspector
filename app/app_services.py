"""
APK Inspector & Verifier - Servicios de la aplicación
Contiene la lógica de negocio separada de la UI
"""

from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import threading
from typing import Dict, Tuple
import subprocess
import re


class AppServices:
    """Clase que contiene los servicios de la aplicación"""

    def __init__(self, components):
        self.components = components
        # ✅ CORREGIDO: Asegurar que tenemos referencia a todos los componentes
        self.apk_analyzer = components.get('apk_analyzer')
        self.logger = components.get('logger')
        self.file_utils = components.get('file_utils')
        self.format_utils = components.get('format_utils')
        self.config_manager = components.get('config_manager')
        self.tool_detector = components.get('tool_detector')
        self.adb_manager = components.get('adb_manager')
        self.pci_analyzer = components.get('pci_analyzer')
        
        # Estado de la aplicación
        self.apk_path = None
        self.apk_name = None
        self.current_log = ""
        self.current_analysis = {}

    def analyze_apk(self, apk_path):
        """Ejecutar análisis completo del APK - CORREGIDO para jarsigner"""
        try:
            if not self.apk_analyzer:
                return False, "APK Analyzer no disponible"
                
            apk_path_obj = Path(apk_path)
            self.apk_path = apk_path_obj
            self.apk_name = apk_path_obj.name
            
            # Actualizar componentes
            self.components['apk_path'] = self.apk_path
            self.components['apk_name'] = self.apk_name
            
            config = self._get_tools_config()
            
            # ✅ CORREGIDO: No requerir herramientas para análisis básico
            if not config.get("build_tools"):
                self.logger.log_warning("Build-tools no configurado, usando análisis básico")
            
            # Ejecutar análisis
            print("🛠️  EJECUTANDO HERRAMIENTAS...")
            results = self.apk_analyzer.analizar_apk_completo(apk_path_obj, config)
            
            # ✅ CORREGIDO: VERIFICAR Y EJECUTAR JARSIGNER MANUALMENTE SI FALTA
            if 'jarsigner' not in results or not results['jarsigner'] or "no disponible" in str(results.get('jarsigner', '')).lower():
                print("🛠️  Ejecutando jarsigner manualmente...")
                results['jarsigner'] = self._ejecutar_jarsigner_manual(apk_path_obj, config)
            
            # ✅ DEBUG: Mostrar output de herramientas para diagnóstico
            print("🔍 DEBUG - HERRAMIENTAS EJECUTADAS:")
            for herramienta, output in results.items():
                status = "✅" if output and "error" not in str(output).lower() and "no encontrado" not in str(output).lower() else "❌"
                print(f"   {status} {herramienta}: {str(output)[:100]}...")
            
            # ✅ CORREGIDO: Usar el método correcto para parsear información
            if hasattr(self.apk_analyzer, 'parsear_informacion_apk'):
                parsed_info = self.apk_analyzer.parsear_informacion_apk(results)
            else:
                # Fallback: usar aapt directamente
                parsed_info = self._parsear_aapt_directo(results.get("aapt", ""))
            
            print(f"📦 PARSED INFO: {parsed_info}")
            
            # Parsear información de firma
            signature_info = self._parse_signature_info(results.get("apksigner", ""), results.get("jarsigner", ""))
            print(f"🔐 SIGNATURE INFO: {signature_info}")
            
            # ✅ CORREGIDO: EJECUTAR PCI DSS USANDO EL MÉTODO CORRECTO
            pci_analysis = self._ejecutar_pci_dss_directo(parsed_info, signature_info, apk_path_obj)
            print(f"🛡️  PCI ANALYSIS RESULT: {pci_analysis}")

            # Guardar análisis actual
            self.current_analysis = {
                'parsed_info': parsed_info,
                'signature_info': signature_info,
                'results': results,
                'pci_analysis': pci_analysis
            }
            
            # Actualizar componentes
            self.components['current_analysis'] = self.current_analysis
            
            # ✅ GENERAR LOG COMPLETO
            self.current_log = self._generar_log_completo(results, parsed_info, signature_info, pci_analysis)
            self.components['current_log'] = self.current_log
            
            # Log de resultados
            self._log_detection_results(parsed_info, signature_info)
            
            return True, "Análisis completado"
            
        except Exception as e:
            error_msg = f"Error durante el análisis: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.logger.log_error("Error en analyze_apk", e)
            return False, error_msg

    def _ejecutar_jarsigner_manual(self, apk_path: Path, config: dict) -> str:
        """Ejecutar jarsigner manualmente si no está en los resultados"""
        try:
            jdk_bin = config.get("jdk_bin", "")
            if not jdk_bin:
                return "JDK bin no configurado"
            
            jarsigner_path = Path(jdk_bin) / "jarsigner"
            if not jarsigner_path.exists():
                jarsigner_path = Path(jdk_bin) / "jarsigner.exe"
            
            if not jarsigner_path.exists():
                return "jarsigner no encontrado en JDK bin"
            
            # Ejecutar jarsigner verify
            result = subprocess.run(
                [str(jarsigner_path), "-verify", "-verbose", "-certs", str(apk_path)],
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error jarsigner: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "jarsigner timeout - tardó demasiado en ejecutarse"
        except Exception as e:
            return f"Error ejecutando jarsigner: {str(e)}"

    def _ejecutar_pci_dss_directo(self, parsed_info: Dict, signature_info: Dict, apk_path: Path) -> Dict:
        """Ejecutar análisis PCI DSS directamente desde el componente - CORREGIDO"""
        try:
            # ✅ VERIFICAR SI EXISTE EL ANALIZADOR PCI DSS EN COMPONENTES
            pci_analyzer = self.components.get('pci_analyzer')
            if not pci_analyzer:
                print("❌ PCI Analyzer no encontrado en componentes")
                return self._generate_basic_pci_analysis(parsed_info, signature_info)
            
            print(f"🛡️  PCI Analyzer encontrado: {type(pci_analyzer)}")
            
            # ✅ VERIFICAR MÉTODOS DISPONIBLES - PRIMERO EL QUE FUNCIONABA
            if hasattr(pci_analyzer, 'analizar_cumplimiento_pci'):
                print("✅ Usando analizar_cumplimiento_pci")
                resultado = pci_analyzer.analizar_cumplimiento_pci(parsed_info, signature_info, apk_path)
            elif hasattr(pci_analyzer, 'analizar_apk'):
                print("✅ Usando analizar_apk")
                resultado = pci_analyzer.analizar_apk(parsed_info, signature_info)
            else:
                print("❌ No se encontraron métodos PCI DSS válidos")
                return self._generate_basic_pci_analysis(parsed_info, signature_info)
            
            print(f"🛡️  PCI DSS ejecutado correctamente")
            
            # ✅ AGREGAR REPORTE COMPLETO AL RESULTADO
            if isinstance(resultado, dict):
                # Generar reporte completo
                if hasattr(pci_analyzer, 'generar_reporte_pci'):
                    reporte_completo = pci_analyzer.generar_reporte_pci(resultado)
                    resultado['reporte_completo'] = reporte_completo
                elif hasattr(pci_analyzer, 'generar_reporte_completo'):
                    reporte_completo = pci_analyzer.generar_reporte_completo(resultado)
                    resultado['reporte_completo'] = reporte_completo
                else:
                    # Generar reporte básico si no hay método específico
                    resultado['reporte_completo'] = self._generar_reporte_pci_basico(resultado)
                
                # Generar resumen compacto
                if hasattr(pci_analyzer, 'generar_resumen_compacto'):
                    resumen_compacto = pci_analyzer.generar_resumen_compacto(resultado)
                    resultado['resumen_compacto'] = resumen_compacto
                
                print(f"🛡️  Hallazgos encontrados: {len(resultado.get('hallazgos', []))}")
                print(f"🛡️  Permisos sensibles: {len(resultado.get('permisos_sensibles', []))}")
            
            return resultado
            
        except Exception as e:
            print(f"❌ ERROR ejecutando PCI DSS: {e}")
            return self._generate_basic_pci_analysis(parsed_info, signature_info)

    def _generar_reporte_pci_basico(self, pci_analysis: Dict) -> str:
        """Generar reporte PCI DSS básico si no hay método específico"""
        reporte = "🛡️  ANÁLISIS PCI DSS BÁSICO\n"
        reporte += "═" * 45 + "\n"
        
        # Información general
        reporte += "📊 INFORMACIÓN GENERAL\n"
        reporte += "─────────────────────────────────────────────\n"
        reporte += f"💻 Soporte nativo: No detectado\n"
        reporte += f"📱 Min SDK: {pci_analysis.get('min_sdk', 'No disponible')}\n\n"
        
        # Permisos sensibles
        permisos_sensibles = pci_analysis.get('permisos_sensibles', [])
        reporte += "🚨 PERMISOS SENSIBLES\n"
        reporte += "─────────────────────────────────────────────\n"
        if permisos_sensibles:
            for perm in permisos_sensibles:
                reporte += f"• {perm}\n"
        else:
            reporte += "No se detectaron permisos sensibles\n"
        
        # Hallazgos
        hallazgos = pci_analysis.get('hallazgos', [])
        reporte += f"\n📊 ESTADÍSTICAS\n"
        reporte += "─────────────────────────────────────────────\n"
        reporte += f"Total de permisos: {pci_analysis.get('total_permisos', 0)}\n"
        reporte += f"Permisos sensibles: {len(permisos_sensibles)}\n"
        reporte += f"Hallazgos de seguridad: {len(hallazgos)}\n"
        
        return reporte

    def _generate_basic_pci_analysis(self, parsed_info, signature_info):
        """Generar análisis PCI DSS básico si el analyzer no funciona"""
        if not parsed_info:
            return {
                'reporte_completo': "🛡️ ANÁLISIS PCI DSS BÁSICO\n═" + "═" * 44 + "\n❌ No hay información del APK para analizar",
                'permisos_totales': 0,
                'permisos_sensibles': [],
                'modo_debug': False,
                'firma_valida': False,
                'hallazgos': []
            }
            
        permissions = parsed_info.get('permissions', [])
        sensitive_perms = []
        
        # Permisos sensibles para PCI DSS
        pci_sensitive_permissions = [
            'android.permission.READ_EXTERNAL_STORAGE',
            'android.permission.WRITE_EXTERNAL_STORAGE', 
            'android.permission.ACCESS_NETWORK_STATE',
            'android.permission.INTERNET',
            'android.permission.ACCESS_WIFI_STATE',
            'android.permission.READ_PHONE_STATE',
            'android.permission.ACCESS_FINE_LOCATION',
            'android.permission.ACCESS_COARSE_LOCATION',
            'android.permission.CAMERA',
            'android.permission.RECORD_AUDIO',
            'android.permission.READ_CONTACTS',
            'android.permission.WRITE_CONTACTS',
            'android.permission.READ_SMS',
            'android.permission.SEND_SMS'
        ]
        
        for perm in permissions:
            if any(sensitive in perm for sensitive in pci_sensitive_permissions):
                sensitive_perms.append(perm)
        
        # Hallazgos basados en análisis básico
        hallazgos = []
        if parsed_info.get('debuggable'):
            hallazgos.append("APK en modo depuración (debuggable)")
        if not signature_info.get('is_valid'):
            hallazgos.append("Firma no válida o no encontrada")
        if len(sensitive_perms) > 5:
            hallazgos.append("Múltiples permisos sensibles detectados")
        
        # Análisis básico
        reporte = "🛡️  ANÁLISIS PCI DSS BÁSICO\n"
        reporte += "═" * 45 + "\n"
        reporte += "📊 ESTADÍSTICAS DE SEGURIDAD\n"
        reporte += "─────────────────────────────────────────────\n"
        reporte += f"💻 Soporte nativo: No detectado\n"
        reporte += f"📱 Min SDK: {parsed_info.get('min_sdk', 'No disponible')}\n\n"
        
        reporte += "🚨 PERMISOS SENSIBLES\n"
        reporte += "─────────────────────────────────────────────\n"
        if sensitive_perms:
            for perm in sensitive_perms:
                reporte += f"• {perm}\n"
        else:
            reporte += "No se detectaron permisos sensibles\n"
        
        reporte += "\n📊 ESTADÍSTICAS\n"
        reporte += "─────────────────────────────────────────────\n"
        reporte += f"Total de permisos: {len(permissions)}\n"
        reporte += f"Permisos sensibles: {len(sensitive_perms)}\n"
        reporte += f"Modo debug: {'SÍ' if parsed_info.get('debuggable') else 'NO'}\n"
        reporte += f"Firma válida: {'SÍ' if signature_info.get('is_valid') else 'NO'}\n"
        reporte += f"Hallazgos: {len(hallazgos)}\n"
        
        if hallazgos:
            reporte += "\n⚠️  HALLAZGOS DE SEGURIDAD:\n"
            for hallazgo in hallazgos:
                reporte += f"• {hallazgo}\n"
        
        return {
            'reporte_completo': reporte,
            'permisos_totales': len(permissions),
            'permisos_sensibles': sensitive_perms,
            'modo_debug': parsed_info.get('debuggable', False),
            'firma_valida': signature_info.get('is_valid', False),
            'hallazgos': hallazgos,
            'min_sdk': parsed_info.get('min_sdk', 'No disponible')
        }

    def _parsear_aapt_directo(self, aapt_output: str) -> Dict:
        """Parsear salida de aapt directamente como fallback"""
        parsed_info = {
            "package": None, "version_name": None, "version_code": None,
            "target_sdk": None, "min_sdk": None, "permissions": [],
            "app_label": None, "debug_mode": False, "debuggable": False,
            "package_name": "", "app_name": "", "build_type": "Release"
        }
        
        if not aapt_output or "error" in aapt_output.lower():
            return parsed_info
            
        lines = aapt_output.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("package:"):
                self._parse_package_line_directo(line, parsed_info)
            elif line.startswith("targetSdkVersion:"):
                parsed_info["target_sdk"] = self._extract_value_directo(line, "targetSdkVersion:")
            elif line.startswith("sdkVersion:"):
                parsed_info["min_sdk"] = self._extract_value_directo(line, "sdkVersion:")
            elif line.startswith("uses-permission:"):
                self._parse_permission_line_directo(line, parsed_info)
            elif line.startswith("application-label:") and not parsed_info["app_label"]:
                parsed_info["app_label"] = self._extract_value_directo(line, "application-label:")
                parsed_info["app_name"] = self._extract_value_directo(line, "application-label:")
            
            if 'application-debuggable' in line.lower():
                parsed_info["debug_mode"] = True
                parsed_info["debuggable"] = True
        
        parsed_info["package_name"] = parsed_info["package"]
        return parsed_info

    def _parse_package_line_directo(self, line: str, parsed: Dict):
        """Parsear línea de package directamente"""
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

    def _parse_permission_line_directo(self, line: str, parsed: Dict):
        """Parsear línea de permisos directamente"""
        try:
            perm_start = line.find("name='")
            if perm_start != -1:
                perm_end = line.find("'", perm_start + 6)
                if perm_end != -1:
                    permission = line[perm_start + 6 : perm_end]
                    parsed["permissions"].append(permission)
        except Exception:
            pass

    def _extract_value_directo(self, line: str, prefix: str = "") -> str:
        """Extraer valor directamente"""
        try:
            if prefix:
                line = line.split(prefix, 1)[1].strip()
            return line.strip().strip("'\"")
        except Exception:
            return ""

    def _parse_signature_info(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        """Parsear información de firma - MEJORADO para extraer empresa"""
        try:
            # Usar signature_verifier si está disponible
            if "signature_verifier" in self.components:
                return self.components["signature_verifier"].parsear_info_firma(
                    apksigner_output, jarsigner_output
                )
            elif hasattr(self.apk_analyzer, 'parsear_informacion_firma'):
                # Usar el método del analyzer si está disponible
                return self.apk_analyzer.parsear_informacion_firma(apksigner_output, jarsigner_output)
            else:
                # ✅ FALLBACK: Parseo básico si no hay signature_verifier
                return self._parse_signature_basic(apksigner_output, jarsigner_output)
        except Exception as e:
            self.logger.log_error("Error parseando firma", e)
            return self._get_default_signature_info()

    def _parse_signature_basic(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        """Parseo básico de información de firma - CORREGIDO para evitar duplicados"""
        signature_versions = []
        company_name = "Desconocida"
        cert_hash = "No disponible"
        cert_info = ""

        # ✅ CORREGIDO: Usar conjunto para evitar duplicados
        version_set = set()

        # Parsear apksigner
        if apksigner_output and "error" not in apksigner_output.lower():
            lines = apksigner_output.split("\n")
            for line in lines:
                line = line.strip()
                
                # ✅ CORREGIDO: Verificar que sea exactamente "true" y no parte de otra palabra
                if "Verified using v1 scheme" in line and "true" in line.lower():
                    version_set.add("v1")
                elif "Verified using v2 scheme" in line and "true" in line.lower():
                    version_set.add("v2")
                elif "Verified using v3 scheme" in line and "true" in line.lower():
                    version_set.add("v3")
                elif "Verified using v3.1 scheme" in line and "true" in line.lower():
                    version_set.add("v3.1")
                elif "Verified using v4 scheme" in line and "true" in line.lower():
                    version_set.add("v4")
                    
                # ✅ CORREGIDO: Buscar hash SHA-256 completo
                if "SHA-256 digest:" in line:
                    parts = line.split("SHA-256 digest:")
                    if len(parts) > 1:
                        cert_hash = parts[1].strip()
                        print(f"🔍 Hash encontrado: {cert_hash}")

                # ✅ CORREGIDO: Buscar DN del certificado para empresa
                if "certificate DN:" in line:
                    parts = line.split("certificate DN:")
                    if len(parts) > 1:
                        dn_info = parts[1].strip()
                        cert_info = dn_info
                        company_name = self._extract_company_from_dn(dn_info)
                        print(f"🔍 Empresa encontrada: {company_name}")

        # ✅ CORREGIDO: Convertir set a lista ordenada
        signature_versions = sorted(list(version_set))

        # Parsear jarsigner para empresa (solo si no se encontró en apksigner)
        if jarsigner_output and company_name == "Desconocida" and "error" not in jarsigner_output.lower():
            lines = jarsigner_output.split("\n")
            for line in lines:
                line = line.strip()
                # Buscar Distinguished Name
                if "Signer #1 certificate DN:" in line:
                    dn_info = line.split("DN:")[1].strip()
                    company_name = self._extract_company_from_dn(dn_info)
                    break
                # Buscar Owner
                elif "Owner:" in line:
                    owner_info = line.split("Owner:")[1].strip()
                    company_name = self._extract_company_from_dn(owner_info)
                    break

        return {
            "company": company_name,
            "is_valid": len(signature_versions) > 0,
            "signature_versions": signature_versions,
            "integrity_ok": len(signature_versions) > 0,
            "cert_hash": cert_hash,
            "certificate_info": cert_info,
            "signature_type": (
                "v" + "/v".join(signature_versions)
                if signature_versions
                else "No firmado"
            ),
        }

    def _extract_company_from_dn(self, dn_string: str) -> str:
        """Extraer empresa desde Distinguished Name"""
        import re

        if not dn_string:
            return "Desconocida"

        # Buscar Organization (O=)
        o_match = re.search(r"O=([^,]+)", dn_string)
        if o_match:
            return o_match.group(1).strip()

        # Buscar Organizational Unit (OU=)
        ou_match = re.search(r"OU=([^,]+)", dn_string)
        if ou_match:
            return ou_match.group(1).strip()

        # Buscar Common Name (CN=)
        cn_match = re.search(r"CN=([^,]+)", dn_string)
        if cn_match:
            return cn_match.group(1).strip()

        return "Desconocida"

    def _get_default_signature_info(self) -> Dict:
        """Información de firma por defecto"""
        return {
            "company": "Desconocida",
            "is_valid": False,
            "signature_versions": [],
            "integrity_ok": False,
            "cert_hash": "No disponible",
            "certificate_info": "",
            "signature_type": "No firmado",
        }

    def _generar_log_completo(self, results, parsed_info, signature_info, pci_analysis):
        """Generar log completo incluyendo PCI DSS - CORREGIDO para incluir comandos"""
        print(f"🪵 GENERANDO LOG COMPLETO...")
        
        log_content = ""
        
        # Información básica del APK usando format_utils
        apk_size_mb = self.format_utils.get_apk_size_mb(self.apk_path) if hasattr(self.format_utils, 'get_apk_size_mb') else None
        
        log_content += self.format_utils.formatear_resumen_apk(
            parsed_info, signature_info, 
            self.apk_name,
            apk_size_mb,
            pci_analysis
        )
        
        # ✅ CORREGIDO: AGREGAR SECCIÓN DE COMANDOS COMPLETOS
        log_content += "\n" + "═" * 80 + "\n"
        log_content += "🔧 COMANDOS EJECUTADOS - LOGS COMPLETOS\n"
        log_content += "═" * 80 + "\n\n"
        
        # ✅ AÑADIR COMANDOS AAPT COMPLETOS
        if results.get('aapt'):
            log_content += "=== AAPT DUMP BADGING ===\n"
            log_content += "═" * 50 + "\n"
            log_content += results['aapt'] + "\n\n"
        else:
            log_content += "=== AAPT DUMP BADGING ===\n"
            log_content += "═" * 50 + "\n"
            log_content += "No disponible\n\n"
        
        # ✅ AÑADIR COMANDOS APKSIGNER COMPLETOS
        if results.get('apksigner'):
            log_content += "=== APKSIGNER VERIFY ===\n"
            log_content += "═" * 50 + "\n"
            log_content += results['apksigner'] + "\n\n"
        else:
            log_content += "=== APKSIGNER VERIFY ===\n"
            log_content += "═" * 50 + "\n"
            log_content += "No disponible\n\n"
        
        # ✅ AÑADIR COMANDOS JARSIGNER COMPLETOS
        if results.get('jarsigner'):
            log_content += "=== JARSIGNER VERIFY ===\n"
            log_content += "═" * 50 + "\n"
            log_content += results['jarsigner'] + "\n\n"
        else:
            log_content += "=== JARSIGNER VERIFY ===\n"
            log_content += "═" * 50 + "\n"
            log_content += "No disponible\n\n"
        
        if pci_analysis and isinstance(pci_analysis, dict) and 'reporte_completo' in pci_analysis:
            # Verificar si el PCI DSS ya está incluido en el resumen formateado
            pci_en_resumen = "🛡️  RESUMEN PCI DSS" in log_content
            
            if not pci_en_resumen:
                log_content += "═" * 80 + "\n"
                log_content += "🛡️ ANÁLISIS PCI DSS DETALLADO\n"
                log_content += "═" * 80 + "\n\n"
                log_content += pci_analysis['reporte_completo'] + "\n"
        
        print(f"🪵 LOG CONTENT GENERADO (primeros 1000 chars): {log_content[:1000]}...")
        
        return log_content

    def _log_detection_results(self, parsed_info: Dict, signature_info: Dict):
        """Log de resultados de detección - DEBUG"""
        # Log modo debug
        if parsed_info.get("debug_mode"):
            self.logger.log_info("✅ APK en modo DEBUG detectado")
        else:
            self.logger.log_info("✅ APK en modo RELEASE detectado")

        # Log empresa
        empresa = signature_info.get("company", "Desconocida")
        if empresa != "Desconocida":
            self.logger.log_info(f"✅ Empresa detectada: {empresa}")
        else:
            self.logger.log_info("⚠️ No se pudo detectar la empresa")

        # Log firma
        versions = signature_info.get("signature_versions", [])
        if versions:
            self.logger.log_info(
                f"✅ Firmas detectadas: {', '.join(versions)}"
            )
        else:
            self.logger.log_info("⚠️ No se detectaron firmas")

    def _get_apk_size_mb(self, apk_path: Path) -> float:
        """Obtener tamaño del APK en MB"""
        try:
            size_bytes = apk_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        except Exception:
            return 0.0

    def _get_tools_config(self):
        """Obtener configuración de herramientas"""
        config = self.config_manager.cargar_config()
        detectado = self.tool_detector.detectar_herramientas()

        return {
            "build_tools": config.get("build_tools") or str(detectado.get("build_tools", "")),
            "platform_tools": config.get("platform_tools") or str(detectado.get("platform_tools", "")),
            "jdk_bin": config.get("jdk_bin") or str(detectado.get("jdk_bin", "")),
        }

    def _format_complete_log(self, results):
        """Formatear log completo del análisis"""
        log_content = "=== AAPT DUMP BADGING ===\n"
        log_content += results.get("aapt", "No disponible") + "\n\n"

        log_content += "=== APKSIGNER VERIFY ===\n"
        log_content += results.get("apksigner", "No disponible") + "\n\n"

        log_content += "=== JARSIGNER VERIFY ===\n"
        log_content += results.get("jarsigner", "No disponible") + "\n"

        return log_content

    # Métodos para gestión de APK
    def install_apk(self, platform_tools, device=None):
        """Instalar APK en dispositivo"""
        if not self.apk_path:
            return False, "No hay APK seleccionado"

        return self.adb_manager.instalar_apk(
            self.apk_path, platform_tools, device
        )

    def uninstall_apk(self, platform_tools, package_name, device=None):
        """Desinstalar aplicación"""
        return self.adb_manager.desinstalar_apk(
            package_name, platform_tools, device
        )

    def get_connected_devices(self, platform_tools):
        """Obtener dispositivos conectados"""
        return self.adb_manager.obtener_dispositivos(platform_tools)

    # Métodos para herramientas
    def get_tools_status(self):
        """Obtener estado de las herramientas"""
        return self.tool_detector.verificar_herramientas_instaladas()

    def save_tools_config(self, config):
        """Guardar configuración de herramientas"""
        return self.config_manager.guardar_config(config)

    # Métodos de utilidad
    def clear_analysis(self):
        """Limpiar análisis actual"""
        self.apk_path = None
        self.apk_name = None
        self.current_log = ""
        self.current_analysis = {}

        # Actualizar componentes
        self.components["apk_path"] = None
        self.components["apk_name"] = None
        self.components["current_log"] = ""
        self.components["current_analysis"] = {}

    def export_log(self, file_path):
        """Exportar log a archivo"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.current_log)
            return True, "Log exportado correctamente"
        except Exception as e:
            return False, f"Error exportando log: {str(e)}"

    def is_pci_analysis_available(self):
        """Verificar si el análisis PCI DSS está disponible"""
        return "pci_analyzer" in self.components and self.components["pci_analyzer"] is not None

    def get_pci_report(self):
        """Obtener reporte PCI DSS si está disponible"""
        if not self.is_pci_analysis_available():
            return "Análisis PCI DSS no disponible"

        analysis = self.current_analysis.get("pci_analysis")
        if not analysis:
            return "No hay análisis PCI DSS disponible"

        # Si el pci_analyzer tiene método generar_reporte_pci, usarlo
        if (hasattr(self.pci_analyzer, 'generar_reporte_pci') and 
            callable(getattr(self.pci_analyzer, 'generar_reporte_pci'))):
            return self.pci_analyzer.generar_reporte_pci(analysis)
        else:
            # Devolver el reporte básico
            return analysis.get('reporte_completo', 'Reporte PCI DSS no disponible')