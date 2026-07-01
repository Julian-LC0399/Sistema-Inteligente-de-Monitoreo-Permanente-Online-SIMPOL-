import streamlit as st
import logging
import time
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# FUNCIONES PARA CONSULTAR ALERTAS
# =====================================================================

def obtener_alertas_activas(ip_servidor=None, criticidad=None):
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
            
            if criticidad and criticidad != "-- Todas --":
                condiciones.append("a.tipo_alerta = %s")
                params.append(criticidad)
            
            if condiciones:
                query += " AND " + " AND ".join(condiciones)
            
            query += " ORDER BY a.fecha_inicio DESC"
            cursor.execute(query, tuple(params))
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo alertas activas: {e}")
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
    nivel = alerta.get('tipo_alerta', 'ESTABLE').upper().strip()
    componente = alerta.get('componente', 'Desconocido')
    fecha_inicio = alerta.get('fecha_inicio', datetime.now())
    comentario = alerta.get('comentario', '')
    ip = alerta.get('ip_servidor', '')
    nombre_alias = alerta.get('nombre_alias', ip)
    val_pct = alerta.get('val_disponible_pct_momento', 0)
    val_gb = alerta.get('val_disponible_gb_momento', 0)
    val_total = alerta.get('val_total_gb_momento', 0)
    
    nivel_normalizado = nivel.upper()
    
    if nivel_normalizado in ["CRITICO", "CRITICAL"]:
        color_borde = "#FF4B4B"
        color_fondo = "#FFF5F5"
        color_texto = "#B71C1C"
        icono = "🔴"
        badge_color = "#FF4B4B"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "CRITICO"
    elif nivel_normalizado in ["PRECAUCION", "WARNING", "PRECAUCIÓN"]:
        color_borde = "#F1C40F"
        color_fondo = "#FFFDF5"
        color_texto = "#F57F17"
        icono = "🟡"
        badge_color = "#F1C40F"
        badge_texto = "#1A1A1A"
        nivel_mostrar = "PRECAUCION"
    else:
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        icono = "🟢"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "ESTABLE"
    
    if isinstance(fecha_inicio, datetime):
        fecha_str = fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_str = str(fecha_inicio)
    
    detalles = f"Valor: {val_pct:.1f}%"
    if val_gb > 0 and val_total > 0:
        detalles += f" | Libre: {val_gb:.1f}/{val_total:.1f} GB"
    
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
                <span style="font-size: 22px;">{icono}</span>
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
            <span>📅 <b>Inicio:</b> {fecha_str}</span>
            <span>📊 <b>{detalles}</b></span>
        </div>
        {f'<div style="margin-top: 10px; font-size: 14px; color: #555; background-color: #FFFFFF; padding: 10px 14px; border-radius: 6px; border: 1px solid #E8E8E8;">💬 <b>Comentario:</b> {comentario}</div>' if comentario else ''}
    </div>
    """
    return html


# =====================================================================
# PESTAÑA 1: ALERTAS ACTIVAS (ENCAPSULADA EN FRAGMENTO)
# =====================================================================
@st.fragment(run_every=15)
def renderizar_alertas_fragment(filtro_servidor, filtro_criticidad, servidores):
    if filtro_servidor == "-- Seleccione un Servidor --":
        st.info("🔍 Seleccione un servidor para visualizar las alertas.")
        return
    elif filtro_criticidad == "-- Todas --":
        st.info("🎯 Seleccione una criticidad para filtrar las alertas.")
        return
    
    serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_servidor), None)
    if not serv_info:
        st.warning("⚠️ Servidor no encontrado en el catalogo.")
        return
    
    ip_filtro = serv_info['ip']
    
    # VERIFICAR SI EL AGENTE ESTA ACTIVO
    agente_activo, _ = obtener_estado_agente(ip_filtro)
    
    # SI EL AGENTE NO ESTA ACTIVO, MOSTRAR MENSAJE Y DETENER
    if not agente_activo:
        st.info("⏳ Agente inactivo. Mostrando ultimos datos registrados.")
        return
    
    alertas_activas = obtener_alertas_activas(ip_filtro, filtro_criticidad)
    
    color_contador = "#C62828" if len(alertas_activas) > 0 else "#2E7D32"
    st.markdown(f"""
        <div style="background-color: #FFFFFF; padding: 8px 16px; border-radius: 6px; border: 1px solid #E0E0E0; margin-bottom: 15px; display: inline-block;">
            <span style="color: #333333; font-weight: bold; font-size: 15px;">🔔 Alertas activas:</span>
            <span style="color: {color_contador}; font-weight: bold; font-size: 18px; margin-left: 8px;">{len(alertas_activas)}</span>
        </div>
    """, unsafe_allow_html=True)
    
    if not alertas_activas:
        st.success("✅ No hay alertas activas para este servidor con la criticidad seleccionada.")
    else:
        for alerta in alertas_activas:
            html_card = renderizar_alerta_card(alerta)
            st.markdown(html_card, unsafe_allow_html=True)
    
    st.session_state["ultima_actualizacion"] = datetime.now()


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
    
    # ==========================================================================
    # MOSTRAR ANALISTA EN SESIÓN - ESTILO GESTION.PY
    # ==========================================================================
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-alertas">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Monitoreo en tiempo real de los componentes criticos</p>', unsafe_allow_html=True)
    
    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_TODAS = "-- Todas --"

    # INICIALIZAR ESTADOS
    if "filtro_alerta_servidor" not in st.session_state:
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
    if "filtro_alerta_criticidad" not in st.session_state:
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
    if "ultima_actualizacion" not in st.session_state:
        st.session_state["ultima_actualizacion"] = datetime.now()

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
    opciones_criticidad = [VALOR_TODAS, "CRITICO", "PRECAUCION", "ESTABLE"]

    # FILTROS
    col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
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
            label_visibility="collapsed"
        )
    with col_f3:
        if st.button("🔄 Actualizar", key="btn_refresh_alerta", use_container_width=True):
            st.rerun()

    # Mostrar hora de ultima actualizacion
    st.markdown(f"""
        <div style="text-align: right; color: #888; font-size: 12px; padding: 5px 0;">
            🔄 Auto-refresh: 15s (si agente activo) | Ultima actualizacion: <b>{st.session_state.get("ultima_actualizacion", datetime.now()).strftime("%H:%M:%S")}</b>
        </div>
    """, unsafe_allow_html=True)

    filtro_servidor = st.session_state.get("filtro_alerta_servidor", VALOR_DEFECTO)
    filtro_criticidad = st.session_state.get("filtro_alerta_criticidad", VALOR_TODAS)

    if filtro_servidor == VALOR_DEFECTO:
        st.info("🔍 Seleccione un servidor para visualizar las alertas.")
    elif filtro_criticidad == VALOR_TODAS:
        st.info("🎯 Seleccione una criticidad para filtrar las alertas.")
    else:
        renderizar_alertas_fragment(filtro_servidor, filtro_criticidad, servidores)


if __name__ == "__main__":
    mostrar_pantalla()