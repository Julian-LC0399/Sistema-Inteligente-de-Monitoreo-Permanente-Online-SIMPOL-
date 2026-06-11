import os
import sys
import logging
import requests
import urllib3
import psutil

# Desactivar advertencias de seguridad para la red interna del banco (SSL auto-firmado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de Logs del Agente de Telemetría compartidos
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
    """Convierte de forma segura un valor a float, manejando vacíos o nulos."""
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
    Extrae métricas desde PRTG retornando una tupla triple optimizada:
    (Valor_Crudo/Principal, Porcentaje_o_Secundario, Estado_Lectura)
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
        
        r = requests.get(PRTG_BASE_URL, params=params, timeout=4.0, verify=False)
        
        if r.status_code == 200:
            json_data = r.json()
            channels = json_data.get("channels", [])
            
            if channels:
                val_crudo_principal = None
                pct_libre_detectado = None
                primer_canal_valido = None
                
                for channel in channels:
                    name = str(channel.get("name", "")).lower()
                    raw_val = safe_float(channel.get("lastvalue_raw", 0))
                    
                    if primer_canal_valido is None and raw_val > 0:
                        primer_canal_valido = raw_val
                    
                    # Detección de canales de porcentaje libre
                    if any(k in name for k in ["%", "pct", "percent", "porc"]):
                        if any(k in name for k in ["libre", "free", "disp", "avail"]):
                            pct_libre_detectado = raw_val
                        elif pct_libre_detectado is None and not any(k in name for k in ["usado", "used"]):
                            pct_libre_detectado = raw_val
                    else:
                        if any(k in name for k in ["libre", "free", "disp", "avail", "space", "bytes", "gb"]):
                            val_crudo_principal = raw_val

                if val_crudo_principal is None:
                    val_crudo_principal = primer_canal_valido if primer_canal_valido is not None else 0.0
                
                if pct_libre_detectado is None and tipo_metrica in ["ram", "disco"]:
                    # Fallback analítico de porcentaje si no viene explícito
                    for channel in channels:
                        raw_val = safe_float(channel.get("lastvalue_raw", 0))
                        if 0.1 <= raw_val <= 100.0 and raw_val != val_crudo_principal:
                            pct_libre_detectado = raw_val
                            break

                # Forzar escalado correcto de porcentajes de PRTG
                if pct_libre_detectado is not None:
                    while pct_libre_detectado > 100.0:
                        pct_libre_detectado /= 10.0

                if tipo_metrica == "red":
                    # Convertir Traffic a MB/s
                    return round(val_crudo_principal / 1024 / 1024, 2) if val_crudo_principal > 0 else 0.0, None, True
                
                elif tipo_metrica == "latencia":
                    return round(val_crudo_principal, 2), None, True
                
                elif tipo_metrica in ["ram", "disco"]:
                    # Retorna el valor crudo en bytes, el porcentaje libre y True
                    return val_crudo_principal, pct_libre_detectado, True
                
                elif tipo_metrica == "servicio":
                    return int(val_crudo_principal), None, True
                
                else:
                    return round(float(val_crudo_principal), 2), None, True
                    
    except Exception as e:
        logging.error(f"[utils.py] ❌ Error en consulta PRTG (Sensor {id_sensor}): {str(e)}")
            
    return 0.0, None, False

def obtener_telemetria_total(config_servidor):
    """Muestrea y calcula el diccionario integral V3.9 acoplado a la BD."""
    # 1. Captura de Fallback Local por si el sensor PRTG no responde o está en 0
    mem_local = psutil.virtual_memory()
    cpu_l = float(psutil.cpu_percent(interval=None))
    
    # Valores por defecto basados en máquina local
    data = {
        "cpu": cpu_l,
        "ram_bytes": int(mem_local.available),
        "ram_gb": round(float(mem_local.available) / 1073741824, 2),
        "ram_pct": round(mem_local.percent, 1),
        "ram_total_gb": round(float(mem_local.total) / 1073741824, 2),
        "red": 0.0,
        "latencia": 0.0,
        "msg": "💻 (MODO LOCAL)"
    }

    # Inicializar los 6 bloques de discos en 0 de forma estructurada
    for i in range(1, 7):
        data[f"disco_{i}_bytes"] = int(0)
        data[f"disco_{i}_gb"] = float(0.0)
        data[f"disco_{i}_pct"] = float(0.0)
        data[f"disco_{i}_total_gb"] = float(0.0)

    # Inicializar los 8 bloques de servicios corporativos
    for i in range(1, 9):
        data[f"servicio_{i}_estado"] = "INACTIVO"
        data[f"servicio_{i}_val"] = float(0.0)

    # 2. Extracción y Conversión desde PRTG si los IDs existen
    id_cpu = int(config_servidor.get('id_sensor_cpu', 0) or 0)
    id_ram = int(config_servidor.get('id_sensor_ram', 0) or 0)
    id_red = int(config_servidor.get('id_sensor_red', 0) or 0)
    id_lat = int(config_servidor.get('id_sensor_latencia', 0) or 0)

    v_cpu, _, ok_cpu = obtener_valor_prtg(id_cpu, "cpu") if id_cpu > 0 else (0.0, None, False)
    v_ram_bytes, p_ram_libre, ok_ram = obtener_valor_prtg(id_ram, "ram") if id_ram > 0 else (0.0, None, False)
    v_red, _, ok_red = obtener_valor_prtg(id_red, "red") if id_red > 0 else (0.0, None, False)
    v_lat, _, ok_lat = obtener_valor_prtg(id_lat, "latencia") if id_lat > 0 else (0.0, None, False)
    
    # Procesamiento de Discos Remotos (PRTG)
    discos_ok = []
    for i in range(1, 7):
        id_disco = int(config_servidor.get(f'id_sensor_disco_{i}', 0) or 0)
        if id_disco > 0:
            v_disc_bytes, p_disc_libre, ok_disc = obtener_valor_prtg(id_disco, "disco")
            if ok_disc and v_disc_bytes > 0:
                # Estructurar bytes (Garantía BIGINT)
                data[f"disco_{i}_bytes"] = int(v_disc_bytes)
                data[f"disco_{i}_gb"] = round(float(v_disc_bytes) / 1073741824, 2)
                
                # Calcular el porcentaje de USO real (Invertir si PRTG da el espacio libre)
                pct_real_uso = 100.0 - p_disc_libre if p_disc_libre is not None else 0.0
                data[f"disco_{i}_pct"] = round(max(0.0, min(100.0, pct_real_uso)), i)
                
                # Estimar el almacenamiento total del volumen remitiéndose al espacio absoluto
                data[f"disco_{i}_total_gb"] = round((float(v_disc_bytes) / (p_disc_libre / 100.0)) / 1073741824, 2) if (p_disc_libre and p_disc_libre > 0) else 100.0
                discos_ok.append(True)
                continue
        discos_ok.append(False)

    # Procesamiento de Servicios Remotos (PRTG)
    for i in range(1, 9):
        id_servicio = int(config_servidor.get(f'id_sensor_servicio_{i}', 0) or 0)
        if id_servicio > 0:
            v_serv, _, ok_serv = obtener_valor_prtg(id_servicio, "servicio")
            # Si el sensor responde y el canal principal es 1, el servicio está operando
            if ok_serv and v_serv == 1:
                data[f"servicio_{i}_estado"] = "ACTIVO"
                data[f"servicio_{i}_val"] = float(1.0)
            elif ok_serv and v_serv == 0:
                data[f"servicio_{i}_estado"] = "OFF"
                data[f"servicio_{i}_val"] = float(0.0)
            else:
                data[f"servicio_{i}_estado"] = "INACTIVO"
                data[f"servicio_{i}_val"] = float(0.0)

    # Consolidación final del origen de datos
    if any([ok_cpu, ok_ram, ok_red, ok_lat]) or any(discos_ok):
        if ok_cpu: data["cpu"] = float(v_cpu)
        if ok_ram and v_ram_bytes > 0:
            data["ram_bytes"] = int(v_ram_bytes)
            data["ram_gb"] = round(float(v_ram_bytes) / 1073741824, 2)
            data["ram_pct"] = round(100.0 - p_ram_libre, 1) if p_ram_libre is not None else data["ram_pct"]
        if ok_red: data["red"] = float(v_red)
        if ok_lat: data["latencia"] = float(v_lat)
        data["msg"] = "🛰️ (PRTG ONLINE V3.9)"

    return data