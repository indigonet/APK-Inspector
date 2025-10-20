import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List
import tempfile

class FileUtils:
    @staticmethod
    def encontrar_logo() -> Optional[str]:
        """Encontrar imagen de logo en varias ubicaciones - Compatible con PyInstaller"""
        logo_path_candidates = []
        
        # Para PyInstaller (ejecutable)
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass:
                logo_path_candidates.append(Path(meipass) / "logo.png")
                logo_path_candidates.append(Path(meipass) / "assets" / "logo.png")
            
            # Directorio del ejecutable
            exe_dir = Path(sys.executable).parent
            logo_path_candidates.append(exe_dir / "logo.png")
            logo_path_candidates.append(exe_dir / "assets" / "logo.png")
        
        # Para desarrollo (script)
        current_dir = Path(__file__).parent.parent
        logo_path_candidates.extend([
            current_dir / "logo.png",
            current_dir / "assets" / "logo.png",  # ← NUEVA RUTA
            Path.cwd() / "logo.png",
            Path.cwd() / "assets" / "logo.png",   # ← NUEVA RUTA
            Path("logo.png"),
            Path("assets") / "logo.png"           # ← NUEVA RUTA
        ])
        
        # Buscar recursivamente
        try:
            for file_path in Path.cwd().rglob("logo.png"):
                logo_path_candidates.append(file_path)
            # Buscar específicamente en assets
            for file_path in Path.cwd().rglob("assets/logo.png"):
                logo_path_candidates.append(file_path)
        except Exception:
            pass
        
        # Eliminar duplicados y verificar existencia
        unique_paths = []
        for p in logo_path_candidates:
            if p and p.exists() and p not in unique_paths:
                unique_paths.append(p)
        
        # Devolver el primero que exista
        for p in unique_paths:
            if p.exists():
                return str(p)
        
        return None

    @staticmethod
    def es_archivo_apk_valido(file_path: str) -> bool:
        """Verificar si un archivo es un APK válido"""
        try:
            path = Path(file_path)
            return (path.exists() and 
                   path.is_file() and 
                   path.suffix.lower() == '.apk' and
                   path.stat().st_size > 1000)  # Mínimo 1KB
        except Exception:
            return False

    @staticmethod
    def obtener_tamano_archivo(file_path: str) -> str:
        """Obtener tamaño de archivo formateado"""
        try:
            size_bytes = Path(file_path).stat().st_size
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
                
            return f"{size_bytes:.1f} TB"
        except Exception:
            return "Desconocido"

    @staticmethod
    def crear_directorio_temporal() -> Path:
        """Crear directorio temporal para análisis"""
        temp_dir = Path(tempfile.mkdtemp(prefix="apk_inspector_"))
        temp_dir.mkdir(exist_ok=True)
        return temp_dir

    @staticmethod
    def limpiar_directorio_temporal(temp_dir: Path):
        """Limpiar directorio temporal de forma segura"""
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Advertencia: No se pudo limpiar directorio temporal: {e}")

    @staticmethod
    def copiar_archivo(origen: Path, destino: Path) -> bool:
        """Copiar archivo de forma segura"""
        try:
            shutil.copy2(origen, destino)
            return True
        except Exception as e:
            print(f"Error copiando archivo: {e}")
            return False

    @staticmethod
    def buscar_archivos_apk(directorio: Path) -> List[Path]:
        """Buscar archivos APK en un directorio"""
        apks = []
        try:
            for archivo in directorio.rglob("*.apk"):
                if archivo.is_file():
                    apks.append(archivo)
        except Exception as e:
            print(f"Error buscando APKs: {e}")
        
        return apks

    @staticmethod
    def obtener_nombre_archivo_sin_extension(ruta_archivo: str) -> str:
        """Obtener nombre de archivo sin extensión"""
        return Path(ruta_archivo).stem

    @staticmethod
    def es_directorio_escriturable(directorio: Path) -> bool:
        """Verificar si un directorio es escribible"""
        try:
            test_file = directorio / ".test_write"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def generar_nombre_archivo_unico(directorio: Path, nombre_base: str, extension: str) -> Path:
        """Generar nombre de archivo único en el directorio"""
        contador = 1
        nombre_archivo = directorio / f"{nombre_base}{extension}"
        
        while nombre_archivo.exists():
            nombre_archivo = directorio / f"{nombre_base}_{contador}{extension}"
            contador += 1
            
        return nombre_archivo