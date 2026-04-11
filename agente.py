import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

# CONFIGURACIÓN UNIFICADA CON SIMPOL.SQL
DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol",  # Actualizado de monitoreo_banco a simpol
    "auth_plugin": "mysql_native_password"
}

def obtener_umbrales():
    """Recupera los umbrales configurados por el analista en la BD."""
    # Valores por defecto del Banco
    p = {"CPU_E": 70, "CPU_P": 80, "CPU_C": 90, "RAM_E": 70, "RAM_P": 80, "RAM_C": 90}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        mapa = {
            "CPU_ESTABLE": "CPU_E", "CPU_PRECAUCION": "CPU_P", "CPU_CRITICO": "CPU_C", 
            "RAM_ESTABLE": "RAM_E", "RAM_PRECAUCION": "RAM_P", "RAM_CRITICO": "RAM_C"
        }
        for m_db, key in mapa.items():
            cursor.execute("SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1", (m_db,))
            res = cursor.fetchone()
            if res: 
                p[key] = int(res[0])
        cursor.close()
        conn.close()
    except: 
        pass # Si falla la BD, usa los valores por defecto
    return p

def evaluar_nivel(val, e, p, c):
    """Lógica de niveles: 3=Crítico, 2=Precaución, 1=Estable."""
    if val >= c: return 3
    if val >= p: return 2
    return 1

def iniciar_agente():
    sensor_id = 2094 
    print(f"🚀 SIMPOL: Agente Activo (Iniciando monitoreo en Sensor {sensor_id})")
    print("----------------------------------------------------------------------")
    
    try:
        while True:
            # 1. Obtener telemetría y umbrales
            cpu, ram, msg_sensor = obtener_telemetria() # msg_sensor ya no se ignora
            u = obtener_umbrales()
            ahora = datetime.now()
            
            # 2. Evaluar estados
            nivel_cpu = evaluar_nivel(cpu, u["CPU_E"], u["CPU_P"], u["CPU_C"])
            nivel_ram = evaluar_nivel(ram, u["RAM_E"], u["RAM_P"], u["RAM_C"])
            
            max_nivel = max(nivel_cpu, nivel_ram)
            estado = "CRÍTICO" if max_nivel == 3 else "PRECAUCIÓN" if max_nivel == 2 else "ESTABLE"
            icono = "🔴" if max_nivel == 3 else "🟠" if max_nivel == 2 else "🟢"

            # 3. Inserción compatible con simpol.sql
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                # Sincronizado con tabla: monitoreo (id, fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema)
                query = """
                    INSERT INTO monitoreo 
                    (fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (ahora, sensor_id, cpu, ram, estado))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                # Salida de Consola enriquecida con la variable msg_sensor
                timestamp = ahora.strftime('%H:%M:%S')
                print(f"[{timestamp}] {icono} {estado:11} | CPU: {cpu:5.1f}% | RAM: {ram:5.1f}% | Fuente: {msg_sensor}")
                
            except mysql.connector.Error as err:
                print(f"[{ahora.strftime('%H:%M:%S')}] ⚠️ Error de Inserción: {err}")

            # Espera institucional de 5 segundos
            time.sleep(5)
            
    except KeyboardInterrupt: 
        print(f"\n🛑 Agente detenido manualmente por el usuario.")

if __name__ == "__main__": 
    iniciar_agente()