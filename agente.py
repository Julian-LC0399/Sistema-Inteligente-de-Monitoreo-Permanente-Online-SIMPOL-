import time
import mysql.connector
from datetime import datetime
import sys
import os

# Importamos la función desde utils.py
from utils import obtener_telemetria_total 

# CONFIGURACIÓN UNIFICADA (Ajustar IP si la BD no es local)
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password",
    "connect_timeout": 5
}

def obtener_servidores_activos():
    """Recupera la lista de servidores con monitoreo activado."""
    servidores = []
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT ip, nombre_alias, id_sensor_cpu, id_sensor_ram, 
                   id_sensor_disco, id_sensor_red, id_sensor_latencia 
            FROM servidores_it 
            WHERE estado_monitoreo = 1
        """
        cursor.execute(query)
        servidores = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"❌ Error al consultar catálogo de servidores: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return servidores

def iniciar_agente():
    print("====================================================")
    print("🚀 AGENTE SIMPOL V2.0 - BANCO CARONÍ")
    print(f"📅 Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("📡 Estado: Monitoreando RAM, DISCO, CPU, RED y LATENCIA")
    print("====================================================")
    
    while True:
        servidores = obtener_servidores_activos()
        
        if not servidores:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Sin servidores activos para monitorear.")
            time.sleep(20)
            continue

        conn_ins = None
        try:
            # Una sola conexión por ciclo para mayor eficiencia
            conn_ins = mysql.connector.connect(**DB_CONFIG)
            cursor_ins = conn_ins.cursor()

            for serv in servidores:
                nombre_actual = serv['nombre_alias']
                
                try:
                    # 1. Obtener telemetría desde utils.py (PRTG o Local)
                    data = obtener_telemetria_total(serv) 
                    ahora = datetime.now()
                    
                    # 2. Lógica de Estados
                    # Tomamos el valor más alto entre CPU, RAM y Disco para el estado visual
                    max_uso = max(data.get('cpu', 0), data.get('ram', 0), data.get('disco', 0))
                    latencia = data.get('latencia', 0)
                    
                    estado = "ÓPTIMO"
                    icono = "🟢"
                    
                    if max_uso >= 90 or latencia > 200:
                        estado = "CRÍTICO"
                        icono = "🔴"
                    elif max_uso >= 75 or latencia > 100:
                        estado = "PRECAUCIÓN"
                        icono = "🟠"

                    # 3. Inserción en la base de datos
                    query = """
                        INSERT INTO monitoreo 
                        (fecha_registro, ip_servidor, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    valores = (
                        ahora, 
                        serv['ip'], 
                        data['cpu'], 
                        data['ram'], 
                        data['disco'], 
                        data['red'], 
                        latencia, 
                        estado
                    )
                    
                    cursor_ins.execute(query, valores)
                    conn_ins.commit()
                    
                    # Log en consola
                    origen = data.get('msg', '📡')
                    print(f"[{ahora.strftime('%H:%M:%S')}] {icono} {nombre_actual:15} | {origen} | CPU:{data['cpu']:5.1f}% | RAM:{data['ram']:5.1f}%")

                except Exception as e:
                    print(f"❌ Error procesando servidor {nombre_actual}: {e}")

            cursor_ins.close()
            
        except Exception as e:
            print(f"❌ Error crítico de conexión a la Base de Datos: {e}")
        finally:
            if conn_ins and conn_ins.is_connected():
                conn_ins.close()

        # Espera antes del siguiente ciclo de escaneo
        time.sleep(15)

if __name__ == "__main__":
    try:
        iniciar_agente()
    except KeyboardInterrupt:
        print("\n\n🛑 Agente detenido manualmente.")
        print("👋 Cerrando procesos de forma segura...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fatal en el hilo del agente: {e}")
        time.sleep(5)