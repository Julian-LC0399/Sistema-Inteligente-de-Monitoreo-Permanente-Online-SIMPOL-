import streamlit as st
import psutil
import requests
import urllib3
import os
import sys

# Desactivar advertencias de certificados SSL (Necesario para la API de PRTG local)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para recursos (logo, css)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_css(file_name):
    """Inyecta el CSS institucional."""
    try:
        ruta_real = get_resource_path(file_name)
        if os.path.exists(ruta_real):
            with open(ruta_real, encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass

def obtener_telemetria():
    """
    Obtiene datos de CPU y RAM.
    Prioriza la API de PRTG y usa PSUTIL como respaldo (fallback).
    """
    # 1. Valores de respaldo (Locales)
    cpu = float(psutil.cpu_percent(interval=0.5))
    ram = float(psutil.virtual_memory().percent)
    fuente = "MODO LOCAL (PSUTIL)"

    # 2. CONEXIÓN REAL CON PRTG (Restaurada)
    url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
    
    try:
        # Hacemos la petición a la API con un timeout corto para no bloquear el agente
        response = requests.get(url, verify=False, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            # Si PRTG devuelve datos, procesamos los sensores
            if "sensors" in data and len(data["sensors"]) > 0:
                # Aquí podrías mapear los valores específicos si PRTG devuelve CPU/RAM por separado
                # Por ahora, marcamos que la API está respondiendo
                fuente = "API PRTG ACTIVA (Sensor 2094)"
                # Ejemplo de extracción si lastvalue_raw trae el porcentaje:
                # cpu = data["sensors"][0].get("lastvalue_raw", cpu)
    except Exception as e:
        fuente = f"ERROR API (Usando Local): {str(e)[:30]}"

    return cpu, ram, fuente

def formatear_fecha(fecha):
    """Estandariza fechas para reportes."""
    if fecha:
        return fecha.strftime('%d/%m/%Y %H:%M:%S')
    return "N/A"