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
import win32gui  # ✅ AGREGADO
import win32con   # ✅ AGREGADO
import win32process  # ✅ AGREGADO

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
        self.embedded_hwnd = None  # ✅ AGREGADO para embedding
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
        Iniciar scrcpy embebido en un HWND padre
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
            # COMANDO OPTIMIZADO PARA EMBEDDING
            cmd = [
                str(scrcpy_path),
                '--max-size', str(max_size),
                '--bit-rate', '8M',
                '--max-fps', '30',
                '--turn-screen-off',
                '--stay-awake',
                '--no-control',
                '--window-borderless',
                '--always-on-top',
                '--disable-screensaver'
            ]
            
            env = os.environ.copy()
            if self.adb_path and self.adb_path != "adb":
                adb_dir = str(Path(self.adb_path).parent)
                env["PATH"] = adb_dir + ";" + env["PATH"]
            
            print(f"🚀 Iniciando scrcpy embebido...")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            time.sleep(2)
            
            if self._is_process_alive():
                self.is_running = True
                
                # Buscar y embebir la ventana
                embedding_result = self._embed_scrcpy_window(parent_hwnd)
                
                if embedding_result["success"]:
                    self.embedded_hwnd = embedding_result["hwnd"]
                    return {
                        "success": True, 
                        "process": self.current_process,
                        "hwnd": self.embedded_hwnd,
                        "message": "Scrcpy embebido iniciado correctamente"
                    }
                else:
                    self.stop_mirror()
                    return {"success": False, "error": embedding_result["error"]}
            else:
                return {"success": False, "error": "No se pudo iniciar scrcpy"}
                
        except Exception as e:
            return {"success": False, "error": f"Error: {e}"}

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
        """Iniciar espejo de pantalla normal (no embebido)"""
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
        
        cmd = [str(scrcpy_path)]
        
        if options and options.get('max_size'):
            cmd.extend(['--max-size', str(options['max_size'])])
        
        if options and options.get('always_on_top'):
            cmd.append('--always-on-top')
        
        if options and options.get('window_borderless'):
            cmd.append('--window-borderless')
        
        cmd.extend([
            '--turn-screen-off',
            '--stay-awake',
            '--disable-screensaver'
        ])
        
        try:
            print(f"🚀 Iniciando scrcpy...")
            print(f"   Comando: {' '.join(cmd)}")
            
            env = os.environ.copy()
            if self.adb_path and self.adb_path != "adb":
                adb_dir = str(Path(self.adb_path).parent)
                env["PATH"] = adb_dir + ";" + env["PATH"]
                print(f"   ADB path: {adb_dir}")
            
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
                print("✅ Espejo de pantalla iniciado correctamente")
                return True
            else:
                try:
                    stdout, stderr = self.current_process.communicate(timeout=1)
                    error_output = stderr if stderr else ""
                    print(f"❌ Scrcpy falló - Código: {self.current_process.returncode}")
                    
                    if error_output:
                        print(f"   Error: {error_output.strip()}")
                except:
                    print(f"❌ Scrcpy falló - No se pudo obtener error")
                
                self.current_process = None
                return False
                
        except Exception as e:
            print(f"❌ Error ejecutando scrcpy: {e}")
            return False

    def stop_mirror(self) -> bool:
        """Detener espejo de pantalla"""
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

    # ... (el resto de los métodos existentes se mantienen igual: take_screenshot, start_recording, etc.)

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
        """Detener grabación y obtener archivo temporal"""
        if not self.is_recording or not self.record_process:
            print("ℹ️ No hay grabación en curso")
            return None
        
        try:
            self.record_process.terminate()
            try:
                self.record_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.record_process.kill()
            
            time.sleep(2)
            
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_video_path = temp_dir / f"temp_recording_{timestamp}.mp4"
            
            result = self._run_adb_command(["pull", "/sdcard/temp_recording.mp4", str(temp_video_path)])
            
            self._run_adb_command(["shell", "rm", "/sdcard/temp_recording.mp4"])
            
            if result and result.returncode == 0 and temp_video_path.exists():
                recording_duration = datetime.now() - self.recording_start_time
                self.is_recording = False
                self.record_process = None
                
                print(f"✅ Grabación temporal guardada: {temp_video_path}")
                print(f"⏱️ Duración: {recording_duration}")
                
                return temp_video_path
            
            return None
            
        except Exception as e:
            print(f"❌ Error deteniendo grabación: {e}")
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