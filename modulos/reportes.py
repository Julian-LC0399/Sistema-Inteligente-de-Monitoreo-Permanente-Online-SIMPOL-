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
        self.cell(0, 5, "Reporte de Servidor (Analisis de Metricas Integrado)", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Pagina {self.page_no()} | Confidencial", 0, 0, "C")

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
    # PESTAÑA 1: GENERACIÓN DE REPORTES EN CALIENTE (MEMORIA VOLÁTIL)
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
                
                for i in range(1, 7):
                    id_disco = srv_info.get(f'id_sensor_disco_{i}')
                    if id_disco is not None and str(id_disco).strip() != "" and int(id_disco) != 0:
                        letra = srv_info.get(f'letra_disco_{i}') or f'Disco {i}'
                        opciones_metricas.append(f"Almacenamiento Disco {i} ({letra})")
                        discos_configurados.append(i)
                        
                for i in range(1, 9): 
                    id_servicio = srv_info.get(f'id_sensor_servicio_{i}')
                    if id_servicio is not None and str(id_servicio).strip() != "" and int(id_servicio) != 0:
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
        # LÓGICA INTERNA DEL BOTÓN PROCESAR
        # =====================================================================
        if btn_procesar:
            try:
                dt_desde = datetime.combine(fecha_inicio, time.min)
                dt_hasta = datetime.combine(fecha_fin, time.max)

                conn_data = conectar_bd()
                cursor_data = conn_data.cursor(dictionary=True)
                
                # REFACTORIZACIÓN DE BÚSQUEDA FLEXIBLE
                letra_d1 = str(srv_info.get('letra_disco_1') or 'XYZ').strip()
                letra_d2 = str(srv_info.get('letra_disco_2') or 'XYZ').strip()
                letra_d3 = str(srv_info.get('letra_disco_3') or 'XYZ').strip()
                letra_d4 = str(srv_info.get('letra_disco_4') or 'XYZ').strip()
                letra_d5 = str(srv_info.get('letra_disco_5') or 'XYZ').strip()
                letra_d6 = str(srv_info.get('letra_disco_6') or 'XYZ').strip()

                # SOLUCIÓN DEFINITIVA: Se usa DATE_FORMAT para ignorar los segundos en la comparación.
                # Si pertenecen al mismo minuto de la alerta o si está dentro del rango abierto, se asocia el CRÍTICO.
                query_monitoreo = """
                    SELECT m.fecha_registro, m.val_cpu, m.val_ram, 
                           m.val_disco_1, m.val_disco_2, m.val_disco_3, m.val_disco_4, m.val_disco_5, m.val_disco_6,
                           m.estado_servicio_1, m.estado_servicio_2, m.estado_servicio_3, m.estado_servicio_4, 
                           m.estado_servicio_5, m.estado_servicio_6, m.estado_servicio_7, m.estado_servicio_8,
                           m.val_red, m.val_latencia,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%cpu%' OR LOWER(a.tipo_alerta) LIKE '%cpu%')
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_cpu,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%ram%' OR LOWER(a.componente) LIKE '%memoria%')
                                 AND LOWER(a.componente) NOT LIKE '%disco%'
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_ram,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 1%' OR LOWER(a.componente) LIKE '%disco1%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_1,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 2%' OR LOWER(a.componente) LIKE '%disco2%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_2,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 3%' OR LOWER(a.componente) LIKE '%disco3%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_3,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 4%' OR LOWER(a.componente) LIKE '%disco4%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_4,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 5%' OR LOWER(a.componente) LIKE '%disco5%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_5,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (LOWER(a.componente) LIKE '%disco 6%' OR LOWER(a.componente) LIKE '%disco6%' OR LOWER(a.componente) LIKE %s)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_disco_6,
                           (
                               SELECT a.tipo_alerta 
                               FROM alertas a 
                               WHERE TRIM(a.ip_servidor) = TRIM(m.ip_servidor)
                                 AND (
                                     DATE_FORMAT(m.fecha_registro, '%Y-%m-%d %H:%i') >= DATE_FORMAT(a.fecha_inicio, '%Y-%m-%d %H:%i')
                                     AND m.fecha_registro <= COALESCE(a.fecha_fin, NOW(3))
                                 )
                               ORDER BY a.id DESC LIMIT 1
                           ) AS alerta_defecto
                    FROM monitoreo m
                    WHERE TRIM(m.ip_servidor) = %s AND m.fecha_registro BETWEEN %s AND %s
                    ORDER BY m.fecha_registro DESC
                """
                
                params_sql = (
                    f"%{letra_d1.lower()}%", f"%{letra_d2.lower()}%", f"%{letra_d3.lower()}%",
                    f"%{letra_d4.lower()}%", f"%{letra_d5.lower()}%", f"%{letra_d6.lower()}%",
                    str(ip_sel).strip(), dt_desde, dt_hasta
                )
                
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

                def evaluar_estado_por_metrica(fila, filtro):
                    filtro_upper = str(filtro).upper()
                    if "CPU" in filtro_upper:
                        val = fila.get('alerta_cpu') or fila.get('alerta_defecto')
                    elif "RAM" in filtro_upper or "MEMORIA" in filtro_upper:
                        val = fila.get('alerta_ram')
                    elif "DISCO" in filtro_upper:
                        d_num = "".join(filter(str.isdigit, filtro_upper))
                        val = fila.get(f'alerta_disco_{d_num}') if d_num else fila.get('alerta_defecto')
                        if val is None:
                            val = fila.get('alerta_defecto')
                    else:
                        val = fila.get('alerta_defecto')
                    
                    return str(val).strip() if val is not None else "Estable"

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
                    header_csv = ["Fecha Registro", "IP Servidor", "CPU(%)", "RAM(GB)"] + [f"Disco{i}(GB)" for i in discos_activos] + [f"Svc{i}(Estado)" for i in servicios_activos] + ["Red(Mbs)", "Latencia(ms)", "Estado Sistema"]
                else:
                    header_csv = ["Fecha Registro", "IP Servidor", metrica_seleccionada, "Estado Sistema"]

                out_csv.write(",".join(header_csv) + "\n")
                
                for r in registros:
                    dt_obj = seguro_fecha(r.get('fecha_registro'))
                    f_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S') if dt_obj else 'N/A'
                    
                    if metrica_seleccionada == "-- Todas las Métricas Activas --":
                        txt_estado = str(r.get('alerta_defecto') or "Estable").strip()
                        fila_datos = [f_str, ip_sel, str(r.get('val_cpu') or 0), str(r.get('val_ram') or 0)] + [str(r.get(f'val_disco_{i}') or 0) for i in discos_activos] + [str(r.get(f'estado_servicio_{i}') or 'OFF') for i in servicios_activos] + [str(r.get('val_red') or 0), str(r.get('val_latencia') or 0), txt_estado]
                    else:
                        txt_estado = evaluar_estado_por_metrica(r, metrica_seleccionada)
                        if "CPU" in metrica_seleccionada: val_col = str(r.get('val_cpu') or 0)
                        elif "RAM" in metrica_seleccionada: val_col = str(r.get('val_ram') or 0)
                        elif "Disco" in metrica_seleccionada:
                            d_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
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
                # GENERACIÓN PDF
                # =============================================================
                pdf = PDF(orientation='L', unit='mm', format='A4')
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, f"Filtro Desde: {fecha_inicio.strftime('%d/%m/%Y')} | Hasta: {fecha_fin.strftime('%d/%m/%Y')}", 0, 1)
                pdf.cell(0, 6, f"Servidor: {srv_info['nombre_alias']} ({ip_sel}) | Dimension: {metrica_seleccionada}", 0, 1)
                pdf.cell(0, 6, f"Volumen Analizado: {conteo_muestras} muestras sincronizadas.", 0, 1)
                pdf.ln(5)

                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, "Resumen Basal de Medias Obtenidas", 0, 1)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 10)
                
                if metrica_seleccionada == "-- Todas las Métricas Activas --" or "CPU" in metrica_seleccionada:
                    pdf.cell(65, 6, f"- Promedio Carga CPU: {p_cpu:.2f} %", 0, 1)
                if metrica_seleccionada == "-- Todas las Métricas Activas --" or "RAM" in metrica_seleccionada:
                    pdf.cell(65, 6, f"- Promedio Consumo RAM: {p_ram:.2f} GB", 0, 1)
                if metrica_seleccionada == "-- Todas las Métricas Activas --" or "Red" in metrica_seleccionada:
                    pdf.cell(65, 6, f"- Promedio Trafico Red: {p_red:.2f} Mb/s", 0, 1)
                if metrica_seleccionada == "-- Todas las Métricas Activas --" or "Latencia" in metrica_seleccionada:
                    pdf.cell(65, 6, f"- Promedio Latencia Nodo: {p_lat:.2f} ms", 0, 1)
                
                if "Disco" in metrica_seleccionada:
                    d_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                    pdf.cell(65, 6, f"- Promedio Almacenamiento Disco {d_num}: {p_discos.get(d_num, 0.0):.2f} GB", 0, 1)
                elif "Servicio" in metrica_seleccionada:
                    s_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                    pdf.cell(65, 6, f"- Disponibilidad Servicio {s_num}: {p_servicios.get(s_num, 0.0):.1f} % Online", 0, 1)

                pdf.ln(4)
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                
                if metrica_seleccionada == "-- Todas las Métricas Activas --":
                    columnas_pdf = [("Fecha/Hora", 30), ("CPU", 14), ("RAM", 14)]
                    for i in discos_activos: columnas_pdf.append((f"D{i}", 11))
                    for i in servicios_activos: columnas_pdf.append((f"S{i}", 10))
                    columnas_pdf += [("Red", 18), ("Latencia", 16), ("Estado", 20)]
                else:
                    columnas_pdf = [("Fecha/Hora", 40), ("IP Servidor", 40), (metrica_seleccionada, 55), ("Estado Sistema", 35)]

                for t, w in columnas_pdf:
                    pdf.cell(w, 6, t, 1, 0, "C", True)
                pdf.ln()

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 8)
                
                for r in registros[:35]:
                    dt_obj = seguro_fecha(r.get('fecha_registro'))
                    f_row = dt_obj.strftime('%d/%m %H:%M') if dt_obj else 'N/A'
                    
                    if metrica_seleccionada == "-- Todas las Métricas Activas --":
                        txt_estado = str(r.get('alerta_defecto') or "Estable").strip()
                        pdf.cell(30, 5, f_row, 1, 0, "C")
                        pdf.cell(14, 5, f"{r.get('val_cpu') or 0}%", 1, 0, "C")
                        pdf.cell(14, 5, f"{r.get('val_ram') or 0}G", 1, 0, "C")
                        for i in discos_activos: pdf.cell(11, 5, f"{r.get(f'val_disco_{i}') or 0}G", 1, 0, "C")
                        for i in servicios_activos:
                            val_s_str = str(r.get(f'estado_servicio_{i}', 'OFF')).strip().upper()
                            pdf.cell(10, 5, "OK" if val_s_str in ['ON', '1', 'TRUE', 'ACTIVO'] else "ERR", 1, 0, "C")
                        pdf.cell(18, 5, f"{r.get('val_red') or 0}Mb", 1, 0, "C")
                        pdf.cell(16, 5, f"{r.get('val_latencia') or 0}ms", 1, 0, "C")
                        pdf.cell(20, 5, txt_estado, 1, 1, "C")
                    else:
                        txt_estado = evaluar_estado_por_metrica(r, metrica_seleccionada)
                        pdf.cell(40, 5, f_row, 1, 0, "C")
                        pdf.cell(40, 5, ip_sel, 1, 0, "C")
                        if "CPU" in metrica_seleccionada: val_txt = f"{r.get('val_cpu') or 0} %"
                        elif "RAM" in metrica_seleccionada: val_txt = f"{r.get('val_ram') or 0} GB"
                        elif "Disco" in metrica_seleccionada:
                            d_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                            val_txt = f"{r.get(f'val_disco_{d_num}') or 0} GB"
                        elif "Servicio" in metrica_seleccionada:
                            s_num = int("".join(filter(str.isdigit, metrica_seleccionada)))
                            val_s_str = str(r.get(f'estado_servicio_{s_num}', 'OFF')).strip().upper()
                            val_txt = "ACTIVO (ON)" if val_s_str in ['ON', '1', 'TRUE', 'ACTIVO'] else "INACTIVO (OFF)"
                        elif "Red" in metrica_seleccionada: val_txt = f"{r.get('val_red') or 0} Mb/s"
                        elif "Latencia" in metrica_seleccionada: val_txt = f"{r.get('val_latencia') or 0} ms"
                        pdf.cell(55, 5, val_txt, 1, 0, "C")
                        pdf.cell(35, 5, txt_estado, 1, 1, "C")

                if len(registros) > 35:
                    pdf.ln(2)
                    pdf.set_font("Arial", "I", 8)
                    pdf.cell(0, 5, "... (* Muestras adicionales omitidas en impresion por optimizacion).", 0, 1)

                bin_pdf = pdf.output(dest='S')
                if isinstance(bin_pdf, (str, bytearray)):
                    if isinstance(bin_pdf, str):
                        bin_pdf = bin_pdf.encode('latin-1', errors='ignore')
                    else:
                        bin_pdf = bytes(bin_pdf)
                else:
                    bin_pdf = bytes(bin_pdf)

                name_pdf = f"Reporte_{ip_sel}_{ts_file}.pdf"

                st.session_state["rep_csv"] = bin_csv
                st.session_state["rep_pdf"] = bin_pdf
                st.session_state["rep_name_csv"] = name_csv
                st.session_state["rep_name_pdf"] = name_pdf
                st.session_state["rep_listo"] = True

                st.success("🎉 ¡Muestras teleométricas procesadas y vinculadas en memoria con éxito!")
                st.rerun()

            except Exception as e:
                st.error("❌ Fallo técnico al procesar las estructuras de datos dinámicas.")
                with open("simpol_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] Error crítico en procesamiento dinámico de reportes.py: {e}\n")

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