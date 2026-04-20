import time
import mysql.connector
from datetime import datetime
# Importamos la nueva función que maneja las 5 métricas
from utils import obtener_telemetria_total 

# CONFIGURACIÓN UNIFICADA
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password"
}

def obtener_servidores_activos():
    """Recupera la lista completa de servidores y sus 5 IDs de sensores."""
    servidores = []
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Traemos todas las columnas de sensores para poder consultarlas
        query = """
            SELECT ip, nombre_alias, id_sensor_cpu, id_sensor_ram, 
                   id_sensor_disco, id_sensor_red, id_sensor_latencia 
            FROM servidores_it 
            WHERE estado_monitoreo = 1
        """
        cursor.execute(query)
        servidores = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al consultar catálogo: {e}")
    return servidores

def iniciar_agente():
    print("🚀 Agente SIMPOL Multi-Sensor (V2.0) iniciado")
    print("📡 Monitoreando: RAM, DISCO, CPU, RED y LATENCIA...")
    
    while True:
        servidores = obtener_servidores_activos()
        
        if not servidores:
            print("⚠️ Esperando servidores activos...")
            time.sleep(10)
            continue

        for serv in servidores:
            ip_actual = serv['ip']
            nombre_actual = serv['nombre_alias']
            
            try:
                # 1. Obtener telemetría total (Pasa el diccionario con los 5 IDs)
                data = obtener_telemetria_total(serv) 
                ahora = datetime.now()
                
                # 2. Lógica de Estados (Basada en la métrica más crítica)
                # Evaluamos CPU, RAM y DISCO para el semáforo
                max_uso = max(data['cpu'], data['ram'], data['disco'])
                
                estado = "ÓPTIMO"
                icono = "🟢"
                if max_uso >= 90 or data['latencia'] > 200:
                    estado = "CRÍTICO"
                    icono = "🔴"
                elif max_uso >= 75 or data['latencia'] > 100:
                    estado = "PRECAUCIÓN"
                    icono = "🟠"

                # 3. Inserción en la nueva tabla de monitoreo (5 valores)
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO monitoreo 
                    (fecha_registro, ip_servidor, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                valores = (
                    ahora, 
                    ip_actual, 
                    data['cpu'], 
                    data['ram'], 
                    data['disco'], 
                    data['red'], 
                    data['latencia'], 
                    estado
                )
                
                cursor.execute(query, valores)
                conn.commit()
                cursor.close()
                conn.close()
                
                # Log visual en consola más completo
                print(f"[{ahora.strftime('%H:%M:%S')}] {icono} {nombre_actual:18} | CPU:{data['cpu']:4.1f}% | RAM:{data['ram']:4.1f}% | DISK:{data['disco']:4.1f}% | LAT:{data['latencia']}ms")

            except Exception as e:
                print(f"❌ Error en {nombre_actual} ({ip_actual}): {e}")

        print(f"--- Ciclo completado. {len(servidores)} servidores procesados. ---")
        time.sleep(15) # Pausa de seguridad para no saturar la API de PRTG

if __name__ == "__main__":
    iniciar_agente()