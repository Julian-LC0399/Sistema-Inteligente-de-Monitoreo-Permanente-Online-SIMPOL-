import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
# Intentamos importar pandas para las funciones de conveniencia
try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

# Mantenemos tu clase PDF igual (es código nativo, no falla)
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "SIMPOL - REPORTE DE GESTIÓN CSU", 0, 1, "L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()} - Confidencial Banco Caroní", 0, 0, "C")

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>📊 Reportes</h2>", unsafe_allow_html=True)
    st.info("Los estados reflejan la configuración vigente al momento de la captura.")

    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        f_inicio = col1.date_input("Desde", datetime.now() - timedelta(days=7))
        f_fin = col2.date_input("Hasta", datetime.now())
        btn_generar = st.form_submit_button("🔍 Generar Vista Previa", use_container_width=True)

    if btn_generar:
        try:
            conn = conectar_bd()
            if conn:
                # EXTRACCIÓN NATIVA: Sin usar pd.read_sql
                cursor = conn.cursor(dictionary=True)
                query = f"""
                    SELECT 
                        fecha_registro as Fecha, 
                        nombre_csu as CSU, 
                        uso_cpu as 'CPU', 
                        uso_ram as 'RAM', 
                        estado_sistema as ESTADO 
                    FROM monitoreo 
                    WHERE DATE(fecha_registro) BETWEEN %s AND %s 
                    ORDER BY fecha_registro DESC
                """
                cursor.execute(query, (f_inicio, f_fin))
                datos = cursor.fetchall() # Lista de diccionarios
                cursor.close()
                conn.close()

                if datos:
                    st.markdown(f"### Se encontraron {len(datos)} registros")
                    
                    # --- VISUALIZACIÓN EN PANTALLA ---
                    if PANDAS_OK:
                        df = pd.DataFrame(datos)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ Modo Servidor: Tabla estática (Sin Pandas)")
                        st.table(datos[:50]) # Mostramos los primeros 50 para no saturar

                    # --- GENERACIÓN DE PDF (Uso de datos nativos) ---
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 10)
                    
                    # Encabezados
                    pdf.set_fill_color(240, 240, 240)
                    columnas = ["Fecha/Hora", "CSU", "CPU", "RAM", "Estado"]
                    anchos = [45, 35, 25, 25, 60]
                    for i, col in enumerate(columnas):
                        pdf.cell(anchos[i], 10, col, 1, 0, "C", True)
                    pdf.ln()

                    pdf.set_font("Arial", "", 9)
                    # Usamos la lista 'datos' directamente en lugar de iterrows()
                    for row in datos[:500]: # Limitamos a 500 para el PDF
                        pdf.cell(anchos[0], 8, str(row["Fecha"]), 1)
                        pdf.cell(anchos[1], 8, str(row["CSU"]), 1)
                        pdf.cell(anchos[2], 8, f"{row['CPU']}%", 1, 0, "C")
                        pdf.cell(anchos[3], 8, f"{row['RAM']}%", 1, 0, "C")
                        pdf.cell(anchos[4], 8, str(row["ESTADO"]).upper(), 1, 1, "C")

                    # Botón de Descarga
                    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
                    st.download_button(
                        label="💾 Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"SIMPOL_Reporte_{f_inicio}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.warning("No existen registros para el período seleccionado.")

        except Exception as e:
            st.error(f"Error al generar reporte: {e}")