import time, mysql.connector
from datetime import datetime
from utils import obtener_telemetria

DB_CONFIG = {"host": "127.0.0.1", "user": "root", "password": "1234", "database": "monitoreo_banco", "auth_plugin": "mysql_native_password"}

def obtener_umbrales():
    p = {"CPU_E": 70, "CPU_P": 80, "CPU_C": 90, "RAM_E": 70, "RAM_P": 80, "RAM_C": 90}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        mapa = {"CPU_ESTABLE": "CPU_E", "CPU_PRECAUCION": "CPU_P", "CPU_CRITICO": "CPU_C", 
                "RAM_ESTABLE": "RAM_E", "RAM_PRECAUCION": "RAM_P", "RAM_CRITICO": "RAM_C"}
        for m_db, key in mapa.items():
            cursor.execute("SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1", (m_db,))
            res = cursor.fetchone()
            if res: p[key] = int(res[0])
        cursor.close(); conn.close()
    except: pass
    return p

def iniciar_agente():
    sensor_id = "2094"
    print(f"🚀 SIMPOL: Agente Activo")
    print("----------------------------------------------------------------------")
    try:
        while True:
            cpu, ram, msg_sensor = obtener_telemetria()
            u = obtener_umbrales()
            ahora = datetime.now()
            
            # Identificación de modo (Local o PRTG con el ID 2094)
            if "LOCAL" in msg_sensor.upper():
                identificador_final = "MODO LOCAL"
            else:
                identificador_final = f" {sensor_id}"

            # Lógica de evaluación por niveles
            def evaluar(val, e, p, c):
                if val >= c: return 3 # Crítico
                if val >= p: return 2 # Precaución
                return 1 # Estable

            nivel_cpu = evaluar(cpu, u["CPU_E"], u["CPU_P"], u["CPU_C"])
            nivel_ram = evaluar(ram, u["RAM_E"], u["RAM_P"], u["RAM_C"])
            
            max_nivel = max(nivel_cpu, nivel_ram)
            estado = "CRÍTICO" if max_nivel == 3 else "PRECAUCIÓN" if max_nivel == 2 else "ESTABLE"
            icono = "🔴" if max_nivel == 3 else "🟠" if max_nivel == 2 else "🟢"

            # Inserción en Base de Datos
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                # nombre_csu guardará el ID: 2094 para que el Menú lo muestre
                cursor.execute("INSERT INTO monitoreo (fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema) VALUES (%s, %s, %s, %s, %s)",
                               (ahora, identificador_final, cpu, ram, estado))
                conn.commit(); cursor.close(); conn.close()
                
                # Salida de Consola con el formato solicitado
                timestamp = ahora.strftime('%H:%M:%S')
                print(f"[{timestamp}] {icono} {estado:11} | CPU: {cpu:5}% | RAM: {ram:5}% | Sensor: {identificador_final}")
                
            except mysql.connector.Error as err:
                print(f"[{ahora.strftime('%H:%M:%S')}] ⚠️ Error DB: {err}")

            time.sleep(5)
    except KeyboardInterrupt: 
        print(f"\n🛑 Agente detenido.")

if __name__ == "__main__": iniciar_agente()