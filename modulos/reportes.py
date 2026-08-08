import streamlit as st
from fpdf import FPDF
from database import conectar_bd
from datetime import datetime, timedelta, time
import re
import tempfile
import os

# =====================================================================
# FUNCIÓN DE MUESTREO INTELIGENTE (OPTIMIZADA PARA 15 SEGUNDOS)
# =====================================================================
def muestrear_datos_inteligente(datos, fecha_inicio, fecha_fin):
    """
    Estrategia óptima para datos cada 15 segundos:
    1. Rango < 1 día: muestra cada 10 registros (2.5 minutos)
    2. Rango 1-7 días: muestra cada 30 registros (7.5 minutos)
    3. Rango 7-30 días: muestra cada 60 registros (15 minutos)
    4. Rango > 30 días: muestra cada 120 registros (30 minutos)
    + Siempre incluye puntos críticos (alertas)
    + Siempre incluye cambios de estado
    + Siempre incluye primer y último registro
    """
    if not datos:
        return []
    
    # Calcular días del rango
    rango_dias = (fecha_fin - fecha_inicio).total_seconds() / 86400
    
    # Determinar intervalo de muestreo según el rango
    if rango_dias <= 1:  # Hasta 1 día
        intervalo = 10  # Cada 10 registros (2.5 minutos)
        max_muestras = 2000
    elif rango_dias <= 7:  # Hasta 1 semana
        intervalo = 30  # Cada 30 registros (7.5 minutos)
        max_muestras = 1500
    elif rango_dias <= 30:  # Hasta 1 mes
        intervalo = 60  # Cada 60 registros (15 minutos)
        max_muestras = 1200
    else:  # Hasta 3 meses
        intervalo = 120  # Cada 120 registros (30 minutos)
        max_muestras = 1000
    
    # PASO 1: Identificar registros críticos (siempre se mantienen)
    criticos = []
    normales = []
    
    for registro in datos:
        es_critico = False
        
        # CPU > 75%
        if registro.get('val_cpu', 0) and float(registro.get('val_cpu', 0)) > 75:
            es_critico = True
        
        # RAM < 25%
        if registro.get('val_ram_disponible_pct', 0) and float(registro.get('val_ram_disponible_pct', 100)) < 25:
            es_critico = True
        
        # Discos < 20%
        for d in range(1, 7):
            pct_libre = registro.get(f'val_disco_{d}_pct_libre', 0)
            if pct_libre and float(pct_libre) < 20:
                es_critico = True
                break
        
        # Latencia > 80ms
        if registro.get('val_latencia_ping', 0) and float(registro.get('val_latencia_ping', 0)) > 80:
            es_critico = True
        
        # Cambio de estado de servicio
        if registro.get('estado_servicio_1') != None:
            es_critico = True
        
        if es_critico:
            criticos.append(registro)
        else:
            normales.append(registro)
    
    # PASO 2: Construir resultado
    resultado = []
    
    # 2.1: Incluir TODOS los críticos (hasta 500)
    if criticos:
        if len(criticos) > 500:
            step = len(criticos) // 500
            resultado.extend(criticos[::step][:500])
        else:
            resultado.extend(criticos)
    
    # 2.2: Muestreo de registros normales
    if normales:
        # Calcular cuántos normales podemos incluir
        restantes = max_muestras - len(resultado)
        if restantes > 0:
            step_normales = max(1, len(normales) // restantes)
            resultado.extend(normales[::step_normales][:restantes])
    
    # 2.3: Siempre incluir el primer y último registro
    if datos and datos[-1] not in resultado:
        resultado.append(datos[-1])
    if datos and datos[0] not in resultado:
        resultado.append(datos[0])
    
    # Ordenar por fecha (más reciente primero)
    resultado.sort(key=lambda x: x['fecha_registro'], reverse=True)
    
    return resultado

# =====================================================================
# FUNCIÓN MEJORADA PARA DETECTAR ESTADOS
# =====================================================================
def detectar_estado(registro, prefix, num_disco=None):
    """
    Detecta el estado de un registro según la métrica
    Retorna: ESTABLE, PRECAUCION, CRITICO
    """
    if prefix == "CPU":
        valor = float(registro.get('val_cpu', 0))
        if valor >= 90:
            return "CRITICO"
        elif valor >= 75:
            return "PRECAUCION"
        else:
            return "ESTABLE"
            
    elif prefix == "RAM":
        pct_disponible = float(registro.get('val_ram_disponible_pct', 100))
        # Porcentaje usado (invertido para ser consistente)
        pct_usado = 100 - pct_disponible
        if pct_usado >= 90:  # Menos del 10% disponible
            return "CRITICO"
        elif pct_usado >= 75:  # Menos del 25% disponible
            return "PRECAUCION"
        else:
            return "ESTABLE"
            
    elif "DISCO" in prefix and num_disco:
        pct_libre = float(registro.get(f'val_disco_{num_disco}_pct_libre', 100))
        if pct_libre <= 10:
            return "CRITICO"
        elif pct_libre <= 20:
            return "PRECAUCION"
        else:
            return "ESTABLE"
            
    elif prefix == "LATENCIA":
        latencia = float(registro.get('val_latencia_ping', 0))
        if latencia >= 150:
            return "CRITICO"
        elif latencia >= 80:
            return "PRECAUCION"
        else:
            return "ESTABLE"
    
    return "ESTABLE"

# =====================================================================
# FUNCIÓN MEJORADA PARA EXTRAER CAMBIOS DE ESTADO
# =====================================================================
def extraer_cambios_estado(datos, prefix, num_disco=None):
    """
    Extrae registros con cambios de estado significativos
    Incluye: cambios de estado, estados críticos, y muestras de estados estables
    """
    if not datos:
        return []
    
    resultados = []
    estado_anterior = None
    contador_estable = 0
    primer_registro = True
    
    for registro in datos:
        # Detectar estado actual
        estado_actual = detectar_estado(registro, prefix, num_disco)
        
        # Siempre incluir el primer registro
        if primer_registro:
            registro_con_estado = registro.copy()
            registro_con_estado['_estado'] = estado_actual
            resultados.append(registro_con_estado)
            estado_anterior = estado_actual
            primer_registro = False
            contador_estable = 0
            continue
        
        # Verificar si hay cambio de estado
        if estado_actual != estado_anterior:
            # Cambio de estado detectado
            registro_con_estado = registro.copy()
            registro_con_estado['_estado'] = estado_actual
            resultados.append(registro_con_estado)
            estado_anterior = estado_actual
            contador_estable = 0
        elif estado_actual == "CRITICO":
            # Siempre incluir todos los estados críticos
            registro_con_estado = registro.copy()
            registro_con_estado['_estado'] = estado_actual
            resultados.append(registro_con_estado)
            contador_estable = 0
        elif estado_actual == "PRECAUCION":
            # Incluir precaución con menos frecuencia (cada 5)
            contador_estable += 1
            if contador_estable % 5 == 0:
                registro_con_estado = registro.copy()
                registro_con_estado['_estado'] = estado_actual
                resultados.append(registro_con_estado)
        else:  # ESTABLE
            # Incluir estados estables cada 20 registros
            contador_estable += 1
            if contador_estable % 20 == 0:
                registro_con_estado = registro.copy()
                registro_con_estado['_estado'] = estado_actual
                resultados.append(registro_con_estado)
    
    # Siempre incluir el último registro
    if datos and datos[0] not in resultados:
        ultimo = datos[0].copy()
        ultimo['_estado'] = detectar_estado(datos[0], prefix, num_disco)
        resultados.append(ultimo)
    
    return resultados

# =====================================================================
# FUNCIÓN PARA LIMITAR RANGO A 3 MESES
# =====================================================================
def limitar_rango_3_meses(fecha_inicio, fecha_fin):
    """
    Limita el rango a máximo 3 meses
    """
    diferencia = (fecha_fin - fecha_inicio).days
    if diferencia > 90:  # 3 meses
        fecha_inicio = fecha_fin - timedelta(days=90)
        return fecha_inicio, fecha_fin, True
    return fecha_inicio, fecha_fin, False

# =====================================================================
# FUNCIÓN AUXILIAR PARA NORMALIZAR COMPONENTES
# =====================================================================
def normalizar_componente(nombre):
    if nombre is None:
        return ""
    
    nombre = str(nombre).strip()
    
    discos_map = {
        "C:": "DISCO1", "C:\\": "DISCO1", "C": "DISCO1",
        "D:": "DISCO2", "D:\\": "DISCO2", "D": "DISCO2",
        "E:": "DISCO3", "E:\\": "DISCO3", "E": "DISCO3",
        "F:": "DISCO4", "F:\\": "DISCO4", "F": "DISCO4",
        "G:": "DISCO5", "G:\\": "DISCO5", "G": "DISCO5",
        "Y:": "DISCO6", "Y:\\": "DISCO6", "Y": "DISCO6",
    }
    
    if nombre in discos_map:
        return discos_map[nombre]
    
    if "DISCO" in nombre.upper():
        return nombre.upper()
    
    if nombre.upper() in ["CPU", "RAM", "LATENCIA", "PING"]:
        return nombre.upper()
    
    if "SERVICIO" in nombre.upper():
        match = re.search(r'SERVICIO[_]?(\d+)', nombre.upper())
        if match:
            return f"SERVICIO{match.group(1)}"
        return nombre.upper()
    
    return nombre.upper().replace("_", "").replace(" ", "").replace(":", "").replace("\\", "")

# =====================================================================
# FUNCIÓN PARA LIMPIAR EL ESTADO DEL MÓDULO REPORTES
# =====================================================================
def limpiar_estado_reportes():
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
        'filtros_aplicados',
        'widget_rep_fi',
        'widget_rep_ff',
        'widget_rep_formato',
        'widget_rep_sensor_general'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state["filtros_aplicados"] = False

# =====================================================================
# FUNCIONES DE ACTUALIZACIÓN DE FECHAS
# =====================================================================
def actualizar_fecha_inicial():
    if "widget_rep_fi" in st.session_state:
        st.session_state["reporte_fecha_i"] = st.session_state["widget_rep_fi"]

def actualizar_fecha_final():
    if "widget_rep_ff" in st.session_state:
        st.session_state["reporte_fecha_f"] = st.session_state["widget_rep_ff"]

# =====================================================================
# CLASE DE CONFIGURACIÓN GRÁFICA DEL REPORTE PDF
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
        self.cell(0, 10, f"Generado por SIMPOL | Pagina {self.page_no()} | Confidencial", 0, 0, "C")

# =====================================================================
# FUNCIONES DE CONSULTA
# =====================================================================
def obtener_datos_reporte(ip_servidor, fecha_inicio, fecha_fin):
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT * FROM monitoreo 
            WHERE ip_servidor = %s 
              AND fecha_registro >= %s 
              AND fecha_registro <= %s
            ORDER BY fecha_registro DESC
        """
        cursor.execute(query, (ip_servidor, fecha_inicio, fecha_fin))
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        st.error(f"❌ Error consultando registros: {e}")
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
        st.error(f"❌ Error obteniendo alertas: {e}")
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
        st.error(f"❌ Error persistiendo archivo en historico: {e}")
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
        st.error(f"❌ Error listando historico filtrado: {e}")
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
# FUNCIÓN PARA OBTENER BYTES DEL PDF
# =====================================================================
def obtener_bytes_pdf(pdf):
    try:
        pdf_bytes = pdf.output(dest='S')
        if isinstance(pdf_bytes, str):
            return pdf_bytes.encode('latin1')
        return pdf_bytes
    except:
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
    
    # Inicializar variables de estado
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
    
    with st.container():
        st.markdown("#### Parámetros de Extracción y Filtrado")

        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            fecha_i = st.date_input(
                "Fecha Inicial:", 
                value=st.session_state.get("reporte_fecha_i", datetime.now() - timedelta(days=1)),
                key="widget_rep_fi"
            )
            if "widget_rep_fi" in st.session_state:
                st.session_state["reporte_fecha_i"] = st.session_state["widget_rep_fi"]
            
        with col_f2:
            fecha_f = st.date_input(
                "Fecha Final:", 
                value=st.session_state.get("reporte_fecha_f", datetime.now()),
                key="widget_rep_ff"
            )
            if "widget_rep_ff" in st.session_state:
                st.session_state["reporte_fecha_f"] = st.session_state["widget_rep_ff"]
            
        with col_f3:
            formatos_lista = ["PDF", "CSV"]
            formato_sel = st.selectbox(
                "Formato de Exportación:",
                options=formatos_lista,
                index=formatos_lista.index(st.session_state["reporte_formato"]),
                key="widget_rep_formato"
            )
            if "widget_rep_formato" in st.session_state:
                st.session_state["reporte_formato"] = st.session_state["widget_rep_formato"]

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
        if "widget_rep_sensor_general" in st.session_state:
            st.session_state["reporte_sensor"] = st.session_state["widget_rep_sensor_general"]

        col_btn_filtrar, col_btn_limpiar = st.columns(2, gap="small")
        
        with col_btn_filtrar:
            if st.button("🔍 Filtrar", use_container_width=True, key="btn_aplicar_filtros"):
                st.session_state["filtros_aplicados"] = True
                st.success("✅ Filtros aplicados correctamente.")
                st.rerun()
        
        with col_btn_limpiar:
            if st.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_clear_all_filters"):
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

        if st.session_state.get("filtros_aplicados", False):
            st.info(f"📌 Filtros activos: Servidor: {st.session_state['reporte_servidor']} | Sensor: {st.session_state['reporte_sensor']} | Fechas: {st.session_state['reporte_fecha_i'].strftime('%d/%m/%Y')} al {st.session_state['reporte_fecha_f'].strftime('%d/%m/%Y')}")

    # =====================================================================
    # GENERACIÓN DE REPORTE
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
        
        # LIMITAR A 3 MESES
        fecha_i, fecha_f, limitado = limitar_rango_3_meses(fecha_i, fecha_f)
        if limitado:
            st.warning(f"⚠️ Rango limitado a 3 meses (desde {fecha_i.strftime('%d/%m/%Y')} hasta {fecha_f.strftime('%d/%m/%Y')})")
        
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
                # Obtener datos
                with st.spinner("🔄 Consultando base de datos..."):
                    datos_completos = obtener_datos_reporte(ip_objetivo, dt_inicio, dt_fin)
                
                if not datos_completos:
                    st.warning(f"⚠️ Telemetría no disponible para `{serv_seleccionado}` en este rango temporal.")
                else:
                    # Muestrear datos inteligentemente
                    datos_muestreados = muestrear_datos_inteligente(datos_completos, dt_inicio, dt_fin)
                    
                    # Mostrar información
                    primera_fecha = datos_completos[-1]['fecha_registro'] if datos_completos else None
                    ultima_fecha = datos_completos[0]['fecha_registro'] if datos_completos else None
                    
                    reduccion = len(datos_completos) - len(datos_muestreados)
                    pct_reduccion = (reduccion / len(datos_completos)) * 100 if datos_completos else 0
                    
                    st.info(f"📊 {len(datos_completos)} registros originales -> {len(datos_muestreados)} muestras ({pct_reduccion:.1f}% de reducción) | Periodo: {primera_fecha.strftime('%d/%m/%Y %H:%M')} - {ultima_fecha.strftime('%d/%m/%Y %H:%M')}")

                    col_btn_gen1, col_btn_gen2 = st.columns([3, 1])
                    with col_btn_gen1:
                        ejecutar_reporte = st.button(f"📊 GENERAR Y ARCHIVAR REPORTE ({formato_sel})", use_container_width=True, key="btn_run_report")
                    
                    if ejecutar_reporte:
                        nombre_base_archivo = f"reporte_{s_prefix}_{serv_info['nombre_alias']}_{fecha_i.strftime('%Y%m%d')}"
                        alerta_detectada_global = None
                        lista_alertas_servidor = obtener_alertas_reporte(ip_objetivo, dt_inicio, dt_fin)
                        ultima_muestra_obj = datos_completos[0] if datos_completos else None

                        # --- OPCIÓN PDF ---
                        if formato_sel == "PDF":
                            try:
                                with st.spinner(f"📄 Generando PDF con {len(datos_muestreados)} muestras..."):
                                    pdf = PDF()
                                    pdf.add_page()
                                    pdf.set_font("Arial", "B", 11)
                                    pdf.cell(0, 7, f"REPORTE: {sensor_general.upper()}", 0, 1)
                                    pdf.set_font("Arial", "", 10)
                                    pdf.cell(50, 6, f"Servidor: {serv_info['nombre_alias']} ({ip_objetivo})", 0, 1)
                                    pdf.cell(50, 6, f"Rango: {fecha_i.strftime('%d/%m/%Y')} al {fecha_f.strftime('%d/%m/%Y')}", 0, 1)
                                    pdf.cell(50, 6, f"Analista: {nombre_analista}", 0, 1)
                                    pdf.cell(50, 6, f"Registros: {len(datos_completos)} -> {len(datos_muestreados)} muestras", 0, 1)
                                    pdf.ln(5)

                                    # Construir bloques de metricas SOLO con sensores activos
                                    bloques_metricas = []
                                    
                                    if s_prefix == "INTEGRAL":
                                        if serv_info.get('id_sensor_cpu') and int(serv_info['id_sensor_cpu']) > 0:
                                            bloques_metricas.append({"prefix": "CPU", "num_disco": None})
                                        if serv_info.get('id_sensor_ram') and int(serv_info['id_sensor_ram']) > 0:
                                            bloques_metricas.append({"prefix": "RAM", "num_disco": None})
                                        for i in range(1, 7):
                                            if serv_info.get(f'id_sensor_disco_{i}') and int(serv_info[f'id_sensor_disco_{i}']) > 0:
                                                bloques_metricas.append({"prefix": f"DISCO{i}", "num_disco": i})
                                        if serv_info.get('id_sensor_latencia') and int(serv_info['id_sensor_latencia']) > 0:
                                            bloques_metricas.append({"prefix": "LATENCIA", "num_disco": None})
                                    else:
                                        bloques_metricas = [{"prefix": s_prefix, "num_disco": num_disco_activo}]

                                    if not bloques_metricas:
                                        pdf.set_font("Arial", "B", 10)
                                        pdf.set_text_color(180, 0, 0)
                                        pdf.cell(0, 10, "⚠️ No hay sensores activos configurados para este servidor", 0, 1, "C")
                                    else:
                                        # Procesar alertas una sola vez
                                        alertas_por_componente = {}
                                        for al in lista_alertas_servidor:
                                            comp = normalizar_componente(al['componente'])
                                            if comp not in alertas_por_componente:
                                                alertas_por_componente[comp] = []
                                            alertas_por_componente[comp].append(al)

                                        # Procesar cada metrica con los datos muestreados
                                        for bloque in bloques_metricas:
                                            p_sub = bloque["prefix"]
                                            num_disco = bloque["num_disco"]
                                            
                                            # Extraer cambios de estado de los datos muestreados
                                            datos_metricas = extraer_cambios_estado(datos_muestreados, p_sub, num_disco)
                                            
                                            if not datos_metricas:
                                                continue
                                            
                                            # Titulo de la metrica
                                            titulo_mostrar = p_sub
                                            if num_disco:
                                                letra = letras_discos[num_disco]
                                                titulo_mostrar = f"DISCO {letra}"
                                            
                                            pdf.set_font("Arial", "B", 10)
                                            pdf.set_text_color(0, 51, 102)
                                            pdf.cell(0, 8, f"MÉTRICA - {titulo_mostrar}", 0, 1)
                                            
                                            # Encabezados
                                            pdf.set_fill_color(0, 51, 102)
                                            pdf.set_text_color(255, 255, 255)
                                            pdf.set_draw_color(180, 180, 180)
                                            pdf.set_font("Arial", "B", 9)
                                            
                                            pdf.cell(35, 7, "Fecha Registro", 1, 0, "C", True)
                                            
                                            if p_sub == "RAM":
                                                pdf.cell(35, 7, "RAM Total", 1, 0, "C", True)
                                                pdf.cell(35, 7, "RAM Disp (GB)", 1, 0, "C", True)
                                                pdf.cell(30, 7, "RAM Disp %", 1, 0, "C", True)
                                            elif "DISCO" in p_sub and num_disco:
                                                letra_activa = letras_discos[num_disco]
                                                pdf.cell(35, 7, f"D. {letra_activa} Tot", 1, 0, "C", True)
                                                pdf.cell(35, 7, f"D. {letra_activa} Lib", 1, 0, "C", True)
                                                pdf.cell(30, 7, f"D. {letra_activa} Lib %", 1, 0, "C", True)
                                            elif p_sub == "CPU":
                                                pdf.cell(100, 7, "Consumo CPU %", 1, 0, "C", True)
                                            elif p_sub == "LATENCIA":
                                                pdf.cell(100, 7, "Latencia (ms)", 1, 0, "C", True)
                                            
                                            pdf.cell(50, 7, "Estado", 1, 1, "C", True)
                                            
                                            pdf.set_text_color(0, 0, 0)
                                            pdf.set_font("Arial", "", 8.5)
                                            
                                            comp_rep = normalizar_componente(p_sub)
                                            alertas_relevantes = alertas_por_componente.get(comp_rep, [])
                                            
                                            for idx, r in enumerate(datos_metricas):
                                                f_registro = r['fecha_registro']
                                                f_text = f_registro.strftime("%d/%m/%Y %H:%M") if hasattr(f_registro, 'strftime') else str(f_registro)
                                                
                                                alerta_activa = None
                                                for al in alertas_relevantes:
                                                    f_ini = al['fecha_inicio']
                                                    f_fin = al['fecha_fin']
                                                    inicio_tolerante = f_ini - timedelta(minutes=2)
                                                    fin_tolerante = (f_fin + timedelta(minutes=2)) if f_fin is not None else None
                                                    
                                                    if f_registro >= inicio_tolerante and (fin_tolerante is None or f_registro <= fin_tolerante):
                                                        alerta_activa = al
                                                        if not alerta_detectada_global: 
                                                            alerta_detectada_global = al
                                                        break
                                                
                                                # Determinar mensaje de alerta
                                                if alerta_activa:
                                                    msg_alerta = str(alerta_activa['tipo_alerta']).upper().strip()
                                                else:
                                                    msg_alerta = r.get('_estado', 'ESTABLE')
                                                
                                                # Color de fondo y texto según estado
                                                pdf.set_fill_color(242, 242, 242) if (idx % 2 == 0) else pdf.set_fill_color(255, 255, 255)
                                                pdf.set_text_color(0, 0, 0)
                                                pdf.cell(35, 6, f_text, 1, 0, "C", True)
                                                
                                                # Valores según métrica
                                                if p_sub == "RAM":
                                                    pdf.cell(35, 6, f"{r.get('val_ram_total_gb', 0.0)} GB", 1, 0, "C", True)
                                                    pdf.cell(35, 6, f"{r.get('val_ram_disponible_gb', 0.0)} GB", 1, 0, "C", True)
                                                    pdf.cell(30, 6, f"{r.get('val_ram_disponible_pct', 0.0)} %", 1, 0, "C", True)
                                                elif "DISCO" in p_sub and num_disco:
                                                    d_tot = r.get(f'val_disco_{num_disco}_total_gb', 0.0)
                                                    d_lib = r.get(f'val_disco_{num_disco}_libres_gb', 0.0)
                                                    d_pct = r.get(f'val_disco_{num_disco}_pct_libre', 0.0)
                                                    pdf.cell(35, 6, f"{d_tot} GB", 1, 0, "C", True)
                                                    pdf.cell(35, 6, f"{d_lib} GB", 1, 0, "C", True)
                                                    pdf.cell(30, 6, f"{d_pct} %", 1, 0, "C", True)
                                                elif p_sub == "CPU":
                                                    pdf.cell(100, 6, f"{r.get('val_cpu', 0.0)} %", 1, 0, "C", True)
                                                elif p_sub == "LATENCIA":
                                                    pdf.cell(100, 6, f"{r.get('val_latencia_ping', 0.0)} ms", 1, 0, "C", True)
                                                
                                                # COLOR SEGÚN ESTADO (VERDE, AMARILLO, ROJO)
                                                if "CRITICO" in msg_alerta or "CRÍTICO" in msg_alerta:
                                                    # ROJO para CRITICO
                                                    pdf.set_fill_color(255, 200, 200)  # Fondo rojo claro
                                                    pdf.set_text_color(180, 0, 0)      # Texto rojo oscuro
                                                elif any(w in msg_alerta for w in ["PRECAUCION", "PRECAUCIÓN", "ADVERTENCIA"]):
                                                    # AMARILLO para PRECAUCION
                                                    pdf.set_fill_color(255, 243, 200)  # Fondo amarillo claro
                                                    pdf.set_text_color(180, 130, 0)    # Texto amarillo oscuro
                                                else:
                                                    # VERDE para ESTABLE
                                                    pdf.set_fill_color(200, 240, 210)  # Fondo verde claro
                                                    pdf.set_text_color(0, 120, 40)     # Texto verde oscuro
                                                
                                                pdf.cell(50, 6, msg_alerta, 1, 1, "C", True)
                                                pdf.set_text_color(0, 0, 0)  # Restaurar color negro
                                            
                                            pdf.ln(2)
                                            pdf.set_font("Arial", "I", 8)
                                            pdf.set_text_color(100, 100, 100)
                                            pdf.cell(0, 5, f"Cambios de estado detectados: {len(datos_metricas)}", 0, 1)
                                            pdf.ln(4)

                                    bytes_pdf = obtener_bytes_pdf(pdf)

                                kb_size_pdf = round(len(bytes_pdf) / 1024.0, 2)
                                
                                st.session_state["rep_pdf"] = bytes_pdf
                                st.session_state["rep_name_pdf"] = f"{nombre_base_archivo}.pdf"
                                st.session_state["rep_listo"] = True
                                
                                guardar_reporte_archivado(
                                    st.session_state["rep_name_pdf"], "PDF", ip_objetivo, bytes_pdf, 
                                    usuario_id, kb_size_pdf, ultima_muestra=ultima_muestra_obj, alerta_vinculada=alerta_detectada_global
                                )
                                st.success(f"✅ PDF generado: {len(datos_completos)} -> {len(datos_muestreados)} muestras")
                            except Exception as e_pdf:
                                st.error(f"❌ Error generando PDF: {str(e_pdf)}")

                        # --- OPCIÓN CSV ---
                        elif formato_sel == "CSV":
                            try:
                                with st.spinner(f"📄 Generando CSV con {len(datos_muestreados)} muestras..."):
                                    lineas_csv = []
                                    
                                    lineas_csv.append(f"REPORTE DE MONITOREO - {sensor_general.upper()}")
                                    lineas_csv.append(f"Servidor: {serv_seleccionado} ({ip_objetivo})")
                                    lineas_csv.append(f"Rango Temporal: {fecha_i.strftime('%d/%m/%Y')} al {fecha_f.strftime('%d/%m/%Y')}")
                                    lineas_csv.append(f"Analista: {nombre_analista}")
                                    lineas_csv.append(f"Registros: {len(datos_completos)} -> {len(datos_muestreados)} muestras")
                                    lineas_csv.append("")
                                    lineas_csv.append("=" * 80)
                                    lineas_csv.append("")
                                    
                                    bloques_metricas = []
                                    
                                    if s_prefix == "INTEGRAL":
                                        if serv_info.get('id_sensor_cpu') and int(serv_info['id_sensor_cpu']) > 0:
                                            bloques_metricas.append({"prefix": "CPU", "num_disco": None})
                                        if serv_info.get('id_sensor_ram') and int(serv_info['id_sensor_ram']) > 0:
                                            bloques_metricas.append({"prefix": "RAM", "num_disco": None})
                                        for i in range(1, 7):
                                            if serv_info.get(f'id_sensor_disco_{i}') and int(serv_info[f'id_sensor_disco_{i}']) > 0:
                                                bloques_metricas.append({"prefix": f"DISCO{i}", "num_disco": i})
                                        if serv_info.get('id_sensor_latencia') and int(serv_info['id_sensor_latencia']) > 0:
                                            bloques_metricas.append({"prefix": "LATENCIA", "num_disco": None})
                                    else:
                                        bloques_metricas = [{"prefix": s_prefix, "num_disco": num_disco_activo}]
                                    
                                    for bloque in bloques_metricas:
                                        p_sub = bloque["prefix"]
                                        num_disco = bloque["num_disco"]
                                        
                                        datos_metricas = extraer_cambios_estado(datos_muestreados, p_sub, num_disco)
                                        
                                        if not datos_metricas:
                                            continue
                                        
                                        titulo_mostrar = p_sub
                                        if num_disco:
                                            letra = letras_discos[num_disco]
                                            titulo_mostrar = f"DISCO {letra}"
                                        
                                        lineas_csv.append(f"=== {titulo_mostrar} ===")
                                        
                                        if p_sub == "RAM":
                                            headers = ["FECHA_REGISTRO", "RAM_TOTAL_GB", "RAM_DISPONIBLE_GB", "RAM_DISPONIBLE_PCT", "ESTADO"]
                                        elif "DISCO" in p_sub and num_disco:
                                            letra = letras_discos[num_disco]
                                            headers = ["FECHA_REGISTRO", f"DISCO_{letra}_TOTAL_GB", f"DISCO_{letra}_LIBRE_GB", f"DISCO_{letra}_LIBRE_PCT", "ESTADO"]
                                        elif p_sub == "CPU":
                                            headers = ["FECHA_REGISTRO", "CPU_PCT", "ESTADO"]
                                        elif p_sub == "LATENCIA":
                                            headers = ["FECHA_REGISTRO", "LATENCIA_MS", "ESTADO"]
                                        else:
                                            headers = ["FECHA_REGISTRO", "VALOR", "ESTADO"]
                                        
                                        lineas_csv.append(",".join(headers))
                                        
                                        for r in datos_metricas:
                                            f_registro = r['fecha_registro']
                                            f_t = f_registro.strftime("%Y-%m-%d %H:%M:%S") if hasattr(f_registro, 'strftime') else str(f_registro)
                                            estado = r.get('_estado', 'ESTABLE')
                                            
                                            if p_sub == "RAM":
                                                row = f"{f_t},{r.get('val_ram_total_gb',0.0)},{r.get('val_ram_disponible_gb',0.0)},{r.get('val_ram_disponible_pct',0.0)},{estado}"
                                            elif "DISCO" in p_sub and num_disco:
                                                row = f"{f_t},{r.get(f'val_disco_{num_disco}_total_gb',0.0)},{r.get(f'val_disco_{num_disco}_libres_gb',0.0)},{r.get(f'val_disco_{num_disco}_pct_libre',0.0)},{estado}"
                                            elif p_sub == "CPU":
                                                row = f"{f_t},{r.get('val_cpu',0.0)},{estado}"
                                            elif p_sub == "LATENCIA":
                                                row = f"{f_t},{r.get('val_latencia_ping',0.0)},{estado}"
                                            else:
                                                row = f"{f_t},0,{estado}"
                                            
                                            lineas_csv.append(row)
                                        
                                        lineas_csv.append("")
                                        lineas_csv.append(f"Cambios de estado detectados: {len(datos_metricas)}")
                                        lineas_csv.append("")
                                        lineas_csv.append("-" * 40)
                                        lineas_csv.append("")

                                    bytes_csv = "\n".join(lineas_csv).encode("utf-8")
                                    kb_size_csv = round(len(bytes_csv) / 1024.0, 2)
                                    
                                    st.session_state["rep_csv"] = bytes_csv
                                    st.session_state["rep_name_csv"] = f"{nombre_base_archivo}.csv"
                                    st.session_state["rep_listo"] = True
                                    
                                    guardar_reporte_archivado(
                                        st.session_state["rep_name_csv"], "CSV", ip_objetivo, bytes_csv, 
                                        usuario_id, kb_size_csv, ultima_muestra=ultima_muestra_obj, alerta_vinculada=alerta_detectada_global
                                    )
                                    st.success(f"✅ CSV generado: {len(datos_completos)} -> {len(datos_muestreados)} muestras")
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