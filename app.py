import streamlit as st
import mysql.connector
import pandas as pd
import plotly.graph_objects as go
import time
import psutil
import requests
import urllib3
from datetime import datetime

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except: pass

st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# --- VARIABLES DE CONEXIÓN ---
PRTG_IP = "127.0.0.1"
API_KEY = "ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======" 
ID_SENSOR = "2094"

def conectar_bd():
    return mysql.connector.connect(host="localhost", user="root", password="1234", database="monitoreo_banco")

def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except: return None

def obtener_telemetria():
    try:
        url = f"https://{PRTG_IP}/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid={ID_SENSOR}&apitoken={API_KEY}"
        r = requests.get(url, timeout=2, verify=False)
        if r.status_code == 200:
            data = r.json()
            val = float(data['sensors'][0].get('lastvalue_raw', 0))
            return val, f"PRTG Sensor {ID_SENSOR}"
    except: pass
    return float(psutil.cpu_percent(interval=None)), "MODO LOCAL"

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- LOGIN ---
if not st.session_state['autenticado']:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>Sistema Inteligente de Monitoreo</p>", unsafe_allow_html=True)
            with st.form("form_acceso"):
                u = st.text_input("USUARIO")
                p = st.text_input("CONTRASEÑA", type="password")
                if st.form_submit_button("AUTENTICAR"):
                    user_info = verificar_usuario(u, p)
                    if user_info:
                        st.session_state['autenticado'] = True
                        st.session_state['user_actual'] = user_info['usuario']
                        st.rerun()
                    else: st.error("Credenciales Inválidas")
    st.stop()

# --- DASHBOARD ---
else:
    with st.sidebar:
        st.markdown("### 🏦 BANCO CARONÍ")
        st.write(f"Analista: **{st.session_state['user_actual']}**")
        if st.button("Cerrar Sesión"):
            st.session_state['autenticado'] = False
            st.rerun()

    st.markdown(f"<h1 style='color:#003366;'>Panel de Monitoreo</h1>", unsafe_allow_html=True)

    cpu_val, cpu_msg = obtener_telemetria()
    ram_val = float(psutil.virtual_memory().percent)

    c1, c2, c3 = st.columns(3)
    c1.metric("USO DE CPU", f"{cpu_val}%", delta=cpu_msg)
    c2.metric("MEMORIA RAM", f"{ram_val}%")
    c3.metric("ESTADO", "ACTIVO")

    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        sql = "INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (datetime.now(), st.session_state['user_actual'], cpu_val, ram_val, "ESTABLE"))
        conn.commit()

        df = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
        conn.close()

        if not df.empty:
            df = df.sort_values('fecha_registro')
            fig = go.Figure()
            
            # CPU - Línea continua
            fig.add_trace(go.Scatter(
                x=df['fecha_registro'], y=df['uso_cpu'], 
                mode='lines', name='CPU %', 
                line=dict(color='#003366', width=3), 
                fill='tozeroy', fillcolor='rgba(0, 51, 102, 0.1)'
            ))
            
            # RAM - Línea punteada (CORREGIDO AQUÍ)
            fig.add_trace(go.Scatter(
                x=df['fecha_registro'], y=df['uso_ram'], 
                mode='lines', name='RAM %', 
                line=dict(color='#D3D3D3', width=2, dash='dot') # 'dash' ahora está dentro de 'line'
            ))
            
            fig.update_layout(
                plot_bgcolor='white', 
                paper_bgcolor='rgba(0,0,0,0)', 
                margin=dict(l=0, r=0, t=30, b=0), 
                height=450, 
                hovermode="x unified", 
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ ERROR TÉCNICO DETECTADO: {e}")
        st.stop()

    time.sleep(5)
    st.rerun()