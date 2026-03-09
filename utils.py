import os
import sys
import streamlit as st

def get_resource_path(relative_path):
    """ Gestiona rutas internas para el ejecutable de PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_css(file_name):
    """ Carga archivos CSS de forma segura en el ejecutable """
    try:
        ruta_css = get_resource_path(file_name)
        with open(ruta_css, "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error al cargar CSS: {e}")

def obtener_telemetria():
    """ Obtiene datos del sistema (psutil) """
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        return cpu, ram, "psutil (Local)"
    except:
        return 0, 0, "Error de sensor"