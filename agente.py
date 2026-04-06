import time
import mysql.connector
from datetime import datetime
from utils import obtener_telemetria

# Configuración de conexión
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
        # Mapeo de métricas SQL a claves del diccionario
        mapa = {
            "CPU_CRIT": "c_crit", 
            "RAM_CRIT": "r_crit", 
            "CPU_WARN": "c_warn", 
            "RAM_WARN": "r_warn"
        }
        
        for metrica_sql, clave_dict in mapa.items():
            cursor.execute(f"SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = '{metrica_sql}' ORDER BY fecha_cambio DESC LIMIT 1")
            res = cursor.fetchone()
            if res:
                u[clave_dict] = int(res['umbral_nuevo'])
        
        cursor.close()
        conn.close()
    except:
        pass # Si falla la BD, usa los valores por defecto
    return u

def iniciar_agente():
    print("\n" + "="*50)
    print("🚀 AGENTE SIMPOL ACTIVADO (SISTEMA CSU)")
    print(f"📡 Monitoreando en: {DB_CONFIG['host']}")
    print("Presione Ctrl+C para detener el agente de forma segura.")
    print("="*50 + "\n")

    try:
        while True:
            try:
                # 1. Obtener telemetría del sistema
                cpu, ram, _ = obtener_telemetria()
                umbrales = obtener_umbrales_actuales()
                fecha = datetime.now()

                # 2. Clasificación dinámica del estado
                if cpu >= umbrales["c_crit"] or ram >= umbrales["r_crit"]:
                    estado = "CRÍTICO"
                elif cpu >= umbrales["c_warn"] or ram >= umbrales["r_warn"]:
                    estado = "PRECAUCIÓN"
                else:
                    estado = "NORMAL"

                # 3. Guardar en la base de datos
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                query = "INSERT INTO monitoreo (fecha_registro, uso_cpu, uso_ram, estado_sistema) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (fecha, cpu, ram, estado))
                conn.commit()
                
                # Feedback en consola
                print(f"[{fecha.strftime('%H:%M:%S')}] CPU: {cpu}% | RAM: {ram}% | ESTADO: {estado}")
                
                cursor.close()
                conn.close()

            except mysql.connector.Error as err:
                print(f"❌ Error de Base de Datos: {err}")
            
            # 4. Espera de 5 segundos
            time.sleep(5)

    except KeyboardInterrupt:
        # Captura el cierre manual (Ctrl+C)
        print("\n" + "—"*50)
        print("🛑 SEÑAL DE DETENCIÓN RECIBIDA")
        print(f"🕒 Hora de cierre: {datetime.now().strftime('%H:%M:%S')}")
        print("✅ Agente SIMPOL desconectado correctamente.")
        print("—"*50)

if __name__ == "__main__":
    iniciar_agente()