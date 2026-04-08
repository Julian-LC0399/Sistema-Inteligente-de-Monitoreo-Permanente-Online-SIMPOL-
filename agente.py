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

def obtener_umbrales_vivos():
    u = {"CPU": 90, "RAM": 90}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        for metrica in ["CPU", "RAM"]:
            query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
            cursor.execute(query, (metrica,))
            res = cursor.fetchone()
            if res:
                u[metrica] = int(res['umbral_nuevo'])
        cursor.close()
        conn.close()
    except: 
        pass
    return u

def iniciar_agente():
    nombre_servidor = "CSU-PRINCIPAL-CARONI"
    print(f"🚀 SIMPOL: Monitoreo iniciado en {nombre_servidor}")
    print("Presiona Ctrl+C para detener el agente de forma segura.")

    try:
        while True:
            try:
                cpu, ram, _ = obtener_telemetria()
                umbrales = obtener_umbrales_vivos()
                fecha = datetime.now()

                u_limite = max(umbrales["CPU"], umbrales["RAM"])
                valor_actual = max(cpu, ram)

                if valor_actual >= u_limite:
                    estado = "CRÍTICO"
                elif valor_actual > 70:
                    estado = "PRECAUCIÓN"
                else:
                    estado = "ESTABLE"

                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                query = """
                    INSERT INTO monitoreo (fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (fecha, nombre_servidor, cpu, ram, estado))
                conn.commit()
                cursor.close()
                conn.close()
                
                # Feedback en consola para saber que está vivo
                print(f"[{fecha.strftime('%H:%M:%S')}] {estado} - CPU: {cpu}% RAM: {ram}%")
                
            except mysql.connector.Error as err:
                print(f"⚠️ Error de base de datos: {err}")
            
            # El banco requiere monitoreo cada 5 segundos
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n🛑 SEÑAL DE DETENCIÓN RECIBIDA")
        print("Finalizando procesos de SIMPOL y cerrando conexiones...")
        print("Agente detenido correctamente. ¡Hasta luego!")

if __name__ == "__main__":
    iniciar_agente()