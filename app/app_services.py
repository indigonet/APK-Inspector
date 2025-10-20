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
        """Ejecutar análisis completo del APK - CORREGIDO PCI DSS"""
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
            
            # Verificar que las herramientas estén configuradas
            if not config.get("build_tools"):
                return False, "Build-tools no configurado. Ve a Configurar Herramientas."
            if not config.get("jdk_bin"):
                return False, "JDK no configurado. Ve a Configurar Herramientas."
            
            # Ejecutar análisis
            print("🛠️  EJECUTANDO HERRAMIENTAS...")
            results = self.apk_analyzer.analizar_apk_completo(apk_path_obj, config)
            
            # ✅ DEBUG: Mostrar output de aapt para diagnóstico
            print("🔍 DEBUG - AAPT OUTPUT COMPLETO:")
            print("=" * 50)
            print(results["aapt"])
            print("=" * 50)
            
            # Parsear información del APK
            parsed_info = self.apk_analyzer.parsear_aapt_badging(results["aapt"])
            print(f"📦 PARSED INFO: {parsed_info}")
            
            # Parsear información de firma
            signature_info = self._parse_signature_info(results["apksigner"], results["jarsigner"])
            print(f"🔐 SIGNATURE INFO: {signature_info}")
            
            # ✅ CORREGIDO: EJECUTAR PCI DSS DIRECTAMENTE DESDE EL COMPONENTE
            print("🛡️  EJECUTANDO ANÁLISIS PCI DSS...")
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
            
            # ✅ GENERAR LOG COMPLETO CON PCI DSS
            self.current_log = self._generar_log_completo(results, parsed_info, signature_info, pci_analysis)
            self.components['current_log'] = self.current_log
            
            # Log de resultados
            self._log_detection_results(parsed_info, signature_info)
            
            return True, "Análisis completado"
            
        except Exception as e:
            error_msg = f"Error durante el análisis: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            return False, error_msg

    def _ejecutar_pci_dss_directo(self, parsed_info: Dict, signature_info: Dict, apk_path: Path) -> Dict:
        """Ejecutar análisis PCI DSS directamente desde el componente"""
        try:
            # ✅ VERIFICAR SI EXISTE EL ANALIZADOR PCI DSS EN COMPONENTES
            pci_analyzer = self.components.get('pci_analyzer')
            if not pci_analyzer:
                print("❌ PCI Analyzer no encontrado en componentes")
                return {"error": "PCI DSS Analyzer no disponible"}
            
            print(f"🛡️  PCI Analyzer encontrado: {type(pci_analyzer)}")
            
            # ✅ VERIFICAR QUE EL MÉTODO EXISTA
            if not hasattr(pci_analyzer, 'analizar_cumplimiento_pci'):
                return {"error": "Método analizar_cumplimiento_pci no disponible"}
            
            # ✅ EJECUTAR ANÁLISIS PCI DSS
            resultado = pci_analyzer.analizar_cumplimiento_pci(parsed_info, signature_info, apk_path)
            print(f"🛡️  PCI DSS ejecutado correctamente")
            
            # ✅ AGREGAR REPORTE COMPLETO AL RESULTADO
            if isinstance(resultado, dict):
                # Generar reporte completo
                if hasattr(pci_analyzer, 'generar_reporte_pci'):
                    reporte_completo = pci_analyzer.generar_reporte_pci(resultado)
                    resultado['reporte_completo'] = reporte_completo
                
                # Generar resumen compacto
                if hasattr(pci_analyzer, 'generar_resumen_compacto'):
                    resumen_compacto = pci_analyzer.generar_resumen_compacto(resultado)
                    resultado['resumen_compacto'] = resumen_compacto
                
                print(f"🛡️  Hallazgos ALTOS encontrados: {len(resultado.get('hallazgos_altos', []))}")
                print(f"🛡️  Hallazgos CRÍTICOS encontrados: {len(resultado.get('hallazgos_criticos', []))}")
            
            return resultado
            
        except Exception as e:
            print(f"❌ ERROR ejecutando PCI DSS: {e}")
            return {"error": f"Error ejecutando PCI DSS: {str(e)}"}

    def _parse_signature_info(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        """Parsear información de firma - MEJORADO para extraer empresa"""
        try:
            # Usar signature_verifier si está disponible
            if "signature_verifier" in self.components:
                return self.components["signature_verifier"].parsear_info_firma(
                    apksigner_output, jarsigner_output
                )
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
        if apksigner_output:
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
        if jarsigner_output and company_name == "Desconocida":
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
        """Generar log completo incluyendo PCI DSS - MEJORADO"""
        print(f"🪵 GENERANDO LOG COMPLETO...")
        
        # ✅ CORREGIDO: Eliminar encabezado redundante
        log_content = ""
        
        # Información básica del APK
        apk_size_mb = self.format_utils.get_apk_size_mb(self.apk_path) if hasattr(self.format_utils, 'get_apk_size_mb') else None
        
        log_content += self.format_utils.formatear_resumen_apk(
            parsed_info, signature_info, 
            self.apk_name,
            apk_size_mb,
            pci_analysis  # ✅ AGREGAR PCI DSS AL RESUMEN
        )
        
        # ✅ MEJORADO: Solo agregar sección PCI DSS si no está en el resumen
        if pci_analysis and isinstance(pci_analysis, dict) and 'reporte_completo' in pci_analysis:
            # Verificar si el PCI DSS ya está incluido en el resumen formateado
            pci_en_resumen = "🛡️  RESUMEN PCI DSS" in log_content
            
            if not pci_en_resumen:
                log_content += "\n" + "═" * 45 + "\n"
                log_content += "🛡️ ANÁLISIS PCI DSS DETALLADO\n"
                log_content += "═" * 45 + "\n"
                log_content += pci_analysis['reporte_completo'] + "\n"
        
        # Logs de herramientas
        log_content += "\n" + "═" * 45 + "\n"
        log_content += "🔧 LOGS DE HERRAMIENTAS\n"
        log_content += "═" * 45 + "\n"
        
        # ✅ AÑADIR COMANDOS EJECUTADOS
        if results.get('aapt'):
            log_content += "\n=== AAPT DUMP BADGING ===\n"
            log_content += results['aapt'] + "\n"
        
        if results.get('apksigner'):
            log_content += "\n=== APKSIGNER VERIFY ===\n"
            log_content += results['apksigner'] + "\n"
        
        if results.get('jarsigner'):
            log_content += "\n=== JARSIGNER VERIFY ===\n"
            log_content += results['jarsigner'] + "\n"
        
        if not results:
            log_content += "No hay logs de herramientas disponibles\n"
        
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

        return self.components["pci_analyzer"].generar_reporte_pci(analysis)