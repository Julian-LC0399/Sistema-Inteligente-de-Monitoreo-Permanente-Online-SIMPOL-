import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import io
import traceback

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte de Auditoria de Infraestructura Multi-Sensor", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Pagina {self.page_no()} | Confidencial", 0, 0, "C")

def archivar_reporte_en_bd(bin_data, nombre, formato, user_id):
    """Guarda el archivo en la base de datos de manera conforme."""
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            calc_kb = len(bin_data) / 1024.0
            tamanio_sanitizado = f"{calc_kb:.2f}"
            
            datos_finales = bytes(bin_data)
            
            id_limpio = None
            if user_id:
                try: id_limpio = int(float(str(user_id).strip()))
                except: id_limpio = None
            
            query = """
                INSERT INTO reportes_archivados 
                (nombre_archivo, formato, contenido, usuario_id, tamanio_kb) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, formato, datos_finales, id_limpio, tamanio_sanitizado))
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error interno en Query de Archivación ({formato}): {e}\n")
    return False

def obtener_historico_reportes():
    """Extrae la metadata histórica de forma segura protegiendo la UI (Excluye el BLOB pesado)."""
    reportes = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, nombre_archivo, formato, tamanio_kb, fecha_generacion, usuario_id 
                FROM reportes_archivados 
                ORDER BY fecha_generacion DESC 
                LIMIT 10
            """
            cursor.execute(query)
            reportes = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error leyendo histórico de BD: {e}\n")
    return reportes

def descargar_contenido_blob(reporte_id):
    """
    EXTRACTOR BAJO DEMANDA: Busca el contenido binario LONGBLOB de un archivo específico
    y lo sanea de bytearray a bytes puros para que Streamlit pueda procesarlo sin colapsar.
    """
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_archivados WHERE id = %s"
            cursor.execute(query, (reporte_id,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultado and resultado['contenido']:
                return bytes(resultado['contenido'])
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error al extraer contenido BLOB ID {reporte_id}: {e}\n")
    return None

def mostrar_pantalla(user_actual, user_id):
    if "rep_listo" not in st.session_state:
        st.session_state["rep_listo"] = False
        st.session_state["data_csv"] = None
        st.session_state["data_pdf"] = None
        st.session_state["name_csv"] = ""
        st.session_state["name_pdf"] = ""

    st.markdown('<h2 style="color:#003366;">📊 Centro de Reportes y Auditoría</h2>', unsafe_allow_html=True)
    st.write(f"Analista en sesión: **{user_actual}**")

    # =====================================================================
    # SECCIÓN 1: PARÁMETROS Y GENERADOR DE REPORTES
    # =====================================================================
    with st.container(border=True):
        st.subheader("Parámetros del Informe")
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Desde", datetime.now() - timedelta(days=7), key="rep_date_ini")
        f_f = c2.date_input("Hasta", datetime.now(), key="rep_date_fin")
        
        area_descarga = st.empty()
        
        if st.button("🚀 GENERAR EXPEDIENTE INTEGRAL", use_container_width=True, key="btn_gen_reporte"):
            conn = None
            try:
                conn = conectar_bd()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    dt_i = datetime.combine(f_i, time.min)
                    dt_f = datetime.combine(f_f, time.max)

                    # === SOLUCIÓN RECOMENDADA: Extracción Multidisco Sanada ===
                    query = """
                        SELECT fecha_registro, ip_servidor, val_cpu, val_ram, 
                               val_disco_1, val_disco_2, val_disco_3, val_disco_4, val_disco_5, 
                               val_red, val_latencia, estado_sistema 
                        FROM monitoreo 
                        WHERE fecha_registro BETWEEN %s AND %s 
                        ORDER BY fecha_registro DESC
                        LIMIT 5000
                    """
                    cursor.execute(query, (dt_i, dt_f))
                    datos = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    conn = None
                else:
                    st.error("No se pudo conectar con la base de datos de infraestructura.")
                    return

                if not datos:
                    st.warning("⚠️ No existen registros de telemetría para el rango seleccionado.")
                else:
                    # --- CONSTRUCCIÓN DEL DATASTREAM CSV MULTIDISCO ---
                    output_csv = io.StringIO()
                    output_csv.write("Fecha,IP Servidor,CPU %,RAM %,Disco 1 %,Disco 2 %,Disco 3 %,Disco 4 %,Disco 5 %,Red Mbps,Latencia ms,Estado Sistema\n")
                    for r in datos:
                        output_csv.write(
                            f"{r['fecha_registro']},{r['ip_servidor']},{r['val_cpu']},{r['val_ram']},"
                            f"{r['val_disco_1']},{r['val_disco_2']},{r['val_disco_3']},{r['val_disco_4']},{r['val_disco_5']},"
                            f"{r['val_red']},{r['val_latencia']},{r['estado_sistema']}\n"
                        )
                    
                    csv_binario = output_csv.getvalue().encode('utf-8', errors='ignore')
                    timestamp_actual = datetime.now().strftime('%d%m%y_%H%M')
                    nombre_csv = f"Reporte_SIMPOL_{timestamp_actual}.csv"

                    # --- CONSTRUCCIÓN DEL EXPEDIENTE PDF ---
                    pdf = PDF(orientation='L', unit='mm', format='A4')
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, f"Periodo de Auditoria: {f_i} al {f_f}", 0, 1)
                    pdf.cell(0, 8, f"Generado por el Analista ID: {user_id} ({user_actual})", 0, 1)
                    pdf.ln(4)
                    
                    pdf.set_fill_color(0, 51, 102)
                    pdf.set_text_color(255, 255, 255)
                    
                    # Ajuste de anchos para acomodar las 5 columnas de discos sin desbordar el A4 Horizontal (297mm)
                    cols = [
                        ("Fecha/Hora", 40), ("IP Servidor", 30), ("CPU", 13), 
                        ("RAM", 13), ("D1", 12), ("D2", 12), ("D3", 12), 
                        ("D4", 12), ("D5", 12), ("RED", 16), ("LAT", 14), ("Estado Sistema", 40)
                    ]
                    for txt, w in cols:
                        pdf.cell(w, 8, txt, 1, 0, "C", True)
                    pdf.ln()

                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 8)
                    
                    for r in datos[:1000]:
                        pdf.cell(40, 7, str(r['fecha_registro']), 1)
                        pdf.cell(30, 7, str(r['ip_servidor']), 1)
                        pdf.cell(13, 7, f"{r['val_cpu']}%", 1, 0, "C")
                        pdf.cell(13, 7, f"{r['val_ram']}%", 1, 0, "C")
                        pdf.cell(12, 7, f"{r['val_disco_1']}%" if r['val_disco_1'] is not None else "-", 1, 0, "C")
                        pdf.cell(12, 7, f"{r['val_disco_2']}%" if r['val_disco_2'] is not None else "-", 1, 0, "C")
                        pdf.cell(12, 7, f"{r['val_disco_3']}%" if r['val_disco_3'] is not None else "-", 1, 0, "C")
                        pdf.cell(12, 7, f"{r['val_disco_4']}%" if r['val_disco_4'] is not None else "-", 1, 0, "C")
                        pdf.cell(12, 7, f"{r['val_disco_5']}%" if r['val_disco_5'] is not None else "-", 1, 0, "C")
                        pdf.cell(16, 7, f"{r['val_red']} Mb", 1, 0, "C")
                        pdf.cell(14, 7, f"{r['val_latencia']} ms", 1, 0, "C")
                        pdf.cell(40, 7, str(r['estado_sistema']), 1, 1, "C")

                    pdf_str = pdf.output(dest='S')
                    if isinstance(pdf_str, str):
                        pdf_binario = pdf_str.encode('latin-1', errors='ignore')
                    else:
                        pdf_binario = bytes(pdf_str)

                    nombre_pdf = f"Reporte_SIMPOL_{timestamp_actual}.pdf"

                    st.session_state["data_csv"] = csv_binario
                    st.session_state["data_pdf"] = pdf_binario
                    st.session_state["name_csv"] = nombre_csv
                    st.session_state["name_pdf"] = nombre_pdf
                    st.session_state["rep_listo"] = True

                    archivar_reporte_en_bd(csv_binario, nombre_csv, 'CSV', user_id)
                    archivar_reporte_en_bd(pdf_binario, nombre_pdf, 'PDF', user_id)

                    st.rerun()

            except Exception as e:
                st.error(f"⚠️ Error cargando sección 📄 Reportes. Revisa simpol_debug.log")
                with open("simpol_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"==================================================\n")
                    f.write(f"Error crítico en pantalla al presionar generar: {e}\n")
                    f.write(traceback.format_exc())
            finally:
                if conn:
                    try: conn.close()
                    except: pass

        if st.session_state["rep_listo"]:
            with area_descarga.container():
                st.markdown("---")
                st.success("✅ Expedientes de auditoría procesados correctamente con arquitectura multi-sensor.")
                st.info(f"💾 **Trazabilidad:** Analista {user_actual} (ID: {user_id})")
                
                d_col1, d_col2 = st.columns(2)
                d_col1.download_button(
                    label="⬇️ Descargar Excel (CSV)", 
                    data=st.session_state["data_csv"], 
                    file_name=st.session_state["name_csv"], 
                    mime="text/csv", 
                    key="dl_btn_csv_final_v3"
                )
                d_col2.download_button(
                    label="⬇️ Descargar Informe (PDF)", 
                    data=st.session_state["data_pdf"], 
                    file_name=st.session_state["name_pdf"], 
                    mime="application/pdf", 
                    key="dl_btn_pdf_final_v3"
                )

    # =====================================================================
    # SECCIÓN 2: HISTORIAL Y RECUPERACIÓN DE REPORTES ARCHIVADOS
    # =====================================================================
    st.markdown('<h3 style="color:#003366;">📜 Historial de Reportes Archivados (Últimos 10)</h3>', unsafe_allow_html=True)
    
    historico = obtener_historico_reportes()
    if not historico:
        st.write("No hay reportes archivados en el histórico de auditoría.")
    else:
        for item in historico:
            with st.container(border=True):
                col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
                col_a.write(f"📄 **Archivo:** `{item['nombre_archivo']}`")
                col_b.write(f"🔹 **Formato:** {item['formato']}")
                
                fecha_f = item['fecha_generacion'].strftime('%d/%m/%Y %H:%M') if item['fecha_generacion'] else 'N/A'
                col_c.write(f"⏱️ **Generado:** {fecha_f}")
                
                mime_tipo = "text/csv" if item['formato'] == "CSV" else "application/pdf"
                datos_archivo = descargar_contenido_blob(item['id'])
                
                if datos_archivo:
                    col_d.download_button(
                        label="📥 Descargar",
                        data=datos_archivo,
                        file_name=item['nombre_archivo'],
                        mime=mime_tipo,
                        key=f"btn_hist_{item['id']}" 
                    )
                else:
                    col_d.error("No disponible")