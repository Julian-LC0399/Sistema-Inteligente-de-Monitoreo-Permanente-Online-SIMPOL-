import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import io

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF (ESTILO BANCO CARONÍ)
# =====================================================================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Corporativo #003366
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte de Servidor (Análisis de Métricas Integrado)", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE CONSULTA A BASE DE DATOS (SOLO LECTURA / READ-ONLY)
# =====================================================================
def obtener_historial_reportes():
    conn = None
    resultado = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT r.id, r.nombre_archivo, r.format as formato, r.tamanio_kb, r.fecha_generacion, 
                       COALESCE(u.usuario, 'Sistema') as registrado_por 
                FROM reportes_archivados r
                LEFT JOIN usuarios u ON r.usuario_id = u.id
                ORDER BY r.id DESC LIMIT 25
            """
            cursor.execute(query)
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error leyendo historial de reportes: {e}\n")
    return resultado

def descargar_contenido_blob(reporte_id):
    conn = None
    blob_data = b""
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_archivados WHERE id = %s"
            cursor.execute(query, (int(reporte_id),))
            fila = cursor.fetchone()
            if fila and fila["contenido"]:
                blob_data = bytes(fila["contenido"])
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error descargar BLOB ID {reporte_id}: {e}\n")
    return blob_data

# =====================================================================
# VISTA PRINCIPAL DEL MÓDULO (ESTRUCTURADA EN PESTAÑAS NATIVAS)
# =====================================================================
def mostrar_pantalla(nombre_analista, usuario_id, usuario_login="admin"):
    if "rep_listo" not in st.session_state:
        st.session_state["rep_listo"] = False
        st.session_state["rep_csv"] = None
        st.session_state["rep_pdf"] = None
        st.session_state["rep_name_csv"] = ""
        st.session_state["rep_name_pdf"] = ""
    
    if "servidor_seleccionado_reporte" not in st.session_state:
        st.session_state["servidor_seleccionado_reporte"] = "-- Seleccione un Servidor --"
        
    if "key_semilla_selectbox" not in st.session_state:
        st.session_state["key_semilla_selectbox"] = 0

    st.markdown('<h2 style="color:#003366;">📋 Centro de Reportes Gerenciales</h2>', unsafe_allow_html=True)
    st.markdown(f"👤 **Analista de Infraestructura:** {nombre_analista} (`{usuario_login}`)", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab_generar, tab_historial = st.tabs(["📊 Generar Reportes Operativos", "📜 Bóveda Digital de Reportes"])

    # =====================================================================
    # PESTAÑA 1: GENERACIÓN DE REPORTES EN CALIENTE
    # =====================================================================
    with tab_generar:
        conn = conectar_bd()
        if not conn:
            st.error("❌ Error de comunicación con la base de datos central.")
            return

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ip, nombre_alias, sistema_operativo,
                   id_sensor_disco_1, letra_disco_1, id_sensor_disco_2, letra_disco_2,
                   id_sensor_disco_3, letra_disco_3, id_sensor_disco_4, letra_disco_4,
                   id_sensor_disco_5, letra_disco_5, id_sensor_disco_6, letra_disco_6,
                   id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4,
                   id_sensor_servicio_5, id_sensor_servicio_6, id_sensor_servicio_7, id_sensor_servicio_8
            FROM servidores WHERE estado_monitoreo = 1 ORDER BY nombre_alias ASC
        """)
        servidores = cursor.fetchall()
        cursor.close()
        conn.close()

        if not servidores:
            st.warning("⚠️ No se registran nodos de servidores activos en la configuración actual.")
            return

        lista_opciones = ["-- Seleccione un Servidor --"] + [f"{s['nombre_alias']} ({s['ip']}) - {s['sistema_operativo']}" for s in servidores]
        
        try:
            default_index = lista_opciones.index(st.session_state["servidor_seleccionado_reporte"])
        except ValueError:
            default_index = 0

        seleccion = st.selectbox(
            "Seleccione Servidor Objetivo:", 
            lista_opciones, 
            index=default_index,
            key=f"rep_sb_servidor_dyn_{st.session_state['key_semilla_selectbox']}"
        )
        
        st.session_state["servidor_seleccionado_reporte"] = seleccion

        opciones_metricas = ["-- Todas las Métricas Activas --"]
        srv_info = None
        discos_configurados = []
        servicios_configurados = []
        
        if seleccion != "-- Seleccione un Servidor --":
            srv_info = next((s for s in servidores if f"{s['nombre_alias']} ({s['ip']}) - {s['sistema_operativo']}" == seleccion), None)
            
            if srv_info:
                opciones_metricas.append("Rendimiento CPU (%)")
                opciones_metricas.append("Consumo Memoria RAM (GB)")
                
                # FILTRO ESTRICTO: ELIMINA LOS SENSORES QUE MARQUEN 0, 00, VACÍO O NONE
                for i in range(1, 7):
                    id_disco = srv_info.get(f'id_sensor_disco_{i}')
                    if id_disco is not None and str(id_disco).strip() not in ("", "0", "00", "None"):
                        letra = srv_info.get(f'letra_disco_{i}') or f'Disco {i}'
                        opciones_metricas.append(f"Almacenamiento Disco {i} ({letra})")
                        discos_configurados.append(i)
                        
                for i in range(1, 8): 
                    id_servicio = srv_info.get(f'id_sensor_servicio_{i}')
                    if id_servicio is not None and str(id_servicio).strip() not in ("", "0", "00", "None"):
                        opciones_metricas.append(f"Estado de Servicio {i}")
                        servicios_configurados.append(i)
                        
                opciones_metricas.append("Tráfico de Red (Mb/s)")
                opciones_metricas.append("Latencia de Nodo (ms)")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fecha_inicio = st.date_input("Fecha Inicial", value=datetime.now() - timedelta(days=7), key="rep_dt_inicio")
        with col_d2:
            fecha_fin = st.date_input("Fecha Final", value=datetime.now(), key="rep_dt_fin")

        metrica_seleccionada = st.selectbox(
            "Filtrar Reporte por Métrica Específica:",
            options=opciones_metricas,
            disabled=(seleccion == "-- Seleccione un Servidor --"),
            key="rep_filtro_metrica_dinamico"
        )

        if fecha_inicio > fecha_fin:
            st.error("❌ Restricción Temporal: La fecha inicial no puede superar a la fecha final.")
            return

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([4, 1])
        with col_btn1:
            btn_procesar = st.button("📊 PROCESAR VISTA DE REPORTES (VOLÁTIL)", use_container_width=True, key="btn_procesar_reporte_maestro")
        with col_btn2:
            btn_limpiar = st.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_limpiar_reportes")

        if btn_limpiar:
            st.session_state["rep_listo"] = False
            st.session_state["rep_csv"] = None
            st.session_state["rep_pdf"] = None
            st.session_state["rep_name_csv"] = ""
            st.session_state["rep_name_pdf"] = ""
            st.session_state["servidor_seleccionado_reporte"] = "-- Seleccione un Servidor --"
            st.session_state["key_semilla_selectbox"] += 1
            st.rerun()

        if seleccion == "-- Seleccione un Servidor --" or not srv_info:
            st.session_state["rep_listo"] = False
            st.info("💡 Por favor, seleccione un servidor objetivo para mapear sus componentes teleométricos.")
            return

        ip_sel = srv_info['ip']

        # =====================================================================
        # LÓGICA INTERNA DEL BOTÓN PROCESAR (MAPPED 1:1 CON ALERTAS V3.7)
        # =====================================================================
        if btn_procesar:
            try:
                dt_desde = datetime.combine(fecha_inicio, time.min)
                dt_hasta = datetime.combine(fecha_fin, time.max)

                conn_data = conectar_bd()
                cursor_data = conn_data.cursor(dictionary=True)
                
                # Consulta con subconsultas correlacionadas filtrando estrictamente por componente exacto
                query_monitoreo = """
                    SELECT m.fecha_registro, m.ip_servidor, m.val_cpu, m.val_ram, 
                           m.val_disco_1, m.val_disco_2, m.val_disco_3, m.val_disco_4, m.val_disco_5, m.val_disco_6,
                           m.estado_servicio_1, m.estado_servicio_2, m.estado_servicio_3, m.estado_servicio_4, 
                           m.estado_servicio_5, m.estado_servicio_6, m.estado_servicio_7, m.estado_servicio_8,
                           m.val_red, m.val_latencia,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'CPU'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_cpu,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'RAM'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_ram,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_1'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_1,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_2'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_2,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_3'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_3,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_4'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_4,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_5'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_5,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'DISCO_6'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_6,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_1'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_1,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_2'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_2,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_3'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_3,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_4'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_4,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_5'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_5,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_6'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_6,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_7'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_7,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'SERVICIO_8'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_servicio_8,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'RED'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_red,
                           (
                               SELECT a.tipo_alerta FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor) AND a.componente = 'LATENCIA'
                                 AND (m.fecha_registro >= a.fecha_inicio AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3)))
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_latencia
                    FROM monitoreo m
                    WHERE TRIM(m.ip_servidor) = %s AND m.fecha_registro BETWEEN %s AND %s
                    ORDER BY m.fecha_registro DESC
                """
                
                params_sql = (str(ip_sel).strip(), dt_desde, dt_hasta)
                cursor_data.execute(query_monitoreo, params_sql)
                registros = cursor_data.fetchall()
                cursor_data.close()
                conn_data.close()

                if not registros:
                    st.error(f"❌ Sin registros de telemetría para {srv_info['nombre_alias']} en el rango seleccionado.")
                    st.session_state["rep_listo"] = False
                    return

                conteo_muestras = len(registros)
                discos_activos = [i for i in discos_configurados if f'val_disco_{i}' in registros[0]]
                servicios_activos = [i for i in servicios_configurados if f'estado_servicio_{i}' in registros[0]]
                
                def seguro_float(valor):
                    try: return float(valor) if valor is not None else 0.0
                    except: return 0.0

                def seguro_fecha(val_fecha):
                    if isinstance(val_fecha, datetime): return val_fecha
                    try: return datetime.strptime(str(val_fecha), '%Y-%m-%d %H:%M:%S')
                    except: return None

                # Evaluación exacta basada en las claves de componentes estandarizadas de la BD
                def evaluar_estado_por_metrica(fila, filtro):
                    filtro_upper = str(filtro).upper()
                    if "CPU" in filtro_upper:
                        val = fila.get('alerta_cpu')
                    elif "RAM" in filtro_upper or "MEMORIA" in filtro_upper:
                        val = fila.get('alerta_ram')
                    elif "DISCO" in filtro_upper:
                        d_num = "".join(filter(str.isdigit, filtro_upper))
                        val = fila.get(f'alerta_disco_{d_num}')
                    elif "SERVICIO" in filtro_upper:
                        s_num = "".join(filter(str.isdigit, filtro_upper))
                        val = fila.get(f'alerta_servicio_{s_num}')
                    elif "RED" in filtro_upper:
                        val = fila.get('alerta_red')
                    elif "LATENCIA" in filtro_upper:
                        val = fila.get('alerta_latencia')
                    else:
                        val = "ESTABLE"
                        
                    if val is None or str(val).strip() == "" or str(val).strip().lower() == "none":
                        val = "ESTABLE"
                    return str(val).strip().upper()

                # Cálculos de medias aritméticas operacionales
                p_cpu = sum(seguro_float(r.get('val_cpu')) for r in registros) / conteo_muestras
                p_ram = sum(seguro_float(r.get('val_ram')) for r in registros) / conteo_muestras
                p_red = sum(seguro_float(r.get('val_red')) for r in registros) / conteo_muestras
                p_lat = sum(seguro_float(r.get('val_latencia')) for r in registros) / conteo_muestras
                
                p_discos = {i: (sum(seguro_float(r.get(f'val_disco_{i}')) for r in registros) / conteo_muestras) for i in discos_activos}
                p_servicios = {}
                for i in servicios_activos:
                    muestras_on = sum(1 for r in registros if str(r.get(f'estado_servicio_{i}', 'OFF')).strip().upper() in ['ON', '1', 'TRUE', 'ACTIVO'])
                    p_servicios[i] = (muestras_on / conteo_muestras) * 100

                ts_file = datetime.now().strftime('%Y%m%d_%H%M%S')

                # =============================================================
                # GENERACIÓN CSV
                # =============================================================
                out_csv = io.StringIO()
                if metrica_seleccionada == "-- Todas las Métricas Activas --":
                    header_csv = ["Fecha Registro", "IP Servidor", "CPU(%)", "CPU Estado", "RAM(GB)", "RAM Estado"]
                    for i in discos_activos:
                        header_csv += [f"Disco{i}(GB)", f"Disco{i} Estado"]
                    for i in servicios_activos:
                        header_csv += [f"Svc{i}(Estado)", f"Svc{i} Estado"]
                    header_csv += ["Red(Mbs)", "Red Estado", "Latencia(ms)", "Latencia Estado"]
                else:
                    header_csv = ["Fecha Registro", "IP Servidor", metrica_seleccionada, "Estado Sistema"]

                out_csv.write(",".join(header_csv) + "\n")
                
                for r in registros:
                    dt_obj = seguro_fecha(r.get('fecha_registro'))
                    f_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S') if dt_obj else 'N/A'
                    
                    if metrica_seleccionada == "-- Todas las Métricas Activas --":
                        st_cpu = evaluar_estado_por_metrica(r, "CPU")
                        st_ram = evaluar_estado_por_metrica(r, "RAM")
                        
                        fila_datos = [f_str, ip_sel, str(r.get('val_cpu') or 0), st_cpu, str(r.get('val_ram') or 0), st_ram]
                        
                        for i in discos_activos:
                            st_d = evaluar_estado_por_metrica(r, f"DISCO_{i}")
                            fila_datos += [str(r.get(f'val_disco_{i}') or 0), st_d]
                            
                        for i in servicios_activos:
                            st_s = evaluar_estado_por_metrica(r, f"SERVICIO_{i}")
                            fila_datos += [str(r.get(f'estado_servicio_{i}') or 'OFF'), st_s]
                            
                        st_red = evaluar_estado_por_metrica(r, "RED")
                        st_lat = evaluar_estado_por_metrica(r, "LATENCIA")
                        fila_datos += [str(r.get('val_red') or 0), st_red, str(r.get('val_latencia') or 0), st_lat]
                    else:
                        txt_estado = evaluar_estado_por_metrica(r, metrica_seleccionada)
                        if "CPU" in metrica_seleccionada: val_col = str(r.get('val_cpu') or 0)
                        elif "RAM" in metrica_seleccionada: val_col = str(r.get('val_ram') or 0)
                        elif "Disco" in metrica_seleccionada:
                            d_num = int("".join([c for c in metrica_seleccionada.split("(")[0] if c.isdigit()]))
                            val_col = str(r.get(f'val_disco_{d_num}') or 0)
                        elif "Servicio" in metrica_seleccionada:
                            s_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                            val_col = str(r.get(f'estado_servicio_{s_num}') or 'OFF')
                        elif "Red" in metrica_seleccionada: val_col = str(r.get('val_red') or 0)
                        elif "Latencia" in metrica_seleccionada: val_col = str(r.get('val_latencia') or 0)
                        else: val_col = "0"
                        fila_datos = [f_str, ip_sel, val_col, txt_estado]
                        
                    out_csv.write(",".join(fila_datos) + "\n")
                
                bin_csv = out_csv.getvalue().encode('utf-8', errors='ignore')
                name_csv = f"Reporte_{ip_sel}_{ts_file}.csv"

                # =============================================================
                # GENERACIÓN PDF (VINCULACIÓN PERFECTA CON COMPONENTES DE ALERTAS)
                # =============================================================
                pdf = PDF(orientation='L', unit='mm', format='A4')
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, f"Filtro Desde: {fecha_inicio.strftime('%d/%m/%Y')} | Hasta: {fecha_fin.strftime('%d/%m/%Y')}", 0, 1)
                pdf.cell(0, 6, f"Servidor: {srv_info['nombre_alias']} ({ip_sel}) | Dimensión: {metrica_seleccionada}", 0, 1)
                pdf.cell(0, 6, f"Volumen Analizado: {conteo_muestras} muestras sincronizadas.", 0, 1)
                pdf.ln(5)

                if metrica_seleccionada == "-- Todas las Métricas Activas --":
                    bloques_sensores = [
                        {"titulo": "1. Rendimiento CPU (%)", "clave_val": "val_cpu", "suffix": "%", "filtro_lbl": "CPU"},
                        {"titulo": "2. Consumo Memoria RAM (GB)", "clave_val": "val_ram", "suffix": " GB", "filtro_lbl": "RAM"}
                    ]
                    
                    for i in discos_activos:
                        letra_lbl = srv_info.get(f'letra_disco_{i}') or f'Disco {i}'
                        bloques_sensores.append({
                            "titulo": f"Almacenamiento Disco {i} ({letra_lbl})",
                            "clave_val": f"val_disco_{i}",
                            "suffix": " GB",
                            "filtro_lbl": f"DISCO_{i}"
                        })
                        
                    for i in servicios_activos:
                        bloques_sensores.append({
                            "titulo": f"Estado de Servicio {i}",
                            "clave_val": f"estado_servicio_{i}",
                            "suffix": "",
                            "filtro_lbl": f"SERVICIO_{i}"
                        })
                        
                    bloques_sensores.append({"titulo": "Tráfico de Red (Mb/s)", "clave_val": "val_red", "suffix": " Mb/s", "filtro_lbl": "RED"})
                    bloques_sensores.append({"titulo": "Latencia de Nodo (ms)", "clave_val": "val_latencia", "suffix": " ms", "filtro_lbl": "LATENCIA"})

                    for b_idx, bloque in enumerate(bloques_sensores):
                        if b_idx > 0:
                            if pdf.get_y() > 150: pdf.add_page()
                            else: pdf.ln(6)
                                
                        pdf.set_font("Arial", "B", 11)
                        pdf.set_text_color(0, 51, 102)
                        pdf.cell(0, 6, bloque["titulo"], 0, 1)
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.set_fill_color(0, 51, 102)
                        pdf.set_text_color(255, 255, 255)
                        pdf.cell(50, 6, "Fecha / Hora Registro", 1, 0, "C", True)
                        pdf.cell(50, 6, "IP Nodo Servidor", 1, 0, "C", True)
                        pdf.cell(60, 6, "Valor Telemetria", 1, 0, "C", True)
                        pdf.cell(45, 6, "Estado Sensor (Historial Alertas)", 1, 1, "C", True)
                        
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", "", 9)
                        
                        for r in registros[:15]:
                            dt_obj = seguro_fecha(r.get('fecha_registro'))
                            f_row = dt_obj.strftime('%d/%m/%Y %H:%M') if dt_obj else 'N/A'
                            
                            txt_estado = evaluar_estado_por_metrica(r, bloque["filtro_lbl"])
                            
                            raw_val = r.get(bloque["clave_val"])
                            if "estado_servicio" in bloque["clave_val"]:
                                val_s_str = str(raw_val or 'OFF').strip().upper()
                                val_txt = "ACTIVO (ON)" if val_s_str in ['ON', '1', 'TRUE', 'ACTIVO'] else "INACTIVO (OFF)"
                            else:
                                val_txt = f"{raw_val or 0}{bloque['suffix']}"
                                
                            pdf.cell(50, 5, f_row, 1, 0, "C")
                            pdf.cell(50, 5, ip_sel, 1, 0, "C")
                            pdf.cell(60, 5, val_txt, 1, 0, "C")
                            pdf.cell(45, 5, txt_estado, 1, 1, "C")
                            
                        if len(registros) > 15:
                            pdf.set_font("Arial", "I", 8)
                            pdf.cell(0, 4, f"... (* Se omitieron {len(registros) - 15} muestras en el PDF por optimización de espacio).", 0, 1)
                            pdf.set_font("Arial", "", 9)
                else:
                    # VISTA INDIVIDUAL REPARADA
                    pdf.set_font("Arial", "B", 11)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 6, "Resumen Basal de Medias Obtenidas", 0, 1)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 10)
                    
                    if "CPU" in metrica_seleccionada: pdf.cell(65, 6, f"- Promedio Carga CPU: {p_cpu:.2f} %", 0, 1)
                    elif "RAM" in metrica_seleccionada: pdf.cell(65, 6, f"- Promedio Consumo RAM: {p_ram:.2f} GB", 0, 1)
                    elif "Red" in metrica_seleccionada: pdf.cell(65, 6, f"- Promedio Trafico Red: {p_red:.2f} Mb/s", 0, 1)
                    elif "Latencia" in metrica_seleccionada: pdf.cell(65, 6, f"- Promedio Latencia Nodo: {p_lat:.2f} ms", 0, 1)
                    elif "Disco" in metrica_seleccionada:
                        d_num = int("".join([c for c in metrica_seleccionada.split("(")[0] if c.isdigit()]))
                        pdf.cell(65, 6, f"- Promedio Almacenamiento Disco {d_num}: {p_discos.get(d_num, 0.0):.2f} GB", 0, 1)
                    elif "Servicio" in metrica_seleccionada:
                        s_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                        pdf.cell(65, 6, f"- Disponibilidad Servicio {s_num}: {p_servicios.get(s_num, 0.0):.1f} % Online", 0, 1)

                    pdf.ln(4)
                    pdf.set_font("Arial", "B", 9)
                    pdf.set_fill_color(0, 51, 102)
                    pdf.set_text_color(255, 255, 255)
                    
                    columnas_pdf = [("Fecha/Hora Registro", 45), ("IP Servidor Objetivo", 45), (metrica_seleccionada, 60), ("Estado Alertas BD", 40)]
                    for t, w in columnas_pdf:
                        pdf.cell(w, 6, t, 1, 0, "C", True)
                    pdf.ln()

                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 9)
                    
                    for r in registros[:35]:
                        txt_estado = evaluar_estado_por_metrica(r, metrica_seleccionada)
                        dt_obj = seguro_fecha(r.get('fecha_registro'))
                        f_row = dt_obj.strftime('%d/%m/%Y %H:%M') if dt_obj else 'N/A'
                        
                        if "CPU" in metrica_seleccionada: val_txt = f"{r.get('val_cpu') or 0} %"
                        elif "RAM" in metrica_seleccionada: val_txt = f"{r.get('val_ram') or 0} GB"
                        elif "Disco" in metrica_seleccionada:
                            d_num = int("".join([c for c in metrica_seleccionada.split("(")[0] if c.isdigit()]))
                            val_txt = f"{r.get(f'val_disco_{d_num}') or 0} GB"
                        elif "Servicio" in metrica_seleccionada:
                            s_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                            val_s_str = str(r.get(f'estado_servicio_{s_num}', 'OFF')).strip().upper()
                            val_txt = "ACTIVO (ON)" if val_s_str in ['ON', '1', 'TRUE', 'ACTIVO'] else "INACTIVO (OFF)"
                        elif "Red" in metrica_seleccionada: val_txt = f"{r.get('val_red') or 0} Mb/s"
                        elif "Latencia" in metrica_seleccionada: val_txt = f"{r.get('val_latencia') or 0} ms"
                        else: val_txt = "0"
                        
                        pdf.cell(45, 5, f_row, 1, 0, "C")
                        pdf.cell(45, 5, ip_sel, 1, 0, "C")
                        pdf.cell(60, 5, val_txt, 1, 0, "C")
                        pdf.cell(40, 5, txt_estado, 1, 1, "C")

                    if len(registros) > 35:
                        pdf.ln(2)
                        pdf.set_font("Arial", "I", 8)
                        pdf.cell(0, 5, "... (* Muestras adicionales omitidas por espacio).", 0, 1)

                bin_pdf = pdf.output(dest='S')
                bin_pdf = bytes(bin_pdf) if not isinstance(bin_pdf, str) else bin_pdf.encode('latin-1', errors='ignore')
                name_pdf = f"Reporte_{ip_sel}_{ts_file}.pdf"

                st.session_state["rep_csv"] = bin_csv
                st.session_state["rep_pdf"] = bin_pdf
                st.session_state["rep_name_csv"] = name_csv
                st.session_state["rep_name_pdf"] = name_pdf
                st.session_state["rep_listo"] = True

                st.success("🎉 ¡Muestras vinculadas a la tabla de alertas v3.7 con éxito!")
                st.rerun()

            except Exception as e:
                st.error("❌ Fallo técnico al procesar las estructuras de datos dinámicas.")
                with open("simpol_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] Error crítico v3.7 en reportes.py: {e}\n")

        # RENDERIZADO DE LOS BOTONES DE DESCARGA
        if st.session_state["rep_listo"]:
            st.markdown("---")
            col_down1, col_down2 = st.columns(2)
            col_down1.download_button(
                label="⬇️ Descargar Reporte Generado (CSV)", 
                data=st.session_state["rep_csv"], 
                file_name=st.session_state["rep_name_csv"], 
                mime="text/csv", 
                key="dl_btn_rep_csv"
            )
            col_down2.download_button(
                label="⬇️ Descargar Informe Firmado (PDF)", 
                data=st.session_state["rep_pdf"], 
                file_name=st.session_state["rep_name_pdf"], 
                mime="application/pdf", 
                key="dl_btn_rep_pdf"
            )

    # =====================================================================
    # PESTAÑA 2: VISUALIZACIÓN DE LA BÓVEDA DIGITAL DE ARCHIVOS
    # =====================================================================
    with tab_historial:
        st.markdown('<h3 style="color:#003366; margin-top:10px;">📜 Expedientes Archivados</h3>', unsafe_allow_html=True)
        
        historial = obtener_historial_reportes()
        if not historial:
            st.info("📭 No se localizan reportes guardados en la base de datos central.")
        else:
            rejilla_columnas = [3.5, 1.2, 1.2, 2.2, 2.2, 1.7]
            
            st.markdown(
                """
                <div style='background-color: #003366; padding: 12px; border-radius: 6px 6px 0px 0px; margin-bottom: -1px;'>
                    <div style='display: flex; color: white; font-weight: bold; font-size: 13px;'>
                        <div style='width: 31.8%; text-align: left;'>Nombre del Expediente</div>
                        <div style='width: 10.9%; text-align: center;'>Formato</div>
                        <div style='width: 10.9%; text-align: center;'>Peso</div>
                        <div style='width: 20.0%; text-align: center;'>Fecha de Creación</div>
                        <div style='width: 20.0%; text-align: right; padding-right:15px;'>Generado Por</div>
                        <div style='width: 15.4%; text-align: center;'>Operación</div>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            for index, item in enumerate(historial):
                fecha_str = item['fecha_generacion'].strftime('%d/%m/%Y %H:%M') if item['fecha_generacion'] else 'N/A'
                badge_class = "badge-pdf" if item['formato'] == "PDF" else "badge-csv"
                background_color = "#E6F0FA" if index % 2 == 0 else "#FFFFFF"
                
                st.markdown(
                    f"""
                    <style>
                        .badge-pdf {{ background-color: #f8d7da; color: #721c24; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                        .badge-csv {{ background-color: #d4edda; color: #155724; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                    </style>
                    <div style='background-color: {background_color}; padding: 8px 12px; border-left: 1px solid #ccc; border-right: 1px solid #ccc; border-bottom: 1px solid #eee; margin-top: -1px;'>
                    """, 
                    unsafe_allow_html=True
                )
                
                c1, c2, c3, c4, c5, c6 = st.columns(rejilla_columnas)
                
                c1.write(f"📄 {item['nombre_archivo']}")
                c2.markdown(f"<div style='text-align:center; padding-top:4px;'><span class='{badge_class}'>{item['formato']}</span></div>", unsafe_allow_html=True)
                c3.markdown(f"<div style='text-align:center; color:#333; padding-top:4px;'>{item['tamanio_kb']}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='text-align:center; color:#333; font-family:monospace; padding-top:4px;'>{fecha_str}</div>", unsafe_allow_html=True)
                c5.markdown(f"<div style='text-align:right; color:#333; padding-top:4px; padding-right:10px;'>👤 {item['registrado_por']}</div>", unsafe_allow_html=True)
                
                with c6:
                    reporte_blob = descargar_contenido_blob(item['id'])
                    st.download_button(
                        label="📥 Descargar",
                        data=bytes(reporte_blob),
                        file_name=item['nombre_archivo'],
                        mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                        key=f"dl_corp_{item['id']}",
                        use_container_width=True
                    )
                        
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    analista = st.session_state.get("nombre_completo", "Analista Institucional")
    uid = st.session_state.get("id", 1)
    ulogin = st.session_state.get("usuario", "operador1")
    
    mostrar_pantalla(analista, uid, ulogin)