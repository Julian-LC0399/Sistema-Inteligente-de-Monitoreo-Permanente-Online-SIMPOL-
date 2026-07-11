import sys
import os
import time
import mysql.connector
from datetime import datetime
import socket
import json

# =============================================================================
# CONFIGURACION DE LOGS - USANDO CARPETA COMPARTIDA
# =============================================================================
if getattr(sys, 'frozen', False):
    LOG_DIR = os.environ.get('TEMP', os.path.dirname(sys.executable))
else:
    LOG_DIR = os.getcwd()

LOG_FILE = os.path.join(LOG_DIR, "agente_simpol.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
    except:
        pass

try:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} - === INICIO DE CARGA DEL ARCHIVO ===\n")
except:
    pass

if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)

log("=" * 50)
log("AGENTE SIMPOL INICIADO")
log(f"sys.frozen: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    log(f"sys._MEIPASS: {sys._MEIPASS}")

try:
    from utils import get_resource_path, obtener_telemetria_total, safe_float
    log("utils importado correctamente")
except ImportError as e:
    log(f"Error importando utils: {e}")
    sys.exit(1)

# =============================================================================
# CONFIGURACION DE BASE DE DATOS
# =============================================================================
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password", 
    "use_pure": True,
    "connect_timeout": 15
}

# =============================================================================
# CONFIGURACION DE TELEGRAM - CARPETA COMPARTIDA EN RED
# =============================================================================
TELEGRAM_TOKEN = "8511465977:AAHAbgPqJ1pSndxZ2JeCcrbXBk0vMSxYx24"
TELEGRAM_CHAT_ID = "7766964399"

# ¡¡¡ CAMBIA ESTA RUTA POR LA CARPETA COMPARTIDA !!!
# Ejemplo: r"C:\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"
# Ejemplo red: r"\\SERVER\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"
MENSAJES_FILE = r"C:\Users\programadorje\Documents\archivos\Julian semestres\UNEG\trabajo de grado\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"

# Todos los estados se notifican
ESTADOS_TELEGRAM = ["CRITICO", "PRECAUCION", "ESTABLE"]

AGENTE_EN_EJECUCION = False
_SOCKET_LOCK = None  

MAPEO_DISCOS = {
    "DISCO_1": "C:\\", "DISCO_2": "D:\\", "DISCO_3": "E:\\",
    "DISCO_4": "F:\\", "DISCO_5": "G:\\", "DISCO_6": "Y:\\"
}

# =============================================================================
# FUNCIONES DE TELEGRAM - GUARDAN EN ARCHIVO
# =============================================================================
def guardar_mensaje_telegram(mensaje):
    """
    Guarda el mensaje en un archivo JSON en la carpeta compartida
    """
    try:
        # Crear carpeta si no existe
        os.makedirs(os.path.dirname(MENSAJES_FILE), exist_ok=True)
        
        # Leer mensajes existentes
        mensajes = []
        if os.path.exists(MENSAJES_FILE):
            try:
                with open(MENSAJES_FILE, "r", encoding="utf-8") as f:
                    mensajes = json.load(f)
            except:
                mensajes = []
        
        # Agregar nuevo mensaje
        mensajes.append({
            "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "mensaje": mensaje
        })
        
        # Guardar todos
        with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
            json.dump(mensajes, f, ensure_ascii=False, indent=2)
        
        log(f"Mensaje guardado en: {MENSAJES_FILE} (Total: {len(mensajes)})")
        return True
    except Exception as e:
        log(f"Error guardando mensaje: {e}")
        return False

def enviar_telegram(mensaje):
    """
    En servidor sin internet: guarda el mensaje en archivo
    """
    log("Guardando mensaje en archivo (servidor sin internet)...")
    return guardar_mensaje_telegram(mensaje)

def formatear_mensaje_alerta(ip, nombre, componente, estado, comentario, val_pct=None):
    """
    Formatea un mensaje de alerta para Telegram
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if estado == "CRITICO":
        titulo = "== ALERTA CRITICA - SIMPOL =="
        accion = "ATENCION: ACCION INMEDIATA REQUERIDA"
    elif estado == "PRECAUCION":
        titulo = "== ALERTA DE PRECAUCION - SIMPOL =="
        accion = "ATENCION: Revisar componente con atencion"
    else:
        titulo = "== SISTEMA NORMALIZADO - SIMPOL =="
        accion = "OK: Todo operando dentro de parametros"
    
    mensaje = f"""
{titulo}

Servidor: {nombre}
IP: {ip}
Componente: {componente}
Estado: {estado}
Hora: {timestamp}
Detalle: {comentario}
"""
    
    if val_pct is not None:
        mensaje += f"Valor: {val_pct:.1f}%\n"
    
    mensaje += f"\n{accion}"
    
    return mensaje.strip()

def formatear_mensaje_resuelto(ip, nombre, componente, estado_anterior, comentario):
    """
    Mensaje cuando se resuelve una alerta
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    mensaje = f"""
== ALERTA RESUELTA - SIMPOL ==

Servidor: {nombre}
IP: {ip}
Componente: {componente}
Estado Anterior: {estado_anterior}
Estado Actual: ESTABLE (Normalizado)
Hora: {timestamp}
Detalle: {comentario}

El sistema ha retornado a su estado normal
"""
    return mensaje.strip()

# =============================================================================
# FUNCIONES DE BASE DE DATOS
# =============================================================================
def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                log("Conexion a MySQL exitosa")
                return conn
        except mysql.connector.Error as e:
            log(f"Error conexion BD (intento {intentos+1}): {e}")
            intentos += 1
            time.sleep(delay)
    log("No se pudo conectar a la BD")
    return None

def obtener_umbrales_servidor(ip):
    conn = conectar_bd_con_reintentos()
    
    umbrales = {
        "cpu_buen_estado": 69.0, 
        "cpu_advertencia": 70.0, 
        "cpu_critico": 85.0,
        "cpu_p_buen_estado": 69.0, 
        "cpu_p_advertencia": 70.0, 
        "cpu_p_critico": 85.0,
        "ram_buen_estado": 20.0, 
        "ram_advertencia": 15.0, 
        "ram_critico": 10.0,
        "disco_1_buen_estado": 25.0, "disco_1_advertencia": 15.0, "disco_1_critico": 5.0,
        "disco_2_buen_estado": 25.0, "disco_2_advertencia": 15.0, "disco_2_critico": 5.0,
        "disco_3_buen_estado": 25.0, "disco_3_advertencia": 15.0, "disco_3_critico": 5.0,
        "disco_4_buen_estado": 25.0, "disco_4_advertencia": 15.0, "disco_4_critico": 5.0,
        "disco_5_buen_estado": 25.0, "disco_5_advertencia": 15.0, "disco_5_critico": 5.0,
        "disco_6_buen_estado": 25.0, "disco_6_advertencia": 15.0, "disco_6_critico": 5.0,
        "red_limite_total_mbps": 100.0, 
        "red_limite_entrante_mbps": 50.0, 
        "red_limite_saliente_mbps": 50.0,
        "latencia_limite_ms": 150.0, 
        "perdida_limite_pct": 1.0
    }
    
    if not conn:
        log(f"Sin conexion BD para {ip}, usando umbrales por defecto")
        return umbrales
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                cpu_buen_estado, cpu_advertencia, cpu_critico,
                cpu_p_buen_estado, cpu_p_advertencia, cpu_p_critico,
                ram_buen_estado, ram_advertencia, ram_critico,
                disco_1_buen_estado, disco_1_advertencia, disco_1_critico,
                disco_2_buen_estado, disco_2_advertencia, disco_2_critico,
                disco_3_buen_estado, disco_3_advertencia, disco_3_critico,
                disco_4_buen_estado, disco_4_advertencia, disco_4_critico,
                disco_5_buen_estado, disco_5_advertencia, disco_5_critico,
                disco_6_buen_estado, disco_6_advertencia, disco_6_critico,
                red_limite_total_mbps, red_limite_entrante_mbps, red_limite_saliente_mbps,
                latencia_limite_ms, perdida_limite_pct
            FROM historico_umbrales 
            WHERE ip_servidor = %s 
            ORDER BY id_historico DESC 
            LIMIT 1
        """
        cursor.execute(query, (ip,))
        row = cursor.fetchone()
        
        if row:
            log(f"Umbrales encontrados para {ip}: CPU Crit={row['cpu_critico']}%, RAM Crit={row['ram_critico']}%")
            for key in umbrales.keys():
                if key in row and row[key] is not None:
                    umbrales[key] = float(row[key])
        else:
            log(f"Sin umbrales configurados para {ip}, usando valores por defecto")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        log(f"Error obteniendo umbrales para {ip}: {e}")
        if conn and conn.is_connected():
            conn.close()
    
    return umbrales

# =============================================================================
# FUNCION PRINCIPAL DE REGISTRO DE ALERTAS
# =============================================================================
def registrar_o_resolver_alerta(ip, componente, estado_calculado, val_total, val_dispo, val_pct, sensor_id):
    conn = conectar_bd_con_reintentos()
    if not conn:
        log(f"No se pudo conectar a BD para gestionar alerta de {componente}")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        query_check = """
            SELECT id, tipo_alerta 
            FROM alertas 
            WHERE ip_servidor = %s AND componente = %s AND estado_alerta = 'ACTIVA' 
            LIMIT 1
        """
        cursor.execute(query_check, (ip, componente))
        alerta_existente = cursor.fetchone()

        cursor_temp = conn.cursor(dictionary=True)
        cursor_temp.execute("SELECT nombre_alias FROM servidores WHERE ip = %s LIMIT 1", (ip,))
        srv = cursor_temp.fetchone()
        nombre_servidor = srv["nombre_alias"] if srv else ip
        cursor_temp.close()

        if "Servicio_" in componente:
            if estado_calculado == "ESTABLE":
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) se encuentra operativo y estable."
            elif estado_calculado == "PRECAUCION":
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) presenta fallos intermitentes o degradacion."
            elif estado_calculado == "CRITICO":
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) se encuentra caido o en estado critico."
            else:
                comentario = f"Servicio {componente} (ID Sensor: {sensor_id}) en estado {estado_calculado}."
        elif componente in ["RED", "LATENCIA"]:
            if estado_calculado == "ESTABLE":
                comentario = f"Problema en {componente} (ID Sensor: {sensor_id}) resuelto. Metrica reporta: {val_pct:.1f}."
            elif estado_calculado == "PRECAUCION":
                comentario = f"Problema en {componente} (ID Sensor: {sensor_id}). Metrica reporta: {val_pct:.1f}."
            else:
                comentario = f"Problema critico en {componente} (ID Sensor: {sensor_id}). Metrica reporta: {val_pct:.1f}."
        else:
            if estado_calculado == "ESTABLE":
                comentario = f"Componente {componente} (ID Sensor: {sensor_id}) normalizado. Reporta {val_pct:.1f}% disponible."
            elif estado_calculado == "PRECAUCION":
                comentario = f"Componente {componente} (ID Sensor: {sensor_id}) en precaucion. Reporta {val_pct:.1f}% disponible."
            else:
                comentario = f"Componente {componente} (ID Sensor: {sensor_id}) en estado critico. Reporta {val_pct:.1f}% disponible."

        if estado_calculado == "ESTABLE":
            if alerta_existente:
                estado_anterior = alerta_existente["tipo_alerta"]
                query_close = """
                    UPDATE alertas 
                    SET estado_alerta = 'RESUELTA', 
                        fecha_fin = CURRENT_TIMESTAMP(3), 
                        comentario = %s 
                    WHERE id = %s
                """
                cursor.execute(query_close, (comentario, alerta_existente["id"]))
                conn.commit()
                log(f"Alerta resuelta para {componente} en {ip} - ESTABLE (era {estado_anterior})")
                
                mensaje_resuelto = formatear_mensaje_resuelto(
                    ip, nombre_servidor, componente, estado_anterior, comentario
                )
                enviar_telegram(mensaje_resuelto)
            else:
                query_check_estable = """
                    SELECT id FROM alertas 
                    WHERE ip_servidor = %s AND componente = %s 
                    AND tipo_alerta = 'ESTABLE' AND estado_alerta = 'ACTIVA'
                    LIMIT 1
                """
                cursor.execute(query_check_estable, (ip, componente))
                estable_existente = cursor.fetchone()
                
                if not estable_existente:
                    query_insert = """
                        INSERT INTO alertas (
                            ip_servidor, componente, tipo_alerta, 
                            val_total_gb_momento, val_disponible_gb_momento, 
                            val_disponible_pct_momento, estado_alerta, comentario
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVA', %s)
                    """
                    cursor.execute(query_insert, (
                        ip, componente, "ESTABLE", 
                        val_total, val_dispo, val_pct, comentario
                    ))
                    conn.commit()
                    log(f"Alerta ESTABLE registrada para {componente} en {ip}")
                    
                    mensaje_estable = formatear_mensaje_alerta(
                        ip, nombre_servidor, componente, "ESTABLE", comentario, val_pct
                    )
                    enviar_telegram(mensaje_estable)
            
            cursor.close()
            conn.close()
            return

        mensaje_alerta = formatear_mensaje_alerta(
            ip, nombre_servidor, componente, estado_calculado, comentario, val_pct
        )
        enviar_telegram(mensaje_alerta)

        if alerta_existente:
            if alerta_existente["tipo_alerta"] == estado_calculado:
                cursor.close()
                conn.close()
                return
            else:
                query_close = """
                    UPDATE alertas 
                    SET estado_alerta = 'RESUELTA', 
                        fecha_fin = CURRENT_TIMESTAMP(3),
                        comentario = 'Cambio de nivel - Cerrada por nueva alerta' 
                    WHERE id = %s
                """
                cursor.execute(query_close, (alerta_existente["id"],))
                conn.commit()

        query_insert = """
            INSERT INTO alertas (
                ip_servidor, componente, tipo_alerta, 
                val_total_gb_momento, val_disponible_gb_momento, 
                val_disponible_pct_momento, estado_alerta, comentario
            ) VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVA', %s)
        """
        cursor.execute(query_insert, (
            ip, componente, estado_calculado, 
            val_total, val_dispo, val_pct, comentario
        ))
        conn.commit()
        log(f"Nueva alerta {estado_calculado} para {componente} en {ip}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        log(f"Error en gestion de alerta para {componente}: {e}")
        if conn and conn.is_connected():
            conn.close()

# =============================================================================
# FUNCION PRINCIPAL DEL AGENTE
# =============================================================================
def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION, _SOCKET_LOCK
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} - >>> EJECUTANDO MOTOR DEL AGENTE <<<\n")
    except:
        pass
    
    log("INICIANDO MOTOR DEL AGENTE")
    
    PID_FILE = os.path.join(LOG_DIR, "agente_simpol.pid")
    
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            try:
                import signal
                os.kill(old_pid, 0)
                print(f"\n[ALERTA] El agente ya esta ejecutandose (PID: {old_pid})", flush=True)
                sys.exit(0)
            except OSError:
                os.remove(PID_FILE)
        except:
            pass
    
    current_pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(current_pid))
        log(f"PID {current_pid} guardado en {PID_FILE}")
    except Exception as e:
        log(f"Error guardando PID: {e}")
    
    try:
        _SOCKET_LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCKET_LOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _SOCKET_LOCK.bind(("127.0.0.1", 9999))
        log("Socket 9999 creado")
    except socket.error as e:
        log(f"Socket fallo: {e}")
        print(f"\n[ALERTA] agente.py ya esta ejecutandose.", flush=True)
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except:
            pass
        sys.exit(0)
        
    AGENTE_EN_EJECUCION = True
    log("AGENTE_EN_EJECUCION = True")
    print("\n" + "="*80)
    print(" SISTEMA DE MONITOREO SIMPOL - AGENTE ACTIVO")
    print("="*80)
    print(" Presiona Control + C para detener el agente.\n", flush=True)
    
    mensaje_inicio = f"""
== SIMPOL AGENTE INICIADO ==

Sistema: Agente de Monitoreo SIMPOL
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Log: {LOG_FILE}
Estado: Monitoreo activo

El sistema esta vigilando los servidores del Banco Caroni
"""
    enviar_telegram(mensaje_inicio)

    try:
        ciclo_num = 0
        while AGENTE_EN_EJECUCION:
            ciclo_num += 1
            log("INICIO DE CICLO")
            conn = conectar_bd_con_reintentos()
            if not conn:
                log("Sin BD, esperando 15s")
                time.sleep(15)
                continue

            try:
                cursor_ins = conn.cursor(dictionary=True)
                cursor_ins.execute("""
                    SELECT DISTINCT s.* 
                    FROM servidores s 
                    WHERE s.estado_monitoreo = 1 
                    ORDER BY s.nombre_alias ASC
                """)
                servidores = cursor_ins.fetchall()
                cursor_ins.close()
                
                log(f"Servidores activos encontrados: {len(servidores)}")

                if not servidores:
                    log("No hay servidores activos")
                    print("No hay servidores activos con estado_monitoreo = 1", flush=True)
                    conn.close()
                    time.sleep(15)
                    continue

                servidores_unicos = {}
                for srv in servidores:
                    ip = srv["ip"]
                    if ip not in servidores_unicos:
                        servidores_unicos[ip] = srv
                    else:
                        log(f"Duplicado detectado para IP {ip}, usando el primero encontrado")
                
                servidores = list(servidores_unicos.values())

                servidores_con_sensores = []
                for srv in servidores:
                    id_cpu = int(srv.get("id_sensor_cpu") or 0)
                    id_ram = int(srv.get("id_sensor_ram") or 0)
                    id_red_total = int(srv.get("id_sensor_red_total") or srv.get("id_sensor_red") or 0)
                    id_red_entrante = int(srv.get("id_sensor_red_entrante") or 0)
                    id_red_saliente = int(srv.get("id_sensor_red_saliente") or 0)
                    id_latencia = int(srv.get("id_sensor_latencia") or 0)
                    ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                    ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                    
                    total_sensores = id_cpu + id_ram + id_red_total + id_red_entrante + id_red_saliente + id_latencia + sum(ids_discos) + sum(ids_servicios)
                    
                    if total_sensores > 0:
                        servidores_con_sensores.append(srv)
                    else:
                        log(f"Servidor {srv['nombre_alias']} ({srv['ip']}) ignorado - sin sensores configurados")
                
                servidores = servidores_con_sensores

                print("\n" + "="*80)
                print(f" CICLO #{ciclo_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f" TOTAL SERVIDORES CON SENSORES: {len(servidores)}")
                print("="*80)

                if not servidores:
                    print("No hay servidores con sensores configurados.")
                    conn.close()
                    time.sleep(15)
                    continue

                for idx, srv in enumerate(servidores, 1):
                    ip = srv["ip"]
                    nombre = srv["nombre_alias"] or ip
                    
                    log(f"Procesando: {nombre} ({ip})")
                    
                    print(f"\n[{idx}/{len(servidores)}] SERVIDOR: {nombre}")
                    print(f"    IP: {ip}")
                    print("    " + "-"*70)
                    
                    id_cpu = int(srv.get("id_sensor_cpu") or 0)
                    id_ram = int(srv.get("id_sensor_ram") or 0)
                    id_red_total = int(srv.get("id_sensor_red_total") or srv.get("id_sensor_red") or 0)
                    id_red_entrante = int(srv.get("id_sensor_red_entrante") or 0)
                    id_red_saliente = int(srv.get("id_sensor_red_saliente") or 0)
                    id_latencia = int(srv.get("id_sensor_latencia") or 0)
                    
                    ids_discos = [int(srv.get(f"id_sensor_disco_{i}") or 0) for i in range(1, 7)]
                    ids_servicios = [int(srv.get(f"id_sensor_servicio_{i}") or 0) for i in range(1, 9)]
                    
                    log(f"Obteniendo telemetria para {nombre}...")
                    telemetria = obtener_telemetria_total(srv)
                    
                    umbrales = obtener_umbrales_servidor(ip)
                    log(f"UMBRALES ACTUALES para {nombre}: RAM Crit={umbrales['ram_critico']}%, CPU Crit={umbrales['cpu_critico']}%")

                    columnas_sql = ["ip_servidor"]
                    parametros_sql = [str(ip)]
                    
                    status_cpu = "ESTABLE"
                    status_ram = "ESTABLE"
                    status_latencia = "ESTABLE"
                    status_discos = {}
                    status_servicios = {}
                    
                    # CPU
                    if id_cpu > 0:
                        v_cpu = safe_float(telemetria.get("cpu") or telemetria.get("CPU", 0.0))
                        
                        if v_cpu >= umbrales["cpu_critico"]:
                            status_cpu = "CRITICO"
                        elif v_cpu >= umbrales["cpu_advertencia"]:
                            status_cpu = "PRECAUCION"
                        else:
                            status_cpu = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "CPU", status_cpu, 100, 100 - v_cpu, v_cpu, id_cpu)
                        columnas_sql.append("val_cpu")
                        parametros_sql.append(v_cpu)

                        cores = []
                        for idx_core in range(1, 9):
                            v_core = safe_float(telemetria.get(f"cpu_p{idx_core}") or telemetria.get(f"CPU_P{idx_core}", 0.0))
                            columnas_sql.append(f"val_cpu_p{idx_core}")
                            parametros_sql.append(v_core)
                            cores.append(f"P{idx_core}:{v_core:.1f}%")
                        
                        estado_icon = "[CRIT]" if status_cpu == "CRITICO" else ("[PREC]" if status_cpu == "PRECAUCION" else "[EST]")
                        print(f"    CPU (ID:{id_cpu}): {v_cpu:.1f}% {estado_icon}")
                        print(f"        Cores: {' '.join(cores)}")

                    # RAM
                    if id_ram > 0:
                        v_ram_total = safe_float(telemetria.get("ram_total_gb") or telemetria.get("RAM_TOTAL_GB", 0.0))
                        v_ram_pct = safe_float(telemetria.get("ram_pct") or telemetria.get("ram_disponible_pct") or telemetria.get("RAM_PCT", 100.0))
                        v_ram_gb = safe_float(telemetria.get("ram_gb") or telemetria.get("ram_disponible_gb") or telemetria.get("RAM_GB", 0.0))
                        
                        if v_ram_pct <= umbrales["ram_critico"]:
                            status_ram = "CRITICO"
                        elif v_ram_pct <= umbrales["ram_advertencia"]:
                            status_ram = "PRECAUCION"
                        else:
                            status_ram = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "RAM", status_ram, v_ram_total, v_ram_gb, v_ram_pct, id_ram)
                        columnas_sql.extend(["val_ram_total_gb", "val_ram_disponible_pct", "val_ram_disponible_gb"])
                        parametros_sql.extend([v_ram_total, v_ram_pct, v_ram_gb])
                        
                        estado_icon = "[CRIT]" if status_ram == "CRITICO" else ("[PREC]" if status_ram == "PRECAUCION" else "[EST]")
                        print(f"    RAM (ID:{id_ram}): {v_ram_pct:.1f}% {estado_icon} ({v_ram_gb:.1f}/{v_ram_total:.1f} GB)")

                    # RED
                    v_red_tot = safe_float(telemetria.get("red_total") or telemetria.get("RED_TOTAL", 0.0))
                    v_red_ent = safe_float(telemetria.get("red_entrante") or telemetria.get("RED_ENTRANTE", 0.0))
                    v_red_sal = safe_float(telemetria.get("red_saliente") or telemetria.get("RED_SALIENTE", 0.0))
                    
                    red_parts = []
                    if id_red_total > 0:
                        columnas_sql.append("val_red_total")
                        parametros_sql.append(v_red_tot)
                        red_parts.append(f"Total:{v_red_tot:.1f}Mbps")
                    if id_red_entrante > 0:
                        columnas_sql.append("val_red_entrante")
                        parametros_sql.append(v_red_ent)
                        red_parts.append(f"Entrante:{v_red_ent:.1f}Mbps")
                    if id_red_saliente > 0:
                        columnas_sql.append("val_red_saliente")
                        parametros_sql.append(v_red_sal)
                        red_parts.append(f"Saliente:{v_red_sal:.1f}Mbps")
                    
                    if red_parts:
                        print(f"    RED: {' | '.join(red_parts)}")

                    # DISCOS
                    for i in range(1, 7):
                        id_sensor_disco = ids_discos[i-1]
                        if id_sensor_disco > 0:
                            letra_unidad = srv.get(f"letra_disco_{i}") or MAPEO_DISCOS.get(f"DISCO_{i}", f"Disco_{i}")
                            total_gb = safe_float(telemetria.get(f"disco_{i}_total_gb") or telemetria.get(f"DISCO_{i}_TOTAL_GB", 0.0))
                            pct_libre = safe_float(telemetria.get(f"disco_{i}_pct") or telemetria.get(f"disco_{i}_pct_libre") or telemetria.get(f"DISCO_{i}_PCT", 0.0))
                            libres_gb = safe_float(telemetria.get(f"disco_{i}_gb") or telemetria.get(f"disco_{i}_libres_gb") or telemetria.get(f"DISCO_{i}_GB", 0.0))
                            status_prtg = int(telemetria.get(f"disco_{i}_prtg_status", 5))
                            
                            clave_critico = f"disco_{i}_critico"
                            clave_advertencia = f"disco_{i}_advertencia"
                            
                            if pct_libre <= umbrales[clave_critico]:
                                st_disco = "CRITICO"
                            elif pct_libre <= umbrales[clave_advertencia]:
                                st_disco = "PRECAUCION"
                            else:
                                st_disco = "ESTABLE"
                            
                            if status_prtg in [2, 3]:
                                st_disco = "CRITICO"
                            elif status_prtg == 4:
                                if st_disco == "ESTABLE":
                                    st_disco = "PRECAUCION"
                                
                            status_discos[i] = st_disco
                            registrar_o_resolver_alerta(ip, letra_unidad, st_disco, total_gb, libres_gb, pct_libre, id_sensor_disco)
                            
                            columnas_sql.extend([f"val_disco_{i}_total_gb", f"val_disco_{i}_pct_libre", f"val_disco_{i}_libres_gb"])
                            parametros_sql.extend([total_gb, pct_libre, libres_gb])
                            
                            estado_icon = "[CRIT]" if st_disco == "CRITICO" else ("[PREC]" if st_disco == "PRECAUCION" else "[EST]")
                            print(f"    DISCO {letra_unidad} (ID:{id_sensor_disco}): {pct_libre:.1f}% {estado_icon} ({libres_gb:.1f}/{total_gb:.1f} GB)")

                    # SERVICIOS
                    for j in range(1, 9):
                        id_sensor_servicio = ids_servicios[j-1]
                        if id_sensor_servicio > 0:
                            st_servicio = str(telemetria.get(f"servicio_{j}_status") or telemetria.get(f"SERVICIO_{j}_STATUS", "ACTIVO")).upper().strip()
                            status_prtg_srv = telemetria.get(f"servicio_{j}_prtg_status")
                            
                            if status_prtg_srv:
                                if int(status_prtg_srv) in [2, 3]:
                                    st_servicio = "CRITICO"
                                elif int(status_prtg_srv) == 4:
                                    st_servicio = "PRECAUCION"
                                elif int(status_prtg_srv) == 1:
                                    st_servicio = "ACTIVO"
                            
                            nivel_alerta = "CRITICO" if st_servicio in ["DOWN", "CRITICO", "INACTIVO"] else ("PRECAUCION" if st_servicio == "PRECAUCION" else "ESTABLE")
                            registrar_o_resolver_alerta(ip, f"Servicio_{j}", nivel_alerta, 0, 0, 0, id_sensor_servicio)

                            columnas_sql.append(f"estado_servicio_{j}")
                            parametros_sql.append(st_servicio)
                            
                            status_servicios[j] = nivel_alerta
                            
                            if st_servicio == "CRITICO":
                                estado_icon = "[CRIT]"
                            elif st_servicio == "PRECAUCION":
                                estado_icon = "[PREC]"
                            else:
                                estado_icon = "[OK]"
                            print(f"    SERVICIO {j} (ID:{id_sensor_servicio}): {st_servicio} {estado_icon}")

                    # LATENCIA
                    if id_latencia > 0:
                        v_ping = safe_float(telemetria.get("latencia_ping") or telemetria.get("LATENCIA_PING", 0.0))
                        v_max = safe_float(telemetria.get("latencia_max") or telemetria.get("LATENCIA_MAX", 0.0))
                        v_min = safe_float(telemetria.get("latencia_min") or telemetria.get("LATENCIA_MIN", 0.0))
                        v_loss = safe_float(telemetria.get("latencia_perdida") or telemetria.get("LATENCIA_LOSS", 0.0))

                        if v_ping >= umbrales["latencia_limite_ms"] or v_loss >= umbrales["perdida_limite_pct"]:
                            status_latencia = "CRITICO"
                        elif v_ping >= 50.0 or v_loss > 0.0:
                            status_latencia = "PRECAUCION"
                        else:
                            status_latencia = "ESTABLE"
                        
                        registrar_o_resolver_alerta(ip, "LATENCIA", status_latencia, 0, 0, v_ping, id_latencia)
                        
                        columnas_sql.extend(["val_latencia_ping", "val_latencia_max", "val_latencia_min", "val_latencia_perdida"])
                        parametros_sql.extend([v_ping, v_max, v_min, v_loss])
                        
                        estado_icon = "[CRIT]" if status_latencia == "CRITICO" else ("[PREC]" if status_latencia == "PRECAUCION" else "[EST]")
                        print(f"    LATENCIA (ID:{id_latencia}): Ping {v_ping:.1f}ms {estado_icon} (Max:{v_max:.1f}ms | Perdida:{v_loss:.1f}%)")

                    # ESTADO DEL SISTEMA
                    tiene_critico = False
                    tiene_precaucion = False
                    
                    if status_cpu == "CRITICO":
                        tiene_critico = True
                    elif status_cpu == "PRECAUCION":
                        tiene_precaucion = True
                    
                    if status_ram == "CRITICO":
                        tiene_critico = True
                    elif status_ram == "PRECAUCION":
                        tiene_precaucion = True
                    
                    if status_latencia == "CRITICO":
                        tiene_critico = True
                    elif status_latencia == "PRECAUCION":
                        tiene_precaucion = True
                    
                    for st_d in status_discos.values():
                        if st_d == "CRITICO":
                            tiene_critico = True
                        elif st_d == "PRECAUCION":
                            tiene_precaucion = True
                    
                    for st_s in status_servicios.values():
                        if st_s == "CRITICO":
                            tiene_critico = True
                        elif st_s == "PRECAUCION":
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
                    
                    log(f"Datos insertados para {nombre}")
                    print("    " + "-"*70)

            except Exception as e_ciclo:
                log(f"Fallo en bucle: {str(e_ciclo)}")
                print(f"Fallo critico en el bucle: {str(e_ciclo)}", flush=True)
                import traceback
                traceback.print_exc()
            finally:
                if conn and conn.is_connected(): 
                    conn.close()
                    log("Conexion BD cerrada")

            log("Esperando 15 segundos...")
            print("\n[INFO] Esperando 15 segundos para el siguiente ciclo...\n")
            time.sleep(15)

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print(" PARADA MANUAL DETECTADA")
        print(" Finalizando agente SIMPOL...")
        print("="*80, flush=True)
        
        mensaje_cierre = f"""
== SIMPOL AGENTE DETENIDO ==

Sistema: Agente de Monitoreo SIMPOL
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Estado: Agente fuera de linea

El monitoreo se ha detenido manualmente
"""
        enviar_telegram(mensaje_cierre)
        
    finally:
        if _SOCKET_LOCK:
            try:
                _SOCKET_LOCK.close()
                print("Socket de bloqueo puerto 9999 liberado.", flush=True)
            except Exception as e_sock:
                print(f"Error al cerrar el socket: {e_sock}", flush=True)
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
                log("Archivo PID eliminado")
        except:
            pass
        print("Agente fuera de linea!", flush=True)

if __name__ == "__main__":
    ejecutar_motor_agente()