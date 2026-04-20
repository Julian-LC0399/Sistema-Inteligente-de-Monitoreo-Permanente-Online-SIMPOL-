import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import io

class PDF(FPDF):
    def header(self):
        # Logo o Título Institucional
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte de Auditoría de Infraestructura Multi-Sensor", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial Banco Caroní", 0, 0, "C")

def archivar_reporte_en_bd(bin_data, nombre, formato, user_id):
    """Guarda el registro del reporte para cumplimiento normativo."""
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
                st.info("Nota: Reporte generado. Pendiente registro en tabla 'reportes_archivados'.")
            conn.close()
    except:
        pass

def mostrar_pantalla(user_actual, user_id):
    st.markdown('<h2 style="color:#003366;">📊 Centro de Reportes y Auditoría</h2>', unsafe_allow_html=True)
    st.write(f"Analista en sesión: **{user_actual}**")

    with st.container(border=True):
        st.subheader("Parámetros del Informe")
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Desde", datetime.now() - timedelta(days=7))
        f_f = c2.date_input("Hasta", datetime.now())
        
        if st.button("🚀 GENERAR EXPEDIENTE INTEGRAL", use_container_width=True):
            try:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                dt_i = datetime.combine(f_i, time.min)
                dt_f = datetime.combine(f_f, time.max)

                # Query actualizada con las nuevas columnas val_xxx
                query = """
                    SELECT fecha_registro, ip_servidor, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema 
                    FROM monitoreo 
                    WHERE fecha_registro BETWEEN %s AND %s 
                    ORDER BY fecha_registro DESC
                """
                cursor.execute(query, (dt_i, dt_f))
                datos = cursor.fetchall()
                conn.close()

                if not datos:
                    st.warning("No existen registros de telemetría para el rango seleccionado.")
                else:
                    # --- GENERACIÓN DE CSV (Estructura de 5 sensores) ---
                    output_csv = io.StringIO()
                    output_csv.write("Fecha,IP,CPU %,RAM %,Disco %,Red Mbps,Latencia ms,Estado\n")
                    for r in datos:
                        fila = f"{r['fecha_registro']},{r['ip_servidor']},{r['val_cpu']},{r['val_ram']},{r['val_disco']},{r['val_red']},{r['val_latencia']},{r['estado_sistema']}\n"
                        output_csv.write(fila)
                    
                    csv_binario = output_csv.getvalue().encode('utf-8')
                    nombre_csv = f"Reporte_SIMPOL_{datetime.now().strftime('%d%m%y')}.csv"
                    archivar_reporte_en_bd(csv_binario, nombre_csv, 'CSV', user_id)

                    # --- GENERACIÓN DE PDF (Formato Horizontal para que quepa todo) ---
                    pdf = PDF(orientation='L', unit='mm', format='A4')
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(0, 10, f"Periodo de Auditoría: {f_i} al {f_f}", 0, 1)
                    
                    # Encabezados de tabla
                    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
                    pdf.cell(45, 10, "Fecha/Hora", 1, 0, "C", True)
                    pdf.cell(25, 10, "CPU", 1, 0, "C", True)
                    pdf.cell(25, 10, "RAM", 1, 0, "C", True)
                    pdf.cell(25, 10, "DISCO", 1, 0, "C", True)
                    pdf.cell(25, 10, "RED", 1, 0, "C", True)
                    pdf.cell(25, 10, "LAT", 1, 0, "C", True)
                    pdf.cell(50, 10, "Estado Sistema", 1, 1, "C", True)

                    # Datos
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
                    for r in datos:
                        pdf.cell(45, 8, str(r['fecha_registro']), 1)
                        pdf.cell(25, 8, f"{r['val_cpu']}%", 1, 0, "C")
                        pdf.cell(25, 8, f"{r['val_ram']}%", 1, 0, "C")
                        pdf.cell(25, 8, f"{r['val_disco']}%", 1, 0, "C")
                        pdf.cell(25, 8, f"{r['val_red']} Mb", 1, 0, "C")
                        pdf.cell(25, 8, f"{r['val_latencia']} ms", 1, 0, "C")
                        pdf.cell(50, 8, str(r['estado_sistema']), 1, 1, "C")

                    pdf_binario = pdf.output(dest='S').encode('latin-1', 'ignore')
                    nombre_pdf = f"Reporte_SIMPOL_{datetime.now().strftime('%d%m%y')}.pdf"
                    archivar_reporte_en_bd(pdf_binario, nombre_pdf, 'PDF', user_id)

                    st.success("✅ Documentos generados y archivados en la base de datos de auditoría.")
                    
                    c_d1, c_d2 = st.columns(2)
                    c_d1.download_button("⬇️ Descargar Excel (CSV)", data=csv_binario, file_name=nombre_csv, mime="text/csv")
                    c_d2.download_button("⬇️ Descargar Informe (PDF)", data=pdf_binario, file_name=nombre_pdf, mime="application/pdf")

            except Exception as e:
                st.error(f"Falla en motor de reportes: {e}")

if __name__ == "__main__":
    mostrar_pantalla("Analista Test", 1)