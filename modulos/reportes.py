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
        self.set_text_color(0, 51, 102) # Azul Corporativo
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte de Servidor", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE PERSISTENCIA Y CONSULTA A BASE DE DATOS
# =====================================================================
def archivar_reporte_corporativo(bin_data, nombre, formato, user_id):
    """Guarda el reporte binario generado en la tabla 'reportes_archivados'."""
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            calc_kb = len(bin_data) / 1024.0
            tamanio_str = f"{calc_kb:.2f} KB"
            
            uid_limpio = None
            if user_id:
                try: uid_limpio = int(float(str(user_id).strip()))
                except: uid_limpio = None
                
            query = """
                INSERT INTO reportes_archivados (nombre_archivo, formato, contenido, usuario_id, tamanio_kb) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, formato, bytes(bin_data), uid_limpio, tamanio_str))
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error archivando reporte ({formato}): {e}\n")
    return False

def obtener_historial_reportes():
    """Recupera el listado optimizado uniendo r.usuario_id con la columna real u.id de usuarios."""
    conn = None
    resultado = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT r.id, r.nombre_archivo, r.formato, r.tamanio_kb, r.fecha_generacion, 
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
    """Extrae bajo demanda el archivo binario LONGBLOB de un reporte guardado."""
    conn = None
    blob_data = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_archivados WHERE id = %s"
            cursor.execute(query, (int(reporte_id),))
            fila = cursor.fetchone()
            if fila:
                blob_data = fila["contenido"]
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error descargando BLOB ID {reporte_id}: {e}\n")
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

    st.markdown('<h2 style="color:#003366;">📋 Centro de Reportes Gerenciales</h2>', unsafe_allow_html=True)
    
    # CORREGIDO: Se removió por completo la palabra admin y las comillas invertidas vacías
    st.markdown(f"👤 **Analista de Infraestructura:** {nombre_analista}", unsafe_allow_html=True)
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
        cursor.execute("SELECT ip, nombre_alias, sistema_operativo FROM servidores WHERE estado_monitoreo = 1 ORDER BY nombre_alias ASC")
        servidores = cursor.fetchall()
        cursor.close()
        conn.close()

        if not servidores:
            st.warning("⚠️ No se registran nodos de servidores activos en la configuración actual.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']}) - {s['sistema_operativo']}": s for s in servidores}
        seleccion = st.selectbox("Seleccione Servidor Objetivo:", list(opciones.keys()), key="rep_sb_servidor")
        srv_info = opciones[seleccion]
        ip_sel = srv_info['ip']

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fecha_inicio = st.date_input("Fecha Inicial", value=datetime.now() - timedelta(days=7), key="rep_dt_inicio")
        with col_d2:
            fecha_fin = st.date_input("Fecha Final", value=datetime.now(), key="rep_dt_fin")

        if fecha_inicio > fecha_fin:
            st.error("❌ Restricción Temporal: La fecha inicial no puede superar a la fecha final.")
            return

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📊 PROCESAR Y ARCHIVAR REPORTES", use_container_width=True, key="btn_procesar_reporte_maestro"):
            try:
                dt_desde = datetime.combine(fecha_inicio, time.min)
                dt_hasta = datetime.combine(fecha_fin, time.max)

                conn_data = conectar_bd()
                cursor_data = conn_data.cursor(dictionary=True)
                
                query_monitoreo = """
                    SELECT fecha_registro, val_cpu, val_ram, 
                           val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, val_disco_6,
                           estado_servicio_1, estado_servicio_2, estado_servicio_3, estado_servicio_4, estado_servicio_5,
                           val_red, val_latencia, estado_sistema 
                    FROM monitoreo 
                    WHERE TRIM(ip_servidor) = %s AND fecha_registro BETWEEN %s AND %s
                    ORDER BY fecha_registro DESC
                """
                cursor_data.execute(query_monitoreo, (str(ip_sel).strip(), dt_desde, dt_hasta))
                registros = cursor_data.fetchall()
                cursor_data.close()
                conn_data.close()

                if not registros:
                    st.error(f"❌ Sin registros de telemetría para {srv_info['nombre_alias']} en el rango seleccionado.")
                    return

                tot_cpu, tot_ram, tot_red, tot_lat = 0.0, 0.0, 0.0, 0.0
                tot_discos = {i: 0.0 for i in range(1, 7)}
                tot_servicios = {i: 0 for i in range(1, 6)}
                conteo_muestras = len(registros)

                for r in registros:
                    tot_cpu += float(r['val_cpu'] or 0)
                    tot_ram += float(r['val_ram'] or 0)
                    tot_red += float(r['val_red'] or 0)
                    tot_lat += float(r['val_latencia'] or 0)
                    
                    for i in range(1, 7):
                        tot_discos[i] += float(r[f'val_disco_{i}'] or 0)
                        
                    for i in range(1, 6):
                        estado_actual = str(r[f'estado_servicio_{i}']).strip().upper()
                        tot_servicios[i] += 1 if estado_actual == 'ON' else 0

                p_cpu = tot_cpu / conteo_muestras
                p_ram = tot_ram / conteo_muestras
                p_red = tot_red / conteo_muestras
                p_lat = tot_lat / conteo_muestras
                
                p_discos = {i: tot_discos[i] / conteo_muestras for i in range(1, 7)}
                p_servicios = {i: (tot_servicios[i] / conteo_muestras) * 100 for i in range(1, 6)}

                ts_file = datetime.now().strftime('%Y%m%d_%H%M%S')

                # =============================================================
                # ENSAMBLAJE DEL REPORTE CSV CORPORATIVO
                # =============================================================
                out_csv = io.StringIO()
                out_csv.write("Fecha Registro,IP Servidor,CPU(%),RAM(GB),Disco1(GB),Disco2(GB),Disco3(GB),Disco4(GB),Disco5(GB),Disco6(GB),Svc1(Estado),Svc2(Estado),Svc3(Estado),Svc4(Estado),Svc5(Estado),Red(Mbs),Latencia(ms),Estado Sistema\n")
                
                for r in registros:
                    f_str = r['fecha_registro'].strftime('%Y-%m-%d %H:%M:%S') if r['fecha_registro'] else 'N/A'
                    out_csv.write(
                        f"{f_str},{ip_sel},{r['val_cpu']},{r['val_ram']},"
                        f"{r['val_disco_1']},{r['val_disco_2']},{r['val_disco_3']},{r['val_disco_4']},{r['val_disco_5']},{r['val_disco_6']},"
                        f"{r['estado_servicio_1']},{r['estado_servicio_2']},{r['estado_servicio_3']},{r['estado_servicio_4']},{r['estado_servicio_5']},"
                        f"{r['val_red']},{r['val_latencia']},{r['estado_sistema']}\n"
                    )
                
                bin_csv = out_csv.getvalue().encode('utf-8', errors='ignore')
                name_csv = f"Reporte_{ip_sel}_{ts_file}.csv"

                # =============================================================
                # ENSAMBLAJE DEL INFORME PDF (A4 HORIZONTAL)
                # =============================================================
                pdf = PDF(orientation='L', unit='mm', format='A4')
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, f"Filtro Desde: {fecha_inicio.strftime('%d/%m/%Y')} | Hasta: {fecha_fin.strftime('%d/%m/%Y')}", 0, 1)
                pdf.cell(0, 6, f"Servidor: {srv_info['nombre_alias']} ({ip_sel}) | S.O: {srv_info['sistema_operativo']}", 0, 1)
                pdf.cell(0, 6, f"Muestras Extraidas: {conteo_muestras} registros.", 0, 1)
                pdf.ln(5)

                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 6, "Resumen Basal de Medias Obtenidas", 0, 1)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 10)
                
                pdf.cell(65, 6, f"• Promedio Carga CPU: {p_cpu:.2f} %", 0, 0)
                pdf.cell(65, 6, f"• Promedio Tráfico Red: {p_red:.2f} Mb/s", 0, 1)
                pdf.cell(65, 6, f"• Promedio Consumo RAM: {p_ram:.2f} GB", 0, 0)
                pdf.cell(65, 6, f"• Promedio Latencia Nodo: {p_lat:.2f} ms", 0, 1)
                pdf.ln(3)

                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 5, "Disponibilidad Promedio en Discos:", 0, 1)
                pdf.set_font("Arial", "", 10)
                pdf.cell(45, 6, f"  Disco 1 (C:): {p_discos[1]:.2f} GB", 0, 0)
                pdf.cell(45, 6, f"  Disco 2 (F:): {p_discos[2]:.2f} GB", 0, 0)
                pdf.cell(45, 6, f"  Disco 3 (E:): {p_discos[3]:.2f} GB", 0, 1)
                pdf.cell(45, 6, f"  Disco 4 (D:): {p_discos[4]:.2f} GB", 0, 0)
                pdf.cell(45, 6, f"  Disco 5 (G:): {p_discos[5]:.2f} GB", 0, 0)
                pdf.cell(45, 6, f"  Disco 6 (H:): {p_discos[6]:.2f} GB", 0, 1)
                pdf.ln(3)

                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 5, "Persistencia Operacional de Servicios (% de tiempo Activo):", 0, 1)
                pdf.set_font("Arial", "", 10)
                pdf.cell(50, 6, f"  Servicio 1: {p_servicios[1]:.1f} %", 0, 0)
                pdf.cell(50, 6, f"  Servicio 2: {p_servicios[2]:.1f} %", 0, 0)
                pdf.cell(50, 6, f"  Servicio 3: {p_servicios[3]:.1f} %", 0, 1)
                pdf.cell(50, 6, f"  Servicio 4: {p_servicios[4]:.1f} %", 0, 0)
                pdf.cell(50, 6, f"  Servicio 5: {p_servicios[5]:.1f} %", 0, 1)
                pdf.ln(6)

                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                
                columnas_pdf = [
                    ("Fecha/Hora", 28), ("CPU", 10), ("RAM", 12), 
                    ("D1", 11), ("D2", 11), ("D3", 11), ("D4", 11), ("D5", 11), ("D6", 11),
                    ("S1", 9), ("S2", 9), ("S3", 9), ("S4", 9), ("S5", 9),
                    ("Tráfico Red", 18), ("Latencia", 15), ("Estado", 18)
                ]
                
                for t, w in columnas_pdf:
                    pdf.cell(w, 6, t, 1, 0, "C", True)
                pdf.ln()

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 7)
                
                for r in registros[:35]:
                    f_row = r['fecha_registro'].strftime('%d/%m %H:%M') if r['fecha_registro'] else 'N/A'
                    pdf.cell(28, 5, f_row, 1, 0, "C")
                    pdf.cell(10, 5, f"{r['val_cpu']}%", 1, 0, "C")
                    pdf.cell(12, 5, f"{r['val_ram']}G", 1, 0, "C")
                    
                    for i in range(1, 7):
                        pdf.cell(11, 5, f"{r[f'val_disco_{i}']}G", 1, 0, "C")
                        
                    for i in range(1, 6):
                        val_s_str = str(r[f'estado_servicio_{i}']).strip().upper()
                        status_svc_txt = "OK" if val_s_str == "ON" else "ERR"
                        pdf.cell(9, 5, status_svc_txt, 1, 0, "C")
                        
                    pdf.cell(18, 5, f"{r['val_red']}Mb", 1, 0, "C")
                    pdf.cell(15, 5, f"{r['val_latencia']}ms", 1, 0, "C")
                    pdf.cell(18, 5, str(r['estado_sistema']), 1, 1, "C")

                if len(registros) > 35:
                    pdf.ln(2)
                    pdf.set_font("Arial", "I", 8)
                    pdf.cell(0, 5, f"... (* Se han omitido {len(registros) - 35} filas adicionales en la vista impresa por razones de optimización).", 0, 1)

                pdf_out = pdf.output(dest='S')
                bin_pdf = pdf_out.encode('latin-1', errors='ignore') if isinstance(pdf_out, str) else bytes(pdf_out)
                name_pdf = f"Reporte_{ip_sel}_{ts_file}.pdf"

                st.session_state["rep_csv"] = bin_csv
                st.session_state["rep_pdf"] = bin_pdf
                st.session_state["rep_name_csv"] = name_csv
                st.session_state["rep_name_pdf"] = name_pdf
                st.session_state["rep_listo"] = True

                archivar_reporte_corporativo(bin_csv, name_csv, 'CSV', usuario_id)
                archivar_reporte_corporativo(bin_pdf, name_pdf, 'PDF', usuario_id)
                
                st.success("🎉 ¡Muestras consolidadas y archivadas en el historial del Banco Caroní!")
                st.rerun()

            except Exception as e:
                st.error("Fallo técnico al procesar las estructuras de datos.")
                with open("simpol_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Error procesando reportes.py: {e}\n")

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
                    blob_data = descargar_contenido_blob(item['id'])
                    if blob_data:
                        st.download_button(
                            label="📥 Descargar",
                            data=blob_data,
                            file_name=item['nombre_archivo'],
                            mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                            key=f"dl_corp_{item['id']}",
                            use_container_width=True
                        )
                    else:
                        st.caption("Vacío")
                        
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    analista = st.session_state.get("nombre_completo", "Analista Institucional")
    uid = st.session_state.get("id", 1)
    ulogin = st.session_state.get("usuario", "operador1")
    
    mostrar_pantalla(analista, uid, ulogin)