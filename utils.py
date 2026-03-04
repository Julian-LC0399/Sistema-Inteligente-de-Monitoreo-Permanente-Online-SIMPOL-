import streamlit as st
import psutil
import requests
import urllib3

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_css(file_name):
    """Lee el archivo CSS e inyecta el código en el HTML de Streamlit"""
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"No se pudo cargar el CSS: {e}")

def obtener_telemetria():
    """Obtiene datos de CPU y RAM (Local o PRTG)"""
    cpu = float(psutil.cpu_percent(interval=None))
    ram = float(psutil.virtual_memory().percent)
    msg = "MODO LOCAL"
    try:
        # Token y URL de tu sensor PRTG
        url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
        r = requests.get(url, timeout=0.8, verify=False)
        if r.status_code == 200:
            cpu = float(r.json()["sensors"][0].get("lastvalue_raw", cpu))
            msg = "PRTG SENSOR"
    except:
        pass
    return cpu, ram, msg