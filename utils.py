import os
import sys
import logging
import requests
import urllib3
import psutil

# Desactivar advertencias de seguridad para la red interna del banco (SSL auto-firmado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de Logs del Agente de Telemetría
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simpol_agente.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# =========================================================
# CONFIGURACIÓN PRTG
# =========================================================
PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "http://127.0.0.1/api/table.json" 

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para recursos, compatible con empaquetado PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def safe_float(valor):
    """Convierte de forma segura un valor a float, manejando vacíos, caracteres o text Null."""
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
                
                # Fallback agresivo para el Porcentaje
                if pct_libre_detectado is None and tipo_metrica in ["ram", "disco"]:
                    for channel in channels:
                        raw_val = safe_float(channel.get("lastvalue_raw", 0))
                        if 0.1 <= raw_val <= 100.0 and raw_val != val_crudo_principal:
                            pct_libre_detectado = raw_val
                            break

                # Normalización estricta de escalas de porcentaje (PRTG corre el decimal a veces)
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
                    if 1.0 <= val_crudo_principal <= 50000.0:
                        val_gb = round(val_crudo_principal, 2)
                    elif val_crudo_principal > 1073741824:
                        val_gb = round(val_crudo_principal / 1073741824, 2)
                    elif val_crudo_principal > 1048576: 
                        val_gb = round(val_crudo_principal / 1048576, 2)
                    else:
                        val_gb = round(val_crudo_principal, 2)
                    
                    p_final = round(pct_libre_detectado, 1) if pct_libre_detectado is not None else 0.0
                    return val_gb, p_final, True
                
                elif tipo_metrica == "servicio":
                    return int(val_crudo_principal), None, True
                
                else:
                    return round(float(val_crudo_principal), 2), None, True
                    
    except Exception as e:
        logging.error(f"[utils.py] ❌ Error general procesando canales en sensor {id_sensor}: {str(e)}")
            
    return 0.0, 0.0 if tipo_metrica in ["ram", "disco"] else None, False

def obtener_telemetria_total(config_servidor):
    """
    Calcula telemetría manejando estrictamente solo los sensores registrados
    para el servidor actual. Soporta de forma dinámica hasta 6 Discos y 8 Servicios.
    """
    # 1. Muestreo Local (Fallback de Contingencia Estricta)
    cpu_l = float(psutil.cpu_percent(interval=None))
    ram_l = round(float(psutil.virtual_memory().available) / 1073741824, 2)
    pct_ram_l = round((float(psutil.virtual_memory().available) / float(psutil.virtual_memory().total)) * 100, 1)
    
    # Payload estructurado base (Los sensores van en None por defecto si no están registrados)
    data = {
        "cpu": cpu_l, "ram": ram_l, "pct_ram": pct_ram_l,
        "red": 0.0, "latencia": 0.0, 
        "disco_1": None, "disco_2": None, "disco_3": None, "disco_4": None, "disco_5": None, "disco_6": None,
        "pct_disco_1": None, "pct_disco_2": None, "pct_disco_3": None, "pct_disco_4": None, "pct_disco_5": None, "pct_disco_6": None,
        "servicio_1": None, "servicio_2": None, "servicio_3": None, "servicio_4": None, "servicio_5": None,
        "servicio_6": None, "servicio_7": None, "servicio_8": None,
        "msg": "💻 (MODO LOCAL)"
    }

    # 2. Consultas individuales a la API de PRTG solo si los sensores base están registrados (> 0)
    id_cpu = int(config_servidor.get('id_sensor_cpu', 0) or 0)
    id_ram = int(config_servidor.get('id_sensor_ram', 0) or 0)
    id_red = int(config_servidor.get('id_sensor_red', 0) or 0)
    id_lat = int(config_servidor.get('id_sensor_latencia', 0) or 0)

    v_cpu, _, ok_cpu = obtener_valor_prtg(id_cpu, "cpu") if id_cpu > 0 else (0.0, None, False)
    v_ram, p_ram, ok_ram = obtener_valor_prtg(id_ram, "ram") if id_ram > 0 else (0.0, None, False)
    v_red, _, ok_red = obtener_valor_prtg(id_red, "red") if id_red > 0 else (0.0, None, False)
    v_lat, _, ok_lat = obtener_valor_prtg(id_lat, "latencia") if id_lat > 0 else (0.0, None, False)
    
    # Bucle optimizado para los 6 Discos (Solo consulta si el ID es válido)
    discos_res = {}
    for i in range(1, 7):
        id_disco = int(config_servidor.get(f'id_sensor_disco_{i}', 0) or 0)
        if id_disco > 0:
            v_disc, p_disc, ok_disc = obtener_valor_prtg(id_disco, "disco")
            discos_res[f'd_{i}'] = v_disc
            discos_res[f'p_{i}'] = p_disc if p_disc is not None else 0.0
            discos_res[f'ok_{i}'] = ok_disc
        else:
            discos_res[f'd_{i}'] = None
            discos_res[f'p_{i}'] = None
            discos_res[f'ok_{i}'] = False

    # Bucle ampliado completo (1 a 8) para la captura limpia de Servicios de Core Bancario
    servicios_res = {}
    for i in range(1, 9):
        id_servicio = int(config_servidor.get(f'id_sensor_servicio_{i}', 0) or 0)
        if id_servicio > 0:
            v_serv, _, ok_serv = obtener_valor_prtg(id_servicio, "servicio")
            servicios_res[f's_{i}'] = "ON" if (ok_serv and v_serv == 1) else "OFF"
        else:
            servicios_res[f's_{i}'] = None  # Indica que el sensor no está registrado en este servidor

    # 3. Consolidación inteligente de datos
    any_prtg_ok = any([ok_cpu, ok_ram, ok_red, ok_lat]) or any(discos_res[f'ok_{i}'] for i in range(1, 7))

    if any_prtg_ok:
        data["cpu"] = v_cpu if ok_cpu else cpu_l
        data["ram"] = v_ram if ok_ram else ram_l
        data["pct_ram"] = p_ram if (ok_ram and p_ram > 0.0) else pct_ram_l
        data["red"] = v_red if ok_red else 0.0
        data["latencia"] = v_lat if ok_lat else 0.0
        
        # Inyección de Telemetría de Almacenamiento Dinámico
        for i in range(1, 7):
            data[f"disco_{i}"] = discos_res[f"d_{i}"]
            data[f"pct_disco_{i}"] = discos_res[f"p_{i}"]

        # Inyección Completa de los 8 Canales de Servicios
        for i in range(1, 9):
            data[f"servicio_{i}"] = servicios_res[f"s_{i}"]
            
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data