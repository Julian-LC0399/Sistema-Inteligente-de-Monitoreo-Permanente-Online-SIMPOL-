import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime
import time
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'C')
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
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # CORRECCIÓN: Usar los nombres de columna que vienen de AgGrid
    stats = {
        "CPU": {"max": df['CPU %'].max(), "avg": df['CPU %'].mean(), "min": df['CPU %'].min()},
        "RAM": {"max": df['RAM %'].max(), "avg": df['RAM %'].mean(), "min": df['RAM %'].min()}
    }

    y_inicial = pdf.get_y()

    # Bloque CPU
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(92, 8, "Métricas de CPU", 1, 1, 'C', True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(92, 6, f" - Valor Máximo: {stats['CPU']['max']}%", 'LR', 1, 'L')
    pdf.cell(92, 6, f" - Promedio de Carga: {stats['CPU']['avg']:.2f}%", 'LR', 1, 'L')
    pdf.cell(92, 6, f" - Valor Mínimo: {stats['CPU']['min']}%", 'LRB', 1, 'L')

    # Bloque RAM
    pdf.set_xy(108, y_inicial)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(92, 8, "Métricas de RAM", 1, 1, 'C', True)
    pdf.set_font('Arial', '', 9)
    pdf.set_x(108)
    pdf.cell(92, 6, f" - Valor Máximo: {stats['RAM']['max']}%", 'LR', 1, 'L')
    pdf.set_x(108)
    pdf.cell(92, 6, f" - Promedio de Carga: {stats['RAM']['avg']:.2f}%", 'LR', 1, 'L')
    pdf.set_x(108)
    pdf.cell(92, 6, f" - Valor Mínimo: {stats['RAM']['min']}%", 'LRB', 1, 'L')
    
    pdf.ln(15)

    # --- SECCIÓN 2: TABLA DE DETALLES ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, '2. DESGLOSE CRONOLÓGICO DE EVENTOS', 0, 1, 'L')
    pdf.ln(2)

    cols = {'Fecha/Hora': 60, 'Nodo': 45, 'CPU %': 30, 'RAM %': 30, 'Estado': 25}
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    for nombre, ancho in cols.items():
        pdf.cell(ancho, 10, nombre, 1, 0, 'C', True)
    
    pdf.ln()
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    
    # CORRECCIÓN: Iterar usando los nombres de columna nuevos
    for _, row in df.iterrows():
        pdf.cell(60, 7, str(row['Fecha/Hora']), 1)
        pdf.cell(45, 7, str(row['Nodo']), 1)
        pdf.cell(30, 7, f"{row['CPU %']}%", 1, 0, 'C')
        pdf.cell(30, 7, f"{row['RAM %']}%", 1, 0, 'C')
        pdf.cell(25, 7, str(row['Estado']), 1, 0, 'C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>Reportes y Auditoría</h2>", unsafe_allow_html=True)
    
    if "ver_reporte" not in st.session_state:
        st.session_state.ver_reporte = False

    with st.expander("📅 Filtros de Exportación", expanded=True):
        c1, c2 = st.columns(2)
        f_inicio = c1.date_input("Fecha Inicial", datetime.now())
        f_fin = c2.date_input("Fecha Final", datetime.now())
        
        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("📊 INICIAR MONITOREO DE REPORTE", use_container_width=True):
            st.session_state.ver_reporte = True
        if col_btn2.button("🛑 DETENER ACTUALIZACIÓN", use_container_width=True):
            st.session_state.ver_reporte = False

    if st.session_state.ver_reporte:
        placeholder = st.empty()
        
        with placeholder.container():
            conn = conectar_bd()
            # Mantenemos los alias para AgGrid
            query = """SELECT fecha_registro as 'Fecha/Hora', 
                              nodo_nombre as 'Nodo', 
                              uso_cpu as 'CPU %', 
                              uso_ram as 'RAM %', 
                              estado as 'Estado' 
                       FROM monitoreo_30_nodos 
                       WHERE DATE(fecha_registro) BETWEEN %s AND %s 
                       ORDER BY id DESC"""
            df = pd.read_sql(query, conn, params=(f_inicio, f_fin))
            conn.close()

            if not df.empty:
                st.markdown(f"**Sincronización Agente:** `{datetime.now().strftime('%H:%M:%S')}`")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Max CPU", f"{df['CPU %'].max()}%")
                m2.metric("Promedio CPU", f"{df['CPU %'].mean():.1f}%")
                m3.metric("Total Registros", len(df))

                # AgGrid
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
                gb.configure_default_column(resizable=True, filterable=True, sortable=True)
                gridOptions = gb.build()

                AgGrid(df, gridOptions=gridOptions, theme='alpine', height=350)

                # Botón de PDF - Ahora sí recibirá las columnas correctas
                pdf_bytes = generar_pdf(df)
                st.download_button(
                    label="📄 DESCARGAR REPORTE PDF",
                    data=pdf_bytes,
                    file_name=f"Reporte_SIMPOL_{f_inicio}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("No hay datos en el rango seleccionado.")

        time.sleep(10)
        st.rerun()