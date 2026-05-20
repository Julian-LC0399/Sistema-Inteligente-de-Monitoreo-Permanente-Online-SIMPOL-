import time
import mysql.connector
from datetime import datetime
import sys
import os

# --- SOPORTE PARA RUTAS INTERNAS SI SE CONGELA A .EXE ---
def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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

def log_agente(mensaje):
    """Escribe las trazas de auditoría y ejecución en la raíz del motor."""
    try:
        directorio_ejecucion = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        ruta_log = os.path.join(directorio_ejecucion, "debug_agente.txt")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mensaje}\n")
            f.flush()
    except:
        pass

def obtener_servidores_activos():
    """Extrae del catálogo los nodos configurados para monitoreo."""
    servidores = []
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Sincronizado con la columna 'estado_monitoreo' de tu BD actual
        query = "SELECT * FROM servidores WHERE estado_monitoreo = 1"
        cursor.execute(query)
        servidores = cursor.fetchall()
        cursor.close()
    except Exception as e:
        log_agente(f"❌ Error de Catálogo SQL: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return servidores

def obtener_umbrales_agente(cursor, ip):
    """Consulta los límites configurados dinámicamente por los analistas."""
    umbrales = {"cpu_critico": 80, "ram_critico": 85, "disco_critico": 90}
    try:
        query = """
            SELECT cpu_critico, ram_critico, disco_critico 
            FROM historico_umbrales 
            WHERE ip_servidor = %s 
            ORDER BY id_historico DESC LIMIT 1
        """
        cursor.execute(query, (ip,))
        res = cursor.fetchone()
        if res:
            umbrales["cpu_critico"] = res[0]
            umbrales["ram_critico"] = res[1]
            umbrales["disco_critico"] = res[2]
    except Exception:
        pass 
    return umbrales

def iniciar_agente():
    """Motor principal del demonio de telemetría."""
    log_agente("🚀 --- INICIANDO MOTOR DE MONITOREO DINÁMICO ---")
    
    try:
        # Importación tardía para aislar procesos de interfaz de Streamlit
        from utils import obtener_telemetria_total
        log_agente("✅ Módulos de telemetría acoplados con éxito.")
    except Exception as e:
        log_agente(f"💥 Error crítico al importar UTILS: {e}")
        return

    while True:
        try:
            # Re-escaneo constante de la BD para capturar cambios en caliente del catálogo
            servidores = obtener_servidores_activos()
            
            if not servidores:
                log_agente("⚠️ Sin servidores activos para monitorear en la tabla 'servidores'.")
                time.sleep(10)
                continue

            conn_ins = mysql.connector.connect(**DB_CONFIG)
            cursor_ins = conn_ins.cursor()

            for serv in servidores:
                try:
                    nombre = serv['nombre_alias']
                    ip = serv['ip']
                    
                    # === FILTRO DE SEGURIDAD MULTI-SENSOR ===
                    id_cpu = serv.get('id_sensor_cpu', 0)
                    id_ram = serv.get('id_sensor_ram', 0)
                    id_disco = serv.get('id_sensor_disco', 0)
                    
                    # Si están vacíos o en 0 (poblado por defecto de la BD), se omite elegantemente
                    if id_cpu == 0 or id_ram == 0 or id_disco == 0:
                        log_agente(f"⏭️ Nodo '{nombre}' ({ip}) omitido temporalmente: Sensores de hardware no mapeados (valores en 0).")
                        continue
                    
                    # === TRAZA DE PROCESAMIENTO EXITOSO ===
                    log_agente(f"🔄 Procesando telemetría para nodo: '{nombre}' ({ip}) -> Sensores [CPU: {id_cpu} | RAM: {id_ram} | DISCO: {id_disco}]")
                    
                    # Consumo de API mediante el conector de utils.py
                    data = obtener_telemetria_total(serv)
                    ahora = datetime.now()
                    
                    v_cpu = data.get('cpu', 0)
                    v_ram = data.get('ram', 0)
                    v_disco = data.get('disco', 0)
                    v_lat = data.get('latencia', 0)
                    
                    # Evaluación de estados según políticas e histórico de umbrales
                    limites = obtener_umbrales_agente(cursor_ins, ip)
                    estado = "ÓPTIMO"
                    
                    if (v_cpu >= limites["cpu_critico"] or 
                        v_ram >= limites["ram_critico"] or 
                        v_disco >= limites["disco_critico"] or 
                        v_lat > 200):
                        estado = "CRÍTICO"
                    elif (v_cpu >= (limites["cpu_critico"] - 10) or 
                          v_ram >= (limites["ram_critico"] - 10) or 
                          v_disco >= (limites["disco_critico"] - 10) or 
                          v_lat > 100):
                        estado = "PRECAUCIÓN"

                    # Inserción limpia en tabla de telemetría viva (monitoreo)
                    query = """
                        INSERT INTO monitoreo 
                        (fecha_registro, ip_servidor, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    valores = (ahora, ip, v_cpu, v_ram, v_disco, data.get('red', 0), v_lat, estado)
                    
                    cursor_ins.execute(query, valores)
                    conn_ins.commit()
                    
                    # Log de confirmación de guardado exitoso
                    log_agente(f"💾 Telemetría guardada con éxito para '{nombre}' ({ip}). Estado: {estado} | {data.get('msg', '')}")

                except Exception as e:
                    log_agente(f"❌ Error al recolectar telemetría en {serv.get('nombre_alias', 'Desconocido')}: {e}")

            cursor_ins.close()
            conn_ins.close()

        except Exception as e:
            log_agente(f"💥 Error en ciclo principal del motor: {e}")

        time.sleep(10) # Intervalo cíclico de escaneo (10 segundos)

if __name__ == "__main__":
    iniciar_agente()