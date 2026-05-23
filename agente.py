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
        cursor = conn.cursor(dictionary=True)
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
    """
    Consulta los límites específicos del semáforo multidisco (5 Volúmenes) en la BD.
    Mapeo explícito y dinámico adaptado a floats para precisión con PRTG.
    """
    # Contingencias dinámicas iniciales preventivas por IP antes de consultar BD
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
            WHERE ip_servidor = %s 
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
    except Exception as e:
        log_agente(f"⚠️ Error al recuperar umbrales específicos para {ip}: {e}. Usando contingencia mapeada.")
    return umbrales

def iniciar_agente():
    """Motor principal del demonio de telemetría."""
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 --- INICIANDO MOTOR DE MONITOREO DINÁMICO (5 DISCO MAX / PRECISION DECIMAL V3.2) ---")
    
    try:
        from utils import obtener_telemetria_total
        log_agente("✅ Módulos de telemetría acoplados con éxito.")
    except Exception as e:
        log_agente(f"💥 Error crítico al importar UTILS: {e}")
        AGENTE_EN_EJECUCION = False
        return

    try:
        while True:
            try:
                servidores = obtener_servidores_activos()
                
                if not servidores:
                    log_agente("⚠️ Sin servidores activos para monitorear en la tabla 'servidores'.")
                    time.sleep(10)
                    continue

                conn_ins = mysql.connector.connect(**DB_CONFIG)
                cursor_ins = conn_ins.cursor(dictionary=True)

                for serv in servidores:
                    try:
                        nombre = serv['nombre_alias']
                        ip = serv['ip']
                        
                        id_cpu = serv.get('id_sensor_cpu', 0)
                        id_ram = serv.get('id_sensor_ram', 0)
                        
                        if id_cpu == 0 or id_ram == 0:
                            log_agente(f"⏭️ Nodo '{nombre}' ({ip}) omitido temporalmente: Sensores de CPU/RAM no mapeados.")
                            continue
                        
                        log_agente(f"🔄 Procesando telemetría para nodo: '{nombre}' ({ip})")
                        
                        # Consumo de API real desde utils
                        data = obtener_telemetria_total(serv)
                        
                        v_cpu = float(data.get('cpu', 0.0))
                        v_ram = float(data.get('ram', 0.0))
                        v_lat = float(data.get('latencia', 0.0))
                        
                        if v_ram > 1024000:
                            v_ram = round(v_ram / (1024**3), 2)
                        
                        # SOLUCIÓN ARQUITECTÓNICA V3.2: Inicialización estricta de la matriz para evitar nulos o descalces visuales
                        valores_discos = {
                            'val_disco_1': 0.0,
                            'val_disco_2': 0.0,
                            'val_disco_3': 0.0,
                            'val_disco_4': 0.0,
                            'val_disco_5': 0.0
                        }
                        peor_estado_disco = "ÓPTIMO"
                        limites = obtener_umbrales_agente(cursor_ins, ip)
                        
                        for i in range(1, 6):
                            id_sensor_disco = serv.get(f'id_sensor_disco_{i}', 0)
                            
                            if id_sensor_disco > 0:
                                # Intenta extraer usando 'disco_X'. Si da nulo, busca un fallback en la data cruda de PRTG
                                raw_val = data.get(f'disco_{i}')
                                if raw_val is None:
                                    raw_val = data.get(f'val_disco_{i}', 0.0)
                                    
                                v_disco_actual = float(raw_val) if raw_val is not None else 0.0
                                
                                # Si utils entrega el espacio de disco en Bytes, normalizar a GB reales
                                if v_disco_actual > 1024000:
                                    v_disco_actual = round(v_disco_actual / (1024**3), 2)
                                
                                valores_discos[f'val_disco_{i}'] = v_disco_actual
                                
                                # --- Evaluación de Semáforo de Almacenamiento ---
                                if v_disco_actual <= limites[f"disco_{i}_critico"]:
                                    peor_estado_disco = "CRÍTICO"
                                elif v_disco_actual <= limites[f"disco_{i}_advertencia"] and peor_estado_disco != "CRÍTICO":
                                    peor_estado_disco = "PRECAUCIÓN"

                        # =========================================================
                        # EVALUACIÓN GENERAL DE SEMÁFORO DE TRES ESTADOS
                        # =========================================================
                        estado = "ÓPTIMO"
                        
                        if (v_cpu >= limites["cpu_critico"] or 
                            v_ram <= limites["ram_critico"] or 
                            peor_estado_disco == "CRÍTICO" or 
                            v_lat >= 500.0):
                            estado = "CRÍTICO"
                            
                        elif (v_cpu >= limites["cpu_advertencia"] or 
                              v_ram <= limites["ram_advertencia"] or 
                              peor_estado_disco == "PRECAUCIÓN" or 
                              v_lat >= 250.0):
                            estado = "PRECAUCIÓN"

                        # Inserción limpia hacia la tabla de telemetría de SIMPOL
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
                        
                        conn_write = mysql.connector.connect(**DB_CONFIG)
                        cursor_write = conn_write.cursor()
                        cursor_write.execute(query, valores)
                        conn_write.commit()
                        cursor_write.close()
                        conn_write.close()
                        
                        log_agente(f"💾 Telemetría asentada para '{nombre}' ({ip}). Métricas: CPU:{v_cpu}% | RAM:{v_ram}GB. Discos activos mapeados: C:{valores_discos['val_disco_1']}GB, D:{valores_discos['val_disco_2']}GB, K:{valores_discos['val_disco_3']}GB. Estado: {estado}")

                    except Exception as e:
                        log_agente(f"❌ Error al recolectar telemetría en {serv.get('nombre_alias', 'Desconocido')}: {e}")

                cursor_ins.close()
                conn_ins.close()

            except Exception as e:
                log_agente(f"💥 Error en ciclo principal del motor: {e}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 [AGENTE] Interrupción manual detectada (Control + C).")
        log_agente("🛑 Motor de telemetría detenido por el operador del sistema.")
        AGENTE_EN_EJECUCION = False
        sys.exit(0)

if __name__ == "__main__":
    iniciar_agente()