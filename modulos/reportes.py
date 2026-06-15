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
        self.cell(0, 5, "Reporte Operacional de Infraestructura y Telemetría", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE CONSULTA A BASE DE DATOS (VERSION SINCRONIZADA V3.9.8)
# =====================================================================
def obtener_datos_reporte(ip_servidor, fecha_inicio, fecha_fin):
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT * FROM monitoreo 
            WHERE ip_servidor = %s AND fecha_registro BETWEEN %s AND %s
            ORDER BY fecha_registro DESC
        """
        cursor.execute(query, (ip_servidor, fecha_inicio, fecha_fin))
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados
    except Exception as e:
        st.error(f"Error consultando registros para reporte: {e}")
        if conn: conn.close()
        return []

def guardar_reporte_archivado(nombre_archivo, formato, ip_servidor, contenido_blob, usuario_id, tamanio_kb):
    conn = conectar_bd()
    if not conn: return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO reportes_archivados 
            (nombre_archivo, format, ip_servidor, contenido, usuario_id, snapshot_total_gb, snapshot_disponible_gb, snapshot_disponible_pct, tamanio_kb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            nombre_archivo, formato, ip_servidor.strip(), contenido_blob, usuario_id, 
            0.0, 0.0, 0.0, tamanio_kb
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error persistiendo archivo en histórico: {e}")
        if conn: conn.close()
        return False

def listar_reportes_archivados_filtrado(ip_servidor, token_sensor):
    conn = conectar_bd()
    resultados = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT r.id, r.nombre_archivo, r.format as formato, r.ip_servidor, r.fecha_generacion, r.tamanio_kb, u.usuario as registrado_por
                FROM reportes_archivados r
                LEFT JOIN usuarios u ON r.usuario_id = u.id
                WHERE TRIM(r.ip_servidor) = %s AND r.nombre_archivo LIKE %s
                ORDER BY r.fecha_generacion DESC
            """
            patron_busqueda = f"%_{token_sensor}_%"
            cursor.execute(query, (ip_servidor.strip(), patron_busqueda))
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error listando histórico filtrado: {e}")
    return resultados

def descargar_contenido_blob(id_archivo):
    conn = conectar_bd()
    blob_data = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_archivados WHERE id = %s"
            cursor.execute(query, (id_archivo,))
            row = cursor.fetchone()
            if row: blob_data = row['contenido']
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error extrayendo binario: {e}")
    return blob_data

# =====================================================================
# VISTA Y CONTROLADOR PRINCIPAL DEL MÓDULO DE REPORTES
# =====================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">📋 Módulo Operacional de Reportes</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Consolidación y Almacenamiento | <b>Gestor:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    from database import obtener_lista_servidores
    servidores = obtener_lista_servidores()
    if not servidores:
        st.info("💡 No se registran nodos de infraestructura para compilar reportes.")
        return

    # --- CONTROL DE ESTADOS EN SESSION STATE ---
    if "filtro_servidor" not in st.session_state:
        st.session_state.filtro_servidor = "-- Seleccione un Servidor --"
    if "filtro_sensor_general" not in st.session_state:
        st.session_state.filtro_sensor_general = "Reporte Integral (Todas las Variables)"
    if "filtro_reporte_especifico" not in st.session_state:
        st.session_state.filtro_reporte_especifico = "Métrica Completa (Set Triple)"
    if "filtro_fecha_i" not in st.session_state:
        st.session_state.filtro_fecha_i = datetime.now() - timedelta(days=1)
    if "filtro_fecha_f" not in st.session_state:
        st.session_state.filtro_fecha_f = datetime.now()

    nombres_servidores = ["-- Seleccione un Servidor --"] + [s['nombre_alias'] for s in servidores]
    
    try:
        idx_inicial = nombres_servidores.index(st.session_state.filtro_servidor)
    except ValueError:
        idx_inicial = 0

    # FILTRO 1: Selector de Servidores
    serv_seleccionado = st.selectbox(
        "Seleccione el Servidor objetivo:", 
        options=nombres_servidores, 
        index=idx_inicial,
        key="widget_rep_servidor"
    )
    st.session_state.filtro_servidor = serv_seleccionado

    if serv_seleccionado == "-- Seleccione un Servidor --":
        st.info("💡 Seleccione un nodo de la lista para activar las herramientas de reportes.")
        return

    serv_info = next((s for s in servidores if s['nombre_alias'] == serv_seleccionado), None)
    ip_objetivo = str(serv_info['ip']).strip()

    # --- MAPEO DINÁMICO DE LETRAS DE DISCO DESDE LA BD (LIMPIANDO \\) ---
    letras_discos = {}
    for i in range(1, 7):
        campo_letra = f'letra_disco_{i}'
        letra_raw = str(serv_info.get(campo_letra, '')).replace('\\', '').strip().upper()
        letras_discos[i] = letra_raw if letra_raw else f"DISCO{i}"

    # FILTRO 2: Sensores Activos en Servidor (Validando ID > 0 según tu BD)
    sensores_disponibles = ["Reporte Integral (Todas las Variables)"]
    
    if serv_info.get('id_sensor_cpu') and int(serv_info['id_sensor_cpu']) > 0:
        sensores_disponibles.append("Uso de CPU")
        
    if serv_info.get('id_sensor_ram') and int(serv_info['id_sensor_ram']) > 0:
        sensores_disponibles.append("Memoria RAM")
        
    for i in range(1, 7):
        campo_sensor = f'id_sensor_disco_{i}'
        if serv_info.get(campo_sensor) and int(serv_info[campo_sensor]) > 0:
            sensores_disponibles.append(f"Disco {letras_discos[i]}")
            
    if serv_info.get('id_sensor_latencia') and int(serv_info['id_sensor_latencia']) > 0:
        sensores_disponibles.append("Latencia de Red")

    if st.session_state.filtro_sensor_general not in sensores_disponibles:
        st.session_state.filtro_sensor_general = sensores_disponibles[0]

    sensor_general = st.selectbox(
        "Sensor registrado en el Servidor:",
        options=sensores_disponibles,
        index=sensores_disponibles.index(st.session_state.filtro_sensor_general),
        key="widget_rep_sensor_general"
    )
    st.session_state.filtro_sensor_general = sensor_general

    s_prefix = "INTEGRAL"
    num_disco_activo = None
    
    if "RAM" in sensor_general: 
        s_prefix = "RAM"
    elif "CPU" in sensor_general: 
        s_prefix = "CPU"
    elif "Latencia" in sensor_general: 
        s_prefix = "LATENCIA"
    elif "Disco" in sensor_general:
        letra_sel = sensor_general.replace("Disco ", "").strip()
        for i, letra in letras_discos.items():
            if letra == letra_sel:
                s_prefix = f"DISCO{i}"
                num_disco_activo = i
                break

    tab1, tab2 = st.tabs(["📊 Generación de Reportes", "📜 Repositorio e Histórico de Archivos"])

    # =====================================================================
    # PESTAÑA 1: PARÁMETROS Y EMISIÓN DE REPORTE POR SENSOR
    # =====================================================================
    with tab1:
        st.markdown("#### Parámetros de Extracción y Filtrado")

        opciones_reporte_especifico = ["Métrica Completa (Set Triple)"]
        if s_prefix == "RAM":
            opciones_reporte_especifico = ["Métrica Completa (Set Triple)", "Solo RAM Disponible (GB)", "Solo RAM Disponible %"]
        elif "DISCO" in s_prefix and num_disco_activo:
            letra_activa = letras_discos[num_disco_activo]
            opciones_reporte_especifico = ["Métrica Completa (Set Triple)", f"Solo Espacio Libre {letra_activa} (GB)", f"Solo Espacio Libre {letra_activa} %"]
        elif s_prefix == "CPU":
            opciones_reporte_especifico = ["Porcentaje de Uso de CPU"]
        elif s_prefix == "LATENCIA":
            opciones_reporte_especifico = ["Métrica de Latencia de Red (ms)"]
        else:
            opciones_reporte_especifico = ["Reporte Consolidado Global SIMPOL"]

        if st.session_state.filtro_reporte_especifico not in opciones_reporte_especifico:
            st.session_state.filtro_reporte_especifico = opciones_reporte_especifico[0]

        reporte_especifico = st.selectbox(
            "Tipo de reporte analítico a generar por sensor:",
            options=opciones_reporte_especifico,
            index=opciones_reporte_especifico.index(st.session_state.filtro_reporte_especifico),
            key="widget_rep_especifico"
        )
        st.session_state.filtro_reporte_especifico = reporte_especifico

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_i = st.date_input("Fecha Inicial:", value=st.session_state.filtro_fecha_i, key="widget_rep_fi")
            st.session_state.filtro_fecha_i = fecha_i
        with col_f2:
            fecha_f = st.date_input("Fecha Final:", value=st.session_state.filtro_fecha_f, key="widget_rep_ff")
            st.session_state.filtro_fecha_f = fecha_f

        col_btn1, col_btn2 = st.columns([3, 1])
        
        with col_btn2:
            if st.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_clear_all_filters"):
                for k in ["widget_rep_servidor", "widget_rep_sensor_general", "widget_rep_especifico", "widget_rep_fi", "widget_rep_ff", "filtro_servidor", "filtro_sensor_general", "filtro_reporte_especifico", "filtro_fecha_i", "filtro_fecha_f"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        dt_inicio = datetime.combine(fecha_i, time.min)
        dt_fin = datetime.combine(fecha_f, time.max)

        if dt_inicio >= dt_fin:
            st.error("❌ La fecha inicial debe ser menor a la fecha final seleccionada.")
        else:
            datos_muestras = obtener_datos_reporte(ip_objetivo, dt_inicio, dt_fin)

            with col_btn1:
                ejecutar_reporte = st.button("📊 GENERAR Y ARCHIVAR REPORTE DIRECTO EN BD", use_container_width=True, type="secondary", key="btn_run_report_gray")

            if ejecutar_reporte:
                if not datos_muestras:
                    st.warning(f"⚠️ Telemetría no disponible para `{serv_seleccionado}` en este rango temporal.")
                else:
                    nombre_base_archivo = f"reporte_{s_prefix}_{serv_info['nombre_alias']}_{fecha_i.strftime('%Y%m%d')}"

                    # --- 1. GENERACIÓN DEL REPORTE PDF (ESTILIZADO BANCO CARONÍ) ---
                    try:
                        pdf = PDF()
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 11)
                        pdf.cell(0, 7, f"REPORTE: {sensor_general.upper()} - {reporte_especifico.upper()}", 0, 1)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(50, 6, f"Servidor Objetivo: {serv_info['nombre_alias']} ({ip_objetivo})", 0, 1)
                        pdf.cell(50, 6, f"Rango Temporal: {fecha_i.strftime('%d/%m/%Y')} al {fecha_f.strftime('%d/%m/%Y')}", 0, 1)
                        pdf.cell(50, 6, f"Analista Emisor: {nombre_analista}", 0, 1)
                        pdf.ln(5)

                        # --- CONFIGURACIÓN DE COLORES DE CABECERA (AZUL CORPORATIVO) ---
                        pdf.set_fill_color(0, 51, 102)   # #003366
                        pdf.set_text_color(255, 255, 255) # Blanco
                        pdf.set_draw_color(180, 180, 180) # Bordes Gris Suave
                        pdf.set_font("Arial", "B", 9)
                        
                        pdf.cell(40, 7, "Fecha Registro", 1, 0, "C", True)

                        # Cabeceras adaptadas dinámicamente a la BD para los 6 discos
                        if s_prefix == "RAM":
                            if "Disponible (GB)" in reporte_especifico:
                                pdf.cell(145, 7, "RAM Disponible (GB)", 1, 1, "C", True)
                            elif "Disponible %" in reporte_especifico:
                                pdf.cell(145, 7, "RAM Disponible %", 1, 1, "C", True)
                            else:
                                pdf.cell(50, 7, "RAM Total (GB)", 1, 0, "C", True)
                                pdf.cell(50, 7, "RAM Disponible (GB)", 1, 0, "C", True)
                                pdf.cell(45, 7, "RAM Disponible %", 1, 1, "C", True)
                        elif "DISCO" in s_prefix and num_disco_activo:
                            letra_activa = letras_discos[num_disco_activo]
                            if "Libre (GB)" in reporte_especifico:
                                pdf.cell(145, 7, f"Disco {letra_activa} Libre (GB)", 1, 1, "C", True)
                            elif "Libre %" in reporte_especifico:
                                pdf.cell(145, 7, f"Disco {letra_activa} Libre %", 1, 1, "C", True)
                            else:
                                pdf.cell(50, 7, f"Disco {letra_activa} Total (GB)", 1, 0, "C", True)
                                pdf.cell(50, 7, f"Disco {letra_activa} Libre (GB)", 1, 0, "C", True)
                                pdf.cell(45, 7, f"Disco {letra_activa} Libre %", 1, 1, "C", True)
                        elif s_prefix == "CPU":
                            pdf.cell(145, 7, "Consumo CPU %", 1, 1, "C", True)
                        elif s_prefix == "LATENCIA":
                            pdf.cell(145, 7, "Latencia de Respuesta (ms)", 1, 1, "C", True)
                        else: # INTEGRAL GLOBAL
                            pdf.cell(30, 7, "CPU %", 1, 0, "C", True)
                            pdf.cell(40, 7, "RAM Disp (GB)", 1, 0, "C", True)
                            pdf.cell(40, 7, f"D. {letras_discos[1]} Lib (GB)", 1, 0, "C", True)
                            pdf.cell(35, 7, "Latencia ms", 1, 1, "C", True)

                        # --- RENDERIZADO DE FILAS CON EFECTO CEBRA ---
                        pdf.set_text_color(0, 0, 0) # Volver a texto negro
                        pdf.set_font("Arial", "", 9)
                        
                        for idx, r in enumerate(datos_muestras[:40]):
                            # Alternar fondo gris claro en las filas pares
                            fila_cebra = (idx % 2 == 0)
                            if fila_cebra:
                                pdf.set_fill_color(242, 242, 242) # #F2F2F2
                            else:
                                pdf.set_fill_color(255, 255, 255) # Blanco
                                
                            f_text = r['fecha_registro'].strftime("%d/%m/%Y %H:%M") if hasattr(r['fecha_registro'], 'strftime') else str(r['fecha_registro'])
                            pdf.cell(40, 6, f_text, 1, 0, "C", True)
                            
                            if s_prefix == "RAM":
                                if "Disponible (GB)" in reporte_especifico:
                                    pdf.cell(145, 6, f"{r.get('val_ram_disponible_gb', 0.0)} GB", 1, 1, "C", True)
                                elif "Disponible %" in reporte_especifico:
                                    pdf.cell(145, 6, f"{r.get('val_ram_disponible_pct', 0.0)} %", 1, 1, "C", True)
                                else:
                                    pdf.cell(50, 6, f"{r.get('val_ram_total_gb', 0.0)} GB", 1, 0, "C", True)
                                    pdf.cell(50, 6, f"{r.get('val_ram_disponible_gb', 0.0)} GB", 1, 0, "C", True)
                                    pdf.cell(45, 6, f"{r.get('val_ram_disponible_pct', 0.0)} %", 1, 1, "C", True)
                            elif "DISCO" in s_prefix and num_disco_activo:
                                d_tot = r.get(f'val_disco_{num_disco_activo}_total_gb', 0.0)
                                d_lib = r.get(f'val_disco_{num_disco_activo}_libres_gb', 0.0)
                                d_pct = r.get(f'val_disco_{num_disco_activo}_pct_libre', 0.0)
                                if "Libre (GB)" in reporte_especifico:
                                    pdf.cell(145, 6, f"{d_lib} GB", 1, 1, "C", True)
                                elif "Libre %" in reporte_especifico:
                                    pdf.cell(145, 6, f"{d_pct} %", 1, 1, "C", True)
                                else:
                                    pdf.cell(50, 6, f"{d_tot} GB", 1, 0, "C", True)
                                    pdf.cell(50, 6, f"{d_lib} GB", 1, 0, "C", True)
                                    pdf.cell(45, 6, f"{d_pct} %", 1, 1, "C", True)
                            elif s_prefix == "CPU":
                                pdf.cell(145, 6, f"{r.get('val_cpu', 0.0)} %", 1, 1, "C", True)
                            elif s_prefix == "LATENCIA":
                                pdf.cell(145, 6, f"{r.get('val_latencia', 0.0)} ms", 1, 1, "C", True)
                            else:
                                pdf.cell(30, 6, f"{r.get('val_cpu', 0.0)}%", 1, 0, "C", True)
                                pdf.cell(40, 6, f"{r.get('val_ram_disponible_gb', 0.0)} GB", 1, 0, "C", True)
                                pdf.cell(40, 6, f"{r.get('val_disco_1_libres_gb', 0.0)} GB", 1, 0, "C", True)
                                pdf.cell(35, 6, f"{r.get('val_latencia', 0.0)} ms", 1, 1, "C", True)

                        pdf_buffer = io.BytesIO()
                        pdf.output(pdf_buffer)
                        bytes_pdf = pdf_buffer.getvalue()
                        kb_size_pdf = round(len(bytes_pdf) / 1024.0, 2)
                        
                        guardar_reporte_archivado(f"{nombre_base_archivo}.pdf", "PDF", ip_objetivo, bytes_pdf, usuario_id, kb_size_pdf)
                    except Exception as e_pdf:
                        st.error(f"Error generando PDF: {e_pdf}")

                    # --- 2. GENERACIÓN DEL REPORTE CSV ---
                    try:
                        if s_prefix == "RAM":
                            columnas = ["FECHA_REGISTRO", "RAM_TOTAL_GB", "RAM_DISPONIBLE_GB", "RAM_DISPONIBLE_PCT"]
                        elif "DISCO" in s_prefix and num_disco_activo:
                            l_act = letras_discos[num_disco_activo]
                            columnas = ["FECHA_REGISTRO", f"DISCO_{l_act}_TOTAL_GB", f"DISCO_{l_act}_LIBRE_GB", f"DISCO_{l_act}_LIBRE_PCT"]
                        elif s_prefix == "CPU":
                            columnas = ["FECHA_REGISTRO", "CPU_PCT"]
                        elif s_prefix == "LATENCIA":
                            columnas = ["FECHA_REGISTRO", "LATENCIA_MS"]
                        else:
                            columnas = ["FECHA_REGISTRO", "CPU_PCT", "RAM_TOTAL", "RAM_LIBRE_GB", "RAM_LIBRE_PCT", f"D_{letras_discos[1]}_LIBRE_GB", "LATENCIA"]

                        lineas_csv = [",".join(columnas)]
                        for r in datos_muestras:
                            f_t = r['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r['fecha_registro'], 'strftime') else str(r['fecha_registro'])
                            
                            if s_prefix == "RAM":
                                row_str = f"{f_t},{r.get('val_ram_total_gb',0.0)},{r.get('val_ram_disponible_gb',0.0)},{r.get('val_ram_disponible_pct',0.0)}"
                            elif "DISCO" in s_prefix and num_disco_activo:
                                d_tot = r.get(f'val_disco_{num_disco_activo}_total_gb', 0.0)
                                d_lib = r.get(f'val_disco_{num_disco_activo}_libres_gb', 0.0)
                                d_pct = r.get(f'val_disco_{num_disco_activo}_pct_libre', 0.0)
                                row_str = f"{f_t},{d_tot},{d_lib},{d_pct}"
                            elif s_prefix == "CPU":
                                row_str = f"{f_t},{r.get('val_cpu',0.0)}"
                            elif s_prefix == "LATENCIA":
                                row_str = f"{f_t},{r.get('val_latencia',0.0)}"
                            else:
                                row_str = f"{f_t},{r.get('val_cpu',0.0)},{r.get('val_ram_total_gb',0.0)},{r.get('val_ram_disponible_gb',0.0)},{r.get('val_ram_disponible_pct',0.0)},{r.get('val_disco_1_libres_gb',0.0)},{r.get('val_latencia',0.0)}"
                            
                            lineas_csv.append(row_str)

                        bytes_csv = "\n".join(lineas_csv).encode("utf-8")
                        kb_size_csv = round(len(bytes_csv) / 1024.0, 2)
                        
                        guardar_reporte_archivado(f"{nombre_base_archivo}.csv", "CSV", ip_objetivo, bytes_csv, usuario_id, kb_size_csv)
                        st.success(f"📦 **Reporte generado:** Se archivaron las variables de `{reporte_especifico}` con éxito en el histórico de la base de datos.")
                    except Exception as e_csv:
                        st.error(f"Error generando CSV: {e_csv}")

    # =====================================================================
    # PESTAÑA 2: REPOSITORIO HISTÓRICO FILTRADO POR EL TOKEN GENERAL
    # =====================================================================
    with tab2:
        st.markdown(f"#### 📜 Histórico Filtrado por Sensor General: `{sensor_general}`")
        
        lista_historica = listar_reportes_archivados_filtrado(ip_objetivo, s_prefix)
        
        if not lista_historica:
            st.info(f"💡 No hay reportes archivados de la categoría `{sensor_general}` para este nodo de infraestructura.")
        else:
            st.markdown(
                '<div style="background-color:#003366; color:white; padding:10px; border-radius:4px; font-weight:bold; font-size:13px; font-family:Arial; display:flex; align-items:center;">'
                '<div style="flex:3;">Nombre del Archivo Guardado</div>'
                '<div style="flex:1.2; text-align:center;">Formato</div>'
                '<div style="flex:1.2; text-align:center;">Tamaño</div>'
                '<div style="flex:2.5; text-align:center;">Fecha de Almacenamiento</div>'
                '<div style="flex:2.2; text-align:center;">Generado Por (Analista)</div>'
                '<div style="flex:1.8; text-align:center;">Acción</div>'
                '</div>', unsafe_allow_html=True
            )

            st.markdown(
                '<style>'
                '.badge-pdf { background-color: #b30000; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size:11px; }'
                '.badge-csv { background-color: #1b5e20; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size:11px; }'
                '</style>', unsafe_allow_html=True
            )

            for item in lista_historica:
                fecha_str = item['fecha_generacion'].strftime("%Y-%m-%d %H:%M:%S") if hasattr(item['fecha_generacion'], 'strftime') else str(item['fecha_generacion'])
                badge_class = "badge-pdf" if item['formato'] == "PDF" else "badge-csv"
                analista_nombre = item['registrado_por'] if item['registrado_por'] else "Sistema"
                
                st.markdown(
                    f'<div style="background-color:#ffffff; border-bottom:1px solid #ddd; padding:12px 10px; font-size:12px; font-family:Arial; display:flex; align-items:center; margin-bottom: 2px;">'
                    f'<div style="flex:3; font-weight:bold; color:#111;">🗃️ {item["nombre_archivo"]}</div>'
                    f'<div style="flex:1.2; text-align:center;"><span class="{badge_class}">{item["formato"]}</span></div>'
                    f'<div style="flex:1.2; text-align:center; color:#444;">{item["tamanio_kb"]} KB</div>'
                    f'<div style="flex:2.5; text-align:center; color:#444; font-family:monospace;">{fecha_str}</div>'
                    f'<div style="flex:2.2; text-align:center; color:#003366; font-weight:500;">👤 {analista_nombre}</div>'
                    f'<div style="flex:1.8; text-align:center;"></div>'
                    f'</div>', unsafe_allow_html=True
                )
                
                with st.container():
                    reporte_blob = descargar_contenido_blob(item['id'])
                    if reporte_blob:
                        st.download_button(
                            label=f"📥 Abrir {item['formato']}",
                            data=bytes(reporte_blob),
                            file_name=item['nombre_archivo'],
                            mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                            key=f"dl_final_{item['id']}",
                            use_container_width=True
                        )