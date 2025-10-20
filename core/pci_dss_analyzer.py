"""
PCI DSS Analyzer - Análisis de cumplimiento con PCI DSS para aplicaciones Android
Payment Card Industry Data Security Standard
"""

import re
from typing import Dict, List, Any, Tuple
from pathlib import Path

class PCIDSSAnalyzer:
    def __init__(self):
        self.requisitos_pci = self._cargar_requisitos_pci()
        self.permisos_sensibles_pci = self._cargar_permisos_sensibles()
    
    def _cargar_requisitos_pci(self) -> Dict:
        """Cargar requisitos PCI DSS v4.0"""
        return {
            'requisito_1': 'Proteger la red',
            'requisito_2': 'Configuraciones seguras',
            'requisito_3': 'Protección de datos de titulares',
            'requisito_4': 'Cifrado de datos en tránsito',
            'requisito_5': 'Protección contra malware',
            'requisito_6': 'Desarrollo de software seguro',
            'requisito_7': 'Control de acceso',
            'requisito_8': 'Autenticación',
            'requisito_9': 'Seguridad física',
            'requisito_10': 'Monitoreo y testing',
            'requisito_11': 'Seguridad de sistemas',
            'requisito_12': 'Política de seguridad'
        }
    
    def _cargar_permisos_sensibles(self) -> Dict:
        """Cargar permisos sensibles para PCI DSS"""
        return {
            'alto_riesgo': [
                'android.permission.READ_EXTERNAL_STORAGE',
                'android.permission.WRITE_EXTERNAL_STORAGE',
                'android.permission.ACCESS_NETWORK_STATE',
                'android.permission.INTERNET',
                'android.permission.NFC',
                'android.permission.BLUETOOTH',
                'android.permission.BLUETOOTH_ADMIN'
            ],
            'medio_riesgo': [
                'android.permission.CAMERA',
                'android.permission.RECORD_AUDIO',
                'android.permission.ACCESS_FINE_LOCATION',
                'android.permission.ACCESS_COARSE_LOCATION'
            ],
            'permisos_pago': [
                'com.android.vending.BILLING',
                'com.google.android.c2dm.permission.RECEIVE',
                'android.permission.WAKE_LOCK'
            ]
        }
    
    def analizar_cumplimiento_pci(self, parsed_info: Dict, signature_info: Dict, apk_path: Path = None) -> Dict:
        """Analizar cumplimiento PCI DSS de la aplicación"""
        
        resultados = {
            'cumplimiento_general': 'NO_EVALUADO',
            'puntuacion_total': 0,
            'requisitos_cumplidos': [],
            'requisitos_no_cumplidos': [],
            'hallazgos_criticos': [],
            'hallazgos_altos': [],
            'recomendaciones': [],
            'nivel_riesgo': 'DESCONOCIDO'
        }
        
        # Análisis de requisitos individuales
        self._analizar_requisito_3(parsed_info, resultados)  # Protección datos
        self._analizar_requisito_4(parsed_info, resultados)  # Cifrado tránsito
        self._analizar_requisito_6(parsed_info, signature_info, resultados)  # Desarrollo seguro
        self._analizar_requisito_7(parsed_info, resultados)  # Control acceso
        self._analizar_requisito_8(parsed_info, resultados)  # Autenticación
        
        # Calcular cumplimiento general
        self._calcular_cumplimiento_general(resultados)
        
        # Filtrar hallazgos ALTOS
        self._filtrar_hallazgos_altos(resultados)
        
        return resultados
    
    def _analizar_requisito_3(self, parsed_info: Dict, resultados: Dict):
        """Requisito 3: Protección de datos de titulares de tarjetas"""
        hallazgos = []
        permisos = parsed_info.get('permissions', [])
        
        # Verificar almacenamiento seguro
        if 'android.permission.WRITE_EXTERNAL_STORAGE' in permisos:
            hallazgos.append({
                'requisito': '3.2.1',
                'titulo': 'Almacenamiento inseguro de datos',
                'tipo': 'ALMACENAMIENTO_INSECURO',
                'nivel': 'ALTO',
                'descripcion': 'App puede escribir en almacenamiento externo sin cifrado',
                'recomendacion': 'Usar almacenamiento interno cifrado para datos sensibles de pago',
                'impacto': 'Exposición de datos de tarjetas en almacenamiento no seguro'
            })
        
        # Verificar permisos de lectura de almacenamiento
        if 'android.permission.READ_EXTERNAL_STORAGE' in permisos:
            hallazgos.append({
                'requisito': '3.2.2',
                'titulo': 'Lectura de almacenamiento externo',
                'tipo': 'LECTURA_ALMACENAMIENTO',
                'nivel': 'MEDIO',
                'descripcion': 'App puede leer almacenamiento externo',
                'recomendacion': 'Validar que no lee datos de tarjetas de almacenamiento externo',
                'impacto': 'Posible acceso a datos sensibles en almacenamiento compartido'
            })
        
        # Verificar si la app maneja datos sensibles
        if self._app_maneja_datos_sensibles(parsed_info):
            hallazgos.append({
                'requisito': '3.1',
                'titulo': 'App maneja datos de pago',
                'tipo': 'DATOS_SENSIBLES',
                'nivel': 'ALTO',
                'descripcion': 'Aplicación procesa información de pagos o tarjetas',
                'recomendacion': 'Implementar cifrado de datos en reposo y políticas de retención',
                'impacto': 'Exposición de datos de tarjetas si no se protege adecuadamente'
            })
        
        if hallazgos:
            resultados['requisitos_no_cumplidos'].append('Requisito 3')
            resultados['hallazgos_criticos'].extend(hallazgos)
        else:
            resultados['requisitos_cumplidos'].append('Requisito 3')
    
    def _analizar_requisito_4(self, parsed_info: Dict, resultados: Dict):
        """Requisito 4: Cifrado de datos en tránsito"""
        hallazgos = []
        permisos = parsed_info.get('permissions', [])
        
        # Verificar uso de internet sin restricciones
        if 'android.permission.INTERNET' in permisos:
            hallazgos.append({
                'requisito': '4.1',
                'titulo': 'Comunicaciones de red sin validación TLS',
                'tipo': 'TRANSACCION_RED',
                'nivel': 'ALTO',
                'descripcion': 'App se conecta a internet - requiere validación TLS obligatoria',
                'recomendacion': 'Implementar TLS 1.2+ con validación de certificados para todas las comunicaciones',
                'impacto': 'Intercepción de datos de tarjetas en tránsito si no usa TLS'
            })
        
        # Verificar comunicaciones NFC/Bluetooth para pagos
        if 'android.permission.NFC' in permisos:
            hallazgos.append({
                'requisito': '4.3',
                'titulo': 'Comunicaciones NFC para pagos',
                'tipo': 'PAGO_CONTACTO',
                'nivel': 'ALTO',
                'descripcion': 'App usa NFC - requiere cifrado de comunicaciones de contacto',
                'recomendacion': 'Validar cifrado end-to-end en transacciones NFC',
                'impacto': 'Intercepción de datos de pago en comunicaciones NFC'
            })
        
        if 'android.permission.BLUETOOTH' in permisos:
            hallazgos.append({
                'requisito': '4.4',
                'titulo': 'Comunicaciones Bluetooth',
                'tipo': 'COMUNICACION_BLUETOOTH',
                'nivel': 'MEDIO',
                'descripcion': 'App usa Bluetooth - validar seguridad de conexiones',
                'recomendacion': 'Usar Bluetooth LE con cifrado para comunicaciones sensibles',
                'impacto': 'Intercepción de datos en conexiones Bluetooth inseguras'
            })
        
        if len(hallazgos) > 0:
            resultados['requisitos_no_cumplidos'].append('Requisito 4')
            resultados['hallazgos_criticos'].extend(hallazgos)
        else:
            resultados['requisitos_cumplidos'].append('Requisito 4')
    
    def _analizar_requisito_6(self, parsed_info: Dict, signature_info: Dict, resultados: Dict):
        """Requisito 6: Desarrollo de software seguro"""
        hallazgos = []
        
        # Verificar modo debug (removida verificación de firma)
        if parsed_info.get('debuggable', False):
            hallazgos.append({
                'requisito': '6.3.2',
                'titulo': 'APK en modo depuración',
                'tipo': 'MODO_DEBUG',
                'nivel': 'ALTO',
                'descripcion': 'APK compilado con modo depuración habilitado',
                'recomendacion': 'Compilar en modo release con debuggable=false para producción',
                'impacto': 'Exposición de información sensible y posibles vulnerabilidades'
            })
        
        # Verificar allowBackup
        if parsed_info.get('allow_backup', True):
            hallazgos.append({
                'requisito': '6.4',
                'titulo': 'Backup automático habilitado',
                'tipo': 'BACKUP_HABILITADO',
                'nivel': 'ALTO',
                'descripcion': 'Backup automático habilitado sin cifrado específico',
                'recomendacion': 'Deshabilitar android:allowBackup o implementar cifrado de backup con clave segura',
                'impacto': 'Exposición de datos de aplicación en backups no cifrados'
            })
        
        # Verificar si exporta componentes
        if self._tiene_componentes_exportados(parsed_info):
            hallazgos.append({
                'requisito': '6.5',
                'titulo': 'Componentes exportados sin protección',
                'tipo': 'COMPONENTES_EXPORTADOS',
                'nivel': 'ALTO',
                'descripcion': 'Activity/Service/Receiver exportados sin restricciones',
                'recomendacion': 'Revisar y proteger componentes exportados con permisos',
                'impacto': 'Acceso no autorizado a funcionalidades de la app'
            })
        
        if hallazgos:
            resultados['requisitos_no_cumplidos'].append('Requisito 6')
            resultados['hallazgos_criticos'].extend(hallazgos)
        else:
            resultados['requisitos_cumplidos'].append('Requisito 6')
    
    def _analizar_requisito_7(self, parsed_info: Dict, resultados: Dict):
        """Requisito 7: Control de acceso"""
        hallazgos = []
        permisos = parsed_info.get('permissions', [])
        
        # Verificar permisos de sistema sensibles
        permisos_riesgo = [
            'android.permission.READ_LOGS',
            'android.permission.DUMP',
            'android.permission.SYSTEM_ALERT_WINDOW',
            'android.permission.BIND_DEVICE_ADMIN'
        ]
        
        for perm in permisos_riesgo:
            if perm in permisos:
                hallazgos.append({
                    'requisito': '7.1.1',
                    'titulo': 'Permiso de sistema de alto riesgo',
                    'tipo': 'PERMISO_SISTEMA',
                    'nivel': 'ALTO',
                    'descripcion': f'App tiene permiso de sistema privilegiado: {perm}',
                    'recomendacion': 'Revisar necesidad de este permiso para procesamiento de pagos',
                    'impacto': 'Acceso elevado al sistema potencialmente innecesario para procesamiento de pagos'
                })
        
        # Verificar permisos de ubicación para apps de pago
        if 'android.permission.ACCESS_FINE_LOCATION' in permisos:
            hallazgos.append({
                'requisito': '7.2.1',
                'titulo': 'Acceso a ubicación precisa',
                'tipo': 'UBICACION_PRECISA',
                'nivel': 'MEDIO',
                'descripcion': 'App accede a ubicación GPS precisa',
                'recomendacion': 'Validar necesidad y proteger datos de ubicación',
                'impacto': 'Exposición de información de ubicación del usuario'
            })
        
        if hallazgos:
            resultados['requisitos_no_cumplidos'].append('Requisito 7')
            resultados['hallazgos_criticos'].extend(hallazgos)
        else:
            resultados['requisitos_cumplidos'].append('Requisito 7')
    
    def _analizar_requisito_8(self, parsed_info: Dict, resultados: Dict):
        """Requisito 8: Autenticación"""
        features = parsed_info.get('features', [])
        permisos = parsed_info.get('permissions', [])
        
        hallazgos = []
        
        # Verificar uso de biometrics para autenticación
        biometric_features = [
            'android.hardware.biometrics',
            'android.hardware.fingerprint'
        ]
        
        has_biometric = any(feat in features for feat in biometric_features)
        
        if not has_biometric and self._es_app_pago(parsed_info):
            hallazgos.append({
                'requisito': '8.2.1',
                'titulo': 'Falta autenticación biométrica',
                'tipo': 'AUTH_BIOMETRICA',
                'nivel': 'MEDIO',
                'descripcion': 'App de pago sin soporte para autenticación biométrica',
                'recomendacion': 'Implementar autenticación biométrica para transacciones de pago',
                'impacto': 'Menor seguridad en autenticación para transacciones sensibles'
            })
        
        # Verificar uso de keyguard para seguridad
        if 'android.permission.DISABLE_KEYGUARD' in permisos:
            hallazgos.append({
                'requisito': '8.3.1',
                'titulo': 'Puede deshabilitar keyguard',
                'tipo': 'KEYGUARD_DISABLE',
                'nivel': 'ALTO',
                'descripcion': 'App puede deshabilitar la pantalla de bloqueo',
                'recomendacion': 'Revisar necesidad de este permiso en app de pagos',
                'impacto': 'Posible bypass de seguridad del dispositivo'
            })
        
        if hallazgos:
            resultados['requisitos_no_cumplidos'].append('Requisito 8')
            resultados['hallazgos_criticos'].extend(hallazgos)
        else:
            resultados['requisitos_cumplidos'].append('Requisito 8')
    
    def _app_maneja_datos_sensibles(self, parsed_info: Dict) -> bool:
        """Determinar si la app maneja datos sensibles de pago"""
        app_name = parsed_info.get('app_name', '').lower()
        package_name = parsed_info.get('package_name', '').lower()
        
        keywords_pago = [
            'bank', 'banco', 'payment', 'pago', 'card', 'tarjeta', 'wallet', 
            'billetera', 'pay', 'money', 'dinero', 'transfer', 'transferencia',
            'financi', 'finance', 'credit', 'crédito', 'debit', 'débito'
        ]
        
        return any(keyword in app_name or keyword in package_name 
                  for keyword in keywords_pago)
    
    def _es_app_pago(self, parsed_info: Dict) -> bool:
        """Determinar si es una aplicación de pago"""
        return self._app_maneja_datos_sensibles(parsed_info)
    
    def _tiene_componentes_exportados(self, parsed_info: Dict) -> bool:
        """Verificar si tiene componentes exportados sin protección"""
        # Esta es una verificación básica, en una implementación real
        # se analizaría el AndroidManifest.xml en detalle
        return False  # Simplificado para este ejemplo
    
    def _calcular_cumplimiento_general(self, resultados: Dict):
        """Calcular cumplimiento general PCI DSS"""
        total_requisitos = 5  # Los que estamos analizando
        cumplidos = len(resultados['requisitos_cumplidos'])
        
        puntuacion = (cumplidos / total_requisitos) * 100
        
        resultados['puntuacion_total'] = round(puntuacion, 1)
        
        # Determinar nivel de cumplimiento
        if puntuacion >= 90:
            resultados['cumplimiento_general'] = 'CUMPLE'
            resultados['nivel_riesgo'] = 'BAJO'
        elif puntuacion >= 70:
            resultados['cumplimiento_general'] = 'CUMPLE PARCIALMENTE'
            resultados['nivel_riesgo'] = 'MEDIO'
        else:
            resultados['cumplimiento_general'] = 'NO CUMPLE'
            resultados['nivel_riesgo'] = 'ALTO'
        
        # Generar recomendaciones generales
        self._generar_recomendaciones_generales(resultados)
    
    def _filtrar_hallazgos_altos(self, resultados: Dict):
        """Filtrar solo los hallazgos de nivel ALTO"""
        hallazgos_altos = []
        for hallazgo in resultados.get('hallazgos_criticos', []):
            if hallazgo.get('nivel') == 'ALTO':
                hallazgos_altos.append(hallazgo)
        resultados['hallazgos_altos'] = hallazgos_altos
    
    def _generar_recomendaciones_generales(self, resultados: Dict):
        """Generar recomendaciones basadas en el análisis"""
        recomendaciones = []
        
        if resultados['puntuacion_total'] < 80:
            recomendaciones.append("🔴 Realizar auditoría de seguridad completa antes de procesar pagos")
        
        hallazgos_altos = len(resultados.get('hallazgos_altos', []))
        if hallazgos_altos > 0:
            recomendaciones.append(f"🔴 Corregir {hallazgos_altos} hallazgos de ALTO riesgo antes de producción")
        
        if any('INTERNET' in str(hallazgo) for hallazgo in resultados['hallazgos_criticos']):
            recomendaciones.append("🔐 Implementar Certificate Pinning para conexiones TLS con servidores de pago")
        
        if any('BACKUP' in str(hallazgo) for hallazgo in resultados['hallazgos_criticos']):
            recomendaciones.append("💾 Implementar política de backup cifrado o deshabilitar backup automático")
        
        if any('DEBUG' in str(hallazgo) for hallazgo in resultados['hallazgos_criticos']):
            recomendaciones.append("🛠️ Compilar versión release con minificación y ofuscación habilitadas")
        
        recomendaciones.append("📋 Consultar con QSA (Qualified Security Assessor) para validación PCI DSS completa")
        
        resultados['recomendaciones'] = recomendaciones
    
    def generar_reporte_pci(self, resultados: Dict) -> str:
        """Generar reporte legible de PCI DSS"""
        reporte = "=== ANÁLISIS PCI DSS ===\n\n"
        
        # Resumen ejecutivo
        reporte += f"Estado de Cumplimiento: {resultados['cumplimiento_general']}\n"
        reporte += f"Puntuación: {resultados['puntuacion_total']}%\n"
        reporte += f"Nivel de Riesgo: {resultados['nivel_riesgo']}\n\n"
        
        # Requisitos cumplidos
        reporte += "✅ REQUISITOS CUMPLIDOS:\n"
        if resultados['requisitos_cumplidos']:
            for req in resultados['requisitos_cumplidos']:
                reporte += f"  • {req}\n"
        else:
            reporte += "  No se encontraron requisitos cumplidos\n"
        
        reporte += "\n"
        
        # Requisitos no cumplidos
        reporte += "❌ REQUISITOS NO CUMPLIDOS:\n"
        if resultados['requisitos_no_cumplidos']:
            for req in resultados['requisitos_no_cumplidos']:
                reporte += f"  • {req}\n"
        else:
            reporte += "  Todos los requisitos analizados están cumplidos\n"
        
        reporte += "\n"
        
        # Hallazgos críticos
        reporte += "🔍 HALLAZGOS CRÍTICOS:\n"
        if resultados['hallazgos_criticos']:
            for hallazgo in resultados['hallazgos_criticos']:
                nivel_emoji = "🔴" if hallazgo['nivel'] == 'ALTO' else "🟡" if hallazgo['nivel'] == 'MEDIO' else "🔵"
                reporte += f"  {nivel_emoji} [{hallazgo['nivel']}] {hallazgo['titulo']}\n"
                reporte += f"     Descripción: {hallazgo['descripcion']}\n"
                reporte += f"     Requisito: {hallazgo['requisito']}\n"
                reporte += f"     Recomendación: {hallazgo['recomendacion']}\n\n"
        else:
            reporte += "  No se encontraron hallazgos críticos\n"
        
        reporte += "\n"
        
        # Recomendaciones
        reporte += "💡 RECOMENDACIONES:\n"
        for rec in resultados['recomendaciones']:
            reporte += f"  • {rec}\n"
        
        reporte += "\n"
        reporte += "⚠️  NOTA: Este es un análisis automatizado. Para certificación PCI DSS completa,\n"
        reporte += "     se requiere auditoría por un QSA (Qualified Security Assessor) certificado.\n"
        
        return reporte

    def generar_resumen_compacto(self, resultados: Dict) -> str:
        """Generar resumen compacto mostrando solo hallazgos ALTOS"""
        if not resultados or resultados.get('cumplimiento_general') == 'NO_EVALUADO':
            return "=== RESUMEN PCI DSS (HALLAZGOS ALTOS) ===\n\nNo hay análisis PCI DSS disponible."
        
        resumen = "=== RESUMEN PCI DSS (HALLAZGOS ALTOS) ===\n\n"
        
        # Información general compacta
        resumen += f"📊 Cumplimiento General: {resultados.get('cumplimiento_general', 'N/A')}\n"
        resumen += f"⭐ Puntuación: {resultados.get('puntuacion_total', 0)}/100\n"
        resumen += f"🚨 Nivel de Riesgo: {resultados.get('nivel_riesgo', 'N/A')}\n\n"
        
        # Mostrar solo hallazgos ALTOS
        hallazgos_altos = resultados.get('hallazgos_altos', [])
        
        if hallazgos_altos:
            resumen += "🔴 HALLAZGOS DE ALTO RIESGO:\n"
            resumen += "=" * 50 + "\n"
            
            for i, hallazgo in enumerate(hallazgos_altos, 1):
                resumen += f"\n{i}. {hallazgo.get('titulo', 'Hallazgo')}\n"
                resumen += f"   • Descripción: {hallazgo.get('descripcion', 'N/A')}\n"
                resumen += f"   • Requisito: {hallazgo.get('requisito', 'N/A')}\n"
                resumen += f"   • Impacto: {hallazgo.get('impacto', 'N/A')}\n"
                resumen += f"   • Recomendación: {hallazgo.get('recomendacion', 'N/A')}\n"
        else:
            resumen += "✅ No se encontraron hallazgos de ALTO riesgo\n\n"
        
        # Resumen estadístico rápido
        requisitos_cumplidos = len(resultados.get('requisitos_cumplidos', []))
        requisitos_no_cumplidos = len(resultados.get('requisitos_no_cumplidos', []))
        total_requisitos = requisitos_cumplidos + requisitos_no_cumplidos
        
        if total_requisitos > 0:
            porcentaje_cumplimiento = (requisitos_cumplidos / total_requisitos) * 100
            resumen += f"\n📈 Resumen Estadístico:\n"
            resumen += f"   • Requisitos cumplidos: {requisitos_cumplidos}/{total_requisitos}\n"
            resumen += f"   • Porcentaje de cumplimiento: {porcentaje_cumplimiento:.1f}%\n"
            resumen += f"   • Hallazgos ALTOS encontrados: {len(hallazgos_altos)}\n"
        
        resumen += "\n💡 Para el análisis completo, ve a 'Comandos' → Filtro 'PCI DSS'"
        
        return resumen