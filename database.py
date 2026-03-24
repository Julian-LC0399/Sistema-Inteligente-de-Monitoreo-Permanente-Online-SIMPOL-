import mysql.connector
import pandas as pd
import streamlit as st


def conectar_bd():
    """Establece la conexión con la base de datos usando el plugin compatible."""
    try:
        config = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "1234",
            "database": "monitoreo_banco",
            "auth_plugin": "mysql_native_password",  # Crucial para evitar errores de autenticación
        }
        conexion = mysql.connector.connect(**config)
        return conexion
    except mysql.connector.Error as err:
        st.error(f"Error crítico de conexión a la base de datos: {err}")
        return None


def verificar_usuario(usuario, clave):
    """Valida credenciales y retorna datos del analista si está activo."""
    conexion = conectar_bd()
    if conexion:
        try:
            cursor = conexion.cursor(dictionary=True)
            # Asegúrate de que la tabla 'usuarios' tenga la columna 'estado'
            query = "SELECT usuario, nombre_completo, rol FROM usuarios WHERE usuario = %s AND clave = %s AND estado = 1"
            cursor.execute(query, (usuario, clave))
            resultado = cursor.fetchone()
            cursor.close()
            conexion.close()
            return resultado
        except mysql.connector.Error as err:
            st.error(f"Error en la consulta de usuario: {err}")
            return None
    return None


def obtener_datos_historicos():
    """Extrae los datos de la tabla monitoreo_nodos para análisis de capacidad y alertas."""
    conexion = conectar_bd()
    if conexion:
        try:
            # Consultamos los datos necesarios para la regresión polinómica en Capacity Planning
            query = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_nodos ORDER BY fecha_registro ASC"

            # Leemos directamente a un DataFrame de Pandas
            df = pd.read_sql(query, conexion)

            conexion.close()
            return df
        except Exception as e:
            st.error(f"Error al extraer datos históricos: {e}")
            if conexion.is_connected():
                conexion.close()
            return pd.DataFrame()
    return pd.DataFrame()
