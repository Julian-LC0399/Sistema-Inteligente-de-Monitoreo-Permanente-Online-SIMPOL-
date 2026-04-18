import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

# CONFIGURACIÓN UNIFICADA
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password"
}

def obtener_servidores_activos():
    """Recupera la lista de IPs y nombres desde la tabla servidores_it."""
    servidores = []
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Solo trae servidores que tengan el monitoreo activo (estado_monitoreo = 1)
        cursor.execute("SELECT ip, nombre_alias FROM servidores_it WHERE estado_monitoreo = 1")
        servidores = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al consultar catálogo de servidores: {e}")
    return servidores

def iniciar_agente():
    print("🚀 Agente SIMPOL Multi-Servidor iniciado")
    print("📡 Escaneando dispositivos en red interna Banco Caroní...")
    
    # El sensor 2094 ha sido comentado y omitido en la lógica de utils.py por solicitud
    # sensor_id_pc = 2094 

    while True:
        # 1. Obtener la lista actualizada de servidores (permite crecimiento dinámico a 30)
        servidores = obtener_servidores_activos()
        
        if not servidores:
            print("⚠️ No hay servidores activos en el catálogo. Reintentando...")
            time.sleep(10)
            continue

        for serv in servidores:
            ip_actual = serv['ip']
            nombre_actual = serv['nombre_alias']
            
            try:
                # 2. Obtener telemetría (Aquí se asocia un ID_SENSOR por IP si lo tienes, 
                # por ahora pasamos None para que use la lógica de IP de utils.py)
                cpu, ram, msg_sensor = obtener_telemetria(id_sensor=None) 
                ahora = datetime.now()
                
                # 3. Lógica de Estados (Semáforo Institucional)
                estado = "ESTABLE"
                icono = "🟢"
                if cpu >= 90 or ram >= 90:
                    estado = "CRÍTICO"
                    icono = "🔴"
                elif cpu >= 75 or ram >= 75:
                    estado = "PRECAUCIÓN"
                    icono = "🟠"

                # 4. Inserción identificando IP y Nombre
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO monitoreo 
                    (fecha_registro, ip_servidor, uso_cpu, uso_ram, estado_sistema, id_sensor) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                # Usamos un ID genérico 0 para el campo id_sensor si no hay uno específico de PRTG aún
                cursor.execute(query, (ahora, ip_actual, cpu, ram, estado, 0))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                print(f"[{ahora.strftime('%H:%M:%S')}] {icono} {nombre_actual:20} ({ip_actual}) | CPU: {cpu:5.1f}% | RAM: {ram:5.1f}%")

            except Exception as e:
                print(f"❌ Error monitoreando {ip_actual}: {e}")

        # Pausa entre barridos de la lista completa
        print("--- Fin de ciclo. Esperando 10 segundos para el próximo barrido ---")
        time.sleep(10)

if __name__ == "__main__":
    iniciar_agente()