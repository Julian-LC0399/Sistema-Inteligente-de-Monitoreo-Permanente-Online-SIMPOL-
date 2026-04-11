import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Auditoría de Monitoreo | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
        self.ln(10)

def mostrar_pantalla():
    st.markdown("""
        <style>
            /* BOTÓN CON COLORES DEL BANCO CARONÍ */
            div.stButton > button {
                color: #ffffff !important;
                background-color: #003366 !important;
                border: 2px solid #003366 !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                height: 3em !important;
                transition: 0.3s;
            }
            div.stButton > button:hover {
                background-color: #00509d !important;
                border-color: #00509d !important;
            }
            [data-testid="stTable"] td { color: black !important; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
            [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366;'>📄 Centro de Reportes de Auditoría</h2>", unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2 = st.columns(2)
        f_i = col1.date_input("Fecha Inicial:", datetime.now() - timedelta(days=1))
        f_f = col2.date_input("Fecha Final:", datetime.now())

        if st.button("🔍 GENERAR REPORTE PDF"):
            dt_i = datetime.combine(f_i, time(0, 0, 0))
            dt_f = datetime.combine(f_f, time(23, 59, 59))
            
            try:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                # CORRECCIÓN: id_sensor en lugar de nombre_csu
                query = """
                    SELECT fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema 
                    FROM monitoreo 
                    WHERE fecha_registro >= %s AND fecha_registro <= %s
                    ORDER BY fecha_registro DESC, id DESC
                """
                cursor.execute(query, (dt_i, dt_f))
                datos = cursor.fetchall()
                
                if not datos:
                    st.warning("No se encontraron registros.")
                else:
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
                    pdf.cell(45, 10, "Fecha/Hora", 1, 0, "C", True)
                    pdf.cell(40, 10, "ID Sensor", 1, 0, "C", True)
                    pdf.cell(20, 10, "CPU %", 1, 0, "C", True)
                    pdf.cell(20, 10, "RAM %", 1, 0, "C", True)
                    pdf.cell(65, 10, "Estado", 1, 1, "C", True)

                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    for row in datos:
                        pdf.cell(45, 8, row['fecha_registro'].strftime('%d/%m/%y %H:%M'), 1)
                        pdf.cell(40, 8, f"ID: {row['id_sensor']}", 1)
                        pdf.cell(20, 8, f"{row['uso_cpu']}%", 1, 0, "C")
                        pdf.cell(20, 8, f"{row['uso_ram']}%", 1, 0, "C")
                        pdf.cell(65, 8, str(row['estado_sistema']), 1, 1, "C")

                    st.download_button("💾 DESCARGAR ARCHIVO PDF", pdf.output(dest='S').encode('latin-1'), "reporte.pdf", "application/pdf")
            except Exception as e: st.error(f"Error: {e}")