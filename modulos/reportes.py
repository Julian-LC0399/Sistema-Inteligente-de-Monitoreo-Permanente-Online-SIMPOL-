import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import base64
import io

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()} | Confidencial Banco Caroní", 0, 0, "C")

def archivar_reporte_en_bd(bin_data, nombre, formato, user_id):
    """Guarda el binario del reporte para auditoría interna"""
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            tamanio = len(bin_data) / 1024 
            query = """
                INSERT INTO reportes_archivados 
                (nombre_archivo, formato, contenido, usuario_id, tamanio_kb) 
                VALUES (%s, %s, %s, %s, %s)
            """
            try:
                cursor.execute(query, (nombre, formato, bin_data, user_id, tamanio))
                conn.commit()
            except:
                st.info("Nota: Reporte generado pero no archivado (Tabla 'reportes_archivados' pendiente).")
            conn.close()
    except Exception as e:
        pass

def mostrar_pantalla(user_actual, user_id):
    """Recibe user_actual y user_id desde app.py para evitar el TypeError"""
    
    # --- ESTILO CORPORATIVO PARA EL BOTÓN ---
    st.markdown("""
        <style>
            div.stButton > button:first-child {
                background-color: #003366;
                color: white;
                border-radius: 5px;
                border: 2px solid #002244;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            div.stButton > button:first-child:hover {
                background-color: #00509d;
                border-color: #00509d;
                color: #ffffff;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366;">📊 Centro de Reportes y Auditoría</h2>', unsafe_allow_html=True)
    st.write(f"Operador responsable: **{user_actual}**")

    with st.container(border=True):
        st.subheader("Configuración del Reporte")
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Fecha Inicio", datetime.now() - timedelta(days=7))
        f_f = c2.date_input("Fecha Fin", datetime.now())
        
        # El botón ahora tomará el estilo definido arriba
        if st.button("🚀 GENERAR Y ARCHIVAR REPORTES", use_container_width=True):
            try:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                dt_i = datetime.combine(f_i, time.min)
                dt_f = datetime.combine(f_f, time.max)

                query = "SELECT * FROM monitoreo WHERE fecha_registro BETWEEN %s AND %s ORDER BY fecha_registro DESC"
                cursor.execute(query, (dt_i, dt_f))
                datos = cursor.fetchall()
                conn.close()

                if not datos:
                    st.warning("No se encontraron registros para este rango de fechas.")
                else:
                    # --- GENERACIÓN DE CSV ---
                    output_csv = io.StringIO()
                    output_csv.write("Fecha,CPU %,RAM %,Estado\n")
                    for r in datos:
                        fila = f"{r['fecha_registro']},{r['uso_cpu']},{r['uso_ram']},{r['estado_sistema']}\n"
                        output_csv.write(fila)
                    
                    csv_binario = output_csv.getvalue().encode('utf-8')
                    nombre_csv = f"SIMPOL_{f_i}.csv"
                    archivar_reporte_en_bd(csv_binario, nombre_csv, 'CSV', user_id)

                    # --- GENERACIÓN DE PDF ---
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, f"Análisis de Telemetría: {f_i} al {f_f}", 0, 1)
                    
                    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
                    pdf.cell(50, 10, "Fecha", 1, 0, "C", True)
                    pdf.cell(30, 10, "CPU %", 1, 0, "C", True)
                    pdf.cell(30, 10, "RAM %", 1, 0, "C", True)
                    pdf.cell(80, 10, "Estado", 1, 1, "C", True)

                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    for r in datos:
                        pdf.cell(50, 8, str(r['fecha_registro']), 1)
                        pdf.cell(30, 8, f"{r['uso_cpu']}%", 1, 0, "C")
                        pdf.cell(30, 8, f"{r['uso_ram']}%", 1, 0, "C")
                        pdf.cell(80, 8, str(r['estado_sistema']), 1, 1)

                    pdf_binario = pdf.output(dest='S').encode('latin-1')
                    nombre_pdf = f"SIMPOL_{f_i}.pdf"
                    archivar_reporte_en_bd(pdf_binario, nombre_pdf, 'PDF', user_id)

                    st.success("✅ Archivos listos para descarga.")
                    
                    col1, col2 = st.columns(2)
                    col1.download_button("⬇️ Descargar CSV", data=csv_binario, file_name=nombre_csv, mime="text/csv")
                    col2.download_button("⬇️ Descargar PDF", data=pdf_binario, file_name=nombre_pdf, mime="application/pdf")

            except Exception as e:
                st.error(f"Error técnico en reportes: {e}")