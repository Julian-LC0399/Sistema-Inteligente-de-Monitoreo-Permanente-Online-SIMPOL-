import streamlit as st
from database import verificar_usuario
from utils import get_resource_path

def mostrar_login():
    _, col2, _ = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        # Uso de ruta segura para el logo
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.title("🏦 SIMPOL")
            
        st.markdown("<h2 style='text-align: center;'>Acceso al Nodo CSU</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("Usuario (ID Analista)")
            clave = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("INGRESAR SISTEMA", use_container_width=True):
                user_data = verificar_usuario(usuario, clave)
                if user_data:
                    st.session_state["autenticado"] = True
                    st.session_state["user_actual"] = user_data["usuario"]
                    st.session_state["nombre_analista"] = user_data["nombre"]
                    st.session_state["rol"] = user_data["rol"].lower() # Forzamos minúsculas para comparar
                    st.rerun()
                else:
                    st.error("Credenciales no válidas para este nodo.")
        st.markdown('</div>', unsafe_allow_html=True)