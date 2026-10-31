import mysql.connector
import streamlit as st
import logging
from datetime import datetime
from security import procesar_login, cambiar_clave, hashear_clave, verificar_clave

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def conectar_bd():
    """Establece conexión con parámetros de compatibilidad forzada para evitar error 2059."""
    config = {
        "host": "127.0.0.1",
        "user": "root",
        "password": "1234",
        "database": "simpol",
        "auth_plugin": "mysql_native_password",
        "use_pure": True,
        "connect_timeout": 5 
    }
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error:
        try:
            config["host"] = "localhost"
            return mysql.connector.connect(**config)
        except Exception:
            return None

# =========================================================================
# 🔧 REPARACIÓN AUTOMÁTICA DE CLAVES INVÁLIDAS (CORREGIDO)
# =========================================================================
def reparar_claves_iniciales():
    """
    Verifica que las claves de los usuarios iniciales sean hashes bcrypt válidos.
    Si el hash está corrupto (no es bcrypt), lo repara con '1234'.
    ¡NUNCA sobreescribe si el hash ya es un bcrypt válido (aunque no sea 1234)!
    """
    conn = conectar_bd()
    if not conn:
        logging.warning("reparar_claves_iniciales: sin conexión a la BD, se omite")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, usuario, clave
            FROM usuarios
            WHERE usuario IN ('seguridad_csu', 'admin_csu', 'operador')
        """)
        usuarios = cursor.fetchall()

        if not usuarios:
            cursor.close()
            conn.close()
            return

        hash_real_1234 = None
        reparados = 0

        for u in usuarios:
            clave_actual = u["clave"] or ""
            es_valido = False

            # ¿Tiene formato de hash bcrypt?
            if clave_actual.startswith("$2b$") or clave_actual.startswith("$2a$"):
                try:
                    # Probamos que bcrypt pueda procesarlo sin excepción
                    verificar_clave("dummy", clave_actual)
                    es_valido = True
                except Exception:
                    es_valido = False

            # SOLO si el hash está corrupto, lo reparamos a 1234
            if not es_valido:
                if hash_real_1234 is None:
                    hash_real_1234 = hashear_clave("1234")
                    logging.info(f"🔧 Hash real de '1234' generado: {hash_real_1234[:35]}...")

                cursor.execute("""
                    UPDATE usuarios
                    SET clave = %s,
                        intentos_fallidos = 0,
                        bloqueado_hasta = NULL,
                        debe_cambiar_clave = 1,
                        estado = 1
                    WHERE id = %s
                """, (hash_real_1234, u["id"]))
                reparados += 1
                logging.warning(f"🔧 Clave reparada (estaba corrupta) para el usuario: {u['usuario']}")

        if reparados > 0:
            conn.commit()
            logging.info(f"✅ {reparados} clave(s) reparada(s) automáticamente. Prueba login con '1234'.")
        else:
            logging.info("✅ Todas las claves iniciales son válidas, nada que reparar.")

        cursor.close()
        conn.close()

    except Exception as e:
        logging.error(f"Error en reparar_claves_iniciales: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# Ejecución automática al importar el módulo
try:
    reparar_claves_iniciales()
except Exception as e:
    logging.error(f"No se pudo ejecutar reparar_claves_iniciales al importar: {e}")


# =========================================================================
# NUEVAS FUNCIONES DE SEGURIDAD (WRAPPERS)
# =========================================================================
def autenticar_usuario(usuario, clave, ip_cliente='127.0.0.1'):
    """Wrapper para el login usando security.py. Maneja la conexión y el commit."""
    conn = conectar_bd()
    if not conn:
        return {"exito": False, "mensaje": "Error de conexión a la base de datos."}
    try:
        cursor = conn.cursor(dictionary=True)
        resultado = procesar_login(cursor, usuario, clave, ip_cliente)
        conn.commit()
        cursor.close()
        conn.close()
        return resultado
    except Exception as e:
        logging.error(f"Error crítico en autenticación: {e}")
        if conn: conn.close()
        return {"exito": False, "mensaje": "Error interno del servidor."}

def actualizar_clave_usuario(usuario_id, clave_actual, clave_nueva, es_admin=False, admin_id=None):
    """Wrapper para cambiar la contraseña usando security.py."""
    conn = conectar_bd()
    if not conn:
        return {"exito": False, "mensaje": "Error de conexión a la base de datos."}
    try:
        cursor = conn.cursor(dictionary=True)
        resultado = cambiar_clave(cursor, usuario_id, clave_actual, clave_nueva, es_admin, admin_id)
        conn.commit()
        cursor.close()
        conn.close()
        return resultado
    except Exception as e:
        logging.error(f"Error crítico al cambiar contraseña: {e}")
        if conn: conn.close()
        return {"exito": False, "mensaje": "Error interno del servidor."}

# =========================================================================
# FUNCIONES EXISTENTES
# =========================================================================
@st.cache_data(ttl=3)
def obtener_lista_servidores():
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, sistema_operativo, tipo,
                       id_sensor_cpu, id_sensor_ram, 
                       id_sensor_disco_1, letra_disco_1,
                       id_sensor_disco_2, letra_disco_2, 
                       id_sensor_disco_3, letra_disco_3, 
                       id_sensor_disco_4, letra_disco_4, 
                       id_sensor_disco_5, letra_disco_5, 
                       id_sensor_disco_6, letra_disco_6,
                       id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, 
                       id_sensor_servicio_4, id_sensor_servicio_5, id_sensor_servicio_6,
                       id_sensor_servicio_7, id_sensor_servicio_8,
                       id_sensor_red_total, id_sensor_red_entrante, id_sensor_red_saliente, 
                       id_sensor_latencia 
                FROM servidores 
                WHERE estado_monitoreo = 1
            """
            cursor.execute(query)
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            logging.error(f"Error al obtener catálogo multidisco: {e}")
            if conn: conn.close()
    return []

@st.cache_data(ttl=2)
def obtener_datos_historicos(ip_objetivo):
    if not ip_objetivo:
        return []
    ip_limpia = str(ip_objetivo).strip()
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, val_cpu, 
                       val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8,
                       val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb,
                       val_disco_1_total_gb, val_disco_1_pct_libre, val_disco_1_libres_gb,
                       val_disco_2_total_gb, val_disco_2_pct_libre, val_disco_2_libres_gb,
                       val_disco_3_total_gb, val_disco_3_pct_libre, val_disco_3_libres_gb,
                       val_disco_4_total_gb, val_disco_4_pct_libre, val_disco_4_libres_gb,
                       val_disco_5_total_gb, val_disco_5_pct_libre, val_disco_5_libres_gb,
                       val_disco_6_total_gb, val_disco_6_pct_libre, val_disco_6_libres_gb,
                       estado_servicio_1, val_servicio_1, estado_servicio_2, val_servicio_2,
                       estado_servicio_3, val_servicio_3, estado_servicio_4, val_servicio_4,
                       estado_servicio_5, val_servicio_5, estado_servicio_6, val_servicio_6,
                       estado_servicio_7, val_servicio_7, estado_servicio_8, val_servicio_8,
                       val_red_total, val_red_entrante, val_red_saliente,
                       val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida, 
                       estado_sistema 
                FROM monitoreo 
                WHERE TRIM(ip_servidor) = %s 
                ORDER BY fecha_registro DESC LIMIT 50
            """
            cursor.execute(query, (ip_limpia,))
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            return datos
        except Exception as e:
            logging.error(f"Error al traer históricos estructurados de {ip_limpia}: {e}")
            if conn: conn.close()
    return []

def guardar_telemetria_servidor(ip_servidor, data):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO monitoreo (
                ip_servidor, val_cpu, 
                val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8,
                val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb,
                val_disco_1_total_gb, val_disco_1_pct_libre, val_disco_1_libres_gb,
                val_disco_2_total_gb, val_disco_2_pct_libre, val_disco_2_libres_gb,
                val_disco_3_total_gb, val_disco_3_pct_libre, val_disco_3_libres_gb,
                val_disco_4_total_gb, val_disco_4_pct_libre, val_disco_4_libres_gb,
                val_disco_5_total_gb, val_disco_5_pct_libre, val_disco_5_libres_gb,
                val_disco_6_total_gb, val_disco_6_pct_libre, val_disco_6_libres_gb,
                estado_servicio_1, val_servicio_1, estado_servicio_2, val_servicio_2,
                estado_servicio_3, val_servicio_3, estado_servicio_4, val_servicio_4,
                estado_servicio_5, val_servicio_5, estado_servicio_6, val_servicio_6,
                estado_servicio_7, val_servicio_7, estado_servicio_8, val_servicio_8,
                val_red_total, val_red_entrante, val_red_saliente,
                val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida,
                estado_sistema
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        valores = (
            str(ip_servidor).strip(), data.get("cpu", 0.0),
            data.get("cpu_p1", 0.0), data.get("cpu_p2", 0.0), data.get("cpu_p3", 0.0), data.get("cpu_p4", 0.0),
            data.get("cpu_p5", 0.0), data.get("cpu_p6", 0.0), data.get("cpu_p7", 0.0), data.get("cpu_p8", 0.0),
            data.get("ram_total_gb", 0.0), data.get("ram_pct", 0.0), data.get("ram_gb", 0.0),
            data.get("disco_1_total_gb", 0.0), data.get("disco_1_pct", 0.0), data.get("disco_1_gb", 0.0),
            data.get("disco_2_total_gb", 0.0), data.get("disco_2_pct", 0.0), data.get("disco_2_gb", 0.0),
            data.get("disco_3_total_gb", 0.0), data.get("disco_3_pct", 0.0), data.get("disco_3_gb", 0.0),
            data.get("disco_4_total_gb", 0.0), data.get("disco_4_pct", 0.0), data.get("disco_4_gb", 0.0),
            data.get("disco_5_total_gb", 0.0), data.get("disco_5_pct", 0.0), data.get("disco_5_gb", 0.0),
            data.get("disco_6_total_gb", 0.0), data.get("disco_6_pct", 0.0), data.get("disco_6_gb", 0.0),
            data.get("estado_servicio_1", "INACTIVO"), data.get("val_servicio_1", 0.0),
            data.get("estado_servicio_2", "INACTIVO"), data.get("val_servicio_2", 0.0),
            data.get("estado_servicio_3", "INACTIVO"), data.get("val_servicio_3", 0.0),
            data.get("estado_servicio_4", "INACTIVO"), data.get("val_servicio_4", 0.0),
            data.get("estado_servicio_5", "INACTIVO"), data.get("val_servicio_5", 0.0),
            data.get("estado_servicio_6", "INACTIVO"), data.get("val_servicio_6", 0.0),
            data.get("estado_servicio_7", "INACTIVO"), data.get("val_servicio_7", 0.0),
            data.get("estado_servicio_8", "INACTIVO"), data.get("val_servicio_8", 0.0),
            data.get("red_total", 0.0), data.get("red_entrante", 0.0), data.get("red_saliente", 0.0),
            data.get("latencia_ping", 0.0), data.get("latencia_max", 0.0), data.get("latencia_min", 0.0), data.get("latencia_perdida", 0.0),
            data.get("estado_sistema", "3")
        )
        cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error al insertar telemetría para el servidor {ip_servidor}: {e}")
        if conn: conn.close()
        return False

def obtener_umbrales_actuales(ip):
    umbrales = {
        "cpu_buen_estado": 69, "cpu_advertencia": 70, "cpu_critico": 85,
        "cpu_p_buen_estado": 69, "cpu_p_advertencia": 70, "cpu_p_critico": 85,
        "ram_buen_estado": 20, "ram_advertencia": 15, "ram_critico": 10,
        "red_limite_total_mbps": 100, "red_limite_entrante_mbps": 50, "red_limite_saliente_mbps": 50,
        "latencia_limite_ms": 150, "perdida_limite_pct": 1
    }
    for i in range(1, 7):
        umbrales.update({f"disco_{i}_buen_estado": 25, f"disco_{i}_advertencia": 15, f"disco_{i}_critico": 5})
    if not ip: return umbrales
    ip_limpia = str(ip).strip()
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM historico_umbrales WHERE TRIM(ip_servidor) = %s ORDER BY id_historico DESC LIMIT 1"
            cursor.execute(query, (ip_limpia,))
            res = cursor.fetchone()
            if res: umbrales = res
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error al obtener matriz de umbrales para {ip_limpia}: {e}")
            if conn: conn.close()
    return umbrales

def obtener_permisos_usuario(usuario_id):
    permisos = []
    if not usuario_id: return permisos
    conn = conectar_bd()
    if conn:
        try:
            conn.commit()
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
            logging.error(f"Error al cargar permisos del usuario {usuario_id}: {e}")
            if conn: conn.close()
    return permisos

def registrar_proyeccion(usuario_id, ip_servidor, metrica, act_total, act_gb, act_pct, pro_total, pro_gb, pro_pct, veredicto, act_red=0.0, pro_red=0.0):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO proyecciones 
                (usuario_id, ip_servidor, metrica_analizada, 
                 val_total_gb, val_actual_disponible_gb, val_actual_disponible_pct, val_actual_red_mbps,
                 val_proyectado_total_gb, val_proyectado_disponible_gb, val_proyectado_disponible_pct, val_proyectado_red_mbps, veredicto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, str(ip_servidor).strip(), metrica, act_total, act_gb, act_pct, act_red, pro_total, pro_gb, pro_pct, pro_red, veredicto))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error al registrar proyección: {e}")
            if conn: conn.close()
    return False

@st.cache_data(ttl=5)
def obtener_reporte_alertas(estado=None, ip=None):
    conn = conectar_bd()
    resultado = []
    if conn:
        try:
            conn.commit()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, ip_servidor, componente, tipo_alerta, 
                       val_total_gb_momento, val_disponible_gb_momento, val_disponible_pct_momento, 
                       val_red_mbps_momento, val_latencia_ms_momento, val_perdida_pct_momento,
                       estado_servicio_momento, fecha_inicio, fecha_fin, estado_alerta 
                FROM alertas WHERE 1=1
            """
            parametros = []
            if estado:
                query += " AND estado_alerta = %s"
                parametros.append(estado)
            if ip:
                query += " AND ip_servidor = %s"
                parametros.append(str(ip).strip())
                
            query += " ORDER BY fecha_inicio DESC"
            cursor.execute(query, tuple(parametros))
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error al extraer logs del reporte de alertas: {e}")
            if conn: conn.close()
    return resultado

def gestionar_estado_alerta(ip_servidor, componente, tipo_alerta, val_total, val_disp_gb, val_disp_pct, est_srv=None, comentario=None, val_red_mbps=0.0, val_latencia_ms=0.0, val_perdida_pct=0.0):
    ip_limpia = str(ip_servidor).strip()
    conn = conectar_bd()
    if not conn: return False
    try:
        cursor = conn.cursor(dictionary=True)
        query_buscar = "SELECT id, tipo_alerta FROM alertas WHERE ip_servidor = %s AND componente = %s AND estado_alerta = 'ACTIVA' LIMIT 1"
        cursor.execute(query_buscar, (ip_limpia, componente))
        alerta_activa = cursor.fetchone()
        
        if tipo_alerta == 'ESTABLE':
            if alerta_activa:
                query_cerrar = "UPDATE alertas SET fecha_fin = NOW(3), estado_alerta = 'RESUELTA', comentario = %s WHERE id = %s"
                cursor.execute(query_cerrar, (comentario or "El componente retorno a niveles operativos normales.", alerta_activa['id']))
            
            query_estable = """
                INSERT INTO alertas (ip_servidor, componente, tipo_alerta, val_total_gb_momento, val_disponible_gb_momento, val_disponible_pct_momento, val_red_mbps_momento, val_latencia_ms_momento, val_perdida_pct_momento, estado_servicio_momento, fecha_fin, estado_alerta, comentario)
                VALUES (%s, %s, 'ESTABLE', %s, %s, %s, %s, %s, %s, %s, NOW(3), 'RESUELTA', 'Estado estable monitoreado.')
            """
            cursor.execute(query_estable, (ip_limpia, componente, val_total, val_disp_gb, val_disp_pct, val_red_mbps, val_latencia_ms, val_perdida_pct, est_srv))
        else:
            if alerta_activa:
                if alerta_activa['tipo_alerta'] != tipo_alerta:
                    query_cerrar_mutacion = "UPDATE alertas SET fecha_fin = NOW(3), estado_alerta = 'RESUELTA', comentario = %s WHERE id = %s"
                    cursor.execute(query_cerrar_mutacion, (f"Transicion de estado operacional hacia {tipo_alerta}.", alerta_activa['id']))
                else:
                    cursor.close()
                    conn.close()
                    return True
            
            query_insertar = """
                INSERT INTO alertas (ip_servidor, componente, tipo_alerta, val_total_gb_momento, val_disponible_gb_momento, val_disponible_pct_momento, val_red_mbps_momento, val_latencia_ms_momento, val_perdida_pct_momento, estado_servicio_momento, estado_alerta, comentario)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVA', %s)
            """
            cursor.execute(query_insertar, (ip_limpia, componente, tipo_alerta, val_total, val_disp_gb, val_disp_pct, val_red_mbps, val_latencia_ms, val_perdida_pct, est_srv, comentario))
            
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error critico gestionando alertas: {e}")
        if conn: conn.close()
        return False

def registrar_reporte_archivado(nombre_archivo, formato, ip_servidor, contenido_blob, usuario_id, alerta_id, tipo_alerta, tamanio_kb, snap_tot=0, snap_disp=0, snap_pct=0, snap_red_tot=0.0, snap_red_ent=0.0, snap_red_sal=0.0, snap_lat=0.0, snap_per=0.0, snap_srv=None):
    conn = conectar_bd()
    if not conn: return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO reportes_archivados 
            (nombre_archivo, format, ip_servidor, contenido, usuario_id, alerta_id, tipo_alerta, tamanio_kb, 
             snapshot_total_gb, snapshot_disponible_gb, snapshot_disponible_pct, 
             snapshot_red_total_mbps, snapshot_red_entrante_mbps, snapshot_red_saliente_mbps,
             snapshot_latencia_ms, snapshot_perdida_pct, snapshot_servicio_estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (nombre_archivo, formato, str(ip_servidor).strip() if ip_servidor else None, contenido_blob, 
                   int(usuario_id) if usuario_id is not None else None, int(alerta_id) if alerta_id is not None else None, 
                   tipo_alerta, tamanio_kb, snap_tot, snap_disp, snap_pct, 
                   snap_red_tot, snap_red_ent, snap_red_sal, snap_lat, snap_per, snap_srv)
        cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error crítico al archivar reporte: {e}")
        if conn: conn.close()
        return False

def registrar_reporte_capacity_archivado(nombre_archivo, formato, metrica, ip_servidor, contenido_blob, usuario_id, alerta_id, tipo_alerta, tamanio_kb, act_tot=0, act_disp=0, pro_disp=0, act_red=0.0, pro_red=0.0):
    conn = conectar_bd()
    if not conn: return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO reportes_capacity_archivados 
            (nombre_archivo, formato, metrica_analizada, ip_servidor, contenido, usuario_id, alerta_id, tipo_alerta, tamanio_kb, 
             analisis_total_gb, analisis_bytes_actuales, analisis_bytes_proyectados, analisis_red_mbps_actual, analisis_red_mbps_proyectado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (nombre_archivo, formato, metrica, str(ip_servidor).strip(), contenido_blob, 
                   int(usuario_id) if usuario_id is not None else None, int(alerta_id) if alerta_id is not None else None, 
                   tipo_alerta, tamanio_kb, act_tot, act_disp, pro_disp, act_red, pro_red)
        cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error crítico al archivar reporte de Capacity: {e}")
        if conn: conn.close()
        return False