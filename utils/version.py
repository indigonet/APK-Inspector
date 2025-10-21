"""
Módulo de control de versiones para APK Inspector
"""

__version__ = "1.0.4"
__version_code__ = "21102025"
__release_date__ = "21/10/2025"
__author__ = "Matias Peñaloza"
__app_name__ = "APK Inspector"

def get_version_info():
    """
    Retorna información completa de la versión
    """
    return {
        "version": __version__,
        "version_code": __version_code__,
        "release_date": __release_date__,
        "author": __author__,
        "app_name": __app_name__
    }

def get_version_string():
    """
    Retorna string formateado de la versión
    """
    return f"{__app_name__} v{__version__} (Build {__version_code__})"

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