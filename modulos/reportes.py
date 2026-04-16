import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import base64
import io

class PDF(FPDF):
    def header(self):
        try:
            self.image('logo-banco.jpg', 10, 8, 33) 
        except:
            pass
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(40) 
        self.cell(0, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()} | Confidencial Banco Caroní", 0, 0, "C")

def archivar_reporte_en_bd(bin_data, nombre, formato, user_id):
    """Guarda el binario del reporte en la tabla de auditoría para el banco"""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        tamanio = len(bin_data) / 1024 
        query = """
            INSERT INTO reportes_archivados 
            (nombre_archivo, formato, contenido, usuario_id, tamanio_kb) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (nombre, formato, bin_data, user_id, tamanio))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ Error al archivar reporte en servidor: {e}")

def mostrar_pantalla(user_actual, user_id):
    st.markdown('<h2 style="color:#003366;">📊 Centro de Reportes y Auditoría</h2>', unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("Configuración del Reporte")
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Fecha Inicio", datetime.now() - timedelta(days=7))
        f_f = c2.date_input("Fecha Fin", datetime.now())
        
        if st.button("🚀 GENERAR Y ARCHIVAR REPORTES (PDF/CSV)", use_container_width=True):
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
                    st.warning("No se encontraron registros para el rango seleccionado.")
                else:
                    # --- GENERACIÓN DE CSV (NATIVO SIN PANDAS) ---
                    output_csv = io.StringIO()
                    output_csv.write("ID,Fecha_Registro,ID_Sensor,CPU_Porcentaje,RAM_Porcentaje,Estado\n")
                    for r in datos:
                        fila = f"{r['id']},{r['fecha_registro']},{r['id_sensor']},{r['uso_cpu']},{r['uso_ram']},{r['estado_sistema']}\n"
                        output_csv.write(fila)
                    
                    csv_binario = output_csv.getvalue().encode('utf-8')
                    nombre_csv = f"SIMPOL_DATA_{f_i}_al_{f_f}.csv"
                    archivar_reporte_en_bd(csv_binario, nombre_csv, 'CSV', user_id)

                    # --- GENERACIÓN DE PDF ---
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, f"Análisis de Telemetría: {f_i} al {f_f}", 0, 1)
                    
                    # Encabezados tabla PDF
                    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
                    pdf.cell(45, 10, "Fecha", 1, 0, "C", True)
                    pdf.cell(30, 10, "CPU %", 1, 0, "C", True)
                    pdf.cell(30, 10, "RAM %", 1, 0, "C", True)
                    pdf.cell(85, 10, "Estado", 1, 1, "C", True)

                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    for r in datos:
                        pdf.cell(45, 8, str(r['fecha_registro']), 1)
                        pdf.cell(30, 8, f"{r['uso_cpu']}%", 1, 0, "C")
                        pdf.cell(30, 8, f"{r['uso_ram']}%", 1, 0, "C")
                        pdf.cell(85, 8, r['estado_sistema'], 1, 1)

                    pdf_binario = pdf.output(dest='S').encode('latin-1')
                    nombre_pdf = f"SIMPOL_REPORTE_{f_i}_al_{f_f}.pdf"
                    archivar_reporte_en_bd(pdf_binario, nombre_pdf, 'PDF', user_id)

                    st.success("✅ Archivos generados y respaldados en la base de datos.")
                    
                    col1, col2 = st.columns(2)
                    col1.download_button("⬇️ Descargar CSV", data=csv_binario, file_name=nombre_csv, mime="text/csv")
                    col2.download_button("⬇️ Descargar PDF", data=pdf_binario, file_name=nombre_pdf, mime="application/pdf")

            except Exception as e:
                st.error(f"Error en el proceso: {e}")