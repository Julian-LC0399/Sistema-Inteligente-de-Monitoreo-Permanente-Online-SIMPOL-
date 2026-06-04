import mysql.connector
import streamlit as st
import logging

# Configuración básica de logs internos de base de datos
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURACIÓN DE CONEXIÓN (Optimizado para el Banco) ---
def conectar_bd():
    """Establece conexión con parámetros de compatibilidad forzada para evitar error 2059."""
    try:
        config = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "1234",
            "database": "simpol",
            "auth_plugin": "mysql_native_password",
            "use_pure": True,
            "connect_timeout": 5 
        }
        return mysql.connector.connect(**config)
    except mysql.connector.Error:
        # Intento de reconexión por nombre de host local alternativo
        try:
            return mysql.connector.connect(
                host="localhost", 
                user="root", 
                password="1234", 
                database="simpol",
                auth_plugin="mysql_native_password",
                use_pure=True,
                connect_timeout=5
            )
        except Exception:
            return None

# --- CONSULTAS CON CACHÉ (Lectura e Historial Pura Nativa en GB) ---

@st.cache_data(ttl=3) # Sincronizado con el Fragment de telemetría de monitoreo.py
def obtener_lista_servidores():
    """
    Obtiene el catálogo de servidores activos adaptado estructuralmente a 6 sensores de disco y 8 de servicios.
    """
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, sistema_operativo, 
                       id_sensor_cpu, id_sensor_ram, 
                       id_sensor_disco_1, letra_disco_1,
                       id_sensor_disco_2, letra_disco_2, 
                       id_sensor_disco_3, letra_disco_3, 
                       id_sensor_disco_4, letra_disco_4, 
                       id_sensor_disco_5, letra_disco_5, 
                       id_sensor_disco_6, letra_disco_6,
                       id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, 
                       id_sensor_servicio_4, id_sensor_servicio_5, id_sensor_servicio_6,
                       id_sensor_servicio_7, id_sensor_servicio_8,
                       id_sensor_red, id_sensor_latencia 
                FROM servidores 
                WHERE estado_monitoreo = 1
            """
            cursor.execute(query)
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            logging.error(f"Error al obtener catálogo multidisco y multiservicios: {e}")
            if conn: conn.close()
    return []

@st.cache_data(ttl=2) # Evita el solapamiento de ejecuciones del fragment
def obtener_datos_historicos(ip_objetivo):
    """
    Trae la telemetría completa filtrada por IP mapeando los 6 volúmenes y los 8 servicios activos.
    """
    if not ip_objetivo:
        return []
        
    ip_limpia = str(ip_objetivo).strip()
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT fecha_registro, val_cpu, val_ram, 
                       val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                       estado_servicio_1, estado_servicio_2, estado_servicio_3, 
                       estado_servicio_4, estado_servicio_5, estado_servicio_6,
                       estado_servicio_7, estado_servicio_8,
                       val_red, val_latencia, estado_sistema 
                FROM monitoreo 
                WHERE TRIM(ip_servidor) = %s 
                ORDER BY fecha_registro DESC LIMIT 50
            """
            cursor.execute(query, (ip_limpia,))
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            return datos
        except Exception as e:
            logging.error(f"Error al traer históricos multidisco y multiservicios de {ip_limpia}: {e}")
            if conn: conn.close()
    return []

# --- CONSULTA DE CONFIGURACIÓN Y AUDITORÍA DE UMBRALES ---

def obtener_umbrales_actuales(ip):
    """
    Consulta la matriz de límites activos para 6 discos y los parámetros de salud del sistema.
    """
    umbrales = {
        "cpu_buen_estado": 69, "cpu_advertencia": 70, "cpu_critico": 85,
        "ram_buen_estado": 12, "ram_advertencia": 8, "ram_critico": 4
    }
    # Inicializar umbrales de 6 discos
    for i in range(1, 7):
        umbrales.update({f"disco_{i}_buen_estado": 60, f"disco_{i}_advertencia": 40, f"disco_{i}_critico": 15})
    
    if not ip: return umbrales
        
    ip_limpia = str(ip).strip()
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM historico_umbrales 
                WHERE TRIM(ip_servidor) = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip_limpia,))
            res = cursor.fetchone()
            if res: umbrales = res
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error al obtener matriz de umbrales para {ip_limpia}: {e}")
            if conn: conn.close()
    return umbrales

# --- CARGAR MATRIZ DE PERMISOS ---

def obtener_permisos_usuario(usuario_id):
    permisos = []
    if not usuario_id: return permisos
        
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor()
            query = """
                SELECT p.codigo_permiso 
                FROM permisos p
                INNER JOIN permisos_usuarios pu ON p.id = pu.permiso_id
                WHERE pu.usuario_id = %s
            """
            cursor.execute(query, (usuario_id,))
            resultados = cursor.fetchall()
            permisos = [row[0] for row in resultados]
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error al cargar permisos del usuario {usuario_id}: {e}")
            if conn: conn.close()
    return permisos

# --- CONTROL DE ACCESOS ---

def verificar_usuario(usuario, clave):
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, usuario, cargo, rol FROM usuarios WHERE usuario = %s AND clave = %s AND estado = 1"
            cursor.execute(query, (usuario, clave))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            logging.error(f"Error en login: {e}")
            if conn: conn.close()
    return None

# --- FUNCIONES DE ESCRITURA, CAPACIDAD Y AUDITORÍA ---

def registrar_proyeccion(usuario_id, ip_servidor, metrica, actual, proyectado, veredicto):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO proyecciones 
                (usuario_id, ip_servidor, metrica_analizada, valor_actual, valor_proyectado, veredicto)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, str(ip_servidor).strip(), metrica, actual, proyectado, veredicto))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error al registrar proyección: {e}")
            if conn: conn.close()
    return False

def registrar_log_acceso(usuario, cargo, rol, resultado="EXITOSO", usuario_id=None):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO log_accesos (usuario_id, usuario, cargo, rol, resultado) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, usuario, cargo, rol, resultado))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error de log: {e}")
            if conn: conn.close()

def registrar_auditoria_usuario(afectado, accion, anterior, nuevo, ejecutor_id, comentario):
    conn = conectar_bd()
    if conn:
        try:
            id_limpio = int(ejecutor_id) if ejecutor_id is not None else None
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_usuarios 
                (usuario_id, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (id_limpio, afectado, accion, anterior, nuevo, comentario))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error de auditoría: {e}")
            if conn: conn.close()
    return False