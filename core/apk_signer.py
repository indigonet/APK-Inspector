import os
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
import sys
import tkinter as tk
from tkinter import filedialog

class APKSigner:
    def __init__(self, logger=None):
        self.logger = logger
    
    def _log(self, message: str, level: str = "info"):
        if self.logger:
            if level == "info":
                self.logger.log_info(message)
            elif level == "error":
                self.logger.log_error(message)
            elif level == "warning":
                self.logger.log_warning(message)

    def ejecutar_comando(self, comando: List[str], timeout: int = 60) -> Tuple[int, str]:
        try:
            self._log(f"Ejecutando: {' '.join(comando)}")
            
            proc = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="ignore"
            )
            
            output = proc.stdout
            if proc.stderr:
                output += f"\nSTDERR: {proc.stderr}"
                
            self._log(f"Comando exitoso: {proc.returncode}")
            return proc.returncode, output
            
        except subprocess.TimeoutExpired:
            error_msg = f"Tiempo de espera agotado ({timeout}s)"
            self._log(error_msg, "error")
            return 1, error_msg
            
        except FileNotFoundError:
            error_msg = f"Comando no encontrado: {comando[0]}"
            self._log(error_msg, "error")
            return 1, error_msg
            
        except Exception as e:
            error_msg = f"Error ejecutando comando: {str(e)}"
            self._log(error_msg, "error")
            return 1, error_msg
    
    def encontrar_apksigner(self, build_tools_path: str) -> Optional[Path]:
        if not build_tools_path:
            self._log("Ruta de build-tools no configurada", "error")
            return None
            
        build_path = Path(build_tools_path)
        
        apksigner_candidates = []
        
        if sys.platform.startswith("win"):
            apksigner_candidates = [
                build_path / "apksigner.bat",
                build_path / "apksigner",
            ]
        else:
            apksigner_candidates = [
                build_path / "apksigner",
                build_path / "apksigner.jar",
            ]
        
        for candidate in apksigner_candidates:
            if candidate.exists():
                self._log(f"apksigner encontrado: {candidate}")
                return candidate
        
        self._log(f"apksigner no encontrado en: {build_path}", "error")
        return None
    
    def seleccionar_destino_firma(self, apk_path: Path, parent_window=None) -> Optional[Path]:
        """Dialogo para seleccionar donde guardar el APK firmado"""
        try:
            # Sugerir nombre por defecto
            nombre_sugerido = f"{apk_path.stem}-signed{apk_path.suffix}"
            
            # Dialogo para guardar archivo
            archivo_destino = filedialog.asksaveasfilename(
                parent=parent_window,
                title="Guardar APK firmado como...",
                initialfile=nombre_sugerido,
                defaultextension=apk_path.suffix,
                filetypes=[("APK files", f"*{apk_path.suffix}"), ("Todos los archivos", "*.*")]
            )
            
            if archivo_destino:
                destino = Path(archivo_destino)
                self._log(f"Destino seleccionado: {destino}")
                return destino
            else:
                self._log("Usuario canceló la selección de destino")
                return None
                
        except Exception as e:
            self._log(f"Error seleccionando destino: {str(e)}", "error")
            return None
    
    def firmar_apk(self, apk_path: Path, jks_path: Path, password: str, build_tools_path: str, alias: str = None, parent_window=None) -> Tuple[bool, str]:
        try:
            if not apk_path.exists():
                return False, f"APK no encontrado: {apk_path}"
            
            if not jks_path.exists():
                return False, f"Keystore JKS no encontrado: {jks_path}"
            
            if not password:
                return False, "La contraseña no puede estar vacía"
            
            apksigner_bin = self.encontrar_apksigner(build_tools_path)
            if not apksigner_bin:
                return False, "apksigner no encontrado en build-tools"
            
            # ✅ NUEVO: Preguntar donde guardar el APK firmado
            apk_signed_path = self.seleccionar_destino_firma(apk_path, parent_window)
            if not apk_signed_path:
                return False, "Operación cancelada por el usuario"
            
            # Verificar que no estamos sobreescribiendo el archivo original
            if apk_signed_path.resolve() == apk_path.resolve():
                return False, "No puedes sobreescribir el archivo original. Elige un nombre diferente."
            
            self._log(f"Firmando APK: {apk_path.name} -> {apk_signed_path.name}")
            
            comando = [
                str(apksigner_bin),
                "sign",
                "--ks", str(jks_path),
                "--ks-pass", f"pass:{password}",
                "--out", str(apk_signed_path),
                str(apk_path)
            ]
            
            if alias:
                comando.extend(["--ks-key-alias", alias])
            
            self._log(f"Iniciando firma de APK: {apk_path.name}")
            
            rc, output = self.ejecutar_comando(comando, timeout=120)
            
            if rc == 0:
                if apk_signed_path.exists():
                    file_size = apk_signed_path.stat().st_size
                    self._log(f"APK firmado creado: {apk_signed_path} ({file_size} bytes)")
                    
                    # Verificar la firma del archivo creado
                    verificacion = self.verificar_firma(apk_signed_path, build_tools_path)
                    if verificacion[0]:
                        return True, f"APK firmado y verificado correctamente:\n{apk_signed_path}"
                    else:
                        return False, f"APK firmado pero falló la verificación:\n{verificacion[1]}"
                else:
                    return False, "Error: El archivo firmado no se creó"
            else:
                # Limpiar archivo si falló
                if apk_signed_path.exists():
                    apk_signed_path.unlink()
                return False, f"Error en firma: {output}"
                
        except Exception as e:
            error_msg = f"Error durante la firma: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def verificar_firma(self, apk_path: Path, build_tools_path: str) -> Tuple[bool, str]:
        try:
            if not apk_path.exists():
                return False, "APK no encontrado"
            
            apksigner_bin = self.encontrar_apksigner(build_tools_path)
            if not apksigner_bin:
                return False, "apksigner no encontrado"
            
            comando = [
                str(apksigner_bin),
                "verify",
                "--verbose",
                str(apk_path)
            ]
            
            rc, output = self.ejecutar_comando(comando, timeout=30)
            
            if rc == 0:
                return True, "Firma verificada correctamente"
            else:
                return False, output
                
        except Exception as e:
            error_msg = f"Error verificando firma: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def crear_keystore(self, destino: Path, password: str, alias: str, validity_days: int = 365, parent_window=None) -> Tuple[bool, str]:
        """Crear un nuevo keystore JKS"""
        try:
            if destino.exists():
                return False, "El archivo ya existe. Elige un nombre diferente."
            
            # Buscar keytool
            keytool_cmd = self._encontrar_keytool()
            if not keytool_cmd:
                return False, "keytool no encontrado. Asegúrate de que JDK esté instalado."
            
            # Datos por defecto para el certificado (en producción pedir más datos)
            dname = f"CN=Android, OU=Android, O=Unknown, L=Unknown, ST=Unknown, C=US"
            
            comando = [
                keytool_cmd,
                "-genkey",
                "-v",
                "-keystore", str(destino),
                "-alias", alias,
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", str(validity_days),
                "-storepass", password,
                "-keypass", password,
                "-dname", dname
            ]
            
            self._log(f"Creando keystore: {destino.name}")
            
            rc, output = self.ejecutar_comando(comando, timeout=30)
            
            if rc == 0:
                if destino.exists():
                    return True, f"Keystore creado correctamente:\n{destino}"
                else:
                    return False, "Error: El keystore no se creó"
            else:
                if destino.exists():
                    destino.unlink()
                return False, f"Error creando keystore: {output}"
                
        except Exception as e:
            error_msg = f"Error creando keystore: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def _encontrar_keytool(self) -> Optional[str]:
        """Encontrar el comando keytool"""
        try:
            # En Windows, buscar en JAVA_HOME
            if sys.platform.startswith("win"):
                java_home = os.environ.get("JAVA_HOME")
                if java_home:
                    keytool_path = Path(java_home) / "bin" / "keytool.exe"
                    if keytool_path.exists():
                        return str(keytool_path)
            
            # Buscar en PATH
            import shutil
            keytool_cmd = shutil.which("keytool")
            if keytool_cmd:
                return keytool_cmd
            
            return None
            
        except Exception:
            return None