import subprocess
from pathlib import Path
from typing import List, Tuple, Dict
import sys

class ADBManager:
    def __init__(self):
        self.devices_cache = None
        
    def obtener_dispositivos(self, platform_tools_path: str) -> Tuple[bool, List[str]]:
        """Obtener lista de dispositivos conectados"""
        if not platform_tools_path:
            return False, ["Platform-tools no configurado"]
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return False, [f"ADB no encontrado en: {platform_path}"]
            
        try:
            rc, output = self._ejecutar_comando(adb_bin, ["devices"])
            if rc != 0:
                return False, [f"Error ejecutando ADB: {output}"]
                
            # Parsear output mejorado
            lineas = output.strip().split('\n')
            dispositivos = []
            
            for linea in lineas:
                linea = linea.strip()
                # Buscar líneas que contengan "device" (no "offline" o "unauthorized")
                if linea and '\tdevice' in linea:
                    device_id = linea.split('\t')[0]
                    dispositivos.append(device_id)
            
            # Si no hay dispositivos, verificar si ADB está funcionando
            if not dispositivos and "daemon" in output.lower():
                return False, ["Servidor ADB no iniciado. Ejecuta 'adb devices' primero."]
                    
            self.devices_cache = dispositivos
            return True, dispositivos
            
        except Exception as e:
            return False, [f"Excepción al obtener dispositivos: {str(e)}"]

    def instalar_apk(self, apk_path: Path, platform_tools_path: str, device_id: str = None) -> Tuple[bool, str]:
        """Instalar APK en dispositivo"""
        if not platform_tools_path:
            return False, "Platform-tools no configurado"
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return False, f"ADB no encontrado en: {platform_path}"
            
        if not apk_path.exists():
            return False, f"APK no encontrado: {apk_path}"
            
        # Construir comando CORREGIDO - el -s debe ir ANTES del comando install
        comando = []
        
        # Si hay dispositivo específico, agregar -s al inicio
        if device_id:
            comando.extend(["-s", device_id])
        
        # Agregar comando install
        comando.extend(["install", "-r", str(apk_path)])
        
        try:
            rc, output = self._ejecutar_comando(adb_bin, comando, timeout=120)  # 2 minutos timeout
            exito = rc == 0
            return exito, output
            
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado durante la instalación"
        except Exception as e:
            return False, f"Error durante instalación: {str(e)}"

    def _ejecutar_comando(self, command_path: Path, args: list, timeout: int = 60) -> Tuple[int, str]:
        """Ejecutar comando ADB"""
        try:
            cmd = [str(command_path)] + args
            proc = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            return proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            return 1, f"Tiempo de espera agotado ({timeout}s)"
        except Exception as e:
            return 1, f"Error ejecutando comando: {str(e)}"

    def obtener_info_dispositivo(self, platform_tools_path: str, device_id: str) -> Dict:
        """Obtener información detallada del dispositivo"""
        if not platform_tools_path:
            return {"error": "Platform-tools no configurado"}
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return {"error": "ADB no encontrado"}
            
        info = {}
        
        # Construir comando base con -s si hay device_id
        base_cmd = []
        if device_id:
            base_cmd.extend(["-s", device_id])
        
        # Obtener modelo
        rc, output = self._ejecutar_comando(adb_bin, base_cmd + ["shell", "getprop", "ro.product.model"])
        if rc == 0 and output.strip():
            info["modelo"] = output.strip()
            
        # Obtener versión Android
        rc, output = self._ejecutar_comando(adb_bin, base_cmd + ["shell", "getprop", "ro.build.version.release"])
        if rc == 0 and output.strip():
            info["android_version"] = output.strip()
            
        # Obtener fabricante
        rc, output = self._ejecutar_comando(adb_bin, base_cmd + ["shell", "getprop", "ro.product.manufacturer"])
        if rc == 0 and output.strip():
            info["fabricante"] = output.strip()
            
        # Obtener nombre del dispositivo
        rc, output = self._ejecutar_comando(adb_bin, base_cmd + ["shell", "getprop", "ro.product.name"])
        if rc == 0 and output.strip():
            info["nombre"] = output.strip()
            
        return info

    def desinstalar_apk(self, platform_tools_path: str, package_name: str, device_id: str = None) -> Tuple[bool, str]:
        """Desinstalar aplicación por nombre de paquete"""
        if not platform_tools_path:
            return False, "Platform-tools no configurado"
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return False, f"ADB no encontrado en: {platform_path}"
            
        # Construir comando
        comando = []
        if device_id:
            comando.extend(["-s", device_id])
        comando.extend(["uninstall", package_name])
        
        try:
            rc, output = self._ejecutar_comando(adb_bin, comando, timeout=60)
            exito = rc == 0
            return exito, output
        except Exception as e:
            return False, f"Error durante desinstalación: {str(e)}"

    def reiniciar_adb(self, platform_tools_path: str) -> Tuple[bool, str]:
        """Reiniciar servidor ADB"""
        if not platform_tools_path:
            return False, "Platform-tools no configurado"
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return False, f"ADB no encontrado en: {platform_path}"
            
        try:
            # Matar servidor ADB
            rc1, output1 = self._ejecutar_comando(adb_bin, ["kill-server"])
            # Iniciar servidor ADB
            rc2, output2 = self._ejecutar_comando(adb_bin, ["start-server"])
            
            return True, "Servidor ADB reiniciado correctamente"
        except Exception as e:
            return False, f"Error reiniciando ADB: {str(e)}"

    def obtener_paquetes_instalados(self, platform_tools_path: str, device_id: str = None) -> Tuple[bool, List[str]]:
        """Obtener lista de paquetes instalados en el dispositivo"""
        if not platform_tools_path:
            return False, ["Platform-tools no configurado"]
            
        platform_path = Path(platform_tools_path)
        adb_bin = platform_path / ("adb.exe" if sys.platform.startswith("win") else "adb")
        
        if not adb_bin.exists():
            return False, [f"ADB no encontrado en: {platform_path}"]
            
        # Construir comando
        comando = []
        if device_id:
            comando.extend(["-s", device_id])
        comando.extend(["shell", "pm", "list", "packages"])
        
        try:
            rc, output = self._ejecutar_comando(adb_bin, comando, timeout=30)
            if rc != 0:
                return False, [f"Error obteniendo paquetes: {output}"]
                
            # Parsear output
            paquetes = []
            for linea in output.strip().split('\n'):
                if linea.startswith('package:'):
                    paquete = linea.replace('package:', '').strip()
                    paquetes.append(paquete)
                    
            return True, paquetes
            
        except Exception as e:
            return False, [f"Excepción al obtener paquetes: {str(e)}"]