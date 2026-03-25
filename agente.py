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

def obtener_umbrales_vigentes():
    """Recupera los últimos umbrales guardados por el usuario en la BD."""
    u = {"c_crit": 85, "r_crit": 90, "c_warn": 70, "r_warn": 75}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Mapeo de métricas según alertas.py
        mapa = {"CPU_CRIT": "c_crit", "RAM_CRIT": "r_crit", "CPU_WARN": "c_warn", "RAM_WARN": "r_warn"}
        for db_key, dict_key in mapa.items():
            cursor.execute(f"SELECT valor_nuevo FROM historico_umbrales WHERE metrica = '{db_key}' ORDER BY id_hist_umb DESC LIMIT 1")
            res = cursor.fetchone()
            if res: u[dict_key] = int(res['valor_nuevo'])
        cursor.close()
        conn.close()
    except:
        pass # Si falla, usa los valores por defecto definidos arriba
    return u

def iniciar_agente():
    print("--- 🚀 AGENTE SIMPOL ACTIVADO (SISTEMA CSU) ---")
    while True:
        try:
            cpu, ram, origen = obtener_telemetria()
            u = obtener_umbrales_vigentes()
            fecha = datetime.now()

            # DETERMINACIÓN DEL ESTADO INMUTABLE
            if cpu >= u["c_crit"] or ram >= u["r_crit"]:
                estado_fijo = "CRÍTICO"
            elif cpu >= u["c_warn"] or ram >= u["r_warn"]:
                estado_fijo = "PRECAUCIÓN"
            else:
                estado_fijo = "NORMAL"

            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = """
                INSERT INTO monitoreo (fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (fecha, "CSU-Principal", cpu, ram, estado_fijo))
            conn.commit()
            print(f"[{fecha.strftime('%H:%M:%S')}] ✅ Guardado: {estado_fijo}")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(30)

if __name__ == "__main__":
    iniciar_agente()