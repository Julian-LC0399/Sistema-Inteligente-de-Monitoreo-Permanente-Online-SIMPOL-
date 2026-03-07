import streamlit as st
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go  # <-- NUEVA IMPORTACIÓN PARA LA GRÁFICA

# --- 1. IMPORTACIONES MODULARES ---
from database import verificar_usuario
from utils import load_css
from modulos import inicio, monitoreo, gestion, reportes

# --- 2. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="SIMPOL | Banco Caroní", 
    layout="wide", 
    page_icon="🏦"
)

# --- 3. APLICAR DISEÑO GLOBAL ---
load_css("style.css")

# --- 4. GESTIÓN DE ESTADO DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- FUNCIÓN PARA EL MÓDULO DE CAPACITY PLANNING (CON PLOTLY) ---
def mostrar_capacity_planning():
    st.markdown("<h2 style='color:#003366;'>📈 Análisis de Proyección de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    st.info("Predicción basada en modelos de regresión lineal sobre el historial del CSU.")

    # --- FILA DE MÉTRICAS (3 columnas) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #007bff;'>
                <h4 style='margin:0;'>🤖 CPU</h4>
                <p style='font-size:12px; color:gray;'>Carga de Procesamiento</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Días para Umbral Crítico", value="22 días", delta="-1 día")
        st.caption("Estatus: Carga incremental por procesos batch.")

    with col2:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #ff4b4b;'>
                <h4 style='margin:0;'>🧠 RAM</h4>
                <p style='font-size:12px; color:gray;'>Memoria Volátil</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Días para Agotamiento", value="14 días", delta="-2 días", delta_color="inverse")
        st.caption("Estatus: Riesgo moderado de swap.")

    with col3:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #28a745;'>
                <h4 style='margin:0;'>💾 DISCO</h4>
                <p style='font-size:12px; color:gray;'>Almacenamiento SQL</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Espacio Restante", value="Estable", delta="0")
        st.caption("Estatus: Capacidad óptima.")

    st.divider()
    
    # --- GRÁFICA PROFESIONAL CON PLOTLY.GRAPH_OBJECTS ---
    st.subheader("Visualización de Tendencia Predictiva (CPU)")
    
    # Simulación de datos para la gráfica
    dias_reales = np.arange(1, 21)
    valores_reales = np.sort(np.random.randint(40, 70, 20)) # Historial
    
    # Lógica de Predicción (Regresión Lineal Simple)
    z = np.polyfit(dias_reales, valores_reales, 1)
    p = np.poly1d(z)
    
    dias_prediccion = np.arange(20, 31)
    valores_prediccion = p(dias_prediccion)

    # Crear la figura Plotly
    fig = go.Figure()

    # Añadir Historial
    fig.add_trace(go.Scatter(
        x=dias_reales, y=valores_reales,
        mode='lines+markers',
        name='Historial Real (CSU)',
        line=dict(color='#003366', width=3)
    ))

    # Añadir Proyección
    fig.add_trace(go.Scatter(
        x=dias_prediccion, y=valores_prediccion,
        mode='lines',
        name='Proyección (IA)',
        line=dict(color='#ff4b4b', width=3, dash='dash')
    ))

    # Línea de Umbral Crítico al 95%
    fig.add_hline(y=95, line_dash="dot", line_color="red", annotation_text="Límite Crítico (95%)")

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Días de Monitoreo",
        yaxis_title="Porcentaje de Uso (%)",
        yaxis=dict(range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

# --- 5. LÓGICA DE ACCESO (LOGIN) ---
if not st.session_state["autenticado"]:
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
                    user_info = verificar_usuario(u, p)
                    
                    if user_info:
                        rol_db = user_info["rol"][0] if isinstance(user_info["rol"], (tuple, list)) else user_info["rol"]
                        
                        st.session_state.update({
                            "autenticado": True,
                            "user_actual": user_info["usuario"],
                            "nombre_analista": user_info["nombre_completo"],
                            "rol": rol_db
                        })
                        st.success("Acceso concedido. Redirigiendo...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas. Intente de nuevo.")
    st.stop()

# --- 6. PANEL DE CONTROL (POST-LOGIN) ---
else:
    opciones_menu = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📈 Capacity Planning", "📄 Reportes PDF"]
    if st.session_state.get("rol") == "admin":
        opciones_menu.append("👥 Gestión de Personal")

    with st.sidebar:
        st.image("logo-banco.jpg", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        
        nombre_display = str(st.session_state.get("nombre_analista") or st.session_state.get("user_actual")).upper()
        rol_display = str(st.session_state.get("rol", "USUARIO")).upper()
        
        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="titulo-seccion-sidebar">Menú Principal</p>', unsafe_allow_html=True)
        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    vista_principal = st.empty()

    with vista_principal.container():
        if seleccion == "🏠 Inicio":
            inicio.mostrar_pantalla()

        elif seleccion == "📊 Monitoreo en Vivo":
            monitoreo.mostrar_pantalla(st.session_state["user_actual"])

        elif seleccion == "📈 Capacity Planning":
            mostrar_capacity_planning()

        elif seleccion == "📄 Reportes PDF":
            reportes.mostrar_pantalla()

        elif seleccion == "👥 Gestión de Personal":
            if st.session_state.get("rol") == "admin":
                gestion.mostrar_pantalla(st.session_state["user_actual"])
            else:
                st.error("No tiene permisos para acceder a este módulo.")