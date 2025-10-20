"""
APK Inspector & Verifier - Punto de entrada principal
"""

import sys
import os
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))  
sys.path.insert(0, str(current_dir / "app"))  

try:
    from app.main import main
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("\n📁 Estructura de directorios:")
    for item in current_dir.iterdir():
        print(f"  - {item.name}/" if item.is_dir() else f"  - {item.name}")
    
    if (current_dir / "app").exists():
        print("\n📁 Contenido de app/:")
        for item in (current_dir / "app").iterdir():
            print(f"  - {item.name}")
    
    input("\nPresiona Enter para salir...")