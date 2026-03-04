import streamlit as st
import mysql.connector
import pandas as pd
import plotly.graph_objects as go
import time
import psutil
import requests
import urllib3
from datetime import datetime

# Desactivar advertencias de certificados SSL para PRTG
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURACIÓN Y RECURSOS ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")

def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass

load_css("style.css")

# --- 2. FUNCIONES DE BACKEND ---
def conectar_bd():
    return mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="1234", 
        database="monitoreo_banco"
    )

def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except:
        return None

def obtener_telemetria():
    try:
        url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
        r = requests.get(url, timeout=1, verify=False)
        if r.status_code == 200:
            val = float(r.json()['sensors'][0].get('lastvalue_raw', 0))
            return val, "PRTG SENSOR"
    except:
        pass
    return float(psutil.cpu_percent(interval=None)), "MODO LOCAL"

# --- 3. LÓGICA DE AUTENTICACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>SISTEMA DE MONITOREO PERMANENTE</p>", unsafe_allow_html=True)
            
            with st.form("form_acceso"):
                u = st.text_input("USUARIO", placeholder="Ingrese ID")
                p = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                
                if st.form_submit_button("AUTENTICAR"):
                    user_info = verificar_usuario(u, p)
                    if user_info:
                        st.session_state['autenticado'] = True
                        st.session_state['user_actual'] = user_info['usuario']
                        st.session_state['nombre_analista'] = user_info['nombre_completo']
                        st.session_state['rol'] = user_info['rol']
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
    st.stop()

# --- 4. DASHBOARD CON NAVEGACIÓN ---
else:
    # Definición de opciones de menú según el ROL
    opciones_menu = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📄 Reportes PDF"]
    if st.session_state.get('rol') == 'admin':
        opciones_menu.append("👥 Gestión de Personal")

    # --- SIDEBAR ---
    with st.sidebar:
        st.image("logo-banco.jpg", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        nombre_display = st.session_state.get('nombre_analista') or st.session_state['user_actual']
        rol_display = st.session_state['rol'].upper()

        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="titulo-seccion-sidebar">Navegación</p>', unsafe_allow_html=True)
        seleccion = st.radio("Ir a:", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state['autenticado'] = False
            st.rerun()

    # --- CUERPO PRINCIPAL (VISTAS DINÁMICAS) ---

    if seleccion == "🏠 Inicio":
        st.markdown(f"<h1 style='color:#003366;'>Bienvenido, {nombre_display}</h1>", unsafe_allow_html=True)
        st.write("---")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            ### Panel de Control de Nodo
            Has ingresado al **Sistema de Monitoreo Permanente (SIMPOL)** del Banco Caroní. 
            Esta plataforma permite supervisar en tiempo real la salud de los recursos críticos del CSU.
            
            **Instrucciones de uso:**
            1. Dirígete a **Monitoreo en Vivo** para observar las métricas de CPU y RAM.
            2. La sección de **Reportes** permite extraer bitácoras históricas.
            3. Si eres administrador, podrás gestionar los accesos en la pestaña de personal.
            """)
        with col2:
            st.info(f"**Sesión actual:**\n\n**Rol:** {rol_display}\n\n**Servidor:** Local/PRTG\n\n**Estado:** Estable")

    elif seleccion == "📊 Monitoreo en Vivo":
        st.markdown(f"<h2 style='color:#003366; margin-top:-30px;'>Centro de Monitoreo: Nodo {st.session_state['user_actual']}</h2>", unsafe_allow_html=True)

        cpu_val, cpu_msg = obtener_telemetria()
        ram_val = float(psutil.virtual_memory().percent)

        m1, m2, m3 = st.columns(3)
        m1.metric("USO DE CPU", f"{cpu_val}%", delta=cpu_msg)
        m2.metric("MEMORIA RAM", f"{ram_val}%", delta="Sincronizado")
        m3.metric("ESTADO", "ACTIVO", delta="Online")

        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            sql_insert = "INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql_insert, (datetime.now(), st.session_state['user_actual'], cpu_val, ram_val, "ESTABLE"))
            conn.commit()

            df = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
            conn.close()

            if not df.empty:
                df = df.sort_values('fecha_registro')
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['fecha_registro'], y=df['uso_cpu'], mode='lines', name='CPU %', line=dict(color='#003366', width=3), fill='tozeroy', fillcolor='rgba(0, 51, 102, 0.1)'))
                fig.add_trace(go.Scatter(x=df['fecha_registro'], y=df['uso_ram'], mode='lines', name='RAM %', line=dict(color='#D3D3D3', width=2, dash='dot')))
                fig.update_layout(plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=30, b=0), height=400, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error de sincronización: {e}")

        time.sleep(5)
        st.rerun()

    elif seleccion == "📄 Reportes PDF":
        st.header("Generación de Documentación")
        st.write("Módulo de exportación de auditoría.")
        st.warning("Esta funcionalidad será activada en el próximo despliegue.")

    elif seleccion == "👥 Gestión de Personal":
        st.header("Administración de Usuarios")
        st.write("Registro y control de analistas del nodo.")
        # Aquí irá el formulario que haremos a continuación
        st.info("Solo el perfil Administrador puede ver esta sección.")