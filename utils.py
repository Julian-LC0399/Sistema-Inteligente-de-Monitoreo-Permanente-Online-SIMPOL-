import streamlit as st
import psutil
import requests
import urllib3
import os
import sys
import base64

# Desactivar advertencias de seguridad para el servidor local
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN PARA EL SERVIDOR DEL BANCO
# Nota: El lunes asegúrate que la URL sea correcta (http o https)
PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "http://127.0.0.1/api/table.json" 

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

def get_base64_image(image_path):
    """Convierte el logo a Base64."""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except:
        pass
    return None

def obtener_valor_prtg(id_sensor):
    """
    Función genérica para extraer CUALQUIER métrica de PRTG.
    Retorna el valor y un booleano indicando si la conexión fue exitosa.
    """
    if not id_sensor or id_sensor == 0:
        return 0.0, False

    try:
        params = {
            "content": "sensors",
            "columns": "objid,lastvalue,lastvalue_raw",
            "filter_objid": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        
        # Timeout corto porque estamos en la red interna del banco
        r = requests.get(PRTG_BASE_URL, params=params, timeout=1.5, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            if "sensors" in json_data and len(json_data["sensors"]) > 0:
                raw_val = json_data["sensors"][0].get("lastvalue_raw", 0)
                
                # Lógica de escala: PRTG suele enviar enteros (ej: 458 para 45.8%)
                # Si es un sensor de Latencia (Ping), el valor suele venir directo.
                # Si es CPU/RAM/Disco, dividimos entre 10 si el valor es alto.
                final_val = float(raw_val) / 10 if raw_val > 150 else float(raw_val)
                return final_val, True
    except Exception:
        pass
    
    return 0.0, False

def obtener_telemetria_total(config_servidor):
    """
    Procesa las 5 métricas de un servidor usando sus IDs de PRTG.
    Si falla, usa valores del sistema local como respaldo.
    """
    # 1. Valores de respaldo (Locales)
    cpu_l = float(psutil.cpu_percent(interval=0.1))
    ram_l = float(psutil.virtual_memory().percent)
    
    # 2. Diccionario de resultados
    data = {
        "cpu": 0.0, "ram": 0.0, "disco": 0.0, 
        "red": 0.0, "latencia": 0.0, "msg": "💻 (LOCAL)"
    }

    # Intentamos obtener cada sensor individualmente
    # Si al menos uno conecta, el mensaje cambia a Satelital
    success_any = False

    data["cpu"], s1 = obtener_valor_prtg(config_servidor.get('id_sensor_cpu'))
    data["ram"], s2 = obtener_valor_prtg(config_servidor.get('id_sensor_ram'))
    data["disco"], s3 = obtener_valor_prtg(config_servidor.get('id_sensor_disco'))
    data["red"], s4 = obtener_valor_prtg(config_servidor.get('id_sensor_red'))
    data["latencia"], s5 = obtener_valor_prtg(config_servidor.get('id_sensor_latencia'))

    if any([s1, s2, s3, s4, s5]):
        data["msg"] = "🛰️ (PRTG ONLINE)"
    else:
        # Si todo falló, llenamos con lo que tenemos a mano
        data["cpu"] = cpu_l
        data["ram"] = ram_l
        data["msg"] = "⚠️ (MODO RESPALDO LOCAL)"

    return data