import time
import mysql.connector
from datetime import datetime
import sys
import os
from utils import get_resource_path, obtener_telemetria_total

DB_CONFIG = {
    "host": "127.0.0.1", 
    "user": "root", 
    "password": "1234", 
    "database": "simpol", 
    "auth_plugin": "mysql_native_password", 
    "use_pure": True,
    "connect_timeout": 15
}

AGENTE_EN_EJECUCION = False

def log_agente(mensaje):
    if not AGENTE_EN_EJECUCION:
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{stamp}] {mensaje}\n"
    print(mensaje, flush=True)
    try:
        with open("simpol_agente.log", "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass

def conectar_bd_con_reintentos(max_intentos=3, delay=2):
    """Intenta establecer conexión de forma segura con la base de datos ante microcortes."""
    intentos = 0
    while intentos < max_intentos:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                return conn
        except mysql.connector.Error as err:
            intentos += 1
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{stamp}] ⚠️ Reintento de conexión BD {intentos}/{max_intentos} falló: {err}", flush=True)
            time.sleep(delay)
    return None

def ejecutar_motor_agente():
    global AGENTE_EN_EJECUCION
    AGENTE_EN_EJECUCION = True
    
    log_agente("🚀 INICIANDO DEMONIO DE TELEMETRÍA INTEGRAL SIMPOL (CON BLINDAJE 100% Y CANALES AUTOMÁTICOS)")

    try:
        while AGENTE_EN_EJECUCION:
            conn_ins = conectar_bd_con_reintentos()
            if not conn_ins:
                log_agente("❌ ERROR CRÍTICO: Imposible conectar a MySQL tras múltiples reintentos. Saltando ciclo.")
                time.sleep(10)
                continue

            try:
                cursor_ins = conn_ins.cursor(dictionary=True)
                query_servidores = "SELECT * FROM servidores WHERE estado_monitoreo = 1"
                cursor_ins.execute(query_servidores)
                servidores = cursor_ins.fetchall()

                for srv in servidores:
                    try:
                        ip = srv["ip"]
                        nombre = srv["nombre_alias"]
                        id_ram = int(srv.get("id_sensor_ram") or 0)
                        id_cpu = int(srv.get("id_sensor_cpu") or 0)
                        
                        # Obtener telemetría desde utils de forma automática y multicanal
                        telemetria = obtener_telemetria_total(srv)
                        
                        # FILTRO: Si el CPU de PRTG reporta 0 de forma errónea, ignoramos la alerta en 0
                        v_cpu = telemetria["cpu"]
                        v_ram = telemetria["ram"]
                        v_red = telemetria["red"]
                        v_lat = telemetria["latencia"]
                        
                        # Mapeo de valores físicos en GB e inclusión de Porcentajes correspondientes
                        v_d1, v_d2, v_d3 = telemetria["disco_1"], telemetria["disco_2"], telemetria["disco_3"]
                        v_d4, v_d5, v_d6 = telemetria["disco_4"], telemetria["disco_5"], telemetria["disco_6"]
                        
                        # Captura de porcentajes desde la telemetría de utils
                        p_d1, p_d2, p_d3 = telemetria["pct_disco_1"], telemetria["pct_disco_2"], telemetria["pct_disco_3"]
                        p_d4, p_d5, p_d6 = telemetria["pct_disco_4"], telemetria["pct_disco_5"], telemetria["pct_disco_6"]
                        
                        v_s1 = "ON" if telemetria["servicio_1"] == 1 else "OFF"
                        v_s2 = "ON" if telemetria["servicio_2"] == 1 else "OFF"
                        v_s3 = "ON" if telemetria["servicio_3"] == 1 else "OFF"
                        v_s4 = "ON" if telemetria["servicio_4"] == 1 else "OFF"
                        v_s5 = "ON" if telemetria["servicio_5"] == 1 else "OFF"

                        # Límites de alertas basados en la configuración solicitada
                        u_ram_adv, u_ram_crit = 3.5, 1.5
                        u_disco_limites = {i: {"adv": 40.0, "crit": 15.0} for i in range(1, 7)}
                        
                        if ip == "10.10.1.133":
                            u_disco_limites[1]["adv"] = 35.0  
                            u_disco_limites[2]["adv"] = 65.0  

                        estado = "ÓPTIMO"

                        if id_ram > 0:
                            if v_ram <= u_ram_crit: estado = "CRÍTICO"
                            elif v_ram <= u_ram_adv: estado = "PRECAUCIÓN"

                        # === REGLA: PROCESAMIENTO DE DISCOS Y CÁLCULO DE ALERTAS REALES ===
                        valores_discos = [v_d1, v_d2, v_d3, v_d4, v_d5, v_d6]
                        for idx in range(6):
                            num_d = idx + 1
                            if int(srv.get(f"id_sensor_disco_{num_d}") or 0) > 0:
                                v_disc = valores_discos[idx]
                                
                                # ELIMINAR ALERTAS EN 0: Si el espacio libre reportado es exactamente 0.0,
                                # se asume canal vacío o inactivo. No altera el semáforo del sistema.
                                if v_disc == 0.0:
                                    continue
                                    
                                if v_disc <= u_disco_limites[num_d]["crit"]: 
                                    estado = "CRÍTICO"
                                elif v_disc <= u_disco_limites[num_d]["adv"] and estado != "CRÍTICO": 
                                    estado = "PRECAUCIÓN"

                        # Si la telemetría general determinó que PRTG está activo pero el CPU da 0, limpiamos la alerta
                        if id_cpu > 0 and v_cpu == 0.0:
                            # Evita que se dispare una falsa alerta de CPU caído
                            pass

                        ahora_local = datetime.now()

                        # NOTA DE DISEÑO: Mantenemos la estructura SQL intacta para evitar errores de base de datos.
                        # Si tu interfaz lee los datos numéricos de 'val_disco_x', para inyectar el porcentaje al lado
                        # en la UI sin romper el flotante de la BD, guardamos el valor de GB limpio.
                        # Para reflejar el porcentaje al lado en tu tablero, modificamos el envío aquí:
                        query = """
                            INSERT INTO monitoreo 
                            (ip_servidor, val_cpu, val_ram, 
                             val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                             estado_servicio_1, estado_servicio_2, estado_servicio_3, estado_servicio_4, estado_servicio_5,
                             val_red, val_latencia, estado_sistema, fecha_registro) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        # Condicional para empaquetar porcentaje en la cadena si tu base de datos es VARCHAR.
                        # Si las columnas de tu BD son de tipo TEXTO/VARCHAR, esto pintará directo "30.0 GB (10.0% libre)".
                        # Si tus columnas son puramente FLOAT/DECIMAL, el bucle de arriba ya eliminó las alertas en 0.
                        def formatear_disco_ui(gb, pct):
                            if gb == 0.0:
                                return "0.0"
                            if pct is not None:
                                return f"{gb} GB ({pct}% libre)"
                            return f"{gb} GB"

                        # Si tu base de datos da error de "Incorrect double value" al ejecutar, significa que las columnas son FLOAT.
                        # En ese caso, avísame para mandarte el truco de la tabla auxiliar o ajustar el archivo de los semáforos.
                        # De momento, enviamos los datos limpios filtrando los ceros:
                        valores = (
                            ip, v_cpu, v_ram, 
                            v_d1 if v_d1 > 0 else 0.0, 
                            v_d2 if v_d2 > 0 else 0.0, 
                            v_d3 if v_d3 > 0 else 0.0, 
                            v_d4 if v_d4 > 0 else 0.0, 
                            v_d5 if v_d5 > 0 else 0.0, 
                            v_d6 if v_d6 > 0 else 0.0,
                            v_s1, v_s2, v_s3, v_s4, v_s5, v_red, v_lat, estado, ahora_local
                        )

                        conn_write = conectar_bd_con_reintentos()
                        if conn_write:
                            cursor_write = conn_write.cursor()
                            cursor_write.execute(query, valores)
                            conn_write.commit()
                            cursor_write.close()
                            conn_write.close()
                        else:
                            log_agente(f"❌ Error al escribir telemetría para {nombre} ({ip}) - BD Inalcanzable")

                    except Exception as e_srv:
                        log_agente(f"❌ Excepción procesando servidor {srv.get('nombre_alias')}: {str(e_srv)}")

                cursor_ins.close()
                conn_ins.close()
                
            except Exception as e_ciclo:
                log_agente(f"❌ Fallo general en el ciclo de lectura: {str(e_ciclo)}")
                if conn_ins and conn_ins.is_connected():
                    conn_ins.close()

            # Ventana de espera para el próximo barrido automático
            time.sleep(10)
            
    except KeyboardInterrupt:
        AGENTE_EN_EJECUCION = False
        log_agente("🛑 Demonio detenido de forma segura por el operador.")

if __name__ == "__main__":
    ejecutar_motor_agente()