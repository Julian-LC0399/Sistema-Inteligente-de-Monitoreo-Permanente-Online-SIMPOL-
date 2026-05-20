import psutil
import requests
import urllib3
import os
import sys

# Desactivar advertencias de seguridad para la red interna del banco
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

def obtener_valor_prtg(id_sensor, tipo_metrica):
    """
    Extrae métricas de PRTG usando la API JSON.
    Recibe el tipo_metrica ('cpu', 'ram', 'disco', 'red', 'latencia') para aplicar escalas dinámicas.
    """
    if not id_sensor or int(id_sensor) == 0:
        return 0.0, False

    try:
        params = {
            "content": "sensors",
            "columns": "objid,lastvalue,lastvalue_raw",
            "filter_objid": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        # Timeout corto (2 segundos) para no colgar el hilo del agente ni de la UI
        r = requests.get(PRTG_BASE_URL, params=params, timeout=2.0, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            if "sensors" in json_data and len(json_data["sensors"]) > 0:
                raw_val = float(json_data["sensors"][0].get("lastvalue_raw", 0))
                
                # === ESCALAS DINÁMICAS POR TIPO DE MÉTRICA (Sincronizado con el Catálogo) ===
                if tipo_metrica == "red":
                    # Convierte los bits crudos de PRTG a Mbps de forma conforme
                    return round(raw_val / 1024 / 1024, 2) if raw_val > 0 else 0.0, True
                elif tipo_metrica == "latencia":
                    return round(raw_val, 2), True
                else: 
                    # CPU / RAM / Disco: PRTG suele entregar los porcentajes multiplicados por 10 (ej: 450 = 45%)
                    final_val = raw_val / 10 if raw_val > 100 else raw_val
                    return round(float(final_val), 2), True
    except:
        pass
    return 0.0, False

def obtener_telemetria_total(config_servidor):
    """Calcula telemetría con respaldo local instantáneo."""
    # Lectura de contingencia local inmediata
    cpu_l = float(psutil.cpu_percent(interval=None))
    ram_l = float(psutil.virtual_memory().percent)
    
    data = {
        "cpu": cpu_l, 
        "ram": ram_l, 
        "disco": 0.0, 
        "red": 0.0, 
        "latencia": 0.0, 
        "msg": "💻 (MODO LOCAL)"
    }

    # Extracción segura mapeando las llaves exactas de tu tabla 'servidores'
    id_cpu = config_servidor.get('id_sensor_cpu', 0)
    id_ram = config_servidor.get('id_sensor_ram', 0)
    id_disco = config_servidor.get('id_sensor_disco', 0)
    id_red = config_servidor.get('id_sensor_red', 0)
    id_lat = config_servidor.get('id_sensor_latencia', 0)
    
    # Consultas individuales pasando el tipo de métrica para activar su escala correspondiente
    v_cpu, ok_cpu = obtener_valor_prtg(id_cpu, "cpu")
    v_ram, ok_ram = obtener_valor_prtg(id_ram, "ram")
    v_disco, ok_disco = obtener_valor_prtg(id_disco, "disco")
    v_red, ok_red = obtener_valor_prtg(id_red, "red")
    v_lat, ok_lat = obtener_valor_prtg(id_lat, "latencia")
    
    # Si al menos un sensor de PRTG responde con éxito, conmutamos a ONLINE
    if any([ok_cpu, ok_ram, ok_disco, ok_red, ok_lat]):
        data["cpu"] = v_cpu if ok_cpu else cpu_l
        data["ram"] = v_ram if ok_ram else ram_l
        data["disco"] = v_disco if ok_disco else 0.0
        data["red"] = v_red if ok_red else 0.0
        data["latencia"] = v_lat if ok_lat else 0.0
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data