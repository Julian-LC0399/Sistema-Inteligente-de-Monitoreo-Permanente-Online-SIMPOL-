import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from utils import get_resource_path

class PDF(FPDF):
    def header(self):
        try:
            # Intentar cargar el logo institucional del banco
            ruta_logo = get_resource_path("logo-banco.jpg")
            self.image(ruta_logo, 10, 8, 33)
        except: 
            pass
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Corporativo Banco Caroní
        self.set_x(45)
        self.cell(0, 10, "SIMPOL - REPORTE DE GESTIÓN CSU", 0, 1, "L")
        self.set_font("Arial", "", 10)
        self.set_text_color(100, 100, 100) # Gris para la fecha
        self.set_x(45)
        self.cell(0, 5, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()} - Confidencial Banco Caroní", 0, 0, "C")

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>📊 Reportes de Telemetría</h2>", unsafe_allow_html=True)
    st.info("Nota: Los estados (Normal/Precaución/Crítico) son inmutables y reflejan la configuración vigente al momento de la captura.")

    # --- FORMULARIO DE FILTRADO ---
    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        f_inicio = col1.date_input("Desde", datetime.now() - timedelta(days=7))
        f_fin = col2.date_input("Hasta", datetime.now())
        btn_generar = st.form_submit_button("🔍 Generar Vista Previa", use_container_width=True)

    if btn_generar:
        try:
            conn = conectar_bd()
            query = f"""
                SELECT 
                    fecha_registro as Fecha, 
                    nombre_csu as CSU, 
                    uso_cpu as 'CPU %', 
                    uso_ram as 'RAM %', 
                    estado_sistema as ESTADO 
                FROM monitoreo 
                WHERE DATE(fecha_registro) BETWEEN '{f_inicio}' AND '{f_fin}' 
                ORDER BY fecha_registro DESC
            """
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                # 1. Visualización en Pantalla
                iconos = {
                    "CRITICO": "🔴 CRÍTICO", "CRÍTICO": "🔴 CRÍTICO", 
                    "ADVERTENCIA": "🟠 PRECAUCIÓN", "PRECAUCIÓN": "🟠 PRECAUCIÓN", 
                    "NORMAL": "🟢 NORMAL"
                }
                df_visual = df.copy()
                df_visual["ESTADO"] = df_visual["ESTADO"].apply(lambda x: iconos.get(str(x).upper(), x))

                st.markdown(f"### Se encontraron {len(df)} registros")
                st.dataframe(df_visual, use_container_width=True, hide_index=True)

                # 2. Generación de PDF Profesional
                pdf = PDF()
                pdf.add_page()
                
                # --- ENCABEZADOS DE TABLA CON COLOR DEL BANCO ---
                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(0, 51, 102)   # FONDO: Azul Banco Caroní
                pdf.set_text_color(255, 255, 255) # TEXTO: Blanco para contraste
                
                columnas = ["Fecha/Hora", "CSU", "CPU", "RAM", "Estado"]
                anchos = [45, 35, 25, 25, 60]
                
                for i, col in enumerate(columnas):
                    pdf.cell(anchos[i], 10, col, 1, 0, "C", True)
                pdf.ln()

                # --- DATOS DE LA TABLA ---
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(0, 0, 0) # Volver a texto negro para los datos
                
                # Solo exportamos los últimos 500 para evitar archivos pesados
                for _, row in df.head(500).iterrows():
                    pdf.cell(anchos[0], 8, str(row["Fecha"]), 1)
                    pdf.cell(anchos[1], 8, str(row["CSU"]), 1)
                    pdf.cell(anchos[2], 8, f"{row['CPU %']}%", 1, 0, "C")
                    pdf.cell(anchos[3], 8, f"{row['RAM %']}%", 1, 0, "C")
                    
                    # Limpiar texto para evitar errores de codificación
                    status_raw = str(row["ESTADO"]).upper().replace("ADVERTENCIA", "PRECAUCION").replace("Í", "I")
                    pdf.cell(anchos[4], 8, status_raw, 1, 1, "C")

                # Salida del PDF
                pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
                
                st.download_button(
                    label="💾 Descargar Reporte PDF (Formato Oficial)",
                    data=pdf_bytes,
                    file_name=f"SIMPOL_Reporte_{f_inicio}_al_{f_fin}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("No existen registros para el período seleccionado.")

        except Exception as e:
            st.error(f"Error al generar reporte: {e}")