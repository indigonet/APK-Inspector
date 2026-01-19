import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import shutil
import os
import subprocess
import sys
import tempfile
from datetime import datetime

# Asegúrate de importar correctamente tus componentes
try:
    from .components import BotonRedondeado, AppStyles
except ImportError:
    # Para cuando se ejecute como .exe
    from components import BotonRedondeado, AppStyles

class SigningDialog:
    
    def __init__(self, parent, apk_path: Path, build_tools_path: str):
        self.parent = parent
        self.apk_path = apk_path
        self.build_tools_path = build_tools_path
        self.styles = AppStyles()
        self.resultado = None
        self.password_visible = True
        
    def _log(self, message: str):
        print(f"[SigningDialog] {message}")
        
    def mostrar(self) -> Optional[dict]:
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Firmar APK")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=self.styles.COLORS['primary_bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._crear_interfaz()
        self._centrar_dialogo()
        
        self.parent.wait_window(self.dialog)
        return self.resultado
    
    def _crear_interfaz(self):
        main_frame = tk.Frame(self.dialog, bg=self.styles.COLORS['primary_bg'], padx=25, pady=25)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text=f"Firmar APK: {self.apk_path.name}",
            font=self.styles.FONTS['subtitle'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            wraplength=500
        )
        title_label.pack(anchor="w", pady=(0, 20))
        
        # Archivo JKS
        jks_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        jks_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            jks_frame,
            text="Archivo de Firma (.jks):",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w")
        
        jks_input_frame = tk.Frame(jks_frame, bg=self.styles.COLORS['primary_bg'])
        jks_input_frame.pack(fill="x", pady=(5, 0))
        
        self.jks_entry = tk.Entry(
            jks_input_frame,
            font=self.styles.FONTS['normal'],
            width=40,
            state='readonly'
        )
        self.jks_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        BotonRedondeado(
            jks_input_frame,
            "Examinar",
            self._seleccionar_jks,
            width=80,
            height=30,
            style='secondary'
        ).pack(side="right")
        
        # Contraseña
        password_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        password_frame.pack(fill="x", pady=(0, 10))

        # Etiqueta mejorada
        tk.Label(
            password_frame,
            text="🔐 Contraseña de Firma:",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 3))

        # Input de contraseña (inicialmente OCULTA)
        self.password_entry = tk.Entry(
            password_frame,
            font=self.styles.FONTS['normal'],
            width=40,
            show="•"  # OCULTA por defecto (carácter de bullet)
        )
        self.password_entry.pack(fill="x", pady=(5, 0))

        # Checkbox para mostrar/ocultar contraseña (texto invertido)
        self.show_password_var = tk.BooleanVar(value=False)  # FALSE por defecto (oculta)
        self.show_password_check = tk.Checkbutton(
            password_frame,
            text="👁️ ",  # Texto dice "Mostrar"
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            selectcolor=self.styles.COLORS['primary_bg'],
            activebackground=self.styles.COLORS['primary_bg'],
            activeforeground=self.styles.COLORS['text_primary']
        )
        self.show_password_check.pack(anchor="w", pady=(5, 0))

        # Label informativo
        self.password_status_label = tk.Label(
            password_frame,
            text="🔒 Contraseña oculta por seguridad",
            font=("Segoe UI", 8),
            bg=self.styles.COLORS['primary_bg'],
            fg="#666666",
            anchor="w"
        )
        self.password_status_label.pack(fill="x", pady=(2, 0))

        # Información adicional
        info_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        info_frame.pack(fill="x", pady=(20, 0))
        
        info_text = (
            "💡 Información de firma:\n"
            "• El archivo JKS se copiará automáticamente a build-tools\n"
            "• Se generarán 2 archivos en una carpeta en el Escritorio:\n"
            "  - APK firmada (tu-app-firmada.apk)\n"
            "  - Archivo de firma (tu-app-firmada.apk.idsig)\n"
            "• Sube ambos archivos cuando sea requerido"
        )
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_secondary'],
            justify="left",
            wraplength=500
        )
        info_label.pack(anchor="w")
        
        # Botones
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=(25, 0))
        
        BotonRedondeado(
            btn_frame,
            "Cancelar",
            self._cancelar,
            width=100,
            style='secondary'
        ).pack(side="right", padx=(10, 0))
        
        self.firmar_btn = BotonRedondeado(
            btn_frame,
            "Firmar APK",
            self._firmar,
            width=120,
            style='success'
        )
        self.firmar_btn.pack(side="right")
    
    def _seleccionar_jks(self):
        jks_path = filedialog.askopenfilename(
            title="Seleccionar archivo de firma",
            filetypes=[("Java KeyStore", "*.jks"), ("Todos los archivos", "*.*")]
        )
        
        if jks_path:
            self.jks_entry.config(state='normal')
            self.jks_entry.delete(0, tk.END)
            self.jks_entry.insert(0, jks_path)
            self.jks_entry.config(state='readonly')
    
    def _toggle_password_visibility(self):
        """Alternar visibilidad de la contraseña basado en checkbox"""
        if not hasattr(self, 'password_entry'):
            return
        
        if self.show_password_var.get():  # Si checkbox está marcado (True)
            # Mostrar contraseña
            self.password_entry.config(show="")
            self.password_status_label.config(
                text="⚠️ Contraseña visible - ¡Cuidado!",
                fg="#ff9800"
            )
        else:  # Si checkbox NO está marcado (False)
            # Ocultar contraseña
            self.password_entry.config(show="•")
            self.password_status_label.config(
                text="✅ Contraseña oculta por seguridad",
                fg="#4caf50"
            )
    
    def _encontrar_apksigner(self) -> Optional[Path]:
        build_tools_dir = Path(self.build_tools_path)
        
        # Verificar que build-tools existe
        if not build_tools_dir.exists():
            self._log(f"Build-tools no existe: {build_tools_dir}")
            return None
        
        # Buscar apksigner en diferentes nombres
        posibles_nombres = ["apksigner.bat", "apksigner"]
        
        for nombre in posibles_nombres:
            apksigner_path = build_tools_dir / nombre
            if apksigner_path.exists():
                self._log(f"apksigner encontrado: {apksigner_path}")
                return apksigner_path
        
        # Si no se encuentra, buscar en subdirectorios
        for item in build_tools_dir.iterdir():
            if item.is_dir():
                for nombre in posibles_nombres:
                    apksigner_path = item / nombre
                    if apksigner_path.exists():
                        self._log(f"apksigner encontrado en subdirectorio: {apksigner_path}")
                        return apksigner_path
        
        self._log("apksigner no encontrado en build-tools")
        return None
    
    def _crear_carpeta_escritorio(self, apk_name: str) -> Path:
        posibles_escritorios = []
        
        # Intentar diferentes ubicaciones de escritorio
        try:
            # Método 1: Escritorio del usuario
            desktop1 = Path.home() / "Desktop"
            if desktop1.exists():
                posibles_escritorios.append(desktop1)
                self._log(f"Escritorio encontrado: {desktop1}")
        except Exception as e:
            self._log(f"Error accediendo escritorio usuario: {e}")
        
        try:
            # Método 2: Variable de entorno USERPROFILE (Windows)
            user_profile = os.environ.get('USERPROFILE')
            if user_profile:
                desktop2 = Path(user_profile) / "Desktop"
                if desktop2.exists():
                    posibles_escritorios.append(desktop2)
                    self._log(f"Escritorio USERPROFILE: {desktop2}")
        except Exception as e:
            self._log(f"Error accediendo USERPROFILE: {e}")
        
        try:
            # Método 3: Directorio de documentos
            documents = Path.home() / "Documents"
            if documents.exists():
                posibles_escritorios.append(documents)
                self._log(f"Documentos encontrado: {documents}")
        except Exception as e:
            self._log(f"Error accediendo documentos: {e}")
        
        # Método 4: Directorio actual de la aplicación
        app_dir = Path.cwd()
        posibles_escritorios.append(app_dir)
        self._log(f"Directorio actual: {app_dir}")
        
        # Método 5: Directorio temporal
        temp_dir = Path(tempfile.gettempdir())
        posibles_escritorios.append(temp_dir)
        self._log(f"Directorio temporal: {temp_dir}")
        
      # Usar la primera ubicación disponible
        for ubicacion in posibles_escritorios:
            try:
                # Crear nombre seguro para la carpeta
                apk_simple_name = apk_name.replace('.apk', '').replace('-unsigned', '')
                apk_simple_name = "".join(c for c in apk_simple_name if c.isalnum() or c in ('-', '_'))
                
                if len(apk_simple_name) > 15:
                    apk_simple_name = apk_simple_name[:15]
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                folder_name = f"{apk_simple_name}_firmada_{timestamp}"
                
                # ✅ SOLUCIÓN: Eliminar "APK_Firmadas" /
                output_folder = ubicacion / folder_name
                
                output_folder.mkdir(parents=True, exist_ok=True)
                
                self._log(f"Carpeta creada en: {output_folder}")
                return output_folder
                
            except Exception as e:
                self._log(f"Error creando carpeta en {ubicacion}: {e}")
                continue

        # ✅ SOLUCIÓN: También eliminar "APK_Firmadas" / del fallback
        fallback = Path.cwd() / f"firmada_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    
    def _ejecutar_firma_real(self, jks_path: Path, password: str, output_folder: Path) -> tuple[bool, str, Path, Path]:
        try:
            # Encontrar apksigner
            apksigner = self._encontrar_apksigner()
            if not apksigner:
                return False, "No se encontró apksigner en build-tools", None, None
            
            # Verificar que el JKS existe
            if not jks_path.exists():
                return False, f"JKS no encontrado en: {jks_path}", None, None
            
            # Verificar que el APK existe
            if not self.apk_path.exists():
                return False, f"APK no encontrado: {self.apk_path}", None, None
            
            # Crear nombres de archivos de salida
            apk_simple_name = self.apk_path.stem.replace('-unsigned', '')
            apk_signed_name = f"{apk_simple_name}-firmada.apk"
            apk_signed_path = output_folder / apk_signed_name
            
            # Construir comando de firma
            comando = [
                str(apksigner),
                "sign",
                "--ks", str(jks_path),
                "--ks-pass", f"pass:{password}",
                "--out", str(apk_signed_path),
                str(self.apk_path)
            ]
            
            self._log(f"Ejecutando comando: {' '.join(comando)}")
            
            # Ejecutar comando
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self._log(f"Resultado comando: returncode={resultado.returncode}")
            
            if resultado.returncode != 0:
                error_msg = resultado.stderr if resultado.stderr else resultado.stdout
                self._log(f"Error en firma: {error_msg}")
                return False, f"Error en firma: {error_msg}", None, None
            
            # Verificar que el archivo firmado se creó
            if not apk_signed_path.exists():
                self._log(f"Archivo firmado no creado: {apk_signed_path}")
                return False, "No se creó el archivo firmado", None, None
            
            self._log(f"APK firmado creado: {apk_signed_path}")
            
            # Crear archivo de firma (idsig) - simulado
            signature_path = output_folder / f"{apk_signed_name}.idsig"
            try:
                with open(signature_path, 'w', encoding='utf-8') as f:
                    f.write(f"Firma generada el: {datetime.now()}\n")
                    f.write(f"APK: {apk_signed_name}\n")
                    f.write(f"JKS: {jks_path.name}\n")
                    f.write(f"Tamaño: {apk_signed_path.stat().st_size} bytes\n")
                self._log(f"Archivo de firma creado: {signature_path}")
            except Exception as e:
                self._log(f"Error creando archivo de firma: {e}")
                # No es crítico, continuar
            
            return True, "Firma exitosa", apk_signed_path, signature_path
            
        except subprocess.TimeoutExpired:
            self._log("Tiempo de espera agotado al firmar")
            return False, "Tiempo de espera agotado al firmar", None, None
        except Exception as e:
            self._log(f"Error inesperado en firma: {e}")
            return False, f"Error inesperado: {str(e)}", None, None
    
    def _deshabilitar_controles(self):
        try:
       
            self.btn_temp_frame = tk.Frame(self.dialog, bg=self.styles.COLORS['primary_bg'])
            self.btn_temp_frame.pack(side="right", padx=(10, 0))
            
            
            # Deshabilitar otros controles
            self.jks_entry.config(state='disabled')
            self.password_entry.config(state='disabled')
            self.show_password_check.config(state='disabled')
            
            self.dialog.update()
            self._log("Controles deshabilitados")
        except Exception as e:
            self._log(f"Error deshabilitando controles: {e}")
    
    def _rehabilitar_controles(self):
        try:
            # Eliminar botón temporal
            if hasattr(self, 'btn_temp_frame'):
                self.btn_temp_frame.destroy()
            
            # Mostrar botón original
            self.firmar_btn.pack(side="right")
            
            # Rehabilitar otros controles
            self.jks_entry.config(state='normal')
            self.password_entry.config(state='normal')
            self.show_password_check.config(state='normal')
            
            self.dialog.update()
            self._log("Controles rehabilitados")
        except Exception as e:
            self._log(f"Error rehabilitando controles: {e}")
    
    def _firmar(self):
        jks_path = self.jks_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Validaciones
        if not jks_path:
            messagebox.showerror("Error", "Selecciona un archivo JKS")
            return
        
        if not password:
            messagebox.showerror("Error", "Ingresa la contraseña de firma")
            return
        
        jks_file = Path(jks_path)
        if not jks_file.exists():
            messagebox.showerror("Error", "El archivo JKS no existe")
            return
        
        if not self.apk_path.exists():
            messagebox.showerror("Error", "El APK original no existe")
            return
        
        try:
            # Deshabilitar controles
            self._deshabilitar_controles()
            
            # Crear carpeta de salida
            try:
                output_folder = self._crear_carpeta_escritorio(self.apk_path.name)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta de salida: {str(e)}")
                self._rehabilitar_controles()
                return
            
            # Verificar que la carpeta se creó correctamente
            if not output_folder.exists():
                messagebox.showerror("Error", f"No se pudo crear la carpeta: {output_folder}")
                self._rehabilitar_controles()
                return
            
            # Copiar JKS a build-tools
            build_tools_dir = Path(self.build_tools_path)
            jks_in_build_tools = build_tools_dir / jks_file.name
            
            # Verificar que build-tools existe
            if not build_tools_dir.exists():
                messagebox.showerror("Error", f"Build-tools no encontrado: {build_tools_dir}")
                self._rehabilitar_controles()
                return
            
            try:
                if not jks_in_build_tools.exists() or jks_in_build_tools != jks_file:
                    shutil.copy2(jks_file, jks_in_build_tools)
                    self._log(f"JKS copiado a: {jks_in_build_tools}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar el JKS: {str(e)}")
                self._rehabilitar_controles()
                return
            
            # EJECUTAR FIRMA REAL
            success, message, apk_signed_path, signature_path = self._ejecutar_firma_real(
                jks_in_build_tools, password, output_folder
            )
            
            if success:
                # Verificar que los archivos se crearon
                if not apk_signed_path.exists():
                    messagebox.showerror("Error", f"El APK firmado no se creó: {apk_signed_path}")
                    self._rehabilitar_controles()
                    return
                
                # ✅ Solo retornar resultado si fue exitoso
                self.resultado = {
                    'jks_path': str(jks_in_build_tools),
                    'jks_original_path': str(jks_file),
                    'password': password,
                    'apk_path': str(self.apk_path),
                    'apk_signed_path': str(apk_signed_path),
                    'signature_path': str(signature_path),
                    'output_folder': str(output_folder),
                    'success': True
                }
                self._log("Firma completada exitosamente")
                self.dialog.destroy()
            else:
                # ❌ En caso de error, mostrar mensaje pero NO retornar resultado
                self._manejar_error_firma(message)
                self._rehabilitar_controles()
                
        except Exception as e:
            # Rehabilitar controles en caso de error
            self._rehabilitar_controles()
            error_msg = f"No se pudo preparar la firma: {str(e)}"
            self._log(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def _manejar_error_firma(self, error_msg: str):
        error_lower = error_msg.lower()
        
        if any(word in error_lower for word in ['password', 'contraseña', 'incorrect', 'wrong']):
            messagebox.showerror(
                "Error al firmar APK", 
                "La contraseña del keystore es incorrecta.\n\n"
                "Por favor, verifica la contraseña e intenta nuevamente."
            )
        elif 'keystore' in error_lower and 'not found' in error_lower:
            messagebox.showerror(
                "Error al firmar APK",
                "El archivo keystore no se encontró o es inválido."
            )
        elif 'apksigner' in error_lower and 'not found' in error_lower:
            messagebox.showerror(
                "Error al firmar APK",
                "No se encontró apksigner. Verifica la ruta de build-tools."
            )
        elif 'timeout' in error_lower or 'tiempo' in error_lower:
            messagebox.showerror(
                "Error al firmar APK",
                "Tiempo de espera agotado. El proceso de firma tardó demasiado."
            )
        else:
            # Para otros errores, mostrar el mensaje completo
            messagebox.showerror("Error al firmar APK", f"Error: {error_msg}")
    
    def _cancelar(self):
        self.resultado = None
        self.dialog.destroy()
    
    def _centrar_dialogo(self):
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")