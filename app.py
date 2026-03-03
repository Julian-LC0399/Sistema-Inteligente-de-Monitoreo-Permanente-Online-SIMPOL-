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

# --- 1. CARGA DE RECURSOS ---
def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass

# Configuración inicial de la página
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
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
    # Intento de conexión a PRTG (ID de sensor 2094 según tu configuración)
    try:
        url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
        r = requests.get(url, timeout=1, verify=False)
        if r.status_code == 200:
            val = float(r.json()['sensors'][0].get('lastvalue_raw', 0))
            return val, "PRTG SENSOR"
    except:
        pass
    # Fallback a sensor local si PRTG no responde
    return float(psutil.cpu_percent(interval=None)), "MODO LOCAL"

# --- 3. CONTROL DE ACCESO ---
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
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
    st.stop()

# --- 4. DASHBOARD PRINCIPAL ---
else:
    # --- SIDEBAR ESTILO BANCO CARONÍ ---
    with st.sidebar:
        # Espacio para el Logo Superior
        st.image("logo-banco.jpg", width=200)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Bloque de Identificación del Analista
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {st.session_state['user_actual']}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● CONECTADO - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        # Bloque de Operaciones (Botones de acción futura)
        st.markdown('<p class="titulo-seccion-sidebar">Operaciones</p>', unsafe_allow_html=True)
        st.info("Herramientas de reporte próximamente disponibles.")
        
        # Bloque de Cierre de Sesión (Al final)
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state['autenticado'] = False
            st.rerun()

    # --- CUERPO DEL DASHBOARD ---
    st.markdown(f"<h2 style='color:#003366; margin-top:-30px;'>Centro de Monitoreo: Nodo {st.session_state['user_actual']}</h2>", unsafe_allow_html=True)

    # Captura de métricas en tiempo real
    cpu_val, cpu_msg = obtener_telemetria()
    ram_val = float(psutil.virtual_memory().percent)

    # Fila de Indicadores (Métricas)
    c1, c2, c3 = st.columns(3)
    c1.metric("USO DE CPU", f"{cpu_val}%", delta=cpu_msg)
    c2.metric("MEMORIA RAM", f"{ram_val}%", delta="Sincronizado")
    c3.metric("ESTADO DEL NODO", "ACTIVO", delta="Online")

    # Inserción en Base de Datos y Visualización
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Guardar registro en MySQL
        sql_insert = "INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql_insert, (datetime.now(), st.session_state['user_actual'], cpu_val, ram_val, "ESTABLE"))
        conn.commit()

        # Consultar datos históricos para la gráfica
        df = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
        conn.close()

        if not df.empty:
            df = df.sort_values('fecha_registro')
            
            # Creación de Gráfica Plotly Profesional
            fig = go.Figure()
            
            # Traza de CPU
            fig.add_trace(go.Scatter(
                x=df['fecha_registro'], y=df['uso_cpu'], 
                mode='lines', name='Uso CPU %', 
                line=dict(color='#003366', width=3), 
                fill='tozeroy', fillcolor='rgba(0, 51, 102, 0.1)'
            ))
            
            # Traza de RAM
            fig.add_trace(go.Scatter(
                x=df['fecha_registro'], y=df['uso_ram'], 
                mode='lines', name='Uso RAM %', 
                line=dict(color='#D3D3D3', width=2, dash='dot')
            ))

            # Diseño de la Gráfica
            fig.update_layout(
                plot_bgcolor='white', 
                paper_bgcolor='rgba(0,0,0,0)', 
                margin=dict(l=0, r=0, t=30, b=0), 
                height=400, 
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(range=[0, 100], showgrid=True, gridcolor='#F0F0F0')
            )
            
            st.markdown("---")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error de sincronización con servidor de datos: {e}")

    # Intervalo de refresco (5 segundos)
    time.sleep(5)
    st.rerun()