import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
from streamlit_autorefresh import st_autorefresh

# --- ESTRUCTURA DEL PDF ---
class PDF(FPDF):
    def header(self):
        try: self.image('logo-banco.jpg', 10, 8, 33) 
        except: pass
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.set_x(45)
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'L')
        self.ln(10)

def mostrar_pantalla():
    # Sincronización cada 30 segundos
    st_autorefresh(interval=30000, key="report_refresh")

    st.markdown("<h2 style='color:#003366;'>📊 Reportes e Inteligencia Predictiva</h2>", unsafe_allow_html=True)

    # --- BLOQUE DE FILTROS ---
    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        with col1:
            f_inicio = st.date_input("Fecha Inicial", datetime.now() - timedelta(days=7))
        with col2:
            f_final = st.date_input("Fecha Final", datetime.now())
        
        # BOTÓN PARA DISPARAR EL FILTRADO
        btn_filtrar = st.form_submit_button("🔍 Filtrar y Actualizar Tabla", use_container_width=True)

    # --- PROCESAMIENTO DE DATOS ---
    try:
        conn = conectar_bd()
        # Filtro corregido con DATE() para precisión total
        query = """
            SELECT fecha_registro as 'Fecha', 
                   nodo_nombre as 'Nodo', 
                   uso_cpu as 'CPU %', 
                   uso_ram as 'RAM %',
                   estado as 'Estado'
            FROM monitoreo_30_nodos 
            WHERE DATE(fecha_registro) >= %s AND DATE(fecha_registro) <= %s
            ORDER BY fecha_registro DESC
        """
        df = pd.read_sql(query, conn, params=(f_inicio, f_final))
        conn.close()

        if not df.empty:
            # Umbrales desde session_state
            u_cpu = st.session_state.get('u_cpu_perc', 80)
            u_ram = st.session_state.get('u_ram_perc', 80)

            # --- TABLA INTERACTIVA (AgGrid) ---
            st.markdown("### 📋 Historial Filtrado")
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationPageSize=15)
            
            # JavaScript para colores en la web
            row_style_jscode = JsCode(f"""
            function(params) {{
                if (params.data['CPU %'] >= {u_cpu} || params.data['RAM %'] >= {u_ram}) {{
                    return {{ 'color': 'white', 'backgroundColor': '#e74c3c' }}
                }} else {{
                    return {{ 'color': 'white', 'backgroundColor': '#27ae60' }}
                }}
            }};
            """)
            gridOptions = gb.build()
            gridOptions['getRowStyle'] = row_style_jscode

            AgGrid(df, gridOptions=gridOptions, allow_unsafe_jscode=True, 
                   columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, theme="streamlit")

            # --- GENERACIÓN DE PDF ---
            st.markdown("---")
            if st.button("📥 Descargar Reporte PDF con Colores de Alerta", use_container_width=True):
                pdf = PDF()
                pdf.add_page()
                
                # Encabezados
                pdf.set_font('Arial', 'B', 10)
                pdf.set_fill_color(0, 51, 102) # Azul oscuro para el header
                pdf.set_text_color(255, 255, 255)
                cols = ["Fecha", "Nodo", "CPU %", "RAM %", "Estado"]
                for col in cols:
                    pdf.cell(38, 10, col, 1, 0, 'C', 1)
                pdf.ln()

                # Datos con semáforo
                pdf.set_font('Arial', '', 9)
                for _, row in df.iterrows():
                    # Lógica de color en PDF
                    if row['CPU %'] >= u_cpu or row['RAM %'] >= u_ram:
                        pdf.set_fill_color(231, 76, 60) # Rojo
                    else:
                        pdf.set_fill_color(39, 174, 96)  # Verde
                    
                    pdf.set_text_color(255, 255, 255) # Texto blanco para contraste
                    
                    # Dibujamos celdas (el 1 final indica que use el fill_color)
                    pdf.cell(38, 8, str(row['Fecha']), 1, 0, 'C', 1)
                    pdf.cell(38, 8, str(row['Nodo']), 1, 0, 'C', 1)
                    pdf.cell(38, 8, f"{row['CPU %']}%", 1, 0, 'C', 1)
                    pdf.cell(38, 8, f"{row['RAM %']}%", 1, 0, 'C', 1)
                    pdf.cell(38, 8, str(row['Estado']), 1, 1, 'C', 1)

                pdf_data = pdf.output(dest='S').encode('latin-1')
                st.download_button(
                    label="💾 Guardar archivo PDF",
                    data=pdf_data,
                    file_name=f"Reporte_SIMPOL_{f_inicio}_al_{f_final}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning(f"No hay datos para el rango: {f_inicio} al {f_final}")

    except Exception as e:
        st.error(f"Error en el reporte: {e}")