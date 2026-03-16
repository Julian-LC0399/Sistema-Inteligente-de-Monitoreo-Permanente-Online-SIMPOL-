import mysql.connector

def conectar_bd():
    # Usamos el plugin de autenticación moderno compatible con MySQL 8+
    # Esto requiere que tengas instalada la librería 'cryptography' en el banco
    return mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="1234", 
        database="monitoreo_banco",
        auth_plugin='caching_sha2_password'
    )

def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        # BINARY asegura que la comparación sea exacta (distingue mayúsculas/minúsculas)
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except mysql.connector.Error as err:
        # Si falla por autenticación, mostramos un mensaje descriptivo en consola
        print(f"Error de base de datos: {err}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None