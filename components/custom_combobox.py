import tkinter as tk
from tkinter import ttk

class CustomCombobox:
    def __init__(self, parent, all_items, styles, on_select_callback=None, width=30):
        self.parent = parent
        self.all_items = all_items
        self.styles = styles
        self.on_select_callback = on_select_callback
        self.width = width
        
        # Variables de estado
        self.filtered_items = all_items.copy()
        self.dropdown_visible = False
        self.current_value = tk.StringVar()
        self.last_hover_index = -1
        
        self._create_widgets()
        self._setup_bindings()
    
    def _create_widgets(self):
        """Crear los widgets del combobox personalizado"""
        # Frame principal
        self.main_frame = tk.Frame(self.parent, bg=self.styles.COLORS['secondary_bg'])
        
        # Entry para búsqueda
        self.entry = tk.Entry(
            self.main_frame,
            textvariable=self.current_value,
            font=("Segoe UI", 10),
            bg="white",
            fg="black",
            relief="solid",
            bd=1,
            width=self.width
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Botón dropdown
        self.dropdown_btn = tk.Button(
            self.main_frame,
            text="▼",
            font=("Segoe UI", 9),
            command=self._toggle_dropdown,
            bg=self.styles.COLORS['accent'],
            fg="white",
            relief="flat",
            width=3,
            cursor="hand2"
        )
        self.dropdown_btn.pack(side="left")
        
        # Frame del dropdown (lista) - se crea en la ventana principal
        self.dropdown_frame = tk.Frame(
            self.parent.winfo_toplevel(),
            bg="white",
            relief="solid",
            bd=1
        )
        
        # Listbox con scrollbar
        listbox_container = tk.Frame(self.dropdown_frame, bg="white")
        listbox_container.pack(fill="both", expand=True, padx=1, pady=1)
        
        self.listbox = tk.Listbox(
            listbox_container,
            font=("Segoe UI", 9),
            bg="white",
            fg="black",
            selectbackground="#007acc",
            selectforeground="white",
            highlightthickness=0,
            borderwidth=0,
            height=15,
            activestyle="none"
        )
        
        self.scrollbar = tk.Scrollbar(
            listbox_container,
            orient="vertical",
            command=self.listbox.yview
        )
        
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Llenar listbox inicial
        self._update_listbox()
    
    def _setup_bindings(self):
        """Configurar eventos básicos sin atajos de teclado"""
        # ✅ ELIMINADO: Todos los atajos de teclado
        
        # Solo bindings esenciales
        self.entry.bind('<KeyRelease>', self._on_key_release)
        self.entry.bind('<FocusIn>', self._on_entry_focus_in)
        self.entry.bind('<FocusOut>', self._on_entry_focus_out)
        
        # Bloquear tecla Space sola
        self.entry.bind('<space>', lambda e: "break")
        
        # ✅ ELIMINADO: Eventos de Ctrl+Space y otras combinaciones
        
        # Bindings del Listbox - solo los básicos
        self.listbox.bind('<Button-1>', self._on_listbox_click)
        self.listbox.bind('<Double-Button-1>', self._on_double_click)
        
        # ✅ ELIMINADO: Eventos de teclado en listbox
        
        # Binding global para clicks fuera
        self.parent.winfo_toplevel().bind('<Button-1>', self._on_global_click)
        
        # ✅ ELIMINADO: Validación de espacios (ya se bloquea con bind)
        
    def _block_spaces_in_entry(self):
        """Bloquear espacios - método simplificado"""
        # Ya se bloquea con el bind '<space>'
        pass

    def _actualizar_packages_ui(self, packages):
        """Actualizar la UI con la lista de packages"""
        if hasattr(self, 'package_combobox'):
            self.package_combobox.set_items(packages)
        
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.config(
                text=f"✅ {len(packages)} packages cargados - Selecciona o escribe para filtrar",
                fg="#4caf50"
            )
        
        # Detectar package del APK automáticamente
        self._detectar_package_apk_inteligente()
    
    # ✅ ELIMINADO: Todos los métodos de control de teclas (Ctrl, Space, etc.)
    
    def _on_key_press(self, event):
        """✅ REEMPLAZADO: Permitir solo caracteres básicos"""
        # Permitir todas las teclas excepto espacio
        if event.char == ' ':
            return "break"
        return
    
    def _on_key_release(self, event):
        """Filtrar mientras escribes"""
        # Actualizar la lista filtrada
        self._filter_items()
        
        # Mostrar dropdown si hay resultados y hay texto
        if self.filtered_items and self.current_value.get():
            self._show_dropdown()
        else:
            self._hide_dropdown()
    
    def _on_global_click(self, event):
        """Detectar clicks fuera del combobox"""
        if not self.dropdown_visible:
            return
            
        # Obtener coordenadas del widget
        entry_x1 = self.entry.winfo_rootx()
        entry_y1 = self.entry.winfo_rooty()
        entry_x2 = entry_x1 + self.entry.winfo_width()
        entry_y2 = entry_y1 + self.entry.winfo_height()
        
        dropdown_x1 = self.dropdown_frame.winfo_rootx()
        dropdown_y1 = self.dropdown_frame.winfo_rooty()
        dropdown_x2 = dropdown_x1 + self.dropdown_frame.winfo_width()
        dropdown_y2 = dropdown_y1 + self.dropdown_frame.winfo_height()
        
        btn_x1 = self.dropdown_btn.winfo_rootx()
        btn_y1 = self.dropdown_btn.winfo_rooty()
        btn_x2 = btn_x1 + self.dropdown_btn.winfo_width()
        btn_y2 = btn_y1 + self.dropdown_btn.winfo_height()
        
        # Verificar si el click fue fuera del área del combobox
        click_in_entry = (entry_x1 <= event.x_root <= entry_x2 and 
                         entry_y1 <= event.y_root <= entry_y2)
        click_in_dropdown = (dropdown_x1 <= event.x_root <= dropdown_x2 and 
                            dropdown_y1 <= event.y_root <= dropdown_y2)
        click_in_dropdown_btn = (btn_x1 <= event.x_root <= btn_x2 and 
                                btn_y1 <= event.y_root <= btn_y2)
        
        if not (click_in_entry or click_in_dropdown or click_in_dropdown_btn):
            self._hide_dropdown_and_focus_entry()
    
    def _on_listbox_click(self, event):
        """Click simple en el listbox"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < self.listbox.size():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            
            selected_item = self.listbox.get(index)
            self.current_value.set(selected_item)
    
    def _on_double_click(self, event):
        """Doble click para seleccionar y cerrar"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < self.listbox.size():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            
            selected_item = self.listbox.get(index)
            self.current_value.set(selected_item)
            
            self._hide_dropdown_and_focus_entry()
            self._trigger_callback()
    
    def _on_listbox_focus_out(self, event):
        """Cuando el listbox pierde el foco"""
        pass
    
    def _filter_items(self):
        """Filtrar items basado en el texto actual"""
        search_text = self.current_value.get().lower()

        if search_text:
            self.filtered_items = [
                item for item in self.all_items
                if search_text in item.lower()
            ]
        else:
            self.filtered_items = self.all_items.copy()

        self._update_listbox()

        if self.filtered_items:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self.listbox.see(0)
    
    def _update_listbox(self):
        """Actualizar el Listbox con items filtrados"""
        self.listbox.delete(0, tk.END)
        for item in self.filtered_items:
            self.listbox.insert(tk.END, item)
        
        self.last_hover_index = -1
    
    def _show_dropdown(self):
        """Mostrar dropdown"""
        if self.dropdown_visible or not self.filtered_items:
            return
        
        toplevel = self.parent.winfo_toplevel()
        
        x = self.entry.winfo_rootx() - toplevel.winfo_rootx()
        y = self.entry.winfo_rooty() - toplevel.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        
        self.dropdown_frame.place(x=x, y=y, width=width, height=250)
        self.dropdown_frame.lift()
        self.dropdown_visible = True
        
        self.listbox.selection_clear(0, tk.END)
        
        if self.filtered_items:
            self.listbox.see(0)
    
    def _hide_dropdown(self):
        """Ocultar el dropdown"""
        if self.dropdown_visible:
            self.dropdown_frame.place_forget()
            self.dropdown_visible = False
    
    def _hide_dropdown_and_focus_entry(self):
        """Ocultar dropdown y enfocar entry"""
        current_selection = self.get()
        self._hide_dropdown()
        self.entry.focus_set()
        self.entry.icursor(tk.END)
        
        if current_selection:
            self.current_value.set(current_selection)
    
    def _toggle_dropdown(self):
        """Alternar visibilidad del dropdown"""
        if self.dropdown_visible:
            self._hide_dropdown_and_focus_entry()
        else:
            if not self.dropdown_visible:
                self._show_dropdown()
    
    def _on_listbox_select(self, event):
        """Cuando se selecciona un item del Listbox"""
        try:
            selection = self.listbox.curselection()
            if selection:
                selected_item = self.listbox.get(selection[0])
                self.current_value.set(selected_item)
                self.parent.after(10, self._remove_cursor)
        except:
            pass
    
    def _remove_cursor(self):
        """Quitar el cursor de escritura del entry"""
        self.entry.selection_clear()
        self.entry.icursor(tk.END)
    
    def _on_entry_focus_in(self, event):
        """Cuando el Entry recibe foco"""
        self.entry.selection_range(0, tk.END)
    
    def _on_entry_focus_out(self, event):
        """Cuando el Entry pierde foco"""
        def hide():
            if self.dropdown_visible:
                focused_widget = self.parent.winfo_toplevel().focus_get()
                if focused_widget != self.listbox and focused_widget != self.dropdown_btn:
                    self._hide_dropdown_and_focus_entry()
        
        self.parent.after(150, hide)
    
    def _trigger_callback(self):
        """Ejecutar callback si está definido"""
        if self.on_select_callback:
            self.on_select_callback(self.current_value.get())
    
    def _clean_input(self, text):
        """Limpiar espacios del texto de entrada"""
        text = text.strip()
        text = ' '.join(text.split())
        return text
    
    # Métodos públicos
    def get(self):
        """Obtener valor actual"""
        return self._clean_input(self.current_value.get())
    
    def set(self, value):
        """Establecer valor"""
        cleaned_value = self._clean_input(value)
        self.current_value.set(cleaned_value)
        self.parent.after(10, self._remove_cursor)
    
    def set_items(self, new_items):
        """Actualizar la lista de items"""
        self.all_items = new_items.copy()
        self.filtered_items = new_items.copy()
        self._update_listbox()
    
    def pack(self, **kwargs):
        """Emular método pack del Frame"""
        return self.main_frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Emular método grid del Frame"""
        return self.main_frame.grid(**kwargs)
    
    def place(self, **kwargs):
        """Emular método place del Frame"""
        return self.main_frame.place(**kwargs)
    
    def focus_set(self):
        """Enfocar el Entry"""
        self.entry.focus_set()
    
    def destroy(self):
        """Destruir todos los widgets"""
        try:
            self.parent.winfo_toplevel().unbind('<Button-1>')
        except:
            pass
        self.main_frame.destroy()
        self.dropdown_frame.destroy()