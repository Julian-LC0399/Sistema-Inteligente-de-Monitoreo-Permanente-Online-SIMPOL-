import streamlit as st
import psutil
import requests
import urllib3
import os
import sys
import base64
import time

# Desactivar advertencias de seguridad para la red interna
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# CONFIGURACIÓN PRTG
# =========================================================
PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "http://127.0.0.1/api/table.json" 

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para recursos, compatible con PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_css(file_name):
    """Inyecta el CSS institucional del banco."""
    try:
        ruta_real = get_resource_path(file_name)
        if os.path.exists(ruta_real):
            with open(ruta_real, encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass

def obtener_valor_prtg(id_sensor):
    """Extrae métricas de PRTG usando la API JSON."""
    if not id_sensor or int(id_sensor) == 0:
        return 0.0, False

    try:
        params = {
            "content": "sensors",
            "columns": "objid,lastvalue,lastvalue_raw",
            "filter_objid": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        # Timeout corto para no congelar la interfaz
        r = requests.get(PRTG_BASE_URL, params=params, timeout=2.0, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            if "sensors" in json_data and len(json_data["sensors"]) > 0:
                raw_val = float(json_data["sensors"][0].get("lastvalue_raw", 0))
                
                # Escalas según ID de sensor
                if int(id_sensor) == 2635: # Red
                    return round(raw_val / 1024, 2), True
                elif int(id_sensor) == 2625: # Latencia
                    return raw_val, True
                else: # CPU/RAM/Disco
                    final_val = raw_val / 10 if raw_val > 100 else raw_val
                    return round(float(final_val), 2), True
    except:
        pass
    return 0.0, False

def obtener_telemetria_total(config_servidor):
    """Calcula telemetría con respaldo local instantáneo."""
    # Interval=None permite lectura inmediata de CPU
    cpu_l = float(psutil.cpu_percent(interval=None))
    ram_l = float(psutil.virtual_memory().percent)
    
    data = {
        "cpu": cpu_l, "ram": ram_l, "disco": 0.0, 
        "red": 0.0, "latencia": 0.0, "msg": "💻 (MODO LOCAL)"
    }

    ids = [
        config_servidor.get('id_sensor_cpu'),
        config_servidor.get('id_sensor_ram'),
        config_servidor.get('id_sensor_disco'),
        config_servidor.get('id_sensor_red'),
        config_servidor.get('id_sensor_latencia')
    ]
    
    resultados = [obtener_valor_prtg(i) for i in ids]
    
    # Si PRTG responde, actualizamos valores
    if any(res[1] for res in resultados):
        data["cpu"] = resultados[0][0] if resultados[0][1] else cpu_l
        data["ram"] = resultados[1][0] if resultados[1][1] else ram_l
        data["disco"] = resultados[2][0]
        data["red"] = resultados[3][0]
        data["latencia"] = resultados[4][0]
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data