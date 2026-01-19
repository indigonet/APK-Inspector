"""
Módulo de control de versiones para ISV Toolkit
"""

__version__ = "1.2.4"
__release_date__ = "14/01/2026"
__author__ = "Matias Peñaloza"
__app_name__ = "ISV Toolkit"

def get_version_info():
    """
    Retorna información completa de la versión
    """
    return {
        "version": __version__,
        "release_date": __release_date__,
        "author": __author__,
        "app_name": __app_name__
    }

def get_version_string():
    """
    Retorna string formateado de la versión
    """
    return f"{__app_name__} v{__version__}"

def get_short_version():
    """
    Retorna versión corta
    """
    return f"v{__version__}"

def check_update_available():
    """
    Placeholder para futura funcionalidad de verificación de actualizaciones
    """
    # TODO: 
    return {
        "update_available": False,
        "latest_version": __version__,
        "download_url": None
    }