import streamlit as st
import pandas as pd
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta
from utils import get_resource_path

class PDF(FPDF):
    def header(self):
        try:
            # Uso de la utilidad de ruta para el logo institucional
            ruta_logo = get_resource_path("logo-banco.jpg")
            self.image(ruta_logo, 10, 8, 33)
        except: 
            pass
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Banco Caroní
        self.set_x(45)
        self.cell(0, 10, "SIMPOL - REPORTE DE GESTIÓN CSU", 0, 1, "L")
        self.ln(10)

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>📊 Reportes e inteligencia predictiva</h2>", unsafe_allow_html=True)

    # --- FORMULARIO DE FILTRADO ---
    with st.form("filtro_reportes"):
        col1, col2 = st.columns(2)
        f_inicio = col1.date_input("Desde", datetime.now() - timedelta(days=7))
        f_fin = col2.date_input("Hasta", datetime.now())
        btn_generar = st.form_submit_button("Consultar Histórico", use_container_width=True)

    if btn_generar:
        try:
            conn = conectar_bd()
            # SQL ACTUALIZADO: Se usa la tabla 'monitoreo' y la columna 'nombre_csu'
            query = f"""
                SELECT fecha_registro as Fecha, nombre_csu as CSU, uso_cpu as 'CPU %', uso_ram as 'RAM %' 
                FROM monitoreo 
                WHERE DATE(fecha_registro) BETWEEN '{f_inicio}' AND '{f_fin}' 
                ORDER BY fecha_registro DESC
            """
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                # --- LÓGICA DE SEMÁFORO (3 NIVELES: NORMAL, PRECAUCIÓN, CRÍTICO) ---
                # Recuperar umbrales de la sesión (con valores por defecto si no existen)
                u_cpu_crit = st.session_state.get("u_cpu_perc", 85)
                u_ram_crit = st.session_state.get("u_ram_perc", 90)
                u_cpu_warn = st.session_state.get("u_cpu_warn", 70)
                u_ram_warn = st.session_state.get("u_ram_warn", 75)
                
                def definir_estado(r):
                    # 1. Evaluación de nivel CRÍTICO (Rojo)
                    if r["CPU %"] >= u_cpu_crit or r["RAM %"] >= u_ram_crit:
                        return "🔴 CRÍTICO"
                    # 2. Evaluación de nivel PRECAUCIÓN (Amarillo)
                    elif r["CPU %"] >= u_cpu_warn or r["RAM %"] >= u_ram_warn:
                        return "🟠 PRECAUCIÓN"
                    # 3. Nivel NORMAL (Verde)
                    return "🟢 NORMAL"

                # Insertar la columna de estado visible solicitada
                df["ESTADO"] = df.apply(definir_estado, axis=1)
                
                st.success(f"Se encontraron {len(df)} registros en el periodo seleccionado.")
                
                # Visualización en la interfaz de Streamlit
                st.dataframe(
                    df, 
                    column_config={
                        "Fecha": st.column_config.DatetimeColumn("Fecha y Hora", format="D/M/Y h:mm A"),
                        "ESTADO": st.column_config.TextColumn("Estatus del Sistema")
                    }, 
                    use_container_width=True, 
                    hide_index=True
                )

                # --- GENERACIÓN DE ARCHIVO PDF ---
                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 10)
                
                # Encabezados de la tabla PDF
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                
                columnas = ["Fecha", "CSU", "CPU %", "RAM %", "Estatus"]
                anchos = [45, 35, 30, 30, 50] # Ajuste de anchos para el reporte
                
                for i in range(len(columnas)):
                    pdf.cell(anchos[i], 10, columnas[i], 1, 0, "C", 1)
                pdf.ln()

                # Contenido de la tabla PDF
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(0, 0, 0)
                
                # Limitamos a los primeros 200 registros en el PDF para evitar saturación de memoria
                for _, row in df.head(200).iterrows():
                    pdf.cell(anchos[0], 8, str(row["Fecha"]), 1)
                    pdf.cell(anchos[1], 8, str(row["CSU"]), 1)
                    pdf.cell(anchos[2], 8, f"{row['CPU %']}%", 1)
                    pdf.cell(anchos[3], 8, f"{row['RAM %']}%", 1)
                    # Limpiamos los emojis para el PDF ya que FPDF estándar no soporta Unicode/Emojis fácilmente
                    texto_estado = row["ESTADO"].replace("🟢 ", "").replace("🔴 ", "").replace("🟠 ", "")
                    pdf.cell(anchos[4], 8, texto_estado, 1, 1)

                # Preparar descarga
                pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
                
                st.divider()
                st.download_button(
                    label="💾 Descargar Reporte en PDF", 
                    data=pdf_output, 
                    file_name=f"Reporte_CSU_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("No se encontraron datos para el rango de fechas seleccionado.")
                
        except Exception as e:
            st.error(f"Error al generar el reporte: {e}")

# Ejecución del módulo
if __name__ == "__main__":
    mostrar_pantalla()