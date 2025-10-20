import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import threading

class FirmaCreateDialog:
    def __init__(self, parent, styles=None, logger=None, config_manager=None):
        self.parent = parent
        self.styles = styles
        self.logger = logger
        self.config_manager = config_manager
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Generador de Firma Digital - APK Inspector")
        self.dialog.geometry("800x800")
        self.dialog.resizable(True, True)
        
        # Usar styles si está disponible, sino valores por defecto
        if self.styles:
            bg_color = self.styles.COLORS.get('primary_bg', '#2b2b2b')
        else:
            bg_color = '#2b2b2b'
            
        self.dialog.configure(bg=bg_color)
        
        # Centrar diálogo
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, 
                               text="Generador de Archivo de Firma (.jks)", 
                               font=('Arial', 14, 'bold'),
                               foreground='#4CAF50')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Campos de entrada
        row = 1
        
        # JDK Path
        ttk.Label(main_frame, text="Ruta JDK:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.jdk_path = tk.StringVar(value=r"C:\Program Files\Java\jdk-11\bin")
        jdk_frame = ttk.Frame(main_frame)
        jdk_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        jdk_entry = ttk.Entry(jdk_frame, textvariable=self.jdk_path, width=50)
        jdk_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(jdk_frame, text="Examinar", command=self.browse_jdk_path).pack(side=tk.RIGHT, padx=(5,0))
        row += 1
        
        # Nombre del keystore
        ttk.Label(main_frame, text="Nombre de Firma:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.keystore_name = tk.StringVar(value="")
        keystore_entry = ttk.Entry(main_frame, textvariable=self.keystore_name, width=50)
        keystore_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Alias
        ttk.Label(main_frame, text="Alias:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.alias_name = tk.StringVar(value="firma_key_app")
        alias_entry = ttk.Entry(main_frame, textvariable=self.alias_name, width=50)
        alias_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Contraseña
        ttk.Label(main_frame, text="Contraseña:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.password = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password, show="*", width=50)
        password_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Confirmar contraseña
        ttk.Label(main_frame, text="Confirmar Contraseña:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.confirm_password = tk.StringVar()
        confirm_entry = ttk.Entry(main_frame, textvariable=self.confirm_password, show="*", width=50)
        confirm_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Información del certificado
        cert_frame = ttk.LabelFrame(main_frame, text="Información del Certificado", padding="5")
        cert_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        cert_frame.columnconfigure(1, weight=1)
        
        cert_row = 0
        fields = [
            ("Nombre y Apellido:", ""),
            ("Unidad Organizativa:", ""),
            ("Organización:", ""),
            ("Ciudad/Localidad:", ""),
            ("Estado/Provincia:", ""),
            ("Código de País (2 letras):", "CL")
        ]
        
        self.cert_fields = {}
        for label_text, default_value in fields:
            ttk.Label(cert_frame, text=label_text).grid(row=cert_row, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value=default_value)
            entry = ttk.Entry(cert_frame, textvariable=var, width=40)
            entry.grid(row=cert_row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5,0))
            field_name = label_text.replace(":", "").replace(" ", "_").lower()
            self.cert_fields[field_name] = var
            cert_row += 1
        
        row += 1
        
        # Área de salida
        output_frame = ttk.LabelFrame(main_frame, text="Salida del Comando", padding="5")
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = tk.Text(output_frame, height=12, width=80, bg='#1e1e1e', fg='#cccccc',
                                  font=('Consolas', 10), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        row += 1
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="Generar Firma", 
                  command=self.generate_signature).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Abrir Carpeta", 
                  command=self.open_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Limpiar Salida", 
                  command=self.clear_output).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cerrar", 
                  command=self.dialog.destroy).pack(side=tk.LEFT)
        
        # Configurar pesos para redimensionamiento
        main_frame.rowconfigure(row, weight=1)
        
    def browse_jdk_path(self):
        path = filedialog.askdirectory(title="Seleccionar directorio JDK bin")
        if path:
            self.jdk_path.set(path)
    
    def validate_inputs(self):
        if not self.jdk_path.get():
            messagebox.showerror("Error", "La ruta JDK es obligatoria")
            return False
            
        if not self.keystore_name.get():
            messagebox.showerror("Error", "El nombre del keystore es obligatorio")
            return False
            
        if not self.alias_name.get():
            messagebox.showerror("Error", "El alias es obligatorio")
            return False
            
        if not self.password.get():
            messagebox.showerror("Error", "La contraseña es obligatoria")
            return False
            
        # VALIDAR LONGITUD DE CONTRASEÑA
        if len(self.password.get()) < 6:
            messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres")
            return False
            
        if self.password.get() != self.confirm_password.get():
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return False
            
        # Validar campos del certificado
        for field_name, var in self.cert_fields.items():
            if not var.get():
                messagebox.showerror("Error", f"El campo '{field_name}' es obligatorio")
                return False
                
        # Validar código de país (2 letras exactamente)
        codigo_pais = self.cert_fields['código_de_país_(2_letras)'].get()
        if len(codigo_pais) != 2 or not codigo_pais.isalpha():
            messagebox.showerror("Error", "El código de país debe ser exactamente 2 letras (ej: ES, US, MX)")
            return False
                
        return True
    
    def generate_signature(self):
        if not self.validate_inputs():
            return
            
        # Verificar si keytool existe
        keytool_path = os.path.join(self.jdk_path.get(), "keytool.exe")
        if not os.path.exists(keytool_path):
            messagebox.showerror("Error", f"No se encontró keytool.exe en:\n{keytool_path}")
            return
        
        # Construir comando (pero se modificará la ubicación en execute_keytool)
        keystore_file = f"{self.keystore_name.get()}.jks"
        cmd = [
            keytool_path,
            "-genkeypair",
            "-v",
            "-keystore", keystore_file,  # Este se modificará después
            "-keyalg", "RSA",
            "-keysize", "2048", 
            "-validity", "10000",
            "-alias", self.alias_name.get()
        ]
        
        self.append_output(f"Microsoft Windows [Version 10.0.26100.2454]\n")
        self.append_output(f"(c) Microsoft Corporation. Todos los derechos reservados.\n\n")
        self.append_output(f"CD: {self.jdk_path.get()}\n")
        self.append_output(f"Comando: {' '.join(cmd)}\n")
        self.append_output(f"NOTA: El archivo se guardará en Documents/APK_Signatures/\n")
        self.append_output("-" * 60 + "\n")
        
        # Ejecutar en hilo separado para no bloquear la UI
        thread = threading.Thread(target=self.execute_keytool, args=(cmd, keystore_file))
        thread.daemon = True
        thread.start()
    
    def execute_keytool(self, cmd, keystore_file):
        try:
            # Validar que la contraseña tenga al menos 6 caracteres
            if len(self.password.get()) < 6:
                self.append_output(f"\n✗ Error: La contraseña debe tener al menos 6 caracteres\n")
                return
                
            # Usar el directorio de documentos o escritorio del usuario en lugar de C:\Program Files
            import os
            from pathlib import Path
            
            # Obtener directorio de documentos del usuario
            documents_dir = Path.home() / "Documents"
            output_dir = documents_dir / "APK_Signatures"
            output_dir.mkdir(exist_ok=True)  # Crear directorio si no existe
            
            # Cambiar el comando para guardar en la nueva ubicación
            cmd_modified = cmd.copy()
            # Encontrar el índice de -keystore y reemplazar el nombre del archivo con la ruta completa
            keystore_index = cmd_modified.index("-keystore") + 1
            cmd_modified[keystore_index] = str(output_dir / keystore_file)
            
            self.append_output(f"Directorio de salida: {output_dir}\n")
            self.append_output(f"Ejecutando keytool...\n")
            
            # Preparar respuestas automáticas CORREGIDAS
            input_data = (
                f"{self.password.get()}\n"  # Enter keystore password
                f"{self.password.get()}\n"  # Re-enter new password
                f"{self.cert_fields['nombre_y_apellido'].get()}\n"  # First and last name
                f"{self.cert_fields['unidad_organizativa'].get()}\n"  # Organizational unit
                f"{self.cert_fields['organización'].get()}\n"  # Organization
                f"{self.cert_fields['ciudad/localidad'].get()}\n"  # City or Locality
                f"{self.cert_fields['estado/provincia'].get()}\n"  # State or Province
                f"{self.cert_fields['código_de_país_(2_letras)'].get()}\n"  # Country code
                "yes\n"  # Confirm information
            )
            
            # Ejecutar proceso en el directorio JDK pero guardar en Documents
            process = subprocess.Popen(
                cmd_modified,
                cwd=self.jdk_path.get(),  # keytool necesita estar en el PATH del JDK
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            # Enviar entradas automáticas y capturar salida
            output, _ = process.communicate(input=input_data)
            
            # Mostrar salida en el área de texto
            self.append_output(output)
            
            if process.returncode == 0:
                final_path = output_dir / keystore_file
                self.append_output(f"\n✓ Archivo '{keystore_file}' generado exitosamente!\n")
                self.append_output(f"Ubicación: {final_path}\n")
                
                # Mostrar mensaje de éxito
                self.dialog.after(100, lambda: messagebox.showinfo(
                    "Éxito", 
                    f"Keystore creado correctamente!\n\n"
                    f"Archivo: {keystore_file}\n"
                    f"Ubicación: {final_path}\n\n"
                    f"Guarda la contraseña de forma segura."
                ))
                
                # Abrir la carpeta donde se guardó
                self.dialog.after(500, lambda: os.startfile(output_dir))
                
            else:
                self.append_output(f"\n✗ Error al generar el archivo. Código: {process.returncode}\n")
                
        except Exception as e:
            self.append_output(f"\n✗ Error ejecutando keytool: {str(e)}\n")
    
    def append_output(self, text):
        def update_text():
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)
            self.output_text.update_idletasks()
        
        self.dialog.after(0, update_text)
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
    
    def open_folder(self):
        """Abrir la carpeta de firmas en Documents"""
        from pathlib import Path
        try:
            documents_dir = Path.home() / "Documents" / "APK_Signatures"
            documents_dir.mkdir(exist_ok=True)  # Crear si no existe
            
            if documents_dir.exists():
                os.startfile(str(documents_dir))
            else:
                messagebox.showerror("Error", f"No se pudo encontrar la carpeta:\n{documents_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")

    def show_firma_create_dialog(parent):
        dialog = FirmaCreateDialog(parent)
        parent.wait_window(dialog.dialog)

    # Ejemplo de uso
    if __name__ == "__main__":
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal
        
        # Mostrar diálogo
        show_firma_create_dialog(root)
        
        root.mainloop()