import streamlit as st
import mysql.connector
import pandas as pd
import time
import psutil
import requests
import urllib3
from datetime import datetime

# Desactivar alertas SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")

# CSS: Limpieza total y estilos SIMPOL
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stHeader"] {visibility: hidden !important;}
    .stApp { background-color: #F4F7F9; }
    
    .titulo-simpol {
        color: #003366 !important;
        font-family: 'Arial Black', sans-serif;
        font-size: 2.8rem;
        margin-top: -50px;
    }

    /* Estilos de los Inputs */
    input { caret-color: black !important; color: #003366 !important; }
    div[data-baseweb="input"]:focus-within { border-color: black !important; box-shadow: 0 0 0 1px black !important; }
    
    /* Formulario de Login */
    [data-testid="stForm"] {
        border: 2px solid #003366 !important;
        border-radius: 15px;
        background-color: white !important;
        max-width: 450px;
        margin: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES BASE ---
def conectar_bd():
    return mysql.connector.connect(host="localhost", user="root", password="1234", database="monitoreo_banco")

def verificar_usuario(user, password):
    try:
        conn = conectar_bd(); cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        res = cursor.fetchone(); conn.close()
        return res
    except: return None

def obtener_metrica_prtg():
    PRTG_IP, API_KEY, ID_SENSOR = "127.0.0.1", "ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======", "2094"
    url = f"https://{PRTG_IP}/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid={ID_SENSOR}&apitoken={API_KEY}"
    try:
        response = requests.get(url, timeout=3, verify=False)
        if response.status_code == 200:
            val = float(response.json()['sensors'][0]['lastvalue_raw'])
            return val, f"CONECTADO (Sensor {ID_SENSOR})"
        return psutil.cpu_percent(), "MODO LOCAL (PRTG Offline)"
    except: return psutil.cpu_percent(), "MODO LOCAL (Error)"

# --- 3. LÓGICA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        try: st.image("logo-banco.jpg", use_container_width=True)
        except: pass
        with st.form("login_simpol"):
            st.markdown("<h3 style='text-align: center; color: #003366;'>Acceso SIMPOL</h3>", unsafe_allow_html=True)
            u = st.text_input("Usuario")
            p = st.text_input("Clave", type="password")
            if st.form_submit_button("INGRESAR"):
                res = verificar_usuario(u, p)
                if res:
                    st.session_state['autenticado'] = True
                    st.session_state['user_actual'] = res['usuario']
                    st.rerun()
                else: st.error("Error de acceso")
    st.stop()

# --- 4. DASHBOARD SIMPOL ---
else:
    with st.sidebar:
        try: st.image("logo-banco.jpg", use_container_width=True)
        except: pass
        st.markdown("---")
        st.write(f"👤 **Analista:** {st.session_state['user_actual']}")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state['autenticado'] = False
            st.rerun()

    # Títulos
    st.markdown("<h1 class='titulo-simpol'>SIMPOL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #003366; font-weight: bold;'>Sistema Inteligente de Monitoreo Permanente Online</p>", unsafe_allow_html=True)

    # Obtener Datos
    cpu, msg = obtener_metrica_prtg()
    ram = psutil.virtual_memory().percent

    # Alertas de estado
    if "CONECTADO" in msg: st.success(f"🟢 {msg}")
    else: st.warning(f"🟡 {msg}")

    # --- INDICADORES ARRIBA DE LA GRÁFICA ---
    # Creamos dos columnas para que las métricas queden alineadas horizontalmente
    col_cpu, col_ram = st.columns(2)
    with col_cpu:
        st.metric(label="USO DE CPU (PRTG)", value=f"{cpu}%")
    with col_ram:
        st.metric(label="USO DE MEMORIA RAM", value=f"{ram}%")

    st.markdown("---") # Línea divisoria

    # --- GRÁFICA ---
    try:
        conn = conectar_bd()
        # Guardar telemetría actual antes de graficar
        cursor = conn.cursor()
        cursor.execute("INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)", 
                       (datetime.now(), st.session_state['user_actual'], cpu, ram, "ESTABLE"))
        conn.commit()
        
        # Leer históricos para la gráfica
        df = pd.read_sql("SELECT fecha_registro, uso_cpu FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 20", conn)
        conn.close()
        
        if not df.empty:
            st.line_chart(df.sort_values('fecha_registro').set_index('fecha_registro'))
    except:
        st.error("Error de conexión con la base de datos para la gráfica.")

    # Auto-refresco
    time.sleep(5)
    st.rerun()