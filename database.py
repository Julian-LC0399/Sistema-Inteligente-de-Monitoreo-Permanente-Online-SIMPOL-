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
            # CORRECCIÓN: Agregado 'id' al SELECT para persistencia de sesión
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
            # CORRECCIÓN: nombre_csu -> id_sensor
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

def registrar_auditoria_usuario(afectado, accion, anterior, nuevo, ejecutor):
    """Guarda cambios en la tabla 'historico_usuarios'."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # Ajustado a los nombres exactos de simpol.sql
            query = """
                INSERT INTO historico_usuarios 
                (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (afectado, accion, str(anterior), str(nuevo), ejecutor))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error de auditoría (User): {e}")

def registrar_auditoria_umbral(metrica, anterior, nuevo, usuario_id, comentario):
    """
    Registra el cambio de umbral en historico_umbrales.
    Sincronizado con simpol.sql (usuario_id, metrica, umbral_anterior, umbral_nuevo, comentario)
    """
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # El orden debe ser igual al VALUES para que el ID numérico entre en la columna correcta
            query = """
                INSERT INTO historico_umbrales 
                (usuario_id, metrica, umbral_anterior, umbral_nuevo, comentario)
                VALUES (%s, %s, %s, %s, %s)
            """
            # Convertimos a tipos de datos compatibles con SQL (INT y STR)
            cursor.execute(query, (int(usuario_id), str(metrica), int(anterior), int(nuevo), str(comentario)))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            # Importante: st.error te ayudará a ver el error en pantalla si algo falla
            st.error(f"Error de auditoría (Umbral): {e}")

def registrar_proyeccion(recurso, actual, proyectado, fecha_fin, dias, veredicto, usuario_id):
    """CORRECCIÓN: Sincronizado con la tabla proyecciones de simpol.sql"""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # CORRECCIÓN: ejecutado_por -> usuario_id (INT) y reordenado según SQL
            query = """
                INSERT INTO proyecciones 
                (usuario_id, recurso_analizado, valor_actual, valor_proyectado, fecha_proyeccion, dias_proyectados, veredicto)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            # Se envía el usuario_id como primer valor
            cursor.execute(query, (usuario_id, recurso, actual, proyectado, fecha_fin, dias, veredicto))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al registrar proyección: {e}")
            return False
    return False