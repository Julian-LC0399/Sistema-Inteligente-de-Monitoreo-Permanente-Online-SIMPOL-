import time
import mysql.connector
from datetime import datetime
import sys
import os
import socket
from utils import get_resource_path, obtener_telemetria_total, safe_float

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

MAPEO_DISCOS = {
    "DISCO_1": "C:\\", "DISCO_2": "D:\\", "DISCO_3": "E:\\",
    "DISCO_4": "F:\\", "DISCO_5": "G:\\", "DISCO_6": "Y:\\"
}

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected(): return conn
        except mysql.connector.Error:
            intentos += 1
            time.sleep(delay)
    return None

def obtener_umbrales_servidor(ip):
    conn = conectar_bd_con_reintentos()
    umbrales = {
        "cpu_critico": 85.0, "cpu_advertencia": 70.0,
        "ram_critico": 10.0, "ram_advertencia": 15.0,
        "disco_critico": 5.0, "disco_advertencia": 25.0,
        "disco_2_critico": 5.0, "disco_2_advertencia": 25.0,
        "disco_3_critico": 5.0, "disco_3_advertencia": 25.0,
        "disco_4_critico": 5.0, "disco_4_advertencia": 25.0,
        "disco_5_critico": 5.0, "disco_5_advertencia": 25.0,
        "disco_6_critico": 5.0, "disco_6_advertencia": 25.0,
        "latencia_limite_ms": 150.0,
        "perdida_limite_pct": 5.0
    }
    if not conn: return umbrales
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                cpu_advertencia, cpu_critico, ram_advertencia, ram_critico, 
                disco_1_advertencia, disco_1_critico, disco_2_advertencia, disco_2_critico,
                disco_3_advertencia, disco_3_critico, disco_4_advertencia, disco_4_critico,
                disco_5_advertencia, disco_5_critico, disco_6_advertencia, disco_6_critico
            FROM historico_umbrales WHERE ip_servidor = %s ORDER BY id_historico DESC LIMIT 1
        """
        cursor.execute(query, (ip,))
        row = cursor.fetchone()
        if row:
            umbrales.update({
                "cpu_critico": safe_float(row["cpu_critico"]), "cpu_advertencia": safe_float(row["cpu_advertencia"]),
                "ram_critico": safe_float(row["ram_critico"]), "ram_advertencia": safe_float(row["ram_advertencia"]),
                "disco_critico": safe_float(row["disco_1_critico"]), "disco_advertencia": safe_float(row["disco_1_advertencia"]),
                "disco_2_critico": safe_float(row["disco_2_critico"]), "disco_2_advertencia": safe_float(row["disco_2_advertencia"]),
                "disco_3_critico": safe_float(row["disco_3_critico"]), "disco_3_advertencia": safe_float(row["disco_3_advertencia"]),
                "disco_4_critico": safe_float(row["disco_4_critico"]), "disco_4_advertencia": safe_float(row["disco_4_advertencia"]),
                "disco_5_critico": safe_float(row["disco_5_critico"]), "disco_5_advertencia": safe_float(row["disco_5_advertencia"]),
                "disco_6_critico": safe_float(row["disco_6_critico"]), "disco_6_advertencia": safe_float(row["disco_6_advertencia"])
            })
        cursor.close()
        conn.close()
    except:
        if conn and conn.is_connected(): conn.close()
    return umbrales

def registrar_o_resolver_alerta(ip, componente, estado_calculado, val_total, val_dispo, val_pct, sensor_id):
    conn = conectar_bd_con_reintentos()
    if not conn: return
    try:
        cursor = conn.cursor(dictionary=True)
        query_check = "SELECT id, tipo_alerta FROM alertas WHERE ip_servidor = %s AND componente = %s AND estado_alerta = 'ACTIVA' LIMIT 1"
        cursor.execute(query_check, (ip, componente))
        alerta_existente = cursor.fetchone()

        if "Servicio_" in componente:
            if estado_calculado in ["ESTABLE", "ACTIVO"]:
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) se ha normalizado correctamente."
            else:
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) se encuentra en estado [{estado_calculado}] o caído."
        elif componente in ["RED", "LATENCIA"]:
            comentario = f"Problema en {componente} (ID Sensor: {sensor_id}). Métrica reporta: {val_pct}."
        else:
            comentario = f"Componente {componente} (ID Sensor: {sensor_id}) reportando {val_pct}% disponible."

        if estado_calculado in ["ESTABLE", "ACTIVO"]:
            if alerta_existente:
                query_close = "UPDATE alertas SET estado_alerta = 'RESUELTA', fecha_fin = CURRENT_TIMESTAMP(3), comentario = 'Normalizado por Agente' WHERE id = %s"
                cursor.execute(query_close, (alerta_existente["id"],))
                conn.commit()
            cursor.close()
            conn.close()
            return

        if alerta_existente:
            if alerta_existente["tipo_alerta"] == estado_calculado:
                cursor.close()
                conn.close()
                return
            else:
                query_close = "UPDATE alertas SET estado_alerta = 'RESUELTA', fecha_fin = CURRENT_TIMESTAMP(3) WHERE id = %s"
                cursor.execute(query_close, (alerta_existente["id"],))
                conn.commit()

        query_insert = """
            INSERT INTO alertas (ip_servidor, componente, tipo_alerta, val_total_gb_momento, 
            val_disponible_gb_momento, val_disponible_pct_momento, estado_alerta, comentario) 
            VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVA', %s)
        """
        cursor.execute(query_insert, (ip, componente, estado_calculado, val_total, val_dispo, val_pct, comentario))
        conn.commit()
        cursor.close()
        conn.close()
    except:
        if conn and conn.is_connected(): conn.close()

def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION, _SOCKET_LOCK
    try:
        _SOCKET_LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCKET_LOCK.bind(("127.0.0.1", 9999))
    except socket.error:
        print(f"\n[🛑 ALERTA] agente.py ya está ejecutándose.", flush=True)
        sys.exit(0)
        
    AGENTE_EN_EJECUCION = True
    print("🚀 INICIANDO DEMONIO DE MONITOREO SIMPOL CORE V4.0.1", flush=True)
    print("💡 Presiona Control + C en cualquier momento para detener el agente de forma limpia.\n", flush=True)

    try:
        while AGENTE_EN_EJECUCION:
            conn = conectar_bd_con_reintentos()
            if not conn:
                time.sleep(15)
                continue

            try:
                cursor_ins = conn.cursor(dictionary=True)
                cursor_ins.execute("SELECT * FROM servidores WHERE estado_monitoreo = 1")
                servidores = cursor_ins.fetchall()
                cursor_ins.close()

                print("\n" + "="*95)
                print(f" ⏱️  CICLO DE INYECCIÓN Y EVALUACIÓN DE ALERTAS SIMPOL ({datetime.now().strftime('%H:%M:%S')})")
                print("="*95)

                for srv in servidores:
                    ip = srv["ip"]
                    nombre = srv["nombre_alias"] or ip
                    
                    id_cpu = int(srv.get("id_sensor_cpu") or 0)
                    id_ram = int(srv.get("id_sensor_ram") or 0)
                    id_red_total = int(srv.get("id_sensor_red_total") or srv.get("id_sensor_red") or 0)
                    id_red_entrante = int(srv.get("id_sensor_red_entrante") or 0)
                    id_red_saliente = int(srv.get("id_sensor_red_saliente") or 0)
                    id_latencia = int(srv.get("id_sensor_latencia") or 0)
                    
                    ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                    ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                    
                    total_sensores = id_cpu + id_ram + id_red_total + id_red_entrante + id_red_saliente + id_latencia + sum(ids_discos) + sum(ids_servicios)
                    if total_sensores == 0: continue
                    
                    telemetria = obtener_telemetria_total(srv)
                    umbrales = obtener_umbrales_servidor(ip) 

                    columnas_sql = ["ip_servidor"]
                    parametros_sql = [str(ip)]
                    
                    status_cpu = "ESTABLE"
                    status_ram = "ESTABLE"
                    status_latencia = "ESTABLE"
                    status_discos = {}
                    
                    log_items_consola = []

                    # =============================================================
                    # CPU - Estados correctos (valores más altos = peor)
                    # =============================================================
                    if id_cpu > 0:
                        v_cpu = safe_float(telemetria.get("cpu") or telemetria.get("CPU", 0.0))
                        
                        if v_cpu >= umbrales["cpu_critico"]:
                            status_cpu = "CRÍTICO"
                        elif v_cpu >= umbrales["cpu_advertencia"]:
                            status_cpu = "PRECAUCIÓN"
                        else:
                            status_cpu = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "CPU", status_cpu, 100, 100 - v_cpu, v_cpu, id_cpu)
                        columnas_sql.append("val_cpu")
                        parametros_sql.append(v_cpu)

                        cores_txt = []
                        for idx in range(1, 9):
                            v_core = safe_float(telemetria.get(f"cpu_p{idx}") or telemetria.get(f"CPU_P{idx}", 0.0))
                            columnas_sql.append(f"val_cpu_p{idx}")
                            parametros_sql.append(v_core)
                            cores_txt.append(f"P{idx}: {v_core}%")
                        log_items_consola.append(f"• CPU Global: {v_cpu}% [{', '.join(cores_txt)}] -> [{status_cpu}]")

                    # =============================================================
                    # RAM - Estados correctos (valores más bajos = peor - porcentaje libre)
                    # =============================================================
                    if id_ram > 0:
                        v_ram_total = safe_float(telemetria.get("ram_total_gb") or telemetria.get("RAM_TOTAL_GB", 0.0))
                        v_ram_pct = safe_float(telemetria.get("ram_pct") or telemetria.get("ram_disponible_pct") or telemetria.get("RAM_PCT", 100.0))
                        v_ram_gb = safe_float(telemetria.get("ram_gb") or telemetria.get("ram_disponible_gb") or telemetria.get("RAM_GB", 0.0))
                        
                        if v_ram_pct <= umbrales["ram_critico"]:
                            status_ram = "CRÍTICO"
                        elif v_ram_pct <= umbrales["ram_advertencia"]:
                            status_ram = "PRECAUCIÓN"
                        else:
                            status_ram = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "RAM", status_ram, v_ram_total, v_ram_gb, v_ram_pct, id_ram)
                        columnas_sql.extend(["val_ram_total_gb", "val_ram_disponible_pct", "val_ram_disponible_gb"])
                        parametros_sql.extend([v_ram_total, v_ram_pct, v_ram_gb])
                        log_items_consola.append(f"• RAM Libre: {v_ram_pct}% ({v_ram_gb}/{v_ram_total} GB) -> [{status_ram}]")

                    # =============================================================
                    # RED - Solo registro de datos (CORREGIDO)
                    # =============================================================
                    v_red_tot = safe_float(telemetria.get("red_total") or telemetria.get("RED_TOTAL", 0.0))
                    v_red_ent = safe_float(telemetria.get("red_entrante") or telemetria.get("RED_ENTRANTE", 0.0))
                    v_red_sal = safe_float(telemetria.get("red_saliente") or telemetria.get("RED_SALIENTE", 0.0))
                    
                    if id_red_total > 0:
                        columnas_sql.append("val_red_total")
                        parametros_sql.append(v_red_tot)
                    if id_red_entrante > 0:
                        columnas_sql.append("val_red_entrante")
                        parametros_sql.append(v_red_ent)
                    if id_red_saliente > 0:
                        columnas_sql.append("val_red_saliente")
                        parametros_sql.append(v_red_sal)
                        
                    if id_red_total > 0 or id_red_entrante > 0 or id_red_saliente > 0:
                        log_items_consola.append(f"• Red Tráfico: Total {v_red_tot} Mbit/s | Entrante: {v_red_ent} Mbit/s | Saliente: {v_red_sal} Mbit/s")

                    # =============================================================
                    # DISCOS - Estados correctos (valores más bajos = peor - porcentaje libre)
                    # =============================================================
                    for i in range(1, 7):
                        id_sensor_disco = ids_discos[i-1]
                        if id_sensor_disco > 0:
                            letra_unidad = srv.get(f"letra_disco_{i}") or MAPEO_DISCOS.get(f"DISCO_{i}", f"Disco_{i}")
                            total_gb = safe_float(telemetria.get(f"disco_{i}_total_gb") or telemetria.get(f"DISCO_{i}_TOTAL_GB", 0.0))
                            pct_libre = safe_float(telemetria.get(f"disco_{i}_pct") or telemetria.get(f"disco_{i}_pct_libre") or telemetria.get(f"DISCO_{i}_PCT", 0.0))
                            libres_gb = safe_float(telemetria.get(f"disco_{i}_gb") or telemetria.get(f"disco_{i}_libres_gb") or telemetria.get(f"DISCO_{i}_GB", 0.0))
                            status_prtg = int(telemetria.get(f"disco_{i}_prtg_status", 5))
                            
                            clave_critico = "disco_critico" if i == 1 else f"disco_{i}_critico"
                            clave_advertencia = "disco_advertencia" if i == 1 else f"disco_{i}_advertencia"
                            
                            # Disco: valores más bajos = peor (porcentaje libre)
                            if pct_libre <= umbrales[clave_critico]:
                                st_disco = "CRÍTICO"
                            elif pct_libre <= umbrales[clave_advertencia]:
                                st_disco = "PRECAUCIÓN"
                            else:
                                st_disco = "ESTABLE"
                            
                            if status_prtg in [2, 3]:
                                st_disco = "CRÍTICO"
                            elif status_prtg == 4:
                                if st_disco == "ESTABLE":
                                    st_disco = "PRECAUCIÓN"
                                
                            status_discos[i] = st_disco
                            registrar_o_resolver_alerta(ip, letra_unidad, st_disco, total_gb, libres_gb, pct_libre, id_sensor_disco)
                            
                            columnas_sql.extend([f"val_disco_{i}_total_gb", f"val_disco_{i}_pct_libre", f"val_disco_{i}_libres_gb"])
                            parametros_sql.extend([total_gb, pct_libre, libres_gb])
                            log_items_consola.append(f"• {letra_unidad}: {pct_libre}% Libre ({libres_gb}/{total_gb} GB) -> [{st_disco}]")

                    # =============================================================
                    # SERVICIOS
                    # =============================================================
                    for j in range(1, 9):
                        id_sensor_servicio = ids_servicios[j-1]
                        if id_sensor_servicio > 0:
                            st_servicio = str(telemetria.get(f"servicio_{j}_status") or telemetria.get(f"SERVICIO_{j}_STATUS", "ACTIVO")).upper().strip()
                            status_prtg_srv = telemetria.get(f"servicio_{j}_prtg_status")
                            
                            if status_prtg_srv:
                                if int(status_prtg_srv) in [2, 3]:
                                    st_servicio = "CRÍTICO"
                                elif int(status_prtg_srv) == 4:
                                    st_servicio = "PRECAUCIÓN"
                                elif int(status_prtg_srv) == 1:
                                    st_servicio = "ACTIVO"
                            
                            nivel_alerta = "CRÍTICO" if st_servicio in ["DOWN", "CRÍTICO", "INACTIVO"] else ("PRECAUCIÓN" if st_servicio == "PRECAUCIÓN" else "ACTIVO")
                            registrar_o_resolver_alerta(ip, f"Servicio_{j}", nivel_alerta, 0, 0, 0, id_sensor_servicio)

                            columnas_sql.append(f"estado_servicio_{j}")
                            parametros_sql.append(st_servicio)
                            log_items_consola.append(f"• Servicio {j}: -> [{st_servicio}]")

                    # =============================================================
                    # LATENCIA - Estados correctos (valores más altos = peor)
                    # =============================================================
                    if id_latencia > 0:
                        v_ping = safe_float(telemetria.get("latencia_ping") or telemetria.get("LATENCIA_PING", 0.0))
                        v_max = safe_float(telemetria.get("latencia_max") or telemetria.get("LATENCIA_MAX", 0.0))
                        v_min = safe_float(telemetria.get("latencia_min") or telemetria.get("LATENCIA_MIN", 0.0))
                        v_loss = safe_float(telemetria.get("latencia_perdida") or telemetria.get("LATENCIA_LOSS", 0.0))

                        if v_ping >= umbrales["latencia_limite_ms"] or v_loss >= umbrales["perdida_limite_pct"]:
                            status_latencia = "CRÍTICO"
                        elif v_ping >= 50.0 or v_loss > 0.0:
                            status_latencia = "PRECAUCIÓN"
                        else:
                            status_latencia = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "LATENCIA", status_latencia, 0, 0, v_ping, id_latencia)
                        
                        columnas_sql.extend(["val_latencia_ping", "val_latencia_max", "val_latencia_min", "val_latencia_perdida"])
                        parametros_sql.extend([v_ping, v_max, v_min, v_loss])
                        log_items_consola.append(f"• Latencia Ping: Avg {v_ping}ms | Max {v_max}ms | Pérdida: {v_loss}% -> [{status_latencia}]")

                    # =============================================================
                    # SEMÁFORO DE SALUD - Estado general del sistema
                    # =============================================================
                    tiene_critico = False
                    tiene_precaucion = False
                    
                    if status_cpu == "CRÍTICO":
                        tiene_critico = True
                    elif status_cpu == "PRECAUCIÓN":
                        tiene_precaucion = True
                    
                    if status_ram == "CRÍTICO":
                        tiene_critico = True
                    elif status_ram == "PRECAUCIÓN":
                        tiene_precaucion = True
                    
                    if status_latencia == "CRÍTICO":
                        tiene_critico = True
                    elif status_latencia == "PRECAUCIÓN":
                        tiene_precaucion = True
                    
                    for st_d in status_discos.values():
                        if st_d == "CRÍTICO":
                            tiene_critico = True
                        elif st_d == "PRECAUCIÓN":
                            tiene_precaucion = True
                    
                    if tiene_critico:
                        estado_sistema = "5"
                    elif tiene_precaucion:
                        estado_sistema = "4"
                    else:
                        estado_sistema = "3"

                    columnas_sql.extend(["estado_sistema", "fecha_registro"])
                    parametros_sql.extend([estado_sistema, datetime.now()])

                    placeholders = ", ".join(["%s"] * len(parametros_sql))
                    query = f"INSERT INTO monitoreo ({', '.join(columnas_sql)}) VALUES ({placeholders})"
                    cursor_write = conn.cursor()
                    cursor_write.execute(query, parametros_sql)
                    conn.commit()
                    cursor_write.close()

                    modo_conexion = telemetria.get("modo_conexion", "MODO PRTG")

                    print(f"\n🖥️  [NODO PROCESADO]: '{nombre}' ({ip}) | 🌐 Conexión: {modo_conexion}")
                    print(f"   ├─📊 [TELEMETRÍA REGISTRADA]:")
                    for line in log_items_consola:
                        print(f"   │  {line}")
                    
                    if estado_sistema == "5":
                        estado_color = "🔴 CRÍTICO"
                    elif estado_sistema == "4":
                        estado_color = "🟡 PRECAUCIÓN"
                    else:
                        estado_color = "🟢 ESTABLE"
                    print(f"   │  • ESTADO DEL SISTEMA: {estado_color}")
                    
                    cursor_alertas = conn.cursor(dictionary=True)
                    cursor_alertas.execute("SELECT componente, tipo_alerta, comentario FROM alertas WHERE ip_servidor = %s AND estado_alerta = 'ACTIVA'", (ip,))
                    alertas_vigentes = cursor_alertas.fetchall()
                    cursor_alertas.close()
                    
                    print(f"   └─🚨 [ALERTAS ACTIVAS BD]:")
                    if alertas_vigentes:
                        for al in alertas_vigentes:
                            if al['tipo_alerta'] == "CRÍTICO":
                                alert_color = "🔴"
                            elif al['tipo_alerta'] == "PRECAUCIÓN":
                                alert_color = "🟡"
                            else:
                                alert_color = "🟢"
                            print(f"      {alert_color} -> [{al['componente']}] | Nivel: {al['tipo_alerta']} | Info: {al['comentario']}")
                    else:
                        print(f"      ✅ Nodo limpio. Sin anomalías vigentes.")
                    print("-" * 95, flush=True)

            except Exception as e_ciclo:
                print(f"❌ Fallo crítico en el bucle: {str(e_ciclo)}", flush=True)
                import traceback
                traceback.print_exc()
            finally:
                if conn and conn.is_connected(): conn.close()

            time.sleep(15)

    except KeyboardInterrupt:
        print("\n\n🛑 Parada manual detectada. Finalizando agente SIMPOL Core limpiamente...", flush=True)
    finally:
        if _SOCKET_LOCK:
            try:
                _SOCKET_LOCK.close()
                print("🔒 Socket de bloqueo puerto 9999 liberado con éxito.", flush=True)
            except Exception as e_sock:
                print(f"⚠️ Error al cerrar el socket: {e_sock}", flush=True)
        print("👋 ¡Agente fuera de línea!", flush=True)

if __name__ == "__main__":
    ejecutar_motor_agente()