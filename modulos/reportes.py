import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime

class PDF(FPDF):
    def header(self):
        # Fondo y Título
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "C")
        
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

def generar_reporte_pdf(datos):
    pdf = PDF()
    pdf.add_page()
    
    # Encabezado de tabla
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 10)
    
    pdf.cell(45, 10, "Fecha/Hora", 1, 0, "C", True)
    pdf.cell(40, 10, "Sensor ID", 1, 0, "C", True) # Etiqueta actualizada
    pdf.cell(25, 10, "CPU %", 1, 0, "C", True)
    pdf.cell(25, 10, "RAM %", 1, 0, "C", True)
    pdf.cell(55, 10, "Estado Sistema", 1, 1, "C", True)

    # Datos de la tabla
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 9)
    
    for row in datos:
        pdf.cell(45, 8, row['fecha_registro'].strftime('%d/%m/%y %H:%M:%S'), 1)
        # CAMBIO: nombre_csu -> id_sensor
        pdf.cell(40, 8, f"SENSOR-{row['id_sensor']}", 1, 0, "C")
        pdf.cell(25, 8, f"{row['uso_cpu']}%", 1, 0, "C")
        pdf.cell(25, 8, f"{row['uso_ram']}%", 1, 0, "C")
        pdf.cell(55, 8, row['estado_sistema'], 1, 1)
    
    return pdf.output(dest='S').encode('latin-1')

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>📊 Reportes Gerenciales</h2>", unsafe_allow_html=True)
    
    st.info("Este módulo exporta los últimos 50 registros de telemetría capturados por los agentes.")

    if st.button("📥 GENERAR Y DESCARGAR PDF", use_container_width=True):
        try:
            conn = conectar_bd()
            cursor = conn.cursor(dictionary=True)
            # Consulta alineada a simpol.sql
            cursor.execute("SELECT * FROM monitoreo ORDER BY fecha_registro DESC LIMIT 50")
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if datos:
                pdf_bytes = generar_reporte_pdf(datos)
                st.download_button(
                    label="💾 Guardar Archivo PDF",
                    data=pdf_bytes,
                    file_name=f"reporte_simpol_{datetime.now().strftime('%Y%md')}.pdf",
                    mime="application/pdf"
                )
                st.success("Reporte generado con éxito.")
            else:
                st.warning("No hay datos históricos para generar el reporte.")
        except Exception as e:
            st.error(f"Error al generar reporte: {e}")