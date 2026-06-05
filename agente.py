import time
import mysql.connector
from datetime import datetime
import sys
import os
import logging
from utils import get_resource_path, obtener_telemetria_total

# =========================================================
# CONFIGURACIÓN GENERAL Y BASE DE DATOS
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

AGENTE_EN_EJECUCION = False

# Configuración de Logging centralizado compatible con simpol_agente.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simpol_agente.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def log_agente(mensaje, nivel="info"):
    """Registra eventos en el log y la consola de manera segura y sincronizada."""
    if not AGENTE_EN_EJECUCION:
        return
    if nivel == "error":
        logging.error(mensaje)
    elif nivel == "warning":
        logging.warning(mensaje)
    else:
        logging.info(mensaje)

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    """Establece conexión de forma segura con la base de datos mitigando microcortes en la red."""
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                return conn
        except mysql.connector.Error as err:
            intentos += 1
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Reintento de conexión BD {intentos}/{max_intentos} falló: {err}", flush=True)
            time.sleep(delay)
    return None

def ejecutar_motor_agente():
    """
    Demonio principal de telemetría SIMPOL.
    Recorre los nodos activos, extrae datos en vivo (PRTG/Local) e inserta en la BD de forma dinámica.
    """
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 INICIANDO DEMONIO DE TELEMETRÍA SIMPOL (FILTRO DINÁMICO DE SENSORES REGISTRADOS)")

    try:
        while AGENTE_EN_EJECUCION:
            # Reutilizamos una única conexión por ciclo para lecturas y escrituras (Optimización de Sockets)
            conn = conectar_bd_con_reintentos()
            if not conn:
                log_agente("❌ ERROR CRÍTICO: Imposible conectar a MySQL tras múltiples reintentos. Saltando ciclo.", "error")
                time.sleep(15)
                continue

            try:
                cursor_ins = conn.cursor(dictionary=True)
                query_servidores = "SELECT * FROM servidores WHERE estado_monitoreo = 1"
                cursor_ins.execute(query_servidores)
                servidores = cursor_ins.fetchall()
                cursor_ins.close()

                for srv in servidores:
                    try:
                        ip = srv["ip"]
                        nombre = srv["nombre_alias"] or ip
                        
                        # 1. Extracción e indexación de IDs de sensores desde la configuración de la BD
                        id_cpu = int(srv.get("id_sensor_cpu") or 0)
                        id_ram = int(srv.get("id_sensor_ram") or 0)
                        id_red = int(srv.get("id_sensor_red") or 0)
                        id_latencia = int(srv.get("id_sensor_latencia") or 0) 
                        
                        ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                        ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                        
                        # Validación de existencia mínima de sensores configurados
                        total_sensores = id_ram + id_cpu + id_red + id_latencia + sum(ids_discos) + sum(ids_servicios)
                        if total_sensores == 0:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏭️ Servidor '{nombre}' ({ip}) saltado: Sin sensores asignados en BD.", flush=True)
                            continue

                        # Obtener telemetría total consolidada en vivo desde utils.py
                        telemetria = obtener_telemetria_total(srv)
                        origen_msg = telemetria.get("msg", "💻 (MODO LOCAL)")
                        
                        # =====================================================================
                        # 2. PROCESAMIENTO INTELIGENTE: PRESERVAR 'NONE' SI NO EXISTE EL SENSOR
                        # =====================================================================
                        v_cpu = float(telemetria.get("cpu") if telemetria.get("cpu") is not None else 0.0) if id_cpu > 0 else 0.0
                        v_ram = float(telemetria.get("ram") if telemetria.get("ram") is not None else 0.0) if id_ram > 0 else 0.0
                        v_red = float(telemetria.get("red") if telemetria.get("red") is not None else 0.0) if id_red > 0 else 0.0
                        v_lat = float(telemetria.get("latencia") if telemetria.get("latencia") is not None else 0.0) if id_latencia > 0 else 0.0
                        
                        # Si el ID del disco es mayor a 0, se guarda el valor o porcentaje obtenido (o 0.0 por defecto); si no existe, se guarda None (NULL en BD)
                        v_d1 = float(telemetria.get("disco_1") if telemetria.get("disco_1") is not None else 0.0) if ids_discos[0] > 0 else None
                        v_d2 = float(telemetria.get("disco_2") if telemetria.get("disco_2") is not None else 0.0) if ids_discos[1] > 0 else None
                        v_d3 = float(telemetria.get("disco_3") if telemetria.get("disco_3") is not None else 0.0) if ids_discos[2] > 0 else None
                        v_d4 = float(telemetria.get("disco_4") if telemetria.get("disco_4") is not None else 0.0) if ids_discos[3] > 0 else None
                        v_d5 = float(telemetria.get("disco_5") if telemetria.get("disco_5") is not None else 0.0) if ids_discos[4] > 0 else None
                        v_d6 = float(telemetria.get("disco_6") if telemetria.get("disco_6") is not None else 0.0) if ids_discos[5] > 0 else None
                        
                        # Los estados de los servicios se extraen ya procesados ("ON", "OFF", None) desde utils.py
                        v_s1 = telemetria.get("servicio_1") if ids_servicios[0] > 0 else None
                        v_s2 = telemetria.get("servicio_2") if ids_servicios[1] > 0 else None
                        v_s3 = telemetria.get("servicio_3") if ids_servicios[2] > 0 else None
                        v_s4 = telemetria.get("servicio_4") if ids_servicios[3] > 0 else None
                        v_s5 = telemetria.get("servicio_5") if ids_servicios[4] > 0 else None
                        v_s6 = telemetria.get("servicio_6") if ids_servicios[5] > 0 else None
                        v_s7 = telemetria.get("servicio_7") if ids_servicios[6] > 0 else None
                        v_s8 = telemetria.get("servicio_8") if ids_servicios[7] > 0 else None

                        # =====================================================================
                        # 3. EVALUACIÓN DEL SEMÁFORO OPERATIVO (ESTÁNDAR PRTG: '3'=OK, '4'=CRIT, '5'=WARN)
                        # =====================================================================
                        u_ram_adv, u_ram_crit = 3.5, 1.5
                        u_disco_limites = {i: {"adv": 40.0, "crit": 15.0} for i in range(1, 7)}
                        
                        if ip == "10.10.1.133":
                            u_disco_limites[1]["adv"] = 35.0  
                            u_disco_limites[2]["adv"] = 65.0  

                        estado_sistema_code = "3" # Por defecto '3' (OK / Up)

                        if id_ram > 0:
                            if v_ram <= u_ram_crit: estado_sistema_code = "4"
                            elif v_ram <= u_ram_adv: estado_sistema_code = "5"

                        # Solo evaluamos alertas de espacio en discos registrados que NO tengan un valor nulo (None)
                        valores_discos = [v_d1, v_d2, v_d3, v_d4, v_d5, v_d6]
                        for idx in range(6):
                            num_d = idx + 1
                            if ids_discos[idx] > 0 and valores_discos[idx] is not None:
                                v_disc = valores_discos[idx]
                                if v_disc <= u_disco_limites[num_d]["crit"]: 
                                    estado_sistema_code = "4"
                                elif v_disc <= u_disco_limites[num_d]["adv"] and estado_sistema_code != "4": 
                                    estado_sistema_code = "5"

                        # Si un servicio crítico activo está caído (OFF), el semáforo del sistema pasa a Crítico
                        valores_servicios = [v_s1, v_s2, v_s3, v_s4, v_s5, v_s6, v_s7, v_s8]
                        for idx in range(8):
                            if ids_servicios[idx] > 0 and valores_servicios[idx] == "OFF":
                                estado_sistema_code = "4"

                        ahora_local = datetime.now()

                        # =====================================================================
                        # 4. INSERCIÓN DE MÉTRICAS EN HISTÓRICO MONITOREO
                        # =====================================================================
                        query = """
                            INSERT INTO monitoreo 
                            (ip_servidor, val_cpu, val_ram, 
                             val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                             estado_servicio_1, estado_servicio_2, estado_servicio_3, estado_servicio_4, estado_servicio_5,
                             estado_servicio_6, estado_servicio_7, estado_servicio_8,
                             val_red, val_latencia, estado_sistema, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        valores = (
                            ip, v_cpu, v_ram, 
                            v_d1, v_d2, v_d3, v_d4, v_d5, v_d6,
                            v_s1, v_s2, v_s3, v_s4, v_s5, v_s6, v_s7, v_s8, 
                            v_red, v_lat, estado_sistema_code, ahora_local
                        )

                        cursor_write = conn.cursor()
                        cursor_write.execute(query, valores)
                        conn.commit()
                        cursor_write.close()

                        # Notificación limpia en consola por cada ciclo
                        print(f"[{ahora_local.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Servidor '{nombre}' ({ip}) monitoreado con éxito. Origen: {origen_msg} | Estado: {estado_sistema_code}", flush=True)

                    except Exception as e_srv:
                        log_agente(f"❌ Excepción procesando servidor {srv.get('nombre_alias', ip)}: {str(e_srv)}", "error")

            except Exception as e_ciclo:
                log_agente(f"❌ Fallo general en el ciclo de procesamiento: {str(e_ciclo)}", "error")
            finally:
                if conn and conn.is_connected():
                    conn.close()

            time.sleep(15)
            
    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        log_agente("🛑 Demonio de telemetría detenido de forma segura por el operador.", "warning")

if __name__ == "__main__":
    ejecutar_motor_agente()