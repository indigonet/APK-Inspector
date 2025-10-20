# En core/signature_verifier.py
import re
from typing import Dict

class SignatureVerifier:
    def __init__(self):
        pass
        
    def parsear_info_firma(self, apksigner_output: str, jarsigner_output: str) -> Dict:
        """Parsear información de firma de ambas herramientas"""
        signature_versions = []
        company_name = "Desconocida"
        is_valid = False
        integrity_ok = False
        cert_hash = "No disponible"
        certificate_info = ""
        
        print(f"🔍 DEBUG: Parseando firma - apksigner_len: {len(apksigner_output)}, jarsigner_len: {len(jarsigner_output)}")
        
        # Parsear output de apksigner
        apksigner_info = self._parse_apksigner_output(apksigner_output)
        signature_versions = apksigner_info["signature_versions"]
        is_valid = apksigner_info["is_valid"]
        integrity_ok = apksigner_info["integrity_ok"]
        cert_hash = apksigner_info["cert_hash"]
        
        # Parsear output de jarsigner para información de compañía
        company_info = self._parse_jarsigner_company(jarsigner_output)
        if company_info:
            company_name = company_info["company"]
            certificate_info = company_info["certificate_info"]
            
        print(f"🔍 DEBUG: Resultados - empresa: {company_name}, versiones: {signature_versions}, hash: {cert_hash}")
            
        return {
            "company": company_name,
            "is_valid": is_valid,
            "signature_versions": signature_versions,
            "integrity_ok": integrity_ok,
            "cert_hash": cert_hash,
            "certificate_info": certificate_info,
            "signature_type": "v" + "/v".join(signature_versions) if signature_versions else "No firmado"
        }

    def _parse_apksigner_output(self, output: str) -> Dict:
        """Parsear output específico de apksigner"""
        signature_versions = []
        is_valid = False
        integrity_ok = False
        cert_hash = "No disponible"
        
        if not output:
            return {
                "signature_versions": signature_versions,
                "is_valid": is_valid,
                "integrity_ok": integrity_ok,
                "cert_hash": cert_hash
            }
            
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if "Verified using v1 scheme (JAR signing): true" in line:
                signature_versions.append("v1")
            elif "Verified using v2 scheme (APK Signature Scheme v2): true" in line:
                signature_versions.append("v2")
            elif "Verified using v3 scheme (APK Signature Scheme v3): true" in line:
                signature_versions.append("v3")
            elif "Verified successfully" in line:
                is_valid = True
                integrity_ok = True
            elif "Signer #1 certificate SHA-256 digest:" in line:
                cert_hash = line.split(":")[1].strip()
            elif "SHA-256 digest:" in line and cert_hash == "No disponible":
                cert_hash = line.split(":")[1].strip()
                
        return {
            "signature_versions": signature_versions,
            "is_valid": is_valid,
            "integrity_ok": integrity_ok,
            "cert_hash": cert_hash
        }

    def _parse_jarsigner_company(self, output: str) -> Dict:
        """Extraer información de compañía del output de jarsigner - MEJORADO"""
        if not output:
            return {"company": "Desconocida", "certificate_info": ""}
            
        lines = output.split('\n')
        company_name = "Desconocida"
        certificate_info = ""
        
        print(f"🔍 DEBUG: Buscando empresa en jarsigner output ({len(lines)} líneas)")
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # ✅ BUSCAR Distinguished Name en diferentes formatos
            if "Signer #1 certificate DN:" in line:
                certificate_info = line.split("DN:")[1].strip()
                company_name = self._extraer_empresa_desde_dn(certificate_info)
                print(f"✅ DEBUG: DN encontrado en línea {i}: {certificate_info}")
                break
            
            # ✅ BUSCAR Owner en formato de lista
            elif "Owner:" in line:
                certificate_info = line.split("Owner:")[1].strip()
                company_name = self._extraer_empresa_desde_dn(certificate_info)
                print(f"✅ DEBUG: Owner encontrado en línea {i}: {certificate_info}")
                break
            
            # ✅ BUSCAR Issuer
            elif "Issuer:" in line:
                certificate_info = line.split("Issuer:")[1].strip()
                company_name = self._extraer_empresa_desde_dn(certificate_info)
                print(f"✅ DEBUG: Issuer encontrado en línea {i}: {certificate_info}")
                break
            
            # ✅ BUSCAR en formato de certificado
            elif "Certificate[" in line and "]" in line:
                # Buscar en las siguientes líneas para encontrar el DN
                for j in range(i, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if "Owner:" in next_line:
                        certificate_info = next_line.split("Owner:")[1].strip()
                        company_name = self._extraer_empresa_desde_dn(certificate_info)
                        print(f"✅ DEBUG: Owner en Certificate[] encontrado: {certificate_info}")
                        break
                if company_name != "Desconocida":
                    break
        
        if company_name == "Desconocida":
            print("❌ DEBUG: No se pudo extraer empresa del jarsigner output")
            # Mostrar primeras líneas para diagnóstico
            for i, line in enumerate(lines[:10]):
                print(f"  Línea {i}: {line}")
        
        return {
            "company": company_name,
            "certificate_info": certificate_info
        }

    def _extraer_empresa_desde_dn(self, dn_string: str) -> str:
        """Extraer empresa desde Distinguished Name - MEJORADO"""
        if not dn_string:
            return "Desconocida"
        
        print(f"🔍 DEBUG: Extrayendo empresa de DN: {dn_string}")
        
        # ✅ PRIORIDAD 1: Buscar Organization (O=) - Más específico para empresas
        o_match = re.search(r'O=([^,]+)', dn_string)
        if o_match:
            empresa = o_match.group(1).strip()
            print(f"✅ DEBUG: Empresa encontrada (O=): {empresa}")
            return empresa
        
        # ✅ PRIORIDAD 2: Buscar Organizational Unit (OU=) - Unidad organizacional
        ou_match = re.search(r'OU=([^,]+)', dn_string)
        if ou_match:
            empresa = ou_match.group(1).strip()
            print(f"✅ DEBUG: Empresa encontrada (OU=): {empresa}")
            return empresa
        
        # ✅ PRIORIDAD 3: Buscar Common Name (CN=) - Nombre común
        cn_match = re.search(r'CN=([^,]+)', dn_string)
        if cn_match:
            empresa = cn_match.group(1).strip()
            print(f"✅ DEBUG: Empresa encontrada (CN=): {empresa}")
            return empresa
        
        print("❌ DEBUG: No se pudo extraer empresa del DN")
        return "Desconocida"