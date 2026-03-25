import streamlit as st
from database import verificar_usuario


def mostrar_login():
    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        # Forzamos el color oscuro para que sea visible
        st.markdown(
            "<h1 style='text-align: center; color: #003366;'>SIMPOL</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h4 style='text-align: center; color: #333333;'>Sistema Inteligente de Monitoreo Permanente Online</h4>",
            unsafe_allow_html=True,
        )
        st.write("---")

        with st.form("login_form"):
            st.markdown(
                "<p style='color: #003366; font-weight: bold;'>🔐 Acceso al Sistema</p>",
                unsafe_allow_html=True,
            )
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")

            if st.form_submit_button("INGRESAR", use_container_width=True):
                user_data = verificar_usuario(usuario, clave)
                if user_data:
                    st.session_state["autenticado"] = True
                    st.session_state["user_actual"] = user_data["usuario"]
                    st.session_state["nombre_analista"] = user_data["nombre_completo"]
                    st.session_state["rol"] = user_data["rol"].lower()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        st.markdown("</div>", unsafe_allow_html=True)
