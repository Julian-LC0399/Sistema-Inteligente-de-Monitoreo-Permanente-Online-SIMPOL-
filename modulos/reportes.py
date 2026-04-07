import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta

# 1. CLASE PDF PROFESIONAL (Nativa)
class PDF(FPDF):
    def header(self):
        # Título institucional
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) 
        self.cell(0, 10, "BANCO CARONI - REPORTE DE GESTION SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} - Confidencial Unidad de Tecnologia", 0, 0, "C")

def obtener_datos_nativos(f_inicio, f_fin):
    """Consulta la BD y retorna una lista de diccionarios (Sin Pandas)."""
    datos = []
    try:
        conn = conectar_bd()
        if conn:
            # Importante: dictionary=True permite usar nombres de columnas en vez de indices
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, nombre_csu, uso_cpu, uso_ram, estado_sistema 
                FROM monitoreo 
                WHERE fecha_registro BETWEEN %s AND %s
                ORDER BY fecha_registro DESC
            """
            cursor.execute(query, (f_inicio, f_fin))
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error en consulta de base de datos: {e}")
    return datos

def mostrar_pantalla():
    # --- ESTILOS CSS PARA BOTONES Y TABLAS ---
    st.markdown("""
        <style>
            /* Arregla el texto de TODOS los botones para que sea negro y legible */
            div.stButton > button {
                color: #000000 !important;
                background-color: #f0f2f6 !important;
                border: 1px solid #d1d3d8 !important;
                font-weight: bold !important;
            }
            /* Estilo de la tabla de vista previa */
            [data-testid="stTable"] {
                background-color: white !important;
                border: 1px solid #dee2e6 !important;
                border-radius: 4px;
            }
            [data-testid="stTable"] td {
                color: black !important;
                border: 1px solid #eee !important;
            }
            [data-testid="stTable"] th {
                background-color: #003366 !important;
                color: white !important;
                text-align: center !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366;'>📄 Centro de Reportes e Historial</h2>", unsafe_allow_html=True)
    st.info("Seleccione el rango de fechas para generar el documento de auditoría.")

    # Filtros de búsqueda
    with st.container(border=True):
        col1, col2 = st.columns(2)
        fecha_i = col1.date_input("Fecha Inicial", datetime.now() - timedelta(days=7))
        fecha_f = col2.date_input("Fecha Final", datetime.now())

        # Botón con texto ahora visible (Negro por CSS)
        if st.button("🔍 PROCESAR DATOS DEL PERIODO", use_container_width=True):
            # Convertir fechas a formato datetime para la BD
            dt_i = datetime.combine(fecha_i, datetime.min.time())
            dt_f = datetime.combine(fecha_f, datetime.max.time())
            
            datos = obtener_datos_nativos(dt_i, dt_f)

            if not datos:
                st.warning("No se encontraron registros para las fechas seleccionadas.")
            else:
                st.success(f"Procesados {len(datos)} registros exitosamente.")
                
                # --- VISTA PREVIA (100% NATIVA) ---
                st.markdown("### 📋 Vista Previa (Ultimos 10)")
                vista = []
                for d in datos[:10]:
                    vista.append({
                        "FECHA": d['fecha_registro'].strftime('%d/%m/%y %H:%M'),
                        "CSU": d['nombre_csu'],
                        "CPU %": f"{d['uso_cpu']}%",
                        "RAM %": f"{d['uso_ram']}%",
                        "ESTADO": d['estado_sistema']
                    })
                st.table(vista)

                # --- GENERACION DE PDF ---
                pdf = PDF()
                pdf.add_page()
                
                # Encabezados de tabla en PDF
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", "B", 10)
                
                # Definir anchos de columna
                pdf.cell(35, 10, "Fecha/Hora", 1, 0, "C", True)
                pdf.cell(35, 10, "Unidad CSU", 1, 0, "C", True)
                pdf.cell(25, 10, "CPU %", 1, 0, "C", True)
                pdf.cell(25, 10, "RAM %", 1, 0, "C", True)
                pdf.cell(65, 10, "Estado del Sistema", 1, 1, "C", True)

                # Filas de la tabla (Limitado a los ultimos 200 por rendimiento de PDF)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 9)
                
                for row in datos[:200]:
                    pdf.cell(35, 8, row['fecha_registro'].strftime('%d/%m/%y %H:%M'), 1)
                    pdf.cell(35, 8, str(row['nombre_csu']), 1)
                    pdf.cell(25, 8, f"{row['uso_cpu']}%", 1, 0, "C")
                    pdf.cell(25, 8, f"{row['uso_ram']}%", 1, 0, "C")
                    pdf.cell(65, 8, str(row['estado_sistema']).upper(), 1, 1, "C")

                # Preparar descarga de archivo
                try:
                    # 'S' retorna el PDF como un string de bytes
                    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
                    
                    st.download_button(
                        label="💾 DESCARGAR REPORTE EN PDF",
                        data=pdf_bytes,
                        file_name=f"Reporte_SIMPOL_{fecha_i}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error tecnico al construir el PDF: {e}")