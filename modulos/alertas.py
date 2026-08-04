import streamlit as st
import logging
import time
import unicodedata
from datetime import datetime, timedelta
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================

def normalizar_texto(texto):
    """Elimina tildes y acentos, convierte a mayúsculas"""
    if not texto:
        return "ESTABLE"
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII')
    return texto.upper().strip()

def obtener_nivel_alerta(tipo_alerta):
    """Normaliza el nivel de alerta de la BD para comparación"""
    nivel = normalizar_texto(tipo_alerta)
    
    if nivel in ["CRITICO", "CRITICAL"]:
        return "CRITICO"
    elif nivel in ["PRECAUCION", "PRECAUCIÓN", "WARNING", "PREC"]:
        return "PRECAUCION"
    elif nivel in ["ACTIVO", "ACTIVE", "OK"]:
        return "ACTIVO"
    else:
        return "ESTABLE"

def obtener_parametros_filtro(criticidad):
    """Retorna el valor a filtrar según la criticidad"""
    if criticidad and criticidad != "-- Todas --":
        if criticidad == "CRITICO":
            return "CRÍTICO"
        elif criticidad == "PRECAUCION":
            return "PRECAUCIÓN"
        elif criticidad == "ESTABLE":
            return "ESTABLE"
        elif criticidad == "ACTIVO":
            return "ACTIVO"
        else:
            return criticidad
    return None

# =====================================================================
# FUNCIONES PARA CONSULTAR ALERTAS
# =====================================================================

def obtener_alertas_activas(ip_servidor=None, criticidad=None, limite=50):
    """Obtiene alertas activas con límite para rendimiento"""
    conn = conectar_bd()
    alertas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT a.*, s.nombre_alias 
                FROM alertas a
                LEFT JOIN servidores s ON a.ip_servidor = s.ip
                WHERE a.estado_alerta = 'ACTIVA'
            """
            params = []
            condiciones = []
            
            if ip_servidor:
                condiciones.append("a.ip_servidor = %s")
                params.append(ip_servidor)
            
            filtro_valor = obtener_parametros_filtro(criticidad)
            if filtro_valor:
                condiciones.append("a.tipo_alerta = %s")
                params.append(filtro_valor)
            
            if condiciones:
                query += " AND " + " AND ".join(condiciones)
            
            query += " ORDER BY a.fecha_inicio DESC LIMIT %s"
            params.append(limite)
            
            cursor.execute(query, tuple(params))
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo alertas activas: {e}")
    return alertas

def obtener_ultimas_alertas_por_servidor(ip_servidor=None, criticidad=None, limite=5):
    """
    Obtiene las últimas 'limite' alertas por servidor.
    Usado SOLO cuando el agente está inactivo.
    """
    conn = conectar_bd()
    alertas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT a.*, s.nombre_alias 
                FROM alertas a
                LEFT JOIN servidores s ON a.ip_servidor = s.ip
                WHERE 1=1
            """
            params = []
            
            if ip_servidor:
                query += " AND a.ip_servidor = %s"
                params.append(ip_servidor)
            
            filtro_valor = obtener_parametros_filtro(criticidad)
            if filtro_valor:
                query += " AND a.tipo_alerta = %s"
                params.append(filtro_valor)
            
            query += " ORDER BY a.fecha_inicio DESC LIMIT %s"
            params.append(limite)
            
            cursor.execute(query, tuple(params))
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo últimas alertas: {e}")
    return alertas

def obtener_ultimo_monitoreo(ip_servidor):
    conn = conectar_bd()
    registro = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM monitoreo 
                WHERE ip_servidor = %s 
                ORDER BY fecha_registro DESC LIMIT 1
            """
            cursor.execute(query, (ip_servidor,))
            registro = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo ultimo monitoreo: {e}")
    return registro

def obtener_estado_agente(ip_servidor):
    registro = obtener_ultimo_monitoreo(ip_servidor)
    if registro and registro.get('fecha_registro'):
        if isinstance(registro['fecha_registro'], datetime):
            diferencia = (datetime.now() - registro['fecha_registro']).total_seconds()
            return diferencia <= 60, registro
    return False, registro

# =====================================================================
# FUNCIONES DE RENDERIZADO
# =====================================================================

def renderizar_alerta_card(alerta):
    """Renderiza una tarjeta de alerta con el estilo original"""
    tipo_alerta_raw = alerta.get('tipo_alerta', 'ESTABLE')
    nivel = obtener_nivel_alerta(tipo_alerta_raw)
    
    componente = alerta.get('componente', 'Desconocido')
    fecha_inicio = alerta.get('fecha_inicio', datetime.now())
    comentario = alerta.get('comentario', '')
    ip = alerta.get('ip_servidor', '')
    nombre_alias = alerta.get('nombre_alias', ip)
    val_pct = alerta.get('val_disponible_pct_momento', 0)
    val_gb = alerta.get('val_disponible_gb_momento', 0)
    val_total = alerta.get('val_total_gb_momento', 0)
    
    # Determinar colores según el nivel - SIN ICONOS
    if nivel == "CRITICO":
        color_borde = "#FF4B4B"
        color_fondo = "#FFF5F5"
        color_texto = "#B71C1C"
        badge_color = "#FF4B4B"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "CRÍTICO"
    elif nivel == "PRECAUCION":
        color_borde = "#F1C40F"
        color_fondo = "#FFFDF5"
        color_texto = "#F57F17"
        badge_color = "#F1C40F"
        badge_texto = "#1A1A1A"
        nivel_mostrar = "PRECAUCIÓN"
    elif nivel == "ACTIVO":
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "ACTIVO"
    else:
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "ESTABLE"
    
    if isinstance(fecha_inicio, datetime):
        fecha_str = fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")
        hora_str = fecha_inicio.strftime("%H:%M:%S")
    else:
        fecha_str = str(fecha_inicio)
        hora_str = str(fecha_inicio)
    
    detalles = f"Valor: {val_pct:.1f}%"
    if val_gb > 0 and val_total > 0:
        detalles += f" | Libre: {val_gb:.1f}/{val_total:.1f} GB"
    
    # ESTILO ORIGINAL - SIN ESTADO NI BADGE ADICIONAL
    html = f"""
    <div style="
        border-left: 8px solid {color_borde};
        background-color: {color_fondo};
        padding: 18px 22px;
        margin-bottom: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #E0E0E0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                <span style="font-weight: bold; font-size: 18px; color: {color_texto};">{componente}</span>
                <span style="color: #555; font-size: 15px; font-weight: 500;">{nombre_alias}</span>
                <span style="color: #888; font-size: 13px;">({ip})</span>
            </div>
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                <span style="
                    background-color: {badge_color};
                    color: {badge_texto};
                    padding: 4px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
                ">{nivel_mostrar}</span>
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 15px; color: #444; display: flex; flex-wrap: wrap; gap: 20px;">
            <span><b>Fecha:</b> {fecha_str}</span>
            <span><b>Hora:</b> {hora_str}</span>
            <span><b>{detalles}</b></span>
        </div>
        {f'<div style="margin-top: 10px; font-size: 14px; color: #555; background-color: #FFFFFF; padding: 10px 14px; border-radius: 6px; border: 1px solid #E8E8E8;"><b>Comentario:</b> {comentario}</div>' if comentario else ''}
    </div>
    """
    return html


def renderizar_contenido(placeholder, filtro_servidor, filtro_criticidad, servidores):
    """Función que renderiza el contenido en el placeholder"""
    
    if filtro_servidor == "-- Seleccione un Servidor --":
        with placeholder.container():
            st.info("🔍 Seleccione un servidor para visualizar las alertas.")
        return
    
    serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_servidor), None)
    if not serv_info:
        with placeholder.container():
            st.warning("⚠️ Servidor no encontrado en el catalogo.")
        return
    
    ip_filtro = serv_info['ip']
    agente_activo, ultimo_registro = obtener_estado_agente(ip_filtro)
    
    # =============================================================
    # LÓGICA DE OBTENCIÓN DE ALERTAS
    # =============================================================
    LIMITE_MOSTRAR = 15  # Para alertas activas
    LIMITE_HISTORICAS = 5  # Para cuando el agente está inactivo
    
    if agente_activo:
        # AGENTE ACTIVO: Mostrar alertas activas (lógica original)
        alertas = obtener_alertas_activas(ip_filtro, filtro_criticidad, LIMITE_MOSTRAR)
    else:
        # AGENTE INACTIVO: Mostrar las 5 últimas alertas
        alertas = obtener_ultimas_alertas_por_servidor(ip_filtro, filtro_criticidad, LIMITE_HISTORICAS)
    
    with placeholder.container():
        # Mostrar mensaje de estado del agente si está inactivo
        if not agente_activo:
            fecha_ultimo = ultimo_registro.get('fecha_registro') if ultimo_registro else None
            if fecha_ultimo:
                if isinstance(fecha_ultimo, datetime):
                    fecha_str = fecha_ultimo.strftime("%Y-%m-%d %H:%M:%S")
                    st.warning(f"⏳ Agente inactivo. Mostrando las últimas {LIMITE_HISTORICAS} alertas registradas. Última conexión: {fecha_str}")
                else:
                    st.warning(f"⏳ Agente inactivo. Mostrando las últimas {LIMITE_HISTORICAS} alertas registradas.")
            else:
                st.warning(f"⏳ Agente inactivo. Mostrando las últimas {LIMITE_HISTORICAS} alertas registradas.")
        
        # Mostrar las alertas
        if not alertas:
            if agente_activo:
                st.info("✅ No hay alertas activas para este servidor.")
            else:
                st.info("📭 No hay alertas registradas para este servidor.")
        else:
            for alerta in alertas:
                html_card = renderizar_alerta_card(alerta)
                st.markdown(html_card, unsafe_allow_html=True)


# =====================================================================
# VISTA PRINCIPAL
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    st.markdown("""
        <style>
            .stSelectbox label {
                font-weight: 600 !important;
                font-size: 14px !important;
            }
            .stButton button {
                font-weight: 600 !important;
                border-radius: 6px !important;
            }
            .info-analista-alertas {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-alertas span {
                color: #003366;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">🚨 Alertas Activas</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-alertas">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_TODAS = "-- Todas --"

    if "filtro_alerta_servidor" not in st.session_state:
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
    if "filtro_alerta_criticidad" not in st.session_state:
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
    if "filtro_aplicado" not in st.session_state:
        st.session_state["filtro_aplicado"] = False
    if "modulo_alertas_activo" not in st.session_state:
        st.session_state["modulo_alertas_activo"] = False

    # PROCESAR LIMPIEZA DE FILTROS
    if "_limpiar_alertas" in st.query_params and st.query_params["_limpiar_alertas"] == "1":
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
        st.session_state["filtro_aplicado"] = False
        st.session_state["modulo_alertas_activo"] = False
        del st.query_params["_limpiar_alertas"]
        st.rerun()

    # DETECTAR SI ESTAMOS EN EL MÓDULO CORRECTO
    if st.session_state.get("modulo_actual", "") != "alertas":
        if st.session_state.get("modulo_alertas_activo", False):
            st.session_state["modulo_alertas_activo"] = False

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
    opciones_criticidad = [VALOR_TODAS, "CRITICO", "PRECAUCION", "ESTABLE"]

    servidor_actual = st.session_state.get("filtro_alerta_servidor", VALOR_DEFECTO)
    disabled_criticidad = servidor_actual == VALOR_DEFECTO

    # FILTROS
    col_f1, col_f2, col_f3, col_f4 = st.columns([3, 2, 1, 1])
    with col_f1:
        st.selectbox(
            "Filtrar Servidor", 
            options=opciones_servidores, 
            key="filtro_alerta_servidor", 
            label_visibility="collapsed"
        )
    with col_f2:
        st.selectbox(
            "Filtrar Criticidad", 
            options=opciones_criticidad, 
            key="filtro_alerta_criticidad", 
            label_visibility="collapsed",
            disabled=disabled_criticidad
        )
    with col_f3:
        if st.button("🔍 Filtrar", key="btn_filtrar_alertas", use_container_width=True):
            st.session_state["filtro_aplicado"] = True
            st.session_state["modulo_alertas_activo"] = True
            st.rerun()
    with col_f4:
        if st.button("🧹 Limpiar", key="btn_limpiar_alertas", use_container_width=True):
            st.query_params["_limpiar_alertas"] = "1"
            st.rerun()

    filtro_servidor = st.session_state.get("filtro_alerta_servidor", VALOR_DEFECTO)
    filtro_criticidad = st.session_state.get("filtro_alerta_criticidad", VALOR_TODAS)
    filtro_aplicado = st.session_state.get("filtro_aplicado", False)

    # =============================================================
    # CONTENEDOR CON AUTO-REFRESH
    # =============================================================
    if not filtro_aplicado:
        st.info("🔍 Seleccione los filtros y presione 'Filtrar' para visualizar las alertas.")
        return

    # Crear placeholder
    placeholder = st.empty()
    
    # RENDERIZAR EL CONTENIDO INMEDIATAMENTE
    renderizar_contenido(placeholder, filtro_servidor, filtro_criticidad, servidores)
    
    # BUCLE DE ACTUALIZACIÓN
    while True:
        time.sleep(15)
        renderizar_contenido(placeholder, filtro_servidor, filtro_criticidad, servidores)


if __name__ == "__main__":
    mostrar_pantalla()