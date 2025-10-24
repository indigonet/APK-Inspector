import tkinter as tk
from tkinter import messagebox, scrolledtext
from pathlib import Path
import threading
import subprocess
import os
from ui.components import BotonRedondeado
from tkinter import ttk

class APKManager:
    """Clase para gestionar instalación/desinstalación de APKs"""
    
    def __init__(self, services, styles, logger, adb_manager):
        self.services = services
        self.styles = styles
        self.logger = logger
        self.adb_manager = adb_manager
    
    def mostrar_opciones_gestion(self, parent, apk_path: Path, apk_name: str, current_analysis: dict, btn_gestionar=None):
        """Mostrar menú de opciones de gestión"""
        if not apk_path:
            messagebox.showerror("Error", "No hay APK seleccionado para gestionar")
            return

        menu = tk.Menu(parent, tearoff=0, font=("Segoe UI", 9))

        package_name = ""
        app_name = "esta APK"
        if current_analysis and 'parsed_info' in current_analysis:
            package_name = current_analysis['parsed_info'].get('package', '')
            app_name_detected = current_analysis['parsed_info'].get('app_label', '')
            if app_name_detected:
                app_name = app_name_detected

        config = self.services._get_tools_config()
        platform_tools = config.get("platform_tools", "")

        # Agregar opción de diagnóstico
        menu.add_command(
            label="Instalar APK en dispositivo",
            command=lambda: self._ejecutar_instalacion(parent, platform_tools, apk_path, apk_name)
        )

        # VERIFICAR SI EL PACKAGE ESTÁ INSTALADO ANTES DE MOSTRAR LA OPCIÓN
        if package_name:
            # Verificar si la aplicación está instalada en el dispositivo
            esta_instalada = self._verificar_aplicacion_instalada(platform_tools, package_name)
            
            if esta_instalada:
                menu.add_command(
                    label=f"Desinstalar {app_name}",
                    command=lambda: self._ejecutar_desinstalacion(parent, platform_tools, package_name, app_name)
                )
            else:
                # Opción deshabilitada si no está instalada
                menu.add_command(
                    label=f"Desinstalar {app_name} (no instalada)",
                    state="disabled"
                )

        menu.add_command(
            label="Desinstalar paquete personalizado...",
            command=lambda: self._solicitar_paquete_desinstalar(parent, platform_tools, current_analysis)
        )

        menu.add_separator()

        menu.add_command(
            label="Ver dispositivos conectados",
            command=lambda: self._ver_dispositivos_conectados(parent, platform_tools)
        )

        menu.add_separator()
        menu.add_command(
            label="🔧 Diagnóstico ADB",
            command=lambda: self._ejecutar_diagnostico(parent, platform_tools)
        )

        try:
            if btn_gestionar:
                x = btn_gestionar.winfo_rootx()
                y = btn_gestionar.winfo_rooty() + btn_gestionar.winfo_height()
            else:
                x = parent.winfo_pointerx()
                y = parent.winfo_pointery()
            
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _verificar_aplicacion_instalada(self, platform_tools: str, package_name: str) -> bool:
        """Verificar si una aplicación está instalada en el dispositivo conectado"""
        try:
            if not platform_tools:
                return False

            platform_path = Path(platform_tools)
            adb_path = platform_path / "adb.exe"
            if not adb_path.exists():
                adb_path = platform_path / "adb"
            if not adb_path.exists():
                return False

            # Verificar dispositivos conectados
            success, devices = self.services.get_connected_devices(platform_tools)
            if not success or not devices:
                return False

            dispositivo = devices[0] if devices else None

            # Comando para verificar si el paquete está instalado
            comando = [str(adb_path)]
            if dispositivo and dispositivo != "unknown":
                comando.extend(["-s", dispositivo])
            
            comando.extend(["shell", "pm", "list", "packages", package_name])
            
            result = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(platform_path)
            )
            
            # Si encuentra el paquete en la lista, está instalado
            if result.returncode == 0 and package_name in result.stdout:
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.log_error(f"Error verificando aplicación instalada: {e}")
            return False

    def _ejecutar_instalacion(self, parent, platform_tools: str, apk_path: Path, apk_name: str):
        """Ejecutar instalación de APK"""
        if not platform_tools:
            messagebox.showerror("Error", "Platform-tools no configurado. Ve a Configurar Herramientas.")
            return

        # Primero verificar que ADB existe
        platform_path = Path(platform_tools)
        adb_path = platform_path / "adb.exe"
        if not adb_path.exists():
            adb_path = platform_path / "adb"
        if not adb_path.exists():
            messagebox.showerror("Error", f"ADB no encontrado en: {platform_tools}")
            return

        success, devices = self.services.get_connected_devices(platform_tools)

        if not success:
            messagebox.showerror("Error", f"No se pudo conectar con ADB: {devices}")
            return

        if not devices:
            messagebox.showerror("Error",
                               "No hay dispositivos Android conectados.\n\n"
                               "Asegúrate de:\n"
                               "1. Tener USB debugging activado\n"
                               "2. Aceptar la conexión ADB en el dispositivo\n"
                               "3. Tener los drivers ADB instalados")
            return

        dispositivo = devices[0] if devices else None
        dispositivo_info = f"Dispositivo: {dispositivo}"

        resultado = messagebox.askyesno(
            "Instalar APK",
            f"¿Instalar {apk_name}?\n\n{dispositivo_info}"
        )

        if resultado:
            progress_dialog = self._mostrar_dialogo_progreso(parent, "Instalando APK...")

            def instalar_thread():
                try:
                    # EJECUTAR DIRECTAMENTE PARA DEBUG
                    success, output = self._ejecutar_instalacion_directa(platform_tools, apk_path, dispositivo)
                    parent.after(0, lambda: self._procesar_resultado_instalacion(
                        progress_dialog, success, output, dispositivo_info, apk_name))
                except Exception as e:
                    parent.after(0, lambda: self._procesar_error_instalacion(
                        progress_dialog, str(e), dispositivo_info))

            threading.Thread(target=instalar_thread, daemon=True).start()

    def _ejecutar_instalacion_directa(self, platform_tools: str, apk_path: Path, dispositivo: str = None):
        """Ejecutar instalación directamente para evitar problemas del servicio"""
        try:
            platform_path = Path(platform_tools)
            adb_path = platform_path / "adb.exe"
            if not adb_path.exists():
                adb_path = platform_path / "adb"

            # Construir comando ADB install -r
            comando = [str(adb_path)]
            
            # Especificar dispositivo si hay uno
            if dispositivo and dispositivo != "unknown":
                comando.extend(["-s", dispositivo])
            
            # Comando de instalación con -r (reemplazar)
            comando.extend(["install", "-r", str(apk_path)])
            
            self.logger.log_info(f"Ejecutando comando ADB: {' '.join(comando)}")
            
            # Ejecutar desde el directorio de platform-tools
            result = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=60,  # Timeout más largo para instalación
                cwd=str(platform_path)
            )
            
            self.logger.log_info(f"Resultado ADB instalación - stdout: {result.stdout}, stderr: {result.stderr}, returncode: {result.returncode}")
            
            if result.returncode == 0:
                if "Success" in result.stdout or "success" in result.stdout.lower():
                    return True, f"✅ Instalación exitosa:\n{result.stdout}"
                else:
                    return True, f"ℹ️ Comando completado:\n{result.stdout}"
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return False, f"❌ Error ADB (código {result.returncode}):\n{error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "⏰ Timeout: La instalación tardó demasiado"
        except Exception as e:
            return False, f"💥 Error ejecutando ADB: {str(e)}"

    def _ejecutar_diagnostico(self, parent, platform_tools: str):
        """Ejecutar diagnóstico de ADB"""
        diagnostico = []
        
        # 1. Verificar si platform_tools está configurado
        if not platform_tools:
            diagnostico.append("❌ Platform-tools no configurado")
            self._mostrar_diagnostico(parent, diagnostico)
            return
        
        diagnostico.append(f"✅ Platform-tools configurado: {platform_tools}")
        
        # 2. Verificar si la ruta existe
        platform_path = Path(platform_tools)
        if not platform_path.exists():
            diagnostico.append(f"❌ La ruta no existe: {platform_tools}")
            self._mostrar_diagnostico(parent, diagnostico)
            return
        diagnostico.append("✅ La ruta existe")
        
        # 3. Buscar adb.exe
        adb_path = platform_path / "adb.exe"
        if not adb_path.exists():
            adb_path = platform_path / "adb"
            
        if not adb_path.exists():
            diagnostico.append(f"❌ ADB no encontrado en: {platform_tools}")
            self._mostrar_diagnostico(parent, diagnostico)
            return
            
        diagnostico.append(f"✅ ADB encontrado: {adb_path}")
        
        # 4. Verificar que ADB funciona
        try:
            result = subprocess.run(
                [str(adb_path), "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[0] if result.stdout else "Versión no disponible"
                diagnostico.append(f"✅ ADB funciona: {version_info}")
            else:
                diagnostico.append(f"❌ ADB no funciona: {result.stderr}")
        except Exception as e:
            diagnostico.append(f"❌ Error ejecutando ADB: {str(e)}")
        
        # 5. Verificar dispositivos
        try:
            result = subprocess.run(
                [str(adb_path), "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    devices = [line for line in lines[1:] if line.strip() and 'device' in line]
                    if devices:
                        diagnostico.append(f"✅ Dispositivos conectados: {len(devices)}")
                        for device in devices:
                            diagnostico.append(f"   📱 {device.split()[0]}")
                    else:
                        diagnostico.append("❌ No hay dispositivos conectados")
                else:
                    diagnostico.append("❌ No hay dispositivos conectados")
            else:
                diagnostico.append(f"❌ Error verificando dispositivos: {result.stderr}")
        except Exception as e:
            diagnostico.append(f"❌ Error verificando dispositivos: {str(e)}")
        
        self._mostrar_diagnostico(parent, diagnostico)

    def _mostrar_diagnostico(self, parent, diagnostico: list):
        """Mostrar resultados del diagnóstico"""
        dialog = tk.Toplevel(parent)
        dialog.title("Diagnóstico ADB")
        dialog.geometry("600x400")
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text="Diagnóstico ADB",
            font=("Segoe UI", 12, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 15))

        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)

        text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap="word",
            font=("Consolas", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=10,
            pady=10
        )
        text_widget.pack(fill="both", expand=True)

        for linea in diagnostico:
            text_widget.insert(tk.END, linea + "\n")

        text_widget.config(state='disabled')

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=(15, 0))

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=100, style='primary').pack(side="right")

        self._centrar_dialogo(dialog, parent)

    def _ejecutar_desinstalacion(self, parent, platform_tools: str, package_name: str, app_name: str):
        """Ejecutar desinstalación de aplicación"""
        if not platform_tools:
            messagebox.showerror("Error", "Platform-tools no configurado. Ve a Configurar Herramientas.")
            return

        # Primero verificar que ADB existe
        platform_path = Path(platform_tools)
        adb_path = platform_path / "adb.exe"
        if not adb_path.exists():
            adb_path = platform_path / "adb"
        if not adb_path.exists():
            messagebox.showerror("Error", f"ADB no encontrado en: {platform_tools}")
            return

        success, devices = self.services.get_connected_devices(platform_tools)

        if not success:
            messagebox.showerror("Error", f"No se pudo conectar con ADB: {devices}")
            return

        if not devices:
            messagebox.showerror("Error", "No hay dispositivos Android conectados")
            return

        dispositivo = devices[0] if devices else None

        resultado = messagebox.askyesno(
            "Desinstalar Aplicación",
            f"¿Estás seguro de que quieres desinstalar {app_name}?\n\n"
            f"Paquete: {package_name}\n"
            f"Dispositivo: {dispositivo}\n\n"
            f"Esta acción no se puede deshacer."
        )

        if resultado:
            progress_dialog = self._mostrar_dialogo_progreso(parent, "Desinstalando aplicación...")

            def desinstalar_thread():
                try:
                    # EJECUTAR DIRECTAMENTE PARA DEBUG
                    success, output = self._ejecutar_desinstalacion_directa(platform_tools, package_name, dispositivo)
                    parent.after(0, lambda: self._procesar_resultado_desinstalacion(
                        progress_dialog, success, output, app_name, package_name))
                except Exception as e:
                    parent.after(0, lambda: self._procesar_error_desinstalacion(
                        progress_dialog, str(e), app_name))

            threading.Thread(target=desinstalar_thread, daemon=True).start()

    def _ejecutar_desinstalacion_directa(self, platform_tools: str, package_name: str, dispositivo: str = None):
        """Ejecutar desinstalación directamente para evitar problemas del servicio"""
        try:
            platform_path = Path(platform_tools)
            adb_path = platform_path / "adb.exe"
            if not adb_path.exists():
                adb_path = platform_path / "adb"

            # Construir comando
            comando = [str(adb_path)]
            
            # Especificar dispositivo si hay uno
            if dispositivo and dispositivo != "unknown":
                comando.extend(["-s", dispositivo])
            
            # Comando de desinstalación
            comando.extend(["uninstall", package_name])
            
            self.logger.log_info(f"Ejecutando comando ADB: {' '.join(comando)}")
            
            # Ejecutar desde el directorio de platform-tools
            result = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(platform_path)
            )
            
            self.logger.log_info(f"Resultado ADB - stdout: {result.stdout}, stderr: {result.stderr}, returncode: {result.returncode}")
            
            if result.returncode == 0:
                if "Success" in result.stdout or "success" in result.stdout.lower():
                    return True, f"✅ Desinstalación exitosa:\n{result.stdout}"
                else:
                    return True, f"ℹ️ Comando completado:\n{result.stdout}"
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return False, f"❌ Error ADB (código {result.returncode}):\n{error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "⏰ Timeout: El comando ADB tardó demasiado"
        except Exception as e:
            return False, f"💥 Error ejecutando ADB: {str(e)}"

    def _procesar_resultado_instalacion(self, progress_dialog, success: bool, output: str, dispositivo_info: str, apk_name: str):
        """Procesar resultado de la instalación"""
        progress_dialog.destroy()
        
        if success:
            self._mostrar_resultado_exitoso(progress_dialog.master, output, dispositivo_info)
            self.logger.log_info(f"APK instalado: {apk_name}")
        else:
            # Mostrar error detallado
            self._mostrar_error_detallado_instalacion(progress_dialog.master, output, apk_name)
            self.logger.log_error(f"Error instalando {apk_name}: {output}")

    def _mostrar_error_detallado_instalacion(self, parent, mensaje_error: str, apk_name: str):
        """Mostrar error detallado de instalación"""
        dialog = tk.Toplevel(parent)
        dialog.title(f"Error Instalando {apk_name}")
        dialog.geometry("650x450")
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text=f"❌ Error al Instalar {apk_name}",
            font=("Segoe UI", 11, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['error'],
            pady=10
        ).pack()

        # Soluciones
        soluciones_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        soluciones_frame.pack(fill="x", pady=10)
        
        tk.Label(
            soluciones_frame,
            text="Posibles soluciones:",
            font=("Segoe UI", 9, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w")
        
        soluciones_text = tk.Text(soluciones_frame, wrap="word", font=("Segoe UI", 9), height=4,
                                bg=self.styles.COLORS['secondary_bg'], fg=self.styles.COLORS['text_primary'],
                                padx=10, pady=5)
        soluciones_text.pack(fill="x", pady=5)
        soluciones_text.insert("1.0", 
            "• Verifica que el APK sea compatible con el dispositivo\n"
            "• Asegúrate de tener suficiente espacio en el dispositivo\n"
            "• La aplicación podría estar ya instalada con diferente firma\n"
            "• Prueba ejecutar manualmente: adb install -r \"archivo.apk\"")
        soluciones_text.config(state="disabled")

        # Error detallado
        error_frame = tk.Frame(main_frame)
        error_frame.pack(fill="both", expand=True)

        error_text = scrolledtext.ScrolledText(error_frame, wrap="word", font=("Consolas", 8),
                                             bg=self.styles.COLORS['secondary_bg'],
                                             fg=self.styles.COLORS['text_primary'],
                                             height=12, padx=10, pady=10)
        error_text.pack(fill="both", expand=True)
        error_text.insert("1.0", mensaje_error)
        error_text.config(state='disabled')

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=10)

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=100, style='primary').pack(side="right")

        self._centrar_dialogo(dialog, parent)

    def _procesar_resultado_desinstalacion(self, progress_dialog, success: bool, output: str, app_name: str, package_name: str):
        """Procesar resultado de la desinstalación"""
        progress_dialog.destroy()
        
        if success:
            messagebox.showinfo("Éxito", f"{app_name} desinstalada correctamente:\n{output}")
            self.logger.log_info(f"Aplicación desinstalada: {package_name}")
        else:
            # Mostrar error detallado
            self._mostrar_error_detallado_desinstalacion(progress_dialog.master, output, app_name, package_name)
            self.logger.log_error(f"Error desinstalando {package_name}: {output}")

    def _mostrar_error_detallado_desinstalacion(self, parent, mensaje_error: str, app_name: str, package_name: str):
        """Mostrar error detallado de desinstalación"""
        dialog = tk.Toplevel(parent)
        dialog.title(f"Error Desinstalando {app_name}")
        dialog.geometry("650x450")
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text=f"❌ Error al Desinstalar {app_name}",
            font=("Segoe UI", 11, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['error'],
            pady=10
        ).pack()

        # Información del paquete
        info_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        info_frame.pack(fill="x", pady=10)
        
        tk.Label(
            info_frame,
            text=f"Paquete: {package_name}",
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_secondary']
        ).pack(anchor="w")

        # Soluciones
        soluciones_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        soluciones_frame.pack(fill="x", pady=10)
        
        tk.Label(
            soluciones_frame,
            text="Posibles soluciones:",
            font=("Segoe UI", 9, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w")
        
        soluciones_text = tk.Text(soluciones_frame, wrap="word", font=("Segoe UI", 9), height=4,
                                bg=self.styles.COLORS['secondary_bg'], fg=self.styles.COLORS['text_primary'],
                                padx=10, pady=5)
        soluciones_text.pack(fill="x", pady=5)
        soluciones_text.insert("1.0", 
            "• Verifica que la aplicación esté instalada en el dispositivo\n"
            "• Asegúrate de tener permisos de administrador\n"
            "• El paquete podría estar protegido o ser del sistema\n"
            "• Prueba ejecutar manualmente: adb uninstall " + package_name)
        soluciones_text.config(state="disabled")

        # Error detallado
        error_frame = tk.Frame(main_frame)
        error_frame.pack(fill="both", expand=True)

        error_text = scrolledtext.ScrolledText(error_frame, wrap="word", font=("Consolas", 8),
                                             bg=self.styles.COLORS['secondary_bg'],
                                             fg=self.styles.COLORS['text_primary'],
                                             height=12, padx=10, pady=10)
        error_text.pack(fill="both", expand=True)
        error_text.insert("1.0", mensaje_error)
        error_text.config(state='disabled')

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=10)

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=100, style='primary').pack(side="right")

        self._centrar_dialogo(dialog, parent)

    def _solicitar_paquete_desinstalar(self, parent, platform_tools: str, current_analysis: dict):
        """Solicitar package name para desinstalar"""
        dialog = tk.Toplevel(parent)
        dialog.title("Desinstalar Paquete Personalizado")
        dialog.geometry("450x220")  
        dialog.resizable(False, False)
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        self._centrar_dialogo(dialog, parent)

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text="Ingresa el nombre del paquete a desinstalar:",
            font=("Segoe UI", 10),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        # Frame para el entry con placeholder
        entry_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        entry_frame.pack(fill="x", pady=(0, 15))

        package_entry = tk.Entry(entry_frame, font=("Segoe UI", 10), width=40)
        package_entry.pack(fill="x")
        package_entry.focus_set()

        # ✅ SOLO PLACEHOLDER - SIN REEMPLAZAR CON EL PACKAGE ACTUAL
        placeholder_text = "Ejemplo: com.example.miapp"
        package_entry.insert(0, placeholder_text)
        package_entry.config(fg=self.styles.COLORS['text_secondary'])  # Color gris para placeholder

        def on_entry_click(event):
            """Manejar clic en el entry"""
            if package_entry.get() == placeholder_text:
                package_entry.delete(0, tk.END)
                package_entry.config(fg=self.styles.COLORS['text_primary'])  # Color normal

        def on_focusout(event):
            """Manejar pérdida de foco"""
            if package_entry.get() == '':
                package_entry.insert(0, placeholder_text)
                package_entry.config(fg=self.styles.COLORS['text_secondary'])

        # Vincular eventos
        package_entry.bind('<FocusIn>', on_entry_click)
        package_entry.bind('<FocusOut>', on_focusout)

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x")

        BotonRedondeado(btn_frame, "Cancelar", dialog.destroy, width=100,
                    style='secondary').pack(side="right", padx=(10, 0))
        BotonRedondeado(btn_frame, "Desinstalar",
                    lambda: self._confirmar_desinstalacion_personalizada(
                        dialog, package_entry.get().strip(), platform_tools, parent, placeholder_text),
                    width=100, style='danger').pack(side="right")

    def _confirmar_desinstalacion_personalizada(self, dialog, package_name: str, platform_tools: str, parent, placeholder_text: str):
        """Confirmar desinstalación personalizada"""
        # Verificar que no sea el placeholder o esté vacío
        if not package_name or package_name == placeholder_text:
            messagebox.showwarning("Advertencia", "Ingresa un nombre de paquete válido")
            return
        
        # Verificar formato básico de package name
        if not self._es_package_name_valido(package_name):
            resultado = messagebox.askyesno(
                "Confirmar Package Name",
                f"El package name '{package_name}' no tiene el formato típico (com.ejemplo.app).\n\n"
                f"¿Estás seguro de que quieres desinstalar este paquete?"
            )
            if not resultado:
                return

        dialog.destroy()
        self._ejecutar_desinstalacion(parent, platform_tools, package_name, "la aplicación personalizada")

    def _es_package_name_valido(self, package_name: str) -> bool:
        """Verificar si el package name tiene un formato válido"""
        # Formato típico: com.ejemplo.app, org.example.app, etc.
        import re
        pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
        return bool(re.match(pattern, package_name))

    def _ver_dispositivos_conectados(self, parent, platform_tools: str):
        """Mostrar información de dispositivos conectados"""
        if not platform_tools:
            messagebox.showerror("Error", "Platform-tools no configurado")
            return

        success, devices = self.services.get_connected_devices(platform_tools)

        if not success:
            messagebox.showerror("Error", f"No se pudieron obtener dispositivos: {devices}")
            return

        if not devices:
            messagebox.showinfo("Dispositivos", "No hay dispositivos Android conectados")
            return

        dialog = tk.Toplevel(parent)
        dialog.title("Dispositivos Conectados")
        dialog.geometry("500x300")
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.transient(parent)
        dialog.grab_set()

        self._centrar_dialogo(dialog, parent)

        main_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text="Dispositivos Android Conectados:",
            font=("Segoe UI", 11, "bold"),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            justify="left"
        ).pack(anchor="w", pady=(0, 15))

        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)

        text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap="word",
            font=("Consolas", 9),
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=10,
            pady=10
        )
        text_widget.pack(fill="both", expand=True)

        for i, dispositivo in enumerate(devices, 1):
            info = self.adb_manager.obtener_info_dispositivo(platform_tools, dispositivo)
            text_widget.insert(tk.END, f"Dispositivo {i}:\n")
            text_widget.insert(tk.END, f"  ID: {dispositivo}\n")
            for key, value in info.items():
                text_widget.insert(tk.END, f"  {key.capitalize()}: {value}\n")
            text_widget.insert(tk.END, "\n")

        text_widget.config(state='disabled')

        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=(15, 0))

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=100, style='primary').pack(side="right")

    def _mostrar_dialogo_progreso(self, parent, mensaje: str):
        """Mostrar diálogo de progreso"""
        dialog = tk.Toplevel(parent)
        dialog.title("Procesando")
        dialog.geometry("280x100")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])

        self._centrar_dialogo(dialog, parent)

        tk.Label(dialog, text=mensaje, font=("Segoe UI", 9), bg=self.styles.COLORS['primary_bg'],
                fg=self.styles.COLORS['text_primary'], pady=15).pack()

        progress = ttk.Progressbar(dialog, mode='indeterminate', length=180)
        progress.pack(pady=8)
        progress.start(10)

        return dialog

    def _procesar_error_instalacion(self, progress_dialog, error: str, dispositivo_info: str):
        """Procesar error durante la instalación"""
        progress_dialog.destroy()
        self._mostrar_resultado_error(progress_dialog.master, error, dispositivo_info)
        self.logger.log_error(f"Excepción instalando APK: {error}")

    def _procesar_error_desinstalacion(self, progress_dialog, error: str, app_name: str):
        """Procesar error durante la desinstalación"""
        progress_dialog.destroy()
        messagebox.showerror("Error", f"Error durante la desinstalación de {app_name}: {str(error)}")
        self.logger.log_error(f"Excepción desinstalando: {error}")

    def _mostrar_resultado_exitoso(self, parent, output: str, dispositivo_info: str):
        """Mostrar resultado exitoso de instalación"""
        dialog = tk.Toplevel(parent)
        dialog.title("Resultado de Instalación")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.geometry("450x300")

        tk.Label(dialog, text="✅ APK Instalado Correctamente", font=("Segoe UI", 10, "bold"),
                bg=self.styles.COLORS['primary_bg'], fg=self.styles.COLORS['success'], pady=12).pack()
        tk.Label(dialog, text=dispositivo_info, font=("Segoe UI", 9),
                bg=self.styles.COLORS['primary_bg'], fg=self.styles.COLORS['text_primary'], pady=3).pack()

        output_frame = tk.Frame(dialog)
        output_frame.pack(fill="both", expand=True, padx=15, pady=8)

        output_text = scrolledtext.ScrolledText(output_frame, wrap="word", font=("Consolas", 8),
                                               bg=self.styles.COLORS['secondary_bg'],
                                               fg=self.styles.COLORS['text_primary'],
                                               height=8, padx=8, pady=8)
        output_text.pack(fill="both", expand=True)
        output_text.insert(1.0, output)
        output_text.config(state='disabled')

        btn_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=8)

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=80, height=30, style='primary').pack()

        self._centrar_dialogo(dialog, parent)

    def _mostrar_resultado_error(self, parent, output: str, dispositivo_info: str):
        """Mostrar resultado de error en instalación"""
        dialog = tk.Toplevel(parent)
        dialog.title("Error de Instalación")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg=self.styles.COLORS['primary_bg'])
        dialog.geometry("550x350")

        tk.Label(dialog, text="❌ Error al Instalar APK", font=("Segoe UI", 10, "bold"),
                bg=self.styles.COLORS['primary_bg'], fg=self.styles.COLORS['error'], pady=12).pack()

        output_frame = tk.Frame(dialog)
        output_frame.pack(fill="both", expand=True, padx=15, pady=8)

        output_text = scrolledtext.ScrolledText(output_frame, wrap="word", font=("Consolas", 8),
                                               bg=self.styles.COLORS['secondary_bg'],
                                               fg=self.styles.COLORS['text_primary'],
                                               height=12, padx=8, pady=8)
        output_text.pack(fill="both", expand=True)
        output_text.insert(1.0, output)
        output_text.config(state='disabled')

        btn_frame = tk.Frame(dialog, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=8)

        BotonRedondeado(btn_frame, "Cerrar", dialog.destroy,
                       width=80, height=30, style='primary').pack()

        self._centrar_dialogo(dialog, parent)

    def _centrar_dialogo(self, dialog, parent):
        """Centrar diálogo en la pantalla"""
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")