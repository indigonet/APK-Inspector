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
        self.percent_label = None
        self.current_progress = 0
        self.is_running = True
        
    def mostrar(self):
        """Mostrar pantalla de carga"""
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("ISV Toolkit - Cargando...")
        self.loading_window.geometry("500x300")
        self.loading_window.resizable(False, False)
        self.loading_window.configure(bg='#1e1e1e')
        
        # Centrar en la pantalla
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        
        # Ocultar ventana principal temporalmente
        self.root.withdraw()
        
        # Hacer que no se pueda cerrar
        self.loading_window.protocol("WM_DELETE_WINDOW", self._disable_close)
        
        # Centrar en pantalla
        self._centrar_ventana()
        
        # Crear interfaz
        self._crear_interfaz()
        
        # Iniciar animación de progreso inicial
        self._iniciar_animacion_progreso()
        
        return self.loading_window
    
    def _disable_close(self):
        """Deshabilitar cierre de ventana"""
        pass  # No hacer nada cuando intentan cerrar
    
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
        main_frame = tk.Frame(self.loading_window, bg='#1e1e1e', padx=40, pady=40)
        main_frame.pack(fill="both", expand=True)
        
        # Logo con estilo moderno
        logo_frame = tk.Frame(main_frame, bg='#1e1e1e')
        logo_frame.pack(pady=(0, 20))
        
        # Texto del logo con gradiente simulado
        logo_label = tk.Label(
            logo_frame,
            text="🔍 APK INSPECTOR",
            font=("Segoe UI", 24, "bold"),
            bg='#1e1e1e',
            fg='#4a9eff',
            pady=5
        )
        logo_label.pack()
        
        # Efecto de subtítulo con animación
        self.subtitle_text = tk.StringVar()
        self.subtitle_text.set("Inicializando herramienta de análisis...")
        
        subtitle_label = tk.Label(
            logo_frame,
            textvariable=self.subtitle_text,
            font=("Segoe UI", 11),
            bg='#1e1e1e',
            fg='#a0a0a0'
        )
        subtitle_label.pack()
        
        # Barra de progreso con estilo moderno
        progress_container = tk.Frame(main_frame, bg='#1e1e1e', pady=25)
        progress_container.pack(fill="x")
        
        # Estilo personalizado para la barra de progreso
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("custom.Horizontal.TProgressbar",
                        background='#4a9eff',
                        troughcolor='#2d2d2d',
                        bordercolor='#2d2d2d',
                        lightcolor='#4a9eff',
                        darkcolor='#4a9eff')
        
        self.progress = ttk.Progressbar(
            progress_container,
            style="custom.Horizontal.TProgressbar",
            mode='determinate',
            length=420,
            maximum=100
        )
        self.progress.pack()
        
        # Contenedor para porcentaje y mensaje
        info_frame = tk.Frame(main_frame, bg='#1e1e1e')
        info_frame.pack(fill="x", pady=(15, 0))
        
        # Porcentaje a la izquierda
        self.percent_label = tk.Label(
            info_frame,
            text="0%",
            font=("Segoe UI", 12, "bold"),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        self.percent_label.pack(side="left")
        
        # Mensaje de estado a la derecha
        self.status_label = tk.Label(
            info_frame,
            text="Cargando componentes...",
            font=("Segoe UI", 10),
            bg='#1e1e1e',
            fg='#cccccc',
            wraplength=300
        )
        self.status_label.pack(side="right")
        
        # Barra de progreso de pasos (opcional)
        self._crear_barra_pasos(main_frame)
        
        # Versión/build info
        version_frame = tk.Frame(main_frame, bg='#1e1e1e')
        version_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        self.version_label = tk.Label(
            version_frame,
            text="ISV Toolkit v1.0.0 • Cargando...",
            font=("Segoe UI", 8),
            bg='#1e1e1e',
            fg='#666666'
        )
        self.version_label.pack(side="left")
        
        # Indicador de que está cargando (animación de puntos)
        self.dots_label = tk.Label(
            version_frame,
            text="",
            font=("Segoe UI", 8),
            bg='#1e1e1e',
            fg='#888888'
        )
        self.dots_label.pack(side="right")
        
        # Iniciar animación de puntos
        self._animar_puntos()
    
    def _crear_barra_pasos(self, parent):
        """Crear barra de pasos de inicialización"""
        steps_frame = tk.Frame(parent, bg='#1e1e1e', pady=15)
        steps_frame.pack(fill="x")
        
        self.steps = [
            {"name": "Verificando herramientas", "completed": False},
            {"name": "Cargando configuración", "completed": False},
            {"name": "Inicializando servicios", "completed": False},
            {"name": "Preparando interfaz", "completed": False}
        ]
        
        self.step_labels = []
        step_container = tk.Frame(steps_frame, bg='#1e1e1e')
        step_container.pack()
        
        for i, step in enumerate(self.steps):
            step_frame = tk.Frame(step_container, bg='#1e1e1e')
            step_frame.grid(row=0, column=i, padx=15)
            
            # Indicador circular
            circle = tk.Canvas(step_frame, width=20, height=20, bg='#1e1e1e', 
                              highlightthickness=0, bd=0)
            circle.create_oval(2, 2, 18, 18, fill='#3a3a3a', outline='#3a3a3a')
            circle.pack()
            
            # Texto del paso
            label = tk.Label(
                step_frame,
                text=step["name"],
                font=("Segoe UI", 8),
                bg='#1e1e1e',
                fg='#888888'
            )
            label.pack(pady=(5, 0))
            
            self.step_labels.append({
                "canvas": circle,
                "label": label,
                "completed": False
            })
    
    def _animar_puntos(self):
        """Animación de puntos '...' que se mueven"""
        def animar():
            dots = ["", ".", "..", "..."]
            i = 0
            while self.is_running and self.dots_label and self.dots_label.winfo_exists():
                self.dots_label.config(text=dots[i % 4])
                i += 1
                time.sleep(0.5)
        
        thread = threading.Thread(target=animar, daemon=True)
        thread.start()
    
    def _iniciar_animacion_progreso(self):
        """Animación inicial del progreso"""
        def animar():
            # Progreso inicial suave
            for i in range(5, 20):
                if not self.is_running:
                    break
                self.actualizar_progreso(i, "Preparando entorno...")
                time.sleep(0.05)
        
        thread = threading.Thread(target=animar, daemon=True)
        thread.start()
    
    def actualizar_progreso(self, porcentaje, mensaje):
        """Actualizar progreso y mensaje"""
        if not self.is_running:
            return
            
        try:
            # Asegurarse de que el porcentaje esté en rango
            porcentaje = max(0, min(100, porcentaje))
            
            # Actualizar UI desde el hilo principal
            def actualizar():
                if (self.progress and self.progress.winfo_exists() and
                    self.percent_label and self.percent_label.winfo_exists() and
                    self.status_label and self.status_label.winfo_exists()):
                    
                    self.progress['value'] = porcentaje
                    self.percent_label.config(text=f"{porcentaje}%")
                    self.status_label.config(text=mensaje)
                    
                    # Actualizar subtítulo para pasos específicos
                    if porcentaje < 25:
                        self.subtitle_text.set("Inicializando herramientas...")
                    elif porcentaje < 50:
                        self.subtitle_text.set("Configurando entorno...")
                    elif porcentaje < 75:
                        self.subtitle_text.set("Cargando servicios...")
                    else:
                        self.subtitle_text.set("Finalizando inicialización...")
                    
                    # Actualizar pasos completados
                    self._actualizar_pasos(porcentaje)
                    
                    self.loading_window.update()
            
            if self.loading_window and self.loading_window.winfo_exists():
                self.loading_window.after(0, actualizar)
                
        except Exception as e:
            print(f"Error actualizando progreso: {e}")
    
    def _actualizar_pasos(self, porcentaje):
        """Actualizar visualización de pasos completados"""
        step_index = int((porcentaje / 100) * len(self.steps))
        
        for i, step in enumerate(self.step_labels):
            canvas = step["canvas"]
            label = step["label"]
            
            if i < step_index and not step["completed"]:
                # Marcar como completado
                canvas.delete("all")
                canvas.create_oval(2, 2, 18, 18, fill='#4a9eff', outline='#4a9eff')
                # Agregar checkmark
                canvas.create_text(10, 10, text="✓", fill='white', font=("Arial", 10, "bold"))
                label.config(fg='#4a9eff')
                step["completed"] = True
    
    def actualizar_version_info(self, texto):
        """Actualizar información de versión"""
        if self.version_label and self.version_label.winfo_exists():
            self.version_label.config(text=texto)
    
    def cerrar(self):
        """Cerrar pantalla de carga con animación"""
        self.is_running = False
        
        def animar_cierre():
            # Animación de cierre suave
            for i in range(100, -1, -5):
                try:
                    if self.progress and self.progress.winfo_exists():
                        self.progress['value'] = i
                        self.loading_window.update()
                        time.sleep(0.01)
                except:
                    break
            
            # Destruir ventana
            if self.loading_window and self.loading_window.winfo_exists():
                self.loading_window.destroy()
            
            # Mostrar ventana principal
            if self.root:
                self.root.deiconify()
                self.root.focus_force()
        
        # Ejecutar animación en hilo separado
        thread = threading.Thread(target=animar_cierre, daemon=True)
        thread.start()