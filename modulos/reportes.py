import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime

class PDF(FPDF):
    def header(self):
        # Logo o Título institucional
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102) # Azul Banco
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Centro de Soporte al Usuario (CSU) - Reporte de Telemetría', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial - Uso Interno Banco', 0, 0, 'C')

def generar_pdf(df):
    pdf = PDF()
    pdf.add_page()
    
    # --- SECCIÓN 1: RESUMEN ESTADÍSTICO ---
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, '1. RESUMEN EJECUTIVO DE CARGA', 0, 1, 'L')
    pdf.set_draw_color(0, 51, 102)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Línea divisoria
    pdf.ln(2)

    # Cálculo de métricas
    stats = {
        "CPU": {"max": df['uso_cpu'].max(), "avg": df['uso_cpu'].mean(), "min": df['uso_cpu'].min()},
        "RAM": {"max": df['uso_ram'].max(), "avg": df['uso_ram'].mean(), "min": df['uso_ram'].min()}
    }

    pdf.set_font('Arial', '', 10)
    # Cuadro de estadísticas
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 25, f"", 1, 0, 'L', True) # Fondo para CPU
    pdf.set_x(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 8, "Métricas de CPU", 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 5, f" - Valor Máximo: {stats['CPU']['max']}%", 0, 1, 'L')
    pdf.cell(95, 5, f" - Promedio de Carga: {stats['CPU']['avg']:.2f}%", 0, 1, 'L')
    pdf.cell(95, 5, f" - Valor Mínimo: {stats['CPU']['min']}%", 0, 1, 'L')

    # Posicionamiento para la columna de RAM
    pdf.set_xy(105, 30) 
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 25, f"", 1, 0, 'L', True)
    pdf.set_x(105)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 8, "Métricas de RAM", 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(95, 5, f" - Valor Máximo: {stats['RAM']['max']}%", 0, 1, 'L')
    pdf.cell(95, 5, f" - Promedio de Carga: {stats['RAM']['avg']:.2f}%", 0, 1, 'L')
    pdf.cell(95, 5, f" - Valor Mínimo: {stats['RAM']['min']}%", 0, 1, 'L')
    
    pdf.ln(10)

    # --- SECCIÓN 2: TABLA DE DETALLES ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, '2. DESGLOSE CRONOLÓGICO DE EVENTOS', 0, 1, 'L')
    pdf.ln(2)

    # Encabezados de tabla
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    
    cols = {'Fecha/Hora': 60, 'Nodo': 45, 'CPU %': 30, 'RAM %': 30, 'Estado': 25}
    for nombre, ancho in cols.items():
        pdf.cell(ancho, 10, nombre, 1, 0, 'C', True)
    
    pdf.ln()
    
    # Filas de la tabla
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    for _, row in df.iterrows():
        pdf.cell(60, 7, str(row['fecha_registro']), 1)
        pdf.cell(45, 7, str(row['nodo_nombre']), 1)
        pdf.cell(30, 7, f"{row['uso_cpu']}%", 1, 0, 'C')
        pdf.cell(30, 7, f"{row['uso_ram']}%", 1, 0, 'C')
        pdf.cell(25, 7, str(row['estado']), 1, 0, 'C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>Reportes y Auditoría</h2>", unsafe_allow_html=True)
    
    with st.expander("📅 Filtros de Exportación", expanded=True):
        c1, c2 = st.columns(2)
        f_inicio = c1.date_input("Fecha Inicial", datetime.now())
        f_fin = c2.date_input("Fecha Final", datetime.now())

    if st.button("📊 GENERAR VISTA PREVIA"):
        conn = conectar_bd()
        query = "SELECT fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado FROM monitoreo_30_nodos WHERE DATE(fecha_registro) BETWEEN %s AND %s ORDER BY id DESC"
        df = pd.read_sql(query, conn, params=(f_inicio, f_fin))
        conn.close()

        if not df.empty:
            # Mostrar métricas rápidas en Streamlit antes de descargar
            m1, m2, m3 = st.columns(3)
            m1.metric("Max CPU", f"{df['uso_cpu'].max()}%")
            m2.metric("Promedio CPU", f"{df['uso_cpu'].mean():.1f}%")
            m3.metric("Registros", len(df))

            st.dataframe(df, use_container_width=True)
            
            pdf_bytes = generar_pdf(df)
            st.download_button(
                label="📄 DESCARGAR INFORME PDF",
                data=pdf_bytes,
                file_name=f"Reporte_CSU_{f_inicio}_al_{f_fin}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.warning("No existen datos para el rango seleccionado.")