import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria 

# Configuración de BD compatible con MySQL 8+
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',
    'database': 'monitoreo_banco',
    'auth_plugin': 'mysql_native_password'
}

def iniciar_agente():
    print("--- 🚀 AGENTE SIMPOL ACTIVADO ---")
    
    while True:
        try:
            # Extraemos los datos usando la lógica de PRTG definida en utils.py
            cpu, ram, origen = obtener_telemetria()
            fecha = datetime.now()
            
            if "LOCAL" in origen:
                print(f"[{fecha.strftime('%H:%M:%S')}] ⚠️ PRTG no respondió. Usando datos locales.")
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO monitoreo_nodos 
                (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) 
                VALUES (%s, %s, %s, %s, %s)
            """
            
            # Determinamos estado simple
            estado_actual = "ESTABLE" if cpu < 85 else "ALERTA"
            valores = (fecha, origen, cpu, ram, estado_actual)
            
            cursor.execute(query, valores)
            conn.commit()
            
            print(f"[{fecha.strftime('%H:%M:%S')}] ✅ Guardado: {origen} (CPU: {cpu}% | RAM: {ram}%)")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error en el ciclo del agente: {e}")
        
        # Espera de 30 segundos entre capturas
        time.sleep(30)

if __name__ == "__main__":
    iniciar_agente()