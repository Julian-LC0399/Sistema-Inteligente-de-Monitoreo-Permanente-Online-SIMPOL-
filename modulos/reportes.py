import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import base64

class PDF(FPDF):
    def header(self):
        # --- AGREGAR LOGO ---
        # Parámetros: ruta, x, y, ancho (el alto se calcula proporcional)
        try:
            self.image('logo-banco.jpg', 10, 8, 33) 
        except:
            # Si no encuentra la imagen, deja el espacio para evitar error
            pass
            
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        # Movemos a la derecha para no chocar con el logo
        self.cell(40) 
        self.cell(0, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "L")
        
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(40)
        self.cell(0, 5, f"Auditoría de Monitoreo | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "L")
        self.ln(10)

def descargar_pdf_auto(bin_data, file_name):
    """Inyecta JS para descargar el archivo automáticamente"""
    b64 = base64.b64encode(bin_data).decode()
    js = f"""
        <a id="download_link" href="data:application/pdf;base64,{b64}" download="{file_name}"></a>
        <script>
            document.getElementById('download_link').click();
        </script>
    """
    st.components.v1.html(js, height=0)

def mostrar_pantalla():
    st.markdown("""
        <style>
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
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366;'>📄 Centro de Reportes de Auditoría</h2>", unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2 = st.columns(2)
        f_i = col1.date_input("Fecha Inicial:", datetime.now() - timedelta(days=1))
        f_f = col2.date_input("Fecha Final:", datetime.now())

        if st.button("🔍 GENERAR Y DESCARGAR REPORTE"):
            dt_i = datetime.combine(f_i, time(0, 0, 0))
            dt_f = datetime.combine(f_f, time(23, 59, 59))
            
            try:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT fecha_registro, id_sensor, uso_cpu, uso_ram, estado_sistema 
                    FROM monitoreo 
                    WHERE fecha_registro >= %s AND fecha_registro <= %s
                    ORDER BY fecha_registro DESC, id DESC
                """
                cursor.execute(query, (dt_i, dt_f))
                datos = cursor.fetchall()
                
                if not datos:
                    st.warning("No se encontraron registros en el rango seleccionado.")
                else:
                    pdf = PDF()
                    pdf.add_page()
                    
                    # Encabezados de tabla
                    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(45, 10, "Fecha/Hora", 1, 0, "C", True)
                    pdf.cell(40, 10, "ID Sensor", 1, 0, "C", True)
                    pdf.cell(20, 10, "CPU %", 1, 0, "C", True)
                    pdf.cell(20, 10, "RAM %", 1, 0, "C", True)
                    pdf.cell(65, 10, "Estado", 1, 1, "C", True)

                    # Datos
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    for row in datos:
                        pdf.cell(45, 8, row['fecha_registro'].strftime('%d/%m/%y %H:%M'), 1)
                        pdf.cell(40, 8, f"ID: {row['id_sensor']}", 1)
                        pdf.cell(20, 8, f"{row['uso_cpu']}%", 1, 0, "C")
                        pdf.cell(20, 8, f"{row['uso_ram']}%", 1, 0, "C")
                        pdf.cell(65, 8, str(row['estado_sistema']), 1, 1, "C")

                    # Generar y descargar
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    descargar_pdf_auto(pdf_output, f"Reporte_SIMPOL_{f_i}.pdf")
                    st.success("✅ Reporte generado con éxito.")
                    
                conn.close()
            except Exception as e: 
                st.error(f"Error al generar reporte: {e}")