import time
import mysql.connector
from datetime import datetime
import sys
import os
from utils import get_resource_path, obtener_telemetria_total

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

def log_agente(mensaje):
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

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    """Intenta establecer conexión de forma segura con la base de datos ante microcortes."""
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                return conn
        except mysql.connector.Error as err:
            intentos += 1
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{stamp}] ⚠️ Reintento de conexión BD {intentos}/{max_intentos} falló: {err}", flush=True)
            time.sleep(delay)
    return None

def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 INICIANDO DEMONIO DE TELEMETRÍA SIMPOL (FILTRO ULTRA-ESTRICTO DE SENSORES)")

    try:
        while AGENTE_EN_EJECUCION:
            conn_ins = conectar_bd_con_reintentos()
            if not conn_ins:
                log_agente("❌ ERROR CRÍTICO: Imposible conectar a MySQL tras múltiples reintentos. Saltando ciclo.")
                time.sleep(15)
                continue

            try:
                cursor_ins = conn_ins.cursor(dictionary=True)
                query_servidores = "SELECT * FROM servidores WHERE estado_monitoreo = 1"
                cursor_ins.execute(query_servidores)
                servidores = cursor_ins.fetchall()

                for srv in servidores:
                    try:
                        ip = srv["ip"]
                        nombre = srv["nombre_alias"]
                        
                        # 1. Extracción de IDs de sensores desde la configuración de la BD
                        id_cpu = int(srv.get("id_sensor_cpu") or 0)
                        id_ram = int(srv.get("id_sensor_ram") or 0)
                        id_red = int(srv.get("id_sensor_red") or 0)
                        id_ping = int(srv.get("id_sensor_ping") or 0)
                        
                        ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                        # MODIFICACIÓN: Rango extendido a range(1, 9) para capturar id_sensor_servicio_1 hasta id_sensor_servicio_8
                        ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                        
                        # Validación de existencia de sensores
                        total_sensores = id_ram + id_cpu + id_red + id_ping + sum(ids_discos) + sum(ids_servicios)
                        if total_sensores == 0:
                            continue

                        # Obtener telemetría total en vivo
                        telemetria = obtener_telemetria_total(srv)
                        
                        # =====================================================================
                        # 2. BLINDAJE COERCITIVO: SI NO HAY SENSOR ASIGNADO, ES 0.0 / OFF
                        # =====================================================================
                        v_cpu = float(telemetria.get("cpu") or 0.0) if id_cpu > 0 else 0.0
                        v_ram = float(telemetria.get("ram") or 0.0) if id_ram > 0 else 0.0
                        v_red = float(telemetria.get("red") or 0.0) if id_red > 0 else 0.0
                        v_lat = float(telemetria.get("latencia") or 0.0) if id_ping > 0 else 0.0
                        
                        v_d1 = float(telemetria.get("disco_1") or 0.0) if ids_discos[0] > 0 else 0.0
                        v_d2 = float(telemetria.get("disco_2") or 0.0) if ids_discos[1] > 0 else 0.0
                        v_d3 = float(telemetria.get("disco_3") or 0.0) if ids_discos[2] > 0 else 0.0
                        v_d4 = float(telemetria.get("disco_4") or 0.0) if ids_discos[3] > 0 else 0.0
                        v_d5 = float(telemetria.get("disco_5") or 0.0) if ids_discos[4] > 0 else 0.0
                        v_d6 = float(telemetria.get("disco_6") or 0.0) if ids_discos[5] > 0 else 0.0
                        
                        v_s1 = "ON" if (ids_servicios[0] > 0 and telemetria.get("servicio_1") == 1) else "OFF"
                        v_s2 = "ON" if (ids_servicios[1] > 0 and telemetria.get("servicio_2") == 1) else "OFF"
                        v_s3 = "ON" if (ids_servicios[2] > 0 and telemetria.get("servicio_3") == 1) else "OFF"
                        v_s4 = "ON" if (ids_servicios[3] > 0 and telemetria.get("servicio_4") == 1) else "OFF"
                        v_s5 = "ON" if (ids_servicios[4] > 0 and telemetria.get("servicio_5") == 1) else "OFF"
                        # MODIFICACIÓN: Blindaje coercitivo mapeado para los nuevos servicios 6, 7 y 8
                        v_s6 = "ON" if (ids_servicios[5] > 0 and telemetria.get("servicio_6") == 1) else "OFF"
                        v_s7 = "ON" if (ids_servicios[6] > 0 and telemetria.get("servicio_7") == 1) else "OFF"
                        v_s8 = "ON" if (ids_servicios[7] > 0 and telemetria.get("servicio_8") == 1) else "OFF"

                        # =====================================================================
                        # 3. EVALUACIÓN DEL SEMÁFORO (ESTADO)
                        # =====================================================================
                        u_ram_adv, u_ram_crit = 3.5, 1.5
                        u_disco_limites = {i: {"adv": 40.0, "crit": 15.0} for i in range(1, 7)}
                        
                        if ip == "10.10.1.133":
                            u_disco_limites[1]["adv"] = 35.0  
                            u_disco_limites[2]["adv"] = 65.0  

                        estado = "ÓPTIMO"

                        if id_ram > 0:
                            if v_ram <= u_ram_crit: estado = "CRÍTICO"
                            elif v_ram <= u_ram_adv: estado = "PRECAUCIÓN"

                        valores_discos = [v_d1, v_d2, v_d3, v_d4, v_d5, v_d6]
                        for idx in range(6):
                            num_d = idx + 1
                            if ids_discos[idx] > 0:
                                v_disc = valores_discos[idx]
                                if v_disc == 0.0:
                                    continue
                                if v_disc <= u_disco_limites[num_d]["crit"]: 
                                    estado = "CRÍTICO"
                                elif v_disc <= u_disco_limites[num_d]["adv"] and estado != "CRÍTICO": 
                                    estado = "PRECAUCIÓN"

                        ahora_local = datetime.now()

                        # 4. Inserción Limpia y Segura
                        # MODIFICACIÓN: Agregadas las columnas estado_servicio_6, estado_servicio_7 y estado_servicio_8 con sus marcadores %s
                        query = """
                            INSERT INTO monitoreo 
                            (ip_servidor, val_cpu, val_ram, 
                             val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                             estado_servicio_1, estado_servicio_2, estado_servicio_3, estado_servicio_4, estado_servicio_5,
                             estado_servicio_6, estado_servicio_7, estado_servicio_8,
                             val_red, val_latencia, estado_sistema, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        # MODIFICACIÓN: Añadidas las variables v_s6, v_s7 y v_s8 en la tupla de valores a insertar
                        valores = (
                            ip, v_cpu, v_ram, 
                            v_d1, v_d2, v_d3, v_d4, v_d5, v_d6,
                            v_s1, v_s2, v_s3, v_s4, v_s5, v_s6, v_s7, v_s8, 
                            v_red, v_lat, estado, ahora_local
                        )

                        conn_write = conectar_bd_con_reintentos()
                        if conn_write:
                            cursor_write = conn_write.cursor()
                            cursor_write.execute(query, valores)
                            conn_write.commit()
                            cursor_write.close()
                            conn_write.close()

                    except Exception as e_srv:
                        log_agente(f"❌ Excepción procesando servidor {srv.get('nombre_alias')}: {str(e_srv)}")

                cursor_ins.close()
                conn_ins.close()
                
            except Exception as e_ciclo:
                log_agente(f"❌ Fallo general en el ciclo de lectura: {str(e_ciclo)}")
                if conn_ins and conn_ins.is_connected():
                    conn_ins.close()

            time.sleep(15)
            
    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        log_agente("🛑 Demonio detenido de forma segura.")

if __name__ == "__main__":
    ejecutar_motor_agente()