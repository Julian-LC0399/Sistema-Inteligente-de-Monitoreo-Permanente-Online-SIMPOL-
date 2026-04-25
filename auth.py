import streamlit as st
from database import verificar_usuario, conectar_bd 

def registrar_acceso_auditoria(usuario, nombre, rol):
    """
    Inserta un registro en la tabla log_accesos con manejo de errores silencioso para .exe
    """
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            # Nota: Si el banco usa un Proxy o red interna, aquí podrías capturar la IP real.
            # Por ahora, mantenemos la lógica pero aseguramos el cierre de conexiones.
            query = """
                INSERT INTO log_accesos (usuario, nombre_completo, rol, ip_cliente, resultado) 
                VALUES (%s, %s, %s, '127.0.0.1', 'EXITOSO')
            """
            cursor.execute(query, (usuario, nombre, rol))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        # En el .exe, los 'print' van a la consola oculta. Es lo correcto.
        print(f"Error en auditoría de acceso: {e}")

def mostrar_login():
    # === ANCLA DE LIMPIEZA DE LOGIN ===
    # Esto asegura que al autenticar, TODO el formulario desaparezca instantáneamente
    canvas_login = st.empty()

    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown(
                "<h1 style='text-align: center; color: #003366;'>SIMPOL</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h4 style='text-align: center; color: #333333; font-size: 14px;'>Sistema Inteligente de Monitoreo Permanente Online</h4>",
                unsafe_allow_html=True,
            )
            st.write("---")

            # Formulario con Key única para evitar colisiones en el .exe
            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    "<p style='color: #003366; font-weight: bold;'>🔐 Acceso al Sistema</p>",
                    unsafe_allow_html=True,
                )
                usuario = st.text_input("Usuario", key="input_user_login")
                clave = st.text_input("Contraseña", type="password", key="input_pass_login")

                if st.form_submit_button("INGRESAR", use_container_width=True):
                    user_data = verificar_usuario(usuario, clave)
                    
                    if user_data:
                        # 1. PERSISTENCIA DE SESIÓN
                        st.session_state["autenticado"] = True
                        st.session_state["user_id"] = user_data["id"]
                        st.session_state["user_actual"] = user_data["usuario"]
                        st.session_state["nombre_analista"] = user_data["nombre_completo"]
                        st.session_state["rol"] = user_data["rol"].lower()
                        
                        # 2. AUDITORÍA
                        registrar_acceso_auditoria(
                            user_data["usuario"], 
                            user_data["nombre_completo"], 
                            user_data["rol"]
                        )
                        
                        # 3. ACTUALIZACIÓN DE PARÁMETROS URL
                        # Usamos el nuevo formato de query_params
                        st.query_params.update({
                            "session": "active",
                            "uid": str(user_data["id"]),
                            "u": user_data["usuario"],
                            "n": user_data["nombre_completo"],
                            "r": user_data["rol"]
                        })
                        
                        # Vaciamos el contenedor de login manualmente antes del rerun
                        canvas_login.empty()
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Contacte al Oficial de Seguridad.")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer institucional fuera del canvas para que no parpadee
    st.markdown(
        """
        <div style='text-align: center; color: #999; font-size: 12px; margin-top: 50px;'>
            © 2026 SIMPOL - Banco Caroní | Departamento de Infraestructura y Redes
        </div>
        """, 
        unsafe_allow_html=True
    )