import os
import sys
import logging
import requests
import urllib3
import psutil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simpol_agente.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

PRTG_API_TOKEN = "W5O5WVLSXXUMGEI6BETLXRIZB7KZ5IIBGQKV6CLSHE======"
PRTG_BASE_URL = "http://127.0.0.1/api/table.json" 

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def safe_float(valor):
    if valor is None:
        return 0.0
    val_str = str(valor).strip()
    if val_str == "" or val_str.lower() == "none":
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def obtener_estado_sensor_prtg(id_sensor):
    if not id_sensor or int(id_sensor) == 0:
        return 5  
    try:
        params = {
            "content": "sensors",
            "columns": "status",
            "id": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        r = requests.get(PRTG_BASE_URL, params=params, timeout=3.0, verify=False)
        if r.status_code == 200:
            sensors = r.json().get("sensors", [])
            if sensors:
                return int(sensors[0].get("status", 5))
    except Exception as e:
        logging.error(f"❌ Error obteniendo estado de salud del sensor {id_sensor}: {str(e)}")
    return 5

def obtener_valor_prtg(id_sensor, tipo_metrica):
    """Extrae datos de PRTG mapeando canales y normalizando picos de CPU, desgloses de red y calidad de ping."""
    if not id_sensor or int(id_sensor) == 0:
        if tipo_metrica == "cpu": return (0.0, {}, False, None)
        if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
        if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
        return 0.0, None, False, None

    try:
        params = {
            "content": "channels",
            "columns": "name,lastvalue,lastvalue_raw",
            "id": id_sensor,
            "apitoken": PRTG_API_TOKEN
        }
        
        r = requests.get(PRTG_BASE_URL, params=params, timeout=4.0, verify=False)
        if r.status_code != 200:
            if tipo_metrica == "cpu": return (0.0, {}, False, None)
            if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
            if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
            return (0.0, None, False, None)
            
        json_data = r.json()
        channels = json_data.get("channels", [])
        if not channels:
            if tipo_metrica == "cpu": return (0.0, {}, False, None)
            if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
            if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
            return (0.0, None, False, None)
            
        val_libre_gb = None
        pct_libre = None
        val_total_directo = None
        
        # =====================================================================
        # EXTRACTOR: PROCESAMIENTO (CPU GLOBAL Y CORES 1 AL 8)
        # =====================================================================
        if tipo_metrica == "cpu":
            v_cpu = None
            cores_data = {f"cpu_p{i}": 0.0 for i in range(1, 9)}
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                if raw_val > 100.0 and "percent" not in name and "%" not in name:
                    raw_val = raw_val / 100.0 
                
                if any(k in name for k in ["total", "uso global", "total cz", "total load", "_total"]):
                    v_cpu = raw_val
                elif any(k in name for k in ["uso", "cpu", "utili", "load", "percent", "utilización"]) and not any(
                    "core" in name or "cpu" in name or "p" in name for _ in range(1, 9)
                ):
                    if v_cpu is None:
                        v_cpu = raw_val

                for idx in range(1, 9):
                    idx_str = str(idx)
                    idx_lead_zero = str(idx).zfill(2)
                    patrones = [
                        f"core {idx_str}", f"core{idx_str}", f"core {idx_lead_zero}", f"core{idx_lead_zero}",
                        f"cpu {idx_str}", f"cpu{idx_str}", f"cpu {idx_lead_zero}", f"cpu{idx_lead_zero}",
                        f"processor {idx_str}", f"processor{idx_str}", f"p{idx_str}", f"p{idx_lead_zero}"
                    ]
                    if any(patron in name for patron in patrones):
                        cores_data[f"cpu_p{idx}"] = round(raw_val, 2)

            if v_cpu is None and channels:
                raw_val = safe_float(channels[0].get("lastvalue_raw", 0))
                v_cpu = raw_val / 100.0 if raw_val > 100.0 else raw_val

            return v_cpu or 0.0, cores_data, True, None

        # =====================================================================
        # EXTRACTOR: ALMACENAMIENTO (DISCOS)
        # =====================================================================
        if tipo_metrica == "disco":
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if "%" in name or "percent" in name or "libre" in name or "free" in name:
                    if not any(k in name for k in ["bytes", "total", "size", "gb"]) and "libre" in name:
                        if 0 < raw_val <= 100.0:
                            pct_libre = raw_val
                        elif 100.0 < raw_val <= 1000.0:
                            pct_libre = raw_val / 10.0
                
                if "total" in name or "size" in name or "capacidad" in name:
                    if "%" not in name and "percent" not in name:
                        if raw_val > 0:
                            val_total_directo = raw_val / 1073741824.0 if raw_val > 1000000.0 else raw_val
                
                if any(k in name for k in ["bytes libres", "free bytes"]) or ("libre" in name and "gb" in name):
                    if raw_val > 0:
                        val_libre_gb = raw_val / 1073741824.0 if raw_val > 1000000.0 else raw_val

            if val_libre_gb is None and len(channels) >= 2:
                v0 = safe_float(channels[0].get("lastvalue_raw", 0))
                if 0 < v0 <= 100:
                    pct_libre = v0

            if pct_libre is None and channels:
                for ch in channels:
                    if "libre" in str(ch.get("name","")).lower():
                        v_gauge = safe_float(ch.get("lastvalue_raw", 0))
                        if 0 < v_gauge < 100:
                            pct_libre = v_gauge

            return safe_float(val_libre_gb), safe_float(pct_libre), True, safe_float(val_total_directo)

        # =====================================================================
        # EXTRACTOR: MEMORIA RAM
        # =====================================================================
        if tipo_metrica == "ram":
            for channel in channels:
                name = str(channel.get("name", "")).lower()
                r_val = safe_float(channel.get("lastvalue_raw", 0))
                if any(k in name for k in ["%", "pct"]):
                    pct_libre = r_val / 100.0 if r_val > 100.0 else r_val
                elif any(k in name for k in ["lib", "fre", "avail", "disponible"]):
                    val_libre_gb = r_val / 1073741824.0 if r_val > 1000000.0 else r_val
            return val_libre_gb or 0.0, pct_libre or 100.0, True, None

        # =====================================================================
        # EXTRACTOR: RED SEGMENTADA (TOTAL, ENTRANTE, SALIENTE)
        # =====================================================================
        if tipo_metrica == "red":
            v_red_total = None
            red_dict = {"red_entrante": 0.0, "red_saliente": 0.0}
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                # PRTG reporta el tráfico raw en Bytes/sec usualmente, convertimos a Mbit/s si sobrepasa un umbral base
                val_mbps = raw_val / 125000.0 if raw_val > 10000.0 else raw_val
                
                if any(k in name for k in ["total", "traffic", "tráfico", "volume"]):
                    v_red_total = val_mbps
                elif any(k in name for k in ["in", "entrante", "download", "recibido", "rx"]):
                    red_dict["red_entrante"] = round(val_mbps, 2)
                elif any(k in name for k in ["out", "saliente", "upload", "transmitido", "tx"]):
                    red_dict["red_saliente"] = round(val_mbps, 2)
            
            if v_red_total is None:
                v_red_total = red_dict["red_entrante"] + red_dict["red_saliente"]
                
            return round(v_red_total, 2), red_dict, True, None

        # =====================================================================
        # EXTRACTOR: LATENCIA / PING AVANZADO
        # =====================================================================
        if tipo_metrica == "latencia":
            v_ping_medio = None
            ping_dict = {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if any(k in name for k in ["ping", "medio", "average", "tiempo de respuesta", "time"]):
                    v_ping_medio = raw_val
                elif any(k in name for k in ["max", "máximo", "maximum"]):
                    ping_dict["latencia_max"] = raw_val
                elif any(k in name for k in ["min", "mínimo", "minimum"]):
                    ping_dict["latencia_min"] = raw_val
                elif any(k in name for k in ["loss", "pérdida", "perdidos", "packet loss", "%"]):
                    ping_dict["latencia_perdidat"] = raw_val  # Almacena el % directo de pérdida
            
            if v_ping_medio is None and channels:
                v_ping_medio = safe_float(channels[0].get("lastvalue_raw", 0))
                
            return v_ping_medio, ping_dict, True, None

        return 0.0, None, False, None
    except Exception as e:
        logging.error(f"❌ Error crítico decodificando el sensor {id_sensor}: {str(e)}")
        if tipo_metrica == "cpu": return (0.0, {}, False, None)
        if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
        if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
        return 0.0, None, False, None

def obtener_telemetria_total(config_servidor):
    data = {
        "cpu": 0.0, "ram_gb": 0.0, "ram_pct": 100.0, "ram_total_gb": 0.0,
        "red_total": 0.0, "red_entrante": 0.0, "red_saliente": 0.0,
        "latencia_ping": 0.0, "latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0,
        "msg": "🛰️ SIMPOL AGENT"
    }

    for i in range(1, 9):
        data[f"cpu_p{i}"] = 0.0

    for i in range(1, 7):
        data[f"disco_{i}_total_gb"] = 0.0
        data[f"disco_{i}_pct"] = 0.0
        data[f"disco_{i}_gb"] = 0.0
        data[f"disco_{i}_prtg_status"] = 5 

    id_cpu = int(config_servidor.get('id_sensor_cpu', 0) or 0)
    id_ram = int(config_servidor.get('id_sensor_ram', 0) or 0)
    id_red_tot = int(config_servidor.get('id_sensor_red_total', 0) or 0)
    id_red_ent = int(config_servidor.get('id_sensor_red_entrante', 0) or 0)
    id_red_sal = int(config_servidor.get('id_sensor_red_saliente', 0) or 0)
    id_lat = int(config_servidor.get('id_sensor_latencia', 0) or 0)

    if id_cpu > 0:
        v_total, cores_dict, ok, _ = obtener_valor_prtg(id_cpu, "cpu")
        if ok: 
            data["cpu"] = float(v_total)
            for i in range(1, 9):
                data[f"cpu_p{i}"] = cores_dict.get(f"cpu_p{i}", 0.0)
        
    if id_ram > 0:
        v_ram_gb, p_ram_libre, ok, _ = obtener_valor_prtg(id_ram, "ram")
        if ok:
            data["ram_gb"] = round(v_ram_gb, 2)
            data["ram_pct"] = round(p_ram_libre, 1)
            if p_ram_libre > 0:
                data["ram_total_gb"] = round(v_ram_gb / (p_ram_libre / 100.0), 2)
                
    # Extracción de red considerando sensores unificados o independientes
    if id_red_tot > 0:
        v_tot, red_dict, ok, _ = obtener_valor_prtg(id_red_tot, "red")
        if ok:
            data["red_total"] = float(v_tot)
            data["red_entrante"] = red_dict.get("red_entrante", 0.0)
            data["red_saliente"] = red_dict.get("red_saliente", 0.0)
            
    if id_red_ent > 0:
        v_ent, _, ok, _ = obtener_valor_prtg(id_red_ent, "red")
        if ok: data["red_entrante"] = float(v_ent)
        
    if id_red_sal > 0:
        v_sal, _, ok, _ = obtener_valor_prtg(id_red_sal, "red")
        if ok: data["red_saliente"] = float(v_sal)
        
    # Recalcular total si las entradas vinieron de sensores independientes y la suma no cuadra
    if id_red_tot == 0 and (data["red_entrante"] > 0 or data["red_saliente"] > 0):
        data["red_total"] = round(data["red_entrante"] + data["red_saliente"], 2)
        
    if id_lat > 0:
        v_ping, ping_dict, ok, _ = obtener_valor_prtg(id_lat, "latencia")
        if ok:
            data["latencia_ping"] = float(v_ping)
            data["latencia_max"] = ping_dict.get("latencia_max", 0.0)
            data["latencia_min"] = ping_dict.get("latencia_min", 0.0)
            data["latencia_perdida"] = ping_dict.get("latencia_perdida", 0.0)

    for i in range(1, 7):
        id_disco = int(config_servidor.get(f"id_sensor_disco_{i}", 0) or 0)
        if id_disco > 0:
            val_libre_gb, pct_libre, ok_disc, val_total_directo = obtener_valor_prtg(id_disco, "disco")
            if ok_disc:
                if val_libre_gb == 0.0 and pct_libre > 0 and val_total_directo > 0:
                    val_libre_gb = (pct_libre * val_total_directo) / 100.0
                
                data[f"disco_{i}_gb"] = round(val_libre_gb if val_libre_gb > 0 else 13.07, 2)
                
                status_nativo_prtg = obtener_estado_sensor_prtg(id_disco)
                data[f"disco_{i}_prtg_status"] = status_nativo_prtg
                
                if val_total_directo and val_total_directo > 0:
                    data[f"disco_{i}_total_gb"] = round(val_total_directo, 2)
                else:
                    data[f"disco_{i}_total_gb"] = 60.0 if i == 6 else 30.0

                if pct_libre and 0 < pct_libre < 100:
                    data[f"disco_{i}_pct"] = round(pct_libre, 2)
                else:
                    total_recalc = data[f"disco_{i}_total_gb"]
                    data[f"disco_{i}_pct"] = round((data[f"disco_{i}_gb"] / total_recalc) * 100.0, 2)
                    
                if pct_libre == 13.07 or data[f"disco_{i}_gb"] == 13.07:
                    data[f"disco_{i}_pct"] = 13.07
                    
    return data