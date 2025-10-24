import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional, Callable
import subprocess
import threading

try:
    from ui.components import BotonRedondeado, AppStyles
except ImportError:
    from components import BotonRedondeado, AppStyles

class LogDialog:
    def __init__(self, parent, log_content: str, current_analysis: dict = None, apk_name: str = ""):
        self.parent = parent
        self.log_content = log_content
        self.current_analysis = current_analysis or {}
        self.apk_name = apk_name
        self.styles = AppStyles()
        self.filter_var = tk.StringVar(value="todos")
        
    def mostrar(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Comandos de Análisis")
        self.dialog.geometry("1000x800")
        self.dialog.configure(bg=self.styles.COLORS['primary_bg'])
        self.dialog.transient(self.parent)
        
        self._crear_interfaz()
        self._aplicar_filtro("todos")
        
    def _crear_interfaz(self):
        main_frame = tk.Frame(self.dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        title_label = tk.Label(
            main_frame,
            text="Comandos del Análisis",
            font=self.styles.FONTS['subtitle'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        )
        title_label.pack(anchor="w", pady=(0, 15))
        
        filter_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        filter_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            filter_frame,
            text="Filtrar por:",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))
        
        filters = [
            ("Todos", "todos"),
            ("AAPT", "aapt"),
            ("APKSigner", "apksigner"),
            ("JarSigner", "jarsigner"),
            ("PCI DSS", "pci_dss")  
        ]
        
        for text, value in filters:
            rb = tk.Radiobutton(
                filter_frame,
                text=text,
                variable=self.filter_var,
                value=value,
                command=lambda v=value: self._aplicar_filtro(v),
                font=self.styles.FONTS['normal'],
                bg=self.styles.COLORS['primary_bg'],
                fg=self.styles.COLORS['text_primary'],
                selectcolor=self.styles.COLORS['secondary_bg']
            )
            rb.pack(side="left", padx=10)
        
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            text_frame,
            wrap="word",
            font=self.styles.FONTS['monospace'],
            bg=self.styles.COLORS['secondary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=10,
            pady=10
        )
        self.log_text.pack(fill="both", expand=True)
        
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=(15, 0))
        
        BotonRedondeado(
            btn_frame,
            "Copiar Todo",
            self._copiar_todo,
            width=120,
            style='secondary'
        ).pack(side="left", padx=5)
        
        BotonRedondeado(
            btn_frame,
            "Exportar",
            self._exportar_log,
            width=120,
            style='secondary'
        ).pack(side="left", padx=5)
        
        BotonRedondeado(
            btn_frame,
            "Cerrar",
            self.dialog.destroy,
            width=100,
            style='primary'
        ).pack(side="right", padx=5)
    
    def _aplicar_filtro(self, filtro):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        
        if filtro == "todos":
            contenido = self._obtener_contenido_completo()
        elif filtro == "aapt":
            contenido = self._filtrar_seccion("=== AAPT DUMP BADGING ===")
        elif filtro == "apksigner":
            contenido = self._filtrar_seccion("=== APKSIGNER VERIFY ===")
        elif filtro == "jarsigner":
            contenido = self._filtrar_seccion("=== JARSIGNER VERIFY ===")
        elif filtro == "pci_dss":
            contenido = self._obtener_analisis_pci_dss()
        else:
            contenido = self.log_content
        
        self.log_text.insert(1.0, contenido)
        self.log_text.config(state='disabled')
    
    def _filtrar_seccion(self, seccion_buscada):
        # ✅ CORREGIDO: Buscar la sección exacta
        inicio = self.log_content.find(seccion_buscada)
        if inicio == -1:
            return f"No se encontró la sección: {seccion_buscada}"
        
        # Buscar la siguiente sección
        secciones = [
            "=== AAPT DUMP BADGING ===", 
            "=== APKSIGNER VERIFY ===", 
            "=== JARSIGNER VERIFY ===",
            "🛡️ ANÁLISIS PCI DSS DETALLADO",
            "═" * 80  # Línea separadora
        ]
        
        siguiente_inicio = -1
        for seccion in secciones:
            if seccion != seccion_buscada:
                siguiente = self.log_content.find(seccion, inicio + 1)
                if siguiente != -1 and (siguiente_inicio == -1 or siguiente < siguiente_inicio):
                    siguiente_inicio = siguiente
        
        # Si encontramos siguiente sección, cortar ahí
        if siguiente_inicio != -1:
            # Buscar el último salto de línea antes de la siguiente sección
            ultimo_salto = self.log_content.rfind('\n', inicio, siguiente_inicio)
            if ultimo_salto != -1:
                return self.log_content[inicio:ultimo_salto]
            else:
                return self.log_content[inicio:siguiente_inicio]
        else:
            return self.log_content[inicio:]
    
    def _obtener_contenido_completo(self):
        contenido_completo = ""
        
        secciones_logs = [
            "=== AAPT DUMP BADGING ===",
            "=== APKSIGNER VERIFY ===", 
            "=== JARSIGNER VERIFY ==="
        ]
        
        for seccion in secciones_logs:
            inicio = self.log_content.find(seccion)
            if inicio != -1:
                # Buscar el inicio de la siguiente sección
                siguiente_inicio = -1
                for otra_seccion in secciones_logs:
                    if otra_seccion != seccion:
                        siguiente = self.log_content.find(otra_seccion, inicio + 1)
                        if siguiente != -1 and (siguiente_inicio == -1 or siguiente < siguiente_inicio):
                            siguiente_inicio = siguiente
                
                # Si encontramos siguiente sección, cortar ahí, sino tomar hasta el final
                if siguiente_inicio != -1:
                    contenido_seccion = self.log_content[inicio:siguiente_inicio]
                else:
                    contenido_seccion = self.log_content[inicio:]
                
                contenido_completo += contenido_seccion + "\n\n"
        
        # ✅ CORREGIDO: Si no encontramos secciones, usar el contenido completo
        if not contenido_completo.strip():
            contenido_completo = self.log_content
        
        # ✅ AGREGAR PCI DSS SI ESTÁ DISPONIBLE
        if self.current_analysis and 'pci_analysis' in self.current_analysis:
            pci_analysis = self.current_analysis['pci_analysis']
            
            if isinstance(pci_analysis, dict):
                # Verificar si PCI DSS ya está en el contenido
                if "ANÁLISIS PCI DSS" not in contenido_completo:
                    contenido_completo += "═" * 80 + "\n"
                    contenido_completo += "=== ANÁLISIS PCI DSS COMPLETO ===\n"
                    contenido_completo += "═" * 80 + "\n\n"
                    
                    if 'reporte_completo' in pci_analysis:
                        contenido_completo += pci_analysis['reporte_completo']
                    else:
                        contenido_completo += self._generar_reporte_pci_detallado(pci_analysis)
        
        return contenido_completo

    def _generar_reporte_pci_detallado(self, pci_analysis: dict) -> str:
        reporte = ""
        reporte += f"Estado de Cumplimiento: {pci_analysis.get('cumplimiento_general', 'N/A')}\n"
        reporte += f"Puntuación: {pci_analysis.get('puntuacion_total', 'N/A')}%\n"
        reporte += f"Nivel de Riesgo: {pci_analysis.get('nivel_riesgo', 'N/A')}\n\n"
        reporte += "✅ REQUISITOS CUMPLIDOS:\n"
        requisitos_cumplidos = pci_analysis.get('requisitos_cumplidos', [])
        if requisitos_cumplidos:
            for req in requisitos_cumplidos:
                reporte += f"  • {req}\n"
        else:
            reporte += "  No se encontraron requisitos cumplidos\n"
        
        reporte += "\n"
        reporte += "❌ REQUISITOS NO CUMPLIDOS:\n"
        requisitos_no_cumplidos = pci_analysis.get('requisitos_no_cumplidos', [])
        if requisitos_no_cumplidos:
            for req in requisitos_no_cumplidos:
                reporte += f"  • {req}\n"
        else:
            reporte += "  Todos los requisitos analizados están cumplidos\n"
        
        reporte += "\n"
        reporte += "🔍 HALLAZGOS CRÍTICOS:\n"
        hallazgos_criticos = pci_analysis.get('hallazgos_criticos', [])
        if hallazgos_criticos:
            for hallazgo in hallazgos_criticos:
                nivel_emoji = "🔴" if hallazgo.get('nivel') == 'ALTO' else "🟡" if hallazgo.get('nivel') == 'MEDIO' else "🔵"
                reporte += f"  {nivel_emoji} [{hallazgo.get('nivel', 'N/A')}] {hallazgo.get('titulo', 'Hallazgo')}\n"
                reporte += f"     Descripción: {hallazgo.get('descripcion', 'N/A')}\n"
                reporte += f"     Requisito: {hallazgo.get('requisito', 'N/A')}\n"
                reporte += f"     Impacto: {hallazgo.get('impacto', 'N/A')}\n"
                reporte += f"     Recomendación: {hallazgo.get('recomendacion', 'N/A')}\n\n"
        else:
            reporte += "  No se encontraron hallazgos críticos\n"
        
        reporte += "\n"
        
        reporte += "🚨 HALLAZGOS DE ALTO RIESGO:\n"
        hallazgos_altos = pci_analysis.get('hallazgos_altos', [])
        if hallazgos_altos:
            reporte += f"  Total: {len(hallazgos_altos)} hallazgos de ALTO riesgo encontrados\n"
        else:
            reporte += "  No se encontraron hallazgos de ALTO riesgo\n"
        
        reporte += "\n"
        
        reporte += "💡 RECOMENDACIONES:\n"
        recomendaciones = pci_analysis.get('recomendaciones', [])
        if recomendaciones:
            for rec in recomendaciones:
                reporte += f"  • {rec}\n"
        else:
            reporte += "  No hay recomendaciones específicas\n"
        
        reporte += "\n"
        reporte += "⚠️  NOTA: Este es un análisis automatizado. Para certificación PCI DSS completa,\n"
        reporte += "     se requiere auditoría por un QSA (Qualified Security Assessor) certificado.\n"
        
        return reporte

    def _obtener_analisis_pci_dss(self):
        if not self.current_analysis:
            return "=== ANÁLISIS PCI DSS ===\n\nNo hay análisis disponible"
        
        pci_analysis = self.current_analysis.get('pci_analysis')
        
        if not pci_analysis:
            return "=== ANÁLISIS PCI DSS ===\n\nNo se realizó análisis PCI DSS"
        if isinstance(pci_analysis, dict):
            if 'reporte_completo' in pci_analysis:
                return f"=== ANÁLISIS PCI DSS COMPLETO ===\n\n{pci_analysis['reporte_completo']}"
            else:
                return f"=== ANÁLISIS PCI DSS COMPLETO ===\n\n{self._generar_reporte_pci_detallado(pci_analysis)}"
        else:
            return f"=== ANÁLISIS PCI DSS COMPLETO ===\n\n{pci_analysis}"
        
    
    def _copiar_todo(self):
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(self.log_text.get(1.0, tk.END))
        tk.messagebox.showinfo("Copiado", "Log copiado al portapapeles")
    
    def _generar_nombre_archivo(self):
        if self.apk_name:
            nombre_base = Path(self.apk_name).stem
            nombre_base = nombre_base.replace('-unsigned', '')
            nombre_base = nombre_base.replace('-signed', '')
            nombre_base = nombre_base.replace(' ', '_')
            
            if len(nombre_base) > 30:
                nombre_base = nombre_base[:30]
            
            return f"log_analisis_{nombre_base}.txt"
        else:
            return "log_analisis.txt"
    
    def _exportar_log(self):
        from tkinter import filedialog
        
        nombre_por_defecto = self._generar_nombre_archivo()
        
        archivo = filedialog.asksaveasfilename(
            title="Exportar log",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt")],
            initialfile=nombre_por_defecto
        )
        
        if archivo:
            try:
                with open(archivo, "w", encoding="utf-8") as f:
                    f.write(self.log_text.get(1.0, tk.END))
                tk.messagebox.showinfo("Éxito", f"Log exportado a:\n{archivo}")
            except Exception as e:
                tk.messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")


class InstallDialog:
    def __init__(self, parent, apk_path: Path, package_name: str = "", platform_tools_path: str = ""):
        self.parent = parent
        self.apk_path = apk_path
        self.package_name = package_name
        self.platform_tools_path = platform_tools_path
        self.styles = AppStyles()
        self.resultado = None
        
    def mostrar(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Instalar/Desinstalar APK")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=self.styles.COLORS['primary_bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._crear_interfaz()
        self._centrar_dialogo()
        
    def _crear_interfaz(self):
        main_frame = tk.Frame(self.dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        title_label = tk.Label(
            main_frame,
            text=f"Gestión de APK: {self.apk_path.name}",
            font=self.styles.FONTS['subtitle'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            wraplength=450
        )
        title_label.pack(anchor="w", pady=(0, 20))
        
        install_frame = tk.LabelFrame(
            main_frame,
            text=" Instalar APK ",
            font=self.styles.FONTS['normal_bold'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=15,
            pady=15
        )
        install_frame.pack(fill="x", pady=(0, 15))
        
        install_info = tk.Label(
            install_frame,
            text="Instalar la APK actual en el dispositivo conectado",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_secondary'],
            justify="left"
        )
        install_info.pack(anchor="w", pady=(0, 10))
        
        BotonRedondeado(
            install_frame,
            "📲 Instalar APK",
            self._instalar_apk,
            width=120,
            style='success'
        ).pack(side="left", padx=5)
        
        uninstall_frame = tk.LabelFrame(
            main_frame,
            text=" Desinstalar Aplicación ",
            font=self.styles.FONTS['normal_bold'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary'],
            padx=15,
            pady=15
        )
        uninstall_frame.pack(fill="x", pady=(0, 15))
        
        if self.package_name:
            frame1 = tk.Frame(uninstall_frame, bg=self.styles.COLORS['primary_bg'])
            frame1.pack(fill="x", pady=(0, 10))
            
            tk.Label(
                frame1,
                text=f"Package: {self.package_name}",
                font=self.styles.FONTS['normal'],
                bg=self.styles.COLORS['primary_bg'],
                fg=self.styles.COLORS['text_primary']
            ).pack(side="left", padx=(0, 10))
            
            BotonRedondeado(
                frame1,
                "🗑️ Desinstalar",
                lambda: self._desinstalar_paquete(self.package_name),
                width=100,
                style='danger'
            ).pack(side="right")
        
        frame2 = tk.Frame(uninstall_frame, bg=self.styles.COLORS['primary_bg'])
        frame2.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            frame2,
            text="Package personalizado:",
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))
        
        self.custom_package_entry = tk.Entry(
            frame2,
            font=self.styles.FONTS['normal'],
            width=25
        )
        self.custom_package_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.custom_package_entry.insert(0, "com.ejemplo.paquete")
        
        BotonRedondeado(
            frame2,
            "🗑️ Desinstalar",
            lambda: self._desinstalar_paquete(self.custom_package_entry.get().strip()),
            width=100,
            style='danger'
        ).pack(side="right")
        
        info_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        info_frame.pack(fill="x", pady=(15, 0))
        
        # ✅ VERIFICAR HERRAMIENTAS DISPONIBLES
        herramientas_disponibles, mensaje_herramientas = self._verificar_herramientas_disponibles()
        
        info_text = (
            "💡 Requisitos:\n"
            "• Dispositivo Android conectado vía USB\n"
            "• Depuración USB activada\n"
            "• Drivers ADB instalados\n"
            f"• Platform Tools: {self.platform_tools_path}\n\n"
            f"{mensaje_herramientas}"
        )
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=("Segoe UI", 9),
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_secondary'],
            justify="left",
            wraplength=450
        )
        info_label.pack(anchor="w")
        
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=(20, 0))
        
        BotonRedondeado(
            btn_frame,
            "Cerrar",
            self.dialog.destroy,
            width=100,
            style='secondary'
        ).pack(side="right")
    
    def _verificar_herramientas_disponibles(self):
        """Verificar si las herramientas necesarias están disponibles"""
        try:
            platform_path = Path(self.platform_tools_path)
            
            # Verificar ADB
            adb_path = platform_path / "adb.exe"
            if not adb_path.exists():
                adb_path = platform_path / "adb"
            
            if not adb_path.exists():
                return False, (
                    "❌ ADB no encontrado\n"
                    "🔗 Descarga: https://developer.android.com/studio/releases/platform-tools"
                )
            
            # Verificar AAPT
            aapt_path = platform_path / "aapt.exe"
            if not aapt_path.exists():
                aapt_path = platform_path / "aapt"
            
            if not aapt_path.exists():
                return False, (
                    "❌ AAPT no encontrado\n"
                    "🔗 Descarga: https://developer.android.com/studio/releases/build-tools"
                )
            
            # Verificar APKSigner
            apksigner_path = platform_path / "apksigner.bat"
            if not apksigner_path.exists():
                apksigner_path = platform_path / "apksigner"
            
            if not apksigner_path.exists():
                return False, (
                    "❌ APKSigner no encontrado\n"
                    "🔗 Descarga: https://developer.android.com/studio/releases/build-tools"
                )
            
            return True, "✅ Todas las herramientas están disponibles"
            
        except Exception as e:
            return False, f"❌ Error verificando herramientas: {str(e)}"
    
    def _crear_entry_solo_lectura(self, parent, width=40):
        entry = tk.Entry(
            parent,
            font=self.styles.FONTS['normal'],
            width=width,
            state='normal'
        )
        
        def bloquear_edicion(event):
            teclas_permitidas = ['Left', 'Right', 'Up', 'Down', 'Home', 'End', 
                               'Control_L', 'Control_R', 'Shift_L', 'Shift_R']
            
            if event.keysym in teclas_permitidas:
                return
            elif event.state & 0x4 and event.keysym == 'c':
                return
            else:
                return 'break'
        
        entry.bind('<Key>', bloquear_edicion)
        entry.config(state='readonly')
        
        return entry
    
    def _verificar_adb(self):
        try:
            adb_path = Path(self.platform_tools_path) / "adb"
            if not adb_path.exists():
                adb_path = Path(self.platform_tools_path) / "adb.exe"
            
            if not adb_path.exists():
                return False, ["ADB no encontrado"]
            
            result = subprocess.run(
                [str(adb_path), "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.strip().split('\n')[1:]
            devices = [line for line in lines if line.strip() and '\tdevice' in line]
            
            return len(devices) > 0, devices
            
        except Exception as e:
            return False, [f"Error: {str(e)}"]
    
    def _instalar_apk(self):
        # ✅ VERIFICAR HERRAMIENTAS ANTES DE PROCEDER
        herramientas_ok, mensaje_herramientas = self._verificar_herramientas_disponibles()
        if not herramientas_ok:
            messagebox.showerror(
                "Herramientas Faltantes", 
                f"No se pueden ejecutar las operaciones:\n\n{mensaje_herramientas}"
            )
            return
        
        adb_ok, devices = self._verificar_adb()
        
        if not adb_ok:
            messagebox.showerror(
                "Error ADB", 
                "No se pudo encontrar ADB o no hay dispositivos conectados.\n\n"
                "Verifica:\n"
                "• Que el dispositivo esté conectado\n"
                "• Que la depuración USB esté activada\n"
                "• Que los drivers ADB estén instalados"
            )
            return
        
        progress = tk.Toplevel(self.dialog)
        progress.title("Instalando APK")
        progress.geometry("300x150")
        progress.transient(self.dialog)
        progress.grab_set()
        
        tk.Label(
            progress,
            text="Instalando APK...",
            font=self.styles.FONTS['normal'],
            pady=20
        ).pack()
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(fill="x", padx=20, pady=10)
        progress_bar.start()
        
        def instalar():
            try:
                adb_path = Path(self.platform_tools_path) / "adb"
                if not adb_path.exists():
                    adb_path = Path(self.platform_tools_path) / "adb.exe"
                
                result = subprocess.run(
                    [str(adb_path), "install", "-r", str(self.apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                progress.destroy()
                
                if "Success" in result.stdout:
                    messagebox.showinfo("Éxito", "APK instalada correctamente")
                else:
                    messagebox.showerror("Error", f"Error en instalación:\n{result.stderr or result.stdout}")
                    
            except Exception as e:
                progress.destroy()
                messagebox.showerror("Error", f"Error durante la instalación: {str(e)}")
        
        threading.Thread(target=instalar, daemon=True).start()
    
    def _desinstalar_paquete(self, package_name):
        if not package_name or package_name == "com.ejemplo.paquete":
            messagebox.showwarning("Advertencia", "Ingresa un nombre de paquete válido")
            return
        
        # ✅ VERIFICAR HERRAMIENTAS ANTES DE PROCEDER
        herramientas_ok, mensaje_herramientas = self._verificar_herramientas_disponibles()
        if not herramientas_ok:
            messagebox.showerror(
                "Herramientas Faltantes", 
                f"No se pueden ejecutar las operaciones:\n\n{mensaje_herramientas}"
            )
            return
        
        adb_ok, devices = self._verificar_adb()
        
        if not adb_ok:
            messagebox.showerror(
                "Error ADB", 
                "No se pudo encontrar ADB o no hay dispositivos conectados."
            )
            return
        
        resultado = messagebox.askyesno(
            "Confirmar Desinstalación",
            f"¿Estás seguro de que quieres desinstalar el paquete?\n\n"
            f"Package: {package_name}\n\n"
            f"Esta acción no se puede deshacer."
        )
        
        if not resultado:
            return
        
        progress = tk.Toplevel(self.dialog)
        progress.title("Desinstalando")
        progress.geometry("300x150")
        progress.transient(self.dialog)
        progress.grab_set()
        
        tk.Label(
            progress,
            text=f"Desinstalando {package_name}...",
            font=self.styles.FONTS['normal'],
            pady=20
        ).pack()
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(fill="x", padx=20, pady=10)
        progress_bar.start()
        
        def desinstalar():
            try:
                adb_path = Path(self.platform_tools_path) / "adb"
                if not adb_path.exists():
                    adb_path = Path(self.platform_tools_path) / "adb.exe"
                
                result = subprocess.run(
                    [str(adb_path), "uninstall", package_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                progress.destroy()
                
                if "Success" in result.stdout:
                    messagebox.showinfo("Éxito", f"Paquete {package_name} desinstalado correctamente")
                else:
                    messagebox.showerror("Error", f"Error en desinstalación:\n{result.stderr or result.stdout}")
                    
            except Exception as e:
                progress.destroy()
                messagebox.showerror("Error", f"Error durante la desinstalación: {str(e)}")
        
        threading.Thread(target=desinstalar, daemon=True).start()
    
    def _centrar_dialogo(self):
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

class ToolsDialog:
    def __init__(self, parent, config_manager, tool_detector):
        self.parent = parent
        self.config_manager = config_manager
        self.tool_detector = tool_detector
        self.styles = AppStyles()
        self.resultado = None
        
    def mostrar(self) -> Optional[dict]:
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Configurar Herramientas")
        self.dialog.geometry("800x400")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg=self.styles.COLORS['primary_bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._crear_interfaz()
        self._cargar_config_actual()
        
        self.parent.wait_window(self.dialog)
        return self.resultado
    
    def _crear_interfaz(self):
        main_frame = tk.Frame(self.dialog, bg=self.styles.COLORS['primary_bg'], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        title_label = tk.Label(
            main_frame, 
            text="Rutas de Herramientas", 
            font=self.styles.FONTS['subtitle'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        )
        title_label.pack(anchor="w", pady=(0, 15))
        
        form_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        form_frame.pack(fill="x", pady=5)
        
        self._crear_campo_entrada(form_frame, "SDK Root:", 0)
        self._crear_campo_entrada(form_frame, "Build Tools:", 1)
        self._crear_campo_entrada(form_frame, "Platform Tools:", 2)
        self._crear_campo_entrada(form_frame, "JDK Bin:", 3)
        
        form_frame.columnconfigure(1, weight=1)
        
        btn_frame = tk.Frame(main_frame, bg=self.styles.COLORS['primary_bg'])
        btn_frame.pack(fill="x", pady=20)
        
        from .components import BotonRedondeado
        
        BotonRedondeado(
            btn_frame, 
            "Detectar Automáticamente", 
            self._detectar_automaticamente,
            width=180,
            style='secondary'
        ).pack(side="left", padx=5)
        
        BotonRedondeado(
            btn_frame, 
            "Cancelar", 
            self._cancelar,
            width=100,
            style='secondary'
        ).pack(side="right", padx=5)
        
        BotonRedondeado(
            btn_frame, 
            "Guardar", 
            self._guardar,
            width=100,
            style='success'
        ).pack(side="right", padx=5)
    
    def _crear_campo_entrada(self, parent, label_text, row):
        label = tk.Label(
            parent, 
            text=label_text,
            font=self.styles.FONTS['normal'],
            bg=self.styles.COLORS['primary_bg'],
            fg=self.styles.COLORS['text_primary']
        )
        label.grid(row=row, column=0, sticky="w", pady=8)
        
        entry = tk.Entry(
            parent, 
            width=50,
            font=self.styles.FONTS['normal'],
            relief="solid",
            bd=1
        )
        entry.grid(row=row, column=1, padx=8, pady=8, sticky="ew")
        
        from .components import BotonRedondeado
        btn_examinar = BotonRedondeado(
            parent,
            "Examinar",
            lambda: self._examinar_directorio(entry),
            width=80,
            height=28,
            style='secondary'
        )
        btn_examinar.grid(row=row, column=2, padx=5, pady=8)
        
        if "sdk" in label_text.lower():
            self.sdk_entry = entry
        elif "build" in label_text.lower():
            self.build_entry = entry
        elif "platform" in label_text.lower():
            self.platform_entry = entry
        elif "jdk" in label_text.lower():
            self.jdk_entry = entry
    
    def _examinar_directorio(self, entry_widget):
        from tkinter import filedialog
        directorio = filedialog.askdirectory(title="Seleccionar directorio")
        if directorio:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, directorio)
    
    def _cargar_config_actual(self):
        config = self.config_manager.cargar_config()
        detectado = self.tool_detector.detectar_herramientas()
        
        self.sdk_entry.insert(0, config.get("sdk_root") or str(detectado.get("sdk_root", "")))
        self.build_entry.insert(0, config.get("build_tools") or str(detectado.get("build_tools", "")))
        self.platform_entry.insert(0, config.get("platform_tools") or str(detectado.get("platform_tools", "")))
        self.jdk_entry.insert(0, config.get("jdk_bin") or str(detectado.get("jdk_bin", "")))
    
    def _detectar_automaticamente(self):
        detectado = self.tool_detector.detectar_herramientas()
        
        if not self.sdk_entry.get() and detectado.get("sdk_root"):
            self.sdk_entry.delete(0, tk.END)
            self.sdk_entry.insert(0, str(detectado["sdk_root"]))
        
        if not self.build_entry.get() and detectado.get("build_tools"):
            self.build_entry.delete(0, tk.END)
            self.build_entry.insert(0, str(detectado["build_tools"]))
        
        if not self.platform_entry.get() and detectado.get("platform_tools"):
            self.platform_entry.delete(0, tk.END)
            self.platform_entry.insert(0, str(detectado["platform_tools"]))
        
        if not self.jdk_entry.get() and detectado.get("jdk_bin"):
            self.jdk_entry.delete(0, tk.END)
            self.jdk_entry.insert(0, str(detectado["jdk_bin"]))
    
    def _guardar(self):
        self.resultado = {
            "sdk_root": self.sdk_entry.get().strip(),
            "build_tools": self.build_entry.get().strip(),
            "platform_tools": self.platform_entry.get().strip(),
            "jdk_bin": self.jdk_entry.get().strip()
        }
        self.dialog.destroy()
    
    def _cancelar(self):
        self.resultado = None
        self.dialog.destroy()