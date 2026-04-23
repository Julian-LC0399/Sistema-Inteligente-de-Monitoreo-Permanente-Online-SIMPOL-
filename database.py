import mysql.connector
import streamlit as st
import sys

def conectar_bd():
    """Establece conexión con parámetros de compatibilidad forzada para el entorno del Banco."""
    try:
        config = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "1234",
            "database": "simpol",
            # Forzamos el uso del plugin nativo para evitar el error 2059
            "auth_plugin": "mysql_native_password",
            # CLAVE: Usa la implementación pura de Python para evitar depender de DLLs externas
            "use_pure": True 
        }
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        # Intento de reconexión automática si falla el host local por resolución de nombre
        if err.errno == 2059 or err.errno == 2003:
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
                st.error(f"Error crítico de conexión (2059): El plugin de autenticación no responde. {err}")
        else:
            st.error(f"Error crítico de conexión: {err}")
        return None

def obtener_lista_servidores():
    """
    Obtiene el catálogo completo de servidores.
    Incluye los IDs de los 5 sensores para que el Agente sepa qué consultar.
    """
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, departamento, 
                       id_sensor_cpu, id_sensor_ram, id_sensor_disco, 
                       id_sensor_red, id_sensor_latencia 
                FROM servidores_it 
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
    """
    Trae la telemetría completa (5 sensores) filtrada por IP.
    """
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