import time
import mysql.connector
from datetime import datetime
import sys
import os

# Importamos las funciones de la arquitectura real de utils.py
from utils import get_resource_path, obtener_telemetria_total

if getattr(sys, 'frozen', False):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

# =========================================================
# CONFIGURACIÓN DB - INTEGRAL BANCO CARONÍ
# =========================================================
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password", 
    "use_pure": True,
    "connect_timeout": 15
}

# Variable de control de ejecución para evitar escrituras fantasmas post-cierre
AGENTE_EN_EJECUCION = False

def log_agente(mensaje):
    """Escribe las trazas de auditoría únicamente si el motor está en ejecución activa."""
    if not AGENTE_EN_EJECUCION:
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{stamp}] {mensaje}\n"
    print(mensaje, flush=True)
    try:
        with open("simpol_agente.log", "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass

def ejecutar_motor_agente():
    """
    Núcleo del Demonio de Telemetría: Escanea secuencialmente cada servidor,
    extrae sus sensores indexados reales a través de utils.py conectándose a PRTG,
    y realiza los cálculos de estado aplicando el semáforo institucional del CSU.
    Filtra en BD para procesar SOLO servidores con al menos un sensor registrado.
    """
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 INICIANDO DEMONIO DE TELEMETRÍA AUTOMATIZADA SIMPOL (RED PRTG REAL)")
    log_agente("🔍 Escaneando topología de infraestructura con sensores válidos...")

    try:
        while AGENTE_EN_EJECUCION:
            conn_ins = None
            try:
                conn_ins = mysql.connector.connect(**DB_CONFIG)
                cursor_ins = conn_ins.cursor(dictionary=True)
                
                # Filtra servidores activos que tengan AL MENOS UN SENSOR configurado (> 0)
                query_servidores = """
                    SELECT * FROM servidores 
                    WHERE estado_monitoreo = 1 
                      AND (
                        COALESCE(id_sensor_cpu, 0) > 0 OR 
                        COALESCE(id_sensor_ram, 0) > 0 OR 
                        COALESCE(id_sensor_red, 0) > 0 OR 
                        COALESCE(id_sensor_latencia, 0) > 0 OR 
                        COALESCE(id_sensor_disco_1, 0) > 0 OR 
                        COALESCE(id_sensor_disco_2, 0) > 0 OR 
                        COALESCE(id_sensor_disco_3, 0) > 0 OR 
                        COALESCE(id_sensor_disco_4, 0) > 0 OR 
                        COALESCE(id_sensor_disco_5, 0) > 0 OR 
                        COALESCE(id_sensor_disco_6, 0) > 0 OR 
                        COALESCE(id_sensor_servicio_1, 0) > 0 OR 
                        COALESCE(id_sensor_servicio_2, 0) > 0 OR 
                        COALESCE(id_sensor_servicio_3, 0) > 0 OR 
                        COALESCE(id_sensor_servicio_4, 0) > 0 OR 
                        COALESCE(id_sensor_servicio_5, 0) > 0
                      )
                """
                cursor_ins.execute(query_servidores)
                servidores = cursor_ins.fetchall()

                if not servidores:
                    log_agente("💤 No se localizaron servidores activos con sensores mapeados. Reintentando...")

                for srv in servidores:
                    try:
                        ip = srv["ip"]
                        nombre = srv["nombre_alias"]
                        
                        # Guardamos los identificadores para las reglas del semáforo
                        id_cpu = int(srv.get("id_sensor_cpu") or 0)
                        id_ram = int(srv.get("id_sensor_ram") or 0)
                        id_lat = int(srv.get("id_sensor_latencia") or 0)
                        
                        # CONSULTA EN TIEMPO REAL MEDIANTE UTILS (Se conecta a PRTG o levanta contingencia local)
                        telemetria = obtener_telemetria_total(srv)
                        
                        v_cpu = telemetria["cpu"]
                        v_ram = telemetria["ram"]
                        v_red = telemetria["red"]
                        v_lat = telemetria["latencia"]
                        
                        v_d1 = telemetria["disco_1"]
                        v_d2 = telemetria["disco_2"]
                        v_d3 = telemetria["disco_3"]
                        v_d4 = telemetria["disco_4"]
                        v_d5 = telemetria["disco_5"]
                        v_d6 = telemetria["disco_6"]
                        
                        v_s1 = telemetria["servicio_1"]
                        v_s2 = telemetria["servicio_2"]
                        v_s3 = telemetria["servicio_3"]
                        v_s4 = telemetria["servicio_4"]
                        v_s5 = telemetria["servicio_5"]

                        # Extracción en caliente de Umbrales desde la Bitácora de Auditoría
                        u_cpu_adv, u_cpu_crit = 70.0, 85.0
                        u_ram_adv, u_ram_crit = 8.0, 4.0
                        
                        # Comportamiento heredado para nodo restringido de RAM de Contingencia
                        if ip == "10.10.1.133":
                            u_ram_adv, u_ram_crit = 1.5, 0.5

                        # Límites mínimos predeterminados para la validación de los 6 Discos
                        u_disco_limites = {i: {"adv": 3.0 if ip == "10.10.1.133" else 40.0, "crit": 1.0 if ip == "10.10.1.133" else 15.0} for i in range(1, 7)}

                        # Parámetros lógicos predeterminados para los 5 Servicios
                        u_servicio_limites = {i: {"adv": 1, "crit": 0} for i in range(1, 6)}

                        # Conexión perezosa interna para descargar la bitácora de umbrales más reciente de la IP
                        conn_umb = None
                        try:
                            conn_umb = mysql.connector.connect(**DB_CONFIG)
                            cursor_umb = conn_umb.cursor(dictionary=True)
                            cursor_umb.execute("SELECT * FROM historico_umbrales WHERE ip_servidor = %s ORDER BY id_historico DESC LIMIT 1", (ip,))
                            res_umb = cursor_umb.fetchone()
                            if res_umb and "disco_1_advertencia" in res_umb:
                                u_cpu_adv = float(res_umb["cpu_advertencia"])
                                u_cpu_crit = float(res_umb["cpu_critico"])
                                u_ram_adv = float(res_umb["ram_advertencia"])
                                u_ram_crit = float(res_umb["ram_critico"])
                                
                                for i in range(1, 7):
                                    u_disco_limites[i]["adv"] = float(res_umb[f"disco_{i}_advertencia"])
                                    u_disco_limites[i]["crit"] = float(res_umb[f"disco_{i}_critico"])

                                for i in range(1, 6):
                                    u_servicio_limites[i]["adv"] = int(res_umb[f"servicio_{i}_advertencia"])
                                    u_servicio_limites[i]["crit"] = int(res_umb[f"servicio_{i}_critico"])
                            cursor_umb.close()
                            conn_umb.close()
                        except Exception:
                            if conn_umb and conn_umb.is_connected(): conn_umb.close()

                        # EVALUACIÓN DE MATRIZ DE RIESGO INSTITUCIONAL (SISTEMA DE SEMÁFOROS)
                        estado = "ÓPTIMO"

                        # 1. Validación de CPU
                        if id_cpu > 0:
                            if v_cpu >= u_cpu_crit: estado = "CRÍTICO"
                            elif v_cpu >= u_cpu_adv and estado != "CRÍTICO": estado = "PRECAUCIÓN"

                        # 2. Validación de RAM
                        if id_ram > 0 and estado != "CRÍTICO":
                            if v_ram <= u_ram_crit: estado = "CRÍTICO"
                            elif v_ram <= u_ram_adv: estado = "PRECAUCIÓN"

                        # 3. Validación Exhaustiva de los 6 Discos Libres
                        valores_discos = [v_d1, v_d2, v_d3, v_d4, v_d5, v_d6]
                        discos_resumen_lista = []

                        for idx in range(6):
                            num_d = idx + 1
                            v_disc = valores_discos[idx]
                            id_disc = int(srv.get(f"id_sensor_disco_{num_d}") or 0)
                            
                            if id_disc > 0:
                                discos_resumen_lista.append(f"D{num_d}:{v_disc}GB")
                                if v_disc <= u_disco_limites[num_d]["crit"]:
                                    estado = "CRÍTICO"
                                elif v_disc <= u_disco_limites[num_d]["adv"] and estado != "CRÍTICO":
                                    estado = "PRECAUCIÓN"
                            else:
                                discos_resumen_lista.append(f"D{num_d}:N/A")
                        
                        discos_resumen = ", ".join(discos_resumen_lista)

                        # 4. Validación Lógica de los 5 Sensores de Servicio
                        valores_servicios = [v_s1, v_s2, v_s3, v_s4, v_s5]

                        for idx in range(5):
                            num_s = idx + 1
                            v_svc = valores_servicios[idx]
                            id_svc = int(srv.get(f"id_sensor_servicio_{num_s}") or 0)

                            if id_svc > 0:
                                if v_svc == 0:
                                    if u_servicio_limites[num_s]["crit"] == 0:
                                        estado = "CRÍTICO"
                                    elif u_servicio_limites[num_s]["adv"] == 1 and estado != "CRÍTICO":
                                        estado = "PRECAUCIÓN"

                        # COMPILACIÓN DEL REGISTRO DE TELEMETRÍA REAL EN LA BASE DE DATO
                        query = """
                            INSERT INTO monitoreo 
                            (ip_servidor, val_cpu, val_ram, 
                             val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                             estado_servicio_1, estado_servicio_2, estado_servicio_3, estado_servicio_4, estado_servicio_5,
                             val_red, val_latencia, estado_sistema, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        valores = (
                            ip, v_cpu, v_ram, 
                            v_d1, v_d2, v_d3, v_d4, v_d5, v_d6,
                            v_s1, v_s2, v_s3, v_s4, v_s5,
                            v_red, v_lat, estado, datetime.now()
                        )

                        conn_write = None
                        try:
                            conn_write = mysql.connector.connect(**DB_CONFIG)
                            cursor_write = conn_write.cursor()
                            cursor_write.execute(query, valores)
                            conn_write.commit()
                            cursor_write.close()
                        finally:
                            if conn_write and conn_write.is_connected():
                                conn_write.close()
                        
                        # LOG CON DECORADOR DE RED REAL
                        marcador_estado = "🟢" if estado == "ÓPTIMO" else ("🟡" if estado == "PRECAUCIÓN" else "🔴")
                        log_cpu = f"{v_cpu}%" if id_cpu > 0 else "N/A"
                        log_ram = f"{v_ram}GB" if id_ram > 0 else "N/A"
                        origen_msg = telemetria["msg"]
                        
                        log_agente(f"{marcador_estado} {origen_msg} NODO: {nombre} ({ip}) | CPU: {log_cpu} | RAM: {log_ram} | Latencia: {f'{v_lat}ms' if id_lat > 0 else 'N/A'} | Almacenamiento: [{discos_resumen}] | Status: {estado}")

                    except Exception:
                        pass 

                cursor_ins.close()
                conn_ins.close()

            except Exception:
                pass

            time.sleep(10)

    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        print("\n[!] Demonio detenido por interrupción de teclado (SIGINT).")

if __name__ == "__main__":
    ejecutar_motor_agente()