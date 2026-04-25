import time
import mysql.connector
from datetime import datetime
import sys
import os

# --- SOPORTE PARA RUTAS INTERNAS DEL EXE ---
def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Ajuste de path para encontrar 'utils' dentro del paquete
if getattr(sys, 'frozen', False):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

# CONFIGURACIÓN DB
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
    try:
        # Forzamos que el log se escriba en la carpeta del ejecutable, no en carpetas temporales
        directorio_ejecucion = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        ruta_log = os.path.join(directorio_ejecucion, "debug_agente.txt")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mensaje}\n")
            f.flush()
    except:
        pass

def obtener_servidores_activos():
    servidores = []
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM servidores_it WHERE estado_monitoreo = 1"
        cursor.execute(query)
        servidores = cursor.fetchall()
        cursor.close()
    except Exception as e:
        log_agente(f"❌ Error de Catálogo SQL: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return servidores

# ESTA ES LA FUNCIÓN QUE LLAMA APP.PY
def iniciar_agente():
    log_agente("🚀 --- INICIANDO MOTOR DE MONITOREO ---")
    
    try:
        # Importación tardía para evitar colisiones de hilos
        from utils import obtener_telemetria_total
        log_agente("✅ Módulos de telemetría cargados.")
    except Exception as e:
        log_agente(f"💥 Error crítico al importar UTILS: {e}")
        return

    while True:
        try:
            servidores = obtener_servidores_activos()
            
            if not servidores:
                log_agente("⚠️ Sin servidores activos para monitorear.")
                time.sleep(20)
                continue

            conn_ins = mysql.connector.connect(**DB_CONFIG)
            cursor_ins = conn_ins.cursor()

            for serv in servidores:
                try:
                    nombre = serv['nombre_alias']
                    ip = serv['ip']
                    
                    data = obtener_telemetria_total(serv)
                    ahora = datetime.now()
                    
                    v_cpu = data.get('cpu', 0)
                    v_ram = data.get('ram', 0)
                    v_disco = data.get('disco', 0)
                    v_lat = data.get('latencia', 0)
                    
                    max_val = max(v_cpu, v_ram, v_disco)
                    estado = "ÓPTIMO"
                    if max_val >= 90 or v_lat > 200: estado = "CRÍTICO"
                    elif max_val >= 75 or v_lat > 100: estado = "PRECAUCIÓN"

                    query = """
                        INSERT INTO monitoreo 
                        (fecha_registro, ip_servidor, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    valores = (ahora, ip, v_cpu, v_ram, v_disco, data.get('red', 0), v_lat, estado)
                    
                    cursor_ins.execute(query, valores)
                    conn_ins.commit()
                    # Quitamos el log de éxito por cada servidor para no saturar el disco del banco
                    # log_agente(f"📊 Registro: {nombre}")

                except Exception as e:
                    log_agente(f"❌ Error en {serv.get('nombre_alias')}: {e}")

            cursor_ins.close()
            conn_ins.close()

        except Exception as e:
            log_agente(f"💥 Error en ciclo principal: {e}")

        time.sleep(10) # Pausa entre escaneos completos

# Esto permite que el archivo funcione tanto importado como solo
if __name__ == "__main__":
    iniciar_agente()