import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from pathlib import Path
import os
from datetime import datetime
from PIL import Image, ImageTk
import io
import subprocess
import sys

class ScrcpyDialog:
    def __init__(self, parent, scrcpy_manager, styles=None, logger=None):
        self.parent = parent
        self.scrcpy_manager = scrcpy_manager
        self.styles = styles or {}
        self.logger = logger
        self.dialog = None
        self.last_screenshot_dir = None
        self.last_recording_dir = None
        self.is_running = False
        self.recording_start_time = None
        self.preview_window = None
        self.monitor_active = True  # Para monitorear scrcpy
        self.device_info = {
            'model': 'Dispositivo',
            'serial': '------',
            'manufacturer': 'Desconocido',
            'android_version': '?',
            'device_name': ''
        }
        
    def mostrar(self):
        """Mostrar diálogo compacto estilo imagen"""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("Android Mirror")
            self.dialog.geometry("400x100")  
            self.dialog.minsize(400, 100)
            self.dialog.configure(bg='#2c3e50')
            self.dialog.resizable(False, False)
            
            # Hacer que siempre esté encima
            self.dialog.attributes('-topmost', True)
            
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
            
            self._create_ultra_compact_interface()
            self._centrar_dialogo()
            
            # Iniciar monitoreo de scrcpy
            self._start_scrcpy_monitor()
            
            return self.dialog
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error abriendo diálogo de scrcpy", e)
            raise e

    def _open_directory(self, file_path):
            """Abrir el directorio que contiene un archivo"""
            try:
                if file_path and os.path.exists(file_path):
                    # Obtener directorio
                    directory = os.path.dirname(file_path)
                    
                    # Abrir en explorador de archivos según sistema operativo
                    if sys.platform == 'win32':
                        os.startfile(directory)
                    elif sys.platform == 'darwin':  # macOS
                        subprocess.Popen(['open', directory])
                    else:  # Linux
                        subprocess.Popen(['xdg-open', directory])
                    
                    return True
                return False
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error abriendo directorio: {file_path}", e)
                return False
            
    def _show_file_saved_notification(self, file_path, file_type="archivo"):
            """Mostrar notificación de archivo guardado"""
            try:
                if not file_path:
                    return
                
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # Convertir tamaño a formato legible
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                elif file_size < 1024 * 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                
                # Actualizar estado con información
                self._update_status(f"{file_type} guardado: {filename} ({size_str})", "#2ecc71")
                
                # Abrir directorio automáticamente
                self._open_directory(file_path)
                
                # Mostrar tooltip temporal
                if hasattr(self, 'dialog') and self.dialog.winfo_exists():
                    # Crear tooltip flotante
                    self._show_tooltip(f"📁 Directorio abierto\n{os.path.dirname(file_path)}")
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error("Error en notificación", e)
        
    def _show_tooltip(self, message, duration=3000):
            """Mostrar tooltip temporal"""
            try:
                # Crear ventana de tooltip
                tooltip = tk.Toplevel(self.dialog)
                tooltip.wm_overrideredirect(True)  # Sin bordes
                tooltip.wm_geometry("+0+0")
                tooltip.configure(bg='#2c3e50', bd=1, relief='solid')
                
                # Crear label
                label = tk.Label(tooltip, text=message, 
                            font=("Segoe UI", 8),
                            bg='#2c3e50', fg='white',
                            padx=10, pady=5)
                label.pack()
                
                # Posicionar cerca del mouse
                x = self.dialog.winfo_pointerx() + 10
                y = self.dialog.winfo_pointery() + 10
                tooltip.wm_geometry(f"+{x}+{y}")
                
                # Destruir después de la duración
                tooltip.after(duration, tooltip.destroy)
                
            except:
                pass  # Ignorar errores de tooltip
            
            
    def _start_scrcpy_monitor(self):
        """Iniciar monitoreo de scrcpy para detectar cuando se cierra"""
        def monitor_scrcpy():
            while self.monitor_active and self.dialog and self.dialog.winfo_exists():
                try:
                    # Verificar si scrcpy sigue corriendo
                    if self.is_running:
                        # Verificar proceso directamente
                        if not self.scrcpy_manager._is_process_alive():
                            print("🔍 Scrcpy se cerró, cerrando diálogo...")
                            self.dialog.after(0, self._close_dialog_on_scrcpy_exit)
                            break
                    
                    time.sleep(2)  # Verificar cada 2 segundos
                    
                except Exception as e:
                    if self.logger:
                        self.logger.log_error("Error en monitor scrcpy", e)
                    break
        
        # Iniciar monitoreo en hilo separado
        threading.Thread(target=monitor_scrcpy, daemon=True).start()
    
    def _close_dialog_on_scrcpy_exit(self):
        """Cerrar diálogo cuando scrcpy se cierra"""
        try:
            self.is_running = False
            self.monitor_active = False
            
            # Cerrar diálogo inmediatamente
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.destroy()
                self.dialog = None
                
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error cerrando diálogo", e)

    def _get_device_info_via_adb(self, serial):
        """Obtener información del dispositivo SOLO via ADB - sin nombres específicos"""
        device_info = {
            'serial': serial,
            'model': 'Dispositivo',
            'manufacturer': 'Desconocido',
            'android_version': '?',
            'device_name': 'Android Device'
        }
        
        try:
            # Propiedades básicas a obtener via ADB
            properties = {
                'model': 'ro.product.model',
                'manufacturer': 'ro.product.manufacturer', 
                'android_version': 'ro.build.version.release',
                'brand': 'ro.product.brand',
                'device': 'ro.product.device',
                'product': 'ro.product.name'
            }
            
            for key, prop in properties.items():
                try:
                    # Usar ADB para obtener propiedad
                    result = subprocess.run(
                        ['adb', '-s', serial, 'shell', 'getprop', prop],
                        capture_output=True, 
                        text=True, 
                        timeout=3,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        value = result.stdout.strip()
                        if key == 'model':
                            device_info['model'] = value
                        elif key == 'manufacturer':
                            device_info['manufacturer'] = value
                        elif key == 'android_version':
                            device_info['android_version'] = value
                        elif key == 'brand':
                            device_info['brand'] = value
                        elif key == 'product':
                            device_info['product'] = value
                            
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
            
            # Intentar obtener nombre del dispositivo
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'settings', 'get', 'global', 'device_name'],
                    capture_output=True, 
                    text=True, 
                    timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['device_name'] = result.stdout.strip()
            except:
                pass
            
            # Si no se pudo obtener modelo, usar "Dispositivo Android"
            if device_info['model'] == 'Dispositivo':
                if 'brand' in device_info and device_info['brand'] != 'Desconocido':
                    device_info['model'] = f"{device_info['brand']} Device"
                else:
                    device_info['model'] = ''
            
            return device_info
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error obteniendo info via ADB para {serial}", e)
            return device_info

    def _create_ultra_compact_interface(self):
        """Interfaz ultra compacta como la imagen - 3 botones centrados"""
        main_frame = tk.Frame(self.dialog, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Fila 1: Información del dispositivo
        device_frame = tk.Frame(main_frame, bg='#2c3e50')
        device_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Estado
        self.status_indicator = tk.Label(device_frame, text="●", 
                                        font=("Segoe UI", 8),
                                        fg='#e74c3c', bg='#2c3e50')
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(device_frame, text="0 conectado", 
                                   font=("Segoe UI", 9),
                                   fg='#ecf0f1', bg='#2c3e50')
        self.status_text.pack(side=tk.LEFT, padx=(2, 10))
        
        # Nombre del dispositivo
        self.device_name = tk.Label(device_frame, text="Dispositivo", 
                           font=("Segoe UI", 9, "bold"),
                           bg='#2c3e50', fg='#ecf0f1')
        self.device_name.pack(side=tk.LEFT)
        
        # Serial
        self.device_sn = tk.Label(device_frame, text="S/N: ------", 
                         font=("Segoe UI", 8),
                         bg='#2c3e50', fg='#bdc3c7')
        self.device_sn.pack(side=tk.RIGHT)
        
        # Fila 2: 3 BOTONES CENTRADOS
        buttons_frame = tk.Frame(main_frame, bg='#2c3e50')
        buttons_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Crear solo 3 botones
        self.reload_btn = self._create_compact_button(
            buttons_frame, "🔄 recargar", self._reload_device, '#3498db', 80)
        
        self.screenshot_btn = self._create_compact_button(
            buttons_frame, "📸 screen shot", self._take_screenshot, '#2ecc71', 80)
        
        # Botón unificado GRABAR/DETENER
        self.record_btn = self._create_compact_button(
            buttons_frame, "🔴 grabar", self._toggle_recording, '#e74c3c', 80)
        
        # Posicionar botones centrados
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        buttons_frame.grid_columnconfigure(2, weight=1)
        
        self.reload_btn.grid(row=0, column=0, padx=2, sticky='ew')
        self.screenshot_btn.grid(row=0, column=1, padx=2, sticky='ew')
        self.record_btn.grid(row=0, column=2, padx=2, sticky='ew')
        
        # Fila 3: Información de grabación
        self.recording_info = tk.Label(main_frame, text="", 
                                      font=("Segoe UI", 8),
                                      fg='#f39c12', bg='#2c3e50')
        self.recording_info.pack(pady=(5, 0))
        
        # Iniciar mirror automáticamente
        self._auto_start_mirror()

    def _create_compact_button(self, parent, text, command, color, width=80):
        """Crear botón compacto"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 8),
            bg=color,
            fg='white',
            relief='flat',
            bd=0,
            padx=5,
            pady=4,
            cursor='hand2',
            width=12
        )
        
        def on_enter(e):
            if btn['state'] == 'normal':
                btn['bg'] = self._lighten_color(color, 10)
            
        def on_leave(e):
            if btn['state'] == 'normal':
                btn['bg'] = color
                
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _lighten_color(self, color, percent):
        """Aclarar color"""
        try:
            color = color.lstrip('#')
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            light_rgb = tuple(min(255, int(c * (1 + percent/100))) for c in rgb)
            return f'#{light_rgb[0]:02x}{light_rgb[1]:02x}{light_rgb[2]:02x}'
        except:
            return color

    def _auto_start_mirror(self):
        """Iniciar mirror automáticamente al abrir SIN diálogos"""
        def auto_start_thread():
            try:
                self._update_status("Conectando...", "#f39c12")
                self._disable_all_buttons()
                
                if not self.scrcpy_manager.ensure_available():
                    self._update_status("Error ADB", "#e74c3c")
                    self._enable_all_buttons()
                    return
                
                devices = self.scrcpy_manager.list_devices()
                if not devices:
                    self._update_status("0 conectado", "#e74c3c")
                    self._enable_all_buttons()
                    return
                
                # Obtener información del dispositivo via ADB
                device_info = devices[0]
                serial = device_info.get('serial', '')
                
                # Usar ADB para obtener info real
                detailed_info = self._get_device_info_via_adb(serial)
                self.device_info = detailed_info
                
                # Mostrar información real
                model = detailed_info.get('model', 'Dispositivo')
                self.device_name.config(text=model)
                self.device_sn.config(text=f"S/N: {serial}")
                
                # Iniciar mirror
                options = {
                    'max_size': 1024,
                    'stay_awake': True,
                    'turn_screen_off': False,
                    'show_touches': False
                }
                
                success = self.scrcpy_manager.start_mirror(options)
                
                if success:
                    self.is_running = True
                    self._update_buttons_state()
                    device_count = len(devices)
                    self._update_status(f"{device_count} conectado", "#2ecc71")
                else:
                    self._update_status("Error mirror", "#e74c3c")
                
                self._enable_all_buttons()
                    
            except Exception as e:
                self._update_status("Error inicio", "#e74c3c")
                self._enable_all_buttons()
                if self.logger:
                    self.logger.log_error("Error auto-start", e)
        
        threading.Thread(target=auto_start_thread, daemon=True).start()

    def _reload_device(self):
        """Recargar dispositivo - reinicia scrcpy completamente"""
        def reload_thread():
            try:
                self._update_status("Reiniciando...", "#f39c12")
                self._disable_all_buttons()
                
                # Detener mirror actual si está corriendo
                if self.is_running:
                    # Detener grabación si está activa
                    if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
                        # Usar método seguro
                        try:
                            self.scrcpy_manager.stop_recording()
                        except:
                            pass
                        self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                        self.recording_info.config(text="")
                    
                    # Detener mirror
                    try:
                        self.scrcpy_manager.stop_mirror()
                    except AttributeError as e:
                        # Si no existe el método, crear uno básico
                        print(f"⚠️ Método stop_mirror no disponible: {e}")
                        self._stop_mirror_fallback()
                    
                    self.is_running = False
                
                # Buscar dispositivos nuevamente
                devices = self.scrcpy_manager.list_devices()
                
                if devices:
                    device_info = devices[0]
                    serial = device_info.get('serial', '')
                    
                    # Obtener información real via ADB
                    detailed_info = self._get_device_info_via_adb(serial)
                    self.device_info = detailed_info
                    
                    model = detailed_info.get('model', 'Dispositivo')
                    self.device_name.config(text=model)
                    self.device_sn.config(text=f"S/N: {serial}")
                    self._update_status(f"{len(devices)} conectado", "#2ecc71")
                    
                    # Reiniciar mirror
                    options = {
                        'max_size': 1024,
                        'stay_awake': True,
                        'turn_screen_off': False,
                        'show_touches': False
                    }
                    
                    success = self.scrcpy_manager.start_mirror(options)
                    
                    if success:
                        self.is_running = True
                        self._update_buttons_state()
                        self._update_status(f"Reiniciado - {len(devices)} conectado", "#2ecc71")
                    else:
                        self._update_status("Error reiniciando", "#e74c3c")
                else:
                    self.device_name.config(text="Dispositivo")
                    self.device_sn.config(text="S/N: ------")
                    self._update_status("0 conectado", "#e74c3c")
                    self.is_running = False
                    self._update_buttons_state()
                
                self._enable_all_buttons()
                    
            except Exception as e:
                self._update_status("Error recarga", "#e74c3c")
                self._enable_all_buttons()
                if self.logger:
                    self.logger.log_error("Error en recarga", e)
        
        threading.Thread(target=reload_thread, daemon=True).start()

    def _stop_mirror_fallback(self):
        """Fallback para detener mirror si no existe el método"""
        try:
            if hasattr(self.scrcpy_manager, 'current_process') and self.scrcpy_manager.current_process:
                self.scrcpy_manager.current_process.terminate()
                try:
                    self.scrcpy_manager.current_process.wait(timeout=3)
                except:
                    pass
                self.scrcpy_manager.current_process = None
            
            if hasattr(self.scrcpy_manager, 'is_running'):
                self.scrcpy_manager.is_running = False
            
            print("✅ Mirror detenido (fallback)")
        except Exception as e:
            print(f"❌ Error deteniendo mirror (fallback): {e}")

    def _take_screenshot(self):
        """Tomar captura de pantalla con guardado automático"""
        if not self.is_running:
            self._update_status("Mirror no activo", "#e74c3c")
            self.dialog.after(2000, lambda: self._update_status("1 conectado", "#2ecc71"))
            return
        
        def screenshot_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Capturando...", "#f39c12")
                
                # Tomar screenshot
                screenshot_path = None
                
                try:
                    screenshot_path = self.scrcpy_manager.take_screenshot()
                except Exception as e:
                    if self.logger:
                        self.logger.log_error("Error usando take_screenshot", e)
                
                # Método alternativo si falla
                if not screenshot_path:
                    screenshot_path = self._take_screenshot_fallback()
                
                if screenshot_path and screenshot_path.exists():
                    # Guardar referencia al directorio
                    self.last_screenshot_dir = str(screenshot_path.parent)
                    
                    # Mostrar preview con opción de guardar en diferente ubicación
                    with open(screenshot_path, 'rb') as f:
                        screenshot_data = f.read()
                    
                    self._show_screenshot_preview(str(screenshot_path), screenshot_data)
                    self._update_status("Captura tomada", "#2ecc71")
                else:
                    self._update_status("Error captura", "#e74c3c")
                    self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))
                    
            except Exception as e:
                self._update_status("Error captura", "#e74c3c")
                if self.logger:
                    self.logger.log_error("Error en screenshot_thread", e)
                self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))
            finally:
                self._enable_all_buttons()
        
        threading.Thread(target=screenshot_thread, daemon=True).start()

    def _take_screenshot_fallback(self):
        """Método de fallback para capturas"""
        try:
            devices = self.scrcpy_manager.list_devices()
            if not devices:
                return None
            
            serial = devices[0].get('serial', '')
            if not serial:
                return None
            
            # Directorio de screenshots
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            screenshot_path = screenshots_dir / filename
            
            # Usar ADB directamente
            result = subprocess.run(
                ['adb', '-s', serial, 'exec-out', 'screencap', '-p'],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0 and result.stdout:
                with open(screenshot_path, 'wb') as f:
                    f.write(result.stdout)
                
                if screenshot_path.exists() and screenshot_path.stat().st_size > 0:
                    return screenshot_path
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error en fallback screenshot", e)
            return None

    def _position_window_within_screen(self, window, width, height, reference_window=None):
        """Posicionar ventana dentro de los límites de la pantalla"""
        try:
            # Obtener dimensiones de la pantalla
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            
            if reference_window and reference_window.winfo_exists():
                # Posicionar relativo a la ventana de referencia
                ref_x = reference_window.winfo_x()
                ref_y = reference_window.winfo_y()
                ref_width = reference_window.winfo_width()
                ref_height = reference_window.winfo_height()
                
                # Calcular posición centrada relativa
                x = ref_x + (ref_width - width) // 2
                y = ref_y + (ref_height - height) // 2
            else:
                # Centrar en pantalla
                x = (screen_width - width) // 2
                y = (screen_height - height) // 2
            
            # Asegurar que la ventana esté dentro de los límites de la pantalla
            x = max(0, min(x, screen_width - width - 10))
            y = max(0, min(y, screen_height - height - 10))
            
            return x, y
            
        except Exception as e:
            # Fallback: centrar en pantalla
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            return (screen_width - width) // 2, (screen_height - height) // 2

    def _show_screenshot_preview(self, image_path, image_data):
        """Mostrar preview de la captura con posicionamiento inteligente"""
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        
        try:
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            max_preview_width = 500
            max_preview_height = 500
            
            ratio = min(max_preview_width / original_width, max_preview_height / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            image.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            window_width = max(new_width + 60, 450)
            window_height = new_height + 180
            
        except Exception as e:
            window_width = 450
            window_height = 500
            photo = None
            if self.logger:
                self.logger.log_error("Error procesando imagen", e)
        
        self.preview_window = tk.Toplevel(self.dialog)
        self.preview_window.title("Preview - Captura de Pantalla")
        self.preview_window.geometry(f"{window_width}x{window_height}")
        self.preview_window.configure(bg='#f0f0f0')
        self.preview_window.resizable(False, False)
        self.preview_window.attributes('-topmost', True)
        
        # ✅ MEJORADO: Posicionar ventana dentro de la pantalla
        x, y = self._position_window_within_screen(self.preview_window, window_width, window_height, self.dialog)
        self.preview_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        main_container = tk.Frame(self.preview_window, bg='#2c3e50', bd=2, relief='raised')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ✅ MEJORADO: Header con botón de cancelar
        header_frame = tk.Frame(main_container, bg='#34495e', height=40)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        header_frame.pack_propagate(False)
        
        device_text = f"📱 {self.device_info.get('model', 'Dispositivo')}"
        header_label = tk.Label(header_frame, text=device_text, 
                               font=("Segoe UI", 9, "bold"),
                               bg='#34495e', fg='white')
        header_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        # ✅ NUEVO: Botón Cancelar en el header
        cancel_header_btn = tk.Button(
            header_frame,
            text="✕ Cancelar",
            command=lambda: self._cancel_preview(image_path),
            font=("Segoe UI", 9),
            bg='#34495e',
            fg='white',
            relief='flat',
            bd=0,
            padx=5,
            cursor='hand2'
        )
        cancel_header_btn.pack(side=tk.RIGHT, padx=(0, 10))
        cancel_header_btn.bind("<Enter>", lambda e: cancel_header_btn.config(bg='#e74c3c'))
        cancel_header_btn.bind("<Leave>", lambda e: cancel_header_btn.config(bg='#34495e'))
        
        image_container = tk.Frame(main_container, bg='#2c3e50', bd=1, relief='sunken')
        image_container.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        if photo:
            image_label = tk.Label(image_container, image=photo, bg='#2c3e50')
            image_label.image = photo
            image_label.pack(pady=10, padx=10)
        else:
            error_label = tk.Label(image_container, text="Error cargando imagen", 
                                 fg='white', bg='#2c3e50', font=("Segoe UI", 10))
            error_label.pack(pady=20)
        
        # ✅ MEJORADO: Frame para información
        info_frame = tk.Frame(main_container, bg='#2c3e50')
        info_frame.pack(fill=tk.X, pady=(0, 10), padx=20)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info_label = tk.Label(info_frame, text=f"📅 Captura tomada: {timestamp}", 
                             font=("Segoe UI", 8),
                             fg='#bdc3c7', bg='#2c3e50')
        info_label.pack(side=tk.LEFT)
        
        size_label = tk.Label(info_frame, text=f"📏 Tamaño: {original_width}x{original_height}", 
                             font=("Segoe UI", 8),
                             fg='#bdc3c7', bg='#2c3e50')
        size_label.pack(side=tk.RIGHT)
        
        # ✅ MEJORADO: Botones mejor organizados
        buttons_frame = tk.Frame(main_container, bg='#2c3e50')
        buttons_frame.pack(pady=(5, 5), padx=20, fill=tk.X)
        
        # Crear 3 botones en una fila
        copy_btn = tk.Button(
            buttons_frame,
            text="📋 Copiar",
            command=lambda: self._copy_to_clipboard(image_data, image_path),
            font=("Segoe UI", 9, "bold"),
            bg='#3498db',
            fg='white',
            relief='raised',
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            width=10
        )
        copy_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        save_btn = tk.Button(
            buttons_frame,
            text="💾 Guardar",
            command=lambda: self._save_screenshot(image_path),
            font=("Segoe UI", 9, "bold"),
            bg='#2ecc71',
            fg='white',
            relief='raised',
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            width=10
        )
        save_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # ✅ NUEVO: Botón Cancelar adicional
        cancel_btn = tk.Button(
            buttons_frame,
            text="❌ Cancelar",
            command=lambda: self._cancel_preview(image_path),
            font=("Segoe UI", 9, "bold"),
            bg='#e74c3c',
            fg='white',
            relief='raised',
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # ✅ MEJORADO: Añadir efectos hover a los botones
        def add_hover_effect(btn, normal_color):
            btn.bind("<Enter>", lambda e: btn.config(bg=self._lighten_color(normal_color, 15)))
            btn.bind("<Leave>", lambda e: btn.config(bg=normal_color))
        
        add_hover_effect(copy_btn, '#3498db')
        add_hover_effect(save_btn, '#2ecc71')
        add_hover_effect(cancel_btn, '#e74c3c')
        add_hover_effect(cancel_header_btn, '#e74c3c')

    def _cancel_preview(self, temp_path):
        """Cancelar preview y limpiar SIN diálogos"""
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        self._update_status("Captura cancelada", "#e74c3c")
        # Restaurar status después de 2 segundos
        self.dialog.after(2000, lambda: self._update_status("1 conectado", "#2ecc71"))

    def _copy_to_clipboard(self, image_data, temp_path):
        """Copiar imagen al portapapeles SIN diálogos"""
        try:
            import win32clipboard
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_data))
            output = io.BytesIO()
            image.save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
            
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            self._update_status("Copiado al portapapeles", "#2ecc71")
            # Restaurar status después de 3 segundos
            self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))
            
        except ImportError:
            self._update_status("pywin32 no instalado", "#e74c3c")
            self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error copiando al portapapeles", e)
            self._update_status("Error copiando", "#e74c3c")
            self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))

    def _save_screenshot(self, temp_path):
        """Guardar screenshot con nombre amigable"""
        try:
            # Guardar automáticamente en carpeta screenshots
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            # Crear nombre amigable
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            device_name = self.device_info.get('model', 'Dispositivo')
            
            # Limpiar nombre del dispositivo
            clean_device_name = "".join(c for c in device_name if c.isalnum() or c in (' ', '-', '_'))
            clean_device_name = clean_device_name.replace(' ', '_')[:30]  # Limitar longitud
            
            # Nombre amigable
            friendly_name = f"Captura_{clean_device_name}_{timestamp}.png"
            final_path = screenshots_dir / friendly_name
            
            import shutil
            shutil.copy2(temp_path, str(final_path))
            
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
            
            # Eliminar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            # Guardar referencia al directorio
            self.last_screenshot_dir = str(screenshots_dir)
            
            # Mostrar notificación con nombre amigable
            self._show_file_saved_notification(str(final_path), "captura")
                
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error guardando screenshot", e)
            self._update_status("Error guardando", "#e74c3c")
            self.dialog.after(3000, lambda: self._update_status("1 conectado", "#2ecc71"))
            
    def _take_screenshot_alternative(self, file_path):
        """Método alternativo para tomar screenshot"""
        try:
            devices = self.scrcpy_manager.list_devices()
            if devices:
                serial = devices[0].get('serial', '')
                if serial:
                    result = subprocess.run(
                        ['adb', '-s', serial, 'exec-out', 'screencap', '-p'],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0 and result.stdout:
                        with open(file_path, 'wb') as f:
                            f.write(result.stdout)
                        return os.path.exists(file_path) and os.path.getsize(file_path) > 0
            return False
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error en método alternativo screenshot", e)
            return False

    def _toggle_recording(self):
        """Botón unificado GRABAR/DETENER - SIN DELAY"""
        if not self.is_running:
            self._update_status("Mirror no activo", "#e74c3c")
            self.dialog.after(2000, lambda: self._update_status("1 conectado", "#2ecc71"))
            return
        
        def recording_thread():
            try:
                # Verificar estado actual
                is_recording = False
                if hasattr(self.scrcpy_manager, 'is_recording'):
                    is_recording = self.scrcpy_manager.is_recording
                
                if not is_recording:
                    # INICIAR grabación - SIN ACTUALIZAR UI PRIMERO
                    self._disable_all_buttons()
                    self._update_status("Iniciando...", "#f39c12")
                    
                    success = False
                    if hasattr(self.scrcpy_manager, 'start_recording'):
                        success = self.scrcpy_manager.start_recording()
                    
                    if success:
                        # Solo actualizar UI después de confirmar que inició
                        self.record_btn.config(text="⏹️ detener", bg='#c0392b')
                        self._update_status("Grabando...", "#e74c3c")
                        
                        # Obtener tiempo REAL de inicio (usar el del manager si existe)
                        if hasattr(self.scrcpy_manager, 'recording_start_time'):
                            self.recording_start_time = self.scrcpy_manager.recording_start_time
                        else:
                            self.recording_start_time = datetime.now()
                        
                        # Iniciar timer con tiempo real
                        self._start_recording_timer()
                    else:
                        self._update_status("Error inicio", "#e74c3c")
                    
                    self._enable_all_buttons()
                else:
                    # DETENER grabación
                    self._stop_recording_accurate()
                    
            except Exception as e:
                print(f"❌ Error en recording_thread: {e}")
                self._update_status("Error", "#e74c3c")
                self._enable_all_buttons()
        
        threading.Thread(target=recording_thread, daemon=True).start()

    def _stop_recording_accurate(self):
        """Detener grabación con tiempo preciso - NO ABRIR DIRECTORIO"""
        def stop_recording_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Finalizando...", "#f39c12")
                
                # 1. Guardar tiempo ANTES de detener
                stop_time = datetime.now()
                recording_duration = None
                
                if self.recording_start_time:
                    recording_duration = (stop_time - self.recording_start_time).total_seconds()
                    print(f"⏱️ Duración grabación: {recording_duration:.1f} segundos")
                
                # 2. Detener grabación
                video_path = None
                if hasattr(self.scrcpy_manager, 'stop_recording'):
                    video_path = self.scrcpy_manager.stop_recording()
                
                # 3. Actualizar UI inmediatamente
                self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                self.recording_info.config(text="")
                
                # 4. Si hay video, preguntar dónde guardar (SIN ABRIR DIRECTORIO)
                if video_path and isinstance(video_path, Path) and video_path.exists():
                    # Mostrar diálogo para elegir ubicación
                    self.dialog.after(0, lambda: self._ask_save_location_simple(video_path, recording_duration))
                else:
                    self._update_status("No se grabó video", "#e74c3c")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                self._update_status("Error grabación", "#e74c3c")
            finally:
                self._enable_all_buttons()
        
        threading.Thread(target=stop_recording_thread, daemon=True).start()

    def _stop_recording_silent(self):
        """Detener grabación y permitir elegir dónde guardar"""
        def stop_recording_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Finalizando...", "#f39c12")
                
                video_path = None
                
                # 1. Detener grabación
                if hasattr(self.scrcpy_manager, 'stop_recording'):
                    try:
                        video_path = self.scrcpy_manager.stop_recording()
                        print(f"📹 Video temporal obtenido: {video_path}")
                    except Exception as e:
                        print(f"❌ Error ejecutando stop_recording: {e}")
                        video_path = None
                else:
                    print("❌ Método stop_recording NO existe")
                    self._update_status("Error método", "#e74c3c")
                    return
                
                # 2. Actualizar UI inmediatamente
                self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                self.recording_info.config(text="")
                
                # 3. Si hay video, preguntar dónde guardar
                if video_path and isinstance(video_path, Path) and video_path.exists():
                    # Mostrar diálogo para elegir ubicación
                    self.dialog.after(0, lambda: self._ask_save_location(video_path))
                else:
                    self._update_status("No se grabó video", "#e74c3c")
                    print("⚠️ No se obtuvo archivo de video válido")
                
            except Exception as e:
                print(f"❌ Error general en stop_recording_thread: {e}")
                self._update_status("Error grabación", "#e74c3c")
            finally:
                self._enable_all_buttons()
        
        threading.Thread(target=stop_recording_thread, daemon=True).start()

    def _ask_save_location_simple(self, temp_video_path, duration=None):
        """Preguntar dónde guardar con nombre amigable"""
        try:
            # Crear nombre amigable con duración si está disponible
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            device_name = self.device_info.get('model', 'Dispositivo')
            
            # Limpiar nombre del dispositivo
            clean_device_name = "".join(c for c in device_name if c.isalnum() or c in (' ', '-', '_'))
            clean_device_name = clean_device_name.replace(' ', '_')[:30]
            
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                if minutes > 0:
                    duration_str = f"{minutes}min{seconds}seg"
                else:
                    duration_str = f"{seconds}seg"
                default_name = f"Grabacion_{clean_device_name}_{timestamp}_{duration_str}.mp4"
            else:
                default_name = f"Grabacion_{clean_device_name}_{timestamp}.mp4"
            
            # Diálogo para elegir ubicación con nombre amigable
            file_path = filedialog.asksaveasfilename(
                title="Guardar Grabación",
                defaultextension=".mp4",
                filetypes=[
                    ("MP4 files", "*.mp4"),
                    ("Video files", "*.mp4;*.avi;*.mov;*.mkv"),
                    ("Todos los archivos", "*.*")
                ],
                initialfile=default_name,
                initialdir=os.path.expanduser("~/Desktop")
            )
            
            if file_path:
                # Mover archivo
                import shutil
                shutil.move(str(temp_video_path), file_path)
                
                # Solo mostrar confirmación
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # Convertir tamaño a formato legible
                if file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                elif file_size < 1024 * 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                
                # Mostrar info amigable
                if duration:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    if minutes > 0:
                        duration_msg = f"{minutes}min {seconds}seg"
                    else:
                        duration_msg = f"{seconds}seg"
                    status_msg = f"✅ Video guardado: {duration_msg}, {size_str}"
                else:
                    status_msg = f"✅ Video guardado: {size_str}"
                
                self._update_status(status_msg, "#2ecc71")
                
                # Opcional: mostrar notificación breve
                self._show_simple_notification("📹 Grabación guardada", filename)
                
            else:
                # Usuario canceló
                self._update_status("Grabación cancelada", "#e74c3c")
                if temp_video_path.exists():
                    temp_video_path.unlink()
                
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            self._update_status("Error guardando", "#e74c3c")

    def _show_simple_notification(self, title, message, duration=2000):
        """Mostrar notificación simple"""
        try:
            # Actualizar el texto del status brevemente
            original_text = self.status_text.cget("text")
            original_color = self.status_indicator.cget("fg")
            
            self._update_status(f"{title}: {message}", "#2ecc71")
            
            # Restaurar después de un tiempo
            def restore():
                if self.dialog and self.dialog.winfo_exists():
                    self._update_status(original_text, original_color)
            
            self.dialog.after(duration, restore)
            
        except:
            pass


    def _show_save_notification(self, file_path, duration=None, file_size=None):
        """Mostrar notificación de guardado (opcional)"""
        try:
            filename = os.path.basename(file_path)
            directory = os.path.dirname(file_path)
            
            # Crear tooltip flotante
            tooltip = tk.Toplevel(self.dialog)
            tooltip.wm_overrideredirect(True)
            tooltip.configure(bg='#2c3e50', bd=1, relief='solid')
            
            # Contenido del tooltip
            message = f"✅ Grabación guardada\n📁 {filename}"
            
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                message += f"\n⏱️  {minutes:02d}:{seconds:02d}"
            
            if file_size:
                if file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                message += f"\n📊 {size_str}"
            
            label = tk.Label(tooltip, text=message, 
                            font=("Segoe UI", 8),
                            bg='#2c3e50', fg='white',
                            padx=10, pady=5)
            label.pack()
            
            # Posicionar cerca del diálogo
            x = self.dialog.winfo_x() + 50
            y = self.dialog.winfo_y() + 50
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Auto-destruir después de 3 segundos
            tooltip.after(3000, tooltip.destroy)
            
        except:
            pass  # Ignorar errores del tooltip

    def _stop_recording_only(self):
        """Detener solo la grabación"""
        def stop_recording_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Finalizando...", "#f39c12")
                
                video_path = None
                if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
                    video_path = self.scrcpy_manager.stop_recording()
                
                self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                self.recording_info.config(text="")
                
                if video_path and os.path.exists(video_path):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    model_name = self.device_info.get('model', 'grabacion').replace(' ', '_')
                    default_name = f"{model_name}_{timestamp}.mp4"
                    final_path = filedialog.asksaveasfilename(
                        title="Guardar grabación de video",
                        defaultextension=".mp4",
                        filetypes=[("MP4 files", "*.mp4"), ("Todos los archivos", "*.*")],
                        initialfile=default_name
                    )
                    
                    if final_path:
                        import shutil
                        shutil.move(video_path, final_path)
                        self._update_status("Grabación guardada", "#2ecc71")
                    else:
                        if os.path.exists(video_path):
                            os.unlink(video_path)
                        self._update_status("Grabación cancelada", "#e74c3c")
                else:
                    self._update_status("1 conectado", "#2ecc71")
                
            except Exception as e:
                self._update_status("Error", "#e74c3c")
                if self.logger:
                    self.logger.log_error("Error guardando grabación", e)
                messagebox.showerror("❌ Error", f"Error al guardar grabación: {str(e)}")
            finally:
                self._enable_all_buttons()
        
        threading.Thread(target=stop_recording_thread, daemon=True).start()

    def _start_recording_timer(self):
        """Timer de grabación preciso"""
        try:
            # Verificar si sigue grabando
            is_recording = False
            if hasattr(self.scrcpy_manager, 'is_recording'):
                is_recording = self.scrcpy_manager.is_recording
            
            if is_recording and self.recording_start_time:
                # Calcular tiempo transcurrido con precisión
                elapsed = (datetime.now() - self.recording_start_time).total_seconds()
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                
                # Actualizar UI
                self.recording_info.config(text=f"Grabando: {minutes:02d}:{seconds:02d}")
                
                # Programar próxima actualización
                self.dialog.after(1000, self._start_recording_timer)
            else:
                # Si dejó de grabar, limpiar
                self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                self.recording_info.config(text="")
                
        except Exception as e:
            print(f"❌ Error en timer: {e}")
            # IMPORTANTE: La siguiente línea debe estar indentada
            pass 
    def _update_status(self, text, color):
        """Actualizar estado"""
        if self.dialog and self.dialog.winfo_exists():
            self.status_indicator.config(fg=color)
            self.status_text.config(text=text)

    def _update_buttons_state(self):
        """Actualizar estado de botones"""
        if self.is_running:
            self.screenshot_btn.config(state="normal")
            self.record_btn.config(state="normal")
        else:
            self.screenshot_btn.config(state="disabled")
            self.record_btn.config(state="disabled")

    def _disable_all_buttons(self):
        """Deshabilitar temporalmente"""
        for btn in [self.reload_btn, self.screenshot_btn, self.record_btn]:
            btn.config(state="disabled")

    def _enable_all_buttons(self):
        """Rehabilitar"""
        self.reload_btn.config(state="normal")
        self._update_buttons_state()

    def _centrar_dialogo(self):
        """Centrar diálogo"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _on_close(self):
        """Manejar cierre"""
        try:
            # Detener monitoreo
            self.monitor_active = False
            
            # Detener grabación si está activa
            if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
                self._stop_recording_only()
            
            # Cerrar ventana de preview
            if self.preview_window and self.preview_window.winfo_exists():
                self.preview_window.destroy()
                self.preview_window = None
            
            # Cerrar diálogo principal
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.destroy()
                self.dialog = None
                
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error al cerrar diálogo", e)
            try:
                if self.dialog:
                    self.dialog.destroy()
            except:
                pass