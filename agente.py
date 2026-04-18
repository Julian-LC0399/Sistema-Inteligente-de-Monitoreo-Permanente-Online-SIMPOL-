import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

# CONFIGURACIÓN UNIFICADA CON SIMPOL.SQL
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password"
}

def obtener_umbrales():
    """Recupera los umbrales actualizados desde historico_umbrales."""
    # Valores por defecto del Banco
    p = {"CPU_E": 70, "CPU_P": 80, "CPU_C": 90, "RAM_E": 70, "RAM_P": 80, "RAM_C": 90}
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Mapeo corregido según simpol.sql (parametro y valor_nuevo)
        mapa = {
            "CPU_ESTABLE": "CPU_E", "CPU_PRECAUCION": "CPU_P", "CPU_CRITICO": "CPU_C", 
            "RAM_ESTABLE": "RAM_E", "RAM_PRECAUCION": "RAM_P", "RAM_CRITICO": "RAM_C"
        }
        
        for m_db, key in mapa.items():
            # Consulta corregida: valor_nuevo y parametro
            query = "SELECT valor_nuevo FROM historico_umbrales WHERE parametro = %s ORDER BY fecha_cambio DESC LIMIT 1"
            cursor.execute(query, (m_db,))
            res = cursor.fetchone()
            if res:
                p[key] = float(res[0])
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Nota: Usando umbrales por defecto (Error: {e})")
    return p

def iniciar_agente():
    print("🚀 Agente SIMPOL iniciado (Presione Ctrl+C para detener)")
    sensor_id = 2094 # ID Institucional
    
    while True:
        try:
            # 1. Obtener datos actuales y umbrales frescos
            cpu, ram, msg_sensor = obtener_telemetria()
            u = obtener_umbrales()
            ahora = datetime.now()
            
            # 2. Lógica de estados (Semáforo)
            max_nivel = 1 # 1: Estable, 2: Precaución, 3: Crítico
            
            # Chequeo de CPU
            if cpu >= u["CPU_C"]: max_nivel = 3
            elif cpu >= u["CPU_P"] and max_nivel < 3: max_nivel = 2
            
            # Chequeo de RAM
            if ram >= u["RAM_C"]: max_nivel = 3
            elif ram >= u["RAM_P"] and max_nivel < 3: max_nivel = 2
            
            estado = "CRÍTICO" if max_nivel == 3 else "PRECAUCIÓN" if max_nivel == 2 else "ESTABLE"
            icono = "🔴" if max_nivel == 3 else "🟠" if max_nivel == 2 else "🟢"

            # 3. Inserción en la base de datos
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                # Sincronizado exactamente con simpol.sql
                query = """
                    INSERT INTO monitoreo 
                    (fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (ahora, sensor_id, cpu, ram, estado))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                timestamp = ahora.strftime('%H:%M:%S')
                print(f"[{timestamp}] {icono} {estado:11} | CPU: {cpu:5.1f}% | RAM: {ram:5.1f}% | Fuente: {msg_sensor}")
                
            except mysql.connector.Error as err:
                print(f"[{ahora.strftime('%H:%M:%S')}] ⚠️ Error de Inserción: {err}")

        except Exception as e:
            print(f"❌ Error inesperado en el ciclo: {e}")

        # Espera de 5 segundos para el siguiente ciclo
        time.sleep(5)

if __name__ == "__main__":
    iniciar_agente()