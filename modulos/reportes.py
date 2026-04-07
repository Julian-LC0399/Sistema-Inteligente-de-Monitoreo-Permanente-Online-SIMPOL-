import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from utils import get_resource_path
from datetime import datetime, timedelta, time

# 1. CLASE PDF NATIVA CON LOGO INSTITUCIONAL
class PDF(FPDF):
    def header(self):
        try:
            ruta_logo = get_resource_path("logo-banco.jpg")
            self.image(ruta_logo, 10, 8, 33)
        except:
            pass
        
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(80)
        self.cell(100, 10, "BANCO CARONI - REPORTE INTEGRAL SIMPOL", 0, 1, "C")
        
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(80)
        self.cell(100, 5, f"Auditoria de Monitoreo | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} - Documento Confidencial", 0, 0, "C")

def obtener_datos_nativos(f_inicio, f_fin):
    datos = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema 
                FROM monitoreo 
                WHERE fecha_registro >= %s AND fecha_registro <= %s
                ORDER BY fecha_registro DESC, id DESC
            """
            cursor.execute(query, (f_inicio, f_fin))
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
    return datos

def mostrar_pantalla():
    # Estilos CSS: Colores y quitar índice
    st.markdown("""
        <style>
            div.stButton > button, div.stDownloadButton > button {
                color: #000000 !important;
                background-color: #f0f2f6 !important;
                border: 1px solid #d1d3d8 !important;
                font-weight: bold !important;
                width: 100%;
            }
            [data-testid="stTable"] td { color: black !important; border: 1px solid #eee !important; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
            /* OCULTAR COLUMNA DE ÍNDICE */
            [data-testid="stTable"] td:nth-child(1), 
            [data-testid="stTable"] th:nth-child(1) {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366;'>📄 Centro de Reportes de Auditoría</h2>", unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2 = st.columns(2)
        f_i = col1.date_input("Fecha Inicial:", datetime.now() - timedelta(days=1))
        f_f = col2.date_input("Fecha Final:", datetime.now())

        if st.button("🔍 GENERAR VISTA PREVIA Y PDF"):
            dt_i = datetime.combine(f_i, time(0, 0, 0))
            dt_f = datetime.combine(f_f, time(23, 59, 59))
            
            datos = obtener_datos_nativos(dt_i, dt_f)

            if not datos:
                st.warning("No se encontraron registros para este periodo.")
            else:
                st.success(f"✅ {len(datos)} registros cargados.")
                
                st.markdown("### 📋 Vista Previa")
                vista = []
                for d in datos[:10]:
                    vista.append({
                        "FECHA": d['fecha_registro'].strftime('%d/%m/%y %H:%M:%S'),
                        "CSU": d['nombre_csu'],
                        "CPU %": f"{d['uso_cpu']}%",
                        "RAM %": f"{d['uso_ram']}%",
                        "ESTADO": d['estado_sistema']
                    })
                st.table(vista)

                pdf = PDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                
                pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 10)
                pdf.cell(45, 10, "Fecha/Hora", 1, 0, "C", True)
                pdf.cell(40, 10, "Unidad CSU", 1, 0, "C", True)
                pdf.cell(20, 10, "CPU %", 1, 0, "C", True)
                pdf.cell(20, 10, "RAM %", 1, 0, "C", True)
                pdf.cell(65, 10, "Estado Sistema", 1, 1, "C", True)

                pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                for row in datos:
                    pdf.cell(45, 8, row['fecha_registro'].strftime('%d/%m/%y %H:%M:%S'), 1)
                    pdf.cell(40, 8, str(row['nombre_csu']), 1)
                    pdf.cell(20, 8, f"{row['uso_cpu']}%", 1, 0, "C")
                    pdf.cell(20, 8, f"{row['uso_ram']}%", 1, 0, "C")
                    pdf.cell(65, 8, str(row['estado_sistema']).upper(), 1, 1, "C")

                try:
                    pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
                    st.download_button(
                        label="💾 DESCARGAR REPORTE PDF COMPLETO",
                        data=pdf_output,
                        file_name=f"AUDITORIA_SIMPOL_{f_i}_AL_{f_f}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error técnico: {e}")