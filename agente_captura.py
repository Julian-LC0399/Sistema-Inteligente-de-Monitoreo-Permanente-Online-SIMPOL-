import time
import sys
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

def iniciar_agente():
    print("====================================================")
    print("🚀 SISTEMA SIMPOL - AGENTE DE CAPTURA AUTOMÁTICA")
    print(f"Iniciado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Registro continuo activo (Ctrl+C para detener)")
    print("====================================================\n")
    
    while True:
        try:
            # 1. Obtener telemetría real (PRTG / Simulado)
            cpu_val, ram_val, fuente_msg = obtener_telemetria()
            
            # Lógica de estado bancario
            estado = "CRÍTICO" if cpu_val > 90 or ram_val > 90 else "ALERTA" if cpu_val > 75 else "ESTABLE"
            
            # 2. Guardar en Base de Datos
            conn = conectar_bd()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO monitoreo_30_nodos 
                (nodo_nombre, uso_cpu, uso_ram, estado, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s)
            """
            # Registramos bajo el nombre 'SISTEMA_AUTO' para auditoría
            cursor.execute(query, ("SISTEMA_AUTO", cpu_val, ram_val, estado, datetime.now()))
            
            conn.commit()
            conn.close()
            
            # Log en terminal para que veas que está trabajando
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Registro Exitoso: CPU {cpu_val}% | RAM {ram_val}% | Status: {estado}")
            
            # 3. Frecuencia de muestreo
            # Para el banco se recomienda cada 5 minutos (300 seg). 
            # Para tu defensa o pruebas, puedes usar 30 o 60 segundos.
            time.sleep(60) 
            
        except KeyboardInterrupt:
            print("\n🛑 Agente detenido por el usuario.")
            sys.exit()
        except Exception as e:
            print(f"\n❌ ERROR EN EL AGENTE: {e}")
            time.sleep(10) # Espera antes de reintentar

if __name__ == "__main__":
    iniciar_agente()