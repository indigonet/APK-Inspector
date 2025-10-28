import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_exe():
    """Construir el ejecutable con todas las herramientas incluidas"""
    
    # Limpiar builds anteriores
    for folder in ['build', 'dist']:
        if Path(folder).exists():
            shutil.rmtree(folder)
    
    # Configuración de PyInstaller
    args = [
        'app/main.py',  # Tu archivo principal
        '--name=APK_Inspector_Pro',
        '--onefile',
        '--windowed',  # Cambia a --console si quieres ver la consola
        '--icon=assets/logoAPP.ico',
        '--add-data=tools;tools',
        '--add-data=assets;assets',
        '--hidden-import=ui.components',
        '--hidden-import=ui.dialogs',
        '--hidden-import=core.apk_analyzer',
        '--hidden-import=utils.APKParser',
        '--clean',
        '--noconfirm'
    ]
    
    print("🚀 Construyendo ejecutable...")
    PyInstaller.__main__.run(args)
    
    print("✅ Build completado! El ejecutable está en la carpeta 'dist/'")

if __name__ == "__main__":
    build_exe()