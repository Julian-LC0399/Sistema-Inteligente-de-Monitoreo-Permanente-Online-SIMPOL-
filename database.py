import mysql.connector

def conectar_bd():
    """Establece la conexión con la base de datos usando el plugin compatible."""
    try:
        config = {
            'host': '127.0.0.1',
            'user': 'root',
            'password': '1234',
            'database': 'monitoreo_banco',
            'auth_plugin': 'mysql_native_password'
        }
        conexion = mysql.connector.connect(**config)
        return conexion
    except mysql.connector.Error as err:
        print(f"Error al conectar: {err}")
        return None

def verificar_usuario(usuario, clave):
    """Tu función de login que ya tienes, pero usando conectar_bd()"""
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT usuario, nombre_completo, rol FROM usuarios WHERE usuario = %s AND clave = %s AND estado = 1"
        cursor.execute(query, (usuario, clave))
        resultado = cursor.fetchone()
        cursor.close()
        conexion.close()
        return resultado
    return None