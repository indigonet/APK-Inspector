"""
APK Parser - Análisis robusto de archivos APK
Maneja parsing de output de aapt dump badging con detección mejorada de Debug
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List

class APKParser:
    """Parser robusto para análisis de APKs que maneja errores y casos edge"""
    
    @staticmethod
    def parsear_aapt_badging(aapt_output: str) -> Dict[str, Any]:
        """Parser mejorado para output de aapt dump badging"""
        print("🔍 DEBUG APK_PARSER - Iniciando parseo de aapt output...")
        print(f"🔍 DEBUG APK_PARSER - Output length: {len(aapt_output)}")
        
        parsed_info = {
            'package': 'No detectado',
            'version_code': 'No detectado', 
            'version_name': 'No detectado',
            'app_label': 'No detectado',
            'sdk_version': 'No detectado',
            'target_sdk': 'No detectado',
            'min_sdk': 'No detectado',
            'permissions': [],
            'debug_mode': False,
            'is_debuggable': False,
            'raw_info': aapt_output,
            'compile_sdk': 'No detectado',
            'platform_build_version': 'No detectado'
        }
        
        try:
            if not aapt_output or not isinstance(aapt_output, str):
                print("❌ DEBUG APK_PARSER - Output vacío o no es string")
                return parsed_info
            
            # ✅ DETECCIÓN ROBUSTA DE DEBUG
            output_lower = aapt_output.lower()
            if "application-debuggable" in output_lower:
                parsed_info['debug_mode'] = True
                parsed_info['is_debuggable'] = True
                print("🔍 DEBUG APK_PARSER - APK en modo DEBUG detectado")
            else:
                print("🔍 DEBUG APK_PARSER - APK en modo RELEASE")
            
            # ✅ PROCESAR LÍNEA POR LÍNEA
            lines = aapt_output.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Package info - línea más importante
                if line.startswith('package:'):
                    package_data = APKParser._parse_package_line_completa(line)
                    parsed_info.update(package_data)
                    print(f"🔍 DEBUG APK_PARSER - Package data: {package_data}")
                
                # SDK info
                elif line.startswith('sdkVersion:'):
                    sdk = APKParser._extraer_valor_comillas(line)
                    if sdk:
                        parsed_info['sdk_version'] = sdk
                        parsed_info['min_sdk'] = sdk
                        print(f"🔍 DEBUG APK_PARSER - SDK: {sdk}")
                
                elif line.startswith('targetSdkVersion:'):
                    target_sdk = APKParser._extraer_valor_comillas(line)
                    if target_sdk:
                        parsed_info['target_sdk'] = target_sdk
                        print(f"🔍 DEBUG APK_PARSER - Target SDK: {target_sdk}")
                
                # Application label
                elif line.startswith('application-label:'):
                    label = APKParser._extraer_valor_comillas(line)
                    if label:
                        parsed_info['app_label'] = label
                        print(f"🔍 DEBUG APK_PARSER - App label: {label}")
                
                elif line.startswith("application:") and "label=" in line:
                    # Buscar en formato: application: label='AppName' icon='res/...'
                    label_match = re.search(r"label='([^']*)'", line)
                    if label_match:
                        parsed_info['app_label'] = label_match.group(1)
                        print(f"🔍 DEBUG APK_PARSER - App label (from application): {parsed_info['app_label']}")
                
                # Permissions
                elif line.startswith('uses-permission:'):
                    permission = APKParser._extraer_valor_comillas(line)
                    if permission and permission not in parsed_info['permissions']:
                        parsed_info['permissions'].append(permission)
                
                # Información de compilación
                elif 'platformBuildVersionName' in line:
                    valor = APKParser._extraer_valor_comillas(line)
                    if valor:
                        parsed_info['platform_build_version'] = valor
                elif 'compileSdkVersion' in line:
                    valor = APKParser._extraer_valor_comillas(line)
                    if valor:
                        parsed_info['compile_sdk'] = valor
            
            # ✅ POST-PROCESAMIENTO: Validar que tenemos datos
            parsed_info = APKParser._validar_y_limpiar_datos(parsed_info)
            
            print(f"🔍 DEBUG APK_PARSER - Parseo completado:")
            print(f"  - Package: {parsed_info['package']}")
            print(f"  - App Label: {parsed_info['app_label']}") 
            print(f"  - Version: {parsed_info['version_name']} ({parsed_info['version_code']})")
            print(f"  - Target SDK: {parsed_info['target_sdk']}")
            print(f"  - Debug: {parsed_info['debug_mode']}")
            
        except Exception as e:
            print(f"❌ ERROR en parsear_aapt_badging: {e}")
        
        return parsed_info
    
    @staticmethod
    def _parse_package_line_completa(line: str) -> Dict[str, str]:
        """Parsear línea de package con todas las informaciones"""
        result = {}
        
        try:
            # Buscar todos los campos posibles en la línea package
            patterns = {
                'package': r"name='([^']*)'",
                'version_code': r"versionCode='([^']*)'",
                'version_name': r"versionName='([^']*)'",
                'platform_build_version': r"platformBuildVersionName='([^']*)'",
                'compile_sdk': r"compileSdkVersion='([^']*)'"
            }
            
            for campo, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    result[campo] = match.group(1)
                    
            print(f"🔍 DEBUG PACKAGE_PARSER - Extraído: {result}")
                
        except Exception as e:
            print(f"❌ ERROR en _parse_package_line_completa: {e}")
        
        return result
    
    @staticmethod
    def _extraer_valor_comillas(line: str) -> str:
        """Extraer valor entre comillas simples de manera robusta"""
        try:
            matches = re.findall(r"'([^']*)'", line)
            if matches:
                return matches[0]
        except Exception as e:
            print(f"❌ ERROR en _extraer_valor_comillas: {e}")
        return None
    
    @staticmethod
    def _validar_y_limpiar_datos(parsed_info: Dict) -> Dict:
        """Validar y limpiar los datos parseados"""
        # Reemplazar None por 'No detectado' para campos críticos
        critical_fields = ['package', 'version_code', 'version_name', 'app_label', 'target_sdk', 'sdk_version']
        
        for field in critical_fields:
            if not parsed_info.get(field) or parsed_info[field] is None:
                parsed_info[field] = 'No detectado'
        
        # Asegurar que permissions es siempre una lista
        if not parsed_info.get('permissions'):
            parsed_info['permissions'] = []
        
        # Limpiar valores que puedan ser "None" como string
        for key, value in parsed_info.items():
            if isinstance(value, str) and value.lower() == 'none':
                parsed_info[key] = 'No detectado'
        
        return parsed_info

    @staticmethod
    def analizar_apk_completo(apk_path: Path, config: Dict) -> Dict[str, Any]:
        """Analizar APK completo integrando todas las herramientas"""
        try:
            print(f"🔍 ANALIZANDO APK: {apk_path.name}")
            
            # Ejecutar aapt
            aapt_output = APKParser._ejecutar_aapt(apk_path, config.get("build_tools"))
            print(f"🔍 AAPT OUTPUT OBTENIDO: {len(aapt_output)} caracteres")
            
            # Ejecutar apksigner
            apksigner_output = APKParser._ejecutar_apksigner(apk_path, config.get("build_tools"))
            print(f"🔍 APKSIGNER OUTPUT OBTENIDO: {len(apksigner_output)} caracteres")
            
            # Ejecutar jarsigner  
            jarsigner_output = APKParser._ejecutar_jarsigner(apk_path, config.get("jdk_bin"))
            print(f"🔍 JARSIGNER OUTPUT OBTENIDO: {len(jarsigner_output)} caracteres")
            
            return {
                "aapt": aapt_output,
                "apksigner": apksigner_output,
                "jarsigner": jarsigner_output
            }
            
        except Exception as e:
            print(f"❌ ERROR en analizar_apk_completo: {e}")
            return {
                "aapt": f"Error: {str(e)}",
                "apksigner": "",
                "jarsigner": ""
            }
    
    @staticmethod
    def _ejecutar_aapt(apk_path: Path, build_tools_path: str) -> str:
        """Ejecutar aapt dump badging"""
        try:
            aapt_path = Path(build_tools_path) / "aapt.exe"
            if not aapt_path.exists():
                return f"Error: aapt no encontrado en {aapt_path}"
            
            comando = [str(aapt_path), 'dump', 'badging', str(apk_path)]
            print(f"🔍 EJECUTANDO AAPT: {' '.join(comando)}")
            
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30
            )
            
            output = resultado.stdout
            print(f"🔍 AAPT RETURN CODE: {resultado.returncode}")
            
            if resultado.returncode != 0:
                print(f"⚠️ AAPT ERROR: {resultado.stderr[:500]}...")
                return f"Error aapt: {resultado.stderr[:500]}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Timeout ejecutando aapt"
        except Exception as e:
            print(f"❌ ERROR en _ejecutar_aapt: {e}")
            return f"Error ejecutando aapt: {str(e)}"

    @staticmethod
    def _ejecutar_apksigner(apk_path: Path, build_tools_path: str) -> str:
        """Ejecutar apksigner verify"""
        try:
            apksigner_path = Path(build_tools_path) / "apksigner.bat"
            if not apksigner_path.exists():
                return "apksigner no disponible"
            
            comando = [str(apksigner_path), 'verify', '--verbose', str(apk_path)]
            print(f"🔍 EJECUTANDO APKSIGNER: {' '.join(comando)}")
            
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30
            )
            
            return resultado.stdout + resultado.stderr
            
        except Exception as e:
            print(f"❌ ERROR en _ejecutar_apksigner: {e}")
            return f"Error ejecutando apksigner: {str(e)}"

    @staticmethod
    def _ejecutar_jarsigner(apk_path: Path, jdk_bin_path: str) -> str:
        """Ejecutar jarsigner verify"""
        try:
            jarsigner_path = Path(jdk_bin_path) / "jarsigner.exe"
            if not jarsigner_path.exists():
                return "jarsigner no disponible"
            
            comando = [str(jarsigner_path), '-verify', '-verbose', str(apk_path)]
            print(f"🔍 EJECUTANDO JARSIGNER: {' '.join(comando)}")
            
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30
            )
            
            return resultado.stdout + resultado.stderr
            
        except Exception as e:
            print(f"❌ ERROR en _ejecutar_jarsigner: {e}")
            return f"Error ejecutando jarsigner: {str(e)}"

    @staticmethod
    def evaluar_calidad_informacion(parsed_info: Dict) -> Dict[str, Any]:
        """Evaluar la calidad y completitud de la información parseada"""
        campos_criticos = ['package', 'app_label', 'version_name', 'version_code', 'target_sdk']
        campos_detectados = []
        campos_faltantes = []
        
        for campo in campos_criticos:
            valor = parsed_info.get(campo)
            if valor and valor != 'No detectado' and str(valor).strip():
                campos_detectados.append(campo)
            else:
                campos_faltantes.append(campo)
        
        # Calcular métricas de calidad
        total_campos = len(campos_criticos)
        campos_ok = len(campos_detectados)
        porcentaje_calidad = (campos_ok / total_campos) * 100 if total_campos > 0 else 0
        
        # Determinar nivel de confianza
        if porcentaje_calidad >= 80:
            nivel_confianza = "ALTO"
        elif porcentaje_calidad >= 50:
            nivel_confianza = "MEDIO"
        else:
            nivel_confianza = "BAJO"
        
        return {
            'campos_detectados': campos_detectados,
            'campos_faltantes': campos_faltantes,
            'porcentaje_calidad': porcentaje_calidad,
            'nivel_confianza': nivel_confianza,
            'es_confiable': porcentaje_calidad >= 60,
            'total_permisos': len(parsed_info.get('permissions', [])),
            'debug_detectado': parsed_info.get('debug_mode', False)
        }