import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import subprocess
import re
from pathlib import Path
import datetime

class StatsManager:
    def __init__(self, adb_manager, styles, logger):
        self.adb_manager = adb_manager
        self.styles = styles
        self.logger = logger
        self.adb_path = self._get_adb_path()

    def _get_adb_path(self):
        """Obtener la ruta de ADB desde la configuración"""
        try:
            if hasattr(self.adb_manager, 'get_adb_path'):
                adb_path = self.adb_manager.get_adb_path()
                if adb_path and Path(adb_path).exists():
                    return adb_path
            
            common_paths = [
                "platform-tools/adb.exe",
                "adb.exe",
                "C:\\Android\\platform-tools\\adb.exe",
                "C:\\Program Files\\Android\\platform-tools\\adb.exe",
                str(Path.home() / "AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe")
            ]
            
            for path in common_paths:
                if Path(path).exists():
                    return path
            
            return "adb"
            
        except Exception as e:
            self.logger.log_warning(f"Error obteniendo ruta ADB: {e}")
            return "adb"

    def _ejecutar_adb(self, comando, timeout=15):
        """Ejecutar comando ADB de forma segura"""
        try:
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    creationflags = subprocess.CREATE_NO_WINDOW
                else:
                    creationflags = 0
            else:
                creationflags = 0

            if isinstance(comando, str):
                if self.adb_path != "adb":
                    full_cmd = f'"{self.adb_path}" {comando}'
                else:
                    full_cmd = f"adb {comando}"
                
                result = subprocess.run(
                    full_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
            else:
                if self.adb_path != "adb":
                    full_cmd = [self.adb_path] + comando
                else:
                    full_cmd = comando
                
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
            
            return result
            
        except subprocess.TimeoutExpired:
            self.logger.log_warning(f"Timeout ejecutando ADB: {comando}")
            return None
        except Exception as e:
            self.logger.log_error(f"Error ejecutando ADB: {comando}", e)
            return None

    def _obtener_uid_package(self, package_name):
        """Obtener UID del package de forma robusta"""
        try:
            result = self._ejecutar_adb(f"shell dumpsys package {package_name} | grep userId")
            if result and result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if "userId=" in line:
                        match = re.search(r'userId=(\d+)', line)
                        if match:
                            return match.group(1)
            return None
        except Exception as e:
            self.logger.log_error(f"Error obteniendo UID para {package_name}: {e}")
            return None

    def _obtener_info_package(self, package_name):
        """Obtener información general del package"""
        info = {}
        try:
            result = self._ejecutar_adb(f"shell dumpsys package {package_name}")
            if result and result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if "versionName" in line:
                        match = re.search(r'versionName=([^\s]+)', line)
                        if match:
                            info['version'] = match.group(1)
                    elif "versionCode" in line:
                        match = re.search(r'versionCode=(\d+)', line)
                        if match:
                            info['version_code'] = match.group(1)
            
            uid = self._obtener_uid_package(package_name)
            if uid:
                info['uid'] = uid
            
        except Exception as e:
            self.logger.log_error(f"Error obteniendo info package: {e}")
        
        return info

    def _obtener_uso_memoria(self, package_name):
        """Obtener uso de memoria de forma robusta"""
        memoria = {}
        try:
            result = self._ejecutar_adb(f"shell dumpsys meminfo {package_name}")
            if result and result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'TOTAL' in line and 'PSS:' in line:
                        pss_match = re.search(r'PSS:\s+(\d+)', line)
                        if pss_match:
                            memoria['pss_kb'] = int(pss_match.group(1))
                            memoria['pss_mb'] = round(int(pss_match.group(1)) / 1024, 2)
                    
                    elif 'Java Heap:' in line:
                        heap_match = re.search(r'Java Heap:\s+(\d+)', line)
                        if heap_match:
                            memoria['java_heap_kb'] = int(heap_match.group(1))
                            memoria['java_heap_mb'] = round(int(heap_match.group(1)) / 1024, 2)
                    
                    elif 'Native Heap:' in line:
                        native_match = re.search(r'Native Heap:\s+(\d+)', line)
                        if native_match:
                            memoria['native_heap_kb'] = int(native_match.group(1))
                            memoria['native_heap_mb'] = round(int(native_match.group(1)) / 1024, 2)
            
            if not memoria:
                memoria['pss_mb'] = 0.0
                memoria['java_heap_mb'] = 0.0
                memoria['native_heap_mb'] = 0.0
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo memoria: {e}")
            memoria['pss_mb'] = 'Error'
            memoria['java_heap_mb'] = 'Error'
            memoria['native_heap_mb'] = 'Error'
        
        return memoria

    def _obtener_pid_package(self, package_name):
        """Obtener el PID de un package"""
        try:
            result = self._ejecutar_adb(f"shell pidof {package_name}")
            if result and result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip()
                if pid.isdigit():
                    return pid
            return None
        except Exception as e:
            self.logger.log_error(f"Error obteniendo PID para {package_name}", e)
            return None

    def _obtener_uso_cpu_mejorado(self, package_name):
        """Obtener uso de CPU de forma MÁS ROBUSTA"""
        cpu_stats = {}
        try:
            uid = self._obtener_uid_package(package_name)
            
            # MÉTODO 1: Usar dumpsys cpuinfo con UID
            if uid:
                result = self._ejecutar_adb("shell dumpsys cpuinfo")
                if result and result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if f"{uid}:" in line or f"/{package_name}" in line:
                            match = re.search(r'(\d+\.?\d*)%\s+' + re.escape(f"{uid}:") + r'.*', line)
                            if not match:
                                match = re.search(r'(\d+\.?\d*)%\s+' + re.escape(f"/{package_name}"), line)
                            
                            if match:
                                cpu_stats['cpu_usage'] = f"{match.group(1)}%"
                                cpu_stats['cpu_detalle'] = line.strip()
                                break
            
            # MÉTODO 2: Usar top si el primer método falla
            if 'cpu_usage' not in cpu_stats:
                pid = self._obtener_pid_package(package_name)
                if pid:
                    result = self._ejecutar_adb(f"shell top -n 1 -b")
                    if result and result.returncode == 0 and result.stdout:
                        for line in result.stdout.split('\n'):
                            if pid in line:
                                parts = line.split()
                                if len(parts) >= 9:
                                    for part in parts:
                                        if '%' in part and part.replace('%', '').replace('.', '').isdigit():
                                            cpu_stats['cpu_usage'] = part
                                            break
                                    else:
                                        if parts[8].replace('.', '').isdigit():
                                            cpu_stats['cpu_usage'] = f"{parts[8]}%"
            
            # MÉTODO 3: Método simplificado con ps
            if 'cpu_usage' not in cpu_stats:
                pid = self._obtener_pid_package(package_name)
                if pid:
                    result = self._ejecutar_adb(f"shell ps -p {pid} -o %cpu")
                    if result and result.returncode == 0 and result.stdout:
                        lines = result.stdout.split('\n')
                        if len(lines) >= 2:
                            cpu_value = lines[1].strip()
                            if cpu_value and cpu_value.replace('.', '').isdigit():
                                cpu_stats['cpu_usage'] = f"{cpu_value}%"
            
            if 'cpu_usage' not in cpu_stats:
                cpu_stats['cpu_usage'] = '0% (App puede no estar ejecutándose)'
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo CPU mejorado: {e}")
            cpu_stats['cpu_usage'] = f'Error: {str(e)}'
        
        return cpu_stats

    def _obtener_consumo_datos_mejorado(self, package_name):
        """Obtener consumo de datos de forma MÁS ROBUSTA"""
        datos_stats = {}
        try:
            uid = self._obtener_uid_package(package_name)
            
            # MÉTODO 1: Usar dumpsys netstats
            if uid:
                result = self._ejecutar_adb("shell dumpsys netstats detail")
                if result and result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    uid_found = False
                    total_rx = 0
                    total_tx = 0
                    
                    for line in lines:
                        if f"uid={uid}" in line:
                            uid_found = True
                            continue
                        
                        if uid_found:
                            if "rb=" in line and "tb=" in line:
                                rx_match = re.search(r'rb=(\d+)', line)
                                tx_match = re.search(r'tb=(\d+)', line)
                                if rx_match:
                                    total_rx += int(rx_match.group(1))
                                if tx_match:
                                    total_tx += int(tx_match.group(1))
                            elif line.strip() == "":
                                break
                    
                    if total_rx > 0 or total_tx > 0:
                        datos_stats['datos_recibidos'] = self._bytes_a_human(total_rx)
                        datos_stats['datos_enviados'] = self._bytes_a_human(total_tx)
                        datos_stats['datos_total'] = self._bytes_a_human(total_rx + total_tx)
                        # Guardar bytes para cálculos
                        datos_stats['bytes_recibidos'] = total_rx
                        datos_stats['bytes_enviados'] = total_tx
                        datos_stats['bytes_total'] = total_rx + total_tx
            
            # MÉTODO 2: Usar /proc/net/xt_qtaguid/stats
            if not datos_stats and uid:
                result = self._ejecutar_adb(f"shell cat /proc/net/xt_qtaguid/stats 2>/dev/null")
                if result and result.returncode == 0 and result.stdout:
                    total_rx = 0
                    total_tx = 0
                    for line in result.stdout.split('\n'):
                        if line.strip() and uid in line:
                            parts = line.split()
                            if len(parts) >= 8:
                                try:
                                    total_rx += int(parts[5])
                                    total_tx += int(parts[7])
                                except (ValueError, IndexError):
                                    continue
                    
                    if total_rx > 0 or total_tx > 0:
                        datos_stats['datos_recibidos'] = self._bytes_a_human(total_rx)
                        datos_stats['datos_enviados'] = self._bytes_a_human(total_tx)
                        datos_stats['datos_total'] = self._bytes_a_human(total_rx + total_tx)
                        datos_stats['bytes_recibidos'] = total_rx
                        datos_stats['bytes_enviados'] = total_tx
                        datos_stats['bytes_total'] = total_rx + total_tx
            
            # MÉTODO 3: Método simplificado
            if not datos_stats:
                result = self._ejecutar_adb(f"shell dumpsys package {package_name}")
                if result and result.returncode == 0 and result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Data received' in line:
                            match = re.search(r'Data received:\s*([\d.]+)\s*(\w+)', line)
                            if match:
                                datos_stats['datos_recibidos'] = f"{match.group(1)} {match.group(2)}"
                        elif 'Data sent' in line:
                            match = re.search(r'Data sent:\s*([\d.]+)\s*(\w+)', line)
                            if match:
                                datos_stats['datos_enviados'] = f"{match.group(1)} {match.group(2)}"
            
            if not datos_stats:
                datos_stats['datos_info'] = 'No se detectó actividad de red reciente'
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo datos mejorado: {e}")
            datos_stats['datos_info'] = f'Error al obtener datos: {str(e)}'
        
        return datos_stats

    def _obtener_info_bateria_mejorado(self, package_name):
        """Obtener información de batería más detallada y amigable"""
        battery_stats = {}
        try:
            # 1. Obtener wake locks específicos del package
            result = self._ejecutar_adb(f"shell dumpsys batterystats {package_name}")
            if result and result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                
                wake_locks = 0
                wake_lock_detalles = []
                
                for line in lines:
                    line_lower = line.lower().strip()
                    
                    # Buscar wake locks
                    if 'partial wakelock' in line_lower:
                        wake_match = re.search(r'(\d+)\s+times', line)
                        if wake_match:
                            wake_locks = int(wake_match.group(1))
                        # Obtener nombre del wake lock
                        wake_name_match = re.search(r'partial wakelock\s+(.*?):', line, re.IGNORECASE)
                        if wake_name_match:
                            wake_lock_detalles.append(wake_name_match.group(1).strip())
                    
                    # Buscar consumo de batería específico
                    elif 'total cpu' in line_lower or 'cpu total' in line_lower:
                        cpu_match = re.search(r'(\d+\.?\d*)\s*(ms|s|m|h)', line)
                        if cpu_match:
                            battery_stats['cpu_time'] = line.strip()
                    
                    # Buscar foreground time
                    elif 'foreground' in line_lower and ('time' in line_lower or 'activities' in line_lower):
                        time_match = re.search(r'(\d+)\s*(ms|s|m|h)', line)
                        if time_match:
                            battery_stats['foreground_time'] = line.strip()
                
                # Formatear wake locks de forma amigable
                if wake_locks > 0:
                    if wake_lock_detalles:
                        wake_info = f"{wake_locks} veces ({', '.join(wake_lock_detalles[:3])}"
                        if len(wake_lock_detalles) > 3:
                            wake_info += f" y {len(wake_lock_detalles) - 3} más)"
                        else:
                            wake_info += ")"
                    else:
                        wake_info = f"{wake_locks} veces"
                    battery_stats['wake_locks'] = wake_info
                else:
                    battery_stats['wake_locks'] = 'No detectados'
            
            # 2. Obtener estado general de la batería del dispositivo
            result = self._ejecutar_adb("shell dumpsys battery")
            if result and result.returncode == 0 and result.stdout:
                battery_info = {}
                
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == 'level':
                            battery_info['nivel'] = value
                            # Añadir emoji según el nivel
                            nivel_int = int(value) if value.isdigit() else 0
                            if nivel_int > 80:
                                battery_info['nivel_emoji'] = "🔋"
                            elif nivel_int > 50:
                                battery_info['nivel_emoji'] = "🔋"
                            elif nivel_int > 20:
                                battery_info['nivel_emoji'] = "🪫"
                            else:
                                battery_info['nivel_emoji'] = "🪫⚠️"
                        
                        elif key == 'health':
                            health_map = {
                                '1': 'Desconocido',
                                '2': 'Buena ✅',
                                '3': 'Sobrecalentada ⚠️',
                                '4': 'Muerta ❌',
                                '5': 'Sobrevoltaje ⚡',
                                '6': 'Falla desconocida ❓',
                                '7': 'Fría ❄️'
                            }
                            battery_info['salud'] = health_map.get(value, f'Desconocido ({value})')
                        
                        elif key == 'status':
                            status_map = {
                                '1': 'Desconocido',
                                '2': 'Cargando 🔌',
                                '3': 'Descargando 🔋',
                                '4': 'No cargando ⚡',
                                '5': 'Llena ✅'
                            }
                            battery_info['estado'] = status_map.get(value, f'Desconocido ({value})')
                        
                        elif key == 'plugged':
                            plugged_map = {
                                '0': 'No conectado',
                                '1': 'AC 🔌',
                                '2': 'USB 📱',
                                '3': 'Inalámbrico 🔋',
                                '4': 'Otro ⚡'
                            }
                            battery_info['conectado'] = plugged_map.get(value, f'Desconocido ({value})')
                        
                        elif key == 'temperature':
                            if value.isdigit():
                                temp_c = int(value) / 10.0
                                battery_info['temperatura'] = f"{temp_c:.1f}°C"
                                if temp_c > 45:
                                    battery_info['temperatura_estado'] = "🔥 Caliente"
                                elif temp_c > 35:
                                    battery_info['temperatura_estado'] = "🌡️ Tibia"
                                else:
                                    battery_info['temperatura_estado'] = "❄️ Normal"
                        
                        elif key == 'voltage':
                            if value.isdigit():
                                voltage_v = int(value) / 1000.0
                                battery_info['voltaje'] = f"{voltage_v:.2f}V"
                
                # Actualizar battery_stats con información formateada
                if 'nivel' in battery_info:
                    battery_stats['battery_level'] = f"{battery_info.get('nivel_emoji', '🔋')} {battery_info['nivel']}%"
                
                if 'salud' in battery_info:
                    battery_stats['battery_health'] = battery_info['salud']
                
                if 'estado' in battery_info:
                    battery_stats['battery_status'] = battery_info['estado']
                
                if 'conectado' in battery_info:
                    battery_stats['battery_plugged'] = battery_info['conectado']
                
                if 'temperatura' in battery_info:
                    battery_stats['battery_temp'] = f"{battery_info['temperatura']} ({battery_info.get('temperatura_estado', '')})"
                
                if 'voltaje' in battery_info:
                    battery_stats['battery_voltage'] = battery_info['voltaje']
            
            # 3. Si no se encontró información específica del package, usar general
            if not battery_stats:
                battery_stats['wake_locks'] = "Información no disponible"
                battery_stats['battery_level'] = "🔋 Nivel: No disponible"
                battery_stats['battery_health'] = "❓ Salud: Desconocida"
            
            # Añadir nota informativa
            battery_stats['nota_bateria'] = "Los datos de batería pueden variar según el dispositivo y versión de Android"
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo batería mejorado: {e}")
            battery_stats['wake_locks'] = 'Error al obtener datos'
            battery_stats['battery_level'] = "❌ Error obteniendo información"
            battery_stats['battery_health'] = "❌ Error obteniendo información"
        
        return battery_stats
    
    def _obtener_tiempo_uso_mejorado(self, package_name):
        """Obtener tiempo de uso de la aplicación de forma robusta"""
        tiempo_stats = {}
        try:
            # MÉTODO 1: Usar dumpsys usagestats (más confiable)
            result = self._ejecutar_adb(f"shell dumpsys usagestats {package_name}")
            if result and result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                total_usage_time = 0
                
                for line in lines:
                    # Buscar tiempo total de uso - patrones más específicos
                    if 'foreground' in line.lower() and 'time' in line.lower():
                        # Buscar patrones como "foreground time: 00:04"
                        time_match = re.search(r'foreground.*?time.*?(\d+):(\d+)', line.lower())
                        if time_match:
                            hours = int(time_match.group(1))
                            minutes = int(time_match.group(2))
                            total_usage_time = hours * 3600 + minutes * 60
                            tiempo_stats['tiempo_total_segundos'] = total_usage_time
                            tiempo_stats['tiempo_total_formateado'] = f"{hours:02d}:{minutes:02d}:00"
                            tiempo_stats['tiempo_detalle'] = f"{hours}h {minutes}m"
                            tiempo_stats['nota_tiempo'] = "Tiempo en primer plano"
                            break
                    
                    # Buscar tiempo total
                    elif 'total time' in line.lower() and 'used' in line.lower():
                        # Buscar formato como "Total time used: 00:04"
                        time_match = re.search(r'total.*?time.*?used.*?(\d+):(\d+)', line, re.IGNORECASE)
                        if time_match:
                            hours = int(time_match.group(1))
                            minutes = int(time_match.group(2))
                            total_usage_time = hours * 3600 + minutes * 60
                            tiempo_stats['tiempo_total_segundos'] = total_usage_time
                            tiempo_stats['tiempo_total_formateado'] = f"{hours:02d}:{minutes:02d}:00"
                            tiempo_stats['tiempo_detalle'] = f"{hours}h {minutes}m"
                            tiempo_stats['nota_tiempo'] = "Tiempo total de uso"
                            break
            
            # MÉTODO 2: Usar dumpsys batterystats para foreground time
            if 'tiempo_total_segundos' not in tiempo_stats:
                result = self._ejecutar_adb(f"shell dumpsys batterystats {package_name} | grep -i 'total'")
                if result and result.returncode == 0 and result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'foreground' in line.lower():
                            # Buscar tiempo en formato (4s, 4m, 4h)
                            patterns = [
                                r'(\d+)\s*(ms|milliseconds?)',
                                r'(\d+)\s*(s|seconds?)',
                                r'(\d+)\s*(m|minutes?)',
                                r'(\d+)\s*(h|hours?)'
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, line, re.IGNORECASE)
                                if match:
                                    value = int(match.group(1))
                                    unit = match.group(2).lower()
                                    
                                    if unit.startswith('ms') or unit.startswith('milli'):
                                        total_usage_time = value / 1000
                                    elif unit.startswith('s'):
                                        total_usage_time = value
                                    elif unit.startswith('m'):
                                        total_usage_time = value * 60
                                    elif unit.startswith('h'):
                                        total_usage_time = value * 3600
                                    
                                    tiempo_stats['tiempo_total_segundos'] = total_usage_time
                                    
                                    # Formatear a HH:MM:SS
                                    hours = int(total_usage_time // 3600)
                                    minutes = int((total_usage_time % 3600) // 60)
                                    seconds = int(total_usage_time % 60)
                                    
                                    tiempo_stats['tiempo_total_formateado'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                    tiempo_stats['tiempo_detalle'] = f"{hours}h {minutes}m {seconds}s"
                                    tiempo_stats['nota_tiempo'] = "Tiempo en primer plano"
                                    break
                            break
            
            # MÉTODO 3: Si no se encuentra, usar una estimación basada en UID
            if 'tiempo_total_segundos' not in tiempo_stats:
                result = self._ejecutar_adb(f"shell dumpsys usagestats | grep -A 5 -B 5 {package_name}")
                if result and result.returncode == 0 and result.stdout:
                    # Intentar parsear tiempo desde el contexto
                    for line in result.stdout.split('\n'):
                        if 'time' in line.lower() and any(char.isdigit() for char in line):
                            # Buscar números en la línea
                            numbers = re.findall(r'\d+', line)
                            if numbers:
                                # Asumir que el primer número es tiempo en segundos
                                try:
                                    total_usage_time = int(numbers[0])
                                    if total_usage_time > 0:
                                        tiempo_stats['tiempo_total_segundos'] = total_usage_time
                                        
                                        hours = int(total_usage_time // 3600)
                                        minutes = int((total_usage_time % 3600) // 60)
                                        seconds = int(total_usage_time % 60)
                                        
                                        tiempo_stats['tiempo_total_formateado'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                        tiempo_stats['tiempo_detalle'] = f"{hours}h {minutes}m {seconds}s"
                                        tiempo_stats['nota_tiempo'] = "Tiempo estimado de uso"
                                        break
                                except ValueError:
                                    pass
            
            # Si no se encontró tiempo de uso, usar 0
            if 'tiempo_total_segundos' not in tiempo_stats:
                tiempo_stats['tiempo_total_formateado'] = "00:00:00"
                tiempo_stats['tiempo_detalle'] = "0h 0m 0s"
                tiempo_stats['nota_tiempo'] = "Sin tiempo de uso registrado"
                tiempo_stats['tiempo_total_segundos'] = 0
                    
        except Exception as e:
            self.logger.log_error(f"Error obteniendo tiempo de uso: {e}")
            tiempo_stats['tiempo_total_formateado'] = "00:00:00"
            tiempo_stats['tiempo_detalle'] = "Error"
            tiempo_stats['nota_tiempo'] = "Error obteniendo tiempo de uso"
            tiempo_stats['tiempo_total_segundos'] = 0
        
        return tiempo_stats

    def _obtener_estado_aplicacion(self, package_name):
        """Obtener estado actual de la aplicación (foreground/background)"""
        try:
            # Verificar si está en primer plano
            result = self._ejecutar_adb("shell dumpsys activity recents | grep -i 'Recent #0'")
            if result and result.returncode == 0 and result.stdout:
                if package_name in result.stdout:
                    return "🟢 En primer plano"
            
            # Verificar procesos activos
            pid = self._obtener_pid_package(package_name)
            if pid:
                return "🟡 En segundo plano (ejecutándose)"
            else:
                return "🔴 No ejecutándose"
                
        except Exception as e:
            self.logger.log_error(f"Error obteniendo estado app: {e}")
            return "⚪ Estado desconocido"

    def _calcular_promedio_datos_por_minuto(self, datos_stats, tiempo_stats):
        """Calcular promedio de datos utilizados por minuto"""
        try:
            # Verificar que tenemos los datos necesarios
            if ('bytes_total' not in datos_stats or 
                'tiempo_total_segundos' not in tiempo_stats or
                tiempo_stats['tiempo_total_segundos'] == 0):
                return None
            
            bytes_total = datos_stats['bytes_total']
            tiempo_segundos = tiempo_stats['tiempo_total_segundos']
            
            # Convertir segundos a minutos
            tiempo_minutos = tiempo_segundos / 60
            
            if tiempo_minutos == 0:
                return None
            
            # Calcular promedio por minuto
            promedio_bytes_por_minuto = bytes_total / tiempo_minutos
            
            # Formatear resultado
            if promedio_bytes_por_minuto < 1024:  # Menos de 1 KB
                return f"{promedio_bytes_por_minuto:.2f} B/min"
            elif promedio_bytes_por_minuto < 1024 * 1024:  # Menos de 1 MB
                return f"{promedio_bytes_por_minuto / 1024:.2f} KB/min"
            else:  # MB o más
                return f"{promedio_bytes_por_minuto / (1024 * 1024):.2f} MB/min"
                
        except Exception as e:
            self.logger.log_error(f"Error calculando promedio datos: {e}")
            return None

    def _calcular_estadisticas_avanzadas(self, datos_stats, tiempo_stats):
        """Calcular estadísticas avanzadas de uso de datos"""
        estadisticas = {}
        try:
            # Verificar datos necesarios
            if ('bytes_recibidos' not in datos_stats or 
                'bytes_enviados' not in datos_stats or
                'tiempo_total_segundos' not in tiempo_stats or
                tiempo_stats['tiempo_total_segundos'] == 0):
                return estadisticas
            
            bytes_rx = datos_stats['bytes_recibidos']
            bytes_tx = datos_stats['bytes_enviados']
            tiempo_segundos = tiempo_stats['tiempo_total_segundos']
            
            # Convertir a minutos
            tiempo_minutos = tiempo_segundos / 60
            
            if tiempo_minutos == 0:
                return estadisticas
            
            # Calcular promedios por minuto
            if bytes_rx > 0:
                promedio_rx_por_minuto = bytes_rx / tiempo_minutos
                estadisticas['promedio_rx_por_minuto'] = self._bytes_a_human(promedio_rx_por_minuto) + "/min"
            
            if bytes_tx > 0:
                promedio_tx_por_minuto = bytes_tx / tiempo_minutos
                estadisticas['promedio_tx_por_minuto'] = self._bytes_a_human(promedio_tx_por_minuto) + "/min"
            
            if bytes_rx + bytes_tx > 0:
                promedio_total_por_minuto = (bytes_rx + bytes_tx) / tiempo_minutos
                estadisticas['promedio_total_por_minuto'] = self._bytes_a_human(promedio_total_por_minuto) + "/min"
            
            # Calcular eficiencia de datos (bytes por segundo)
            if tiempo_segundos > 0:
                estadisticas['bytes_por_segundo'] = f"{(bytes_rx + bytes_tx) / tiempo_segundos:.2f} B/s"
            
            # Calcular porcentaje de subida vs bajada
            total_bytes = bytes_rx + bytes_tx
            if total_bytes > 0:
                porcentaje_rx = (bytes_rx / total_bytes) * 100
                porcentaje_tx = (bytes_tx / total_bytes) * 100
                estadisticas['ratio_rx_tx'] = f"📥 {porcentaje_rx:.1f}% / 📤 {porcentaje_tx:.1f}%"
            
            return estadisticas
            
        except Exception as e:
            self.logger.log_error(f"Error calculando estadísticas avanzadas: {e}")
            return estadisticas

    def _calcular_promedios_tiempo_uso(self, tiempo_stats):
        """Calcular promedios basados en el tiempo de uso"""
        promedios = {}
        try:
            if 'tiempo_total_segundos' not in tiempo_stats:
                return promedios
            
            tiempo_total = tiempo_stats['tiempo_total_segundos']
            
            if tiempo_total == 0:
                return promedios
            
            # Convertir a diferentes unidades
            tiempo_minutos = tiempo_total / 60
            tiempo_horas = tiempo_total / 3600
            tiempo_dias = tiempo_total / 86400
            
            # Calcular promedios
            if tiempo_horas > 0:
                promedios['uso_promedio_por_dia'] = f"{tiempo_horas:.2f} horas"
                if tiempo_dias >= 1:
                    promedios['uso_promedio_por_dia'] = f"{tiempo_horas / tiempo_dias:.2f} horas/día"
            
            # Agregar desglose detallado
            promedios['desglose_tiempo'] = {
                'segundos': tiempo_total,
                'minutos': tiempo_minutos,
                'horas': tiempo_horas,
                'dias': tiempo_dias
            }
            
            return promedios
            
        except Exception as e:
            self.logger.log_error(f"Error calculando promedios de tiempo: {e}")
            return promedios

    def _bytes_a_human(self, bytes_size):
        """Convertir bytes a formato legible"""
        try:
            if bytes_size == 0:
                return "0 B"
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.2f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.2f} TB"
        except:
            return "N/A"

    def obtener_estadisticas_app(self, package_name):
        """Obtener estadísticas COMPLETAS de forma más robusta"""
        try:
            stats = {}
            
            # 1. Obtener información básica del package
            package_info = self._obtener_info_package(package_name)
            if package_info:
                stats.update(package_info)
            
            # 2. Obtener uso de memoria
            memoria_info = self._obtener_uso_memoria(package_name)
            if memoria_info:
                stats.update(memoria_info)
            
            # 3. Obtener uso de CPU MEJORADO
            cpu_info = self._obtener_uso_cpu_mejorado(package_name)
            if cpu_info:
                stats.update(cpu_info)
            
            # 4. Obtener consumo de datos MEJORADO
            datos_info = self._obtener_consumo_datos_mejorado(package_name)
            if datos_info:
                stats.update(datos_info)
            
            # 5. Obtener información de batería MEJORADO
            battery_info = self._obtener_info_bateria_mejorado(package_name)
            if battery_info:
                stats.update(battery_info)
            
            # 6. Obtener tiempo de uso
            tiempo_info = self._obtener_tiempo_uso_mejorado(package_name)
            if tiempo_info:
                stats.update(tiempo_info)
            
            # 7. Obtener estado actual (foreground/background)
            estado_actual = self._obtener_estado_aplicacion(package_name)
            stats['estado_actual'] = estado_actual
            
            # 8. ✅ NUEVO: Calcular promedios y estadísticas avanzadas
            if datos_info and tiempo_info:
                # Promedio simple de datos por minuto
                promedio_simple = self._calcular_promedio_datos_por_minuto(datos_info, tiempo_info)
                if promedio_simple:
                    stats['promedio_datos_minuto'] = promedio_simple
                
                # Estadísticas avanzadas
                estadisticas_avanzadas = self._calcular_estadisticas_avanzadas(datos_info, tiempo_info)
                if estadisticas_avanzadas:
                    stats.update(estadisticas_avanzadas)
            
            # 9. ✅ NUEVO: Calcular promedios de tiempo de uso
            promedios_tiempo = self._calcular_promedios_tiempo_uso(tiempo_info)
            if promedios_tiempo:
                stats.update(promedios_tiempo)
            
            return True, stats
            
        except Exception as e:
            self.logger.log_error(f"Error en obtener_estadisticas_app: {e}")
            return False, f"❌ Error obteniendo estadísticas: {str(e)}"

    def mostrar_estadisticas_app(self, parent, package_name):
        """Mostrar estadísticas de la aplicación"""
        if not package_name:
            messagebox.showwarning("Advertencia", "Selecciona un package primero")
            return
            
        def obtener_estadisticas():
            try:
                progress_dialog = self._mostrar_dialogo_progreso(parent, "Obteniendo estadísticas...")
                
                success_stats, result_stats = self.obtener_estadisticas_app(package_name)
                
                parent.after(0, lambda: self._procesar_estadisticas(
                    progress_dialog, parent, package_name, success_stats, result_stats))
                    
            except Exception as e:
                parent.after(0, lambda: self._procesar_error_estadisticas(progress_dialog, str(e)))

        threading.Thread(target=obtener_estadisticas, daemon=True).start()

    def _procesar_estadisticas(self, progress_dialog, parent, package_name, success_stats, result_stats):
        """Procesar y mostrar estadísticas obtenidas"""
        if progress_dialog and progress_dialog.winfo_exists():
            progress_dialog.destroy()
        
        dialog = tk.Toplevel(parent)
        dialog.title(f"📊 Estadísticas - {package_name}")
        dialog.geometry("1000x850") 
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text=f"📊 Estadísticas Completas - {package_name}",
            font=("Segoe UI", 14, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['accent'],
            pady=10
        ).pack()

        stats_container = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        stats_container.pack(fill="both", expand=True, pady=10)

        stats_text = scrolledtext.ScrolledText(
            stats_container,
            wrap="word",
            font=("Consolas", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            height=45,
            padx=15,
            pady=15
        )
        stats_text.pack(fill="both", expand=True)

        if success_stats and isinstance(result_stats, dict):
            self._formatear_estadisticas_en_texto(stats_text, result_stats)
        else:
            self._mostrar_error_estadisticas(stats_text, result_stats)

        stats_text.config(state='disabled')

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=10)


        tk.Button(
            btn_frame,
            text="Cerrar",
            command=dialog.destroy,
            font=("Segoe UI", 9),
            bg="#6c757d",
            fg="white",
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side="right")

        self._centrar_dialogo(dialog, parent)

    def _formatear_estadisticas_en_texto(self, stats_text, result_stats):
        """Formatear las estadísticas en el widget de texto"""
        stats_text.insert("1.0", "📈 ESTADÍSTICAS DETALLADAS\n")
        stats_text.insert("2.0", "=" * 60 + "\n\n")
        
        # SECCIÓN DE ESTADO ACTUAL
        stats_text.insert("end", "🎯 ESTADO ACTUAL:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", f"• {result_stats.get('estado_actual', 'Desconocido')}\n")
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE INFORMACIÓN GENERAL
        stats_text.insert("end", "📱 INFORMACIÓN GENERAL:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", f"• UID: {result_stats.get('uid', 'No disponible')}\n")
        if 'version' in result_stats:
            stats_text.insert("end", f"• Versión: {result_stats['version']}\n")
        if 'version_code' in result_stats:
            stats_text.insert("end", f"• Código de versión: {result_stats['version_code']}\n")
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE TIEMPO DE USO (MEJORADA)
        stats_text.insert("end", "⏰ TIEMPO DE USO:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        if 'tiempo_total_formateado' in result_stats:
            stats_text.insert("end", f"• ⏱️  Tiempo total: {result_stats['tiempo_total_formateado']}\n")
        if 'tiempo_detalle' in result_stats:
            stats_text.insert("end", f"• 📊 Desglose: {result_stats['tiempo_detalle']}\n")
        if 'nota_tiempo' in result_stats:
            stats_text.insert("end", f"• 💡 Nota: {result_stats['nota_tiempo']}\n")
        
        # Mostrar promedios de tiempo si están disponibles
        if 'uso_promedio_por_dia' in result_stats:
            stats_text.insert("end", f"• 📅 Uso promedio: {result_stats['uso_promedio_por_dia']}\n")
        
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE USO DE MEMORIA
        stats_text.insert("end", "🧠 USO DE MEMORIA:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", f"• Memoria total (PSS): {result_stats.get('pss_mb', 'N/A')} MB\n")
        stats_text.insert("end", f"• Java Heap: {result_stats.get('java_heap_mb', 'N/A')} MB\n")
        stats_text.insert("end", f"• Native Heap: {result_stats.get('native_heap_mb', 'N/A')} MB\n")
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE USO DE CPU
        stats_text.insert("end", "⚡ USO DE CPU:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", f"• Uso de CPU: {result_stats.get('cpu_usage', 'No disponible')}\n")
        if 'cpu_detalle' in result_stats:
            stats_text.insert("end", f"• Detalle: {result_stats['cpu_detalle']}\n")
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE CONSUMO DE DATOS (MEJORADA)
        stats_text.insert("end", "📡 CONSUMO DE DATOS:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        
        if 'datos_recibidos' in result_stats:
            stats_text.insert("end", f"• 📥 Datos recibidos: {result_stats['datos_recibidos']}\n")
        if 'datos_enviados' in result_stats:
            stats_text.insert("end", f"• 📤 Datos enviados: {result_stats['datos_enviados']}\n")
        if 'datos_total' in result_stats:
            stats_text.insert("end", f"• 📊 Total transferido: {result_stats['datos_total']}\n")
        
        # Mostrar promedios de datos si están disponibles
        if 'promedio_datos_minuto' in result_stats:
            stats_text.insert("end", f"• 📈 Promedio por minuto: {result_stats['promedio_datos_minuto']}\n")
        
        if 'promedio_rx_por_minuto' in result_stats:
            stats_text.insert("end", f"• ⬇️  Recepción/min: {result_stats['promedio_rx_por_minuto']}\n")
        
        if 'promedio_tx_por_minuto' in result_stats:
            stats_text.insert("end", f"• ⬆️  Envío/min: {result_stats['promedio_tx_por_minuto']}\n")
        
        if 'ratio_rx_tx' in result_stats:
            stats_text.insert("end", f"• 📊 Ratio Rx/Tx: {result_stats['ratio_rx_tx']}\n")
        
        if not any(key in result_stats for key in ['datos_recibidos', 'datos_enviados', 'datos_total']):
            stats_text.insert("end", f"• {result_stats.get('datos_info', 'No se detectó actividad de red')}\n")
        
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE CONSUMO DE BATERÍA
        stats_text.insert("end", "🔋 CONSUMO DE BATERÍA:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", f"• Wake locks: {result_stats.get('wake_locks', 'No disponible')}\n")
        if 'battery_level' in result_stats:
            stats_text.insert("end", f"• Nivel de batería: {result_stats['battery_level']}\n")
        if 'battery_health' in result_stats:
            stats_text.insert("end", f"• Salud de batería: {result_stats['battery_health']}\n")
        stats_text.insert("end", "\n")
        
        # SECCIÓN DE RESUMEN Y RECOMENDACIONES
        stats_text.insert("end", "💡 RESUMEN Y ANÁLISIS:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        
        # Análisis automático basado en los datos
        if 'tiempo_total_segundos' in result_stats and result_stats['tiempo_total_segundos'] > 0:
            tiempo_horas = result_stats['tiempo_total_segundos'] / 3600
            if tiempo_horas < 1:
                stats_text.insert("end", "• 🟢 Uso bajo: La aplicación se usa poco tiempo\n")
            elif tiempo_horas < 5:
                stats_text.insert("end", "• 🟡 Uso moderado: Tiempo de uso normal\n")
            else:
                stats_text.insert("end", "• 🔴 Uso intensivo: Mucho tiempo de uso\n")
        
        if 'pss_mb' in result_stats and isinstance(result_stats['pss_mb'], (int, float)):
            if result_stats['pss_mb'] < 100:
                stats_text.insert("end", "• 🟢 Memoria: Uso eficiente de memoria\n")
            elif result_stats['pss_mb'] < 300:
                stats_text.insert("end", "• 🟡 Memoria: Uso moderado de memoria\n")
            else:
                stats_text.insert("end", "• 🔴 Memoria: Alto consumo de memoria\n")
        
        stats_text.insert("end", "\n")
        stats_text.insert("end", "📝 NOTAS:\n")
        stats_text.insert("end", "-" * 40 + "\n")
        stats_text.insert("end", "• Los datos se obtienen del sistema Android en tiempo real\n")
        stats_text.insert("end", "• Para datos más precisos, ejecuta la aplicación\n")
        stats_text.insert("end", "• Los promedios se calculan basados en el tiempo de uso total\n")

    def _mostrar_error_estadisticas(self, stats_text, result_stats):
        """Mostrar mensaje de error en las estadísticas"""
        stats_text.insert("1.0", "❌ ERROR AL OBTENER ESTADÍSTICAS\n")
        stats_text.insert("end", "=" * 45 + "\n\n")
        
        if isinstance(result_stats, str):
            stats_text.insert("end", f"Error: {result_stats}\n\n")
        
        stats_text.insert("end", "🔧 POSIBLES SOLUCIONES:\n")
        stats_text.insert("end", "-" * 25 + "\n")
        stats_text.insert("end", "• Verifica que el dispositivo esté conectado\n")
        stats_text.insert("end", "• Asegúrate de que la aplicación esté instalada\n")
        stats_text.insert("end", "• Intenta reiniciar el servidor ADB\n")
        stats_text.insert("end", "• Ejecuta la aplicación para registrar tiempo de uso\n")

    def _actualizar_estadisticas(self, dialog, package_name, stats_text):
        """Actualizar las estadísticas en tiempo real"""
        def actualizar():
            success_stats, result_stats = self.obtener_estadisticas_app(package_name)
            dialog.after(0, lambda: self._refrescar_estadisticas(stats_text, success_stats, result_stats))
        
        threading.Thread(target=actualizar, daemon=True).start()

    def _refrescar_estadisticas(self, stats_text, success_stats, result_stats):
        """Refrescar el contenido de las estadísticas"""
        stats_text.config(state='normal')
        stats_text.delete(1.0, tk.END)
        
        if success_stats and isinstance(result_stats, dict):
            self._formatear_estadisticas_en_texto(stats_text, result_stats)
        else:
            self._mostrar_error_estadisticas(stats_text, result_stats)
        
        stats_text.config(state='disabled')

    def _procesar_error_estadisticas(self, progress_dialog, error):
        """Procesar error al obtener estadísticas"""
        if progress_dialog and progress_dialog.winfo_exists():
            progress_dialog.destroy()
        messagebox.showerror("Error", f"No se pudieron obtener las estadísticas:\n{error}")

    def _mostrar_dialogo_progreso(self, parent, mensaje):
        """Mostrar diálogo de progreso"""
        dialog = tk.Toplevel(parent)
        dialog.title("Procesando")
        dialog.geometry("300x100")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.resizable(False, False)

        self._centrar_dialogo(dialog, parent)

        tk.Label(
            dialog,
            text=mensaje,
            font=("Segoe UI", 10),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            pady=20
        ).pack()

        progress = ttk.Progressbar(
            dialog,
            mode='indeterminate',
            length=200
        )
        progress.pack(pady=10)
        progress.start()

        return dialog

    def _centrar_dialogo(self, dialog, parent):
        """Centrar diálogo en la pantalla"""
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")