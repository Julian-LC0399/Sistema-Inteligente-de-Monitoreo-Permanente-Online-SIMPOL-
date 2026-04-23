import streamlit as st
import psutil
import requests
import urllib3
import os
import sys
import base64
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración (considera mover estos a un archivo de configuración si es posible)
PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "http://127.0.0.1/api/table.json" 

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def obtener_valor_prtg(id_sensor):
    """Extrae métricas de PRTG con manejo de errores mejorado."""
    if not id_sensor or int(id_sensor) == 0:
        return 0.0, False

    try:
        params = {
            "content": "sensors",
            "columns": "objid,lastvalue,lastvalue_raw",
            "filter_objid": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        
        # Aumentamos ligeramente el timeout a 2.5s para evitar bloqueos innecesarios
        r = requests.get(PRTG_BASE_URL, params=params, timeout=2.5, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            if "sensors" in json_data and len(json_data["sensors"]) > 0:
                raw_val = float(json_data["sensors"][0].get("lastvalue_raw", 0))
                
                # --- Lógica de sensores (Aquí podrías parametrizar los IDs) ---
                if int(id_sensor) == 2625: # Latencia
                    return raw_val, True
                elif int(id_sensor) == 2635: # Red
                    return round(raw_val / 1024, 2), True
                else: # CPU/RAM/Disco
                    final_val = raw_val / 10 if raw_val > 100 else raw_val
                    return round(float(final_val), 2), True
                    
    except Exception as e:
        # LOG PARA EL EXE: Si falla, guarda en un archivo al lado del ejecutable
        with open("error_log_utils.txt", "a") as f:
            f.write(f"[{time.ctime()}] Error sensor {id_sensor}: {str(e)}\n")
        return 0.0, False
    
    return 0.0, False

def obtener_telemetria_total(config_servidor):
    """
    Procesa las métricas. Si PRTG falla, el modo respaldo es casi instantáneo.
    """
    # 1. Fallback local rápido
    cpu_l = float(psutil.cpu_percent(interval=None)) # Interval None no bloquea
    ram_l = float(psutil.virtual_memory().percent)
    
    data = {"cpu": cpu_l, "ram": ram_l, "disco": 0.0, "red": 0.0, "latencia": 0.0, "msg": "💻 (MODO LOCAL)"}

    # Intentar traer PRTG
    # Si alguna configuración falta, saltamos ese sensor
    ids = [
        config_servidor.get('id_sensor_cpu'),
        config_servidor.get('id_sensor_ram'),
        config_servidor.get('id_sensor_disco'),
        config_servidor.get('id_sensor_red'),
        config_servidor.get('id_sensor_latencia')
    ]
    
    resultados = [obtener_valor_prtg(i) for i in ids]
    
    # Si al menos uno tiene éxito (valor True en la tupla), actualizamos
    if any(res[1] for res in resultados):
        data["cpu"] = resultados[0][0] if resultados[0][1] else cpu_l
        data["ram"] = resultados[1][0] if resultados[1][1] else ram_l
        data["disco"] = resultados[2][0]
        data["red"] = resultados[3][0]
        data["latencia"] = resultados[4][0]
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data