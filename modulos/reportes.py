import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime
from datetime import timedelta
import time
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- CLASE PARA LA ESTRUCTURA DEL PDF ---
class PDF(FPDF):
    def header(self):
        # 1. Insertar Logo (Asegúrate de que el archivo exista en la carpeta principal)
        try:
            # Parámetros: ruta, x, y, ancho
            self.image('logo-banco.jpg', 10, 8, 33) 
        except:
            pass # Si no hay logo, el código sigue sin romperse

        # 2. Título del Reporte
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102) # Azul Banco
        self.set_x(45) # Espacio para el logo
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'L')
        
        # 3. Subtítulo
        self.set_x(45)
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Centro de Soporte al Usuario (CSU) - Reporte de Telemetría', 0, 1, 'L')
        self.ln(15) # Espacio antes del contenido

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial - Uso Interno Banco Caroní', 0, 0, 'C')

# --- FUNCIÓN PARA CONSTRUIR EL PDF ---
def generar_pdf(df):
    pdf = PDF()
    pdf.add_page()
    
    # SECCIÓN 1: RESUMEN ESTADÍSTICO
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, '1. RESUMEN EJECUTIVO DE CARGA', 0, 1, 'L')
    pdf.set_draw_color(0, 51, 102)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Cálculo de métricas (Usando nombres de columnas compatibles con AgGrid)
    stats = {
        "CPU": {"max": df['CPU %'].max(), "avg": df['CPU %'].mean(), "min": df['CPU %'].min()},
        "RAM": {"max": df['RAM %'].max(), "avg": df['RAM %'].mean(), "min": df['RAM %'].min()}
    }

    y_inicial = pdf.get_y()

    # Cuadro de CPU
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(92, 8, "Métricas de CPU", 1, 1, 'C', True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(92, 6, f" - Valor Máximo: {stats['CPU']['max']}%", 'LR', 1, 'L')
    pdf.cell(92, 6, f" - Promedio de Carga: {stats['CPU']['avg']:.2f}%", 'LR', 1, 'L')
    pdf.cell(92, 6, f" - Valor Mínimo: {stats['CPU']['min']}%", 'LRB', 1, 'L')

    # Cuadro de RAM
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

    # SECCIÓN 2: TABLA DE DETALLES
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
    for _, row in df.iterrows():
        pdf.cell(60, 7, str(row['Fecha/Hora']), 1)
        pdf.cell(45, 7, str(row['Nodo']), 1)
        pdf.cell(30, 7, f"{row['CPU %']}%", 1, 0, 'C')
        pdf.cell(30, 7, f"{row['RAM %']}%", 1, 0, 'C')
        pdf.cell(25, 7, str(row['Estado']), 1, 0, 'C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# --- FUNCIÓN PRINCIPAL DE LA PANTALLA ---
def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>Reportes y Auditoría de Red</h2>", unsafe_allow_html=True)
    
    # Control de actualización automática
    if "ver_reporte" not in st.session_state:
        st.session_state.ver_reporte = False

    with st.expander("📅 Configuración del Reporte", expanded=True):
        c1, c2 = st.columns(2)
        f_inicio = c1.date_input("Desde", datetime.now())
        f_fin = c2.date_input("Hasta", datetime.now())
        
        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("📊 INICIAR MONITOREO EN VIVO", use_container_width=True):
            st.session_state.ver_reporte = True
        if btn_col2.button("🛑 DETENER ACTUALIZACIÓN", use_container_width=True):
            st.session_state.ver_reporte = False

    if st.session_state.ver_reporte:
        placeholder = st.empty()
        
        with placeholder.container():
            conn = conectar_bd()
            # Consulta con Alias para AgGrid y PDF
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
                st.markdown(f"**Sincronización con Agente:** `{datetime.now().strftime('%H:%M:%S')}`")
                
                # Métricas Rápidas
                m1, m2, m3 = st.columns(3)
                m1.metric("Máximo CPU", f"{df['CPU %'].max()}%")
                m2.metric("Promedio Carga", f"{df['CPU %'].mean():.1f}%")
                m3.metric("Registros", len(df))

                # Configuración de Tabla AgGrid
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
                gb.configure_default_column(resizable=True, filterable=True, sortable=True)
                gb.configure_column("Estado", cellStyle={'color': 'white', 'backgroundColor': '#003366'})
                gridOptions = gb.build()

                AgGrid(df, gridOptions=gridOptions, theme='alpine', height=350)

                # Opción de Descarga
                pdf_bytes = generar_pdf(df)
                st.download_button(
                    label="📄 DESCARGAR INFORME PDF (Miembro Institucional)",
                    data=pdf_bytes,
                    file_name=f"Reporte_CSU_{f_inicio}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("No se encontraron registros para el rango de fechas seleccionado.")

        # Ciclo de refresco (Sincronía con el agente)
        time.sleep(10)
        st.rerun()



def calcular_capacidad_predictiva(df, columna_metrica):
    """
    Analiza la tendencia de una métrica (CPU o RAM) y predice 
    cuántos días faltan para llegar al umbral crítico (95%).
    """
    if len(df) < 5: # Necesitamos al menos 5 registros para una tendencia seria
        return None, "Datos insuficientes para predecir"

    # Preparamos los datos (X = tiempo, Y = consumo)
    y = df[columna_metrica].values
    x = np.arange(len(y))

    # Regresión lineal: y = mx + b
    modelo = np.polyfit(x, y, 1)
    pendiente = modelo[0]
    intercepto = modelo[1]

    # Si la pendiente es negativa o cero, el consumo es estable
    if pendiente <= 0:
        return "Estable", "No se prevé saturación"

    # Calculamos cuándo 'y' llegará a 95%
    # 95 = pendiente * x + intercepto  => x = (95 - intercepto) / pendiente
    indice_colapso = (95 - intercepto) / pendiente
    dias_restantes = indice_colapso - (len(y) - 1)
    
    fecha_estimada = datetime.now() + timedelta(days=int(max(0, dias_restantes)))
    
    return int(dias_restantes), fecha_estimada.strftime('%d/%m/%Y')