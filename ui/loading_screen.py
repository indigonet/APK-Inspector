import tkinter as tk
from tkinter import ttk
import threading
import time
from pathlib import Path

class LoadingScreen:
    def __init__(self, root):
        self.root = root
        self.loading_window = None
        self.progress = None
        self.status_label = None
        self.current_progress = 0
        
    def mostrar(self):
        """Mostrar pantalla de carga"""
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("APK Inspector")
        self.loading_window.geometry("500x300")
        self.loading_window.resizable(False, False)
        self.loading_window.configure(bg='#2b2b2b')
        
        # Centrar en la pantalla y hacerla modal
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        
        # Ocultar ventana principal temporalmente
        self.root.withdraw()
        
        # Configurar para que no tenga bordes de ventana (opcional)
        # self.loading_window.overrideredirect(True)
        
        # Centrar en pantalla
        self._centrar_ventana()
        
        self._crear_interfaz()
        return self.loading_window
        
    def _centrar_ventana(self):
        """Centrar ventana en la pantalla"""
        self.loading_window.update_idletasks()
        screen_width = self.loading_window.winfo_screenwidth()
        screen_height = self.loading_window.winfo_screenheight()
        x = (screen_width - 500) // 2
        y = (screen_height - 300) // 2
        self.loading_window.geometry(f"500x300+{x}+{y}")
        
    def _crear_interfaz(self):
        """Crear interfaz de la pantalla de carga"""
        # Frame principal
        main_frame = tk.Frame(self.loading_window, bg='#2b2b2b', padx=40, pady=40)
        main_frame.pack(fill="both", expand=True)
        
        # Logo o título
        title_label = tk.Label(
            main_frame,
            text="🔍 APK Inspector",
            font=("Segoe UI", 20, "bold"),
            bg='#2b2b2b',
            fg='#ffffff',
            pady=20
        )
        title_label.pack()
        
        # Subtítulo
        subtitle_label = tk.Label(
            main_frame,
            text="Analizador de aplicaciones Android",
            font=("Segoe UI", 11),
            bg='#2b2b2b',
            fg='#cccccc',
            pady=5
        )
        subtitle_label.pack()
        
        # Barra de progreso
        progress_frame = tk.Frame(main_frame, bg='#2b2b2b', pady=30)
        progress_frame.pack(fill="x")
        
        self.progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400,
            maximum=100
        )
        self.progress.pack()
        
        # Porcentaje
        self.percent_label = tk.Label(
            progress_frame,
            text="0%",
            font=("Segoe UI", 10, "bold"),
            bg='#2b2b2b',
            fg='#ffffff'
        )
        self.percent_label.pack(pady=5)
        
        # Etiqueta de estado
        self.status_label = tk.Label(
            main_frame,
            text="Inicializando aplicación...",
            font=("Segoe UI", 10),
            bg='#2b2b2b',
            fg='#ffffff',
            wraplength=400
        )
        self.status_label.pack()
        
        # Versión
        version_label = tk.Label(
            main_frame,
            text="Cargando...",
            font=("Segoe UI", 8),
            bg='#2b2b2b',
            fg='#888888',
            pady=10
        )
        version_label.pack(side="bottom")
        
    def actualizar_progreso(self, porcentaje, mensaje):
        """Actualizar progreso y mensaje"""
        if self.progress and self.status_label and self.percent_label:
            self.progress['value'] = porcentaje
            self.percent_label.config(text=f"{porcentaje}%")
            self.status_label.config(text=mensaje)
            self.loading_window.update()
            
    def cerrar(self):
        """Cerrar pantalla de carga y mostrar ventana principal"""
        if self.loading_window:
            self.loading_window.destroy()
        self.root.deiconify() 