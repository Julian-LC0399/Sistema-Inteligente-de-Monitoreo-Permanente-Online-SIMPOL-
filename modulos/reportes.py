import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

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
    st_autorefresh(interval=30000, key="report_refresh")
    st.markdown("<h2 style='color:#003366;'>📊 Reportes e Inteligencia Predictiva</h2>", unsafe_allow_html=True)

    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        with col1:
            f_inicio = st.date_input("Fecha Inicial", datetime.now() - timedelta(days=7))
        with col2:
            f_final = st.date_input("Fecha Final", datetime.now())
        btn_filtrar = st.form_submit_button("🔍 Filtrar y Actualizar Tabla", use_container_width=True)

    try:
        conn = conectar_bd()
        query = """
            SELECT fecha_registro as 'Fecha', nodo_nombre as 'Nodo', 
                   uso_cpu as 'CPU %', uso_ram as 'RAM %', estado as 'Estado'
            FROM monitoreo_nodos 
            WHERE DATE(fecha_registro) >= %s AND DATE(fecha_registro) <= %s
            ORDER BY fecha_registro DESC
        """
        df = pd.read_sql(query, conn, params=(f_inicio, f_final))
        conn.close()

        if not df.empty:
            u_cpu = st.session_state.get('u_cpu_perc', 80)
            u_ram = st.session_state.get('u_ram_perc', 80)

            st.markdown("### 📋 Historial Filtrado")
            
            # --- SEMÁFORO VISUAL NATIVO ---
            # Creamos una columna que use iconos o colores según el umbral
            df['Nivel'] = df.apply(lambda r: "CRÍTICO" if r['CPU %'] >= u_cpu or r['RAM %'] >= u_ram else "NORMAL", axis=1)

            st.dataframe(
                df,
                column_config={
                    "CPU %": st.column_config.ProgressColumn("CPU %", min_value=0, max_value=100, format="%d%%"),
                    "RAM %": st.column_config.ProgressColumn("RAM %", min_value=0, max_value=100, format="%d%%"),
                    "Nivel": st.column_config.StatusColumn("ALERTA", mapping={
                        "CRÍTICO": "red",
                        "NORMAL": "green",
                    })
                },
                use_container_width=True,
                hide_index=True
            )

            # --- GENERACIÓN DE PDF (Sin cambios en lógica, solo limpieza) ---
            st.markdown("---")
            if st.button("📥 Descargar Reporte PDF con Colores de Alerta", use_container_width=True):
                pdf = PDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 10)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                cols = ["Fecha", "Nodo", "CPU %", "RAM %", "Estado"]
                for col in cols:
                    pdf.cell(38, 10, col, 1, 0, 'C', 1)
                pdf.ln()

                pdf.set_font('Arial', '', 9)
                for _, row in df.iterrows():
                    if row['CPU %'] >= u_cpu or row['RAM %'] >= u_ram:
                        pdf.set_fill_color(231, 76, 60)
                    else:
                        pdf.set_fill_color(39, 174, 96)
                    
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(38, 8, str(row['Fecha']), 1, 0, 'C', 1)
                    pdf.cell(38, 8, str(row['Nodo']), 1, 0, 'C', 1)
                    pdf.cell(38, 8, f"{row['CPU %']}%", 1, 0, 'C', 1)
                    pdf.cell(38, 8, f"{row['RAM %']}%", 1, 0, 'C', 1)
                    pdf.cell(38, 8, str(row['Estado']), 1, 1, 'C', 1)

                pdf_data = pdf.output(dest='S').encode('latin-1')
                st.download_button(
                    label="💾 Guardar archivo PDF",
                    data=pdf_data,
                    file_name=f"Reporte_SIMPOL_{f_inicio}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("No hay datos en este rango.")
    except Exception as e:
        st.error(f"Error en reporte: {e}")