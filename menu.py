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

@st.cache_data(ttl=3) # TTL bajo para refrescar las alertas del menú con el agente
def obtener_datos_menu():
    estados = []
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # MODIFICACIÓN: Solicitamos los campos de sensores individuales para analizarlos
            query = """
                SELECT m.ip_servidor, m.val_cpu, m.estado_sistema, s.nombre_alias,
                       m.val_cpu, m.val_ram, m.val_disco, m.val_red, m.val_latencia
                FROM monitoreo m
                INNER JOIN (
                    SELECT ip_servidor, MAX(fecha_registro) as max_fecha
                    FROM monitoreo GROUP BY ip_servidor
                ) m2 ON m.ip_servidor = m2.ip_servidor AND m.fecha_registro = m2.max_fecha
                INNER JOIN servidores s ON m.ip_servidor = s.ip
                WHERE s.estado_monitoreo = 1
            """
            cursor.execute(query)
            estados = cursor.fetchall()
            cursor.close()
            conn.close()
    except: 
        return []
    return estados

def cambiar_pagina():
    if "nav_radio" in st.session_state:
        st.session_state["seccion_actual"] = st.session_state["nav_radio"]

def seccion_alertas_dinamicas():
    st.markdown("<p style='font-weight:bold; margin-bottom:5px; color:#003366;'>⚠️ ALERTAS ACTIVAS</p>", unsafe_allow_html=True)
    servidores_estado = obtener_datos_menu()
    
    if not servidores_estado:
        st.caption("🟢 Todos los nodos estables")
        return

    tiene_alertas = False

    for s in servidores_estado:
        # Evaluamos únicamente los servidores que presenten anomalías
        if s['estado_sistema'] in ['CRÍTICO', 'PRECAUCIÓN']:
            tiene_alertas = True
            icono = "🔥" if s['estado_sistema'] == 'CRÍTICO' else "⚠️"
            alias = s['nombre_alias']
            
            # Análisis nativo de umbrales para identificar el sensor en falla
            detalles_fallas = []
            if s['val_cpu'] >= 90: detalles_fallas.append(f"CPU ({s['val_cpu']}% Crítico)")
            elif s['val_cpu'] >= 75: detalles_fallas.append(f"CPU ({s['val_cpu']}%)")
                
            if s['val_ram'] >= 90: detalles_fallas.append(f"RAM ({s['val_ram']}% Crítico)")
            elif s['val_ram'] >= 75: detalles_fallas.append(f"RAM ({s['val_ram']}%)")
                
            if s['val_disco'] >= 90: detalles_fallas.append(f"Disco ({s['val_disco']}% Crítico)")
            elif s['val_disco'] >= 75: detalles_fallas.append(f"Disco ({s['val_disco']}%)")
                
            if s['val_latencia'] > 200: detalles_fallas.append(f"Latencia ({s['val_latencia']}ms Crítica)")
            elif s['val_latencia'] > 100: detalles_fallas.append(f"Latencia ({s['val_latencia']}ms)")

            # En caso de que el estado general cambie pero las métricas individuales estén en rango normal
            if not detalles_fallas:
                detalles_fallas.append("Saturación general de entorno")

            # Formateamos la cadena con los sensores afectados
            sensores_str = ", ".join(detalles_fallas)
            
            # Renderizado visual optimizado para la barra lateral (Sidebar)
            if s['estado_sistema'] == 'CRÍTICO':
                st.error(f"{icono} **{alias}**\n\nFalla en: {sensores_str}")
            else:
                st.warning(f"{icono} **{alias}**\n\nFalla en: {sensores_str}")

    if not tiene_alertas:
        st.success("✅ Infraestructura en estado ÓPTIMO")

def generar_menu():
    seccion_persistente = st.session_state.get("seccion_actual", "🏠 Inicio")
    
    with st.sidebar:
        # LOGO BANCO CARONÍ
        img_path = get_resource_path(os.path.join("assets", "logo_caroni.jpg"))
        img_b64 = get_base64_image(img_path)
        if img_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/jpeg;base64,{img_b64}" style="width:100%; border-radius:10px; margin-bottom:15px;"></div>', unsafe_allow_html=True)
        
        # MONITOR DINÁMICO CON DETALES DE SENSORES
        seccion_alertas_dinamicas()
        
        st.divider()

        # NAVEGACIÓN
        opciones = ["🏠 Inicio", "🖥️ Servidores", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
        
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

        # ==============================================================================
        # CORRECCIÓN DE CIERRE DE SESIÓN FULMINANTE (Evita el auto-login del F5)
        # ==============================================================================
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            # 1. Forzamos la sobreescritura inmediata de los parámetros en la URL a valores vacíos
            # Esto destruye el 's=1' antes del rerun, impidiendo que app.py te reconozca
            st.query_params["s"] = "0"
            st.query_params["p"] = "🏠 Inicio"
            st.query_params["r"] = ""
            st.query_params["uid"] = ""
            st.query_params["n"] = ""
            
            # 2. Desconectamos los interruptores de sesión
            st.session_state["autenticado"] = False
            st.session_state["seccion_actual"] = "🏠 Inicio"
            
            # 3. Limpiamos el resto de variables del analista
            if "rol" in st.session_state: del st.session_state["rol"]
            if "user_id" in st.session_state: del st.session_state["user_id"]
            if "nombre_analista" in st.session_state: del st.session_state["nombre_analista"]
            
            st.rerun()

if __name__ == "__main__":
    generar_menu()