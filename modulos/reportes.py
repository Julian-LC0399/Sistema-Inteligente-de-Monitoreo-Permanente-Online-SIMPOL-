import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from utils import get_resource_path

# Clase para generar el PDF con formato institucional
class PDF(FPDF):
    def header(self):
        try:
            # Uso de ruta absoluta segura para el servidor
            self.image(get_resource_path('logo-banco.jpg'), 10, 8, 33)
        except:
            pass # Si no encuentra el logo, no rompe el reporte
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.set_x(45)
        self.cell(0, 10, 'SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'L')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>📊 Reportes e inteligencia predictiva</h2>", unsafe_allow_html=True)

    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        with col1:
            f_inicio = st.date_input("Desde", datetime.now() - timedelta(days=7))
        with col2:
            f_fin = st.date_input("Hasta", datetime.now())
        
        btn_generar = st.form_submit_button("Consultar Histórico", use_container_width=True)

    if btn_generar:
        try:
            conn = conectar_bd()
            # Ajustar nombres de columnas según tu DB
            query = f"SELECT fecha_registro as Fecha, 'Nodo-CSU' as Nodo, uso_cpu as 'CPU %', uso_ram as 'RAM %' FROM monitoreo_log WHERE fecha_registro BETWEEN '{f_inicio}' AND '{f_fin}' ORDER BY fecha_registro DESC"
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                st.success(f"Se encontraron {len(df)} registros.")
                st.dataframe(df, use_container_width=True)

                # --- GENERACIÓN DEL PDF ---
                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 10)
                
                # Encabezados de tabla en el PDF
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                columnas = ["Fecha", "Nodo", "CPU %", "RAM %", "Estatus"]
                for col in columnas:
                    pdf.cell(38, 10, col, 1, 0, 'C', 1)
                pdf.ln()

                # Datos de la tabla
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 0, 0)
                for _, row in df.head(100).iterrows(): # Limitamos a 100 para el PDF por rendimiento
                    pdf.cell(38, 8, str(row['Fecha']), 1)
                    pdf.cell(38, 8, str(row['Nodo']), 1)
                    pdf.cell(38, 8, f"{row['CPU %']}%", 1)
                    pdf.cell(38, 8, f"{row['RAM %']}%", 1)
                    # Lógica de estatus visual
                    estatus = "NORMAL" if row['CPU %'] < 85 else "CRITICO"
                    pdf.cell(38, 8, estatus, 1, 1)

                # Botón de descarga
                pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
                st.download_button(
                    label="💾 Descargar Reporte en PDF",
                    data=pdf_output,
                    file_name=f"Reporte_SIMPOL_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("No hay datos para el rango de fechas seleccionado.")
        except Exception as e:
            st.error(f"Error generando reporte: {e}")