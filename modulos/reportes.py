import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

class PDF(FPDF):
    def header(self):
        # Intento de cargar logo, si no existe no rompe el código
        try: self.image('logo-banco.jpg', 10, 8, 33) 
        except: pass
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.set_x(45)
        self.cell(0, 10, 'SISTEMA SIMPOL - REPORTE DE GESTIÓN OPERATIVA', 0, 1, 'L')
        self.ln(10)

def mostrar_pantalla():
    # Refresco automático cada 30 segundos
    st_autorefresh(interval=30000, key="report_refresh")
    st.markdown("<h2 style='color:#003366;'>📊 Reportes e Inteligencia Predictiva</h2>", unsafe_allow_html=True)

    # --- FORMULARIO DE FILTROS ---
    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        with col1:
            f_inicio = st.date_input("Fecha Inicial", datetime.now() - timedelta(days=7))
        with col2:
            f_final = st.date_input("Fecha Final", datetime.now())
        btn_filtrar = st.form_submit_button("🔍 Filtrar y Actualizar Reporte")

    # --- LÓGICA DE CONSULTA ---
    db = conectar_bd()
    if db:
        try:
            # Consulta a la nueva tabla sin el "30"
            query = """
                SELECT fecha_registro as Fecha, nodo_nombre as Nodo, 
                       uso_cpu as 'CPU %', uso_ram as 'RAM %'
                FROM monitoreo_nodos 
                WHERE DATE(fecha_registro) BETWEEN %s AND %s
                ORDER BY fecha_registro DESC
            """
            df = pd.read_sql(query, db, params=(f_inicio, f_final))
            db.close()

            if not df.empty:
                # --- PROCESAMIENTO DE DATOS ---
                u_cpu = st.session_state.get('u_cpu_perc', 85)
                u_ram = st.session_state.get('u_ram_perc', 90)

                # Creamos la columna de estado con Emojis (Sustituye a StatusColumn)
                df['ALERTA'] = df.apply(
                    lambda r: "🔴 CRÍTICO" if r['CPU %'] >= u_cpu or r['RAM %'] >= u_ram else "🟢 NORMAL", 
                    axis=1
                )

                # --- VISUALIZACIÓN EN PANTALLA ---
                st.markdown("### Historial de Telemetría")
                st.dataframe(
                    df,
                    column_config={
                        "CPU %": st.column_config.ProgressColumn("CPU %", min_value=0, max_value=100, format="%d%%"),
                        "RAM %": st.column_config.ProgressColumn("RAM %", min_value=0, max_value=100, format="%d%%"),
                        "ALERTA": st.column_config.TextColumn("Estado Visual")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                # --- GENERACIÓN DE PDF ---
                if st.button("📥 Descargar Reporte en PDF"):
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 10)
                    
                    # Encabezados de tabla PDF
                    pdf.set_fill_color(0, 51, 102)
                    pdf.set_text_color(255, 255, 255)
                    cols = ["Fecha", "Nodo", "CPU %", "RAM %", "Estado"]
                    for col in cols:
                        pdf.cell(38, 10, col, 1, 0, 'C', 1)
                    pdf.ln()

                    # Filas de la tabla PDF
                    pdf.set_font('Arial', '', 9)
                    for _, row in df.iterrows():
                        # Lógica de colores para el PDF (Sin emojis para evitar error de encoding)
                        if row['CPU %'] >= u_cpu or row['RAM %'] >= u_ram:
                            pdf.set_fill_color(231, 76, 60) # Rojo
                            txt_estado = "CRITICO"
                        else:
                            pdf.set_fill_color(39, 174, 96) # Verde
                            txt_estado = "NORMAL"
                        
                        pdf.set_text_color(255, 255, 255)
                        pdf.cell(38, 8, str(row['Fecha']), 1, 0, 'C', 1)
                        pdf.cell(38, 8, str(row['Nodo']), 1, 0, 'C', 1)
                        pdf.cell(38, 8, f"{row['CPU %']}%", 1, 0, 'C', 1)
                        pdf.cell(38, 8, f"{row['RAM %']}%", 1, 0, 'C', 1)
                        pdf.cell(38, 8, txt_estado, 1, 1, 'C', 1)

                    # Descarga del archivo
                    fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
                    nombre_archivo = f"Reporte_SIMPOL_{fecha_str}.pdf"
                    pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
                    
                    st.download_button(
                        label="Click para Guardar PDF",
                        data=pdf_output,
                        file_name=nombre_archivo,
                        mime="application/pdf"
                    )
            else:
                st.warning("No se encontraron datos en el rango de fechas seleccionado.")

        except Exception as e:
            st.error(f"Error al procesar el reporte: {e}")
    else:
        st.error("No se pudo conectar a la base de datos. Verifique database.py")