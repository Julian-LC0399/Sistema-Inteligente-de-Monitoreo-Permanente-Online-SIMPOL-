import streamlit as st
from database import autenticar_usuario, actualizar_clave_usuario
import os
import sys
import base64

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
                    mime = {'ico': 'image/x-icon', '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg', '.png': 'image/png'}.get(ext, 'image/jpeg')
                    if ext == '.ico':
                        mime = 'image/x-icon'
                    return base64.b64encode(img_data).decode(), mime
            except Exception:
                continue
    return None, None


def _encabezado_login(logo_b64, logo_mime):
    """Dibuja el encabezado corporativo del login"""
    if logo_b64:
        st.markdown(
            f"""
            <div style='text-align: center; padding: 10px 0 5px 0;'>
                <div style='display: flex; align-items: center; justify-content: center; gap: 15px;'>
                    <img src="data:{logo_mime};base64,{logo_b64}"
                         style='width: 60px; height: 60px; object-fit: contain;' alt="SIMPOL Logo">
                    <h1 style='color: #003366; font-size: 52px; font-weight: 900; margin: 0; letter-spacing: 2px;'>
                        SIMPOL
                    </h1>
                </div>
            </div>
            """, unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style='text-align: center; padding: 10px 0 5px 0;'>
                <h1 style='color: #003366; font-size: 52px; font-weight: 900; margin-bottom: 5px; letter-spacing: 2px;'>
                    🏦 SIMPOL
                </h1>
            </div>
            """, unsafe_allow_html=True,
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
        """, unsafe_allow_html=True,
    )
    st.write("---")


def _formulario_login(canvas_login, logo_b64, logo_mime):
    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            _encabezado_login(logo_b64, logo_mime)

            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    "<p style='color: #003366; font-weight: bold; font-size: 16px;'>🔐 Acceso al Sistema</p>",
                    unsafe_allow_html=True,
                )
                usuario = st.text_input("Usuario", key="input_user_login")
                clave = st.text_input("Contraseña", type="password", key="input_pass_login")

                if st.form_submit_button("INGRESAR", use_container_width=True):
                    if not usuario or not clave:
                        st.warning("Debe ingresar usuario y contraseña.")
                        return

                    # === LÓGICA DE SEGURIDAD ===
                    resultado = autenticar_usuario(usuario, clave, ip_cliente="127.0.0.1")

                    if not resultado.get("exito"):
                        st.error(resultado.get("mensaje", "Credenciales incorrectas."))
                        return

                    # Login exitoso
                    st.session_state["autenticado"] = True
                    st.session_state["user_id"] = resultado["usuario_id"]
                    st.session_state["user_actual"] = usuario
                    st.session_state["rol"] = resultado["rol"].lower()
                    st.session_state["cargo"] = resultado.get("cargo", "Analista")  # ✅ AGREGADO
                    st.session_state["debe_cambiar_clave"] = resultado.get("debe_cambiar_clave", False)

                    # Si debe cambiar clave -> mostrar pantalla de cambio obligatorio
                    if resultado.get("debe_cambiar_clave", False):
                        canvas_login.empty()
                        st.session_state["_forzar_cambio_clave"] = True
                        st.rerun()

                    # Flujo normal
                    canvas_login.empty()
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)


def _formulario_cambio_obligatorio(canvas_login, logo_b64, logo_mime):
    """Pantalla de cambio de contraseña obligatorio (primer login / reset admin)"""
    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            _encabezado_login(logo_b64, logo_mime)

            st.markdown(
                """
                <div style='background:#fff3cd; border-left:5px solid #ffc107; padding:12px 16px;
                            border-radius:6px; margin-bottom:15px;'>
                    <p style='color:#856404; margin:0; font-weight:600;'>
                        ⚠️ Debe cambiar su contraseña antes de continuar.
                    </p>
                    <p style='color:#856404; margin:6px 0 0 0; font-size:13px;'>
                        Política: mínimo 8 caracteres, 1 mayúscula, 1 número y 1 carácter especial.
                    </p>
                </div>
                """, unsafe_allow_html=True,
            )

            with st.form("cambio_clave_obligatorio"):
                clave_actual = st.text_input("Contraseña actual", type="password", key="cc_actual")
                clave_nueva = st.text_input("Nueva contraseña", type="password", key="cc_nueva")
                clave_conf = st.text_input("Confirmar nueva contraseña", type="password", key="cc_conf")

                if st.form_submit_button("CAMBIAR CONTRASEÑA", use_container_width=True):
                    if not clave_actual or not clave_nueva or not clave_conf:
                        st.warning("Complete todos los campos.")
                        return
                    if clave_nueva != clave_conf:
                        st.error("La nueva contraseña y su confirmación no coinciden.")
                        return

                    resultado = actualizar_clave_usuario(
                        usuario_id=st.session_state["user_id"],
                        clave_actual=clave_actual,
                        clave_nueva=clave_nueva,
                        es_admin=False,
                    )

                    if not resultado.get("exito"):
                        st.error(resultado.get("mensaje", "No se pudo cambiar la contraseña."))
                        return

                    st.success("✅ Contraseña actualizada correctamente.")
                    st.session_state["debe_cambiar_clave"] = False
                    st.session_state["_forzar_cambio_clave"] = False
                    canvas_login.empty()
                    st.rerun()

            # Botón para cancelar sesión si el usuario no recuerda su clave actual
            if st.button("Cancelar e iniciar sesión con otro usuario"):
                for k in ["autenticado", "user_id", "user_actual", "rol",
                          "cargo", "debe_cambiar_clave", "_forzar_cambio_clave"]:
                    st.session_state.pop(k, None)
                st.query_params.clear()
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)


def mostrar_login():
    logo_b64, logo_mime = get_logo_base64()
    canvas_login = st.empty()

    # Determinar si estamos en flujo de cambio obligatorio
    if st.session_state.get("_forzar_cambio_clave", False) and st.session_state.get("autenticado"):
        _formulario_cambio_obligatorio(canvas_login, logo_b64, logo_mime)
    else:
        _formulario_login(canvas_login, logo_b64, logo_mime)

    st.markdown(
        """
        <div style='text-align: center; color: #999; font-size: 12px; margin-top: 50px;'>
            © 2026 SIMPOL - Banco Caroní | Departamento de Infraestructura y Redes
        </div>
        """,
        unsafe_allow_html=True,
    )