import time
import mysql.connector
from datetime import datetime
import sys
import os
import logging
import socket
from utils import get_resource_path, obtener_telemetria_total, safe_float

# Configuración centralizada de la Base de Datos SIMPOL
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
_SOCKET_LOCK = None  

def mapear_estado_servicio(estado_crudo):
    """
    Sincroniza y homologa los estados nativos de PRTG / Sistemas Operativos
    con el ENUM ('ACTIVO', 'INACTIVO', 'OFF') estricto de la BD de SIMPOL.
    """
    if not estado_crudo:
        return 'INACTIVO'
        
    estado = str(estado_crudo).strip().upper()
    
    if any(palabra in estado for palabra in ['ACTIV', 'RUN', 'ONLIN', 'START', 'UP', 'OK', '1', 'TRUE']):
        return 'ACTIVO'
    if any(palabra in estado for palabra in ['OFF', 'DISABL', 'DESHAB', 'SHUTDOWN']):
        return 'OFF'
        
    return 'INACTIVO'

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected(): return conn
        except mysql.connector.Error as err:
            intentos += 1
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Reintento {intentos}/{max_intentos}: {err}", flush=True)
            time.sleep(delay)
    return None

def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION, _SOCKET_LOCK
    
    try:
        _SOCKET_LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCKET_LOCK.bind(("127.0.0.1", 9999))
    except socket.error:
        print(f"\n[🛑 ALERTA SIMPOL] El demonio 'agente.py' ya se encuentra en ejecución activa.", flush=True)
        sys.exit(0)
        
    AGENTE_EN_EJECUCION = True
    print("🚀 INICIANDO DEMONIO DE MONITOREO SIMPOL CORE - BANCO CARONÍ", flush=True)

    try:
        while AGENTE_EN_EJECUCION:
            conn = conectar_bd_con_reintentos()
            if not conn:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ No se pudo conectar a la BD central. Reintentando en 15s...", flush=True)
                time.sleep(15)
                continue

            try:
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
                        
                        # Conversión e inicialización segura previniendo valores NULL de la interfaz web
                        ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                        ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]

                        # Evaluación limpia de presencia de sensores asignados
                        total_sensores = id_cpu + id_ram + id_red + id_latencia + sum(ids_discos) + sum(ids_servicios)
                        if total_sensores == 0: 
                            continue

                        # Consumo de telemetría mapeada desde utils.py
                        telemetria = obtener_telemetria_total(srv)
                        
                        estado_sistema_code = "3"
                        
                        # CORRECCIÓN DEFENSIVA DE BÚSQUEDA DE LLAVE CPU
                        v_cpu_raw = telemetria.get("cpu") if telemetria.get("cpu") is not None else telemetria.get("cpu_uso", telemetria.get("val_cpu", 0.0))
                        v_cpu = safe_float(v_cpu_raw) if id_cpu > 0 else 0.0
                        
                        # Control de alertas de estado del sistema basado en CPU operativo
                        if id_cpu > 0 and v_cpu >= 85.0: estado_sistema_code = "4"
                        elif id_cpu > 0 and v_cpu >= 70.0: estado_sistema_code = "5"

                        ahora_local = datetime.now()

                        query = """
                            INSERT INTO monitoreo (
                                ip_servidor, val_cpu, 
                                val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb,
                                val_disco_1_total_gb, val_disco_1_pct_libre, val_disco_1_libres_gb,
                                val_disco_2_total_gb, val_disco_2_pct_libre, val_disco_2_libres_gb,
                                val_disco_3_total_gb, val_disco_3_pct_libre, val_disco_3_libres_gb,
                                val_disco_4_total_gb, val_disco_4_pct_libre, val_disco_4_libres_gb,
                                val_disco_5_total_gb, val_disco_5_pct_libre, val_disco_5_libres_gb,
                                val_disco_6_total_gb, val_disco_6_pct_libre, val_disco_6_libres_gb,
                                estado_servicio_1, val_servicio_1,
                                estado_servicio_2, val_servicio_2,
                                estado_servicio_3, val_servicio_3,
                                estado_servicio_4, val_servicio_4,
                                estado_servicio_5, val_servicio_5,
                                estado_servicio_6, val_servicio_6,
                                estado_servicio_7, val_servicio_7,
                                estado_servicio_8, val_servicio_8,
                                val_red, val_latencia, estado_sistema, fecha_registro
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s
                            )
                        """
                        
                        v_ram_total = safe_float(telemetria.get("ram_total_gb", 0.0)) if id_ram > 0 else 0.0
                        v_ram_pct = safe_float(telemetria.get("ram_pct", 100.0)) if id_ram > 0 else 0.0
                        v_ram_gb = safe_float(telemetria.get("ram_gb", 0.0)) if id_ram > 0 else 0.0

                        # BLINDAJE INTEGRAL: Pasamos los valores directamente. Si no hay ID o falla, se inyecta su float por defecto (0.0 o 100.0), NUNCA un NULL.
                        parametros_sql = [
                            str(ip), 
                            v_cpu,
                            v_ram_total,
                            v_ram_pct,
                            v_ram_gb
                        ]
                        
                        # Procesamiento de almacenamiento asignado
                        sys_discos_log = []
                        for i in range(1, 7):
                            id_sensor_disco = ids_discos[i-1]
                            letra_unidad = srv.get(f"letra_disco_{i}") or f"Disco_{i}"
                            
                            if id_sensor_disco > 0:
                                total_gb = safe_float(telemetria.get(f"disco_{i}_total_gb", 0.0))
                                pct_libre = safe_float(telemetria.get(f"disco_{i}_pct", 0.0))
                                libres_gb = safe_float(telemetria.get(f"disco_{i}_gb", 0.0))
                                
                                parametros_sql.append(total_gb)
                                parametros_sql.append(pct_libre)
                                parametros_sql.append(libres_gb)
                                sys_discos_log.append(f"{letra_unidad} (ID Sensor: {id_sensor_disco}) -> Total: {total_gb}GB | Libre: {pct_libre}% ({libres_gb}GB)")
                            else:
                                parametros_sql.extend([0.0, 0.0, 0.0]) # Forzar floats estables en lugar de None
                        
                        # Procesamiento e impresión de Servicios Asignados
                        sys_servicios_log = []
                        for i in range(1, 8 + 1):
                            id_sensor_servicio = ids_servicios[i-1]
                            
                            if id_sensor_servicio > 0:
                                estado_crudo = telemetria.get(f"servicio_{i}_estado", "INACTIVO")
                                st_servicio = mapear_estado_servicio(estado_crudo)
                                v_servicio = safe_float(telemetria.get(f"servicio_{i}_valor", 0.0))
                                
                                parametros_sql.append(st_servicio)
                                parametros_sql.append(v_servicio)
                                sys_servicios_log.append(f"Servicio {i} (ID Sensor: {id_sensor_servicio}) -> [Estado BD: {st_servicio} | Valor: {v_servicio}]")
                            else:
                                parametros_sql.extend(['INACTIVO', 0.0]) # Homologar con el ENUM de tu base de datos
                                
                        v_red = safe_float(telemetria.get("red", 0.0)) if id_red > 0 else 0.0
                        v_latencia = safe_float(telemetria.get("latencia", 0.0)) if id_latencia > 0 else 0.0

                        parametros_sql.extend([
                            v_red,
                            v_latencia,
                            str(estado_sistema_code),
                            ahora_local
                        ])

                        cursor_write = conn.cursor()
                        cursor_write.execute(query, parametros_sql)
                        conn.commit()
                        cursor_write.close()

                        # =========================================================================
                        # REPORTE ESTRICTO POR TERMINAL DE SENSORES REGISTRADOS (> 0)
                        # =========================================================================
                        print(f"[{ahora_local.strftime('%H:%M:%S')}] ✅ REGISTRO EXITOSO: '{nombre}' ({ip})", flush=True)
                        
                        if id_cpu > 0 or id_ram > 0:
                            nucleo_str = "    ├── NÚCLEO ---->"
                            if id_cpu > 0: nucleo_str += f" CPU (ID: {id_cpu}): {v_cpu}%"
                            if id_ram > 0: nucleo_str += f" | RAM (ID: {id_ram}): Total: {v_ram_total}GB - Disp: {v_ram_pct}% ({v_ram_gb}GB)"
                            print(nucleo_str, flush=True)
                        
                        if sys_discos_log:
                            print(f"    ├── ALMACENAMIENTO REGISTRADO:", flush=True)
                            for disco_str in sys_discos_log:
                                print(f"    │    └── {disco_str}", flush=True)
                                
                        if sys_servicios_log:
                            print(f"    ├── SERVICIOS CORE REGISTRADOS:", flush=True)
                            for srv_str in sys_servicios_log:
                                print(f"    │    └── {srv_str}", flush=True)
                                
                        if id_red > 0 or id_latencia > 0:
                            trafico_str = "    └── TRÁFICO --->"
                            if id_red > 0: trafico_str += f" Red (ID: {id_red}): {v_red} Mbps"
                            if id_latencia > 0: trafico_str += f" | Latencia (ID: {id_latencia}): {v_latencia} ms"
                            print(trafico_str, flush=True)
                        print("-" * 80, flush=True)

                    except Exception as e_srv:
                        print(f"❌ Error en servidor {ip}: {str(e_srv)}", flush=True)

            except Exception as e_ciclo:
                print(f"❌ Fallo de transacción en ciclo de telemetría: {str(e_ciclo)}", flush=True)
            finally:
                if conn and conn.is_connected(): conn.close()

            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n🛑 Demonio SIMPOL detenido manualmente por el operador.", flush=True)
        AGENTE_EN_EJECUCION = False
        if _SOCKET_LOCK: _SOCKET_LOCK.close()

if __name__ == "__main__":
    ejecutar_motor_agente()