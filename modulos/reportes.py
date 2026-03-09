import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
from streamlit_autorefresh import st_autorefresh
from utils import get_resource_path

# --- 1. ESTRUCTURA DEL PDF (ENCABEZADO Y FORMATO) ---
class PDF(FPDF):
    def header(self):
        # Localización dinámica del logo para el ejecutable
        try: 
            logo_path = get_resource_path('logo-banco.jpg')
            self.image(logo_path, 10, 8, 33) 
        except: 
            pass
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.set_x(45)
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'L')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def mostrar_pantalla():
    # Sincronización automática cada 30 segundos
    st_autorefresh(interval=30000, key="report_refresh")

    st.markdown("<h2 style='color:#003366;'>📊 Reportes e Inteligencia Predictiva</h2>", unsafe_allow_html=True)

    # --- 2. BLOQUE DE FILTROS ---
    with st.form("filtro_reportes"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            f_inicio = st.date_input("Fecha Inicial", datetime.now() - timedelta(days=7))
        with col2:
            f_final = st.date_input("Fecha Final", datetime.now())
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_filtrar = st.form_submit_button("🔍 FILTRAR HISTORIAL")

    # --- 3. OBTENCIÓN DE DATOS DESDE LA BASE DE DATOS ---
    try:
        conn = conectar_bd()
        # Convertimos fechas a string para la consulta SQL
        str_inicio = f_inicio.strftime('%Y-%m-%d 00:00:00')
        str_final = f_final.strftime('%Y-%m-%d 23:59:59')
        
        query = """
            SELECT fecha_registro AS Fecha, nodo AS Nodo, uso_cpu AS 'CPU %', uso_ram AS 'RAM %'
            FROM telemetria 
            WHERE fecha_registro BETWEEN %s AND %s
            ORDER BY fecha_registro DESC
        """
        df = pd.read_sql(query, conn, params=(str_inicio, str_final))
        conn.close()

        if not df.empty:
            # Añadimos columna de estado lógica
            u_cpu = st.session_state.get('u_cpu_perc', 85)
            u_ram = st.session_state.get('u_ram_perc', 90)
            
            df['Estado'] = df.apply(
                lambda x: 'ALERTA' if x['CPU %'] >= u_cpu or x['RAM %'] >= u_ram else 'ESTABLE', 
                axis=1
            )

            # --- 4. CONFIGURACIÓN DE TABLA INTERACTIVA (AgGrid) ---
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            
            # Código JS para colorear las filas en la interfaz
            cellsytle_jscode = JsCode(f"""
            function(params) {{
                if (params.data['CPU %'] >= {u_cpu} || params.data['RAM %'] >= {u_ram}) {{
                    return {{ 'color': 'white', 'backgroundColor': '#e74c3c' }}
                }}
                return null;
            }};
            """)
            gb.configure_column("Estado", cellStyle=cellsytle_jscode)
            
            gridOptions = gb.build()

            AgGrid(
                df, 
                gridOptions=gridOptions, 
                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                theme="streamlit",
                allow_unsafe_jscode=True
            )

            # --- 5. GENERACIÓN DE PDF ---
            st.markdown("---")
            if st.button("📑 GENERAR Y DESCARGAR REPORTE PDF"):
                pdf = PDF()
                pdf.add_page()
                
                # Resumen de filtros
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 10, f"Periodo: {f_inicio} al {f_final}", 0, 1)
                pdf.ln(5)

                # Encabezados de tabla
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(45, 10, 'Fecha/Hora', 1, 0, 'C', 1)
                pdf.cell(35, 10, 'Nodo', 1, 0, 'C', 1)
                pdf.cell(30, 10, 'CPU %', 1, 0, 'C', 1)
                pdf.cell(30, 10, 'RAM %', 1, 0, 'C', 1)
                pdf.cell(45, 10, 'Estado', 1, 1, 'C', 1)

                # Filas con semáforo
                pdf.set_font('Arial', '', 9)
                pdf.set_text_color(0, 0, 0)
                
                for _, row in df.iterrows():
                    # Color según estado
                    if row['Estado'] == 'ALERTA':
                        pdf.set_fill_color(255, 200, 200) # Rojo suave
                    else:
                        pdf.set_fill_color(200, 255, 200) # Verde suave
                    
                    pdf.cell(45, 8, str(row['Fecha']), 1, 0, 'C', 1)
                    pdf.cell(35, 8, str(row['Nodo']), 1, 0, 'C', 1)
                    pdf.cell(30, 8, f"{row['CPU %']}%", 1, 0, 'C', 1)
                    pdf.cell(30, 8, f"{row['RAM %']}%", 1, 0, 'C', 1)
                    pdf.cell(45, 8, str(row['Estado']), 1, 1, 'C', 1)

                # Generar blob de datos
                pdf_output = pdf.output(dest='S').encode('latin-1')
                
                st.download_button(
                    label="💾 Descargar Archivo PDF",
                    data=pdf_output,
                    file_name=f"Reporte_SIMPOL_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("No se encontraron registros para el rango de fechas seleccionado.")

    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")