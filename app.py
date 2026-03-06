import streamlit as st
import time

# --- 1. IMPORTACIONES MODULARES ---
# Importamos las herramientas y la conexión
from database import verificar_usuario
from utils import load_css

# Importamos las vistas (componentes)
# Se añade 'reportes' a la importación modular
from modulos import inicio, monitoreo, gestion, reportes

# --- 2. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="SIMPOL | Banco Caroní", 
    layout="wide", 
    page_icon="🏦"
)

# --- 3. APLICAR DISEÑO GLOBAL ---
# Llamamos a la función de utils.py para inyectar el CSS
load_css("style.css")

# --- 4. GESTIÓN DE ESTADO DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- 5. LÓGICA DE ACCESO (LOGIN) ---
if not st.session_state["autenticado"]:
    # Contenedor para centrar el login
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        
        with col_login:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>SISTEMA INTELIGENTE DE MONITOREO PERMANENTE ONLINE</p>", unsafe_allow_html=True)
            
            with st.form("form_acceso"):
                u = st.text_input("USUARIO", placeholder="Ingrese ID de Analista")
                p = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                
                if st.form_submit_button("ACCEDER"):
                    # Uso de la función importada de database.py
                    user_info = verificar_usuario(u, p)
                    
                    if user_info:
                        st.session_state.update({
                            "autenticado": True,
                            "user_actual": user_info["usuario"],
                            "nombre_analista": user_info["nombre_completo"],
                            "rol": user_info["rol"]
                        })
                        st.success("Acceso concedido. Redirigiendo...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas. Intente de nuevo.")
    st.stop()

# --- 6. PANEL DE CONTROL (POST-LOGIN) ---
else:
    # Definición dinámica del menú según el ROL
    opciones_menu = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📄 Reportes PDF"]
    if st.session_state.get("rol") == "admin":
        opciones_menu.append("👥 Gestión de Personal")

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.image("logo-banco.jpg", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        nombre_display = st.session_state.get("nombre_analista") or st.session_state["user_actual"]
        
        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {st.session_state['rol'].upper()} - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="titulo-seccion-sidebar">Menú Principal</p>', unsafe_allow_html=True)
        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    # --- ÁREA DE TRABAJO DINÁMICA ---
    # Usamos st.empty para asegurar que la pantalla se limpie entre módulos
    vista_principal = st.empty()

    with vista_principal.container():
        if seleccion == "🏠 Inicio":
            inicio.mostrar_pantalla()

        elif seleccion == "📊 Monitoreo en Vivo":
            monitoreo.mostrar_pantalla(st.session_state["user_actual"])

        elif seleccion == "📄 Reportes PDF":
            # Sustitución del placeholder por la llamada al módulo real
            reportes.mostrar_pantalla()

        elif seleccion == "👥 Gestión de Personal":
            # Solo se ejecuta si el rol es admin (validación adicional)
            if st.session_state.get("rol") == "admin":
                gestion.mostrar_pantalla(st.session_state["user_actual"])
            else:
                st.error("No tiene permisos para acceder a este módulo.")