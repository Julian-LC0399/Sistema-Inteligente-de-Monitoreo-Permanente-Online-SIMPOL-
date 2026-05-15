import streamlit as st
import base64
import os
from database import conectar_bd
from utils import obtener_telemetria_total, get_resource_path

# Optimizamos la carga de imagen para que solo ocurra UNA vez
@st.cache_resource
def get_base64_image(image_path):
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as f: 
                return base64.b64encode(f.read()).decode()
    except: return None
    return None

@st.cache_data(ttl=10) # Aumentamos un poco el TTL para dar respiro al .exe
def obtener_datos_menu():
    estados = []
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT m.ip_servidor, m.val_cpu, m.estado_sistema, s.nombre_alias
                FROM monitoreo m
                INNER JOIN (
                    SELECT ip_servidor, MAX(fecha_registro) as max_fecha
                    FROM monitoreo GROUP BY ip_servidor
                ) m2 ON m.ip_servidor = m2.ip_servidor AND m.fecha_registro = m2.max_fecha
                INNER JOIN servidores_it s ON m.ip_servidor = s.ip
                WHERE s.estado_monitoreo = 1
            """
            cursor.execute(query)
            estados = cursor.fetchall()
            cursor.close()
    except: pass
    finally:
        if conn: conn.close()
    return estados

def seccion_alertas_dinamicas():
    servidores = obtener_datos_menu()
    if servidores:
        st.markdown("<p style='font-size:11px; font-weight:bold; color:grey; margin-bottom:5px;'>ESTADO VIVO:</p>", unsafe_allow_html=True)
        html_sidebar = ""
        for s in servidores:
            color = "#ff4b4b" if s['estado_sistema'] == "CRÍTICO" else "#f39c12" if s['estado_sistema'] == "PRECAUCIÓN" else "#28a745"
            html_sidebar += f"""
                <div style="border-left: 3px solid {color}; background: #f0f2f6; padding: 5px; 
                            border-radius: 3px; margin-bottom: 2px; font-size: 10px; color: #333;">
                    <b>{s['nombre_alias']}</b> | {s['val_cpu']}%
                </div>
            """
        st.markdown(html_sidebar, unsafe_allow_html=True)

def cambiar_pagina():
    """Función para limpiar todo rastro antes de cambiar de sección"""
    st.cache_data.clear()

# === CAMBIO CLAVE PARA EVITAR EL TYPEERROR ===
def generar_menu(seccion_persistente="🏠 Inicio"):
    with st.sidebar:
        # LOGO OPTIMIZADO
        img_path = get_resource_path("logo-banco.jpg")
        img_b64 = get_base64_image(img_path)
        if img_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/jpeg;base64,{img_b64}" style="width:100%; border-radius:10px; margin-bottom:15px;"></div>', unsafe_allow_html=True)
        
        # MONITOR
        seccion_alertas_dinamicas()
        
        st.divider()

        # NAVEGACIÓN
        opciones = ["🏠 Inicio", "🖥️ Servidores", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
        
        # Lógica de índice para que el radio sepa dónde estaba tras el F5
        try:
            idx = opciones.index(seccion_persistente)
        except (ValueError, KeyError):
            idx = 0

        seleccion = st.radio(
            "Menú", 
            opciones, 
            index=idx, 
            key="nav_radio", 
            label_visibility="collapsed",
            on_change=cambiar_pagina
        )
        
        st.session_state["seccion_actual"] = seleccion

        st.divider()

        # CIERRE DE SESIÓN
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="primary", key="btn_logout"):
            st.query_params.clear()
            for key in list(st.session_state.keys()):
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
        return seleccion