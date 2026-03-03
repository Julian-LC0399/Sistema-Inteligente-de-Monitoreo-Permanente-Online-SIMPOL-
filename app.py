import streamlit as st
import mysql.connector
import pandas as pd
import time
import psutil
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- FUNCIÓN DE CARGA SEGURA ---
def load_css(file_name):
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide")
load_css("style.css")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

placeholder = st.empty()

if not st.session_state['autenticado']:
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            # Logo del Banco
            try: st.image("logo-banco.jpg", use_container_width=True)
            except: pass
            
            with st.form("login_simpol"):
                # Título forzado a azul mediante clase CSS
                st.markdown("<h2 class='titulo-login'>CONTROL DE ACCESO</h2>", unsafe_allow_html=True)
                
                u = st.text_input("USUARIO", placeholder="ID de Analista")
                # El CSS ocultará el botón del ojo automáticamente
                p = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                
                if st.form_submit_button("INGRESAR AL SISTEMA"):
                    # Aquí conectas con tu función verificar_usuario
                    if u == "admin" and p == "1234": # Prueba
                        st.session_state['autenticado'] = True
                        st.session_state['user_actual'] = u
                        placeholder.empty()
                        st.rerun()
                    else:
                        st.error("Credenciales Incorrectas")
    st.stop()

# --- DASHBOARD (POST-LOGIN) ---
else:
    with st.sidebar:
        st.write(f"Sesión: {st.session_state['user_actual']}")
        if st.button("Cerrar Sesión"):
            st.session_state['autenticado'] = False
            st.rerun()
    
    st.title("Panel de Monitoreo SIMPOL")
    st.write("Bienvenido al sistema.")