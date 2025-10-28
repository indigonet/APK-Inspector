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
import json

class ScrcpyDialog:
    def __init__(self, parent, scrcpy_manager, styles=None, logger=None):
        self.parent = parent
        self.scrcpy_manager = scrcpy_manager
        self.styles = styles or {}
        self.logger = logger
        self.dialog = None
        self.is_running = False
        self.recording_start_time = None
        self.preview_window = None
        self.device_info = {
    'model': 'Dispositivo',
    'serial': '------',
    'manufacturer': 'Desconocido',
    'android_version': '?',
    'device_name': 'Dispositivo Android',
    'device_type': 'DESCONOCIDO'
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
            
            return self.dialog
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error abriendo diálogo de scrcpy", e)
            raise e

    def _create_ultra_compact_interface(self):
        """Interfaz ultra compacta como la imagen - 3 botones centrados"""
        main_frame = tk.Frame(self.dialog, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Fila 1: Información del dispositivo (más compacta)
        device_frame = tk.Frame(main_frame, bg='#2c3e50')
        device_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Estado e información del dispositivo
        self.status_indicator = tk.Label(device_frame, text="●", 
                                        font=("Segoe UI", 8),
                                        fg='#e74c3c', bg='#2c3e50')
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(device_frame, text="0 conectado", 
                                   font=("Segoe UI", 9),
                                   fg='#ecf0f1', bg='#2c3e50')
        self.status_text.pack(side=tk.LEFT, padx=(2, 10))
        
        self.device_name = tk.Label(device_frame, text="Dispositivo", 
                           font=("Segoe UI", 9, "bold"),
                           bg='#2c3e50', fg='#ecf0f1')
        self.device_name.pack(side=tk.LEFT)
        
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
        
        # Botón unificado GRABAR/DETENER (misma posición)
        self.record_btn = self._create_compact_button(
            buttons_frame, "🔴 grabar", self._toggle_recording, '#e74c3c', 80)
        
        # Centrar los botones horizontalmente
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        buttons_frame.grid_columnconfigure(2, weight=1)
        buttons_frame.grid_columnconfigure(3, weight=1)
        
        # Posicionar botones centrados (3 botones distribuidos)
        self.reload_btn.grid(row=0, column=0, padx=2, sticky='ew')
        self.screenshot_btn.grid(row=0, column=1, padx=2, sticky='ew')
        self.record_btn.grid(row=0, column=2, padx=2, sticky='ew')
        
        # Fila 3: Información de grabación
        self.recording_info = tk.Label(main_frame, text="", 
                                      font=("Segoe UI", 8),
                                      fg='#f39c12', bg='#2c3e50')
        self.recording_info.pack(pady=(5, 0))
        
        # Botón de inicio oculto - se activa automáticamente
        self._auto_start_mirror()

    def _get_device_info(self, serial):
        """Obtener información detallada del dispositivo via ADB - MEJORADO"""
        try:
            device_info = {
                'serial': serial,
                'model': 'DX8000',
                'manufacturer': 'ingenico',
                'android_version': '10',
                'device_name': 'DX8000'
            }
            
            # Obtener modelo - método más robusto
            commands = [
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.build.product'],
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.device']
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        device_info['model'] = result.stdout.strip()
                        break
                except:
                    continue
            
            # Obtener fabricante
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.manufacturer'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['manufacturer'] = result.stdout.strip().lower()
            except:
                pass
            
            # Obtener versión de Android
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.build.version.release'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['android_version'] = result.stdout.strip()
            except:
                pass
            
            # Obtener nombre del dispositivo
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.name'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['device_name'] = result.stdout.strip()
            except:
                pass
            
            return device_info
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error obteniendo info del dispositivo {serial}", e)
            # Devolver valores por defecto para Ingenico DX8000
            return {
                'serial': serial,
                'model': 'DX8000',
                'manufacturer': 'ingenico',
                'android_version': '10',
                'device_name': 'DX8000'
            }
        
    def _detect_device_type(self, serial):
        """Detectar tipo de dispositivo basado en el serial number"""
        # Si el serial es alfanumérico de 12 caracteres -> INGENICO
        if len(serial) == 12 and any(c.isalpha() for c in serial) and any(c.isdigit() for c in serial):
            return {
                'type': 'INGENICO',
                'model': 'DX8000', 
                'manufacturer': 'ingenico',
                'default_name': 'DX8000'
            }
        # Si el serial es numérico de 10 dígitos -> PAX
        elif len(serial) == 10 and serial.isdigit():
            return {
                'type': 'PAX',
                'model': 'A920Pro',
                'manufacturer': 'PAX', 
                'default_name': 'A920Pro'
            }
        # Por defecto -> INGENICO
        else:
            return {
                'type': 'INGENICO',
                'model': 'DX8000',
                'manufacturer': 'ingenico',
                'default_name': 'DX8000'
            }

    def _get_device_info(self, serial):
        """Obtener información detallada del dispositivo via ADB - MEJORADO"""
        try:
            # Primero detectar el tipo de dispositivo basado en el serial
            device_type = self._detect_device_type(serial)
            
            device_info = {
                'serial': serial,
                'model': device_type['model'],
                'manufacturer': device_type['manufacturer'],
                'android_version': '10',
                'device_name': device_type['default_name'],
                'device_type': device_type['type']
            }
            
            # Obtener modelo real via ADB
            commands = [
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.build.product'],
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.device']
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        device_info['model'] = result.stdout.strip()
                        break
                except:
                    continue
            
            # Obtener fabricante real
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.manufacturer'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['manufacturer'] = result.stdout.strip().lower()
            except:
                pass
            
            # Obtener versión de Android
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.build.version.release'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['android_version'] = result.stdout.strip()
            except:
                pass
            
            # Obtener nombre del dispositivo
            try:
                result = subprocess.run(
                    ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.name'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    device_info['device_name'] = result.stdout.strip()
            except:
                pass
            
            return device_info
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error obteniendo info del dispositivo {serial}", e)
            # Devolver valores basados en detección por serial
            device_type = self._detect_device_type(serial)
            return {
                'serial': serial,
                'model': device_type['model'],
                'manufacturer': device_type['manufacturer'],
                'android_version': '10',
                'device_name': device_type['default_name'],
                'device_type': device_type['type']
            }

    def _create_compact_button(self, parent, text, command, color, width=80):
        """Crear botón compacto como en la imagen"""
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
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        light_rgb = tuple(min(255, int(c * (1 + percent/100))) for c in rgb)
        return f'#{light_rgb[0]:02x}{light_rgb[1]:02x}{light_rgb[2]:02x}'

    def _auto_start_mirror(self):
        """Iniciar mirror automáticamente al abrir"""
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
                
                # Obtener información detallada del dispositivo
                device_info = devices[0]
                serial = device_info.get('serial', '228AKD863723')
                
                # Obtener información completa del dispositivo
                detailed_info = self._get_device_info(serial)
                self.device_info = detailed_info
                
                # Actualizar info del dispositivo en la UI
                model = detailed_info.get('model', 'DX8000')
                
                self.device_name.config(text=model)
                self.device_sn.config(text=f"S/N: {serial}")
                
                # Configurar e iniciar mirror automáticamente
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
                    self._update_status(f"{len(devices)} conectado", "#2ecc71")
                else:
                    self._update_status("Error mirror", "#e74c3c")
                
                self._enable_all_buttons()
                    
            except Exception as e:
                self._update_status("Error", "#e74c3c")
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
                        self.scrcpy_manager.stop_recording()
                        self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                        self.recording_info.config(text="")
                    
                    # Detener mirror
                    self.scrcpy_manager.stop_mirror()
                    self.is_running = False
                
                # Buscar dispositivos nuevamente
                devices = self.scrcpy_manager.list_devices()
                
                if devices:
                    device_info = devices[0]
                    serial = device_info.get('serial', '228AKD863723')
                    
                    # Obtener información detallada del dispositivo
                    detailed_info = self._get_device_info(serial)
                    self.device_info = detailed_info
                    
                    model = detailed_info.get('model', 'DX8000')
                    
                    self.device_name.config(text=model)
                    self.device_sn.config(text=f"S/N: {serial}")
                    self._update_status(f"{len(devices)} conectado", "#2ecc71")
                    
                    # Reiniciar mirror con nueva configuración
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
                    self.device_name.config(text="DX8000")
                    self.device_sn.config(text="S/N: ------")
                    self._update_status("0 conectado", "#e74c3c")
                    self.is_running = False
                    self._update_buttons_state()
                
                self._enable_all_buttons()
                    
            except Exception as e:
                self._update_status("Error", "#e74c3c")
                self._enable_all_buttons()
                if self.logger:
                    self.logger.log_error("Error en recarga", e)
        
        threading.Thread(target=reload_thread, daemon=True).start()

    def _take_screenshot(self):
        """Tomar captura de pantalla con preview y opciones"""
        if not self.is_running:
            messagebox.showwarning("Advertencia", "El mirror no está activo")
            return
        
        def screenshot_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Capturando...", "#f39c12")
                
                # Tomar screenshot a un archivo temporal
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                success = False
                screenshot_data = None
                
                try:
                    # Método 1: Intentar sin parámetros
                    if hasattr(self.scrcpy_manager, 'take_screenshot'):
                        try:
                            screenshot_path = self.scrcpy_manager.take_screenshot()
                            if screenshot_path and os.path.exists(screenshot_path):
                                # Mover el archivo a la ubicación temporal
                                import shutil
                                shutil.move(screenshot_path, temp_path)
                                success = True
                        except TypeError:
                            # Si falla, intentar con parámetro
                            try:
                                screenshot_path = self.scrcpy_manager.take_screenshot(temp_path)
                                success = screenshot_path and os.path.exists(screenshot_path)
                            except:
                                success = False
                    
                    # Método 2: Alternativo ADB
                    if not success:
                        success = self._take_screenshot_alternative(temp_path)
                    
                    # Leer los datos de la imagen para el portapapeles
                    if success and os.path.exists(temp_path):
                        with open(temp_path, 'rb') as f:
                            screenshot_data = f.read()
                            
                except Exception as e:
                    if self.logger:
                        self.logger.log_error("Error tomando screenshot", e)
                    success = False
                
                if success and screenshot_data:
                    # Mostrar preview con opciones
                    self._show_screenshot_preview(temp_path, screenshot_data)
                    self._update_status("1 conectado", "#2ecc71")
                else:
                    self._update_status("Error captura", "#e74c3c")
                    messagebox.showerror("❌ Error", "No se pudo tomar la captura de pantalla")
                    # Limpiar archivo temporal si existe
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
            except Exception as e:
                self._update_status("Error", "#e74c3c")
                if self.logger:
                    self.logger.log_error("Error en screenshot_thread", e)
                messagebox.showerror("❌ Error", f"Error al tomar captura: {str(e)}")
            finally:
                self._enable_all_buttons()
        
        threading.Thread(target=screenshot_thread, daemon=True).start()

    def _show_screenshot_preview(self, image_path, image_data):
        """Mostrar preview de la captura con bordes y mejor diseño"""
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        
        # Cargar imagen para determinar dimensiones
        try:
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            # Calcular tamaño adaptativo para preview
            max_preview_width = 500
            max_preview_height = 500
            
            # Mantener relación de aspecto
            ratio = min(max_preview_width / original_width, max_preview_height / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            # Redimensionar imagen para preview
            image.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Calcular tamaño de ventana basado en la imagen
            window_width = max(new_width + 60, 450)  # Más espacio para bordes
            window_height = new_height + 180  # Más espacio para botones y info
            
        except Exception as e:
            # En caso de error, usar tamaño por defecto
            window_width = 450
            window_height = 500
            photo = None
            if self.logger:
                self.logger.log_error("Error procesando imagen para preview", e)
        
        self.preview_window = tk.Toplevel(self.dialog)
        self.preview_window.title("Preview - Captura de Pantalla")
        self.preview_window.geometry(f"{window_width}x{window_height}")
        self.preview_window.configure(bg='#f0f0f0')
        self.preview_window.resizable(False, False)
        self.preview_window.attributes('-topmost', True)
        
        # Agregar bordes estilo ventana
        main_container = tk.Frame(self.preview_window, bg='#2c3e50', bd=2, relief='raised')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header con información del dispositivo
        header_frame = tk.Frame(main_container, bg='#34495e', height=40)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        header_frame.pack_propagate(False)
        
        # Información del dispositivo en el header
        device_text = f"📱 {self.device_info.get('model', 'DX8000')} | S/N: {self.device_info.get('serial', '228AKD863723')}"
        header_label = tk.Label(header_frame, text=device_text, 
                               font=("Segoe UI", 9, "bold"),
                               bg='#34495e', fg='white')
        header_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Frame para la imagen con borde
        image_container = tk.Frame(main_container, bg='#2c3e50', bd=1, relief='sunken')
        image_container.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Mostrar imagen
        if photo:
            image_label = tk.Label(image_container, image=photo, bg='#2c3e50')
            image_label.image = photo  # Mantener referencia
            image_label.pack(pady=10, padx=10)
        else:
            error_label = tk.Label(image_container, text="Error cargando imagen", 
                                 fg='white', bg='#2c3e50', font=("Segoe UI", 10))
            error_label.pack(pady=20)
        
        # Frame para botones con mejor distribución
        buttons_frame = tk.Frame(main_container, bg='#2c3e50')
        buttons_frame.pack(pady=15, padx=20, fill=tk.X)
        
        # Botón Copiar al Portapapeles
        copy_btn = tk.Button(
            buttons_frame,
            text="📋 Copiar al Portapapeles",
            command=lambda: self._copy_to_clipboard(image_data, image_path),
            font=("Segoe UI", 10, "bold"),
            bg='#3498db',
            fg='white',
            relief='raised',
            bd=2,
            padx=20,
            pady=10,
            cursor='hand2',
            width=18
        )
        copy_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Botón Guardar
        save_btn = tk.Button(
            buttons_frame,
            text="💾 Guardar Archivo",
            command=lambda: self._save_screenshot(image_path),
            font=("Segoe UI", 10, "bold"),
            bg='#2ecc71',
            fg='white',
            relief='raised',
            bd=2,
            padx=20,
            pady=10,
            cursor='hand2',
            width=18
        )
        save_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Botón Cancelar
        cancel_btn = tk.Button(
            buttons_frame,
            text="❌ Cancelar",
            command=lambda: self._cancel_screenshot(image_path),
            font=("Segoe UI", 10, "bold"),
            bg='#e74c3c',
            fg='white',
            relief='raised',
            bd=2,
            padx=20,
            pady=10,
            cursor='hand2',
            width=18
        )
        cancel_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Centrar ventana
        self.preview_window.update_idletasks()
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - self.preview_window.winfo_width()) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - self.preview_window.winfo_height()) // 2
        self.preview_window.geometry(f"+{x}+{y}")

    def _copy_to_clipboard(self, image_data, temp_path):
        """Copiar imagen al portapapeles"""
        try:
            import win32clipboard
            from PIL import Image
            import io
            
            # Convertir datos a imagen PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convertir a formato compatible con clipboard
            output = io.BytesIO()
            image.save(output, "BMP")
            data = output.getvalue()[14:]  # Remover header BMP
            output.close()
            
            # Copiar al portapapeles
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            # Cerrar ventana y limpiar
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
            
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            self._update_status("Copiado al portapapeles", "#2ecc71")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error copiando al portapapeles", e)
            messagebox.showerror("❌ Error", "No se pudo copiar al portapapeles")

    def _save_screenshot(self, temp_path):
        """Guardar screenshot sin diálogo de confirmación"""
        try:
            # Crear nombre por defecto
            default_name = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            default_path = os.path.join(os.path.expanduser("~"), "Desktop", default_name)
            
            # Mover archivo temporal a ubicación final
            import shutil
            shutil.move(temp_path, default_path)
            
            # Cerrar ventana
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
            
            self._update_status(f"Guardado: {default_name}", "#2ecc71")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error guardando screenshot", e)
            messagebox.showerror("❌ Error", f"No se pudo guardar: {str(e)}")

    def _cancel_screenshot(self, temp_path):
        """Cancelar y limpiar"""
        # Cerrar ventana
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
        
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        self._update_status("1 conectado", "#2ecc71")

    def _take_screenshot_alternative(self, file_path):
        """Método alternativo para tomar screenshot"""
        try:
            # Usar comando ADB directo
            import subprocess
            devices = self.scrcpy_manager.list_devices()
            if devices:
                serial = devices[0].get('serial', '228AKD863723')
                if serial:
                    # Ejecutar comando screencap via ADB
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
        """Botón unificado GRABAR/DETENER grabación"""
        if not self.is_running:
            messagebox.showwarning("Advertencia", "El mirror no está activo")
            return
        
        def recording_thread():
            try:
                if not self.scrcpy_manager.is_recording:
                    # INICIAR GRABACIÓN
                    self._disable_all_buttons()
                    self._update_status("Iniciando grabación...", "#f39c12")
                    
                    success = False
                    try:
                        success = self.scrcpy_manager.start_recording()
                    except Exception as e:
                        if self.logger:
                            self.logger.log_error("Error iniciando grabación", e)
                        success = False
                    
                    if success:
                        # Cambiar botón a modo "DETENER"
                        self.record_btn.config(text="⏹️ detener", bg='#c0392b')
                        self._update_status("Grabando...", "#e74c3c")
                        self.recording_start_time = time.time()
                        self._start_recording_timer()
                    else:
                        self._update_status("Error grabación", "#e74c3c")
                        messagebox.showerror("❌ Error", "No se pudo iniciar la grabación")
                    
                    self._enable_all_buttons()
                else:
                    # DETENER GRABACIÓN (sin cerrar scrcpy)
                    self._stop_recording_only()
                    
            except Exception as e:
                self._update_status("Error", "#e74c3c")
                self._enable_all_buttons()
                if self.logger:
                    self.logger.log_error("Error en recording_thread", e)
        
        threading.Thread(target=recording_thread, daemon=True).start()

    def _stop_recording_only(self):
        """Detener solo la grabación y abrir diálogo para guardar"""
        def stop_recording_thread():
            try:
                self._disable_all_buttons()
                self._update_status("Finalizando...", "#f39c12")
                
                video_path = None
                if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
                    video_path = self.scrcpy_manager.stop_recording()
                
                # Restaurar botón a modo "GRABAR"
                self.record_btn.config(text="🔴 grabar", bg='#e74c3c')
                self.recording_info.config(text="")
                
                if video_path and os.path.exists(video_path):
                    # Abrir diálogo para guardar el video
                    default_name = f"grabacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    final_path = filedialog.asksaveasfilename(
                        title="Guardar grabación de video",
                        defaultextension=".mp4",
                        filetypes=[("MP4 files", "*.mp4"), ("Todos los archivos", "*.*")],
                        initialfile=default_name
                    )
                    
                    if final_path:
                        # Mover el archivo a la ubicación seleccionada
                        import shutil
                        shutil.move(video_path, final_path)
                        self._update_status("Grabación guardada", "#2ecc71")
                    else:
                        # Si cancela, eliminar el archivo temporal
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
        """Timer de grabación - muestra minutos:segundos"""
        if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
            elapsed = int(time.time() - self.recording_start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.recording_info.config(text=f"Grabando: {minutes:02d}:{seconds:02d}")
            self.dialog.after(1000, self._start_recording_timer)

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
            # Detener grabación si está activa
            if hasattr(self.scrcpy_manager, 'is_recording') and self.scrcpy_manager.is_recording:
                self._stop_recording_only()
            
            if self.dialog:
                self.dialog.destroy()
                
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error al cerrar diálogo", e)
            if self.dialog:
                self.dialog.destroy()