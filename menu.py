import streamlit as st
import base64
import os
from utils import get_resource_path

@st.cache_resource
def get_base64_image(image_path):
    """Carga y procesa el logo institucional de forma eficiente en memoria"""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as f: 
                return base64.b64encode(f.read()).decode()
    except Exception: 
        return None
    return None

def cambiar_pagina():
    """Manejador seguro para la conmutación de secciones y purga del estado residual"""
    if "widget_navegacion" in st.session_state:
        nueva_seccion = st.session_state["widget_navegacion"]
        seccion_anterior = st.session_state.get("seccion_actual", "🏠 Inicio")
        
        # Si el usuario realmente cambió de módulo, ejecutamos la purga en el State
        if nueva_seccion != seccion_anterior:
            
            # 1. Purga de Alertas
            if seccion_anterior == "🔔 Alertas":
                claves_alertas = [
                    "sb_alerta_srv", "filtro_alerta_servidor",
                    "filtro_alerta_criticidad"
                ]
                for clave in claves_alertas:
                    if clave in st.session_state:
                        del st.session_state[clave]
            
            # Purga de Umbrales
            if seccion_anterior == "⚙️ Umbrales":
                claves_umbrales = [
                    "filtro_umbral_servidor", 
                    "filtro_umbral_componente",
                    "justificacion_umbrales"
                ]
                for clave in claves_umbrales:
                    if clave in st.session_state:
                        del st.session_state[clave]
            
            # 2. Purga de Infraestructura / Monitoreo
            if seccion_anterior in ["🖥️ Monitoreo en vivo", "🖥️ Servidores"]:
                claves_infra = [
                    "filtro_monitoreo_nombre", "filtro_monitoreo_sensor", 
                    "servidor_seleccionado", "filtro_servidor_nombre", 
                    "accion_infra"
                ]
                for clave in claves_infra:
                    if clave in st.session_state:
                        del st.session_state[clave]

            # Actualizamos la sección actual en el estado maestro
            st.session_state["seccion_actual"] = nueva_seccion

def generar_menu():
    """Genera la estructura del menú lateral totalmente aislada de app.py"""
    
    # ==========================================================================
    # DETECTOR DE CLIC EN LOGOUT (HTML PARSER)
    # ==========================================================================
    if st.query_params.get("logout") == "1":
        st.query_params.clear()
        st.query_params.update({
            "s": "0",
            "p": "🏠 Inicio",
            "r": "",
            "uid": "",
            "n": ""
        })
        st.session_state["autenticado"] = False
        st.session_state["seccion_actual"] = "🏠 Inicio"
        
        claves_a_remover = ["rol", "user_id", "user_actual", "nombre_analista", "permisos", "accion_personal"]
        for clave in claves_a_remover:
            if clave in st.session_state:
                del st.session_state[clave]
        st.rerun()

    with st.sidebar:
        st.markdown("""
            <style>
                .sidebar-institucional { padding: 5px; }
                div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {
                    color: #003366 !important;
                    font-weight: bold !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-institucional">', unsafe_allow_html=True)
        
        # ==========================================================================
        # 1. CONTROL DE RUTA Y RENDERIZADO DEL LOGO INSTITUCIONAL
        # ==========================================================================
        img_path = None
        for ext in [".png", ".jpg", ".jpeg"]:
            posible_ruta = get_resource_path(f"logo-banco{ext}")
            if os.path.exists(posible_ruta):
                img_path = posible_ruta
                break
            
            posible_ruta_local = os.path.abspath(f"logo-banco{ext}")
            if os.path.exists(posible_ruta_local):
                img_path = posible_ruta_local
                break

        img_b64 = get_base64_image(img_path) if img_path else None

        if img_b64:
            mime_type = "png" if img_path.lower().endswith(".png") else "jpeg"
            st.markdown(f'<div style="text-align:center;"><img src="data:image/{mime_type};base64,{img_b64}" style="width:100%; max-width:260px; border-radius:4px; margin-bottom:15px;"></div>', unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='color:#003366; text-align:center; font-family:Arial; margin-bottom:20px;'>🏛️ BANCO CARONÍ</h3>", unsafe_allow_html=True)
        
        st.divider()

        # ==========================================================================
        # 2. FILTRADO DINÁMICO DE OPCIONES SEGÚN ROL DE SEGURIDAD
        # ==========================================================================
        opciones = [
            "🏠 Inicio", 
            "🖥️ Servidores", 
            "🖥️ Monitoreo en vivo", 
            "📈 Capacity planning", 
            "🔔 Alertas",
            "⚙️ Umbrales",
            "📄 Reportes"
        ]
        
        rol_usuario = str(st.session_state.get("rol", "operador")).strip().lower()
        if rol_usuario in ["admin", "seguridad", "oficial", "oficial_seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
        
        # ==========================================================================
        # 3. WIDGET DE NAVEGACIÓN - CON KEY CORRECTA
        # ==========================================================================
        # Obtener la sección actual, asegurando que sea válida
        seccion_persistente = st.session_state.get("seccion_actual", "🏠 Inicio")
        if seccion_persistente not in opciones:
            seccion_persistente = "🏠 Inicio"

        # =============================================================
        # IMPORTANTE: Usar key="widget_navegacion" (NO "nav_radio")
        # =============================================================
        seleccion = st.radio(
            "Navegación del Sistema", 
            opciones, 
            index=opciones.index(seccion_persistente) if seccion_persistente in opciones else 0,
            key="widget_navegacion",
            label_visibility="collapsed",
            on_change=cambiar_pagina
        )
        
        # Garantizamos el estado maestro alineado con la interfaz
        st.session_state["seccion_actual"] = seleccion
        st.divider()

        # ==========================================================================
        # 4. BOTÓN DE CIERRE DE SESIÓN EN HTML PURO
        # ==========================================================================
        html_logout = """
        <a href="?logout=1" target="_self" style="text-decoration: none;">
            <div style="
                background-color: #ECEFF1;
                color: #003366 !important;
                border: 1px solid #003366;
                border-radius: 4px;
                height: 40px;
                line-height: 40px;
                text-align: center;
                font-weight: bold;
                font-family: Arial, sans-serif;
                font-size: 14px;
                text-transform: uppercase;
                cursor: pointer;
                transition: all 0.3s ease;
                display: block;
                width: 100%;
            " 
            onmouseover="this.style.backgroundColor='#001f3f'; this.style.color='#FFCC00'; this.style.borderColor='#FFCC00';" 
            onmouseout="this.style.backgroundColor='#ECEFF1'; this.style.color='#003366'; this.style.borderColor='#003366';">
                🚪 Cerrar Sesión
            </div>
        </a>
        """
        st.markdown(html_logout, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)