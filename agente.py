import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria 

# Configuración de BD que ya probamos con el "LOGRADO"
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',
    'database': 'monitoreo_banco',
    'auth_plugin': 'mysql_native_password'
}

def iniciar_agente():
    print("--- 🚀 AGENTE SIMPOL ACTIVADO (FUENTE: UTILS.PY) ---")
    
    while True:
        try:
            # Extraemos los datos usando tu lógica de PRTG
            cpu, ram, origen = obtener_telemetria()
            
            fecha = datetime.now()
            # Si el origen dice "MODO LOCAL", es que PRTG falló
            if "LOCAL" in origen:
                print(f"⚠️ Alerta: PRTG no respondió. Usando datos locales.")
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO monitoreo_nodos 
                (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) 
                VALUES (%s, %s, %s, %s, %s)
            """
            # Guardamos 'PRTG_SENSOR' o 'MODO LOCAL' en la columna nodo_nombre
            valores = (fecha, origen, cpu, ram, "ESTABLE" if cpu < 75 else "ALERTA")
            
            cursor.execute(query, valores)
            conn.commit()
            
            print(f"[{fecha.strftime('%H:%M:%S')}] ✅ Guardado: {origen} (CPU: {cpu}%)")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    iniciar_agente()