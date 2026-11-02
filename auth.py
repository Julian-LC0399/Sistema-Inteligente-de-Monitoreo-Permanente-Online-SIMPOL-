import streamlit as st
import streamlit.components.v1 as components
from database import conectar_bd, crear_sesion_activa
from security import procesar_login, cambiar_clave, validar_politica_clave
import os
import sys
import base64
import secrets


def get_resource_path(relative_path):
    """Localiza recursos dentro del paquete .exe o en desarrollo"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_logo_base64():
    """Carga el favicon y lo convierte a base64"""
    logo_paths = [
        get_resource_path("favicon.ico"),
        get_resource_path("centro.jpg"),
        get_resource_path("SIMPOL.jpg"),
        "favicon.ico",
        "centro.jpg",
        "SIMPOL.jpg"
    ]

    for path in logo_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    img_data = f.read()
                    ext = os.path.splitext(path)[1].lower()
                    if ext == '.ico':
                        mime = 'image/x-icon'
                    elif ext in ['.jpg', '.jpeg']:
                        mime = 'image/jpeg'
                    elif ext == '.png':
                        mime = 'image/png'
                    else:
                        mime = 'image/jpeg'
                    return base64.b64encode(img_data).decode(), mime
            except Exception:
                continue

    return None, None


def bloquear_autocompletado():
    """
    Fuerza autocomplete=off en todos los inputs del documento padre (Streamlit)
    y neutraliza el autofill visual de Chrome/Edge.
    """
    st.markdown(
        """
        <style>
        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus,
        input:-webkit-autofill:active {
            -webkit-box-shadow: 0 0 0 30px #ffffff inset !important;
            box-shadow: 0 0 0 30px #ffffff inset !important;
            -webkit-text-fill-color: #000000 !important;
            transition: background-color 5000s ease-in-out 0s;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    components.html(
        """
        <script>
        (function() {
            try {
                const doc = window.parent.document;

                const aplicar = () => {
                    doc.querySelectorAll('input').forEach(el => {
                        el.setAttribute('autocomplete', 'off');
                        el.setAttribute('autocorrect', 'off');
                        el.setAttribute('autocapitalize', 'off');
                        el.setAttribute('spellcheck', 'false');
                    });
                };

                aplicar();

                const obs = new MutationObserver(aplicar);
                obs.observe(doc.body, { childList: true, subtree: true });
            } catch (e) {
                console.warn('No se pudo aplicar bloqueo de autocompletado:', e);
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _encabezado_login(logo_b64, logo_mime):
    """Dibuja el encabezado corporativo"""
    if logo_b64:
        st.markdown(
            f"""
            <div style='text-align: center; padding: 10px 0 5px 0;'>
                <div style='display: flex; align-items: center; justify-content: center; gap: 15px;'>
                    <img src="data:{logo_mime};base64,{logo_b64}" 
                         style='width: 60px; height: 60px; object-fit: contain;' 
                         alt="SIMPOL Logo">
                    <h1 style='color: #003366; font-size: 52px; font-weight: 900; margin: 0; letter-spacing: 2px;'>
                        SIMPOL
                    </h1>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style='text-align: center; padding: 10px 0 5px 0;'>
                <h1 style='color: #003366; font-size: 52px; font-weight: 900; margin-bottom: 5px; letter-spacing: 2px;'>
                    SIMPOL
                </h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style='text-align: center; padding: 0 0 15px 0;'>
            <h3 style='color: #1a5276; font-size: 22px; font-weight: 600; margin: 0; 
                       background: linear-gradient(90deg, #003366, #1a6b8a);
                       -webkit-background-clip: text;
                       -webkit-text-fill-color: transparent;
                       letter-spacing: 1px;'>
                Sistema Inteligente de Monitoreo Permanente Online
            </h3>
            <div style='width: 60%; height: 3px; background: linear-gradient(90deg, #003366, #3498db); 
                        margin: 8px auto 0 auto; border-radius: 2px;'>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("---")


def _formulario_recuperacion(canvas_login, logo_b64, logo_mime):
    """Formulario para restablecer la contraseña"""
    bloquear_autocompletado()

    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            _encabezado_login(logo_b64, logo_mime)

            st.markdown(
                "<p style='color: #003366; font-weight: bold; font-size: 16px;'>Restablecer Contraseña</p>",
                unsafe_allow_html=True,
            )

            with st.form("recuperacion_form", clear_on_submit=False):
                usuario = st.text_input("Usuario", key="rec_usuario")
                clave_actual = st.text_input("Contraseña actual", type="password", key="rec_clave_actual")
                clave_nueva = st.text_input("Nueva contraseña", type="password", key="rec_clave_nueva")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submit_cambio = st.form_submit_button("ACTUALIZAR", use_container_width=True)
                with col_btn2:
                    submit_volver = st.form_submit_button("VOLVER", use_container_width=True)

                if submit_volver:
                    st.session_state["modo_recuperacion"] = False
                    canvas_login.empty()
                    st.rerun()

                if submit_cambio:
                    if not usuario or not clave_actual or not clave_nueva:
                        st.warning("Debe completar todos los campos.")
                    else:
                        es_valida, msg_politica = validar_politica_clave(clave_nueva)
                        if not es_valida:
                            st.error(msg_politica)
                        else:
                            conn = conectar_bd()
                            if conn:
                                try:
                                    cursor = conn.cursor(dictionary=True)
                                    cursor.execute("SELECT id, usuario FROM usuarios WHERE usuario = %s", (usuario,))
                                    user = cursor.fetchone()

                                    if not user:
                                        st.error("El usuario no existe.")
                                    else:
                                        resultado = cambiar_clave(cursor, user['id'], clave_actual, clave_nueva, es_admin=False)

                                        if not resultado.get("exito"):
                                            st.error(resultado.get("mensaje", "No se pudo actualizar la contraseña."))
                                        else:
                                            conn.commit()
                                            st.success("Contraseña actualizada correctamente. Inicie sesión.")
                                            
                                            st.session_state["modo_recuperacion"] = False
                                            for _k in ["autenticado", "user_id", "user_actual", "cargo", "rol",
                                                       "seccion_actual", "_seccion_anterior", "modulo_actual", "token_sesion"]:
                                                st.session_state.pop(_k, None)
                                            
                                            st.query_params.clear()
                                            canvas_login.empty()
                                            st.rerun()

                                    cursor.close()
                                except Exception as e:
                                    st.error(f"Error en la base de datos: {e}")
                                finally:
                                    if conn.is_connected():
                                        conn.close()
                            else:
                                st.error("Error de conexión con la base de datos.")

            st.markdown('</div>', unsafe_allow_html=True)


def mostrar_login():
    logo_b64, logo_mime = get_logo_base64()
    bloquear_autocompletado()

    canvas_login = st.empty()

    if st.session_state.get("modo_recuperacion", False):
        _formulario_recuperacion(canvas_login, logo_b64, logo_mime)
        return

    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            _encabezado_login(logo_b64, logo_mime)

            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    "<p style='color: #003366; font-weight: bold; font-size: 16px;'>Acceso al Sistema</p>",
                    unsafe_allow_html=True,
                )
                usuario = st.text_input("Usuario", key="input_user_login")
                clave = st.text_input("Contraseña", type="password", key="input_pass_login")

                if st.form_submit_button("INGRESAR", use_container_width=True):
                    if not usuario or not clave:
                        st.warning("Debe ingresar usuario y contraseña.")
                    else:
                        conn = conectar_bd()
                        if conn:
                            try:
                                cursor = conn.cursor(dictionary=True)
                                resultado = procesar_login(cursor, usuario, clave, ip_cliente="127.0.0.1")
                                
                                if resultado.get("exito"):
                                    user_id = resultado["usuario_id"]
                                    
                                    token_sesion = secrets.token_hex(32)
                                    crear_sesion_activa(token_sesion, user_id, ip_cliente="127.0.0.1", user_agent="Streamlit App")
                                    
                                    import hashlib
                                    token_hash = hashlib.sha256(token_sesion.encode('utf-8')).hexdigest()
                                    cursor.execute("""
                                        INSERT INTO auditoria_sesiones (usuario_id, token_hash, evento, seccion, ip_cliente, user_agent, detalle)
                                        VALUES (%s, %s, 'LOGIN', 'Inicio', '127.0.0.1', 'Streamlit App', 'Inicio de sesión exitoso')
                                    """, (user_id, token_hash))
                                    
                                    conn.commit()
                                    cursor.close()

                                    st.session_state["autenticado"] = True
                                    st.session_state["user_id"] = user_id
                                    st.session_state["user_actual"] = usuario
                                    st.session_state["cargo"] = resultado.get("cargo", "Analista")
                                    st.session_state["rol"] = resultado["rol"].lower()
                                    st.session_state["token_sesion"] = token_sesion
                                    st.session_state["seccion_actual"] = "Inicio"

                                    st.query_params["p"] = "Inicio"
                                    st.query_params["token"] = token_sesion

                                    canvas_login.empty()
                                    st.rerun()
                                else:
                                    conn.commit()
                                    cursor.close()
                                    st.error(resultado.get("mensaje", "Credenciales incorrectas."))
                            except Exception as e:
                                st.error(f"Error en la autenticación: {e}")
                            finally:
                                if conn.is_connected():
                                    conn.close()
                        else:
                            st.error("Error de conexión con la base de datos.")

            col_link1, col_link2, col_link3 = st.columns([1, 2, 1])
            with col_link2:
                if st.button("¿Olvidaste tu contraseña?", use_container_width=True, key="btn_ir_recuperacion"):
                    st.session_state["modo_recuperacion"] = True
                    canvas_login.empty()
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style='text-align: center; color: #999; font-size: 12px; margin-top: 50px;'>
            2026 SIMPOL - Banco Caroní | Departamento de Infraestructura y Redes
        </div>
        """,
        unsafe_allow_html=True,
    )