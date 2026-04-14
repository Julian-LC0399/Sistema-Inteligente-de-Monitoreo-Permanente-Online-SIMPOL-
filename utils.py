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
    """Obtiene datos de CPU y RAM con sincronía forzada para PRTG."""
    # 1. Preparar respaldo local con intervalo real para evitar el 0.0
    cpu_local = float(psutil.cpu_percent(interval=0.1))
    ram_local = float(psutil.virtual_memory().percent)
    
    cpu = cpu_local
    ram = ram_local
    msg = "💻 (MODO LOCAL)"
    
    try:
        # 2. URL de PRTG (Aumentamos estabilidad)
        # Nota: He mantenido tu token, pero subimos el timeout a 2.0 segundos
        url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
        
        r = requests.get(url, timeout=2.0, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            if "sensors" in json_data and len(json_data["sensors"]) > 0:
                # Extraemos el valor raw (PRTG suele darlo multiplicado por 10 o en escala)
                raw_val = json_data["sensors"][0].get("lastvalue_raw", cpu_local)
                
                # Ajuste de escala: Si PRTG envía 450 para decir 45.0%
                cpu = float(raw_val) / 10 if raw_val > 100 else float(raw_val)
                
                msg = "🛰️ (PRTG SENSOR 2094)"
    except Exception as e:
        # Si hay error, msg se queda como MODO LOCAL
        pass

    return cpu, ram, msg