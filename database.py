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

def verificar_usuario(usuario, clave):
    """Valida credenciales y devuelve el ID numérico para las llaves foráneas."""
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

def obtener_datos_historicos():
    """Trae la telemetría usando el nuevo estándar de id_sensor."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY fecha_registro DESC LIMIT 100"
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            return datos
        except Exception as e:
            print(f"Error al traer históricos: {e}")
    return []

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
    """Sincronizado con tabla 'historico_usuarios' de simpol.sql"""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # Columnas exactas de simpol.sql
            query = """
                INSERT INTO historico_usuarios 
                (usuario_id, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (int(ejecutor_id), afectado, accion, str(anterior), str(nuevo), comentario))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error de auditoría (User): {e}")

def registrar_auditoria_umbral(metrica, anterior, nuevo, usuario_id, comentario):
    """Sincronizado con tabla 'historico_umbrales' de simpol.sql"""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # CORRECCIÓN: Nombres de columnas según tu línea 40 de simpol.sql
            query = """
                INSERT INTO historico_umbrales 
                (usuario_id, parametro, valor_anterior, valor_nuevo, justificacion)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (int(usuario_id), str(metrica), str(anterior), str(nuevo), str(comentario)))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error de auditoría (Umbral): {e}")
            
def registrar_proyeccion(recurso, actual, proyectado, fecha_fin, dias, veredicto, usuario_id):
    """Sincronizado con la tabla proyecciones de simpol.sql"""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO proyecciones 
                (usuario_id, recurso_analizado, valor_actual, valor_proyectado, fecha_proyeccion, dias_proyectados, veredicto)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, recurso, actual, proyectado, fecha_fin, dias, veredicto))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al registrar proyección: {e}")
            return False
    return False