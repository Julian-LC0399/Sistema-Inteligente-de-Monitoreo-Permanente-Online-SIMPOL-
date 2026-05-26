import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import io

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF (ESTILO BANCO CARONÍ)
# =====================================================================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Corporativo
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte de servidor", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE PERSISTENCIA Y CONSULTA A BASE DE DATOS
# =====================================================================
def archivar_reporte_en_bd(bin_data, nombre, formato, user_id):
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            query = """INSERT INTO reportes_archivados 
                       (nombre_archivo, formato, contenido, usuario_id, tamanio_kb) 
                       VALUES (%s, %s, %s, %s, %s)"""
            tamanio_kb = f"{round(len(bin_data) / 1024, 2)} KB"
            cursor.execute(query, (nombre, formato, bytes(bin_data), user_id, tamanio_kb))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        st.error(f"Error al archivar: {e}")
    finally:
        if conn and conn.is_connected(): 
            conn.close()
    return False

def obtener_lista_servidores():
    conn = conectar_bd()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ip, nombre_alias FROM servidores ORDER BY nombre_alias ASC")
        servidores = cursor.fetchall()
        cursor.close()
        return servidores
    except Exception as e:
        st.error(f"Error al obtener servidores: {e}")
        return []
    finally:
        conn.close()

def obtener_historico_reportes():
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    r.id, 
                    r.nombre_archivo, 
                    r.formato, 
                    r.tamanio_kb, 
                    r.fecha_generacion,
                    COALESCE(u.usuario, 'Sistema') AS registrado_por
                FROM reportes_archivados r
                LEFT JOIN usuarios u ON r.usuario_id = u.id
                ORDER BY r.id DESC 
                LIMIT 20
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            return resultados
    except Exception as e:
        st.error(f"Error al obtener historial de base de datos: {e}")
        return []
    finally:
        if conn and conn.is_connected(): 
            conn.close()
    return []

def descargar_contenido_blob(reporte_id):
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT contenido FROM reportes_archivados WHERE id = %s", (int(reporte_id),))
            fila = cursor.fetchone()
            cursor.close()
            return fila["contenido"] if fila else None
    except: 
        return None
    finally:
        if conn and conn.is_connected(): 
            conn.close()

def obtener_datos_monitoreo(f_inicio, f_fin, ip_servidor=None):
    conn = conectar_bd()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        dt_inicio = datetime.combine(f_inicio, time.min)
        dt_fin = datetime.combine(f_fin, time.max)
        
        if ip_servidor:
            query = """
                SELECT m.fecha_registro, s.nombre_alias, m.val_cpu, m.val_ram, m.val_disco_1
                FROM monitoreo m
                INNER JOIN servidores s ON m.ip_servidor = s.ip
                WHERE m.fecha_registro BETWEEN %s AND %s AND m.ip_servidor = %s
                ORDER BY m.fecha_registro DESC
                LIMIT 500
            """
            cursor.execute(query, (dt_inicio, dt_fin, ip_servidor))
        else:
            query = """
                SELECT m.fecha_registro, s.nombre_alias, m.val_cpu, m.val_ram, m.val_disco_1
                FROM monitoreo m
                INNER JOIN servidores s ON m.ip_servidor = s.ip
                WHERE m.fecha_registro BETWEEN %s AND %s
                ORDER BY m.fecha_registro DESC
                LIMIT 500
            """
            cursor.execute(query, (dt_inicio, dt_fin))
            
        datos = cursor.fetchall()
        cursor.close()
        return datos
    except Exception as e:
        st.error(f"Error extrayendo telemetría: {e}")
        return []
    finally:
        conn.close()

# =====================================================================
# VISTA PRINCIPAL DE LA PANTALLA
# =====================================================================
def mostrar_pantalla(nombre_analista, usuario_id):
    st.markdown('<h2 style="color:#003366;">📋 Centro de Reportes</h2>', unsafe_allow_html=True)
    
    # === 1. SECCIÓN DE GENERACIÓN ===
    with st.expander("🛠️ Generar Nuevo Reporte Técnico"):
        col1, col2 = st.columns(2)
        f_inicio = col1.date_input("Fecha Inicio", datetime.now() - timedelta(days=1))
        f_fin = col2.date_input("Fecha Fin", datetime.now())
        
        lista_srv = obtener_lista_servidores()
        opciones_srv = {"Todos los Servidores": None}
        for s in lista_srv:
            opciones_srv[f"{s['nombre_alias']} ({s['ip']})"] = s['ip']
            
        seleccion_srv = st.selectbox("Filtrar por Servidor", list(opciones_srv.keys()))
        ip_seleccionada = opciones_srv[seleccion_srv]
        
        tipo_formato = st.selectbox("Formato de Salida", ["PDF", "CSV"])
        
        if st.button("🚀 Generar y Archivar"):
            st.info("Compilando datos reales de la tabla monitoreo...")
            
            registros_telemetria = obtener_datos_monitoreo(f_inicio, f_fin, ip_seleccionada)
            
            if not registros_telemetria:
                st.warning("⚠️ No se encontraron registros de monitoreo para los criterios seleccionados.")
            
            buffer = io.BytesIO()
            
            if tipo_formato == "PDF":
                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 8, f"Analisis de infraestructura solicitado por: {nombre_analista}", 0, 1)
                pdf.cell(0, 8, f"Servidor bajo analisis: {seleccion_srv}", 0, 1)
                pdf.cell(0, 8, f"Rango auditado: {f_inicio} al {f_fin}", 0, 1)
                pdf.cell(0, 8, f"Total registros evaluados: {len(registros_telemetria)}", 0, 1)
                pdf.ln(5)
                
                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(230, 240, 250)
                pdf.cell(45, 7, "Fecha/Hora", 1, 0, "C", True)
                pdf.cell(55, 7, "Servidor", 1, 0, "C", True)
                pdf.cell(30, 7, "CPU (%)", 1, 0, "C", True)
                pdf.cell(30, 7, "RAM (GB)", 1, 0, "C", True)
                pdf.cell(30, 7, "Disco 1 (%)", 1, 1, "C", True)
                
                pdf.set_font("Arial", "", 9)
                for reg in registros_telemetria[:100]:
                    f_reg = reg['fecha_registro'].strftime("%d/%m %H:%M") if isinstance(reg['fecha_registro'], datetime) else str(reg['fecha_registro'])
                    pdf.cell(45, 6, f_reg, 1, 0, "C")
                    pdf.cell(55, 6, str(reg['nombre_alias']), 1, 0, "L")
                    pdf.cell(30, 6, f"{reg['val_cpu']}%", 1, 0, "C")
                    pdf.cell(30, 6, f"{reg['val_ram']} GB", 1, 0, "C")
                    pdf.cell(30, 6, f"{reg['val_disco_1']}%", 1, 1, "C")
                
                pdf_output = pdf.output(dest='S')
                if isinstance(pdf_output, str):
                    pdf_output = pdf_output.encode('latin1')
                buffer.write(pdf_output)
                
            else:
                csv_lines = ["Fecha_Registro,Servidor,Valor_CPU,Valor_RAM,Espacio_Disco1\n"]
                for reg in registros_telemetria:
                    f_reg = reg['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(reg['fecha_registro'], datetime) else str(reg['fecha_registro'])
                    csv_lines.append(f"{f_reg},{reg['nombre_alias']},{reg['val_cpu']},{reg['val_ram']},{reg['val_disco_1']}\n")
                
                csv_text = "".join(csv_lines)
                buffer.write(csv_text.encode('utf-8'))
            
            bin_data = buffer.getvalue()
            nombre_final = f"Reporte_SIMPOL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{tipo_formato.lower()}"
            
            if archivar_reporte_en_bd(bin_data, nombre_final, tipo_formato, usuario_id):
                st.success(f"✅ ¡Éxito! Archivo '{nombre_final}' guardado.")
                st.rerun()
            else:
                st.error("No se pudo archivar el reporte.")

    # === 2. TABLA DEL HISTORIAL CON COLORES CORPORATIVOS ===
    st.markdown("### 📜 Historial de reportes Almacenados")
    
    historico = obtener_historico_reportes()
    
    if not historico:
        st.info("No se encontraron reportes archivados en el sistema.")
    else:
        # Estilos CSS optimizados para las etiquetas (Badges) de formato
        st.markdown("""
            <style>
                .badge-pdf {
                    background-color: #ffcccc; color: #cc0000; padding: 2px 8px;
                    border-radius: 4px; font-weight: bold; font-size: 11px;
                }
                .badge-csv {
                    background-color: #d4edda; color: #155724; padding: 2px 8px;
                    border-radius: 4px; font-weight: bold; font-size: 11px;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Distribución de anchos compartida e idéntica
        layout_grid = [4.0, 1.2, 1.3, 2.2, 2.0, 1.5]
        
        # 1. CABECERA: Fondo Azul Marino Corporativo (#003366) con Texto Blanco
        with st.container():
            st.markdown(
                """
                <div style='background-color: #003366; padding: 12px; border-radius: 6px 6px 0px 0px; margin-bottom: -1px;'>
                    <div style='display: flex; color: white; font-weight: bold; font-size: 13px;'>
                        <div style='width: 32.5%; text-align: left;'>Nombre del Archivo</div>
                        <div style='width: 9.7%; text-align: center;'>Formato</div>
                        <div style='width: 10.5%; text-align: center;'>Tamaño</div>
                        <div style='width: 17.8%; text-align: center;'>Fecha Registro</div>
                        <div style='width: 16.2%; text-align: right;'>Registrado Por</div>
                        <div style='width: 13.3%; text-align: center;'>Acción</div>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        # 2. CUERPO: Filas Nativas con fondo alternado sutil (Azul Claro Institucional #E6F0FA)
        for idx, item in enumerate(historico):
            fecha_str = item['fecha_generacion'].strftime("%Y-%m-%d %H:%M") if isinstance(item['fecha_generacion'], datetime) else str(item['fecha_generacion'])
            badge_class = "badge-pdf" if item['formato'] == "PDF" else "badge-csv"
            
            # Alternamos el color de fondo por cada registro de forma elegante
            fondo_fila = "#E6F0FA" if idx % 2 == 0 else "#FFFFFF"
            
            st.markdown(f"<div style='background-color: {fondo_fila}; padding: 8px 12px; border-left: 1px solid #ccc; border-right: 1px solid #ccc; border-bottom: 1px solid #eee; margin-top: -1px;'>", unsafe_allow_html=True)
            
            c1, c2, c3, c4, c5, c6 = st.columns(layout_grid)
            
            c1.write(f"📄 {item['nombre_archivo']}")
            c2.markdown(f"<div style='text-align:center; padding-top:4px;'><span class='{badge_class}'>{item['formato']}</span></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:center; color:#333; padding-top:4px;'>{item['tamanio_kb']}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='text-align:center; color:#333; font-family:monospace; padding-top:4px;'>{fecha_str}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div style='text-align:right; padding-top:4px;'>👤 {item['registrado_por']}</div>", unsafe_allow_html=True)
            
            with c6:
                blob_data = descargar_contenido_blob(item['id'])
                if blob_data:
                    st.download_button(
                        label="📥 Descargar",
                        data=blob_data,
                        file_name=item['nombre_archivo'],
                        mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                        key=f"dl_corp_{item['id']}",
                        use_container_width=True
                    )
                else:
                    st.caption("Vacío")
                    
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Nombre Completo")
    id_usuario = st.session_state.get("id", 1)
    
    mostrar_pantalla(cargo_usuario, id_usuario)