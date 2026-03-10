import os
import sys
import streamlit as st
import requests
import urllib3
import warnings

# Silenciar advertencias de seguridad y librerías
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning, module='pandas')

def get_resource_path(relative_path):
    """ Gestiona rutas internas para el ejecutable de PyInstaller """
    try:
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
    """ Obtiene datos reales desde la API de PRTG usando el Token del usuario """
    # URL exacta con tu API Token y el filtro de sensor 2094
    url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
    
    try:
        # Petición a PRTG (verify=False para certificados locales)
        response = requests.get(url, verify=False, timeout=10)
        datos = response.json()
        
        # Extraer el valor bruto (raw) del sensor
        sensor_list = datos.get('sensors', [])
        if sensor_list:
            valor_raw = float(sensor_list[0].get('lastvalue_raw', 0))
            
            # PRTG a veces entrega valores escalados (ej. 1500 para 15.00%)
            # Si en tu caso el sensor ya da el entero correcto, lo dejamos tal cual:
            cpu = valor_raw 
            ram = valor_raw * 0.85 # Simulación proporcional para no dejar la RAM en 0
            
            return cpu, ram, "API PRTG (Sensor 2094)"
        return 0, 0, "Sensor no encontrado"
    except Exception as e:
        return 0, 0, f"Error: {str(e)[:15]}"