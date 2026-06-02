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
    Recibe el tipo_metrica ('cpu', 'ram', 'disco', 'red', 'latencia', 'servicio') para aplicar escalas dinámicas.
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
                
                # === ESCALAS DINÁMICAS POR TIPO DE MÉTRICA ===
                if tipo_metrica == "red":
                    return round(raw_val / 1024 / 1024, 2) if raw_val > 0 else 0.0, True
                
                elif tipo_metrica == "latencia":
                    return round(raw_val, 2), True
                
                elif tipo_metrica in ["ram", "disco"]:
                    # Convierte Bytes crudos de PRTG a Gigabytes (GB) Líquidos
                    val_gb = round(raw_val / 1073741824, 2) if raw_val > 0 else 0.0
                    return val_gb, True
                
                elif tipo_metrica == "servicio":
                    # Los servicios devuelven estado lógico binario directamente en PRTG
                    return int(raw_val), True
                
                else: 
                    final_val = raw_val / 10 if raw_val > 100 else raw_val
                    return round(float(final_val), 2), True
    except:
        pass
    return 0.0, False

def obtener_telemetria_total(config_servidor):
    """
    Calcula telemetría con respaldo local instantáneo y mapeo dinámico multidisco (1 al 6) y multiservicio (1 al 5).
    """
    # Lectura de contingencia local inmediata
    cpu_l = float(psutil.cpu_percent(interval=None))
    
    # Contingencia local de RAM: Convierte la memoria disponible local de bytes a GB reales
    ram_disponible_local = float(psutil.virtual_memory().available)
    ram_l = round(ram_disponible_local / 1073741824, 2)
    
    # Inicialización del payload de datos mapeado a la estructura final de 6 Discos y 5 Servicios
    data = {
        "cpu": cpu_l, 
        "ram": ram_l, 
        "red": 0.0, 
        "latencia": 0.0, 
        "disco_1": 0.0, "disco_2": 0.0, "disco_3": 0.0, "disco_4": 0.0, "disco_5": 0.0, "disco_6": 0.0,
        "servicio_1": 0, "servicio_2": 0, "servicio_3": 0, "servicio_4": 0, "servicio_5": 0,
        "msg": "💻 (MODO LOCAL)"
    }

    # Extracción de sensores base
    id_cpu = config_servidor.get('id_sensor_cpu', 0)
    id_ram = config_servidor.get('id_sensor_ram', 0)
    id_red = config_servidor.get('id_sensor_red', 0)
    id_lat = config_servidor.get('id_sensor_latencia', 0)
    
    # Consultas individuales base pasando tipo de métrica
    v_cpu, ok_cpu = obtener_valor_prtg(id_cpu, "cpu")
    v_ram, ok_ram = obtener_valor_prtg(id_ram, "ram")
    v_red, ok_red = obtener_valor_prtg(id_red, "red")
    v_lat, ok_lat = obtener_valor_prtg(id_lat, "latencia")
    
    # Lista de banderas para verificar el estado de la red PRTG
    banderas_ok = [ok_cpu, ok_ram, ok_red, ok_lat]
    
    # MATRIZ DE ALMACENAMIENTO: Extracción para los 6 sensores de disco en paralelo
    discos_resultados = {}
    for i in range(1, 7):
        id_disco = config_servidor.get(f'id_sensor_disco_{i}', 0)
        v_disc, ok_disc = obtener_valor_prtg(id_disco, "disco")
        discos_resultados[f'disco_{i}'] = v_disc
        discos_resultados[f'ok_disco_{i}'] = ok_disc
        banderas_ok.append(ok_disc)

    # MATRIZ DE SERVICIOS: Extracción para los 5 sensores de servicio en paralelo
    servicios_resultados = {}
    for i in range(1, 6):
        id_servicio = config_servidor.get(f'id_sensor_servicio_{i}', 0)
        v_serv, ok_serv = obtener_valor_prtg(id_servicio, "servicio")
        servicios_resultados[f'servicio_{i}'] = v_serv if ok_serv else 0
        banderas_ok.append(ok_serv)
    
    # Si al menos un sensor de PRTG (base, discos o servicios) responde con éxito, conmutamos a ONLINE
    if any(banderas_ok):
        data["cpu"] = v_cpu if ok_cpu else cpu_l
        data["ram"] = v_ram if ok_ram else ram_l
        data["red"] = v_red if ok_red else 0.0
        data["latencia"] = v_lat if ok_lat else 0.0
        
        # Inyección dinámica de almacenamiento procesado (1 al 6)
        for i in range(1, 7):
            data[f"disco_{i}"] = discos_resultados[f"disco_{i}"] if discos_resultados[f"ok_disco_{i}"] else 0.0

        # Inyección dinámica de estado de servicios procesado (1 al 5)
        for i in range(1, 6):
            data[f"servicio_{i}"] = servicios_resultados[f"servicio_{i}"]
            
        data["msg"] = "🛰️ (PRTG ONLINE)"

    return data