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
        'app/main.py',
        '--name=ISV_Toolkit',
        '--noconsole',
        '--icon=assets/logoAPP.ico',
        '--add-data=tools;tools',
        '--add-data=assets;assets',
        '--clean',
        '--noconfirm'
    ]

    
    print("🚀 Construyendo ejecutable...")
    PyInstaller.__main__.run(args)
    
    print("✅ Build completado! El ejecutable está en la carpeta 'dist/'")

if __name__ == "__main__":
    build_exe()