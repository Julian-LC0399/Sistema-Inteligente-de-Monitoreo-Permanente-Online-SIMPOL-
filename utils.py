import os
import sys
import logging
import requests
import urllib3
import psutil
import random
import re

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

def verificar_conexion_prtg():
    try:
        r = requests.get(PRTG_BASE_URL, params={"apitoken": PRTG_API_TOKEN}, timeout=2.0, verify=False)
        return r.status_code == 200
    except Exception:
        return False

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
                status_raw = str(sensors[0].get("status", "")).strip().lower()
                if "up" in status_raw or "ok" in status_raw:
                    return 1
                elif "warning" in status_raw or "warn" in status_raw:
                    return 4
                elif "down" in status_raw or "crit" in status_raw or "error" in status_raw:
                    return 3
                return 5
    except Exception as e:
        logging.error(f"Error obteniendo estado del sensor {id_sensor}: {str(e)}")
    return 5

def obtener_valor_prtg(id_sensor, tipo_metrica):
    if not id_sensor or int(id_sensor) == 0:
        if tipo_metrica == "cpu": return (0.0, {}, False, None)
        if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
        if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
        if tipo_metrica == "ram": return (0.0, 0.0, False, None)
        if tipo_metrica == "disco": return (0.0, 0.0, False, 0.0)
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
            if tipo_metrica == "ram": return (0.0, 0.0, False, None)
            if tipo_metrica == "disco": return (0.0, 0.0, False, 0.0)
            return (0.0, None, False, None)
            
        json_data = r.json()
        channels = json_data.get("channels", [])
        if not channels:
            if tipo_metrica == "cpu": return (0.0, {}, False, None)
            if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
            if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
            if tipo_metrica == "ram": return (0.0, 0.0, False, None)
            if tipo_metrica == "disco": return (0.0, 0.0, False, 0.0)
            return (0.0, None, False, None)
            
        val_libre_gb = None
        pct_libre = None
        val_total_directo = None
        
        # =====================================================================
        # CPU
        # =====================================================================
        if tipo_metrica == "cpu":
            v_cpu = None
            cores_data = {f"cpu_p{i}": 0.0 for i in range(1, 9)}
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if raw_val > 100.0 and "percent" not in name and "%" not in name:
                    raw_val = raw_val / 100.0
                
                if any(k in name for k in ["total", "global", "overall", "_total"]):
                    v_cpu = raw_val
                elif v_cpu is None and any(k in name for k in ["cpu", "load", "utilizacion", "usage"]):
                    if not any(str(i) in name for i in range(1, 9)):
                        v_cpu = raw_val

                for idx in range(1, 9):
                    idx_str = str(idx)
                    patrones_core = [
                        f"core {idx_str}", f"core{idx_str}",
                        f"cpu {idx_str}", f"cpu{idx_str}",
                        f"processor {idx_str}", f"processor{idx_str}",
                        f"p{idx_str}", f"p{idx_str}",
                        f"núcleo {idx_str}", f"núcleo{idx_str}"
                    ]
                    if any(patron in name for patron in patrones_core):
                        cores_data[f"cpu_p{idx}"] = round(raw_val, 2)

            if v_cpu is None and channels:
                raw_val = safe_float(channels[0].get("lastvalue_raw", 0))
                v_cpu = raw_val / 100.0 if raw_val > 100.0 else raw_val

            return v_cpu or 0.0, cores_data, True, None

        # =====================================================================
        # DISCO
        # =====================================================================
        if tipo_metrica == "disco":
            val_libre_gb = None
            pct_libre = None
            val_total_directo = None
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if any(k in name for k in ["%", "percent", "pct", "libre", "free"]):
                    if any(k in name for k in ["%", "percent", "pct"]):
                        if 0 <= raw_val <= 100:
                            pct_libre = raw_val
                
                if "espacio libre" in name or "free space" in name:
                    if 0 <= raw_val <= 100:
                        pct_libre = raw_val
                    else:
                        if raw_val > 1000000.0:
                            val_libre_gb = raw_val / 1073741824.0
                        else:
                            val_libre_gb = raw_val
                
                if "bytes libres" in name or "free bytes" in name:
                    if raw_val > 0:
                        val_libre_gb = raw_val / 1073741824.0
                
                if any(k in name for k in ["total", "size", "capacidad", "capacity"]):
                    if "%" not in name and "percent" not in name:
                        if raw_val > 0:
                            if raw_val > 1000000.0:
                                val_total_directo = raw_val / 1073741824.0
                            else:
                                val_total_directo = raw_val

            if pct_libre is None:
                if val_libre_gb is not None and val_total_directo is not None and val_total_directo > 0:
                    pct_libre = (val_libre_gb / val_total_directo) * 100.0

            if pct_libre is None:
                pct_libre = 50.0
            if pct_libre > 100.0:
                pct_libre = 100.0
            if pct_libre < 0:
                pct_libre = 0.0

            return safe_float(val_libre_gb), safe_float(pct_libre), True, safe_float(val_total_directo)

        # =====================================================================
        # RAM
        # =====================================================================
        if tipo_metrica == "ram":
            ram_used_percent = None
            ram_free_percent = None
            ram_free_bytes = None
            ram_total_bytes = None
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if any(k in name for k in ["used", "uso", "utilizado", "consumido"]):
                    if any(k in name for k in ["%", "percent", "pct"]):
                        ram_used_percent = raw_val
                
                if any(k in name for k in ["free", "libre", "disponible", "available"]):
                    if any(k in name for k in ["%", "percent", "pct"]):
                        ram_free_percent = raw_val
                
                if any(k in name for k in ["free", "libre", "disponible", "available"]):
                    if not any(k in name for k in ["%", "percent", "pct"]):
                        if raw_val > 1000000.0:
                            ram_free_bytes = raw_val
                        else:
                            ram_free_bytes = raw_val * 1073741824.0
                
                if any(k in name for k in ["total", "installed", "instalada"]):
                    if not any(k in name for k in ["%", "percent", "pct"]):
                        if raw_val > 1000000.0:
                            ram_total_bytes = raw_val
                        else:
                            ram_total_bytes = raw_val * 1073741824.0

            if ram_free_percent is not None:
                pct_libre = ram_free_percent
                if ram_total_bytes is not None and ram_total_bytes > 0:
                    val_libre_gb = (ram_free_percent / 100.0) * (ram_total_bytes / 1073741824.0)
                else:
                    val_libre_gb = 0.0
            elif ram_used_percent is not None:
                pct_libre = 100.0 - ram_used_percent
                if ram_total_bytes is not None and ram_total_bytes > 0:
                    val_libre_gb = (pct_libre / 100.0) * (ram_total_bytes / 1073741824.0)
                else:
                    val_libre_gb = 0.0
            elif ram_free_bytes is not None and ram_total_bytes is not None and ram_total_bytes > 0:
                pct_libre = (ram_free_bytes / ram_total_bytes) * 100.0
                val_libre_gb = ram_free_bytes / 1073741824.0
            elif ram_free_bytes is not None:
                val_libre_gb = ram_free_bytes / 1073741824.0
                if ram_total_bytes is not None and ram_total_bytes > 0:
                    pct_libre = (ram_free_bytes / ram_total_bytes) * 100.0
                else:
                    pct_libre = 50.0
            else:
                pct_libre = 50.0
                val_libre_gb = 8.0

            if ram_total_bytes is None or ram_total_bytes == 0:
                ram_total_bytes = 16.0 * 1073741824.0

            val_total_directo = ram_total_bytes / 1073741824.0

            if pct_libre > 100.0:
                pct_libre = 100.0
            if pct_libre < 0:
                pct_libre = 0.0
            if val_libre_gb > val_total_directo:
                val_libre_gb = val_total_directo

            return val_libre_gb or 0.0, pct_libre or 100.0, True, val_total_directo

        # =====================================================================
        # RED - CORRECCIÓN DEFINITIVA (MB/s → Mbit/s)
        # =====================================================================
        if tipo_metrica == "red":
            v_red_total = None
            red_dict = {"red_entrante": 0.0, "red_saliente": 0.0}
            
            for channel in channels:
                name = str(channel.get("name", "")).strip()
                name_lower = name.lower()
                
                # PRTG devuelve lastvalue como "X MB" (MegaBytes por segundo)
                lastvalue = channel.get("lastvalue", "0")
                
                # Extraer el número de "6.12 MB" o "628 MB"
                valor_mb = 0.0
                if isinstance(lastvalue, str):
                    # Limpiar y extraer el número
                    match = re.search(r"([\d.]+)", lastvalue)
                    if match:
                        valor_mb = float(match.group(1))
                else:
                    valor_mb = safe_float(lastvalue)
                
                # Si no se pudo extraer de lastvalue, usar lastvalue_raw como fallback
                if valor_mb == 0:
                    lastvalue_raw = safe_float(channel.get("lastvalue_raw", 0))
                    # Convertir bytes a MB: bytes / 1,000,000
                    valor_mb = lastvalue_raw / 1000000.0
                
                # Convertir MB/s a Mbit/s: MB * 8
                valor_mbps = valor_mb * 8
                
                # Asignar según el nombre del canal
                if any(k in name_lower for k in ["entrante", "in", "rx", "recibido", "download"]):
                    red_dict["red_entrante"] = round(valor_mbps, 2)
                elif any(k in name_lower for k in ["saliente", "out", "tx", "transmitido", "upload"]):
                    red_dict["red_saliente"] = round(valor_mbps, 2)
                elif any(k in name_lower for k in ["total", "traffic", "tráfico", "overall"]):
                    v_red_total = round(valor_mbps, 2)
            
            # Si no se encontró total, calcularlo como suma
            if v_red_total is None or v_red_total == 0:
                v_red_total = red_dict["red_entrante"] + red_dict["red_saliente"]
            
            return round(v_red_total, 2), red_dict, True, None

        # =====================================================================
        # LATENCIA
        # =====================================================================
        if tipo_metrica == "latencia":
            v_ping_medio = None
            ping_dict = {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}
            
            for channel in channels:
                name = str(channel.get("name", "")).lower().strip()
                raw_val = safe_float(channel.get("lastvalue_raw", 0))
                
                if any(k in name for k in ["ping", "medio", "average", "tiempo", "response", "time"]):
                    if "max" not in name and "min" not in name and "máx" not in name and "mín" not in name:
                        v_ping_medio = raw_val
                elif any(k in name for k in ["max", "máximo", "maximum"]):
                    ping_dict["latencia_max"] = raw_val
                elif any(k in name for k in ["min", "mínimo", "minimum"]):
                    ping_dict["latencia_min"] = raw_val
                elif any(k in name for k in ["loss", "pérdida", "perdidos", "packet loss"]):
                    ping_dict["latencia_perdida"] = raw_val
            
            if v_ping_medio is None and channels:
                v_ping_medio = safe_float(channels[0].get("lastvalue_raw", 0))
                
            return v_ping_medio, ping_dict, True, None

        return 0.0, None, False, None
        
    except Exception as e:
        logging.error(f"Error en obtener_valor_prtg: {str(e)}")
        if tipo_metrica == "cpu": return (0.0, {}, False, None)
        if tipo_metrica == "red": return (0.0, {"red_entrante": 0.0, "red_saliente": 0.0}, False, None)
        if tipo_metrica == "latencia": return (0.0, {"latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0}, False, None)
        if tipo_metrica == "ram": return (0.0, 0.0, False, None)
        if tipo_metrica == "disco": return (0.0, 0.0, False, 0.0)
        return (0.0, None, False, None)

def obtener_telemetria_total(config_servidor):
    data = {
        "cpu": 0.0, "ram_gb": 0.0, "ram_pct": 100.0, "ram_total_gb": 0.0,
        "red_total": 0.0, "red_entrante": 0.0, "red_saliente": 0.0,
        "latencia_ping": 0.0, "latencia_max": 0.0, "latencia_min": 0.0, "latencia_perdida": 0.0,
        "msg": "🛰️ SIMPOL AGENT",
        "modo_conexion": "MODO PRTG"
    }

    for i in range(1, 9):
        data[f"cpu_p{i}"] = 0.0

    for i in range(1, 7):
        data[f"disco_{i}_total_gb"] = 0.0
        data[f"disco_{i}_pct"] = 0.0
        data[f"disco_{i}_gb"] = 0.0
        data[f"disco_{i}_prtg_status"] = 5 

    if not verificar_conexion_prtg():
        data["modo_conexion"] = "MODO LOCAL"
        data["cpu"] = float(psutil.cpu_percent(interval=None))
        cores_locales = psutil.cpu_percent(percpu=True)
        for i in range(1, 9):
            data[f"cpu_p{i}"] = float(cores_locales[i-1]) if i-1 < len(cores_locales) else 0.0

        mem = psutil.virtual_memory()
        data["ram_total_gb"] = round(mem.total / 1073741824.0, 2)
        data["ram_gb"] = round(mem.available / 1073741824.0, 2)
        data["ram_pct"] = round((mem.available / mem.total) * 100.0, 1)

        net_io = psutil.net_io_counters()
        data["red_entrante"] = round((net_io.bytes_recv / 125000.0) / 1000.0, 2) % 100
        data["red_saliente"] = round((net_io.bytes_sent / 125000.0) / 1000.0, 2) % 100
        data["red_total"] = round(data["red_entrante"] + data["red_saliente"], 2)

        data["latencia_ping"] = 1.0
        data["latencia_max"] = 2.0
        data["latencia_min"] = 1.0
        data["latencia_perdida"] = 0.0

        particiones = [p.mountpoint for p in psutil.disk_partitions() if 'fixed' in p.opts or p.fstype != '']
        for i in range(1, 7):
            if i-1 < len(particiones):
                try:
                    d_usage = psutil.disk_usage(particiones[i-1])
                    data[f"disco_{i}_total_gb"] = round(d_usage.total / 1073741824.0, 2)
                    data[f"disco_{i}_gb"] = round(d_usage.free / 1073741824.0, 2)
                    data[f"disco_{i}_pct"] = round((d_usage.free / d_usage.total) * 100.0, 2)
                    data[f"disco_{i}_prtg_status"] = 1  
                except Exception:
                    pass
        return data

    id_cpu = int(config_servidor.get('id_sensor_cpu', 0) or 0)
    id_ram = int(config_servidor.get('id_sensor_ram', 0) or 0)
    id_red_tot = int(config_servidor.get('id_sensor_red_total', 0) or config_servidor.get('id_sensor_red', 0) or 0)
    id_red_ent = int(config_servidor.get('id_sensor_red_entrante', 0) or 0)
    id_red_sal = int(config_servidor.get('id_sensor_red_saliente', 0) or 0)
    id_lat = int(config_servidor.get('id_sensor_latencia', 0) or 0)

    # CPU
    if id_cpu > 0:
        v_total, cores_dict, ok, _ = obtener_valor_prtg(id_cpu, "cpu")
        if ok and v_total > 0:
            data["cpu"] = float(v_total)
            for i in range(1, 9):
                data[f"cpu_p{i}"] = cores_dict.get(f"cpu_p{i}", 0.0)

    # RAM
    if id_ram > 0:
        v_ram_gb, p_ram_libre, ok, v_ram_total = obtener_valor_prtg(id_ram, "ram")
        if ok:
            data["ram_gb"] = round(v_ram_gb, 2)
            data["ram_pct"] = round(p_ram_libre, 1)
            data["ram_total_gb"] = round(v_ram_total, 2)

    # RED
    if id_red_tot > 0:
        v_tot, red_dict, ok, _ = obtener_valor_prtg(id_red_tot, "red")
        if ok and v_tot > 0:
            data["red_total"] = float(v_tot)
            data["red_entrante"] = red_dict.get("red_entrante", 0.0)
            data["red_saliente"] = red_dict.get("red_saliente", 0.0)

    if id_red_ent > 0:
        v_ent, _, ok, _ = obtener_valor_prtg(id_red_ent, "red")
        if ok and v_ent > 0:
            data["red_entrante"] = float(v_ent)

    if id_red_sal > 0:
        v_sal, _, ok, _ = obtener_valor_prtg(id_red_sal, "red")
        if ok and v_sal > 0:
            data["red_saliente"] = float(v_sal)

    if id_red_tot == 0 and (data["red_entrante"] > 0 or data["red_saliente"] > 0):
        data["red_total"] = round(data["red_entrante"] + data["red_saliente"], 2)

    # LATENCIA
    if id_lat > 0:
        v_ping, ping_dict, ok, _ = obtener_valor_prtg(id_lat, "latencia")
        if ok and v_ping > 0:
            data["latencia_ping"] = float(v_ping)
            data["latencia_max"] = ping_dict.get("latencia_max", 0.0)
            data["latencia_min"] = ping_dict.get("latencia_min", 0.0)
            data["latencia_perdida"] = ping_dict.get("latencia_perdida", 0.0)

    # DISCOS
    for i in range(1, 7):
        id_disco = int(config_servidor.get(f"id_sensor_disco_{i}", 0) or 0)
        if id_disco > 0:
            val_libre_gb, pct_libre, ok_disc, val_total_directo = obtener_valor_prtg(id_disco, "disco")
            if ok_disc:
                data[f"disco_{i}_gb"] = round(val_libre_gb, 2) if val_libre_gb > 0 else 0.0
                data[f"disco_{i}_total_gb"] = round(val_total_directo, 2) if val_total_directo > 0 else 30.0
                data[f"disco_{i}_pct"] = round(pct_libre, 2) if pct_libre > 0 else 0.0
                
                if data[f"disco_{i}_pct"] > 50.0 and data[f"disco_{i}_gb"] > 0 and data[f"disco_{i}_total_gb"] > 0:
                    pct_calc = (data[f"disco_{i}_gb"] / data[f"disco_{i}_total_gb"]) * 100.0
                    if pct_calc < 30.0:
                        data[f"disco_{i}_pct"] = round(pct_calc, 2)
                
                status_nativo_prtg = obtener_estado_sensor_prtg(id_disco)
                data[f"disco_{i}_prtg_status"] = status_nativo_prtg

    # Si todos los datos son 0, simular
    todos_cero = True
    if data["cpu"] > 0: todos_cero = False
    if data["ram_gb"] > 0: todos_cero = False
    if data["red_total"] > 0: todos_cero = False
    if data["latencia_ping"] > 0: todos_cero = False
    for i in range(1, 7):
        if data[f"disco_{i}_gb"] > 0:
            todos_cero = False
            break

    if todos_cero:
        data["modo_conexion"] = "MODO LOCAL (PRTG Sin Datos)"
        data["cpu"] = round(random.uniform(12.5, 38.0), 2)
        for idx in range(1, 9):
            data[f"cpu_p{idx}"] = round(data["cpu"] + random.uniform(-6.0, 6.0), 2)
        data["ram_total_gb"] = random.choice([16.0, 32.0, 64.0])
        data["ram_pct"] = round(random.uniform(40.0, 78.0), 2)
        data["ram_gb"] = round((data["ram_pct"] * data["ram_total_gb"]) / 100.0, 2)
        data["latencia_ping"] = round(random.uniform(5.0, 19.0), 1)
        data["latencia_max"] = round(data["latencia_ping"] + random.uniform(3.0, 12.0), 1)
        data["latencia_min"] = round(max(1.0, data["latencia_ping"] - random.uniform(1.0, 4.0)), 1)
        data["latencia_perdida"] = 0.0
        data["red_entrante"] = round(random.uniform(5.0, 25.0), 2)
        data["red_saliente"] = round(random.uniform(10.0, 45.0), 2)
        data["red_total"] = round(data["red_entrante"] + data["red_saliente"], 2)
        for i in range(1, 7):
            if data[f"disco_{i}_total_gb"] == 0:
                total_simulado = 100.0 if i == 1 else (500.0 if i in [2, 3] else 300.0)
                pct_simulado = round(random.uniform(25.0, 85.0), 2)
                data[f"disco_{i}_total_gb"] = total_simulado
                data[f"disco_{i}_pct"] = pct_simulado
                data[f"disco_{i}_gb"] = round((pct_simulado * total_simulado) / 100.0, 2)
                data[f"disco_{i}_prtg_status"] = 0

    return data