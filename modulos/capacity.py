import streamlit as st
import io
import traceback
from datetime import datetime
from fpdf import FPDF
from database import obtener_lista_servidores, obtener_datos_historicos, registrar_proyeccion

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF (ESTILO BANCO CARONÍ)
# =====================================================================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Corporativo
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Informe Tecnico de Planificacion de Capacidad (Capacity Planning)", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Pagina {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE PERSISTENCIA EN TABLA EXCLUSIVA (NUEVA ARQUITECTURA)
# =====================================================================
def archivar_reporte_capacity(bin_data, nombre, formato, metrica, ip, user_id):
    """Guarda el archivo en la nueva tabla exclusiva 'reportes_capacity_archivados'."""
    from database import conectar_bd
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            calc_kb = len(bin_data) / 1024.0
            tamanio_sanitizado = f"{calc_kb:.2f} KB"
            
            id_limpio = None
            if user_id:
                try: id_limpio = int(float(str(user_id).strip()))
                except: id_limpio = None
            
            query = """
                INSERT INTO reportes_capacity_archivados 
                (nombre_archivo, formato, metrica_analizada, ip_servidor, contenido, usuario_id, tamanio_kb) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, formato, metrica, ip, bytes(bin_data), id_limpio, tamanio_sanitizado))
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error en Bóveda Dedicada Capacity ({formato}): {e}\n")
    return False

def obtener_historico_capacity():
    """Recupera metadatos optimizados desde la tabla exclusiva (Carga veloz sin BLOB)."""
    from database import conectar_bd
    conn = None
    resultado = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, nombre_archivo, formato, metrica_analizada, ip_servidor, tamanio_kb, fecha_generacion 
                FROM reportes_capacity_archivados 
                ORDER BY id DESC LIMIT 20
            """
            cursor.execute(query)
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error leyendo historial exclusivo Capacity: {e}\n")
    return resultado

def descargar_blob_capacity(reporte_id):
    """Carga perezosa (Lazy Loading) del contenido LONGBLOB desde la tabla dedicada."""
    from database import conectar_bd
    conn = None
    blob_data = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_capacity_archivados WHERE id = %s"
            cursor.execute(query, (int(reporte_id),))
            fila = cursor.fetchone()
            if fila:
                blob_data = fila["contenido"]
            cursor.close()
            conn.close()
    except Exception as e:
        with open("simpol_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Error extrayendo BLOB Dedicado ID {reporte_id}: {e}\n")
    return blob_data

# =====================================================================
# VISTA PRINCIPAL DE LA PANTALLA (ESTRUCTURADA EN PESTAÑAS)
# =====================================================================
def mostrar_pantalla(nombre_analista, usuario_id, usuario_login):
    if "cap_listo" not in st.session_state:
        st.session_state["cap_listo"] = False
        st.session_state["cap_csv"] = None
        st.session_state["cap_pdf"] = None
        st.session_state["cap_name_csv"] = ""
        st.session_state["cap_name_pdf"] = ""

    st.markdown('<h2 style="color:#003366;">📈 Capacity Planning - Banco Caroní</h2>', unsafe_allow_html=True)
    st.markdown(f"👤 **Cargo Responsable:** {nombre_analista} (`usuario: {usuario_login}`)", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab_simulacion, tab_historial = st.tabs(["📊 Nueva Proyección", "📜 Consultar Bóveda de Capacity"])

    # =====================================================================
    # PESTAÑA 1: GENERACIÓN DE PROYECCIONES EN VIVO
    # =====================================================================
    with tab_simulacion:
        servidores = obtener_lista_servidores()
        if not servidores:
            st.warning("⚠️ No hay servidores activos para realizar proyecciones.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        seleccion = st.selectbox("Seleccione Servidor para Análisis de Capacidad:", list(opciones.keys()), key="cap_serv_sel")
        serv_info = opciones[seleccion]
        ip_sel = serv_info['ip']

        col1, col2 = st.columns(2)
        with col1:
            metrica_label = st.selectbox(
                "Métrica / Sensor a Proyectar:", 
                ["CPU", "RAM", "DISCO 1 (C:\\)", "DISCO 2 (F:\\)", "DISCO 3 (E:\\)", "DISCO 4 (D:\\)", "DISCO 5 (G:\\)", "RED", "PING"], 
                key="cap_metrica_sel"
            )
            mapa_metrica = {
                "CPU": "val_cpu", "RAM": "val_ram", 
                "DISCO 1 (C:\\)": "val_disco_1", "DISCO 2 (F:\\)": "val_disco_2", 
                "DISCO 3 (E:\\)": "val_disco_3", "DISCO 4 (D:\\)": "val_disco_4", 
                "DISCO 5 (G:\\)": "val_disco_5",
                "RED": "val_red", "PING": "val_latencia"
            }
            columna_db = mapa_metrica[metrica_label]
            
        with col2:
            dias_proy = st.slider("Días a proyectar:", 7, 90, 30, key="cap_slider_dias")
        
        # Validación estricta e indexación por Sensor de Disco
        if "DISCO" in metrica_label:
            num_disco = int(metrica_label.split(" ")[1])
            if serv_info.get(f'id_sensor_disco_{num_disco}', 0) == 0:
                st.error(f"❌ El volumen seleccionado ({metrica_label}) no se encuentra indexado ni activo en este servidor.")
                return

        datos = obtener_datos_historicos(ip_sel)
        if len(datos) < 5:
            st.error(f"❌ Datos insuficientes para {seleccion}. Se requieren al menos 5 registros históricos.")
            return

        valores = [d[columna_db] for d in datos]
        valor_actual = sum(valores[:5]) / 5  
        
        if "DISCO" in metrica_label or metrica_label == "RAM":
            factor_reduccion = 0.92 if "DISCO" in metrica_label else 0.95
            valor_proyectado = max(0.0, valor_actual * factor_reduccion)
        else:
            factor_crecimiento = 1.05
            valor_proyectado = valor_actual * factor_crecimiento
            if metrica_label == "CPU":
                valor_proyectado = min(100.0, valor_proyectado)

        st.markdown(f'<h4 style="color:#003366; margin-top:20px;">Tendencia Proyectada: {metrica_label}</h4>', unsafe_allow_html=True)
        
        h_base = 150
        y_actual = h_base - (min(valor_actual, 100) * 1.2)
        y_proy = h_base - (min(valor_proyectado, 100) * 1.2)
        puntos = f"0,{h_base} 0,{y_actual} 150,{y_actual} 300,{y_proy} 300,{h_base}"
        simbolo_unidad = "% Disp." if ("DISCO" in metrica_label or metrica_label == "RAM") else ("%" if metrica_label == "CPU" else ("Mb/s" if metrica_label == "RED" else "ms"))

        st.markdown(f"""
        <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <svg width="100%" height="180" viewBox="0 0 300 180">
                <line x1="0" y1="{h_base}" x2="300" y2="{h_base}" stroke="#ccc" stroke-width="2" />
                <polyline points="{puntos}" fill="rgba(0, 51, 102, 0.15)" stroke="#003366" stroke-width="3" />
                <circle cx="0" cy="{y_actual}" r="4" fill="#2c3e50" />
                <circle cx="300" cy="{y_proy}" r="4" fill="#003366" />
                <text x="5" y="{y_actual - 10}" font-size="12" fill="#2c3e50">Hoy: {valor_actual:.1f} {simbolo_unidad}</text>
                <text x="180" y="{y_proy - 10}" font-size="12" fill="#003366" font-weight="bold">Prox: {valor_proyectado:.1f} {simbolo_unidad}</text>
                <text x="0" y="170" font-size="10" fill="#999">Estado Actual</text>
                <text x="240" y="170" font-size="10" fill="#999">+{dias_proy} días</text>
            </svg>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        
        veredicto = "CRÍTICO" if (("DISCO" in metrica_label or metrica_label == "RAM") and valor_proyectado <= 10.0) or (metrica_label == "CPU" and valor_proyectado >= 85.0) else "SUFICIENTE"
        
        if veredicto == "CRÍTICO":
            st.error(f"🚩 ALERTA DE CAPACITY PLANNING: Se proyecta el colapso o agotamiento de {metrica_label} en la ventana de {dias_proy} días.")
        else:
            st.success(f"✅ Previsión de Capacidad: El recurso {metrica_label} posee suficiente tolerancia operativa.")

        # Botón de Procesamiento
        if st.button("🚀 REGISTRAR Y GENERAR EXPEDIENTES DE CAPACITY", use_container_width=True, key="btn_gen_capacity_files"):
            try:
                timestamp_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Compilar CSV
                output_csv = io.StringIO()
                output_csv.write("Fecha Analisis,IP Servidor,Nombre,Metrica Analizada,Ventana Dias,Valor Actual,Valor Proyectado,Unidad,Veredicto,Usuario,Cargo\n")
                output_csv.write(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{ip_sel},{serv_info['nombre_alias']},{metrica_label},"
                    f"{dias_proy},{valor_actual:.2f},{valor_proyectado:.2f},{simbolo_unidad},{veredicto},{usuario_login},{nombre_analista}\n"
                )
                csv_binario = output_csv.getvalue().encode('utf-8', errors='ignore')
                nombre_csv = f"Capacity_{ip_sel}_{metrica_label.replace(' ', '_').replace('\\','')}_{timestamp_actual}.csv"

                # Compilar PDF (A4 Horizontal)
                pdf = PDF(orientation='L', unit='mm', format='A4')
                pdf.add_page()
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, f"Fecha de Analisis: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
                
                pdf.cell(0, 8, f"Usuario: {usuario_login}", 0, 1)
                pdf.cell(0, 8, f"Cargo: {nombre_analista}", 0, 1)
                pdf.ln(4)
                
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                cols = [
                    ("IP Servidor", 35), ("Nombre Alias", 40), ("Métrica/Sensor", 40), 
                    ("Ventana", 25), ("Valor Actual", 30), ("Valor Proyectado", 35), ("Veredicto Técnico", 40)
                ]
                for txt, w in cols:
                    pdf.cell(w, 8, txt, 1, 0, "C", True)
                pdf.ln()

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 9)
                pdf.cell(35, 7, str(ip_sel), 1, 0, "C")
                pdf.cell(40, 7, str(serv_info['nombre_alias']), 1, 0, "C")
                pdf.cell(40, 7, str(metrica_label), 1, 0, "C")
                pdf.cell(25, 7, f"+{dias_proy} dias", 1, 0, "C")
                pdf.cell(30, 7, f"{valor_actual:.2f} {simbolo_unidad}", 1, 0, "C")
                pdf.cell(35, 7, f"{valor_proyectado:.2f} {simbolo_unidad}", 1, 0, "C")
                
                if veredicto == "CRÍTICO":
                    pdf.set_text_color(200, 0, 0)
                    pdf.set_font("Arial", "B", 9)
                else:
                    pdf.set_text_color(0, 128, 0)
                pdf.cell(40, 7, str(veredicto), 1, 1, "C")
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 10)
                pdf.ln(10)
                pdf.cell(0, 6, "Declaracion de Riesgos Operativos e Infraestructura:", 0, 1)
                pdf.set_font("Arial", "I", 9)
                if veredicto == "CRÍTICO":
                    pdf.multi_cell(0, 5, f"ALERTA: Se ha determinado un riesgo inminente por saturacion del recurso '{metrica_label}' dentro del periodo evaluado. Se requiere el escalamiento inmediato al departamento de arquitectura de servidores del Banco Caroni.")
                else:
                    pdf.multi_cell(0, 5, f"EVALUACION CONFORME: El recurso '{metrica_label}' opera dentro de las metricas basales aceptables con holgura suficiente.")

                pdf_str = pdf.output(dest='S')
                pdf_binario = pdf_str.encode('latin-1', errors='ignore') if isinstance(pdf_str, str) else bytes(pdf_str)
                nombre_pdf = f"Capacity_{ip_sel}_{metrica_label.replace(' ', '_').replace('\\','')}_{timestamp_actual}.pdf"

                st.session_state["cap_csv"] = csv_binario
                st.session_state["cap_pdf"] = pdf_binario
                st.session_state["cap_name_csv"] = nombre_csv
                st.session_state["cap_name_pdf"] = nombre_pdf
                st.session_state["cap_listo"] = True

                # Persistencia
                archivar_reporte_capacity(csv_binario, nombre_csv, 'CSV', metrica_label, ip_sel, usuario_id)
                archivar_reporte_capacity(pdf_binario, nombre_pdf, 'PDF', metrica_label, ip_sel, usuario_id)
                
                registrar_proyeccion(
                    usuario_id=usuario_id, ip_servidor=ip_sel, metrica=metrica_label,
                    actual=float(valor_actual), proyectado=float(valor_proyectado), veredicto=veredicto
                )
                st.success("🎉 ¡Expediente guardado con éxito en la tabla de Capacity!")
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error("⚠️ Error procesando expedientes de Capacity.")
                with open("simpol_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Error critico en capacity.py: {e}\n{traceback.format_exc()}\n")

        if st.session_state["cap_listo"]:
            st.markdown("---")
            d_col1, d_col2 = st.columns(2)
            d_col1.download_button(
                label="⬇️ Descargar Simulación Actual (CSV)", 
                data=st.session_state["cap_csv"], 
                file_name=st.session_state["cap_name_csv"], 
                mime="text/csv", 
                key="dl_cap_csv_btn"
            )
            d_col2.download_button(
                label="⬇️ Descargar Informe Firmado Actual (PDF)", 
                data=st.session_state["cap_pdf"], 
                file_name=st.session_state["cap_name_pdf"], 
                mime="application/pdf", 
                key="dl_cap_pdf_btn"
            )

    # =====================================================================
    # PESTAÑA 2: TABLA CORPORATIVA DE HISTORIAL (MUESTRA REPORTES CAPACITY)
    # =====================================================================
    with tab_historial:
        st.markdown('<h3 style="color:#003366; margin-top:10px;">📜 Bóveda Exclusiva de Capacity Planning</h3>', unsafe_allow_html=True)
        st.write("Consulta directa e inmediata de expedientes generados previamente:")
        
        historico_archivos = obtener_historico_capacity()
        
        if not historico_archivos:
            st.info("📭 No hay expedientes grabados en la tabla dedicada de Capacity.")
        else:
            layout_grid = [3.5, 1.8, 1.2, 1.5, 2.0, 1.5]
            
            st.markdown(
                """
                <div style='background-color: #003366; padding: 12px; border-radius: 6px 6px 0px 0px; margin-bottom: -1px;'>
                    <div style='display: flex; color: white; font-weight: bold; font-size: 13px;'>
                        <div style='width: 30.4%; text-align: left;'>Nombre del Archivo</div>
                        <div style='width: 15.6%; text-align: center;'>Métrica / Sensor</div>
                        <div style='width: 10.4%; text-align: center;'>Formato</div>
                        <div style='width: 13.0%; text-align: center;'>Tamaño</div>
                        <div style='width: 17.4%; text-align: right;'>Fecha Registro</div>
                        <div style='width: 13.2%; text-align: center;'>Acción</div>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            for idx, item in enumerate(historico_archivos):
                f_gen = item['fecha_generacion'].strftime('%d/%m/%Y %H:%M') if item['fecha_generacion'] else 'N/A'
                fondo_fila = "#E6F0FA" if idx % 2 == 0 else "#FFFFFF"
                
                st.markdown(f"<div style='background-color: {fondo_fila}; padding: 8px 12px; border-left: 1px solid #ccc; border-right: 1px solid #ccc; border-bottom: 1px solid #eee; margin-top: -1px;'>", unsafe_allow_html=True)
                
                c1, c2, c3, c4, c5, c6 = st.columns(layout_grid)
                
                c1.write(f"📄 {item['nombre_archivo']}")
                c2.markdown(f"<div style='text-align:center; font-weight:500; padding-top:4px;'>📊 {item['metrica_analizada']}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div style='text-align:center; padding-top:4px;'><span style='background-color:#e2e8f0; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold;'>{item['formato']}</span></div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='text-align:center; color:#333; padding-top:4px;'>{item['tamanio_kb']}</div>", unsafe_allow_html=True)
                c5.markdown(f"<div style='text-align:right; color:#333; padding-top:4px; font-family:monospace;'>{f_gen}</div>", unsafe_allow_html=True)
                
                with c6:
                    datos_binarios_historicos = descargar_blob_capacity(item['id'])
                    if datos_binarios_historicos:
                        mime_tipo = "text/csv" if item['formato'] == "CSV" else "application/pdf"
                        st.download_button(
                            label="📥 Descargar",
                            data=datos_binarios_historicos,
                            file_name=item['nombre_archivo'],
                            mime=mime_tipo,
                            key=f"btn_hist_cap_{item['id']}",
                            use_container_width=True
                        )
                    else:
                        st.caption("Error")
                        
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Nombre Completo")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "Usuario")
    
    mostrar_pantalla(cargo_usuario, id_usuario, login_usuario)