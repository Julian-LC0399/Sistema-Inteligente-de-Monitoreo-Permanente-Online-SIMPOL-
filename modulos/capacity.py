import streamlit as st
import io
import traceback
from datetime import datetime
from fpdf import FPDF
from database import conectar_bd, obtener_lista_servidores, obtener_datos_historicos

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF (ESTILO BANCO CARONÍ)
# =====================================================================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102) # Azul Corporativo Banco Caroní
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Informe Tecnico de Planificacion de Capacidad (Capacity Planning V4.0.3)", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# PERSISTENCIA EN TABLA DE PROYECCIONES
# =====================================================================
def registrar_proyeccion_v398(usuario_id, ip_servidor, metrica, t_gb, act_gb, act_pct, proy_gb, proy_pct, veredicto):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO proyecciones 
            (usuario_id, ip_servidor, metrica_analizada, 
             val_total_gb, val_actual_disponible_gb, val_actual_disponible_pct, 
             val_proyectado_total_gb, val_proyectado_disponible_gb, val_proyectado_disponible_pct, veredicto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (usuario_id, ip_servidor.strip(), metrica, t_gb, act_gb, act_pct, t_gb, proy_gb, proy_pct, veredicto))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error registrando proyeccion en tabla nucleo: {e}")
        if conn: conn.close()
        return False

# =====================================================================
# FUNCIONES DE PERSISTENCIA EN LOGS DE ARCHIVOS ANALÍTICOS
# =====================================================================
def guardar_reporte_capacity_bd(nombre_archivo, formato, metrica, ip_servidor, contenido_blob, usuario_id, alerta_id, tipo_alerta, tamanio_kb, total_gb, act_gb, proy_gb):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        bytes_actuales = float(act_gb) * 1024.0 * 1024.0 * 1024.0
        bytes_proyectados = float(proy_gb) * 1024.0 * 1024.0 * 1024.0
        
        query = """
            INSERT INTO reportes_capacity_archivados 
            (nombre_archivo, formato, metrica_analizada, ip_servidor, contenido, usuario_id, 
             alerta_id, tipo_alerta, analisis_total_gb, analisis_bytes_actuales, analisis_bytes_proyectados, tamanio_kb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (nombre_archivo, formato, metrica, ip_servidor.strip(), contenido_blob, usuario_id, 
                               alerta_id, tipo_alerta, total_gb, bytes_actuales, bytes_proyectados, tamanio_kb))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error registrando archivo analitico en BD: {e}")
        if conn: conn.close()
        return False

def listar_reportes_capacity_bd(ip_servidor):
    conn = conectar_bd()
    resultados = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, nombre_archivo, formato, metrica_analizada, ip_servidor, fecha_generacion, tamanio_kb
                FROM reportes_capacity_archivados
                WHERE TRIM(ip_servidor) = %s
                ORDER BY fecha_generacion DESC
            """
            cursor.execute(query, (ip_servidor.strip(),))
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error listando historico de capacity: {e}")
    return resultados

def descargar_blob_capacity(id_archivo):
    conn = conectar_bd()
    blob_data = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT contenido FROM reportes_capacity_archivados
                WHERE id = %s
            """
            cursor.execute(query, (id_archivo,))
            row = cursor.fetchone()
            if row:
                blob_data = row['contenido']
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error descargando binario de base de datos: {e}")
    return blob_data

# =====================================================================
# CALLBACKS PARA MANEJO DE ESTADOS REACTIVOS
# =====================================================================
def reset_reporte():
    st.session_state.reporte_generado = False

def disparar_reporte():
    st.session_state.reporte_generado = True

# =====================================================================
# VISTA Y CONTROLADOR PRINCIPAL DEL MÓDULO CAPACITY PLANNING
# =====================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">📈 Planificacion de Capacidad (Capacity Planning)</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Algoritmos de Tendencia Lineal e Infraestructura Virtual | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    if "sel_servidor" not in st.session_state:
        st.session_state.sel_servidor = "-- Seleccione un Servidor --"
    if "sel_metrica" not in st.session_state:
        st.session_state.sel_metrica = ""
    if "reporte_generado" not in st.session_state:
        st.session_state.reporte_generado = False

    pestana_analisis, pestana_boveda = st.tabs(["📊 Simulación y Análisis Técnico", "🗄️ Bóveda de Reportes Archivados"])

    try:
        servidores_activos = obtener_lista_servidores()
        if not servidores_activos:
            with pestana_analisis:
                st.info("💡 No hay servidores virtuales mapeados para realizar modelos de proyeccion.")
            return

        opciones_servidores = ["-- Seleccione un Servidor --"] + [s['nombre_alias'] for s in servidores_activos]

        with pestana_analisis:
            col_f1, col_f2 = st.columns([3, 1])
            with col_f1:
                servidor_sel = st.selectbox(
                    "1. Seleccione el Nodo de Infraestructura Virtual", 
                    options=opciones_servidores, 
                    key="sel_servidor",
                    on_change=reset_reporte
                )
            with col_f2:
                st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                if st.button("🧹 Limpiar Filtros", use_container_width=True):
                    st.session_state.sel_servidor = "-- Seleccione un Servidor --"
                    st.session_state.sel_metrica = ""
                    st.session_state.reporte_generado = False
                    st.rerun()

            if servidor_sel == "-- Seleccione un Servidor --":
                st.info("💡 Por favor, elija un servidor de la infraestructura para desplegar sus métricas disponibles.")
                return

            info_servidor = next((s for s in servidores_activos if s['nombre_alias'] == servidor_sel), None)
            ip_objetivo = str(info_servidor['ip']).strip()

            dict_metricas_config = {}
            if int(info_servidor.get('id_sensor_cpu') or 0) > 0:
                dict_metricas_config["Procesamiento (Uso % CPU)"] = {
                    "col_pct": "val_cpu", "col_total": None, "col_gb": None, "tipo": "consumo"
                }
            if int(info_servidor.get('id_sensor_ram') or 0) > 0:
                dict_metricas_config["Memoria Volatil (Disponible % RAM)"] = {
                    "col_pct": "val_ram_disponible_pct", "col_total": "val_ram_total_gb", "col_gb": "val_ram_disponible_gb", "tipo": "disponibilidad"
                }
            for d in range(1, 7):
                if int(info_servidor.get(f'id_sensor_disco_{d}') or 0) > 0:
                    letra_bd = info_servidor.get(f'letra_disco_{d}')
                    letra_limpia = str(letra_bd).replace('\\', '') if letra_bd else f"Disco {d}"
                    dict_metricas_config[f"Almacenamiento Libre Unidad {letra_limpia} (% Libre)"] = {
                        "col_pct": f"val_disco_{d}_pct_libre", "col_total": f"val_disco_{d}_total_gb", "col_gb": f"val_disco_{d}_libres_gb", "tipo": "disponibilidad"
                    }

            if not dict_metricas_config:
                st.warning("⚠️ El servidor seleccionado no posee sensores de hardware mapeados en el catalogo.")
                return

            metrica_sel = st.selectbox(
                "2. Seleccione la Metrica de Hardware a Modelar", 
                options=list(dict_metricas_config.keys()), 
                key="sel_metrica",
                on_change=reset_reporte
            )
            meta_metrica = dict_metricas_config[metrica_sel]

            st.markdown("#### ⚙️ Parametros del Escenario de Capacidad")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                dias_proyeccion = st.slider("Horizonte de simulacion (Dias a proyectar):", min_value=7, max_value=180, value=30, step=7, on_change=reset_reporte)
            with col_p2:
                porcentaje_ajuste_analista = st.slider("Factor de Ajuste de Crecimiento Adicional (%):", min_value=0, max_value=50, value=0, step=5, on_change=reset_reporte)

            conn_temp = conectar_bd()
            datos_diarios = []
            if conn_temp:
                try:
                    cursor_temp = conn_temp.cursor(dictionary=True)
                    c_pct = meta_metrica["col_pct"]
                    c_tot = meta_metrica["col_total"] if meta_metrica["col_total"] else "1"
                    c_gb = meta_metrica["col_gb"] if meta_metrica["col_gb"] else "1"
                    
                    query_diaria = f"""
                        SELECT DATE(fecha_registro) AS fecha_limpia, AVG({c_pct}) AS promedio_pct, MAX({c_tot}) AS max_total_gb, AVG({c_gb}) AS promedio_gb
                        FROM monitoreo WHERE TRIM(ip_servidor) = %s GROUP BY DATE(fecha_registro) ORDER BY fecha_limpia ASC
                    """
                    cursor_temp.execute(query_diaria, (ip_objetivo,))
                    datos_diarios = cursor_temp.fetchall()
                    cursor_temp.close()
                    conn_temp.close()
                except Exception as e_sql:
                    st.error(f"Fallo en la query analitica de agrupacion: {e_sql}")
                    if conn_temp: conn_temp.close()

            CON_DATOS_SUFICIENTES = True
            modo_contingencia_txt = "Ninguno (Calculo Real Basado en Historial)"
            
            if not datos_diarios or len(datos_diarios) < 3:
                CON_DATOS_SUFICIENTES = False
                if datos_diarios and len(datos_diarios) > 0:
                    valores_pct = [float(datos_diarios[-1]['promedio_pct'] or 0.0)]
                    valores_total = [float(datos_diarios[-1]['max_total_gb'] or 0.0)]
                    valores_gb = [float(datos_diarios[-1]['promedio_gb'] or 0.0)]
                    fechas_filtradas = [datos_diarios[-1]['fecha_limpia']]
                else:
                    valores_pct = [80.0 if meta_metrica["tipo"] == "disponibilidad" else 20.0]
                    valores_total = [float(info_servidor.get(meta_metrica["col_total"]) or 100.0) if meta_metrica["col_total"] else 0.0]
                    valores_gb = [valores_total[0] * 0.8] if meta_metrica["tipo"] == "disponibilidad" else [0.0]
                    fechas_filtradas = [datetime.now().date()]
            else:
                valores_pct = [float(d['promedio_pct'] or 0.0) for d in datos_diarios]
                valores_total = [float(d['max_total_gb'] or 0.0) for d in datos_diarios]
                valores_gb = [float(d['promedio_gb'] or 0.0) for d in datos_diarios]
                fechas_filtradas = [d['fecha_limpia'] for d in datos_diarios]

            num_muestras = len(valores_pct)
            X = list(range(num_muestras))
            Y = valores_pct

            if CON_DATOS_SUFICIENTES:
                sum_x = sum(X)
                sum_y = sum(Y)
                sum_x_cuadrado = sum([x**2 for x in X])
                sum_xy = sum([X[i] * Y[i] for i in range(num_muestras)])
                denominador = (num_muestras * sum_x_cuadrado) - (sum_x**2)
                if denominador == 0:
                    pendiente, interseccion = 0.0, Y[-1]
                else:
                    pendiente = ((num_muestras * sum_xy) - (sum_x * sum_y)) / denominador
                    interseccion = (sum_y - (pendiente * sum_x)) / num_muestras
            else:
                factor_direccion = -1.0 if meta_metrica["tipo"] == "disponibilidad" else 1.0
                if dias_proyeccion <= 14:
                    pendiente = (1.25 / 7.0) * factor_direccion
                    modo_contingencia_txt = "Estimación Normativa Semanal (+1.25% / 7d)"
                else:
                    pendiente = (5.0 / 30.0) * factor_direccion
                    modo_contingencia_txt = "Estimación Normativa Mensual (+5.0% / 30d)"
                interseccion = Y[-1]

            pct_actual = Y[-1]
            total_gb_actual = valores_total[-1]
            gb_actual = valores_gb[-1]
            
            indice_proyectado = num_muestras + dias_proyeccion - 1
            pct_base_proyectado = (pendiente * indice_proyectado) + interseccion

            if meta_metrica["tipo"] == "consumo":
                pct_final_proyectado = pct_base_proyectado * (1 + (porcentaje_ajuste_analista / 100.0))
                pct_final_proyectado = max(0.0, min(100.0, pct_final_proyectado))
                gb_proyectado_final = 0.0
                if pct_final_proyectado >= 85.0:
                    veredicto, color_alert = "CRÍTICO", "red"
                    detalle_veredicto = "Saturacion de CPU inminente. El consumo proyectado supera el umbral corporativo del 85%."
                elif pct_final_proyectado >= 70.0:
                    veredicto, color_alert = "PRECAUCIÓN", "orange"
                    detalle_veredicto = "Crecimiento elevado en procesamiento. Se aconseja revision preventiva."
                else:
                    veredicto, color_alert = "ESTABLE", "green"
                    detalle_veredicto = f"La capacidad de procesamiento operara de forma segura en los proximos {dias_proyeccion} dias."
            else:
                pct_final_proyectado = pct_base_proyectado * (1 - (porcentaje_ajuste_analista / 100.0))
                pct_final_proyectado = max(0.0, min(100.0, pct_final_proyectado))
                gb_proyectado_final = round((total_gb_actual * pct_final_proyectado) / 100.0, 2)
                if pct_final_proyectado <= 10.0:
                    veredicto, color_alert = "CRÍTICO", "red"
                    detalle_veredicto = "Agotamiento total de recurso libre inminente (Menos del 10% disponible)."
                elif pct_final_proyectado <= 20.0:
                    veredicto, color_alert = "PRECAUCIÓN", "orange"
                    detalle_veredicto = "Recurso libre escaso para responder ante contingencias operativas (Menos del 20% disponible)."
                else:
                    veredicto, color_alert = "ESTABLE", "green"
                    detalle_veredicto = "La infraestructura mantendra indices de disponibilidad saludables durante el periodo simulado."

            st.markdown(" ")
            if st.button("🚀 Generar Reporte y Procesar Simulación de Tendencia", use_container_width=True):
                st.session_state.reporte_generado = True
                st.rerun()

            if st.session_state.reporte_generado:
                st.markdown("---")
                if not CON_DATOS_SUFICIENTES:
                    st.warning(f"⚠️ **Modo de Proyección Estática Normativa Activo:** Muestras históricas insuficientes. Aplicando algoritmo de {modo_contingencia_txt}.")

                st.markdown(
                    f'<div style="background-color:#f8f9fa; border:1px solid #ddd; border-left:6px solid {color_alert}; padding:15px; border-radius:4px; margin-top:10px;">'
                    f'<h4 style="margin:0px; color:#333;">Veredicto Tecnico: <span style="color:{color_alert}; font-weight:bold;">{veredicto}</span></h4>'
                    f'<p style="margin:5px 0px; font-size:13px; color:#555;">{detalle_veredicto}</p>'
                    f'<ul style="margin:5px 0px; padding-left:20px; font-size:12px; color:#444;">'
                    f'<li><b>Muestra Porcentual Actual:</b> {round(pct_actual, 2)}%</li>'
                    f'<li><b>Tendencia Porcentual Proyectada:</b> {round(pct_final_proyectado, 2)}%</li>'
                    f'{"<li><b>Capacidad Absoluta Actual:</b> " + str(round(gb_actual, 2)) + " GB de " + str(round(total_gb_actual, 2)) + " GB Totales</li>" if meta_metrica["tipo"] == "disponibilidad" else ""}'
                    f'{"<li><b>Capacidad Absoluta Proyectada:</b> " + str(round(gb_proyectado_final, 2)) + " GB libres estimados</li>" if meta_metrica["tipo"] == "disponibilidad" else ""}'
                    f'<li><b>Pendiente Lineal Aplicada (m):</b> {round(pendiente, 4)} unidades/dia</li>'
                    f'</ul>'
                    f'</div>', unsafe_allow_html=True
                )

                st.markdown("##### 📁 Exportar Documentacion Analitica (Archivado Automático Activo)")
                col_exp1, col_exp2 = st.columns(2)
                nombre_doc_pdf = f"capacity_{ip_objetivo}_{datetime.now().strftime('%Y%m%d')}.pdf"
                nombre_doc_csv = f"capacity_{ip_objetivo}_{datetime.now().strftime('%Y%m%d')}.csv"

                # 1. COMPILACIÓN DE PDF CON TABLA ESTILIZADA CON COLORES INSTITUCIONALES
                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, f"Resumen Detallado - Nodo: {servidor_sel} ({ip_objetivo})", 0, 1)
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 6, f"Metrica de Analisis: {metrica_sel}", 0, 1)
                pdf.cell(0, 6, f"Fecha de Evaluacion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
                pdf.cell(0, 6, f"Horizonte de Proyeccion: {dias_proyeccion} dias", 0, 1)
                pdf.cell(0, 6, f"Factor de Crecimiento Analista: +{porcentaje_ajuste_analista}%", 0, 1)
                pdf.cell(0, 6, f"Veredicto Final SIMPOL: {veredicto}", 0, 1)
                pdf.cell(0, 6, f"Detalle Diagnostico: {detalle_veredicto}", 0, 1)
                pdf.cell(0, 6, f"Modo Contingencia del Banco: {modo_contingencia_txt}", 0, 1)
                pdf.ln(6)
                
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "Metricas Base Calculadas:", 0, 1)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 5, f"- Porcentaje Muestra Actual: {round(pct_actual, 2)}%", 0, 1)
                pdf.cell(0, 5, f"- Porcentaje Final Proyectado: {round(pct_final_proyectado, 2)}%", 0, 1)
                if meta_metrica["tipo"] == "disponibilidad":
                    pdf.cell(0, 5, f"- Espacio Actual Disponible: {round(gb_actual, 2)} GB de {round(total_gb_actual, 2)} GB Totales", 0, 1)
                    pdf.cell(0, 5, f"- Espacio Libre Proyectado: {round(gb_proyectado_final, 2)} GB", 0, 1)
                pdf.cell(0, 5, f"- Coeficiente de Pendiente (m): {round(pendiente, 4)} unidades/dia", 0, 1)
                pdf.ln(8)

                # RENDERIZADO DE TABLA ESTILO BANCO CARONÍ
                pdf.set_font("Arial", "B", 10)
                # Configurar colores del encabezado (Azul Corporativo y texto blanco)
                pdf.set_fill_color(0, 51, 102)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(60, 8, "Fecha (Muestra)", 1, 0, "C", True)
                pdf.cell(45, 8, "Valor Promedio (%)", 1, 1, "C", True)
                
                # Restaurar el texto a color oscuro para los registros
                pdf.set_text_color(51, 51, 51)
                pdf.set_font("Arial", "", 10)
                
                for i in range(min(num_muestras, 15)):
                    f_iter = fechas_filtradas[i]
                    f_str = f_iter.strftime('%Y-%m-%d') if hasattr(f_iter, 'strftime') else str(f_iter)
                    
                    # Zebra striping alternando el color de fondo de las filas
                    if i % 2 == 0:
                        pdf.set_fill_color(245, 245, 245) # Gris muy suave
                    else:
                        pdf.set_fill_color(255, 255, 255) # Blanco puro
                        
                    pdf.cell(60, 7, f_str, 1, 0, "C", True)
                    pdf.cell(45, 7, f"{round(valores_pct[i], 2)}%", 1, 1, "C", True)

                # Limpiar estados de color de FPDF por seguridad
                pdf.set_text_color(0, 0, 0)

                pdf_buffer = io.BytesIO()
                pdf.output(pdf_buffer)
                bytes_pdf = pdf_buffer.getvalue()

                # 2. COMPILACIÓN DE CSV CON DATOS REALES COMPLETOS
                csv_lineas = [
                    "PROPIEDAD,VALOR",
                    f"Servidor Nombrado,{servidor_sel}",
                    f"Direccion IP V4,{ip_objetivo}",
                    f"Metrica de Analisis,{metrica_sel}",
                    f"Fecha Ejecucion,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Horizonte Simulado Dias,{dias_proyeccion}",
                    f"Factor Analista Pct,{porcentaje_ajuste_analista}",
                    f"Veredicto SIMPOL,{veredicto}",
                    f"Detalle Tecnico,{detalle_veredicto}",
                    f"Modo Contingencia Banco,{modo_contingencia_txt}",
                    f"Porcentaje Actual,{round(pct_actual, 2)}",
                    f"Porcentaje Proyectado,{round(pct_final_proyectado, 2)}",
                    f"Total Capacidad GB,{round(total_gb_actual, 2)}",
                    f"Actual Libre GB,{round(gb_actual, 2)}",
                    f"Proyectado Libre GB,{round(gb_proyectado_final, 2)}",
                    f"Pendiente Lineal M,{round(pendiente, 4)}"
                ]
                bytes_csv = "\n".join(csv_lineas).encode("utf-8")

                with col_exp1:
                    def archivar_pdf_callback():
                        registrar_proyeccion_v398(usuario_id, ip_objetivo, metrica_sel, float(total_gb_actual), float(gb_actual), float(pct_actual), float(gb_proyectado_final), float(pct_final_proyectado), veredicto)
                        kb = round(len(bytes_pdf) / 1024.0, 2)
                        guardar_reporte_capacity_bd(nombre_doc_pdf, "PDF", metrica_sel, ip_objetivo, bytes_pdf, usuario_id, None, veredicto, kb, total_gb_actual, gb_actual, gb_proyectado_final)
                    
                    st.download_button(
                        label="📥 Exportar y Archivar Informe (PDF)", 
                        data=bytes_pdf, 
                        file_name=nombre_doc_pdf, 
                        mime="application/pdf", 
                        use_container_width=True, 
                        on_click=archivar_pdf_callback, 
                        key="btn_auto_pdf"
                    )

                with col_exp2:
                    def archivar_csv_callback():
                        registrar_proyeccion_v398(usuario_id, ip_objetivo, metrica_sel, float(total_gb_actual), float(gb_actual), float(pct_actual), float(gb_proyectado_final), float(pct_final_proyectado), veredicto)
                        kb = round(len(bytes_csv) / 1024.0, 2)
                        guardar_reporte_capacity_bd(nombre_doc_csv, "CSV", metrica_sel, ip_objetivo, bytes_csv, usuario_id, None, veredicto, kb, total_gb_actual, gb_actual, gb_proyectado_final)
                    
                    st.download_button(
                        label="📥 Exportar y Archivar Matriz (CSV)", 
                        data=bytes_csv, 
                        file_name=nombre_doc_csv, 
                        mime="text/csv", 
                        use_container_width=True, 
                        on_click=archivar_csv_callback, 
                        key="btn_auto_csv"
                    )

        # PESTAÑA 2: BÓVEDA DIGITAL
        with pestana_boveda:
            if servidor_sel == "-- Seleccione un Servidor --":
                st.info("💡 Seleccione un servidor en la pestaña anterior para consultar su bóveda digital.")
            else:
                st.markdown(f"#### 📜 Repositorio de Informes Archivados para `{servidor_sel}`")
                items_historicos = listar_reportes_capacity_bd(ip_objetivo)
                if not items_historicos:
                    st.caption("No se registran informes técnicos de capacity auto-archivados para este nodo.")
                else:
                    st.markdown(
                        '<div style="background-color:#003366; color:white; padding:8px; border-radius:3px; font-weight:bold; font-size:13px; font-family:Arial; display:flex;">'
                        '<div style="flex:2.5;">Nombre del Documento Tecnico</div>'
                        '<div style="flex:2; text-align:center;">Metrica Analizada</div>'
                        '<div style="flex:0.8; text-align:center;">Formato</div>'
                        '<div style="flex:0.8; text-align:center;">Tamaño</div>'
                        '<div style="flex:1.8; text-align:center;">Fecha de Generacion</div>'
                        '</div>', unsafe_allow_html=True
                    )
                    for item in items_historicos:
                        f_gen = item['fecha_generacion'].strftime("%Y-%m-%d %H:%M") if hasattr(item['fecha_generacion'], 'strftime') else str(item['fecha_generacion'])
                        badge_color = "#003366" if item['formato'] == "PDF" else "#2e7d32"
                        st.markdown(
                            f'<div style="background-color:#ffffff; border-bottom:1px solid #eee; padding:10px 8px; font-size:12px; font-family:Arial; display:flex; align-items:center;">'
                            f'<div style="flex:2.5; font-weight:bold; color:#333;">📄 {item["nombre_archivo"]}</div>'
                            f'<div style="flex:2; text-align:center; color:#555;">{item["metrica_analizada"]}</div>'
                            f'<div style="flex:0.8; text-align:center;"><span style="background-color:{badge_color}; color:white; padding:2px 6px; border-radius:3px; font-weight:bold;">{item["formato"]}</span></div>'
                            f'<div style="flex:0.8; text-align:center; color:#444;">{item["tamanio_kb"]} KB</div>'
                            f'<div style="flex:1.8; text-align:center; color:#666; font-family:monospace;">{f_gen}</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                        datos_binarios = descargar_blob_capacity(item['id'])
                        if datos_binarios:
                            mime_tipo = "text/csv" if item['formato'] == "CSV" else "application/pdf"
                            st.download_button(label=f"📥 Descargar {item['nombre_archivo']}", data=datos_binarios, file_name=item['nombre_archivo'], mime=mime_tipo, key=f"btn_grid_dl_{item['id']}", use_container_width=True)

    except Exception as e_main:
        st.error(f"Fallo general critico en la ejecucion de la vista analitica: {e_main}")
        traceback.print_exc()

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin_csu")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)