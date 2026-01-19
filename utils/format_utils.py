from math import perm
from typing import List, Dict, Any
import os
import sys
import socket
from pathlib import Path
import re
import subprocess

class FormatUtils:
    
    # Diccionario con los links de descarga de las herramientas
    HERRAMIENTAS_DESCARGAS = {
        "platform_tools": {
            "nombre": "Android Platform Tools",
            "url": "https://developer.android.com/studio/releases/platform-tools",
            "descripcion": "Incluye ADB y otras herramientas esenciales"
        },
        "build_tools": {
            "nombre": "Android Build Tools", 
            "url": "https://developer.android.com/studio/releases/build-tools",
            "descripcion": "Incluye AAPT, APKSigner y herramientas de compilación"
        },
        "jdk": {
            "nombre": "Java Development Kit (JDK)",
            "url": "https://www.oracle.com/java/technologies/downloads/",
            "descripcion": "JDK 8 o superior requerido para jarsigner"
        },
        "aapt": {
            "nombre": "AAPT (Android Asset Packaging Tool)",
            "url": "https://developer.android.com/studio/command-line/aapt2",
            "descripcion": "Herramienta para analizar archivos APK"
        },
        "apksigner": {
            "nombre": "APKSigner",
            "url": "https://developer.android.com/studio/command-line/apksigner",
            "descripcion": "Herramienta para verificar firmas de APK"
        },
        "adb": {
            "nombre": "ADB (Android Debug Bridge)",
            "url": "https://developer.android.com/studio/command-line/adb",
            "descripcion": "Herramienta de depuración y conexión con dispositivos"
        }
    }

    @staticmethod

    
    def crear_mensaje_estado_herramientas(estado_herramientas: Dict) -> str:
        """Crear mensaje de estado de herramientas con emojis y formato mejorado"""
        # Constantes de formato
        SEPARADOR_ANCHO = 50
        SEPARADOR_FUERTE = "═" * SEPARADOR_ANCHO
        SEPARADOR_SUAVE = "─" * SEPARADOR_ANCHO
        
        # Emojis y símbolos modernos
        EMOJIS = {
            "titulo": "⚙️",
            "instalado": "✅",
            "no_instalado": "❌",
            "link": "🔗",
            "ubicacion": "📁",
            "descarga": "📥",
            "detalle": "📋",
            "disponible": "✓",
            "info": "💡",
            "herramienta": "🛠️"
        }
        
        # Construir mensaje
        lineas = []
        
        # Encabezado
        lineas.append(f"\n{SEPARADOR_FUERTE}")
        lineas.append(f"{EMOJIS['titulo']}  ESTADO DE HERRAMIENTAS  {EMOJIS['herramienta']}")
        lineas.append(f"{SEPARADOR_FUERTE}")
        
        herramientas_faltantes = []
        
        # Procesar cada herramienta
        for herramienta, info in estado_herramientas.items():
            nombre_formateado = herramienta.replace('_', ' ').title()
            
            if info["instalado"]:
                ruta_corta = FormatUtils._acortar_ruta(info["ruta"])
                lineas.append(f"{EMOJIS['instalado']} {nombre_formateado}")
                lineas.append(f"   {EMOJIS['ubicacion']} {ruta_corta}")
                
                # Sub-herramientas
                sub_herramientas = []
                
                if herramienta == "platform_tools" and info["adb"]:
                    sub_herramientas.append("ADB")
                if herramienta == "build_tools":
                    if info["aapt"]:
                        sub_herramientas.append("AAPT")
                    if info["apksigner"]:
                        sub_herramientas.append("APKSigner")
                if herramienta == "jdk" and info["jarsigner"]:
                    sub_herramientas.append("JarSigner")
                
                if sub_herramientas:
                    lineas.append(f"   {EMOJIS['detalle']} " + 
                                ", ".join(f"{EMOJIS['disponible']} {tool}" for tool in sub_herramientas))
            else:
                lineas.append(f"{EMOJIS['no_instalado']} {nombre_formateado}")
                lineas.append(f"   ⚠️  No detectado")
                herramientas_faltantes.append(herramienta)
            
            lineas.append("")  # Espacio entre herramientas
        
        # Links de descarga si faltan herramientas
        if herramientas_faltantes:
            lineas.append(f"{SEPARADOR_SUAVE}")
            lineas.append(f"{EMOJIS['descarga']}  HERRAMIENTAS FALTANTES")
            lineas.append(f"{SEPARADOR_SUAVE}")
            
            for herramienta in herramientas_faltantes:
                if herramienta in FormatUtils.HERRAMIENTAS_DESCARGAS:
                    info_descarga = FormatUtils.HERRAMIENTAS_DESCARGAS[herramienta]
                    
                    lineas.append(f"{EMOJIS['link']} {info_descarga['nombre']}")
                    lineas.append(f"   📍 URL: {info_descarga['url']}")
                    lineas.append(f"   📝 {info_descarga['descripcion']}")
                    
                    # Añadir consejo específico si existe
                    if "consejo" in info_descarga:
                        lineas.append(f"   {EMOJIS['info']} {info_descarga['consejo']}")
                    
                    lineas.append("")  # Espacio entre descargas
        
        # Footer con instrucciones
        if herramientas_faltantes:
            lineas.append(f"{SEPARADOR_SUAVE}")
            lineas.append(f"{EMOJIS['info']}  INSTRUCCIONES DE INSTALACIÓN")
            lineas.append(f"{SEPARADOR_SUAVE}")
            
            instrucciones = [
                "1. 📥 Descarga las herramientas faltantes desde los links anteriores",
                "2. 🛠️  Instala siguiendo los pasos del instalador",
                "3. ⚙️  Añade las rutas de instalación al PATH del sistema",
                "4. 🔄 Reinicia la aplicación y el sistema operativo si es necesario",
                "5. ✅ Verifica que las herramientas sean detectadas correctamente"
            ]
            
            lineas.extend(instrucciones)
            lineas.append("")
        
        return "\n".join(lineas)


    @staticmethod
    def obtener_links_descarga_herramientas(herramientas_faltantes: List[str]) -> str:
        """Obtener lista formateada de links de descarga para herramientas específicas"""
        if not herramientas_faltantes:
            return "✅ Todas las herramientas están instaladas correctamente."
        
        # Constantes de formato
        ANCHO = 55
        SEPARADOR = "─" * ANCHO
        EMOJIS = {
            "titulo": "📦",
            "link": "🔗",
            "info": "💡",
            "paso": "🔸",
            "herramienta": "⚙️",
            "advertencia": "⚠️"
        }
        
        # Construir mensaje
        lineas = []
        
        # Encabezado
        lineas.append(f"\n{SEPARADOR}")
        lineas.append(f"{EMOJIS['titulo']}  LINKS DE DESCARGA  {EMOJIS['herramienta']}")
        lineas.append(f"{SEPARADOR}\n")
        
        # Links por herramienta
        for herramienta in herramientas_faltantes:
            if herramienta in FormatUtils.HERRAMIENTAS_DESCARGAS:
                info = FormatUtils.HERRAMIENTAS_DESCARGAS[herramienta]
                
                # Tarjeta de herramienta
                lineas.append(f"🛠️  {info['nombre']}")
                lineas.append(f"{EMOJIS['link']}  {info['url']}")
                lineas.append(f"{EMOJIS['info']}  {info['descripcion']}")
                
                # Información adicional si existe
                if "version_recomendada" in info:
                    lineas.append(f"📌 Versión recomendada: {info['version_recomendada']}")
                if "sistema_operativo" in info:
                    lineas.append(f"💻 Compatible con: {info['sistema_operativo']}")
                if "notas_instalacion" in info:
                    lineas.append(f"📝 Notas: {info['notas_instalacion']}")
                
                lineas.append("")  # Espacio entre herramientas
        
        # Instrucciones generales
        lineas.append(f"{SEPARADOR}")
        lineas.append(f"{EMOJIS['info']}  GUÍA RÁPIDA DE INSTALACIÓN")
        lineas.append(f"{SEPARADOR}")
        
        pasos = [
            f"{EMOJIS['paso']} Descarga los instaladores desde los links anteriores",
            f"{EMOJIS['paso']} Ejecuta cada instalador como administrador",
            f"{EMOJIS['paso']} Durante la instalación, selecciona 'Add to PATH' si está disponible",
            f"{EMOJIS['paso']} Para JDK, configura la variable de entorno JAVA_HOME",
            f"{EMOJIS['paso']} Reinicia tu terminal/consola después de cada instalación",
            f"{EMOJIS['paso']} Verifica con: adb --version, java -version, etc."
        ]
        
        lineas.extend(pasos)
        lineas.append("")
        
        # Advertencia importante
        lineas.append(f"{EMOJIS['advertencia']}  IMPORTANTE")
        lineas.append(f"{EMOJIS['advertencia']}  Después de instalar, cierra completamente esta aplicación")
        lineas.append(f"{EMOJIS['advertencia']}  y ábrela nuevamente para que detecte las herramientas.")
        
        return "\n".join(lineas)


    # Sugerencia: Añadir estos datos mejorados a HERRAMIENTAS_DESCARGAS
    HERRAMIENTAS_DESCARGAS_MEJORADO = {
        "platform_tools": {
            "nombre": "Android SDK Platform-Tools",
            "url": "https://developer.android.com/studio/releases/platform-tools",
            "descripcion": "Incluye ADB, Fastboot y otras herramientas esenciales",
            "version_recomendada": "Más reciente",
            "sistema_operativo": "Windows, macOS, Linux",
            "consejo": "Extrae en una ruta sin espacios (ej: C:\\android-tools\\)",
            "notas_instalacion": "Añade la carpeta 'platform-tools' al PATH del sistema"
        },
        "build_tools": {
            "nombre": "Android SDK Build-Tools",
            "url": "https://developer.android.com/studio/releases/build-tools",
            "descripcion": "Incluye AAPT, APKSigner, zipalign y herramientas de compilación",
            "version_recomendada": "API 33+",
            "sistema_operativo": "Windows, macOS, Linux",
            "consejo": "Instala desde Android Studio SDK Manager"
        },
        "jdk": {
            "nombre": "Java Development Kit (JDK)",
            "url": "https://www.oracle.com/java/technologies/javase-jdk17-downloads.html",
            "descripcion": "JDK 17+ para firmar APKs con JarSigner",
            "version_recomendada": "JDK 17 LTS",
            "sistema_operativo": "Windows, macOS, Linux",
            "notas_instalacion": "Configura las variables JAVA_HOME y añade bin al PATH"
        }
    }
    @staticmethod
    def verificar_herramientas_criticas(estado_herramientas: Dict) -> Dict:
        """Verificar herramientas críticas y retornar estado detallado"""
        herramientas_criticas = ['platform_tools', 'build_tools', 'jdk']
        herramientas_faltantes = []
        herramientas_instaladas = []
        
        for herramienta in herramientas_criticas:
            if herramienta in estado_herramientas:
                if estado_herramientas[herramienta]["instalado"]:
                    herramientas_instaladas.append(herramienta)
                else:
                    herramientas_faltantes.append(herramienta)
        
        return {
            "todas_instaladas": len(herramientas_faltantes) == 0,
            "faltantes": herramientas_faltantes,
            "instaladas": herramientas_instaladas,
            "mensaje_estado": FormatUtils.crear_mensaje_estado_herramientas(estado_herramientas),
            "links_descarga": FormatUtils.obtener_links_descarga_herramientas(herramientas_faltantes)
        }

    @staticmethod
    def formatear_resumen_apk(
        parsed_info: Dict,
        signature_info: Dict,
        apk_name: str,
        apk_size_mb: float = None,
        pci_analysis: Dict = None
    ) -> str:
        build_mode = FormatUtils._detectar_modo_build_seguro(parsed_info)
        es_info_no_confiable = FormatUtils._evaluar_calidad_informacion(parsed_info)
        
        # 🟦 ENCABEZADO PRINCIPAL
        contenido = "\n" + "═" * 45 + "\n"
        contenido += "🔷 INFORMACIÓN DEL APK\n"
        contenido += "═" * 45 + "\n"
        
        # ✅ ADVERTENCIA MEJORADA
        if es_info_no_confiable:
            contenido += "⚠️  INFORMACIÓN POTENCIALMENTE INCOMPLETA\n"
            contenido += "    Puede deberse a:\n"
            contenido += "    • Errores en el AndroidManifest.xml\n"
            contenido += "    • APK corrupto u ofuscado\n"
            contenido += "    • Problemas con herramientas de análisis\n\n"
        
        # ✅ MOSTRAR INFORMACIÓN CON VALORES POR DEFECTO MEJORADOS
        contenido += f" Archivo: {apk_name}\n"
        contenido += f" Paquete: {parsed_info.get('package', 'No detectado')}\n"
        contenido += f" Aplicación: {parsed_info.get('app_label', 'No detectado')}\n"
        contenido += f" Versión: {parsed_info.get('version_name', 'No detectado')} ({parsed_info.get('version_code', 'No detectado')})\n"
        contenido += f" Target SDK: {parsed_info.get('target_sdk', 'No detectado')}\n"

        if apk_size_mb is not None:
            contenido += f" Tamaño: {apk_size_mb:.1f} MB\n"

        contenido += f" Modo: {build_mode}\n"

        # 🟦 INFORMACIÓN DE FIRMA
        contenido += "\n" + "─" * 45 + "\n"
        contenido += "🔐 INFORMACIÓN DE FIRMA\n"
        contenido += "─" * 45 + "\n"
        
        signature_versions = signature_info.get("signature_versions", [])
        if signature_versions == ["v2"]:
            contenido += "📝 Firma válida: v2 - No Compatible Con Maxstore\n"
        else:
            signature_text = ", ".join(signature_versions) if signature_versions else "No firmado"
            is_valid = signature_info.get("is_valid", False)
            if signature_versions:
                estado = " (Verificada)" if is_valid else " (Verificada)"
                contenido += f"📝 Firma válida: {signature_text}{estado}\n"
            else:
                contenido += f"📝 Firma válida: {signature_text}\n"
        
        cert_hash = signature_info.get('cert_hash', 'No disponible')
        contenido += f"🔑 Hash SHA-256: {cert_hash}\n"

        # 🟦 DETALLES TÉCNICOS
        contenido += "\n" + "─" * 45 + "\n"
        contenido += "🧠 DETALLES TÉCNICOS\n"
        contenido += "─" * 45 + "\n"

        native_codes = parsed_info.get('native_codes', 'Android')
        contenido += f"💻 Soporte nativo: {native_codes}\n"

        min_sdk = parsed_info.get('min_sdk', parsed_info.get('sdk_version', 'No detectado'))
        contenido += f"📱 Min SDK: {min_sdk}\n"

        # 🟦 PERMISOS SENSIBLES
        contenido += "\n" + "─" * 45 + "\n"
        contenido += "🚨 PERMISOS SENSIBLES\n"
        contenido += "─" * 45 + "\n"
        
        permissions = parsed_info.get("permissions", [])
        sensitive_perms = FormatUtils._filtrar_permisos_sensibles(permissions)

        if sensitive_perms:
            for perm in sensitive_perms[:10]:
                perm_short = perm.replace("android.permission.", "")
                contenido += f"• {perm_short}\n"
            if len(sensitive_perms) > 10:
                contenido += f"• ... y {len(sensitive_perms) - 10} permisos más\n"
        else:
            contenido += "No se detectaron permisos sensibles\n"

        # 🟦 ESTADÍSTICAS
        contenido += "\n" + "─" * 45 + "\n"
        contenido += "📊 ESTADÍSTICAS\n"
        contenido += "─" * 45 + "\n"
        contenido += f"Total de permisos: {len(permissions)}\n"
        contenido += f"Permisos sensibles: {len(sensitive_perms)}\n"

        # 🟦 PCI DSS
        if pci_analysis:
            contenido += "\n" + "═" * 45 + "\n"
            contenido += "🛡️  RESUMEN PCI DSS\n"
            contenido += "═" * 45 + "\n"
            contenido += FormatUtils._generar_resumen_pci_completo(pci_analysis)

        return contenido

    @staticmethod
    def _detectar_modo_build_seguro(parsed_info: Dict) -> str:
        """Detección segura del modo de build con manejo robusto de None"""
        print("🔍 DEBUG - Iniciando detección segura de modo build...")
        
        try:
            # Estrategia 1: Verificar flags explícitos del APKParser
            debug_mode = parsed_info.get("debug_mode")
            is_debuggable = parsed_info.get("is_debuggable")
            
            if debug_mode is True:
                print("🔍 DEBUG - Detectado por debug_mode: True")
                return "Debug"
            
            if is_debuggable is True:
                print("🔍 DEBUG - Detectado por is_debuggable: True")
                return "Debug"
            
            # Estrategia 2: Búsqueda segura en raw_info
            raw_info = parsed_info.get("raw_info")
            if raw_info and isinstance(raw_info, str):
                # Convertir a minúsculas de forma segura
                raw_lower = raw_info.lower()
                
                # Patrones específicos de debug
                debug_patterns = [
                    "application-debuggable",
                    "debuggable=true",
                    "android:debuggable=\"true\"",
                    "debuggable=\"true\""
                ]
                
                for pattern in debug_patterns:
                    if pattern in raw_lower:
                        print(f"🔍 DEBUG - Detectado por pattern: {pattern}")
                        return "Debug"
                
                # Búsqueda contextual de 'debuggable'
                if "debuggable" in raw_lower:
                    lines = raw_info.split('\n')
                    for line in lines:
                        if 'debuggable' in line.lower():
                            print(f"🔍 DEBUG - Línea con debuggable: {line.strip()}")
                            if 'true' in line.lower():
                                print("🔍 DEBUG - Detectado debuggable=true en contexto")
                                return "Debug"
            else:
                print("🔍 DEBUG - raw_info no disponible o no es string")
            
            # Estrategia 3: Análisis seguro de metadatos y nombres
            package = parsed_info.get("package", "")
            version_name = parsed_info.get("version_name", "")
            app_label = parsed_info.get("app_label", "")
            apk_filename = parsed_info.get("apk_filename", "")
            
            # Convertir a minúsculas de forma segura
            package_lower = package.lower() if package else ""
            version_name_lower = version_name.lower() if version_name else ""
            app_label_lower = app_label.lower() if app_label else ""
            apk_filename_lower = apk_filename.lower() if apk_filename else ""
            
            # Indicadores fuertes de debug
            debug_indicators = ['debug', 'test', 'dev', 'uat', 'staging', 'preprod']
            
            # Buscar en diferentes campos de forma segura
            search_fields = [
                package_lower, 
                version_name_lower, 
                app_label_lower, 
                apk_filename_lower
            ]
            
            for field in search_fields:
                for indicator in debug_indicators:
                    if field and indicator in field:
                        print(f"🔍 DEBUG - Detectado indicador '{indicator}' en campo")
                        return "Debug"
            
            # Estrategia 4: Características típicas de builds debug
            version_code = parsed_info.get("version_code", "")
            if version_code and isinstance(version_code, str):
                version_code_lower = version_code.lower()
                if any(indicator in version_code_lower for indicator in ['debug', 'test', 'dev']):
                    print(f"🔍 DEBUG - Indicador debug en version_code: {version_code}")
                    return "Debug"
            
            # Estrategia 5: Verificar si es un APK de desarrollo por el package name
            if package_lower:
                dev_package_indicators = ['.debug', '.test', '.dev', '.sample', '.demo']
                for indicator in dev_package_indicators:
                    if indicator in package_lower:
                        print(f"🔍 DEBUG - Package name indica desarrollo: {package}")
                        return "Debug"
            
            # Estrategia 6: Por el contexto de análisis (fallback)
            aapt_success = parsed_info.get('aapt_success', True)
            if not aapt_success:
                print("🔍 DEBUG - aapt falló, asumiendo Release por precaución")
                return "Release"
                
        except Exception as e:
            print(f"❌ ERROR en _detectar_modo_build_seguro: {e}")
            # En caso de error, retornar Release por seguridad
            return "Release"
            
        # Por defecto, asumir Release (más común en producción)
        print("🔍 DEBUG - No se detectaron indicadores Debug, usando Release por defecto")
        return "Release"

    @staticmethod
    def _evaluar_calidad_informacion(parsed_info: Dict) -> bool:
        """Evaluar si la información del APK es confiable"""
        campos_criticos = ['package', 'app_label', 'version_name', 'version_code', 'target_sdk']
        campos_faltantes = 0
        
        for campo in campos_criticos:
            valor = parsed_info.get(campo)
            # Considerar faltante si es None, 'No detectado', o string vacío
            if not valor or valor == 'No detectado' or (isinstance(valor, str) and valor.strip() == ''):
                campos_faltantes += 1
                print(f"🔍 DEBUG - Campo crítico faltante: {campo}")
        
        # Considerar no confiable si faltan 3 o más campos críticos
        es_no_confiable = campos_faltantes >= 3
        if es_no_confiable:
            print(f"🔍 DEBUG - Información no confiable: {campos_faltantes} campos críticos faltantes")
        
        return es_no_confiable

    @staticmethod
    def _generar_resumen_pci_completo(pci_analysis: Dict) -> str:
        """Generar resumen completo del análisis PCI DSS en el formato solicitado"""
        if not pci_analysis:
            return "Análisis PCI DSS no disponible"
        
        print(f"🔍 DEBUG FORMATUTILS - Generando resumen PCI: {type(pci_analysis)}")
        
        contenido = ""
        
        if isinstance(pci_analysis, dict):
            # Buscar la estructura de resumen PCI DSS
            resumen = pci_analysis.get('resumen', {})
            hallazgos_altos = pci_analysis.get('hallazgos_altos', [])
            
            # Si no encuentra en la estructura esperada, buscar en otras ubicaciones
            if not resumen and not hallazgos_altos:
                # Buscar estructura alternativa del pci_dss_analyzer
                if 'estado_general' in pci_analysis:
                    resumen = pci_analysis
                if 'hallazgos_criticos' in pci_analysis:
                    hallazgos_altos = pci_analysis.get('hallazgos_criticos', [])
                elif 'hallazgos_altos' in pci_analysis:
                    hallazgos_altos = pci_analysis.get('hallazgos_altos', [])
            
            # 📊 ENCABEZADO DE RESUMEN
            estado = resumen.get('estado_general', pci_analysis.get('estado_general', 'NO CUMPLE'))
            puntuacion = resumen.get('puntuacion', pci_analysis.get('puntuacion', '0'))
            nivel_riesgo = resumen.get('nivel_riesgo', pci_analysis.get('nivel_riesgo', 'ALTO'))
            
            contenido += f"📊 Cumplimiento General: {estado}\n"
            contenido += f"🚨 Nivel de Riesgo: {nivel_riesgo}\n\n"
            
            # 🔴 HALLAZGOS DE ALTO RIESGO
            if hallazgos_altos:
                contenido += "🔴 HALLAZGOS DE ALTO RIESGO:\n"
                contenido += "=" * 50 + "\n\n"
                
                for i, hallazgo in enumerate(hallazgos_altos[:5], 1):
                    if isinstance(hallazgo, dict):
                        titulo = hallazgo.get('titulo', hallazgo.get('descripcion', 'Hallazgo sin título'))
                        requisito = hallazgo.get('requisito', 'N/A')
                        riesgo = hallazgo.get('riesgo', 'ALTO')
                        impacto = hallazgo.get('impacto', 'No especificado')
                        recomendacion = hallazgo.get('recomendacion', 'No especificada')
                    else:
                        titulo = str(hallazgo)
                        requisito = "N/A"
                        riesgo = "ALTO"
                        impacto = "No especificado"
                        recomendacion = "Revisar en análisis detallado"
                    
                    contenido += f"{i}. {titulo}\n"
                    contenido += f"   • Requisito: {requisito}\n"
                    contenido += f"   • Riesgo: {riesgo}\n"
                    contenido += f"   • Impacto: {impacto}\n"
                    contenido += f"   • Recomendación: {recomendacion}\n\n"
            else:
                contenido += "✅ No se encontraron hallazgos de alto riesgo\n\n"
            
            # 📈 RESUMEN ESTADÍSTICO
            estadisticas = resumen.get('estadisticas', {})
            cumplidos = estadisticas.get('cumplidos', pci_analysis.get('requisitos_cumplidos', 0))
            total = estadisticas.get('total', pci_analysis.get('total_requisitos', 0))
            hallazgos_count = estadisticas.get('hallazgos_altos', len(hallazgos_altos))
            
            if total > 0:
                porcentaje = (cumplidos / total) * 100
            else:
                porcentaje = 0
                
            contenido += "📈 Resumen Estadístico:\n"
            contenido += f"   • Requisitos cumplidos: {cumplidos}/{total}\n"
            contenido += f"   • Porcentaje de cumplimiento: {porcentaje:.1f}%\n"
            contenido += f"   • Hallazgos ALTOS encontrados: {hallazgos_count}\n\n"
            
            contenido += "💡 Para el análisis completo, ve a 'Comandos' → Filtro 'PCI DSS'"
            
        else:
            contenido += "Formato de análisis PCI DSS no reconocido\n"
        
        return contenido

    @staticmethod
    def _filtrar_permisos_sensibles(permissions: List[str]) -> List[str]:
        """Filtrar permisos considerados sensibles"""
        keywords_sensibles = [
            "INTERNET", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION",
            "CAMERA", "RECORD_AUDIO", "READ_CONTACTS", "WRITE_CONTACTS",
            "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE", "READ_PHONE_STATE",
            "CALL_PHONE", "READ_SMS", "SEND_SMS", "ACCESS_BACKGROUND_LOCATION",
            "BILLING", "FOREGROUND_SERVICE", "BLUETOOTH", "NFC", "BIOMETRIC",
            "FINGERPRINT", "ACCESS_NETWORK_STATE",
        ]

        sensitive_perms = []
        if permissions:
            for perm in permissions:
                if perm and isinstance(perm, str):
                    perm_upper = perm.upper()
                    if any(keyword in perm_upper for keyword in keywords_sensibles):
                        sensitive_perms.append(perm)

        return sensitive_perms

    # ========== MÉTODOS DE APKParser INTEGRADOS ==========

    @staticmethod
    def analizar_apk_completo(apk_path: Path, aapt_path: Path) -> Dict[str, Any]:
        """Método unificado para análisis completo de APK"""
        print(f"🔍 ANALIZANDO APK: {apk_path.name}")
        
        # Ejecutar aapt y parsear resultado
        parsed_info = FormatUtils._ejecutar_aapt_y_parsear(apk_path, aapt_path)
        
        # Evaluar calidad de la información
        calidad_info = FormatUtils._evaluar_calidad_completa(parsed_info)
        
        # Agregar información de calidad al resultado
        parsed_info['calidad_analisis'] = calidad_info
        parsed_info['es_confiable'] = calidad_info['es_confiable']
        
        print(f"🔍 ANÁLISIS COMPLETADO - Confiable: {calidad_info['es_confiable']}")
        
        return parsed_info

    @staticmethod
    def _ejecutar_aapt_y_parsear(apk_path: Path, aapt_path: Path) -> Dict[str, Any]:
        """Ejecutar aapt y parsear el output con el parser mejorado"""
        try:
            if not apk_path.exists():
                raise FileNotFoundError(f"APK no encontrada: {apk_path}")
            
            if not aapt_path.exists():
                raise FileNotFoundError(f"aapt no encontrado: {aapt_path}")
            
            # Ejecutar comando aapt
            comando = [str(aapt_path), 'dump', 'badging', str(apk_path)]
            print(f"🔍 EJECUTANDO AAPT: {' '.join(comando)}")
            
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = resultado.stdout
            error_output = resultado.stderr
            
            print(f"🔍 AAPT OUTPUT: {len(output)} caracteres, Return code: {resultado.returncode}")
            
            if resultado.returncode != 0:
                print(f"⚠️ AAPT ADVERTENCIA - Código: {resultado.returncode}")
                if error_output:
                    print(f"⚠️ AAPT STDERR: {error_output[:500]}...")
            
            # Parsear output con el método mejorado
            parsed_info = FormatUtils._parsear_output_aapt_avanzado(output, apk_path.name)
            
            # Agregar información de ejecución
            parsed_info['apk_path'] = str(apk_path)
            parsed_info['aapt_success'] = resultado.returncode == 0
            parsed_info['aapt_error'] = error_output if resultado.returncode != 0 else None
            
            return parsed_info
            
        except subprocess.TimeoutExpired:
            print("❌ ERROR: Timeout ejecutando aapt")
            return FormatUtils._crear_respuesta_error("Timeout ejecutando aapt", apk_path.name)
        except Exception as e:
            print(f"❌ ERROR en _ejecutar_aapt_y_parsear: {e}")
            return FormatUtils._crear_respuesta_error(str(e), apk_path.name)

    @staticmethod
    def _parsear_output_aapt_avanzado(output: str, apk_filename: str = "") -> Dict[str, Any]:
        """Parser avanzado para output de aapt dump badging"""
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
            'raw_info': output,
            'apk_filename': apk_filename,
            'compile_sdk': 'No detectado',
            'platform_build_version': 'No detectado'
        }
        
        try:
            print("🔍 ANALIZANDO OUTPUT AAPT...")
            
            # ✅ DETECCIÓN EXHAUSTIVA DE DEBUG
            if output and isinstance(output, str):
                output_lower = output.lower()
                debug_detectado = False
                
                # Patrones de debug
                debug_patterns = [
                    "application-debuggable",
                    "debuggable=true",
                    "android:debuggable=\"true\""
                ]
                
                for pattern in debug_patterns:
                    if pattern in output_lower:
                        debug_detectado = True
                        print(f"🔍 DEBUG DETECTADO: {pattern}")
                        break
                
                parsed_info['debug_mode'] = debug_detectado
                parsed_info['is_debuggable'] = debug_detectado
            
            # ✅ SEPARAR Y PROCESAR LÍNEAS
            if output:
                lines = output.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Package info (línea más importante)
                    if line.startswith('package:'):
                        package_data = FormatUtils._parsear_linea_package_completa(line)
                        if package_data:
                            parsed_info.update(package_data)
                    
                    # SDK info
                    elif line.startswith('sdkVersion:'):
                        valor = FormatUtils._extraer_valor_entre_comillas(line)
                        if valor:
                            parsed_info['sdk_version'] = valor
                            parsed_info['min_sdk'] = valor
                    elif line.startswith('targetSdkVersion:'):
                        valor = FormatUtils._extraer_valor_entre_comillas(line)
                        if valor:
                            parsed_info['target_sdk'] = valor
                    
                    # Application label
                    elif line.startswith('application-label:'):
                        valor = FormatUtils._extraer_valor_entre_comillas(line)
                        if valor:
                            parsed_info['app_label'] = valor
                    elif line.startswith("application:") and "label=" in line:
                        label_match = re.search(r"label='([^']*)'", line)
                        if label_match:
                            parsed_info['app_label'] = label_match.group(1)
                    
                    # Permissions
                    elif line.startswith('uses-permission:'):
                        permission = FormatUtils._extraer_valor_entre_comillas(line)
                        if permission and permission not in parsed_info['permissions']:
                            parsed_info['permissions'].append(perm)
                    
                    # Información de compilación
                    elif 'platformBuildVersionName' in line:
                        valor = FormatUtils._extraer_valor_entre_comillas(line)
                        if valor:
                            parsed_info['platform_build_version'] = valor
                    elif 'compileSdkVersion' in line:
                        valor = FormatUtils._extraer_valor_entre_comillas(line)
                        if valor:
                            parsed_info['compile_sdk'] = valor
            
            print(f"🔍 PARSER COMPLETADO - Package: {parsed_info['package']}")
            
        except Exception as e:
            print(f"❌ ERROR en _parsear_output_aapt_avanzado: {e}")
        
        return parsed_info

    @staticmethod
    def _parsear_linea_package_completa(line: str) -> Dict[str, str]:
        """Parsear línea de package con todas las informaciones"""
        result = {}
        
        try:
            if not line:
                return result
                
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
                    
        except Exception as e:
            print(f"❌ ERROR en _parsear_linea_package_completa: {e}")
        
        return result

    @staticmethod
    def _extraer_valor_entre_comillas(line: str) -> str:
        """Extraer valor entre comillas simples de forma segura"""
        try:
            if not line:
                return None
            matches = re.findall(r"'([^']*)'", line)
            if matches:
                return matches[0]
        except Exception as e:
            print(f"❌ ERROR en _extraer_valor_entre_comillas: {e}")
        return None

    @staticmethod
    def _evaluar_calidad_completa(parsed_info: Dict) -> Dict[str, Any]:
        """Evaluación completa de la calidad de la información"""
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

    @staticmethod
    def _crear_respuesta_error(mensaje_error: str, apk_filename: str) -> Dict[str, Any]:
        """Crear respuesta de error estandarizada"""
        return {
            'package': 'Error en análisis',
            'version_code': 'Error',
            'version_name': 'Error',
            'app_label': 'Error',
            'sdk_version': 'Error',
            'target_sdk': 'Error',
            'permissions': [],
            'debug_mode': False,
            'is_debuggable': False,
            'raw_info': f"Error: {mensaje_error}",
            'apk_filename': apk_filename,
            'aapt_success': False,
            'error': mensaje_error
        }

    # ========== MÉTODOS ORIGINALES MANTENIDOS ==========

    @staticmethod
    def formatear_tiempo_ejecucion(segundos: float) -> str:
        """Formatear tiempo de ejecución"""
        if segundos < 1:
            return f"{segundos*1000:.0f} ms"
        elif segundos < 60:
            return f"{segundos:.1f} segundos"
        else:
            minutos = segundos / 60
            return f"{minutos:.1f} minutos"

    @staticmethod
    def formatear_lista_permisos(permissions: List[str], max_items: int = 10) -> str:
        """Formatear lista de permisos para mostrar"""
        if not permissions:
            return "No se encontraron permisos"

        if len(permissions) <= max_items:
            return "\n".join([f"• {perm}" for perm in permissions])
        else:
            primeros = "\n".join([f"• {perm}" for perm in permissions[:max_items]])
            return primeros + f"\n• ... y {len(permissions) - max_items} permisos más"

    @staticmethod
    def _acortar_ruta(ruta: str) -> str:
        """Acortar rutas largas para mejor visualización"""
        if ruta and len(ruta) > 50:
            partes = ruta.split("\\")
            if len(partes) > 3:
                return f"{partes[0]}\\...\\{partes[-2]}\\{partes[-1]}"
        return ruta

    @staticmethod
    def formatear_info_firma_avanzada(signature_info: Dict) -> str:
        """Formato avanzado para información de firma"""
        contenido = "\n" + "═" * 45 + "\n"
        contenido += "🔍 DETALLES DE FIRMA\n"
        contenido += "═" * 45 + "\n"

        versions = signature_info.get("signature_versions", [])
        
        if versions == ["v2"]:
            signature_text = "v2 - Firma Predeterminada de Android"
            estado = "✅ Válida"
        else:
            if versions:
                signature_text = ', '.join(versions)
                estado = "✅ Válida" if signature_info.get("is_valid", False) else "❌ Inválida"
            else:
                signature_text = "No firmado"
                estado = "❌ Inválida"
                
        contenido += f"🔸 Versiones: {signature_text}\n"
        contenido += f"📄 Estado: {estado}\n"

        integridad = "✅ Intacta" if signature_info.get("integrity_ok") else "⚠️ Comprometida"
        contenido += f"🧱 Integridad: {integridad}\n"

        cert_hash = signature_info.get("cert_hash", "No disponible")
        if versions != ["v2"] and cert_hash and cert_hash != "No disponible" and len(cert_hash) > 40:
            hash_cortado = f"{cert_hash[:20]}...{cert_hash[-20:]}"
            contenido += f"🔑 Hash: {hash_cortado}\n"
        elif versions == ["v2"]:
            contenido += f"🔑 Hash: No disponible (firma predeterminada)\n"
        else:
            contenido += f"🔑 Hash: {cert_hash}\n"

        cert_info = signature_info.get("certificate_info", "")
        if cert_info and versions != ["v2"]:
            contenido += f"\n📋 Certificado: {cert_info}\n"

        return contenido

    @staticmethod
    def get_apk_size_mb(apk_path):
        """Obtener el tamaño del archivo APK en megabytes"""
        try:
            if apk_path and isinstance(apk_path, Path) and apk_path.exists():
                size_bytes = apk_path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                print(f"DEBUG: Tamaño del APK calculado - {size_mb:.1f} MB")
                return round(size_mb, 1)
            else:
                print(f"DEBUG: APK path no válido - {apk_path}")
        except Exception as e:
            print(f"DEBUG: Error obteniendo tamaño del APK: {e}")

        return None

    @staticmethod
    def extraer_hash_certificado(cert_data: bytes) -> str:
        """Extraer hash SHA-256 del certificado"""
        try:
            import hashlib
            sha256_hash = hashlib.sha256(cert_data).hexdigest().upper()
            return ':'.join([sha256_hash[i:i+2] for i in range(0, len(sha256_hash), 2)])
        except Exception as e:
            print(f"ERROR calculando hash: {e}")
            return "Error en cálculo"


# Clases auxiliares (mantenidas igual)
class SingleInstanceApp:
    """Clase para asegurar que solo se ejecute una instancia de la aplicación"""
    
    def __init__(self, app_name="ISVtoolkit"):
        self.app_name = app_name
        self.socket = None
        self.is_running = False

    def is_already_running(self):
        """Verificar si ya hay una instancia de la aplicación ejecutándose"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(("localhost", 0))
            self.socket.getsockname()

            import hashlib
            app_hash = hashlib.md5(self.app_name.encode()).hexdigest()[:8]
            port = 50000 + int(app_hash, 16) % 10000

            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(("localhost", port))
            test_socket.listen(1)

            self.is_running = False
            return False

        except socket.error:
            self.is_running = True
            return True

    def show_warning_message(self):
        """Mostrar mensaje de advertencia cuando ya hay una instancia ejecutándose"""
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Aplicación ya en ejecución",
            f"'{self.app_name}' ya se está ejecutando.\n\n"
            "Por favor, cierra la instancia actual antes de abrir una nueva.",
        )
        root.destroy()

    def cleanup(self):
        """Limpiar recursos al cerrar la aplicación"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

def check_single_instance():
    """Función para verificar instancia única - usar en main.py"""
    app_instance = SingleInstanceApp("APK Inspector")
    if app_instance.is_already_running():
        app_instance.show_warning_message()
        return False
    return True