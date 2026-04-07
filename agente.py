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
    """Consulta la BD usando las mismas etiquetas que alertas.py."""
    u = {"c_crit": 85, "r_crit": 90} 
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        for metrica_sql, clave_dict in [("CPU", "c_crit"), ("RAM", "r_crit")]:
            query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
            cursor.execute(query, (metrica_sql,))
            res = cursor.fetchone()
            if res:
                u[clave_dict] = int(res['umbral_nuevo'])
        
        cursor.close()
        conn.close()
    except:
        pass 
    return u

def iniciar_agente():
    nombre_servidor = "CSU-PRINCIPAL-CARONI"
    print(f"🚀 SIMPOL: Monitoreo iniciado en {nombre_servidor}")
    print("💡 Presiona Ctrl+C para detener el agente de forma segura.")

    while True:
        try:
            cpu, ram, _ = obtener_telemetria()
            umbrales = obtener_umbrales_actuales()
            fecha = datetime.now()

            if cpu >= umbrales["c_crit"] or ram >= umbrales["r_crit"]:
                estado = "CRÍTICO"
            elif cpu >= (umbrales["c_crit"] - 15) or ram >= (umbrales["r_crit"] - 15):
                estado = "PRECAUCIÓN"
            else:
                estado = "NORMAL"

            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = """
                INSERT INTO monitoreo (fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (fecha, nombre_servidor, cpu, ram, estado))
            conn.commit()
            
            print(f"[{fecha.strftime('%H:%M:%S')}] {estado} -> CPU: {cpu}% | RAM: {ram}%")
            
            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            print(f"⚠️ Error de conexión a BD: {err}")
        
        time.sleep(5) 

# --- CAMBIO AQUÍ: MANEJO DEL CIERRE ---
if __name__ == "__main__":
    try:
        iniciar_agente()
    except KeyboardInterrupt:
        print("\n" + "="*40)
        print("🛑 AGENTE DETENIDO POR EL USUARIO")
        print("Finalizando procesos de monitoreo SIMPOL...")
        print("="*40)