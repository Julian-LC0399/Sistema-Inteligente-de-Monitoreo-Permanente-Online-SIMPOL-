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
            query = """
                INSERT INTO log_accesos (usuario, nombre_completo, rol, ip_cliente, resultado) 
                VALUES (%s, %s, %s, '127.0.0.1', 'EXITOSO')
            """
            cursor.execute(query, (usuario, nombre, rol))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error en auditoría de acceso: {e}")

def mostrar_login():
    # === ANCLA DE LIMPIEZA DE LOGIN ===
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

            # Mantenemos el formulario seguro con Key única para el .exe
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
                        # 1. TRUCO MAESTRO: Limpiar los parámetros residuales del logout (?s=0...)
                        # Esto evita que app.py lea la URL corrupta post-logout.
                        st.query_params.clear()
                        
                        # 2. PERSISTENCIA DE SESIÓN ATÓMICA EN MEMORIA (Prioridad absoluta)
                        st.session_state["autenticado"] = True
                        st.session_state["user_id"] = user_data["id"]
                        st.session_state["user_actual"] = user_data["usuario"]
                        st.session_state["nombre_analista"] = user_data["nombre_completo"]
                        st.session_state["rol"] = user_data["rol"].lower()
                        
                        # 3. AUDITORÍA SÍNCRONA
                        registrar_acceso_auditoria(
                            user_data["usuario"], 
                            user_data["nombre_completo"], 
                            user_data["rol"]
                        )
                        
                        # 4. ASIGNACIÓN LIMPIA DE NUEVOS PARÁMETROS
                        st.query_params.update({
                            "s": "1",
                            "p": "🏠 Inicio",
                            "r": user_data["rol"].lower(),
                            "uid": str(user_data["id"]),
                            "u": user_data["usuario"],
                            "n": user_data["nombre_completo"]
                        })
                        
                        # 5. DESMONTAJE VISUAL Y REFRESCO INMEDIATO
                        canvas_login.empty()
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Contacte al Oficial de Seguridad.")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer institucional fuera del canvas para evitar parpadeos
    st.markdown(
        """
        <div style='text-align: center; color: #999; font-size: 12px; margin-top: 50px;'>
            © 2026 SIMPOL - Banco Caroní | Departamento de Infraestructura y Redes
        </div>
        """, 
        unsafe_allow_html=True
    )