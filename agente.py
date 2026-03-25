import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "1234",
    "database": "monitoreo_banco",
    "auth_plugin": "mysql_native_password",
}

def obtener_umbrales_actuales():
    """Consulta la tabla historico_umbrales para aplicar la última regla guardada."""
    u = {"c_crit": 85, "r_crit": 90, "c_warn": 70, "r_warn": 75}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Buscamos por la columna 'metrica' y ordenamos por 'fecha_cambio'
        mapa = {"CPU_CRIT": "c_crit", "RAM_CRIT": "r_crit", "CPU_WARN": "c_warn", "RAM_WARN": "r_warn"}
        
        for metrica_sql, clave_dict in mapa.items():
            cursor.execute(f"SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = '{metrica_sql}' ORDER BY fecha_cambio DESC LIMIT 1")
            res = cursor.fetchone()
            if res:
                u[clave_dict] = int(res['umbral_nuevo'])
        
        cursor.close()
        conn.close()
    except:
        pass
    return u

def iniciar_agente():
    print("--- 🚀 AGENTE SIMPOL ACTIVADO (SISTEMA CSU) ---")
    while True:
        try:
            cpu, ram, _ = obtener_telemetria()
            umbrales = obtener_umbrales_actuales()
            fecha = datetime.now()

            # Clasificación dinámica basada en la BD
            if cpu >= umbrales["c_crit"] or ram >= umbrales["r_crit"]:
                estado = "CRÍTICO"
            elif cpu >= umbrales["c_warn"] or ram >= umbrales["r_warn"]:
                estado = "PRECAUCIÓN"
            else:
                estado = "NORMAL"

            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = "INSERT INTO monitoreo (fecha_registro, uso_cpu, uso_ram, estado_sistema) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fecha, cpu, ram, estado))
            conn.commit()
            print(f"[{fecha.strftime('%H:%M:%S')}] Registro guardado: {estado}")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(30)

if __name__ == "__main__":
    iniciar_agente()