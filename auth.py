import streamlit as st
from database import verificar_usuario, conectar_bd
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
                    if ext == '.ico':
                        mime = 'image/x-icon'
                    elif ext == '.jpg' or ext == '.jpeg':
                        mime = 'image/jpeg'
                    elif ext == '.png':
                        mime = 'image/png'
                    else:
                        mime = 'image/jpeg'
                    return base64.b64encode(img_data).decode(), mime
            except Exception as e:
                continue
    
    return None, None

def registrar_acceso_auditoria(usuario, cargo, rol):
    """
    Inserta un registro en la tabla log_accesos con manejo de errores silencioso para entornos .exe
    """
    conn = None
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO log_accesos (usuario, cargo, rol, ip_cliente, resultado) 
                VALUES (%s, %s, %s, '127.0.0.1', 'EXITOSO')
            """
            cursor.execute(query, (usuario, cargo, rol))
            conn.commit()
            cursor.close()
    except Exception as e:
        print(f"Error en auditoría de acceso: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

def mostrar_login():
    # Obtener logo en base64
    logo_b64, logo_mime = get_logo_base64()
    
    # === ANCLA DE LIMPIEZA DE LOGIN ===
    canvas_login = st.empty()

    with canvas_login.container():
        _, col2, _ = st.columns([1, 2, 1])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # =============================================================
            # TÍTULO PRINCIPAL CON LOGO (FAVICON)
            # =============================================================
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
                # Fallback: solo texto con emoji
                st.markdown(
                    """
                    <div style='text-align: center; padding: 10px 0 5px 0;'>
                        <h1 style='color: #003366; font-size: 52px; font-weight: 900; margin-bottom: 5px; letter-spacing: 2px;'>
                            🏦 SIMPOL
                        </h1>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            
            # SUBTÍTULO - Más grande, visible y con estilo corporativo
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

            # Mantenemos el formulario seguro con Key única para el subproceso .exe
            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    "<p style='color: #003366; font-weight: bold; font-size: 16px;'>🔐 Acceso al Sistema</p>",
                    unsafe_allow_html=True,
                )
                usuario = st.text_input("Usuario", key="input_user_login")
                clave = st.text_input("Contraseña", type="password", key="input_pass_login")

                if st.form_submit_button("INGRESAR", use_container_width=True):
                    user_data = verificar_usuario(usuario, clave)
                    
                    if user_data:
                        # 1. Limpiar parámetros residuales del logout
                        st.query_params.clear()
                        
                        # 2. PERSISTENCIA DE SESIÓN ATÓMICA (Uso de 'cargo')
                        st.session_state["autenticado"] = True
                        st.session_state["user_id"] = user_data["id"]
                        st.session_state["user_actual"] = user_data["usuario"]
                        st.session_state["cargo"] = user_data["cargo"]  # Corregido
                        st.session_state["rol"] = user_data["rol"].lower()
                        
                        # 3. AUDITORÍA SÍNCRONA DE ACCESO
                        registrar_acceso_auditoria(
                            user_data["usuario"], 
                            user_data["cargo"], 
                            user_data["rol"]
                        )
                        
                        # 4. ASIGNACIÓN LIMPIA DE NUEVOS PARÁMETROS EN LA URL
                        st.query_params.update({
                            "s": "1",
                            "p": "🏠 Inicio",
                            "r": user_data["rol"].lower(),
                            "uid": str(user_data["id"]),
                            "u": user_data["usuario"],
                            "c": user_data["cargo"]  # Pasamos 'c' de cargo en la URL si hace falta
                        })
                        
                        # 5. DESMONTAJE VISUAL Y REFRESCO INMEDIATO
                        canvas_login.empty()
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Contacte al Oficial de Seguridad.")
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer institucional
    st.markdown(
        """
        <div style='text-align: center; color: #999; font-size: 12px; margin-top: 50px;'>
            © 2026 SIMPOL - Banco Caroní | Departamento de Infraestructura y Redes
        </div>
        """, 
        unsafe_allow_html=True
    )