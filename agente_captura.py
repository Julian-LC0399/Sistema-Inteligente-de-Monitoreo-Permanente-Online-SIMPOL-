import time
import sys
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

def iniciar_agente():
    print("====================================================")
    print("🚀 SIMPOL - AGENTE DE CAPTURA REAL (SENSOR 2094)")
    print(f"Iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("====================================================\n")
    
    while True:
        try:
            # 1. Obtener telemetría de la API de PRTG
            cpu_val, ram_val, fuente = obtener_telemetria()
            
            # Lógica de estado bancario (Alertas)
            estado = "CRÍTICO" if cpu_val > 90 else "ALERTA" if cpu_val > 75 else "ESTABLE"
            
            # 2. Insertar en la Base de Datos
            conn = conectar_bd()
            cursor = conn.cursor()
            query = """
                INSERT INTO monitoreo_30_nodos 
                (nodo_nombre, uso_cpu, uso_ram, estado, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, ("SISTEMA_AUTO", cpu_val, ram_val, estado, datetime.now()))
            conn.commit()
            conn.close()
            
            # Log de control en la consola del .exe
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛰️ PRTG -> BD: {cpu_val}% | Status: {estado}")
            
            # Muestreo cada 20 segundos
            time.sleep(20)
            
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            print(f"Error Agente: {e}")
            time.sleep(10)

if __name__ == "__main__":
    iniciar_agente()