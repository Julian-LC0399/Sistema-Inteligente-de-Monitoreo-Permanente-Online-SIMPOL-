import streamlit as st
import mysql.connector
import pandas as pd
import time
import psutil
import requests
import urllib3
from datetime import datetime

# Desactivar advertencias de certificados SSL para conexiones locales
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CARGA DE ESTILOS ---
def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error al cargar CSS: {e}")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# --- VARIABLES GLOBALES PRTG ---
PRTG_IP = "127.0.0.1"
API_KEY = "ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======" 
ID_SENSOR = "2094"

# --- FUNCIONES DE BASE DE DATOS ---
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
        # Validación binaria para exactitud
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except:
        return None

# --- FUNCIONES DE TELEMETRÍA ---
def obtener_datos_monitoreo():
    # Intento de conexión con PRTG
    url = f"https://{PRTG_IP}/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid={ID_SENSOR}&apitoken={API_KEY}"
    try:
        response = requests.get(url, timeout=2, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'sensors' in data and len(data['sensors']) > 0:
                val = float(data['sensors'][0].get('lastvalue_raw', 0))
                return val, f"PRTG: Sensor {ID_SENSOR}"
        
        # Fallback local si PRTG no responde 200
        return float(psutil.cpu_percent(interval=None)), "MODO LOCAL (PRTG OFF)"
    except:
        # Fallback local si hay error de red
        return float(psutil.cpu_percent(interval=None)), "MODO LOCAL (Error Red)"

# --- LÓGICA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- INTERFAZ DE LOGIN ---
if not st.session_state['autenticado']:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_central, _ = st.columns([1, 1.2, 1])
        
        with col_central:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>Sistema Inteligente de Monitoreo Permanente Online</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.markdown("<p style='text-align:center; color:#003366; font-weight:bold;'>LOGIN INSTITUCIONAL</p>", unsafe_allow_html=True)
                user_input = st.text_input("USUARIO", placeholder="Ingrese su ID")
                pass_input = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                
                if st.form_submit_button("AUTENTICAR"):
                    user_data = verificar_usuario(user_input, pass_input)
                    if user_data:
                        st.session_state['autenticado'] = True
                        st.session_state['user_actual'] = user_data['usuario']
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas o usuario no registrado")
    st.stop()

# --- INTERFAZ DASHBOARD (SOLO SI ESTÁ AUTENTICADO) ---
# Sidebar
with st.sidebar:
    st.markdown("## 🏦 BANCO CARONÍ")
    st.write(f"Analista: **{st.session_state['user_actual']}**")
    st.markdown("---")
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

# Cuerpo Principal
st.markdown(f"<h1 style='color:#003366;'>Dashboard de Monitoreo: {st.session_state['user_actual']}</h1>", unsafe_allow_html=True)

# 1. Obtención de métricas en tiempo real
cpu_pct, cpu_msg = obtener_datos_monitoreo()
ram_pct = float(psutil.virtual_memory().percent)

# 2. Visualización de Indicadores Principales
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="USO DE CPU", value=f"{cpu_pct}%", delta=cpu_msg)
with col2:
    st.metric(label="MEMORIA RAM", value=f"{ram_pct}%", delta="Normal")
with col3:
    st.metric(label="ESTADO DEL NODO", value="ACTIVO", delta="Online")

# 3. Persistencia en Base de Datos y Gráfica Histórica
try:
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Insertar nueva telemetría
    cursor.execute(
        "INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)", 
        (datetime.now(), st.session_state['user_actual'], cpu_pct, ram_pct, "ESTABLE")
    )
    conn.commit()
    
    # Consultar últimos 30 registros para la gráfica
    query_grafica = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 30"
    df = pd.read_sql(query_grafica, conn)
    conn.close()
    
    if not df.empty:
        st.markdown("---")
        st.markdown("<h4 style='color:#003366;'>Tendencia de Rendimiento (Últimos 30 Ciclos)</h4>", unsafe_allow_html=True)
        # Reordenar para que la línea fluya de izquierda a derecha
        df_plot = df.sort_values('fecha_registro').set_index('fecha_registro')
        st.area_chart(df_plot, color=["#003366", "#D3D3D3"])

except Exception as e:
    st.warning(f"⚠️ Sincronizando con la Base de Datos... (Datos en vivo activos)")

# 4. Refresco Automático cada 5 segundos
time.sleep(5)
st.rerun()