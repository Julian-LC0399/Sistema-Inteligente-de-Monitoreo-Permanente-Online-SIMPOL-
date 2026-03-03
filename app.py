import streamlit as st
import mysql.connector
import pandas as pd
import time
import psutil
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Acceso - Banco Caroní", layout="wide", page_icon="🏦")

# --- CREDENCIALES PRTG ---
PRTG_IP = "127.0.0.1"
API_KEY = "ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======" 
ID_SENSOR = "2094"

# --- FUNCIÓN DE CONEXIÓN A MYSQL ---
def conectar_bd():
    return mysql.connector.connect(
        host="localhost", user="root", password="1234", database="monitoreo_banco"
    )

# --- SISTEMA DE LOGUEO ---
def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE usuario = %s AND clave = %s"
        cursor.execute(query, (user, password))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado
    except:
        return None

# LÓGICA DE SESIÓN
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔐 Control de Acceso - Infraestructura")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            user_data = verificar_usuario(u, p)
            if user_data:
                st.session_state['autenticado'] = True
                st.session_state['user_actual'] = user_data['usuario']
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop() # Detiene el script aquí si no está logueado

# --- SI LLEGA AQUÍ, EL USUARIO ESTÁ LOGUEADO ---

# Botón para cerrar sesión en la barra lateral
with st.sidebar:
    st.write(f"👤 Usuario: **{st.session_state['user_actual']}**")
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

# --- FUNCIÓN PRTG (LA QUE YA TENÍAS VERDE) ---
def obtener_metrica_prtg():
    url = f"https://{PRTG_IP}/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid={ID_SENSOR}&apitoken={API_KEY}"
    try:
        response = requests.get(url, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            sensores = data.get('sensors', [])
            if sensores:
                return float(sensores[0].get('lastvalue_raw', 0)), f"CONECTADO (Sensor {ID_SENSOR})"
        return psutil.cpu_percent(), "MODO LOCAL (PRTG 401/Off)"
    except:
        return psutil.cpu_percent(), "MODO LOCAL (Error Red)"

# --- DASHBOARD ---
st.title(f"🏦 Monitor Banco Caroní - {st.session_state['user_actual']}")
st.markdown(f"Bienvenido al panel de control. Nivel de acceso: **LECTURA**")

cpu, msg = obtener_metrica_prtg()
ram = psutil.virtual_memory().percent

if "CONECTADO" in msg:
    st.success(f"🟢 {msg}")
else:
    st.warning(f"🟡 {msg}")

# Guardar en MySQL (Telemetría)
try:
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)", 
                   (datetime.now(), st.session_state['user_actual'], cpu, ram, "ESTABLE"))
    conn.commit()
    cursor.close()
    conn.close()
except:
    pass

# Visualización
c1, c2 = st.columns(2)
c1.metric("CPU PRTG", f"{cpu}%")
c2.metric("RAM LOCAL", f"{ram}%")

# Gráfica Histórica
try:
    conn = conectar_bd()
    df = pd.read_sql(f"SELECT fecha_registro, uso_cpu FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 30", conn)
    conn.close()
    if not df.empty:
        st.line_chart(df.sort_values('fecha_registro').set_index('fecha_registro'))
except:
    pass

time.sleep(3)
st.rerun()