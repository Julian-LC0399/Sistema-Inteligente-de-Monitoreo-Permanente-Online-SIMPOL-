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

# Variable de control de ejecución para evitar escrituras fantasmas post-cierre
AGENTE_EN_EJECUCION = False

def log_agente(mensaje):
    """Escribe las trazas de auditoría únicamente si el motor está en ejecución activa."""
    if not AGENTE_EN_EJECUCION:
        return
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
        conn.commit() # Rompe el aislamiento REPEATABLE READ de MySQL.
        
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM servidores WHERE estado_monitoreo = 1"
        cursor.execute(query)
        servidores = cursor.fetchall()
        cursor.close()
    except Exception as e:
        log_agente(f"❌ Error de Catálogo SQL en Servidores: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return servidores

def obtener_umbrales_agente(cursor, ip):
    """
    Consulta los límites específicos del semáforo multidisco (5 Volúmenes) en la BD.
    Mapeo explícito y dinámico adaptado a floats para precisión.
    """
    if ip == "10.10.1.133":  # Perfil UAP Compensación (Límites Bajos en GB)
        umbrales = {
            "cpu_advertencia": 70.0, "cpu_critico": 85.0,
            "ram_advertencia": 1.5, "ram_critico": 0.5,
            "disco_1_advertencia": 3.0, "disco_1_critico": 1.0,
            "disco_2_advertencia": 3.0, "disco_2_critico": 1.0,
            "disco_3_advertencia": 3.0, "disco_3_critico": 1.0,
            "disco_4_advertencia": 3.0, "disco_4_critico": 1.0,
            "disco_5_advertencia": 3.0, "disco_5_critico": 1.0
        }
    else:  # Perfil estándar servidores de alta capacidad
        umbrales = {
            "cpu_advertencia": 70.0, "cpu_critico": 85.0,
            "ram_advertencia": 8.0, "ram_critico": 4.0,
            "disco_1_advertencia": 40.0, "disco_1_critico": 15.0,
            "disco_2_advertencia": 40.0, "disco_2_critico": 15.0,
            "disco_3_advertencia": 40.0, "disco_3_critico": 15.0,
            "disco_4_advertencia": 40.0, "disco_4_critico": 15.0,
            "disco_5_advertencia": 40.0, "disco_5_critico": 15.0
        }
        
    try:
        query = """
            SELECT cpu_advertencia, cpu_critico, 
                   ram_advertencia, ram_critico, 
                   disco_1_advertencia, disco_1_critico,
                   disco_2_advertencia, disco_2_critico,
                   disco_3_advertencia, disco_3_critico,
                   disco_4_advertencia, disco_4_critico,
                   disco_5_advertencia, disco_5_critico
            FROM historico_umbrales 
            WHERE TRIM(ip_servidor) = %s 
            ORDER BY id_historico DESC LIMIT 1
        """
        cursor.execute(query, (ip,))
        res = cursor.fetchone()
        
        if res:
            if isinstance(res, dict):
                for k, v in res.items():
                    umbrales[k] = float(v) if v is not None else umbrales[k]
            else:
                nombres_campos = [
                    "cpu_advertencia", "cpu_critico", "ram_advertencia", "ram_critico",
                    "disco_1_advertencia", "disco_1_critico", "disco_2_advertencia", "disco_2_critico",
                    "disco_3_advertencia", "disco_3_critico", "disco_4_advertencia", "disco_4_critico",
                    "disco_5_advertencia", "disco_5_critico"
                ]
                for idx, campo in enumerate(nombres_campos):
                    if idx < len(res) and res[idx] is not None:
                        umbrales[campo] = float(res[idx])
    except Exception:
        pass 
    return umbrales

def iniciar_agente():
    """Motor principal del demonio de telemetría."""
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 --- INICIANDO MOTOR DE MONITOREO DINÁMICO (PRECISIÓN DECIMAL V3.2) ---")
    
    try:
        from utils import obtener_telemetria_total
    except Exception as e:
        log_agente(f"💥 Error crítico al importar UTILS: {e}")
        AGENTE_EN_EJECUCION = False
        return

    try:
        while True:
            try:
                servidores = obtener_servidores_activos()
                
                if not servidores:
                    time.sleep(10)
                    continue

                conn_ins = mysql.connector.connect(**DB_CONFIG)
                conn_ins.commit()
                cursor_ins = conn_ins.cursor(dictionary=True)

                for serv in servidores:
                    try:
                        nombre = serv['nombre_alias']
                        ip = str(serv['ip']).strip()
                        
                        # Extraer sensores principales mapeando fallas de tipo
                        try:
                            id_cpu = int(serv.get('id_sensor_cpu') or 0)
                            id_ram = int(serv.get('id_sensor_ram') or 0)
                        except (ValueError, TypeError):
                            id_cpu = 0
                            id_ram = 0
                        
                        # Consumo seguro de la API utils
                        data = obtener_telemetria_total(serv)
                        
                        # ARQUITECTURA FLEXIBLE: Si el sensor está en 0, no mide y asienta 0.0 sin omitir el nodo
                        v_cpu = float(data.get('cpu', 0.0)) if id_cpu > 0 else 0.0
                        v_ram = float(data.get('ram', 0.0)) if id_ram > 0 else 0.0
                        
                        try:
                            id_lat = int(serv.get('id_sensor_latencia') or 0)
                        except: id_lat = 0
                        v_lat = float(data.get('latencia', 0.0)) if id_lat > 0 else 0.0
                        
                        if v_ram > 1024000:
                            v_ram = round(v_ram / (1024**3), 2)
                        
                        valores_discos = {f'val_disco_{i}': 0.0 for i in range(1, 6)}
                        peor_estado_disco = "ÓPTIMO"
                        limites = obtener_umbrales_agente(cursor_ins, ip)
                        
                        discos_str_lista = []
                        for i in range(1, 6):
                            try:
                                id_sensor_disco = int(serv.get(f'id_sensor_disco_{i}') or 0)
                            except (ValueError, TypeError):
                                id_sensor_disco = 0
                                
                            letra_disco = serv.get(f'letra_disco_{i}') or f"D{i}"
                            
                            # Solo procesa almacenamiento si tiene un sensor asignado en el catálogo
                            if id_sensor_disco > 0:
                                raw_val = data.get(f'disco_{i}')
                                if raw_val is None:
                                    raw_val = data.get(f'val_disco_{i}', 0.0)
                                    
                                v_disco_actual = float(raw_val) if raw_val is not None else 0.0
                                
                                if v_disco_actual > 1024000:
                                    v_disco_actual = round(v_disco_actual / (1024**3), 2)
                                
                                valores_discos[f'val_disco_{i}'] = v_disco_actual
                                discos_str_lista.append(f"{letra_disco}:{v_disco_actual}GB")
                                
                                # Evaluación condicional de semáforos de disco
                                if v_disco_actual <= limites[f"disco_{i}_critico"]:
                                    peor_estado_disco = "CRÍTICO"
                                elif v_disco_actual <= limites[f"disco_{i}_advertencia"] and peor_estado_disco != "CRÍTICO":
                                    peor_estado_disco = "PRECAUCIÓN"

                        discos_resumen = ", ".join(discos_str_lista) if discos_str_lista else "Ninguno"

                        # =========================================================
                        # EVALUACIÓN DE SEMÁFORO INTELIGENTE (TOLERANTE A SENSORES INACTIVOS)
                        # =========================================================
                        estado = "ÓPTIMO"
                        if id_cpu > 0 and v_cpu >= limites["cpu_critico"]: estado = "CRÍTICO"
                        elif id_ram > 0 and v_ram <= limites["ram_critico"]: estado = "CRÍTICO"
                        elif peor_estado_disco == "CRÍTICO": estado = "CRÍTICO"
                        elif id_lat > 0 and v_lat >= 500.0: estado = "CRÍTICO"
                        
                        if estado == "ÓPTIMO":
                            if id_cpu > 0 and v_cpu >= limites["cpu_advertencia"]: estado = "PRECAUCIÓN"
                            elif id_ram > 0 and v_ram <= limites["ram_advertencia"]: estado = "PRECAUCIÓN"
                            elif peor_estado_disco == "PRECAUCIÓN": estado = "PRECAUCIÓN"
                            elif id_lat > 0 and v_lat >= 250.0: estado = "PRECAUCIÓN"

                        # Inserción atómica hacia la tabla de telemetría de SIMPOL
                        query = """
                            INSERT INTO monitoreo 
                            (ip_servidor, val_cpu, val_ram, 
                             val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, 
                             val_red, val_latencia, estado_sistema) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        valores = (
                            ip, v_cpu, v_ram,
                            valores_discos['val_disco_1'], valores_discos['val_disco_2'],
                            valores_discos['val_disco_3'], valores_discos['val_disco_4'],
                            valores_discos['val_disco_5'],
                            data.get('red', 0.0), v_lat, estado
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
                        
                        # LOG CONCISO CON SOPORTE COMPORTAMIENTO ADAPTATIVO N/A
                        marcador_estado = "🟢" if estado == "ÓPTIMO" else ("🟡" if estado == "PRECAUCIÓN" else "🔴")
                        log_cpu = f"{v_cpu}%" if id_cpu > 0 else "N/A"
                        log_ram = f"{v_ram}GB" if id_ram > 0 else "N/A"
                        
                        log_agente(f"{marcador_estado} [ASENTADO] NODO: {nombre} ({ip}) | CPU: {log_cpu} | RAM: {log_ram} | Latencia: {f'{v_lat}ms' if id_lat > 0 else 'N/A'} | Almacenamiento: [{discos_resumen}] | Status: {estado}")

                    except Exception:
                        pass # Silencia excepciones internas de nodos corruptos para proteger el buffer

                cursor_ins.close()
                conn_ins.close()

            except Exception:
                pass

            time.sleep(10)

    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        sys.exit(0)

if __name__ == "__main__":
    iniciar_agente()