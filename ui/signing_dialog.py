import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import shutil
import os
from datetime import datetime
from .components import BotonRedondeado, AppStyles

class SigningDialog:
    """Diálogo para firmar APK"""
    
    def __init__(self, parent, apk_path: Path, build_tools_path: str):
        self.parent = parent
        self.apk_path = apk_path
        self.build_tools_path = build_tools_path
        self.styles = AppStyles()
        self.resultado = None
        self.password_visible = True  # Por defecto visible
        
    def mostrar(self) -> Optional[dict]:
        """Mostrar diálogo de firma"""
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
        """Crear interfaz del diálogo de firma"""
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
        
        tk.Label(
            password_frame,
            text="Contraseña de Firma:",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(anchor="w")
        
        # Input de contraseña
        self.password_entry = tk.Entry(
            password_frame,
            font=self.styles.FONTS['normal'],
            width=40,
            show=""  # Por defecto visible
        )
        self.password_entry.pack(fill="x", pady=(5, 0))
        
        # Checkbox para mostrar/ocultar contraseña (debajo del input)
        self.show_password_var = tk.BooleanVar(value=True)  # Por defecto visible
        self.show_password_check = tk.Checkbutton(
            password_frame,
            text="Ocultar contraseña",
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
        
        BotonRedondeado(
            btn_frame,
            "Firmar APK",
            self._firmar,
            width=120,
            style='success'
        ).pack(side="right")
    
    def _seleccionar_jks(self):
        """Seleccionar archivo JKS"""
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
        """Alternar visibilidad de la contraseña"""
        if self.show_password_var.get():
            # Checkbox marcado = ocultar contraseña
            self.password_entry.config(show="•")
            self.show_password_check.config(text="Mostrar contraseña")
        else:
            # Checkbox desmarcado = mostrar contraseña
            self.password_entry.config(show="")
            self.show_password_check.config(text="Ocultar contraseña")
    
    def _crear_carpeta_escritorio(self, apk_name: str) -> Path:
        """Crear carpeta en el escritorio para los archivos firmados"""
        desktop = Path.home() / "Desktop"
        # Simplificar el nombre de la APK
        apk_simple_name = apk_name.replace('.apk', '').replace('-unsigned', '')
        if len(apk_simple_name) > 20:
            apk_simple_name = apk_simple_name[:20] + "..."
        
        folder_name = f"{apk_simple_name}-firmada"
        output_folder = desktop / folder_name
        
        # Crear la carpeta si no existe
        output_folder.mkdir(exist_ok=True)
        
        return output_folder
    
    def _copiar_apk_a_carpeta_final(self, output_folder: Path) -> Path:
        """Copiar la APK original a la carpeta final (esto sería reemplazado por la APK firmada real)"""
        apk_simple_name = self.apk_path.stem.replace('-unsigned', '')
        apk_final_path = output_folder / f"{apk_simple_name}-firmada.apk"
        
        # En la implementación real, aquí se generaría la APK firmada
        # Por ahora solo copiamos la original como ejemplo
        shutil.copy2(self.apk_path, apk_final_path)
        return apk_final_path
    
    def _crear_archivo_firma(self, output_folder: Path) -> Path:
        """Crear archivo de firma (esto sería generado por el proceso real de firma)"""
        apk_simple_name = self.apk_path.stem.replace('-unsigned', '')
        signature_path = output_folder / f"{apk_simple_name}-firmada.apk.idsig"
        
        # En la implementación real, aquí se generaría el archivo de firma
        # Por ahora creamos un archivo vacío como ejemplo
        signature_path.touch()
        return signature_path
    
    def _mostrar_exito(self, output_folder: Path, apk_signed_path: Path, signature_path: Path):
        """Mostrar mensaje de éxito con botón Aceptar"""
        success_dialog = tk.Toplevel(self.dialog)
        success_dialog.title("Firma Exitosa")
        success_dialog.geometry("500x300")
        success_dialog.resizable(False, False)
        success_dialog.configure(bg=self.styles.COLORS['primary_bg'])
        success_dialog.transient(self.dialog)
        success_dialog.grab_set()
        
        # Centrar diálogo de éxito
        success_dialog.update_idletasks()
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - success_dialog.winfo_width()) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - success_dialog.winfo_height()) // 2
        success_dialog.geometry(f"+{x}+{y}")
        
        # Contenido del diálogo de éxito
        main_frame = tk.Frame(success_dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        success_text = (
            "✅ APK firmada exitosamente\n\n"
            f"📁 Ubicación: Escritorio/{output_folder.name}/\n"
            f"📦 APK firmada: {apk_signed_path.name}\n"
            f"🔐 Archivo de firma: {signature_path.name}\n\n"
            "Sube ambos archivos cuando sea requerido."
        )
        
        success_label = tk.Label(
            main_frame,
            text=success_text,
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            justify="left"
        )
        success_label.pack(anchor="w", pady=(0, 20))
        
        BotonRedondeado(
            main_frame,
            "Aceptar",
            lambda: [success_dialog.destroy(), self.dialog.destroy()],
            width=100,
            style='success'
        ).pack(side="right")
    
    def _manejar_error_firma(self, error_msg: str):
        """Manejar errores de firma mostrando mensajes específicos"""
        if "keystore password was incorrect" in error_msg or "failed to decrypt" in error_msg:
            messagebox.showerror(
                "Error al firmar APK", 
                "La contraseña del keystore es incorrecta.\n\n"
                "Por favor, verifica la contraseña e intenta nuevamente."
            )
        else:
            # Para otros errores, mostrar el mensaje completo
            messagebox.showerror("Error al firmar APK", f"Error: {error_msg}")
    
    def _firmar(self):
        """Procesar la firma del APK"""
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
        
        # Crear carpeta en el escritorio
        output_folder = self._crear_carpeta_escritorio(self.apk_path.name)
        
        # Copiar JKS a build-tools si es necesario
        build_tools_dir = Path(self.build_tools_path)
        jks_in_build_tools = build_tools_dir / jks_file.name
        
        try:
            # Si el JKS no está en build-tools, copiarlo
            if not jks_in_build_tools.exists() or jks_in_build_tools != jks_file:
                shutil.copy2(jks_file, jks_in_build_tools)
            
            # Aquí va tu proceso real de firma
            try:
                # Simular proceso de firma - ESTO SERÍA REEMPLAZADO POR TU LÓGICA REAL
                apk_signed_path = self._copiar_apk_a_carpeta_final(output_folder)
                signature_path = self._crear_archivo_firma(output_folder)
                
                # Configurar el resultado con las rutas finales
                self.resultado = {
                    'jks_path': str(jks_in_build_tools),
                    'jks_original_path': str(jks_file),
                    'password': password,
                    'apk_path': str(self.apk_path),
                    'apk_signed_path': str(apk_signed_path),
                    'signature_path': str(signature_path),
                    'output_folder': str(output_folder)
                }
                
                # Mostrar diálogo de éxito
                self._mostrar_exito(output_folder, apk_signed_path, signature_path)
                
            except Exception as e:
                self._manejar_error_firma(str(e))
                # No destruir el diálogo para permitir corregir los datos
                return
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo preparar la firma: {str(e)}")
    
    def _cancelar(self):
        """Cancelar firma"""
        self.resultado = None
        self.dialog.destroy()
    
    def _centrar_dialogo(self):
        """Centrar diálogo en la pantalla"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")