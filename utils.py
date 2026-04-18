import streamlit as st
import psutil
import requests
import urllib3
import os
import sys

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN GLOBAL DEL SERVIDOR BANCO CARONÍ
# Clave API proporcionada para el servidor de producción
PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "https://127.0.0.1/api/table.json"

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

def obtener_telemetria(id_sensor=None):
    """
    Obtiene datos de CPU y RAM. 
    Si recibe un id_sensor, consulta a PRTG. 
    Si no, o si falla, usa el modo local de respaldo.
    """
    # 1. Respaldo Local (Evita valores 0.0)
    cpu_local = float(psutil.cpu_percent(interval=0.1))
    ram_local = float(psutil.virtual_memory().percent)
    
    cpu = cpu_local
    ram = ram_local
    msg = "💻 (MODO LOCAL)"

    # Si no hay ID de sensor (o es el 2094 de prueba), usamos local por seguridad o 
    # procedemos a intentar la conexión si es un sensor real del servidor.
    if id_sensor and id_sensor != 2094:
        try:
            # Construcción dinámica de la URL con el nuevo Token del servidor
            params = {
                "content": "sensors",
                "columns": "objid,lastvalue,lastvalue_raw",
                "filter_objid": id_sensor,
                "apitoken": PRTG_API_TOKEN
            }
            
            r = requests.get(PRTG_BASE_URL, params=params, timeout=2.0, verify=False)
            
            if r.status_code == 200:
                json_data = r.json()
                if "sensors" in json_data and len(json_data["sensors"]) > 0:
                    raw_val = json_data["sensors"][0].get("lastvalue_raw", cpu_local)
                    
                    # Ajuste de escala automático de PRTG
                    cpu = float(raw_val) / 10 if raw_val > 100 else float(raw_val)
                    msg = f"🛰️ (PRTG SENSOR {id_sensor})"
        except Exception:
            # En caso de caída de red o timeout, retorna los valores locales
            pass
    else:
        # Mensaje informativo si se intenta usar el sensor de prueba 2094
        if id_sensor == 2094:
            msg = "⚠️ (SENSOR 2094 OMITIDO - MODO LOCAL)"

    return cpu, ram, msg