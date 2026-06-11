import time
import mysql.connector
from datetime import datetime
import sys
import os
import logging
import socket  # <-- Incorporado para el candado de exclusión mutua
from utils import get_resource_path, obtener_telemetria_total

# Configuración de base de datos nativa conector puro
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
_SOCKET_LOCK = None  # Instancia global para retener el puerto firmemente en memoria

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simpol_agente.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def log_agente(mensaje, nivel="info"):
    if not AGENTE_EN_EJECUCION: return
    if nivel == "error": logging.error(mensaje)
    elif nivel == "warning": logging.warning(mensaje)
    else: logging.info(mensaje)

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected(): return conn
        except mysql.connector.Error as err:
            intentos += 1
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Intento de conexión {intentos}/{max_intentos} falló: {err}", flush=True)
            time.sleep(delay)
    return None

def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION, _SOCKET_LOCK
    
    # -------------------------------------------------------------------------
    # 🛡️ BLINDAJE ANTI-DUPLICADOS (Socket Lock)
    # -------------------------------------------------------------------------
    try:
        _SOCKET_LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Enlazamos a localhost en un puerto de control exclusivo para el Agente Core
        _SOCKET_LOCK.bind(("127.0.0.1", 9999))
    except socket.error:
        print(f"\n[🛑 ALERTA SIMPOL] El demonio 'agente.py' ya se encuentra en ejecución activa en otra terminal o hilo.", flush=True)
        print("Abortando inicialización duplicada de forma segura para proteger la integridad de la Base de Datos.\n", flush=True)
        sys.exit(0)
        
    AGENTE_EN_EJECUCION = True
    log_agente("🚀 INICIANDO DEMONIO DE MONITOREO SIMPOL CORE - BANCO CARONÍ V3.9")

    try:
        while AGENTE_EN_EJECUCION:
            conn = conectar_bd_con_reintentos()
            if not conn:
                log_agente("❌ ERROR DE RED: Imposible conectar al motor MySQL.", "error")
                time.sleep(15)
                continue

            try:
                # 1. Leer servidores configurados para telemetría activa
                cursor_ins = conn.cursor(dictionary=True)
                cursor_ins.execute("SELECT * FROM servidores WHERE estado_monitoreo = 1")
                servidores = cursor_ins.fetchall()
                cursor_ins.close()

                for srv in servidores:
                    try:
                        ip = srv["ip"]
                        nombre = srv["nombre_alias"] or ip
                        
                        id_cpu = int(srv.get("id_sensor_cpu") or 0)
                        id_ram = int(srv.get("id_sensor_ram") or 0)
                        id_red = int(srv.get("id_sensor_red") or 0)
                        id_latencia = int(srv.get("id_sensor_latencia") or 0) 
                        
                        ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                        ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                        
                        total_sensores = id_cpu + id_ram + id_red + id_latencia + sum(ids_discos) + sum(ids_servicios)
                        if total_sensores == 0: 
                            continue

                        # 2. Invocar muestreo integral de la API extendida
                        telemetria = obtener_telemetria_total(srv)
                        origen_msg = telemetria.get("msg", "💻 (MODO LOCAL)")
                        
                        # 3. Máquina de Estados / Cálculo de Semáforo (estado_sistema)
                        estado_sistema_code = "3"

                        # Regla RAM para Servidores Corporativos
                        v_ram_pct = telemetria.get("ram_pct", 0.0) if id_ram > 0 else 0.0
                        if id_ram > 0:
                            if v_ram_pct >= 90.0: estado_sistema_code = "4"
                            elif v_ram_pct >= 75.0: estado_sistema_code = "5"

                        # Regla Discos Dinámicos
                        for i in range(1, 7):
                            if ids_discos[i-1] > 0:
                                d_pct = telemetria.get(f"disco_{i}_pct", 0.0)
                                if d_pct >= 95.0: 
                                    estado_sistema_code = "4"
                                elif d_pct >= 85.0 and estado_sistema_code != "4": 
                                    estado_sistema_code = "5"

                        # Regla Servicios Core Bancarios
                        for i in range(1, 9):
                            if ids_servicios[i-1] > 0:
                                if telemetria.get(f"servicio_{i}_estado") == "OFF":
                                    estado_sistema_code = "4"

                        ahora_local = datetime.now()

                        # 4. QUERY ESTRUCTURADA ASIGNANDO LAS 50 COLUMNAS DE LA TABLA V3.9
                        query = """
                            INSERT INTO monitoreo (
                                ip_servidor, val_cpu, val_ram_bytes, val_ram_gb, val_ram_pct, val_ram_total_gb,
                                val_disco_1_bytes, val_disco_1_gb, val_disco_1_pct, val_disco_1_total_gb,
                                val_disco_2_bytes, val_disco_2_gb, val_disco_2_pct, val_disco_2_total_gb,
                                val_disco_3_bytes, val_disco_3_gb, val_disco_3_pct, val_disco_3_total_gb,
                                val_disco_4_bytes, val_disco_4_gb, val_disco_4_pct, val_disco_4_total_gb,
                                val_disco_5_bytes, val_disco_5_gb, val_disco_5_pct, val_disco_5_total_gb,
                                val_disco_6_bytes, val_disco_6_gb, val_disco_6_pct, val_disco_6_total_gb,
                                estado_servicio_1, val_servicio_1, estado_servicio_2, val_servicio_2,
                                estado_servicio_3, val_servicio_3, estado_servicio_4, val_servicio_4,
                                estado_servicio_5, val_servicio_5, estado_servicio_6, val_servicio_6,
                                estado_servicio_7, val_servicio_7, estado_servicio_8, val_servicio_8,
                                val_red, val_latencia, estado_sistema, fecha_registro
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s
                            )
                        """
                        
                        parametros_sql = [
                            str(ip),
                            float(telemetria.get("cpu", 0.0)) if id_cpu > 0 else 0.0,
                            int(telemetria.get("ram_bytes", 0)) if id_ram > 0 else 0,
                            float(telemetria.get("ram_gb", 0.0)) if id_ram > 0 else 0.0,
                            float(telemetria.get("ram_pct", 0.0)) if id_ram > 0 else 0.0,
                            float(telemetria.get("ram_total_gb", 0.0)) if id_ram > 0 else 0.0
                        ]
                        
                        for i in range(1, 7):
                            if ids_discos[i-1] > 0:
                                parametros_sql.append(int(telemetria.get(f"disco_{i}_bytes", 0)))
                                parametros_sql.append(float(telemetria.get(f"disco_{i}_gb", 0.0)))
                                parametros_sql.append(float(telemetria.get(f"disco_{i}_pct", 0.0)))
                                parametros_sql.append(float(telemetria.get(f"disco_{i}_total_gb", 0.0)))
                            else:
                                parametros_sql.extend([0, 0.0, 0.0, 0.0])
                        
                        for i in range(1, 9):
                            if ids_servicios[i-1] > 0:
                                parametros_sql.append(str(telemetria.get(f"servicio_{i}_estado", "OFF")))
                                parametros_sql.append(float(telemetria.get(f"servicio_{i}_val", 0.0)))
                            else:
                                parametros_sql.extend(["INACTIVO", 0.0])
                        
                        parametros_sql.extend([
                            float(telemetria.get("red", 0.0)) if id_red > 0 else 0.0,
                            float(telemetria.get("latencia", 0.0)) if id_latencia > 0 else 0.0,
                            str(estado_sistema_code),
                            ahora_local
                        ])

                        cursor_write = conn.cursor()
                        cursor_write.execute(query, parametros_sql)
                        conn.commit()
                        cursor_write.close()

                        print(f"[{ahora_local.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✅ '{nombre}' ({ip}) guardado con éxito. Source: {origen_msg} | Semáforo: {estado_sistema_code}", flush=True)

                    except Exception as e_srv:
                        log_agente(f"❌ Excepción procesando servidor {srv.get('nombre_alias', ip)}: {str(e_srv)}", "error")

            except Exception as e_ciclo:
                log_agente(f"❌ Fallo crítico en el ciclo transaccional: {str(e_ciclo)}", "error")
            finally:
                if conn and conn.is_connected(): 
                    conn.close()

            time.sleep(15)
            
    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        if _SOCKET_LOCK:
            _SOCKET_LOCK.close()
        print("\n🛑 Demonio SIMPOL detenido de manera controlada por el operador.", flush=True)

if __name__ == "__main__":
    ejecutar_motor_agente()