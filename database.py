import mysql.connector
import streamlit as st
import sys

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
    except mysql.connector.Error as err:
        # Intento de reconexión por nombre de host local
        try:
            return mysql.connector.connect(
                host="localhost", 
                user="root", 
                password="1234", 
                database="simpol",
                auth_plugin="mysql_native_password",
                use_pure=True
            )
        except Exception:
            return None

# --- CONSULTAS CON CACHÉ (Lectura) ---

@st.cache_data(ttl=5)
def obtener_lista_servidores():
    """Obtiene el catálogo de servidores activos."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, departamento, 
                       id_sensor_cpu, id_sensor_ram, id_sensor_disco, 
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
            print(f"Error al obtener catálogo: {e}")
    return []

@st.cache_data(ttl=5)
def obtener_datos_historicos(ip_objetivo):
    """Trae la telemetría completa filtrada por IP."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema 
                FROM monitoreo 
                WHERE ip_servidor = %s 
                ORDER BY fecha_registro DESC LIMIT 100
            """
            cursor.execute(query, (ip_objetivo,))
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            return datos
        except Exception as e:
            print(f"Error al traer históricos de {ip_objetivo}: {e}")
    return []

# --- FUNCIONES DE ESCRITURA Y SEGURIDAD ---

def verificar_usuario(usuario, clave):
    """Valida credenciales y devuelve el perfil del usuario."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, usuario, nombre_completo, rol FROM usuarios WHERE usuario = %s AND clave = %s AND estado = 1"
            cursor.execute(query, (usuario, clave))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            st.error(f"Error en login: {e}")
    return None

def registrar_proyeccion(usuario_id, ip_servidor, metrica, actual, proyectado, veredicto):
    """Registra el análisis de Capacity Planning."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO proyecciones 
                (usuario_id, ip_servidor, metrica_analizada, valor_actual, valor_proyectado, veredicto)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, ip_servidor, metrica, actual, proyectado, veredicto))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error al registrar proyección: {e}")
    return False

def registrar_log_acceso(usuario, nombre, rol, resultado="EXITOSO"):
    """Registra auditoría de accesos."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO log_accesos (usuario, nombre_completo, rol, resultado) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (usuario, nombre, rol, resultado))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error de log: {e}")

def registrar_auditoria_usuario(afectado, accion, anterior, nuevo, ejecutor_id, comentario):
    """
    Función requerida por gestion.py y usuario.py.
    Asegura que el nombre sea exacto para evitar ImportError en el EXE.
    """
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_usuarios 
                (usuario_id, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (int(ejecutor_id), afectado, accion, str(anterior), str(nuevo), comentario))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error de auditoría: {e}")
    return False