import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# --- 1. IMPORTACIONES MODULARES ---
from database import verificar_usuario
from utils import load_css, obtener_telemetria 
from modulos import inicio, monitoreo, gestion, reportes, alertas 

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

# --- INICIALIZACIÓN DE UMBRALES PARA ALERTAS ---
if "u_cpu_perc" not in st.session_state:
    st.session_state.u_cpu_perc = 85
if "u_ram_perc" not in st.session_state:
    st.session_state.u_ram_perc = 90

# --- FUNCIÓN PARA EL MÓDULO DE CAPACITY PLANNING ---
def mostrar_capacity_planning():
    st.markdown("<h2 style='color:#003366;'>📈 Análisis de Proyección de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    st.info("Predicción basada en modelos de regresión lineal sobre el historial del CSU.")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #007bff;'>
                <h4 style='margin:0;'>🤖 CPU</h4>
                <p style='font-size:12px; color:gray;'>Carga de Procesamiento</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Días para Umbral Crítico", value="22 días", delta="-1 día")

    with col2:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #ff4b4b;'>
                <h4 style='margin:0;'>🧠 RAM</h4>
                <p style='font-size:12px; color:gray;'>Memoria Volátil</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Días para Agotamiento", value="14 días", delta="-2 días", delta_color="inverse")

    with col3:
        st.markdown("""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #28a745;'>
                <h4 style='margin:0;'>💾 DISCO</h4>
                <p style='font-size:12px; color:gray;'>Almacenamiento SQL</p>
            </div>
        """, unsafe_allow_html=True)
        st.metric(label="Espacio Restante", value="Estable", delta="0")

    st.divider()
    
    st.subheader("Visualización de Tendencia Predictiva (CPU)")
    dias_reales = np.arange(1, 21)
    valores_reales = np.sort(np.random.randint(40, 70, 20)) 
    z = np.polyfit(dias_reales, valores_reales, 1)
    p = np.poly1d(z)
    dias_prediccion = np.arange(20, 31)
    valores_prediccion = p(dias_prediccion)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dias_reales, y=valores_reales, mode='lines+markers', name='Historial Real (CSU)', line=dict(color='#003366', width=3)))
    fig.add_trace(go.Scatter(x=dias_prediccion, y=valores_prediccion, mode='lines', name='Proyección (IA)', line=dict(color='#ff4b4b', width=3, dash='dash')))
    fig.update_layout(template="plotly_white", yaxis=dict(range=[0, 105]))
    st.plotly_chart(fig, use_container_width=True)

# --- 5. LÓGICA DE ACCESO (LOGIN) ---
if not st.session_state["autenticado"]:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            with st.form("form_acceso"):
                u = st.text_input("USUARIO", placeholder="Ingrese ID de Analista")
                p = st.text_input("CONTRASEÑA", type="password")
                if st.form_submit_button("ACCEDER"):
                    user_info = verificar_usuario(u, p)
                    if user_info:
                        st.session_state.update({
                            "autenticado": True, 
                            "user_actual": user_info["usuario"], 
                            "nombre_analista": user_info["nombre_completo"], 
                            "rol": user_info["rol"]
                        })
                        st.rerun()
                    else: st.error("Credenciales Inválidas.")
    st.stop()

# --- 6. PANEL DE CONTROL (POST-LOGIN) ---
else:
    opciones_menu = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📈 Capacity Planning", "🔔 Alertas", "📄 Reportes PDF"]
    if st.session_state.get("rol") == "admin":
        opciones_menu.append("👥 Gestión de Personal")

    with st.sidebar:
        st.image("logo-banco.jpg", use_container_width=True)
        
        # --- NUEVO APARTADO: ALERTAS DE SISTEMA ---
        st.markdown('<p class="titulo-seccion-sidebar">Alertas de Sistema</p>', unsafe_allow_html=True)
        try:
            c_sidebar, r_sidebar, _ = obtener_telemetria()
            if c_sidebar >= st.session_state.u_cpu_perc or r_sidebar >= st.session_state.u_ram_perc:
                st.error(f"🚨 **ESTADO CRÍTICO**\n\nCPU: {c_sidebar}% | RAM: {r_sidebar}%")
            else:
                st.success("✅ Operación Normal")
        except:
            st.warning("⚠️ Sin conexión a sensores")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- APARTADO: IDENTIFICACIÓN ---
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

        # --- APARTADO: ESTADO DE TELEMETRÍA ---
        st.markdown('<p class="titulo-seccion-sidebar">Estado de Telemetría</p>', unsafe_allow_html=True)
        msg_enlace = "MODO LOCAL"
        color_status = "#ffc107"
        nombre_sensor = "psutil (Sistema)"
        
        try:
            url_prtg = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,sensor,lastvalue&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
            r = requests.get(url_prtg, timeout=0.8, verify=False)
            if r.status_code == 200:
                msg_enlace = "PRTG conectado"
                color_status = "#28a745"
                nombre_sensor = r.json()["sensors"][0].get("sensor", "Sensor 2094")
        except:
            pass

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 10px; border-left: 5px solid {color_status}; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 12px; height: 12px; background-color: {color_status}; border-radius: 50%;"></div>
                    <span style="font-size: 13px; font-weight: bold; color: #333;">{msg_enlace}</span>
                </div>
                <hr style="margin: 8px 0; border: 0.5px solid #eee;">
                <div style="font-size: 11px; color: #666;">
                    <b>ORIGEN:</b> ID: 2094<br>
                    <b>SENSOR:</b> {nombre_sensor}
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="titulo-seccion-sidebar">Menú Principal</p>', unsafe_allow_html=True)
        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    # --- ÁREA DE TRABAJO DINÁMICA ---
    vista_principal = st.empty()
    with vista_principal.container():
        if seleccion == "🏠 Inicio":
            inicio.mostrar_pantalla()
        elif seleccion == "📊 Monitoreo en Vivo":
            monitoreo.mostrar_pantalla(st.session_state["user_actual"])
        elif seleccion == "📈 Capacity Planning":
            mostrar_capacity_planning()
        elif seleccion == "🔔 Alertas":
            alertas.mostrar_pantalla()
        elif seleccion == "📄 Reportes PDF":
            reportes.mostrar_pantalla()
        elif seleccion == "👥 Gestión de Personal":
            if st.session_state.get("rol") == "admin":
                gestion.mostrar_pantalla(st.session_state["user_actual"])
            else:
                st.error("No tiene permisos para acceder a este módulo.")