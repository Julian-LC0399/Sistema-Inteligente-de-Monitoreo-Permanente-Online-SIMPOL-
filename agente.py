import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

# Configuración de BD compatible con el Script Maestro y MySQL 8+
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "1234",
    "database": "monitoreo_banco",
    "auth_plugin": "mysql_native_password", # Crucial para evitar error 4058
}

def iniciar_agente():
    print("--- 🚀 AGENTE SIMPOL ACTIVADO (SISTEMA CSU) ---")
    print("Capturando métricas con lógica de Semáforo: Normal, Advertencia, Critico")

    while True:
        try:
            # 1. Extraemos los datos (PRTG o Local vía utils.py)
            cpu, ram, origen = obtener_telemetria()
            fecha = datetime.now()

            # 2. LÓGICA DE CLASIFICACIÓN PROFESIONAL (3 NIVELES)
            # Definimos los umbrales base para el guardado automático
            estado_actual = "Normal" # Por defecto
            
            if cpu >= 85 or ram >= 90:
                estado_actual = "Critico"
            elif cpu >= 70 or ram >= 75:
                estado_actual = "Advertencia" # Nivel de precaución solicitado

            # 3. Conexión e Inserción en la BBDD Profesional
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # SQL ACTUALIZADO: Tabla 'monitoreo' y columna 'nombre_csu'
            query = """
                INSERT INTO monitoreo 
                (fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema) 
                VALUES (%s, %s, %s, %s, %s)
            """

            valores = (fecha, "CSU-Principal", cpu, ram, estado_actual)

            cursor.execute(query, valores)
            conn.commit()

            # Log en consola para el técnico de guardia
            print(
                f"[{fecha.strftime('%H:%M:%S')}] ✅ Guardado en CSU: CPU {cpu}% | RAM {ram}% | ESTADO: {estado_actual.upper()}"
            )

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Error en el ciclo del agente: {e}")

        # Intervalo de 30 segundos para no saturar los logs del banco
        time.sleep(30)

if __name__ == "__main__":
    iniciar_agente()