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
        self.ignore_focus_out = False  # Nueva variable para controlar el foco
        
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
        """Configurar los eventos con mejoras de accesibilidad"""
        # Bindings del Entry
        self.entry.bind('<KeyRelease>', self._on_key_release)
        self.entry.bind('<Return>', self._on_enter)
        self.entry.bind('<Down>', lambda e: self._show_dropdown_and_focus_listbox())
        self.entry.bind('<Up>', lambda e: self._show_dropdown_and_focus_listbox())
        self.entry.bind('<FocusIn>', self._on_entry_focus_in)
        self.entry.bind('<FocusOut>', self._on_entry_focus_out)
        self.entry.bind('<Tab>', self._on_entry_tab)
        
        # ✅ Binding para Ctrl+Space
        self.entry.bind('<Control-space>', self._on_ctrl_space)
        self.entry.bind('<Control-KeyPress-space>', self._on_ctrl_space)
        
        # Bindings del Listbox
        self.listbox.bind('<<ListboxSelect>>', self._on_listbox_select)
        self.listbox.bind('<Button-1>', self._on_listbox_click)  # ✅ NUEVO: Click simple
        self.listbox.bind('<Double-Button-1>', self._on_double_click)
        self.listbox.bind('<Return>', self._on_listbox_enter)
        self.listbox.bind('<Escape>', lambda e: self._hide_dropdown_and_focus_entry())
        self.listbox.bind('<KeyRelease>', self._filter_from_listbox)
        self.listbox.bind('<Up>', self._on_listbox_arrow_key)
        self.listbox.bind('<Down>', self._on_listbox_arrow_key)
        self.listbox.bind('<Tab>', self._on_listbox_tab)
        self.listbox.bind('<FocusOut>', self._on_listbox_focus_out)  # ✅ NUEVO: Foco fuera del listbox
        
        # ✅ NUEVO: Bindings para efecto hover
        self.listbox.bind('<Motion>', self._on_mouse_motion)
        self.listbox.bind('<Leave>', self._on_mouse_leave)
        
        # Bindings del botón dropdown
        self.dropdown_btn.bind('<Tab>', self._on_dropdown_btn_tab)
        
        # ✅ NUEVO: Binding global para detectar clicks fuera del combobox
        self.parent.winfo_toplevel().bind('<Button-1>', self._on_global_click)
    
    def _on_global_click(self, event):
        """Detectar clicks fuera del combobox"""
        # Verificar si el click fue fuera del combobox
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
        
        # Verificar si el click fue fuera del área del combobox
        click_in_entry = (entry_x1 <= event.x_root <= entry_x2 and 
                         entry_y1 <= event.y_root <= entry_y2)
        click_in_dropdown = (dropdown_x1 <= event.x_root <= dropdown_x2 and 
                            dropdown_y1 <= event.y_root <= dropdown_y2)
        click_in_dropdown_btn = (self.dropdown_btn.winfo_rootx() <= event.x_root <= self.dropdown_btn.winfo_rootx() + self.dropdown_btn.winfo_width() and
                                self.dropdown_btn.winfo_rooty() <= event.y_root <= self.dropdown_btn.winfo_rooty() + self.dropdown_btn.winfo_height())
        
        if not (click_in_entry or click_in_dropdown or click_in_dropdown_btn):
            # Click fuera del combobox, ocultar dropdown pero mantener selección
            self._hide_dropdown_and_focus_entry()
    
    def _on_listbox_click(self, event):
        """✅ NUEVO: Manejar click simple en el listbox"""
        # Obtener el índice clickeado
        index = self.listbox.nearest(event.y)
        if 0 <= index < self.listbox.size():
            # Seleccionar el item
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            
            # Actualizar el entry con la selección
            selected_item = self.listbox.get(index)
            self.current_value.set(selected_item)
            
            # ✅ NO ocultar el dropdown - mantenerlo visible para posible doble click
            # Solo actualizar y mantener la selección
    
    def _on_double_click(self, event):
        """✅ MEJORADO: Doble click para seleccionar y cerrar"""
        # Obtener el índice clickeado
        index = self.listbox.nearest(event.y)
        if 0 <= index < self.listbox.size():
            # Seleccionar el item
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            
            # Actualizar el entry con la selección
            selected_item = self.listbox.get(index)
            self.current_value.set(selected_item)
            
            # Ocultar dropdown y ejecutar callback
            self._hide_dropdown_and_focus_entry()
            self._trigger_callback()
    
    def _on_listbox_focus_out(self, event):
        """✅ NUEVO: Cuando el listbox pierde el foco"""
        # No hacer nada inmediatamente, dejar que _on_global_click maneje esto
        pass

    def _on_ctrl_space(self, event):
        """Filtrar y mostrar dropdown con Ctrl+Space"""
        self._filter_items()
        self._show_dropdown()
        return "break"
    
    def _on_mouse_motion(self, event):
        """Efecto hover cuando el mouse se mueve sobre el listbox"""
        if not self.dropdown_visible:
            return
            
        index = self.listbox.nearest(event.y)
        
        if 0 <= index < self.listbox.size() and index != self.last_hover_index:
            self._remove_hover_effect()
            self._apply_hover_effect(index)
            self.last_hover_index = index
    
    def _on_mouse_leave(self, event):
        """Remover efecto hover cuando el mouse sale del listbox"""
        self._remove_hover_effect()
        self.last_hover_index = -1
    
    def _apply_hover_effect(self, index):
        """Aplicar efecto hover a un índice específico"""
        if index not in self.listbox.curselection():
            self.listbox.itemconfig(index, {'bg': '#e6f3ff', 'fg': 'black'})
    
    def _remove_hover_effect(self):
        """Remover efecto hover de todos los items"""
        if self.last_hover_index != -1 and self.last_hover_index < self.listbox.size():
            if self.last_hover_index not in self.listbox.curselection():
                self.listbox.itemconfig(self.last_hover_index, {
                    'bg': self.listbox.cget('bg'), 
                    'fg': self.listbox.cget('fg')
                })
    
    def _remove_all_hover_effects(self):
        """Remover todos los efectos hover del listbox"""
        for i in range(self.listbox.size()):
            if i not in self.listbox.curselection():
                self.listbox.itemconfig(i, {
                    'bg': self.listbox.cget('bg'), 
                    'fg': self.listbox.cget('fg')
                })
        self.last_hover_index = -1
    
    def _on_key_release(self, event):
        """Cuando se escribe en el Entry"""
        if event.keysym in ['Return', 'Escape', 'Up', 'Down']:
            return
        
        self._filter_items()
        
        if self.current_value.get() and not self.dropdown_visible:
            self._show_dropdown()
    
    def _filter_from_listbox(self, event):
        """Filtrar desde el Listbox mismo"""
        if event.keysym in ['Return', 'Escape', 'Up', 'Down', 'Tab']:
            return
        
        try:
            selection = self.listbox.curselection()
            if selection:
                current_text = self.listbox.get(selection[0])
                if event.keysym not in ['Up', 'Down']:
                    self.current_value.set(current_text)
                    self._filter_items()
        except:
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
    
    def _update_listbox(self):
        """Actualizar el Listbox con items filtrados"""
        self.listbox.delete(0, tk.END)
        for item in self.filtered_items:
            self.listbox.insert(tk.END, item)
        
        self.last_hover_index = -1
    
    def _show_dropdown(self):
        """Mostrar el dropdown"""
        if self.dropdown_visible or not self.filtered_items:
            return
        
        toplevel = self.parent.winfo_toplevel()
        
        x = self.entry.winfo_rootx() - toplevel.winfo_rootx()
        y = self.entry.winfo_rooty() - toplevel.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        
        self.dropdown_frame.place(x=x, y=y, width=width, height=250)
        self.dropdown_frame.lift()
        self.dropdown_visible = True
        
        # Limpiar selección previa
        self.listbox.selection_clear(0, tk.END)
        
        if self.filtered_items:
            self.listbox.see(0)
    
    def _show_dropdown_and_focus_listbox(self):
        """Mostrar dropdown y enfocar el listbox"""
        self._show_dropdown()
        if self.dropdown_visible:
            self.listbox.focus_set()
            if self.filtered_items:
                self.listbox.selection_set(0)
                self.listbox.activate(0)
    
    def _hide_dropdown(self):
        """Ocultar el dropdown"""
        if self.dropdown_visible:
            self.dropdown_frame.place_forget()
            self.dropdown_visible = False
            self._remove_all_hover_effects()
    
    def _hide_dropdown_and_focus_entry(self):
        """✅ MEJORADO: Ocultar dropdown pero mantener selección"""
        current_selection = self.get()
        self._hide_dropdown()
        self.entry.focus_set()
        self.entry.icursor(tk.END)
        
        # ✅ Mantener la selección actual en el entry
        if current_selection:
            self.current_value.set(current_selection)
    
    def _toggle_dropdown(self):
        """Alternar visibilidad del dropdown"""
        if self.dropdown_visible:
            self._hide_dropdown_and_focus_entry()
        else:
            self._show_dropdown_and_focus_listbox()
    
    def _on_listbox_select(self, event):
        """Cuando se selecciona un item del Listbox"""
        try:
            selection = self.listbox.curselection()
            if selection:
                selected_item = self.listbox.get(selection[0])
                self.current_value.set(selected_item)
                
                self.parent.after(10, self._remove_cursor)
                self._remove_all_hover_effects()
                
        except:
            pass
    
    def _remove_cursor(self):
        """Quitar el cursor de escritura del entry"""
        self.entry.selection_clear()
        self.entry.icursor(tk.END)
    
    def _on_listbox_enter(self, event):
        """Enter en el Listbox"""
        self._on_listbox_select(event)
        self._hide_dropdown_and_focus_entry()
        self._trigger_callback()
    
    def _on_listbox_arrow_key(self, event):
        """Manejar teclas de flecha en el Listbox"""
        self._remove_all_hover_effects()
        
        if event.keysym == 'Up':
            current_index = self.listbox.curselection()
            if current_index and current_index[0] > 0:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(current_index[0] - 1)
                self.listbox.activate(current_index[0] - 1)
                self.listbox.see(current_index[0] - 1)
        elif event.keysym == 'Down':
            current_index = self.listbox.curselection()
            last_index = self.listbox.size() - 1
            if current_index and current_index[0] < last_index:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(current_index[0] + 1)
                self.listbox.activate(current_index[0] + 1)
                self.listbox.see(current_index[0] + 1)
    
    def _on_enter(self, event):
        """Enter en el Entry"""
        current_text = self.current_value.get()
        if current_text:
            matching_items = [item for item in self.all_items if current_text.lower() in item.lower()]
            if matching_items:
                exact_match = [item for item in matching_items if item.lower() == current_text.lower()]
                if exact_match:
                    self.current_value.set(exact_match[0])
                else:
                    self.current_value.set(matching_items[0])
                self._trigger_callback()
        
        self._hide_dropdown()
        self.parent.after(10, self._remove_cursor)
    
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
    
    def _on_entry_tab(self, event):
        """Manejar Tab en el Entry"""
        if self.dropdown_visible:
            self.listbox.focus_set()
            if self.filtered_items:
                self.listbox.selection_set(0)
                self.listbox.activate(0)
            return "break"
    
    def _on_listbox_tab(self, event):
        """Manejar Tab en el Listbox"""
        self._hide_dropdown_and_focus_entry()
        self.parent.after(10, self._remove_cursor)
    
    def _on_dropdown_btn_tab(self, event):
        """Manejar Tab en el botón dropdown"""
        pass
    
    def _trigger_callback(self):
        """Ejecutar callback si está definido"""
        if self.on_select_callback:
            self.on_select_callback(self.current_value.get())
    
    # Métodos públicos
    def get(self):
        """Obtener valor actual"""
        return self.current_value.get()
    
    def set(self, value):
        """Establecer valor"""
        self.current_value.set(value)
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
        # ✅ NUEVO: Remover binding global
        try:
            self.parent.winfo_toplevel().unbind('<Button-1>')
        except:
            pass
        self.main_frame.destroy()
        self.dropdown_frame.destroy()