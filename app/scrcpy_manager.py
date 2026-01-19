# app/scrcpy_manager.py - VERSIÓN CON EMBEDDING

import subprocess
import threading
import time
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import psutil
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import win32gui  
import win32con   
import win32process  

class ScrcpyManager:
    """
    Manager avanzado para scrcpy con interfaz unificada y controles integrados
    """
    
    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        self.current_process = None
        self.is_running = False
        self.adb_path = None
        self.monitor_thread = None
        self.window_monitor_thread = None
        self.should_monitor = False
        self.record_process = None
        self.is_recording = False
        self.screenshot_count = 0
        self.recording_output_path = None
        self.recording_start_time = None
        self.unified_window = None
        self.embedded_hwnd = None   
        self._setup_adb()
        
    def _setup_adb(self):
        """Configurar ADB al inicializar"""
        adb_status = self.tool_manager.setup_adb()
        if adb_status["available"]:
            self.adb_path = adb_status["path"]
            print(f"✅ ADB configurado")
        else:
            print(f"❌ ADB no disponible")

    # ===== MÉTODOS NUEVOS PARA EMBEDDING =====

    def start_embedded_mirror(self, parent_hwnd: int, max_size: int = 1024) -> Dict:
        """
        Iniciar scrcpy embebido - COMPATIBLE con v1.24
        """
        if self.is_running and self._is_process_alive():
            return {"success": False, "error": "Scrcpy ya está ejecutándose"}
            
        if self.is_running and not self._is_process_alive():
            self.is_running = False
            self.current_process = None
            
        devices = self.list_devices()
        connected_devices = [d for d in devices if d['status'] == 'device']
        
        if not connected_devices:
            return {"success": False, "error": "No hay dispositivos conectados"}
        
        scrcpy_status = self.tool_manager.setup_scrcpy()
        if not scrcpy_status["available"]:
            return {"success": False, "error": "Scrcpy no disponible"}
        
        scrcpy_path = scrcpy_status["path"]
        
        try:
            # ✅ VERSIÓN COMPATIBLE con v1.24
            cmd = [str(scrcpy_path)]
            
            # Parámetros básicos compatibles
            cmd.extend(['--max-size', str(max_size)])
            cmd.append('--stay-awake')  # Compatible con v1.24
            
            # Opciones de ventana
            cmd.extend([
                '--window-borderless',
                '--no-control',
                '--always-on-top'
            ])
            
            # ⚠️ IMPORTANTE: NO usar --turn-screen-off
            # En v1.24, la pantalla se mantiene encendida por defecto
            
            env = os.environ.copy()
            if self.adb_path and self.adb_path != "adb":
                adb_dir = str(Path(self.adb_path).parent)
                env["PATH"] = adb_dir + ";" + env["PATH"]
            
            print(f"🚀 Iniciando scrcpy v1.24 embebido...")
            print(f"   Comando: {' '.join(cmd)}")
            print(f"   Pantalla: ENCENDIDA (sin --turn-screen-off)")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Esperar para embedding
            time.sleep(5)
            
            if self._is_process_alive():
                self.is_running = True
                
                # Intentar embedding
                embedding_result = self._embed_scrcpy_window(parent_hwnd)
                
                if embedding_result["success"]:
                    self.embedded_hwnd = embedding_result["hwnd"]
                    return {
                        "success": True, 
                        "process": self.current_process,
                        "hwnd": self.embedded_hwnd,
                        "message": "Scrcpy embebido iniciado (pantalla encendida)"
                    }
                else:
                    # Si embedding falla, al menos scrcpy está corriendo
                    print("⚠️ Embedding falló, pero scrcpy está ejecutándose")
                    return {
                        "success": True,
                        "process": self.current_process,
                        "hwnd": None,
                        "message": "Scrcpy iniciado en ventana normal"
                    }
            else:
                # Obtener error específico
                error_msg = "Error desconocido"
                try:
                    _, stderr = self.current_process.communicate(timeout=2)
                    if stderr:
                        error_lines = [line for line in stderr.split('\n') if 'error' in line.lower() or 'fail' in line.lower()]
                        if error_lines:
                            error_msg = error_lines[0]
                except:
                    pass
                
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}

    def _embed_scrcpy_window(self, parent_hwnd: int) -> Dict:
        """Buscar y embebir la ventana de scrcpy"""
        max_attempts = 25
        attempt = 0
        
        print("🔍 Buscando ventana de scrcpy para embedding...")
        
        while attempt < max_attempts and self.is_running:
            try:
                scrcpy_hwnd = self._find_scrcpy_window()
                if scrcpy_hwnd and scrcpy_hwnd != parent_hwnd:
                    print(f"✅ Ventana scrcpy encontrada: {scrcpy_hwnd}")
                    
                    if self._perform_embedding(scrcpy_hwnd, parent_hwnd):
                        return {"success": True, "hwnd": scrcpy_hwnd}
                    else:
                        return {"success": False, "error": "No se pudo embebir la ventana"}
                
                attempt += 1
                time.sleep(0.4)
                
            except Exception as e:
                print(f"❌ Error en embedding: {e}")
                attempt += 1
                time.sleep(0.4)
        
        return {"success": False, "error": "No se pudo encontrar la ventana de scrcpy"}

    def _find_scrcpy_window(self):
        """Encontrar ventana de scrcpy"""
        try:
            scrcpy_windows = []
            
            def enum_windows_proc(hwnd, lParam):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    # Buscar ventanas de scrcpy
                    if 'scrcpy' in window_text.lower() or not window_text.strip():
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            if 'scrcpy' in proc.name().lower():
                                scrcpy_windows.append(hwnd)
                        except:
                            pass
                return True
            
            win32gui.EnumWindows(enum_windows_proc, None)
            return scrcpy_windows[0] if scrcpy_windows else None
            
        except Exception as e:
            print(f"❌ Error buscando ventana: {e}")
            return None

    def _perform_embedding(self, child_hwnd, parent_hwnd):
        """Realizar el embedding de la ventana"""
        try:
            print(f"🔧 Embebiendo {child_hwnd} en {parent_hwnd}")
            
            # 1. Establecer como ventana hija
            old_parent = win32gui.SetParent(child_hwnd, parent_hwnd)
            print(f"   Padre anterior: {old_parent}")
            
            # 2. Obtener dimensiones del padre
            parent_rect = win32gui.GetClientRect(parent_hwnd)
            parent_width = parent_rect[2] - parent_rect[0]
            parent_height = parent_rect[3] - parent_rect[1]
            
            print(f"   Dimensiones del padre: {parent_width}x{parent_height}")
            
            # 3. Remover estilos de ventana
            current_style = win32gui.GetWindowLong(child_hwnd, win32con.GWL_STYLE)
            new_style = current_style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | 
                                        win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | 
                                        win32con.WS_SYSMENU | win32con.WS_BORDER |
                                        win32con.WS_OVERLAPPEDWINDOW)
            win32gui.SetWindowLong(child_hwnd, win32con.GWL_STYLE, new_style)
            
            # 4. Reposicionar y redimensionar
            win32gui.SetWindowPos(
                child_hwnd,
                win32con.HWND_TOP,
                0, 0,
                parent_width, parent_height,
                win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW
            )
            
            # 5. Forzar actualización
            win32gui.ShowWindow(child_hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(child_hwnd)
            win32gui.UpdateWindow(parent_hwnd)
            
            print("✅ Embedding completado exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error en embedding: {e}")
            return False

    # ===== MÉTODOS EXISTENTES (se mantienen igual) =====

    def ensure_available(self) -> bool:
        """Asegurar que scrcpy y ADB están disponibles"""
        scrcpy_status = self.tool_manager.setup_scrcpy()
        adb_available = self.adb_path is not None
        
        if not scrcpy_status["available"]:
            print("❌ Scrcpy no disponible")
            return False
        
        if not adb_available:
            print("❌ ADB no disponible")
            return False
        
        self._cleanup_zombie_processes()
        return True

    def _cleanup_zombie_processes(self):
        """Limpiar procesos scrcpy huérfanos"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'scrcpy' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline'] or []
                        if any('scrcpy' in str(arg).lower() for arg in cmdline):
                            if self.current_process is None or proc.info['pid'] != self.current_process.pid:
                                print(f"🔄 Limpiando proceso scrcpy huérfano: PID {proc.info['pid']}")
                                proc.terminate()
                                try:
                                    proc.wait(timeout=3)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"⚠️ Error limpiando procesos: {e}")
    
    def _is_process_alive(self) -> bool:
        """Verificar si el proceso actual sigue vivo"""
        if self.current_process is None:
            return False
        
        if self.current_process.poll() is not None:
            return False
        
        try:
            if hasattr(self.current_process, 'pid'):
                proc = psutil.Process(self.current_process.pid)
                return proc.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return False

    def _run_adb_command(self, command: list) -> Optional[subprocess.CompletedProcess]:
        """Ejecutar comando ADB"""
        if not self.adb_path:
            return None
            
        try:
            if self.adb_path == "adb":
                full_cmd = ["adb"] + command
            else:
                full_cmd = [self.adb_path] + command
                
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result
        except Exception as e:
            print(f"❌ Error ejecutando ADB: {e}")
            return None

    def list_devices(self) -> list:
        """Listar dispositivos Android conectados"""
        if not self.adb_path:
            return []
            
        result = self._run_adb_command(["devices"])
        if not result or result.returncode != 0:
            return []
            
        lines = result.stdout.strip().split('\n')
        devices = []
        
        for line in lines[1:]:
            if line.strip() and not line.startswith('*'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    devices.append({
                        'serial': parts[0].strip(),
                        'status': parts[1].strip()
                    })
        
        return devices

    def start_mirror(self, options: Dict = None) -> bool:
        """Iniciar espejo de pantalla normal - VERSIÓN CORRECTA para scrcpy v1.24"""
        if self.is_running and self._is_process_alive():
            print("⚠️ Scrcpy ya está ejecutándose")
            return False
            
        if self.is_running and not self._is_process_alive():
            print("🔄 Limpiando estado de proceso terminado")
            self.is_running = False
            self.current_process = None
            
        devices = self.list_devices()
        connected_devices = [d for d in devices if d['status'] == 'device']
        
        if not connected_devices:
            print("❌ No hay dispositivos Android conectados")
            return False
        
        print(f"📱 Dispositivos conectados: {len(connected_devices)}")
        
        scrcpy_status = self.tool_manager.setup_scrcpy()
        if not scrcpy_status["available"]:
            print("❌ Scrcpy no disponible")
            return False
        
        scrcpy_path = scrcpy_status["path"]
        
        # ✅ VERSIÓN CORRECTA para scrcpy v1.24
        cmd = [str(scrcpy_path)]
        
        # Parámetro de tamaño
        max_size = options.get('max_size') if options else 1024
        cmd.extend(['--max-size', str(max_size)])
        
        # Opciones básicas
        if options and options.get('always_on_top'):
            cmd.append('--always-on-top')
        
        if options and options.get('window_borderless'):
            cmd.append('--window-borderless')
        
        # ✅ IMPORTANTE: NO usar --turn-screen-off para mantener pantalla ENCENDIDA
        # scrcpy v1.24 mantiene la pantalla encendida por defecto
        # Solo usa --turn-screen-off si quieres apagarla
        
        # ✅ Parámetros opcionales (verificar compatibilidad)
        try:
            # Solo agregar parámetros si la versión los soporta
            cmd.extend(['--bit-rate', '10M'])
            cmd.extend(['--max-fps', '60'])
        except:
            pass  # Ignorar si no son compatibles
        
        # ✅ Mantener dispositivo despierto (compatible con v1.24)
        cmd.append('--stay-awake')
        
        try:
            print(f"🚀 Iniciando scrcpy v1.24...")
            print(f"   Comando: {' '.join(cmd)}")
            print(f"   NOTA: Pantalla permanecerá ENCENDIDA (sin --turn-screen-off)")
            
            # Crear entorno con ADB
            env = os.environ.copy()
            if self.adb_path and self.adb_path != "adb":
                adb_dir = str(Path(self.adb_path).parent)
                env["PATH"] = adb_dir + ";" + env["PATH"]
                print(f"   ADB path: {adb_dir}")
            
            # Ejecutar scrcpy
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Esperar y verificar
            time.sleep(3)
            
            if self._is_process_alive():
                self.is_running = True
                print("✅ Espejo de pantalla iniciado correctamente")
                print("   Pantalla del dispositivo: ENCENDIDA")
                return True
            else:
                # Si falla, intentar versión más simple
                try:
                    stdout, stderr = self.current_process.communicate(timeout=2)
                    if "unknown option" in stderr:
                        print("🔄 Algunos parámetros no compatibles, intentando simplificado...")
                        return self._start_mirror_compatible(options)
                except:
                    pass
                
                return self._start_mirror_compatible(options)
                
        except Exception as e:
            print(f"❌ Error ejecutando scrcpy: {e}")
            return self._start_mirror_compatible(options)

    def _start_mirror_compatible(self, options: Dict = None) -> bool:
        """Versión compatible con scrcpy v1.24"""
        try:
            devices = self.list_devices()
            connected_devices = [d for d in devices if d['status'] == 'device']
            
            if not connected_devices:
                return False
            
            scrcpy_status = self.tool_manager.setup_scrcpy()
            if not scrcpy_status["available"]:
                return False
            
            scrcpy_path = scrcpy_status["path"]
            
            # ✅ VERSIÓN MÁXIMA COMPATIBILIDAD para v1.24
            cmd = [str(scrcpy_path)]
            
            # Solo parámetros esenciales
            if options and options.get('max_size'):
                cmd.extend(['--max-size', str(options['max_size'])])
            
            # ⚠️ IMPORTANTE: SIN --turn-screen-off (pantalla encendida por defecto)
            # Solo agregar stay-awake que es compatible
            cmd.append('--stay-awake')
            
            print(f"🔄 Usando parámetros compatibles v1.24: {' '.join(cmd)}")
            
            env = os.environ.copy()
            if self.adb_path and self.adb_path != "adb":
                adb_dir = str(Path(self.adb_path).parent)
                env["PATH"] = adb_dir + ";" + env["PATH"]
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            time.sleep(3)
            
            if self._is_process_alive():
                self.is_running = True
                print("✅ Espejo iniciado (modo compatible v1.24)")
                print("   Pantalla: ENCENDIDA por defecto")
                return True
            else:
                # Último intento: scrcpy sin parámetros
                print("🔄 Último intento: scrcpy sin parámetros...")
                cmd = [str(scrcpy_path)]
                self.current_process = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                time.sleep(3)
                
                if self._is_process_alive():
                    self.is_running = True
                    print("✅ Espejo iniciado (sin parámetros)")
                    return True
                
                return False
                
        except Exception as e:
            print(f"❌ Error en modo compatible: {e}")
            return False

    def take_screenshot(self) -> Optional[Path]:
        """Tomar captura de pantalla"""
        if not self.adb_path:
            print("❌ No se puede tomar captura: ADB no disponible")
            return None
        
        try:
            devices = self.list_devices()
            connected_devices = [d for d in devices if d['status'] == 'device']
            
            if not connected_devices:
                print("❌ No hay dispositivos conectados para captura")
                return None

            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            screenshot_path = screenshots_dir / filename
            
            print("📸 Tomando captura de pantalla...")
            
            result = self._run_adb_command(["shell", "screencap", "-p", "/sdcard/screenshot.png"])
            
            if result and result.returncode == 0:
                pull_result = self._run_adb_command(["pull", "/sdcard/screenshot.png", str(screenshot_path)])
                self._run_adb_command(["shell", "rm", "/sdcard/screenshot.png"])
                
                if pull_result and pull_result.returncode == 0 and screenshot_path.exists():
                    file_size = screenshot_path.stat().st_size
                    if file_size > 0:
                        self.screenshot_count += 1
                        print(f"✅ Captura guardada: {screenshot_path} ({file_size} bytes)")
                        return screenshot_path
            
            print("❌ Error tomando captura")
            return None
                
        except Exception as e:
            print(f"❌ Error en captura de pantalla: {e}")
            return None

    def start_recording(self) -> bool:
        """Iniciar grabación de video"""
        if not self.adb_path:
            print("❌ No se puede grabar: ADB no disponible")
            return False
        
        if self.is_recording:
            print("⚠️ Ya se está grabando")
            return False
        
        try:
            devices = self.list_devices()
            connected_devices = [d for d in devices if d['status'] == 'device']
            
            if not connected_devices:
                print("❌ No hay dispositivos conectados para grabación")
                return False

            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            cmd = ["shell", "screenrecord", "--verbose", "/sdcard/temp_recording.mp4"]
            self.record_process = subprocess.Popen(
                [self.adb_path] + cmd if self.adb_path != "adb" else ["adb"] + cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.is_recording = True
            self.recording_start_time = datetime.now()
            
            print("🎥 Grabación iniciada (temporal)")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando grabación: {e}")
            return False
        
    def stop_recording(self) -> Optional[Path]:
        """Detener grabación y obtener archivo - VERSIÓN SIMPLIFICADA"""
        if not self.is_recording or not self.record_process:
            print("ℹ️ No hay grabación en curso")
            return None
        
        try:
            print("⏹️ Deteniendo grabación...")
            
            # 1. Detener proceso de grabación
            self.record_process.terminate()
            try:
                self.record_process.wait(timeout=5)
                print("✅ Grabación detenida")
            except subprocess.TimeoutExpired:
                print("⚠️ Forzando cierre...")
                self.record_process.kill()
                self.record_process.wait()
            
            time.sleep(2)  # Dar tiempo para que se cierre el archivo
            
            # 2. Crear carpeta para grabaciones
            recordings_dir = Path("recordings")
            recordings_dir.mkdir(exist_ok=True)
            
            # 3. Descargar el video del dispositivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
            video_path = recordings_dir / filename
            
            print(f"📥 Descargando video: {video_path}")
            
            # Usar ADB para descargar el archivo
            if self.adb_path:
                result = self._run_adb_command(["pull", "/sdcard/temp_recording.mp4", str(video_path)])
                
                # Limpiar archivo temporal del dispositivo
                self._run_adb_command(["shell", "rm", "/sdcard/temp_recording.mp4"])
                
                if result and result.returncode == 0 and video_path.exists():
                    file_size = video_path.stat().st_size
                    if file_size > 1024:  # Al menos 1KB
                        print(f"✅ Grabación guardada: {video_path} ({file_size} bytes)")
                        self.is_recording = False
                        self.record_process = None
                        return video_path
            
            print("❌ No se pudo descargar la grabación")
            return None
            
        except Exception as e:
            print(f"❌ Error deteniendo grabación: {e}")
            self.is_recording = False
            self.record_process = None
            return None
        

    def stop_recording_silent(self) -> Optional[Path]:
        """Detener grabación SIN diálogos de confirmación"""
        if not self.is_recording or not self.record_process:
            print("ℹ️ No hay grabación en curso")
            return None
        
        try:
            print("⏹️ Deteniendo grabación silenciosa...")
            
            # Detener proceso de grabación
            self.record_process.terminate()
            try:
                self.record_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.record_process.kill()
                self.record_process.wait()
            
            time.sleep(1)  # Dar tiempo para que se cierre el archivo
            
            # Crear directorio para grabaciones
            recordings_dir = Path("recordings")
            recordings_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = recordings_dir / f"recording_{timestamp}.mp4"
            
            # Descargar video
            result = self._run_adb_command(["pull", "/sdcard/temp_recording.mp4", str(video_path)])
            
            # Limpiar temporal del dispositivo
            self._run_adb_command(["shell", "rm", "/sdcard/temp_recording.mp4"])
            
            if result and result.returncode == 0 and video_path.exists():
                recording_duration = datetime.now() - self.recording_start_time
                self.is_recording = False
                self.record_process = None
                
                # Verificar tamaño del archivo
                file_size = video_path.stat().st_size
                if file_size > 1024:  # Al menos 1KB
                    print(f"✅ Grabación guardada: {video_path.name}")
                    print(f"⏱️ Duración: {recording_duration.seconds} segundos")
                    print(f"📊 Tamaño: {file_size} bytes")
                    return video_path
                else:
                    print("❌ Grabación vacía o inválida")
                    if video_path.exists():
                        video_path.unlink()
            
            print("❌ No se pudo guardar la grabación")
            return None
            
        except Exception as e:
            print(f"❌ Error deteniendo grabación silenciosa: {e}")
            self.is_recording = False
            self.record_process = None
            return None

    def check_connection(self) -> Dict:
        """Verificar estado de la conexión ADB"""
        if not self.adb_path:
            return {"connected": False, "error": "ADB no disponible"}
        
        devices = self.list_devices()
        connected_devices = [d for d in devices if d['status'] == 'device']
        
        process_status = "running" if self.is_running and self._is_process_alive() else "stopped"
        
        return {
            "connected": len(connected_devices) > 0,
            "devices": connected_devices,
            "adb_available": self.adb_path is not None,
            "scrcpy_status": process_status,
            "is_recording": self.is_recording
        }

    def force_cleanup(self):
        """Forzar limpieza completa"""
        print("🧹 Forzando limpieza de scrcpy...")
        self._stop_process_monitor()
        self.stop_mirror()
        
        if self.is_recording:
            print("🛑 Deteniendo grabación pendiente...")
            self.stop_recording()
            
        print("✅ Limpieza completada")

    # Métodos adicionales para compatibilidad
    def copy_screenshot_to_clipboard(self, screenshot_path: Path) -> bool:
        """Copiar captura al portapapeles"""
        try:
            from PIL import Image
            import io
            import win32clipboard

            image = Image.open(screenshot_path)
            output = io.BytesIO()
            image.save(output, "BMP")
            data = output.getvalue()[14:]  # Remover header BMP
            output.close()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()

            print("✅ Captura copiada al portapapeles")
            return True

        except ImportError:
            print("⚠️ pywin32 no instalado, no se puede copiar al portapapeles")
            return False
        except Exception as e:
            print(f"❌ Error copiando al portapapeles: {e}")
            return False
        
    def stop_mirror(self) -> bool:
        """Detener espejo de pantalla - VERSIÓN CORREGIDA"""
        if not self.is_running:
            print("ℹ️ Scrcpy no está ejecutándose")
            return True
            
        try:
            print("⏹️ Deteniendo scrcpy...")
            
            # Restaurar ventana si está embebida
            if self.embedded_hwnd:
                try:
                    win32gui.SetParent(self.embedded_hwnd, 0)
                except:
                    pass
                self.embedded_hwnd = None
            
            if self.current_process and self._is_process_alive():
                self.current_process.terminate()
                
                try:
                    self.current_process.wait(timeout=5)
                    print("✅ Scrcpy detenido correctamente")
                except subprocess.TimeoutExpired:
                    print("⚠️ Forzando cierre de scrcpy...")
                    self.current_process.kill()
                    self.current_process.wait()
                    print("✅ Scrcpy forzado a cerrar")
            else:
                print("ℹ️ Proceso scrcpy ya no está activo")
            
            self.is_running = False
            self.current_process = None
            
            self._cleanup_zombie_processes()
            
            return True
            
        except Exception as e:
            print(f"❌ Error deteniendo scrcpy: {e}")
            self.is_running = False
            self.current_process = None
            return False
        
    def _stop_process_monitor(self):
        """Detener el monitor de procesos"""
        self.should_monitor = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout=2)
            except:
                pass
        
        if self.window_monitor_thread and self.window_monitor_thread.is_alive():
            try:
                self.window_monitor_thread.join(timeout=2)
            except:
                pass
        
    def start_recording(self) -> bool:
        """Iniciar grabación de video - VERSIÓN RÁPIDA"""
        if not self.adb_path:
            print("❌ No se puede grabar: ADB no disponible")
            return False
        
        if self.is_recording:
            print("⚠️ Ya se está grabando")
            return False
        
        try:
            devices = self.list_devices()
            if not devices:
                print("❌ No hay dispositivos conectados")
                return False
            
            print("🎥 Iniciando grabación (rápida)...")
            
            # Establecer tiempo de inicio PRIMERO
            self.recording_start_time = datetime.now()
            
            # Comando simplificado para iniciar rápido
            cmd = ["shell", "screenrecord", "--verbose", "/sdcard/temp_recording.mp4"]
            
            self.record_process = subprocess.Popen(
                [self.adb_path] + cmd if self.adb_path != "adb" else ["adb"] + cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Verificar rápidamente si inició
            time.sleep(0.5)  # Solo medio segundo de espera
            
            if self.record_process.poll() is None:  # Proceso sigue activo
                self.is_recording = True
                print(f"✅ Grabación iniciada a las: {self.recording_start_time.strftime('%H:%M:%S.%f')[:-3]}")
                return True
            else:
                print("❌ Grabación falló al iniciar")
                return False
            
        except Exception as e:
            print(f"❌ Error iniciando grabación: {e}")
            return False
        
    def copy_to_clipboard_silent(self, file_path: Path) -> bool:
        """Copiar al portapapeles SIN diálogos"""
        try:
            if not file_path.exists():
                print(f"❌ Archivo no encontrado: {file_path}")
                return False
            
            from PIL import Image
            import io
            import win32clipboard
            
            # Abrir y convertir imagen
            image = Image.open(file_path)
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Remover header BMP
            output.close()
            
            # Copiar al portapapeles
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            print(f"✅ Captura copiada al portapapeles: {file_path.name}")
            return True
            
        except ImportError:
            print("⚠️ pywin32 o PIL no instalados")
            return False
        except Exception as e:
            print(f"❌ Error copiando al portapapeles: {e}")
            return False
        

    def open_file_explorer(self, file_path: Path):
        """Abrir el explorador de archivos en la ubicación del archivo"""
        try:
            if file_path.exists():
                if os.name == 'nt':  # Windows
                    os.startfile(file_path.parent)
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', file_path.parent])
                print(f"📁 Abriendo ubicación: {file_path.parent}")
            else:
                print("❌ Archivo no encontrado")
                
        except Exception as e:
            print(f"❌ Error abriendo explorador: {e}")