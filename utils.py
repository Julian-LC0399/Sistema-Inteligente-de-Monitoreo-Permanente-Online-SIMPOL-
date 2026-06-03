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

def safe_float(valor):
    """Convierte de forma segura un valor a float, manejando vacíos o textos."""
    if valor is None:
        return 0.0
    val_str = str(valor).strip()
    if val_str == "" or val_str.lower() == "none":
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def obtener_valor_prtg(id_sensor, tipo_metrica):
    """
    Extrae métricas y PORCENTAJES de PRTG usando la API JSON de Canales Extendidos.
    Filtra de forma ultra-flexible para capturar el porcentaje libre exacto.
    """
    if not id_sensor or int(id_sensor) == 0:
        return 0.0, None, False

    try:
        params = {
            "content": "channels",
            "columns": "name,lastvalue,lastvalue_raw",
            "id": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        
        r = requests.get(PRTG_BASE_URL, params=params, timeout=3.5, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            channels = json_data.get("channels", [])
            
            if channels:
                val_crudo_principal = None
                pct_libre_detectado = None
                primer_canal_valido = None
                
                # REVISIÓN: Recorremos los canales devueltos por PRTG
                for channel in channels:
                    name = str(channel.get("name", "")).lower()
                    raw_val = safe_float(channel.get("lastvalue_raw", 0))
                    
                    # Guardamos el primer valor numérico que aparezca como respaldo (Fallback)
                    if primer_canal_valido is None and raw_val > 0:
                        primer_canal_valido = raw_val
                    
                    # 1. BÚSQUEDA DEL CANAL DE PORCENTAJE (Ultra flexible)
                    # Si el nombre contiene %, pct, percent, porc o es un valor típicamente menor o igual a 100
                    if "%" in name or "pct" in name or "percent" in name or "porc" in name or "libre (%)" in name or "free (%)" in name:
                        if any(k in name for k in ["libre", "free", "disp", "avail"]):
                            pct_libre_detectado = raw_val
                        elif pct_libre_detectado is None and not any(k in name for k in ["usado", "used"]):
                            pct_libre_detectado = raw_val
                    
                    # 2. BÚSQUEDA DEL CANAL DE ESPACIO EN BYTES / GB (VALOR PRINCIPAL)
                    else:
                        if any(k in name for k in ["libre", "free", "disp", "avail", "space", "volátil", "total", "bytes", "gb", "disk", "disco"]):
                            val_crudo_principal = raw_val

                # --- VALIDACIÓN DE RESPALDO EN CASO DE MATCHES NULOS ---
                if val_crudo_principal is None:
                    if primer_canal_valido is not None and primer_canal_valido > 100.0:
                        val_crudo_principal = primer_canal_valido
                    else:
                        val_crudo_principal = 0.0
                
                # Fallback agresivo para el Porcentaje: Si el ciclo principal no lo atrapó por el nombre,
                # pero vemos un segundo canal con un valor coherente de porcentaje (ej: entre 0 y 100), lo capturamos
                if pct_libre_detectado is None and tipo_metrica in ["ram", "disco"]:
                    for channel in channels:
                        name = str(channel.get("name", "")).lower()
                        raw_val = safe_float(channel.get("lastvalue_raw", 0))
                        # Si el valor raw está entre 0.1 y 100 y no es el principal de los GB, asumimos que es el %
                        if 0.1 <= raw_val <= 100.0 and raw_val != val_crudo_principal:
                            pct_libre_detectado = raw_val
                            break

                # Normalización estricta de escalas de porcentaje (PRTG a veces manda el valor corrido un decimal)
                if pct_libre_detectado is not None:
                    if pct_libre_detectado > 100:
                        pct_libre_detectado = pct_libre_detectado / 10.0
                    if pct_libre_detectado > 100:
                        pct_libre_detectado = pct_libre_detectado / 10.0

                # === APLICAR CONVERSIONES SEGÚN EL TIPO DE MÉTRICA ===
                if tipo_metrica == "red":
                    val_final = round(val_crudo_principal / 1024 / 1024, 2) if val_crudo_principal > 0 else 0.0
                    return val_final, None, True
                
                elif tipo_metrica == "latencia":
                    return round(val_crudo_principal, 2), None, True
                
                elif tipo_metrica in ["ram", "disco"]:
                    # Si viene un valor ya pre-calculado directo en GB por PRTG (ej. 30 o 60)
                    if 1.0 <= val_crudo_principal <= 50000.0:
                        val_gb = round(val_crudo_principal, 2)
                    # Si viene un valor gigante en Bytes
                    elif val_crudo_principal > 1073741824:
                        val_gb = round(val_crudo_principal / 1073741824, 2)
                    elif val_crudo_principal > 1048576: 
                        val_gb = round(val_crudo_principal / 1048576, 2)
                    else:
                        val_gb = round(val_crudo_principal, 2)
                    
                    p_final = round(pct_libre_detectado, 1) if pct_libre_detectado is not None else None
                    return val_gb, p_final, True
                
                elif tipo_metrica == "servicio":
                    return int(val_crudo_principal), None, True
                
                else:
                    return round(float(val_crudo_principal), 2), None, True
                    
    except Exception as e:
        with open("simpol_agente.log", "a", encoding="utf-8") as f:
            f.write(f"[utils.py] ❌ Error general procesando canales en sensor {id_sensor}: {str(e)}\n")
            
    return 0.0, None, False

def obtener_telemetria_total(config_servidor):
    """
    Calcula telemetría y porcentajes con respaldo local e indexación automática multicanal.
    """
    cpu_l = float(psutil.cpu_percent(interval=None))
    ram_l = round(float(psutil.virtual_memory().available) / 1073741824, 2)
    pct_ram_l = round((float(psutil.virtual_memory().available) / float(psutil.virtual_memory().total)) * 100, 1)
    
    data = {
        "cpu": cpu_l, "ram": ram_l, "pct_ram": pct_ram_l,
        "red": 0.0, "latencia": 0.0, 
        "disco_1": 0.0, "disco_2": 0.0, "disco_3": 0.0, "disco_4": 0.0, "disco_5": 0.0, "disco_6": 0.0,
        "pct_disco_1": None, "pct_disco_2": None, "pct_disco_3": None, "pct_disco_4": None, "pct_disco_5": None, "pct_disco_6": None,
        "servicio_1": 0, "servicio_2": 0, "servicio_3": 0, "servicio_4": 0, "servicio_5": 0,
        "msg": "💻 (MODO LOCAL)"
    }

    v_cpu, _, ok_cpu = obtener_valor_prtg(config_servidor.get('id_sensor_cpu', 0), "cpu")
    v_ram, p_ram, ok_ram = obtener_valor_prtg(config_servidor.get('id_sensor_ram', 0), "ram")
    v_red, _, ok_red = obtener_valor_prtg(config_servidor.get('id_sensor_red', 0), "red")
    v_lat, _, ok_lat = obtener_valor_prtg(config_servidor.get('id_sensor_latencia', 0), "latencia")
    
    discos_res = {}
    for i in range(1, 7):
        v_disc, p_disc, ok_disc = obtener_valor_prtg(config_servidor.get(f'id_sensor_disco_{i}', 0), "disco")
        discos_res[f'd_{i}'] = v_disc
        discos_res[f'p_{i}'] = p_disc
        discos_res[f'ok_{i}'] = ok_disc if (ok_disc and v_disc > 0) else False

    servicios_res = {}
    for i in range(1, 6):
        v_serv, _, ok_serv = obtener_valor_prtg(config_servidor.get(f'id_sensor_servicio_{i}', 0), "servicio")
        servicios_res[f's_{i}'] = v_serv if ok_serv else 0

    prtg_activo = False
    if ok_cpu and v_cpu > 0: prtg_activo = True
    if ok_ram or ok_red or ok_lat: prtg_activo = True
    if any(discos_res[f'ok_{i}'] for i in range(1, 7)): prtg_activo = True

    if prtg_activo:
        data["cpu"] = v_cpu if (ok_cpu and v_cpu > 0) else cpu_l
        data["ram"] = v_ram if ok_ram else ram_l
        data["pct_ram"] = p_ram if (ok_ram and p_ram is not None) else pct_ram_l
        data["red"] = v_red if ok_red else 0.0
        data["latencia"] = v_lat if ok_lat else 0.0
        
        for i in range(1, 7):
            if discos_res[f"ok_{i}"]:
                data[f"disco_{i}"] = discos_res[f"d_{i}"]
                data[f"pct_disco_{i}"] = discos_res[f"p_{i}"]
            else:
                data[f"disco_{i}"] = 0.0
                data[f"pct_disco_{i}"] = None

        for i in range(1, 6):
            data[f"servicio_{i}"] = servicios_res[f"s_{i}"]
            
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data