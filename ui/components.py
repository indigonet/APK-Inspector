import tkinter as tk
from typing import Callable, Dict, Any
import tkinter.ttk as ttk

class Tooltip:
    """Clase para crear tooltips en widgets - Versión robusta"""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.entrar)
        self.widget.bind("<Leave>", self.salir)
        self.widget.bind("<Motion>", self.mover)
    
    def entrar(self, event=None):
        """Mostrar tooltip"""
        self.mostrar_tooltip(event)
    
    def salir(self, event=None):
        """Ocultar tooltip"""
        self.ocultar_tooltip()
    
    def mover(self, event=None):
        """Mover tooltip con el mouse"""
        if self.tooltip and event:
            self.actualizar_posicion(event.x_root, event.y_root)
    
    def mostrar_tooltip(self, event=None):
        """Mostrar tooltip"""
        if self.tooltip:
            return  # Ya está mostrándose
        
        # Obtener posición
        if event:
            x = event.x_root + 15
            y = event.y_root + 15
        else:
            # Método alternativo para widgets sin eventos
            try:
                # Intentar obtener bbox del widget
                bbox = self.widget.bbox("all")
                if bbox:
                    x1, y1, x2, y2 = bbox
                    x = self.widget.winfo_rootx() + (x2 - x1) // 2
                    y = self.widget.winfo_rooty() + y2 + 5
                else:
                    # Usar posición del widget
                    x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
                    y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            except:
                # Último recurso
                x = self.widget.winfo_rootx() + 25
                y = self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # Hacer que el tooltip esté siempre encima
        self.tooltip.attributes('-topmost', True)
        
        label = tk.Label(
            self.tooltip, 
            text=self.text, 
            justify='left',
            background="#f2f1f6", 
            relief='solid', 
            borderwidth=1,
            font=("Segoe UI", 8),
            padx=5,
            pady=2
        )
        label.pack()
    
    def actualizar_posicion(self, x, y):
        """Actualizar posición del tooltip"""
        if self.tooltip:
            self.tooltip.wm_geometry(f"+{x+15}+{y+15}")
    
    def ocultar_tooltip(self):
        """Ocultar tooltip"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class AppStyles:
    """Estilos de la aplicación - integrados en components"""
    
    # Colores
    COLORS = {
        'primary_bg': '#f5f5f5',
        'secondary_bg': '#ffffff',
        'accent': '#2196F3',
        'success': '#4CAF50',
        'warning': '#FF9800',
        'error': '#f44336',
        'text_primary': '#000000',
        'text_secondary': '#666666',
        'border': '#cccccc',
        'disabled_bg': '#f0f0f0',    # Nuevo color para estado deshabilitado
        'disabled_text': '#a0a0a0',  # Nuevo color para texto deshabilitado
        'disabled_border': '#d0d0d0' # Nuevo color para borde deshabilitado
    }
    
    # Fuentes
    FONTS = {
        'title': ('Segoe UI', 16, 'bold'),
        'subtitle': ('Segoe UI', 12, 'bold'),
        'normal': ('Segoe UI', 10),
        'monospace': ('Consolas', 10)
    }
    
    # Espaciado
    SPACING = {
        'small': 5,
        'medium': 10,
        'large': 15,
        'xlarge': 20
    }

class BotonRedondeado(tk.Canvas):
    """Botón redondeado con estilos integrados, cursor hand2 y estado deshabilitado"""
    
    def __init__(self, parent, text: str, command: Callable, **kwargs):
        self.styles = AppStyles()
        
        # Configuración por defecto con estilos
        self.width = kwargs.pop('width', 120)
        self.height = kwargs.pop('height', 35)
        self.corner_radius = kwargs.pop('corner_radius', 20)
        
        super().__init__(parent, width=self.width, height=self.height, 
                        highlightthickness=0, bg=parent.cget('bg'), cursor="hand2")
        
        self.command = command
        self.text = text
        self.enabled = True  # Estado por defecto: habilitado
        
        # Estilos de botón
        button_style = self._get_button_style(kwargs.pop('style', 'primary'))
        self.states = {
            'normal': kwargs.pop('bg_color', button_style['normal']),
            'hover': kwargs.pop('hover_color', button_style['hover']), 
            'active': kwargs.pop('active_color', button_style['active']),
            'disabled': kwargs.pop('disabled_color', self.styles.COLORS['disabled_bg'])
        }
        self.border_color = kwargs.pop('border_color', button_style['border'])
        self.border_width = kwargs.pop('border_width', 2)
        self.text_color = kwargs.pop('text_color', button_style['text'])
        self.disabled_text_color = kwargs.pop('disabled_text_color', self.styles.COLORS['disabled_text'])
        self.disabled_border_color = kwargs.pop('disabled_border_color', self.styles.COLORS['disabled_border'])
        
        self.current_state = 'normal'
        
        # Event bindings
        self.bind("<Enter>", self._al_entrar)
        self.bind("<Leave>", self._al_salir)
        self.bind("<ButtonPress-1>", self._al_presionar)
        self.bind("<ButtonRelease-1>", self._al_soltar)
        
        # Tooltip
        tooltip_text = kwargs.pop('tooltip_text', '')
        if tooltip_text:
            Tooltip(self, tooltip_text)
        
        self.dibujar_boton()
    
    def _get_button_style(self, style_name: str) -> Dict[str, str]:
        """Obtener configuración de estilo para el botón"""
        styles = {
            'primary': {
                'normal': '#FFFFFF',  # Blanco puro
                'hover': '#F5F5F5',   # Blanco ligeramente gris
                'active': '#EEEEEE',  # Gris muy claro
                'border': '#000000',  # Negro
                'text': '#000000'     # Negro
            },
            'secondary': {
                'normal': '#F8F9FA',  # Blanco casi puro
                'hover': '#E9ECEF',   # Gris muy claro
                'active': '#DEE2E6',  # Gris claro
                'border': '#495057',  # Gris oscuro
                'text': '#000000'     # Negro
            },
            'danger': {
                'normal': '#FFFFFF',  # Blanco
                'hover': '#FFEBEE',   # Rojo muy claro
                'active': '#FFCDD2',  # Rosa claro
                'border': '#D32F2F',  # Rojo
                'text': '#D32F2F'     # Rojo
            },
            'success': {
                'normal': '#FFFFFF',  # Blanco
                'hover': '#E8F5E8',   # Verde muy claro
                'active': '#C8E6C9',  # Verde claro
                'border': '#2E7D32',  # Verde oscuro
                'text': '#2E7D32'     # Verde oscuro
            },
            'sign': { 
                'normal': '#FFFFFF',  # Blanco
                'hover': '#F1F8E9',   # Verde muy claro
                'active': '#DCEDC8',  # Verde claro
                'border': '#4CAF50',  # Verde
                'text': '#2E7D32'     # Verde oscuro
            },
            'logcat': { 
                'normal': "#FFFFFF",   # Blanco
                'hover': "#FFFDE7",    # Amarillo muy claro
                'active': "#EAE194",   # Amarillo claro
                'border': "#FFD600",   # Amarillo vibrante
                'text': "#212121"      # Negro
            },
            'APK': {
                'normal': '#FFFFFF',   # Blanco
                'hover': "#CEDEF5",    # Azul muy claro
                'active': '#E3F2FD',   # Azul claro
                'border': "#2196F3",   # Azul Android
                'text': '#000000'      # Negro
            },
            'warning': {
                'normal': '#FFFFFF',   # Blanco
                'hover': '#FFF8E1',    # Amarillo muy claro
                'active': '#FFECB3',   # Amarillo claro
                'border': '#FFA000',   # Amarillo anaranjado
                'text': '#E65100'      # Naranja oscuro
            }
        }
        return styles.get(style_name, styles['primary'])
    
    def habilitar(self):
        """Habilitar el botón"""
        self.enabled = True
        self.config(cursor="hand2")
        self.current_state = 'normal'
        self.dibujar_boton()
    
    def deshabilitar(self):
        """Deshabilitar el botón"""
        self.enabled = False
        self.config(cursor="")
        self.current_state = 'disabled'
        self.dibujar_boton()
    
    def esta_habilitado(self) -> bool:
        """Verificar si el botón está habilitado"""
        return self.enabled
    
    def dibujar_boton(self):
        """Dibujar botón con estilos aplicados"""
        self.delete("all")
        
        # Determinar colores según el estado
        if not self.enabled:
            fill_color = self.states['disabled']
            outline_color = self.disabled_border_color
            text_color = self.disabled_text_color
        else:
            fill_color = self.states[self.current_state]
            outline_color = self.border_color
            text_color = self.text_color
        
        # Rectángulo redondeado
        self.crear_rectangulo_redondeado(
            self.border_width//2, 
            self.border_width//2, 
            self.width - self.border_width//2, 
            self.height - self.border_width//2, 
            radius=self.corner_radius,
            fill=fill_color,
            outline=outline_color, 
            width=self.border_width
        )
        
        # Texto
        self.create_text(
            self.width//2, 
            self.height//2,
            text=self.text, 
            fill=text_color,
            font=self.styles.FONTS['normal']
        )
    
    def crear_rectangulo_redondeado(self, x1, y1, x2, y2, radius=20, **kwargs):
        """Crear rectángulo con esquinas redondeadas"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)
    
    def _al_entrar(self, event):
        if self.enabled:
            self.current_state = 'hover'
            self.dibujar_boton()
    
    def _al_salir(self, event):
        if self.enabled:
            self.current_state = 'normal'
            self.dibujar_boton()
    
    def _al_presionar(self, event):
        if self.enabled:
            self.current_state = 'active'
            self.dibujar_boton()
    
    def _al_soltar(self, event):
        if self.enabled:
            self.current_state = 'hover'
            self.dibujar_boton()
            self.command()

class PanelDeslizante(tk.Frame):
    """Panel expandible con estilos integrados"""
    
    def __init__(self, parent, titulo: str, **kwargs):
        self.styles = AppStyles()
        super().__init__(parent, **kwargs)
        self.expandido = False
        self.contenido = None
        
        # Frame del título con estilos
        self.frame_titulo = tk.Frame(self, bg=self.styles.COLORS['secondary_bg'])
        self.frame_titulo.pack(fill="x", padx=5, pady=2)
        
        self.btn_toggle = BotonRedondeado(
            self.frame_titulo, 
            f"▶ {titulo}", 
            self.toggle,
            width=200, 
            height=30,
            style='secondary'
        )
        self.btn_toggle.pack(anchor="w")
        
    def toggle(self):
        """Alternar entre expandido y contraído"""
        self.expandido = not self.expandido
        
        if self.expandido:
            self.btn_toggle.itemconfig(1, text=f"▼ {self.btn_toggle.text.split(' ', 1)[1]}")
            self.mostrar_contenido()
        else:
            self.btn_toggle.itemconfig(1, text=f"▶ {self.btn_toggle.text.split(' ', 1)[1]}")
            self.ocultar_contenido()
    
    def mostrar_contenido(self):
        """Mostrar contenido del panel"""
        if self.contenido:
            self.contenido.pack(fill="x", padx=10, pady=5)
    
    def ocultar_contenido(self):
        """Ocultar contenido del panel"""
        if self.contenido:
            self.contenido.pack_forget()
    
    def set_contenido(self, widget):
        """Establecer el contenido del panel"""
        self.contenido = widget