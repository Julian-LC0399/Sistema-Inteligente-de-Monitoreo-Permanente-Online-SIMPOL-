import mysql.connector
import streamlit as st

def conectar_bd():
    """Establece conexión con los parámetros del Banco Caroní."""
    try:
        config = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "1234",
            "database": "monitoreo_banco",
            # Plugin forzado para evitar el error 4058 en Windows Server
            "auth_plugin": "mysql_native_password", 
        }
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        st.error(f"Error crítico de conexión: {err}")
        return None

def verificar_usuario(usuario, clave):
    """Valida credenciales y el nuevo rol de seguridad."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Buscamos en la tabla 'usuarios' con el nuevo esquema
            query = "SELECT usuario, nombre_completo, rol FROM usuarios WHERE usuario = %s AND clave = %s AND estado = 1"
            cursor.execute(query, (usuario, clave))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            st.error(f"Error en login: {e}")
    return None

def obtener_datos_historicos():
    """
    Extrae datos usando cursores nativos.
    Ya no usa Pandas (pd.read_sql) para evitar errores de DLL en el servidor.
    """
    conn = conectar_bd()
    datos = []
    if conn:
        try:
            # dictionary=True hace que cada fila sea un diccionario {'columna': valor}
            cursor = conn.cursor(dictionary=True)
            query = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo ORDER BY fecha_registro ASC"
            cursor.execute(query)
            datos = cursor.fetchall()  # Retorna una lista de diccionarios
            cursor.close()
            conn.close()
            return datos 
        except Exception as e:
            st.error(f"Error al extraer telemetría: {e}")
    
    # Si falla o no hay datos, devuelve una lista vacía compatible con bucles
    return datos

# --- FUNCIONES DE AUDITORÍA (Mantenidas como código nativo seguro) ---

def registrar_auditoria_usuario(afectado, accion, anterior, nuevo, ejecutor):
    """Guarda cambios de personal en 'historico_usuarios'."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
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

def registrar_auditoria_umbral(metrica, anterior, nuevo, ejecutor):
    """Guarda cambios de alertas en 'historico_umbrales'."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_umbrales 
                (metrica, umbral_anterior, umbral_nuevo, modificado_por)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (metrica, str(anterior), str(nuevo), ejecutor))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error de auditoría (Umbral): {e}")


def registrar_proyeccion(recurso, actual, proyectado, fecha_fin, dias, veredicto, ejecutor):
    """Guarda el análisis de Capacity Planning en la tabla 'proyecciones'."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO proyecciones 
                (recurso_analizado, valor_actual, valor_proyectado, fecha_proyeccion, dias_proyectados, veredicto, ejecutado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (recurso, actual, proyectado, fecha_fin, dias, veredicto, ejecutor))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error al guardar proyección: {e}")
    return False