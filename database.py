import mysql.connector
import streamlit as st

def conectar_bd():
    """Establece conexión con los parámetros del Banco Caroní."""
    try:
        config = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "1234",
            "database": "simpol",
            "auth_plugin": "mysql_native_password", 
        }
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        st.error(f"Error crítico de conexión: {err}")
        return None

def obtener_lista_servidores():
    """Obtiene el catálogo de servidores para los selectores de la interfaz."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Trae solo los activos para el monitoreo
            cursor.execute("SELECT ip, nombre_alias, departamento FROM servidores_it WHERE estado_monitoreo = 1")
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error al obtener catálogo: {e}")
    return []

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

def obtener_datos_historicos(ip_objetivo):
    """Trae la telemetría filtrada por una IP específica."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Filtramos por IP para que los gráficos SVG no mezclen servidores
            query = """
                SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema 
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

def registrar_proyeccion(usuario_id, ip_servidor, metrica, actual, proyectado, veredicto):
    """Registra el análisis de Capacity Planning sincronizado con el nuevo SQL."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # Columnas ajustadas a tu tabla 'proyecciones' final
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
    """Auditoría de cambios en personal."""
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
        except Exception as e:
            print(f"Error de auditoría: {e}")