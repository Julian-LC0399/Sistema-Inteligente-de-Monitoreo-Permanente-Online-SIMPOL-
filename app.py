import streamlit as st
import mysql.connector
import pandas as pd
import time
import psutil
import requests
import urllib3
from datetime import datetime

# Desactivar alertas de certificados para PRTG
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CARGA DE CSS EXTERNO ---
def load_css(file_name):
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# --- CREDENCIALES PRTG ---
PRTG_IP = "127.0.0.1"
API_KEY = "ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======" 
ID_SENSOR = "2094"

# --- FUNCIONES DE BACKEND ---
def conectar_bd():
    return mysql.connector.connect(
        host="localhost", user="root", password="1234", database="monitoreo_banco"
    )

def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        # BINARY para validación exacta de mayúsculas/minúsculas
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        res = cursor.fetchone()
        conn.close()
        return res
    except: return None

def obtener_metrica_prtg():
    url = f"https://{PRTG_IP}/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid={ID_SENSOR}&apitoken={API_KEY}"
    try:
        r = requests.get(url, timeout=3, verify=False)
        if r.status_code == 200:
            val = float(r.json()['sensors'][0]['lastvalue_raw'])
            return val, f"Sensor {ID_SENSOR} ONLINE"
        return psutil.cpu_percent(), "MODO LOCAL (PRTG OFF)"
    except: return psutil.cpu_percent(), "MODO LOCAL (Error Red)"

# --- GESTIÓN DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

placeholder = st.empty()

# --- PANTALLA DE LOGIN ---
if not st.session_state['autenticado']:
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        
        with col_login:
            # Reemplazo del logo por el título del sistema
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>Sistema Inteligente de Monitoreo Permanente Online</p>", unsafe_allow_html=True)
            
            with st.form("login_simpol"):
                st.markdown("<p style='text-align:center; color:#003366; font-weight:bold; margin-bottom:20px;'>NODO DE CONTROL BANCARIO</p>", unsafe_allow_html=True)
                
                u = st.text_input("USUARIO", placeholder="ID de Analista")
                p = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                
                if st.form_submit_button("AUTENTICAR ACCESO"):
                    user_data = verificar_usuario(u, p)
                    if user_data:
                        st.session_state['autenticado'] = True
                        st.session_state['user_actual'] = user_data['usuario']
                        placeholder.empty() # Borrado total del login
                        st.rerun()
                    else:
                        st.error("Credenciales Incorrectas")
    st.stop()

# --- PANTALLA DASHBOARD (POST-LOGIN) ---
else:
    with st.sidebar:
        st.markdown("## SIMPOL v1.0")
        st.write(f"👤 Analista: **{st.session_state['user_actual']}**")
        if st.button("Cerrar Sesión"):
            st.session_state['autenticado'] = False
            st.rerun()

    st.markdown("<h1 style='color:#003366; margin-top:-60px;'>Panel de Monitoreo en Tiempo Real</h1>", unsafe_allow_html=True)
    
    cpu, msg = obtener_metrica_prtg()
    ram = psutil.virtual_memory().percent

    # Guardar Telemetría en MySQL
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)", 
                       (datetime.now(), st.session_state['user_actual'], cpu, ram, "OK"))
        conn.commit(); conn.close()
    except: pass

    # Visualización de Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("CPU (PRTG)", f"{cpu}%", delta=msg)
    c2.metric("RAM (LOCAL)", f"{ram}%")
    c3.metric("ESTADO", "ACTIVO")

    # Gráfica Histórica
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT fecha_registro, uso_cpu FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 25", conn)
        conn.close()
        if not df.empty:
            st.markdown("<h4 style='color:#003366;'>Histórico de Rendimiento del Nodo</h4>", unsafe_allow_html=True)
            st.area_chart(df.sort_values('fecha_registro').set_index('fecha_registro'), color="#003366")
    except: pass

    # Auto-refresco
    time.sleep(5)
    st.rerun()