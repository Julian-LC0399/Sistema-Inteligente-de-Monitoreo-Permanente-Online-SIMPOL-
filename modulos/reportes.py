import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import re
import tempfile
import os

# =====================================================================
# FUNCIÓN AUXILIAR PARA NORMALIZAR COMPONENTES
# =====================================================================
def normalizar_componente(nombre):
    """
    Normaliza el nombre del componente para comparación entre alertas y reportes.
    
    Ejemplos:
        "C:" -> "DISCO1"
        "D:" -> "DISCO2"
        "CPU" -> "CPU"
        "Servicio_1" -> "SERVICIO1"
    """
    if nombre is None:
        return ""
    
    nombre = str(nombre).strip()
    
    # Mapeo de discos (ALERTA -> REPORTE)
    discos_map = {
        "C:": "DISCO1", "C:\\": "DISCO1", "C": "DISCO1",
        "D:": "DISCO2", "D:\\": "DISCO2", "D": "DISCO2",
        "E:": "DISCO3", "E:\\": "DISCO3", "E": "DISCO3",
        "F:": "DISCO4", "F:\\": "DISCO4", "F": "DISCO4",
        "G:": "DISCO5", "G:\\": "DISCO5", "G": "DISCO5",
        "Y:": "DISCO6", "Y:\\": "DISCO6", "Y": "DISCO6",
    }
    
    # Si es un disco, devolver el mapeo
    if nombre in discos_map:
        return discos_map[nombre]
    
    # Si contiene DISCO, devolverlo tal cual
    if "DISCO" in nombre.upper():
        return nombre.upper()
    
    # CPU, RAM, LATENCIA
    if nombre.upper() in ["CPU", "RAM", "LATENCIA", "PING"]:
        return nombre.upper()
    
    # Servicios
    if "SERVICIO" in nombre.upper():
        match = re.search(r'SERVICIO[_]?(\d+)', nombre.upper())
        if match:
            return f"SERVICIO{match.group(1)}"
        return nombre.upper()
    
    # Si no coincide con nada, limpiar caracteres especiales
    return nombre.upper().replace("_", "").replace(" ", "").replace(":", "").replace("\\", "")

# =====================================================================
# FUNCIÓN PARA LIMPIAR EL ESTADO DEL MÓDULO REPORTES
# =====================================================================
def limpiar_estado_reportes():
    """Limpia todas las variables de estado del módulo reportes"""
    keys_to_clear = [
        'rep_listo',
        'rep_csv',
        'rep_pdf',
        'rep_name_csv',
        'rep_name_pdf',
        'key_semilla_selectbox',
        'reporte_servidor',
        'reporte_sensor',
        'reporte_fecha_i',
        'reporte_fecha_f',
        'reporte_formato',
        'filtros_aplicados'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state["filtros_aplicados"] = False

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF (ESTILO BANCO CARONÍ)
# =====================================================================
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "BANCO CARONI - SISTEMA SIMPOL", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(0, 5, "Reporte Operacional de Infraestructura y Telemetría", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por SIMPOL | Página {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE CONSULTA A BASE DE DATOS
# =====================================================================
def obtener_datos_reporte(ip_servidor, fecha_inicio, fecha_fin):
    """Obtiene TODOS los registros del rango de fechas sin límite"""
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT * FROM monitoreo 
            WHERE ip_servidor = %s AND fecha_registro BETWEEN %s AND %s
            ORDER BY fecha_registro DESC
        """
        cursor.execute(query, (ip_servidor, fecha_inicio, fecha_fin))
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        st.error(f"❌ Error consultando registros para reporte: {e}")
        return []
    finally:
        if conn: conn.close()

def obtener_alertas_reporte(ip_servidor, fecha_inicio, fecha_fin):
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT id, componente, tipo_alerta, fecha_inicio, fecha_fin, comentario
            FROM alertas
            WHERE ip_servidor = %s 
              AND (
                   (fecha_inicio BETWEEN %s AND %s)
                OR (fecha_fin BETWEEN %s AND %s)
                OR (fecha_inicio <= %s AND (fecha_fin IS NULL OR fecha_fin >= %s))
              )
        """
        cursor.execute(query, (ip_servidor, fecha_inicio, fecha_fin, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio))
        alertas = cursor.fetchall()
        cursor.close()
        return alertas
    except Exception as e:
        st.error(f"❌ Error obteniendo alertas del servidor: {e}")
        return []
    finally:
        if conn: conn.close()

def guardar_reporte_archivado(nombre_archivo, formato, ip_servidor, contenido_blob, usuario_id, tamanio_kb, ultima_muestra=None, alerta_vinculada=None):
    conn = conectar_bd()
    if not conn: return False
    try:
        cursor = conn.cursor()
        
        snap_ram_tot = 0.0; snap_ram_disp = 0.0; snap_ram_pct = 0.0
        snap_red_tot = 0.0; snap_red_ent = 0.0; snap_red_sal = 0.0
        snap_lat = 0.0; snap_per = 0.0; snap_srv = None
        
        if ultima_muestra:
            snap_ram_tot = float(ultima_muestra.get('val_ram_total_gb') or 0.0)
            snap_ram_disp = float(ultima_muestra.get('val_ram_disponible_gb') or 0.0)
            snap_ram_pct = float(ultima_muestra.get('val_ram_disponible_pct') or 0.0)
            snap_red_tot = float(ultima_muestra.get('val_red_total') or 0.0)
            snap_red_ent = float(ultima_muestra.get('val_red_entrante') or 0.0)
            snap_red_sal = float(ultima_muestra.get('val_red_saliente') or 0.0)
            snap_lat = float(ultima_muestra.get('val_latencia_ping') or 0.0)
            snap_per = float(ultima_muestra.get('val_latencia_perdida') or 0.0)
            snap_srv = ultima_muestra.get('estado_servicio_1')

        id_alerta = alerta_vinculada.get('id') if alerta_vinculada else None
        tipo_alerta_txt = 'ESTABLE'
        if alerta_vinculada and alerta_vinculada.get('tipo_alerta'):
            tipo_alerta_txt = str(alerta_vinculada['tipo_alerta']).upper().strip()

        query = """
            INSERT INTO reportes_archivados 
            (nombre_archivo, `format`, ip_servidor, contenido, usuario_id, alerta_id, tipo_alerta,
             snapshot_total_gb, snapshot_disponible_gb, snapshot_disponible_pct, 
             snapshot_red_total_mbps, snapshot_red_entrante_mbps, snapshot_red_saliente_mbps,
             snapshot_latencia_ms, snapshot_perdida_pct, snapshot_servicio_estado, tamanio_kb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            nombre_archivo, formato, ip_servidor.strip(), contenido_blob, usuario_id, id_alerta, tipo_alerta_txt,
            snap_ram_tot, snap_ram_disp, snap_ram_pct, 
            snap_red_tot, snap_red_ent, snap_red_sal,
            snap_lat, snap_per, snap_srv, tamanio_kb
        ))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        st.error(f"❌ Error persistiendo archivo en histórico: {e}")
        return False
    finally:
        if conn: conn.close()

def listar_reportes_archivados_filtrado(ip_servidor, token_sensor):
    conn = conectar_bd()
    resultados = []
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT r.id, r.nombre_archivo, r.format as formato, r.ip_servidor, r.fecha_generacion, r.tamanio_kb, u.usuario as registrado_por
            FROM reportes_archivados r
            LEFT JOIN usuarios u ON r.usuario_id = u.id
            WHERE TRIM(r.ip_servidor) = %s AND r.nombre_archivo LIKE %s
            ORDER BY r.fecha_generacion DESC
        """
        patron_busqueda = f"%_{token_sensor}_%"
        cursor.execute(query, (ip_servidor.strip(), patron_busqueda))
        resultados = cursor.fetchall()
        cursor.close()
    except Exception as e:
        st.error(f"❌ Error listando histórico filtrado: {e}")
    finally:
        if conn: conn.close()
    return resultados

def descargar_contenido_blob(id_archivo):
    conn = conectar_bd()
    blob_data = None
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT contenido FROM reportes_archivados WHERE id = %s"
        cursor.execute(query, (id_archivo,))
        row = cursor.fetchone()
        if row: blob_data = row['contenido']
        cursor.close()
    except Exception as e:
        st.error(f"❌ Error extrayendo binario: {e}")
    finally:
        if conn: conn.close()
    return blob_data

# =====================================================================
# FUNCIÓN PARA OBTENER BYTES DEL PDF (CORREGIDA - SIN SOBRECARGA DE MEMORIA)
# =====================================================================
def obtener_bytes_pdf(pdf):
    """Convierte un objeto PDF a bytes de manera compatible sin sobrecargar memoria"""
    try:
        # Intentar método para fpdf2 (versiones modernas)
        pdf_bytes = pdf.output(dest='S')
        if isinstance(pdf_bytes, str):
            return pdf_bytes.encode('latin1')
        return pdf_bytes
    except:
        # Fallback usando tempfile para versiones antiguas
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            with open(tmp_file.name, 'rb') as f:
                bytes_pdf = f.read()
            os.unlink(tmp_file.name)
            return bytes_pdf

# =====================================================================
# VISTA Y CONTROLADOR PRINCIPAL DEL MÓDULO DE REPORTES
# =====================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    
    # =============================================================
    # INICIO DE LA VISTA
    # =============================================================
    
    # Inicializar variables de estado con nombres únicos para evitar conflictos
    if "reporte_servidor" not in st.session_state:
        st.session_state["reporte_servidor"] = "-- Seleccione un Servidor --"
    if "reporte_sensor" not in st.session_state:
        st.session_state["reporte_sensor"] = "Reporte Integral (Todas las Variables)"
    if "reporte_fecha_i" not in st.session_state:
        st.session_state["reporte_fecha_i"] = datetime.now() - timedelta(days=1)
    if "reporte_fecha_f" not in st.session_state:
        st.session_state["reporte_fecha_f"] = datetime.now()
    if "reporte_formato" not in st.session_state:
        st.session_state["reporte_formato"] = "PDF"
    if "filtros_aplicados" not in st.session_state:
        st.session_state["filtros_aplicados"] = False
    
    st.markdown("""
        <style>
            .info-analista-reportes {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-reportes span {
                color: #003366;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">📋 Módulo Operacional de Reportes</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-reportes">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    if "rep_listo" not in st.session_state: st.session_state["rep_listo"] = False
    if "rep_csv" not in st.session_state: st.session_state["rep_csv"] = None
    if "rep_pdf" not in st.session_state: st.session_state["rep_pdf"] = None
    if "rep_name_csv" not in st.session_state: st.session_state["rep_name_csv"] = ""
    if "rep_name_pdf" not in st.session_state: st.session_state["rep_name_pdf"] = ""
    if "key_semilla_selectbox" not in st.session_state: st.session_state["key_semilla_selectbox"] = 1000

    from database import obtener_lista_servidores
    servidores = obtener_lista_servidores()
    if not servidores:
        st.info("📭 No se registran nodos de infraestructura para compilar reportes.")
        return

    nombres_servidores = ["-- Seleccione un Servidor --"] + [s['nombre_alias'] for s in servidores]
    
    # =====================================================================
    # FILTROS - Usan variables directas (no temp_*)
    # =====================================================================
    with st.container():
        st.markdown("#### Parámetros de Extracción y Filtrado")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fecha_i = st.date_input(
                "Fecha Inicial:", 
                value=st.session_state["reporte_fecha_i"], 
                key="widget_rep_fi"
            )
            st.session_state["reporte_fecha_i"] = fecha_i
            
        with col_f2:
            fecha_f = st.date_input(
                "Fecha Final:", 
                value=st.session_state["reporte_fecha_f"], 
                key="widget_rep_ff"
            )
            st.session_state["reporte_fecha_f"] = fecha_f
            
        with col_f3:
            formatos_lista = ["PDF", "CSV"]
            formato_sel = st.selectbox(
                "Formato de Exportación:",
                options=formatos_lista,
                index=formatos_lista.index(st.session_state["reporte_formato"]),
                key="widget_rep_formato"
            )
            st.session_state["reporte_formato"] = formato_sel

        # Selector de servidor
        serv_seleccionado = st.selectbox(
            "Seleccione el Servidor objetivo:", 
            options=nombres_servidores, 
            index=nombres_servidores.index(st.session_state["reporte_servidor"]) if st.session_state["reporte_servidor"] in nombres_servidores else 0,
            key=f"sb_srv_reportes_semilla_{st.session_state['key_semilla_selectbox']}"
        )
        st.session_state["reporte_servidor"] = serv_seleccionado

        if serv_seleccionado == "-- Seleccione un Servidor --":
            st.info("🖥️ Seleccione un nodo de la lista para activar las herramientas de reportes.")
            return

        serv_info = next((s for s in servidores if s['nombre_alias'] == serv_seleccionado), None)
        ip_objetivo = str(serv_info['ip']).strip()

        letras_discos = {}
        for i in range(1, 7):
            campo_letra = f'letra_disco_{i}'
            letra_raw = str(serv_info.get(campo_letra, '')).replace('\\', '').strip().upper()
            letras_discos[i] = letra_raw if letra_raw else f"DISCO{i}"

        sensores_disponibles = ["Reporte Integral (Todas las Variables)"]
        
        if serv_info.get('id_sensor_cpu') and int(serv_info['id_sensor_cpu']) > 0:
            sensores_disponibles.append("Uso de CPU")
        if serv_info.get('id_sensor_ram') and int(serv_info['id_sensor_ram']) > 0:
            sensores_disponibles.append("Memoria RAM")
        for i in range(1, 7):
            campo_sensor = f'id_sensor_disco_{i}'
            if serv_info.get(campo_sensor) and int(serv_info[campo_sensor]) > 0:
                sensores_disponibles.append(f"Disco {letras_discos[i]}")
        if serv_info.get('id_sensor_latencia') and int(serv_info['id_sensor_latencia']) > 0:
            sensores_disponibles.append("Latencia de Red")

        if st.session_state["reporte_sensor"] not in sensores_disponibles:
            st.session_state["reporte_sensor"] = sensores_disponibles[0]

        sensor_general = st.selectbox(
            "Sensor registrado en el Servidor:",
            options=sensores_disponibles,
            index=sensores_disponibles.index(st.session_state["reporte_sensor"]),
            key="widget_rep_sensor_general"
        )
        st.session_state["reporte_sensor"] = sensor_general

        # =====================================================================
        # BOTONES: FILTRAR Y LIMPIAR FILTROS
        # =====================================================================
        col_btn_filtrar, col_btn_limpiar = st.columns(2, gap="small")
        
        with col_btn_filtrar:
            if st.button("🔍 Filtrar", use_container_width=True, key="btn_aplicar_filtros"):
                st.session_state["filtros_aplicados"] = True
                st.success("✅ Filtros aplicados correctamente.")
                st.rerun()
        
        with col_btn_limpiar:
            if st.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_clear_all_filters"):
                # Resetear todo
                st.session_state["reporte_servidor"] = "-- Seleccione un Servidor --"
                st.session_state["reporte_sensor"] = "Reporte Integral (Todas las Variables)"
                st.session_state["reporte_fecha_i"] = datetime.now() - timedelta(days=1)
                st.session_state["reporte_fecha_f"] = datetime.now()
                st.session_state["reporte_formato"] = "PDF"
                st.session_state["filtros_aplicados"] = False
                st.session_state["rep_listo"] = False
                st.session_state["rep_csv"] = None
                st.session_state["rep_pdf"] = None
                st.session_state["key_semilla_selectbox"] += 1
                st.success("🧹 Filtros limpiados correctamente.")
                st.rerun()

        # Mostrar estado de los filtros aplicados
        if st.session_state.get("filtros_aplicados", False):
            st.info(f"📌 Filtros activos: Servidor: {st.session_state['reporte_servidor']} | Sensor: {st.session_state['reporte_sensor']} | Fechas: {st.session_state['reporte_fecha_i'].strftime('%d/%m/%Y')} al {st.session_state['reporte_fecha_f'].strftime('%d/%m/%Y')}")

    # =====================================================================
    # GENERACIÓN DE REPORTE (USA LOS FILTROS APLICADOS)
    # =====================================================================
    if st.session_state.get("filtros_aplicados", False):
        serv_seleccionado = st.session_state["reporte_servidor"]
        sensor_general = st.session_state["reporte_sensor"]
        fecha_i = st.session_state["reporte_fecha_i"]
        fecha_f = st.session_state["reporte_fecha_f"]
        formato_sel = st.session_state["reporte_formato"]
        
        serv_info = next((s for s in servidores if s['nombre_alias'] == serv_seleccionado), None)
        if not serv_info:
            st.warning("⚠️ El servidor seleccionado ya no está disponible.")
            st.session_state["filtros_aplicados"] = False
            st.rerun()
            return
            
        ip_objetivo = str(serv_info['ip']).strip()
        
        s_prefix = "INTEGRAL"
        num_disco_activo = None
        
        if "RAM" in sensor_general: s_prefix = "RAM"
        elif "CPU" in sensor_general: s_prefix = "CPU"
        elif "Latencia" in sensor_general: s_prefix = "LATENCIA"
        elif "Disco" in sensor_general:
            letra_sel = sensor_general.replace("Disco ", "").strip()
            for i, letra in letras_discos.items():
                if letra == letra_sel:
                    s_prefix = f"DISCO{i}"
                    num_disco_activo = i
                    break

        tab1, tab2 = st.tabs(["📊 Generación de Reportes", "📜 Repositorio e Histórico de Archivos"])

        with tab1:
            dt_inicio = datetime.combine(fecha_i, time.min)
            dt_fin = datetime.combine(fecha_f, time.max)

            if dt_inicio >= dt_fin:
                st.error("❌ La fecha inicial debe ser menor a la fecha final seleccionada.")
            else:
                # 🔥 OBTENER TODOS LOS DATOS DEL RANGO DE FECHAS
                datos_muestras = obtener_datos_reporte(ip_objetivo, dt_inicio, dt_fin)
                lista_alertas_servidor = obtener_alertas_reporte(ip_objetivo, dt_inicio, dt_fin)
                ultima_muestra_obj = datos_muestras[0] if datos_muestras else None

                # Mostrar información de los datos obtenidos
                st.info(f"📊 Se encontraron {len(datos_muestras)} registros en el rango de fechas seleccionado.")

                # =====================================================================
                # BOTÓN DE GENERACIÓN DE REPORTE
                # =====================================================================
                col_btn_gen1, col_btn_gen2 = st.columns([3, 1])
                with col_btn_gen1:
                    ejecutar_reporte = st.button(f"📊 GENERAR Y ARCHIVAR REPORTE ({formato_sel})", use_container_width=True, key="btn_run_report")
                
                if ejecutar_reporte:
                    if not datos_muestras:
                        st.warning(f"⚠️ Telemetría no disponible para `{serv_seleccionado}` en este rango temporal.")
                    else:
                        nombre_base_archivo = f"reporte_{s_prefix}_{serv_info['nombre_alias']}_{fecha_i.strftime('%Y%m%d')}"
                        alerta_detectada_global = None

                        # --- OPCIÓN PDF ---
                        if formato_sel == "PDF":
                            try:
                                # Mostrar progreso
                                with st.spinner(f"Generando PDF con {len(datos_muestras)} registros..."):
                                    pdf = PDF()
                                    pdf.add_page()
                                    pdf.set_font("Arial", "B", 11)
                                    pdf.cell(0, 7, f"REPORTE: {sensor_general.upper()}", 0, 1)
                                    pdf.set_font("Arial", "", 10)
                                    pdf.cell(50, 6, f"Servidor Objetivo: {serv_info['nombre_alias']} ({ip_objetivo})", 0, 1)
                                    pdf.cell(50, 6, f"Rango Temporal: {fecha_i.strftime('%d/%m/%Y')} al {fecha_f.strftime('%d/%m/%Y')}", 0, 1)
                                    pdf.cell(50, 6, f"Analista Emisor: {nombre_analista}", 0, 1)
                                    pdf.cell(50, 6, f"Total de Registros: {len(datos_muestras)}", 0, 1)
                                    pdf.ln(5)

                                    bloques_metricas = []
                                    if s_prefix == "INTEGRAL":
                                        bloques_metricas = [
                                            {"titulo": f"MÉTRICA - USO DE CPU (TODOS LOS REGISTROS DEL RANGO)", "prefix": "CPU"},
                                            {"titulo": f"MÉTRICA - MEMORIA RAM (TODOS LOS REGISTROS DEL RANGO)", "prefix": "RAM"},
                                            {"titulo": f"MÉTRICA - LATENCIA DE RED (TODOS LOS REGISTROS DEL RANGO)", "prefix": "LATENCIA"}
                                        ]
                                        for i in range(1, 7):
                                            campo_sensor = f'id_sensor_disco_{i}'
                                            if serv_info.get(campo_sensor) and int(serv_info[campo_sensor]) > 0:
                                                bloques_metricas.append({"titulo": f"MÉTRICA - DISCO {letras_discos[i]} (TODOS LOS REGISTROS DEL RANGO)", "prefix": f"DISCO{i}", "disco_idx": i})
                                    else:
                                        bloques_metricas = [{"titulo": f"MÉTRICA - {sensor_general.upper()} (TODOS LOS REGISTROS DEL RANGO)", "prefix": s_prefix, "disco_idx": num_disco_activo}]

                                    # Limitar la cantidad de registros por bloque para evitar PDF gigante
                                    MAX_REGISTROS_POR_BLOQUE = 500
                                    registros_a_mostrar = datos_muestras
                                    if len(registros_a_mostrar) > MAX_REGISTROS_POR_BLOQUE:
                                        pdf.set_font("Arial", "I", 9)
                                        pdf.cell(0, 5, f"NOTA: Mostrando los últimos {MAX_REGISTROS_POR_BLOQUE} registros de {len(registros_a_mostrar)} totales.", 0, 1, "L")
                                        registros_a_mostrar = registros_a_mostrar[:MAX_REGISTROS_POR_BLOQUE]

                                    for bloque in bloques_metricas:
                                        p_sub = bloque["prefix"]
                                        pdf.set_font("Arial", "B", 10)
                                        pdf.set_text_color(0, 51, 102)
                                        pdf.cell(0, 8, bloque["titulo"], 0, 1)
                                        
                                        pdf.set_fill_color(0, 51, 102)
                                        pdf.set_text_color(255, 255, 255)
                                        pdf.set_draw_color(180, 180, 180)
                                        pdf.set_font("Arial", "B", 9)
                                        
                                        pdf.cell(35, 7, "Fecha Registro", 1, 0, "C", True)

                                        if p_sub == "RAM":
                                            pdf.cell(35, 7, "RAM Total", 1, 0, "C", True)
                                            pdf.cell(35, 7, "RAM Disp (GB)", 1, 0, "C", True)
                                            pdf.cell(30, 7, "RAM Disp %", 1, 0, "C", True)
                                        elif "DISCO" in p_sub:
                                            d_idx = bloque["disco_idx"]
                                            letra_activa = letras_discos[d_idx]
                                            pdf.cell(35, 7, f"D. {letra_activa} Tot", 1, 0, "C", True)
                                            pdf.cell(35, 7, f"D. {letra_activa} Lib (GB)", 1, 0, "C", True)
                                            pdf.cell(30, 7, f"D. {letra_activa} Lib %", 1, 0, "C", True)
                                        elif p_sub == "CPU":
                                            pdf.cell(100, 7, "Consumo CPU %", 1, 0, "C", True)
                                        elif p_sub == "LATENCIA":
                                            pdf.cell(100, 7, "Latencia de Respuesta (ms)", 1, 0, "C", True)

                                        pdf.cell(50, 7, "Estado", 1, 1, "C", True)

                                        pdf.set_text_color(0, 0, 0)
                                        pdf.set_font("Arial", "", 8.5)
                                        
                                        # 🔥 MOSTRAR REGISTROS DEL RANGO (CON LÍMITE PARA EVITAR SOBRECARGA)
                                        for idx, r in enumerate(registros_a_mostrar):
                                            f_registro = r['fecha_registro']
                                            f_text = f_registro.strftime("%d/%m/%Y %H:%M") if hasattr(f_registro, 'strftime') else str(f_registro)
                                            
                                            alerta_activa = None
                                            for al in lista_alertas_servidor:
                                                comp_bd = normalizar_componente(al['componente'])
                                                comp_rep = normalizar_componente(p_sub)
                                                
                                                if comp_bd == comp_rep:
                                                    f_ini = al['fecha_inicio']
                                                    f_fin = al['fecha_fin']
                                                    
                                                    inicio_tolerante = f_ini - timedelta(minutes=2)
                                                    fin_tolerante = (f_fin + timedelta(minutes=2)) if f_fin is not None else None
                                                    
                                                    if f_registro >= inicio_tolerante and (fin_tolerante is None or f_registro <= fin_tolerante):
                                                        alerta_activa = al
                                                        if not alerta_detectada_global: 
                                                            alerta_detectada_global = al
                                                        break

                                            msg_alerta = str(alerta_activa['tipo_alerta']).upper().strip() if alerta_activa else "ESTABLE"

                                            pdf.set_fill_color(242, 242, 242) if (idx % 2 == 0) else pdf.set_fill_color(255, 255, 255)
                                            pdf.set_text_color(0, 0, 0)
                                            pdf.cell(35, 6, f_text, 1, 0, "C", True)
                                            
                                            if p_sub == "RAM":
                                                pdf.cell(35, 6, f"{r.get('val_ram_total_gb', 0.0)} GB", 1, 0, "C", True)
                                                pdf.cell(35, 6, f"{r.get('val_ram_disponible_gb', 0.0)} GB", 1, 0, "C", True)
                                                pdf.cell(30, 6, f"{r.get('val_ram_disponible_pct', 0.0)} %", 1, 0, "C", True)
                                            elif "DISCO" in p_sub:
                                                d_idx = bloque["disco_idx"]
                                                d_tot = r.get(f'val_disco_{d_idx}_total_gb', 0.0)
                                                d_lib = r.get(f'val_disco_{d_idx}_libres_gb', 0.0)
                                                d_pct = r.get(f'val_disco_{d_idx}_pct_libre', 0.0)
                                                pdf.cell(35, 6, f"{d_tot} GB", 1, 0, "C", True)
                                                pdf.cell(35, 6, f"{d_lib} GB", 1, 0, "C", True)
                                                pdf.cell(30, 6, f"{d_pct} %", 1, 0, "C", True)
                                            elif p_sub == "CPU":
                                                pdf.cell(100, 6, f"{r.get('val_cpu', 0.0)} %", 1, 0, "C", True)
                                            elif p_sub == "LATENCIA":
                                                pdf.cell(100, 6, f"{r.get('val_latencia_ping', 0.0)} ms", 1, 0, "C", True)

                                            if "CRITICO" in msg_alerta or "CRÍTICO" in msg_alerta:
                                                pdf.set_fill_color(255, 214, 214)
                                                pdf.set_text_color(180, 0, 0)
                                            elif any(w in msg_alerta for w in ["PRECAUCION", "PRECAUCIÓN", "ADVERTENCIA"]):
                                                pdf.set_fill_color(255, 243, 205)
                                                pdf.set_text_color(133, 100, 4)
                                            else:
                                                pdf.set_fill_color(212, 239, 223)
                                                pdf.set_text_color(21, 103, 51)

                                            pdf.cell(50, 6, msg_alerta, 1, 1, "C", True)
                                            pdf.set_text_color(0, 0, 0)
                                        
                                        # Mostrar resumen al final del bloque
                                        pdf.ln(2)
                                        pdf.set_font("Arial", "I", 8)
                                        pdf.cell(0, 5, f"Total de registros mostrados para {p_sub}: {len(registros_a_mostrar)}", 0, 1, "L")
                                        if len(datos_muestras) > MAX_REGISTROS_POR_BLOQUE:
                                            pdf.cell(0, 5, f"Total de registros disponibles: {len(datos_muestras)}", 0, 1, "L")
                                        pdf.ln(4)

                                    # 🔥 USAR LA FUNCIÓN CORREGIDA PARA OBTENER BYTES
                                    bytes_pdf = obtener_bytes_pdf(pdf)

                                kb_size_pdf = round(len(bytes_pdf) / 1024.0, 2)
                                
                                st.session_state["rep_pdf"] = bytes_pdf
                                st.session_state["rep_name_pdf"] = f"{nombre_base_archivo}.pdf"
                                st.session_state["rep_listo"] = True
                                
                                guardar_reporte_archivado(
                                    st.session_state["rep_name_pdf"], "PDF", ip_objetivo, bytes_pdf, 
                                    usuario_id, kb_size_pdf, ultima_muestra=ultima_muestra_obj, alerta_vinculada=alerta_detectada_global
                                )
                                st.success(f"✅ Reporte PDF generado con {len(datos_muestras)} registros y guardado exitosamente en el historial.")
                            except Exception as e_pdf:
                                st.error(f"❌ Error generando PDF: {str(e_pdf)}")

                        # --- OPCIÓN CSV ---
                        elif formato_sel == "CSV":
                            try:
                                with st.spinner(f"Generando CSV con {len(datos_muestras)} registros..."):
                                    lineas_csv = []
                                    bloques_metricas = []
                                    if s_prefix == "INTEGRAL":
                                        bloques_metricas = [
                                            {"titulo": "USO DE CPU (TODOS LOS REGISTROS DEL RANGO)", "prefix": "CPU", "cols": ["FECHA_REGISTRO", "CPU_PCT", "ESTADO"]},
                                            {"titulo": "MEMORIA RAM (TODOS LOS REGISTROS DEL RANGO)", "prefix": "RAM", "cols": ["FECHA_REGISTRO", "RAM_TOTAL_GB", "RAM_DISPONIBLE_GB", "RAM_DISPONIBLE_PCT", "ESTADO"]},
                                            {"titulo": "LATENCIA DE RED (TODOS LOS REGISTROS DEL RANGO)", "prefix": "LATENCIA", "cols": ["FECHA_REGISTRO", "LATENCIA_MS", "ESTADO"]}
                                        ]
                                        for i in range(1, 7):
                                            campo_sensor = f'id_sensor_disco_{i}'
                                            if serv_info.get(campo_sensor) and int(serv_info[campo_sensor]) > 0:
                                                letra_activa = letras_discos[i]
                                                bloques_metricas.append({
                                                    "titulo": f"DISCO {letra_activa} (TODOS LOS REGISTROS DEL RANGO)", 
                                                    "prefix": f"DISCO{i}", 
                                                    "disco_idx": i,
                                                    "cols": ["FECHA_REGISTRO", f"DISCO_{letra_activa}_TOTAL_GB", f"DISCO_{letra_activa}_LIBRE_GB", f"DISCO_{letra_activa}_LIBRE_PCT", "ESTADO"]
                                                })
                                    else:
                                        if s_prefix == "RAM":
                                            columnas = ["FECHA_REGISTRO", "RAM_TOTAL_GB", "RAM_DISPONIBLE_GB", "RAM_DISPONIBLE_PCT", "ESTADO"]
                                        elif "DISCO" in s_prefix and num_disco_activo:
                                            l_act = letras_discos[num_disco_activo]
                                            columnas = ["FECHA_REGISTRO", f"DISCO_{l_act}_TOTAL_GB", f"DISCO_{l_act}_LIBRE_GB", f"DISCO_{l_act}_LIBRE_PCT", "ESTADO"]
                                        elif s_prefix == "CPU":
                                            columnas = ["FECHA_REGISTRO", "CPU_PCT", "ESTADO"]
                                        elif s_prefix == "LATENCIA":
                                            columnas = ["FECHA_REGISTRO", "LATENCIA_MS", "ESTADO"]
                                        else:
                                            columnas = ["FECHA_REGISTRO", "VALOR", "ESTADO"]
                                        bloques_metricas = [{"titulo": sensor_general.upper() + " (TODOS LOS REGISTROS DEL RANGO)", "prefix": s_prefix, "disco_idx": num_disco_activo, "cols": columnas}]

                                    # Agregar cabecera con información del reporte
                                    lineas_csv.append(f"REPORTE DE MONITOREO - {sensor_general.upper()}")
                                    lineas_csv.append(f"Servidor: {serv_seleccionado} ({ip_objetivo})")
                                    lineas_csv.append(f"Rango Temporal: {fecha_i.strftime('%d/%m/%Y')} al {fecha_f.strftime('%d/%m/%Y')}")
                                    lineas_csv.append(f"Analista: {nombre_analista}")
                                    lineas_csv.append(f"Total de Registros: {len(datos_muestras)}")
                                    lineas_csv.append("")
                                    lineas_csv.append("=" * 80)
                                    lineas_csv.append("")

                                    for bloque in bloques_metricas:
                                        lineas_csv.append(f"=== {bloque['titulo']} ===")
                                        lineas_csv.append(",".join(bloque["cols"]))
                                        
                                        # 🔥 MOSTRAR TODOS LOS REGISTROS DEL RANGO
                                        for r in datos_muestras:
                                            f_registro = r['fecha_registro']
                                            f_t = f_registro.strftime("%Y-%m-%d %H:%M:%S") if hasattr(f_registro, 'strftime') else str(f_registro)
                                            
                                            alerta_activa = None
                                            for al in lista_alertas_servidor:
                                                comp_bd = normalizar_componente(al['componente'])
                                                comp_rep = normalizar_componente(bloque["prefix"])
                                                
                                                if comp_bd == comp_rep:
                                                    f_ini = al['fecha_inicio']
                                                    f_fin = al['fecha_fin']
                                                    if f_registro >= (f_ini - timedelta(minutes=2)) and (f_fin is None or f_registro <= (f_fin + timedelta(minutes=2))):
                                                        alerta_activa = al
                                                        if not alerta_detectada_global: 
                                                            alerta_detectada_global = al
                                                        break

                                            txt_alerta_csv = str(alerta_activa['tipo_alerta']).upper().strip() if alerta_activa else "ESTABLE"

                                            if bloque["prefix"] == "RAM":
                                                row_str = f"{f_t},{r.get('val_ram_total_gb',0.0)},{r.get('val_ram_disponible_gb',0.0)},{r.get('val_ram_disponible_pct',0.0)},{txt_alerta_csv}"
                                            elif "DISCO" in bloque["prefix"]:
                                                d_idx = bloque["disco_idx"]
                                                row_str = f"{f_t},{r.get(f'val_disco_{d_idx}_total_gb',0.0)},{r.get(f'val_disco_{d_idx}_libres_gb',0.0)},{r.get(f'val_disco_{d_idx}_pct_libre',0.0)},{txt_alerta_csv}"
                                            elif bloque["prefix"] == "CPU":
                                                row_str = f"{f_t},{r.get('val_cpu',0.0)},{txt_alerta_csv}"
                                            elif bloque["prefix"] == "LATENCIA":
                                                row_str = f"{f_t},{r.get('val_latencia_ping',0.0)},{txt_alerta_csv}"
                                            else:
                                                row_str = f"{f_t},0,{txt_alerta_csv}"
                                            
                                            lineas_csv.append(row_str)
                                        
                                        # Agregar resumen al final del bloque
                                        lineas_csv.append("")
                                        lineas_csv.append(f"Total de registros para {bloque['prefix']}: {len(datos_muestras)}")
                                        lineas_csv.append("")
                                        lineas_csv.append("-" * 40)
                                        lineas_csv.append("")

                                    # Agregar pie de página
                                    lineas_csv.append("")
                                    lineas_csv.append("=" * 80)
                                    lineas_csv.append(f"Reporte generado por SIMPOL v4.0")
                                    lineas_csv.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                    lineas_csv.append(f"Total de registros en el reporte: {len(datos_muestras)}")

                                    bytes_csv = "\n".join(lineas_csv).encode("utf-8")
                                    kb_size_csv = round(len(bytes_csv) / 1024.0, 2)
                                    
                                    st.session_state["rep_csv"] = bytes_csv
                                    st.session_state["rep_name_csv"] = f"{nombre_base_archivo}.csv"
                                    st.session_state["rep_listo"] = True
                                    
                                    guardar_reporte_archivado(
                                        st.session_state["rep_name_csv"], "CSV", ip_objetivo, bytes_csv, 
                                        usuario_id, kb_size_csv, ultima_muestra=ultima_muestra_obj, alerta_vinculada=alerta_detectada_global
                                    )
                                    st.success(f"✅ Reporte CSV generado con {len(datos_muestras)} registros y archivado con éxito.")
                            except Exception as e_csv:
                                st.error(f"❌ Error generando CSV: {str(e_csv)}")

        # =====================================================================
        # PESTAÑA 2: REPOSITORIO HISTÓRICO FILTRADO
        # =====================================================================
        with tab2:
            st.markdown(f"#### 📜 Histórico Filtrado por Sensor General: `{sensor_general}`")
            
            lista_historica = listar_reportes_archivados_filtrado(ip_objetivo, s_prefix)
            
            if not lista_historica:
                st.info(f"📭 No hay reportes archivados de la categoría `{sensor_general}` para este nodo de infraestructura.")
            else:
                st.markdown(
                    '<div style="background-color:#003366; color:white; padding:10px; border-radius:4px; font-weight:bold; font-size:13px; font-family:Arial; display:flex; align-items:center;">'
                    '<div style="flex:3;">Nombre del Archivo Guardado</div>'
                    '<div style="flex:1.2; text-align:center;">Formato</div>'
                    '<div style="flex:1.2; text-align:center;">Tamaño</div>'
                    '<div style="flex:2.5; text-align:center;">Fecha de Almacenamiento</div>'
                    '<div style="flex:2.2; text-align:center;">Generado Por (Analista)</div>'
                    '<div style="flex:1.8; text-align:center;">Acción</div>'
                    '</div>', unsafe_allow_html=True
                )

                st.markdown(
                    '<style>'
                    '.badge-pdf { background-color: #b30000; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size:11px; }'
                    '.badge-csv { background-color: #1b5e20; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size:11px; }'
                    '</style>', unsafe_allow_html=True
                )

                for item in lista_historica:
                    fecha_str = item['fecha_generacion'].strftime("%Y-%m-%d %H:%M:%S") if hasattr(item['fecha_generacion'], 'strftime') else str(item['fecha_generacion'])
                    badge_class = "badge-pdf" if item['formato'] == "PDF" else "badge-csv"
                    analista_nombre = item['registrado_por'] if item['registrado_por'] else "Sistema"
                    
                    st.markdown(
                        f'<div style="background-color:#ffffff; border-bottom:1px solid #ddd; padding:12px 10px; font-size:12px; font-family:Arial; display:flex; align-items:center; margin-bottom: 2px;">'
                        f'<div style="flex:3; font-weight:bold; color:#111;">🗃️ {item["nombre_archivo"]}</div>'
                        f'<div style="flex:1.2; text-align:center;"><span class="{badge_class}">{item["formato"]}</span></div>'
                        f'<div style="flex:1.2; text-align:center; color:#444;">{item["tamanio_kb"]} KB</div>'
                        f'<div style="flex:2.5; text-align:center; color:#444; font-family:monospace;">{fecha_str}</div>'
                        f'<div style="flex:2.2; text-align:center; color:#003366; font-weight:500;">👤 {analista_nombre}</div>'
                        f'<div style="flex:1.8; text-align:center;"></div>'
                        f'</div>', unsafe_allow_html=True
                    )
                    
                    with st.container():
                        reporte_blob = descargar_contenido_blob(item['id'])
                        if reporte_blob:
                            st.download_button(
                                label=f"📥 Abrir {item['formato']}",
                                data=bytes(reporte_blob),
                                file_name=item['nombre_archivo'],
                                mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                                key=f"dl_final_{item['id']}",
                                use_container_width=True
                            )
    else:
        st.info("🔍 Selecciona los filtros y presiona **'Filtrar'** para comenzar.")

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("cargo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)