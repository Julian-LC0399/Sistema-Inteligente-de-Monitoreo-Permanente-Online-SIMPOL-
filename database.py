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

# --- CONSULTAS CON CACHÉ (Lectura e Historial Pura Nativa en GB) ---

@st.cache_data(ttl=5)
def obtener_lista_servidores():
    """
    Obtiene el catálogo de servidores activos adaptado estructuralmente a 5 sensores de disco.
    SOLUCIÓN ARQUITECTÓNICA: Agrega las columnas letra_disco_X para desacoplar las vistas de Streamlit.
    """
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, sistema_operativo, 
                       id_sensor_cpu, id_sensor_ram, 
                       id_sensor_disco_1, letra_disco_1,
                       id_sensor_disco_2, letra_disco_2, 
                       id_sensor_disco_3, letra_disco_3, 
                       id_sensor_disco_4, letra_disco_4, 
                       id_sensor_disco_5, letra_disco_5, 
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
            print(f"Error al obtener catálogo multidisco (5 Volúmenes): {e}")
    return []

@st.cache_data(ttl=5)
def obtener_datos_historicos(ip_objetivo):
    """
    Trae la telemetría completa filtrada por IP mapeando los 5 volúmenes de almacenamiento.
    Los valores de val_ram y val_disco_X vienen expresados directamente en GB reales desde la BD V3.2.
    """
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, val_cpu, val_ram, 
                       val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, 
                       val_red, val_latencia, estado_sistema 
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
            print(f"Error al traer históricos multidisco de {ip_objetivo}: {e}")
    return []

# --- CONSULTA DE CONFIGURACIÓN Y AUDITORÍA DE UMBRALES (Límites Quirúrgicos en GB Libres V3.2) ---

def obtener_umbrales_actuales(ip):
    """
    Consulta la matriz de límites activos (Advertencia y Crítico) para una IP específica.
    Mapea de manera quirúrgica los 5 volúmenes de almacenamiento y la RAM expresados en GB Libres.
    Retorna los valores de contingencia institucional (en GB) si no hay registros previos.
    """
    umbrales = {
        "cpu_advertencia": 70, "cpu_critico": 85,           # CPU en %
        "ram_advertencia": 8, "ram_critico": 4,             # RAM en GB Libres mínimos
        "disco_1_advertencia": 20, "disco_1_critico": 10,   # Discos en GB Libres mínimos
        "disco_2_advertencia": 40, "disco_2_critico": 15,
        "disco_3_advertencia": 40, "disco_3_critico": 15,
        "disco_4_advertencia": 40, "disco_4_critico": 15,
        "disco_5_advertencia": 40, "disco_5_critico": 15
    }
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT cpu_advertencia, cpu_critico, 
                       ram_advertencia, ram_critico, 
                       disco_1_advertencia, disco_1_critico,
                       disco_2_advertencia, disco_2_critico,
                       disco_3_advertencia, disco_3_critico,
                       disco_4_advertencia, disco_4_critico,
                       disco_5_advertencia, disco_5_critico
                FROM historico_umbrales 
                WHERE ip_servidor = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            res = cursor.fetchone()
            if res:
                umbrales = res
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error al obtener matriz de umbrales multidisco para {ip}: {e}")
    return umbrales

# --- CARGAR MATRIZ DE PERMISOS (Soporte M:N Corregido en Español) ---

def obtener_permisos_usuario(usuario_id):
    """
    Consulta la matriz Muchos a Muchos (M:N) utilizando estrictamente la columna 'permiso_id'
    y retorna la lista plana de códigos autorizados para la interfaz de SIMPOL.
    """
    permisos = []
    conn = conectar_bd()
    if conn:
        try:
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
            print(f"Error al cargar permisos del usuario {usuario_id}: {e}")
    return permisos

# --- CONTROL DE ACCESOS ---

def verificar_usuario(usuario, clave):
    """Valida credenciales y devuelve el registro del usuario (Asegurando el ID)."""
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

# --- FUNCIONES DE ESCRITURA, CAPACIDAD Y AUDITORÍA ---

def registrar_proyeccion(usuario_id, ip_servidor, metrica, actual, proyectado, veredicto):
    """
    Registra análisis de Capacity Planning (Análisis basados en GB).
    """
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

def registrar_log_acceso(usuario, nombre, rol, resultado="EXITOSO", usuario_id=None):
    """Registra auditoría de accesos mapeando el ID de la cuenta (Integridad Bancaria)."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO log_accesos (usuario_id, usuario, nombre_completo, rol, resultado) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, usuario, nombre, rol, resultado))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error de log: {e}")

def registrar_auditoria_usuario(afectado, accion, anterior, nuevo, ejecutor_id, comentario):
    """Registra cambios sobre cuentas de usuario."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_usuarios 
                (usuario_id, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (int(ejecutor_id), afectado, accion, anterior, nuevo, comentario))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error de auditoría: {e}")
    return False