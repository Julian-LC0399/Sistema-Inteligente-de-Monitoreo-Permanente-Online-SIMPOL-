import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def limpiar_y_actualizar():
    """Limpia el estado y refresca la aplicación"""
    if "filtro_usuario" in st.session_state:
        st.session_state["filtro_usuario"] = ""
    st.session_state.mostrar_registro = False
    st.session_state.usuario_a_editar = None
    st.rerun()

def mostrar_pantalla(user_actual, user_id):
    # --- 1. ESTADOS ---
    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False
    if "usuario_a_editar" not in st.session_state:
        st.session_state.usuario_a_editar = None

    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    # --- 2. CSS DE ALTA PRECISIÓN (SOLUCIONA TEXTO CORTADO) ---
    st.markdown("""
        <style>
            /* Encabezados de Tabla Forzados */
            .header-tabla {
                color: #003366 !important;
                font-weight: bold !important;
                border-bottom: 2px solid #003366 !important;
                padding-bottom: 5px;
                font-size: 14px;
            }
            
            .fila-texto {
                color: #000000 !important;
                font-weight: 500;
                padding-top: 10px;
            }

            /* Estilo Global de Botones para que NO se corten */
            div.stButton > button {
                background-color: #003366 !important;
                color: white !important;
                font-weight: bold !important;
                border-radius: 4px !important;
                border: 1px solid #003366 !important;
                padding: 10px 20px !important;
                width: auto !important; /* El botón crece según el texto */
                min-width: 130px !important; /* Pero tiene un mínimo para verse cuadrado */
                height: 42px !important;
                display: inline-flex !important;
                align-items: center;
                justify-content: center;
            }
            
            div.stButton > button:hover {
                border-color: #ffcc00 !important;
                color: #ffcc00 !important;
            }

            /* Botones de la tabla más compactos */
            [data-testid="column"] div.stButton > button {
                min-width: 100px !important;
                height: 32px !important;
                font-size: 12px !important;
                padding: 5px 10px !important;
            }

            /* Quitar el fondo gris de los formularios */
            [data-testid="stForm"] {
                background-color: white !important;
                border: 1px solid #003366 !important;
                padding: 30px !important;
                border-radius: 10px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: #003366;'>👥 Gestión de Seguridad y Analistas</h2>", unsafe_allow_html=True)

    # --- 3. BOTÓN REGISTRAR SUPERIOR ---
    if st.button("➕ REGISTRAR NUEVO ANALISTA", use_container_width=False):
        st.session_state.usuario_a_editar = None
        st.session_state.mostrar_registro = True
        st.rerun()

    # --- 4. TABLA DE USUARIOS ---
    st.write("")
    h1, h2, h3, h4 = st.columns([1.5, 3.5, 1.5, 1])
    h1.markdown("<div class='header-tabla'>USUARIO</div>", unsafe_allow_html=True)
    h2.markdown("<div class='header-tabla'>NOMBRE COMPLETO</div>", unsafe_allow_html=True)
    h3.markdown("<div class='header-tabla'>ESTADO</div>", unsafe_allow_html=True)
    h4.markdown("<div class='header-tabla'></div>", unsafe_allow_html=True)

    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario, nombre_completo, estado FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()

        for u in usuarios:
            c1, c2, c3, c4 = st.columns([1.5, 3.5, 1.5, 1])
            with c1: st.markdown(f"<p class='fila-texto'>{u['usuario']}</p>", unsafe_allow_html=True)
            with c2: st.markdown(f"<p class='fila-texto'>{u['nombre_completo']}</p>", unsafe_allow_html=True)
            with c3: 
                label = "✅ ACTIVO" if u['estado'] == 1 else "🚫 SUSPENDIDO"
                st.markdown(f"<p class='fila-texto'>{label}</p>", unsafe_allow_html=True)
            with c4:
                if st.button("EDITAR", key=f"btn_{u['id']}", use_container_width=True):
                    st.session_state.usuario_a_editar = u
                    st.session_state.mostrar_registro = True
                    st.rerun()
            st.markdown("<hr style='margin:0; border:0.5px solid #eee;'>", unsafe_allow_html=True)

        # --- 5. FORMULARIOS OPTIMIZADOS ---
        if st.session_state.mostrar_registro:
            u_edit = st.session_state.usuario_a_editar
            st.write("")

            if u_edit is None:
                # --- ALTA ---
                st.markdown("### 🆕 Alta de Nuevo Analista")
                with st.form("form_alta"):
                    f1, f2, f3 = st.columns(3)
                    n_nom = f1.text_input("Nombre y Apellido")
                    n_usr = f2.text_input("ID Usuario (Login)")
                    n_pwd = f3.text_input("Contraseña Provisional", type="password")
                    
                    st.write("")
                    # Usamos columnas anchas para los botones para que no se corten
                    b_col1, b_col2, _ = st.columns([1.5, 1.5, 4])
                    if b_col1.form_submit_button("✅ CREAR"):
                        if n_nom and n_usr and n_pwd:
                            # Lógica INSERT aquí
                            limpiar_y_actualizar()
                        else: st.error("Faltan datos.")
                    if b_col2.form_submit_button("❌ CANCELAR"):
                        limpiar_y_actualizar()

            else:
                # --- EDICIÓN ---
                st.markdown(f"### 📝 Modificar Analista: {u_edit['usuario']}")
                with st.form("form_edit"):
                    e1, e2 = st.columns(2)
                    e_nom = e1.text_input("Nombre Completo", value=u_edit['nombre_completo'])
                    e_usr = e2.text_input("Usuario (No editable)", value=u_edit['usuario'], disabled=True)
                    
                    e_mot = st.text_input("Justificación del Cambio")
                    
                    st.write("")
                    # Tres botones con espacio suficiente
                    bt1, bt2, bt3, _ = st.columns([1.5, 1.8, 1.5, 3])
                    
                    if bt1.form_submit_button("💾 GUARDAR"):
                        if not e_mot: st.error("Indique el motivo.")
                        else:
                            ejecutar_update_nombre(u_edit['usuario'], u_edit['nombre_completo'], e_nom, user_id, e_mot)
                            limpiar_y_actualizar()

                    label_st = "DESACTIVAR" if u_edit['estado'] == 1 else "ACTIVAR"
                    if bt2.form_submit_button(f"🔒 {label_st}"):
                        if not e_mot: st.error("Indique el motivo.")
                        else:
                            ejecutar_update_estado(u_edit['usuario'], u_edit['estado'], user_id, user_actual, e_mot)
                            limpiar_y_actualizar()

                    if bt3.form_submit_button("❌ SALIR"):
                        limpiar_y_actualizar()

    except Exception as e:
        st.error(f"Error: {e}")

# Funciones de persistencia SQL...
def ejecutar_update_nombre(usuario, viejo, nuevo, ejecutor_id, comentario):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, usuario))
        conn.commit()
        registrar_auditoria_usuario(usuario, "CAMBIO DE NOMBRE", viejo, nuevo, ejecutor_id, comentario)
        conn.close()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(usuario, estado_actual, ejecutor_id, ejecutor_login, comentario):
    if str(usuario) == str(ejecutor_login):
        st.error("No puedes suspender tu propio usuario.")
        return
    nuevo_st = 0 if estado_actual == 1 else 1
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_st, usuario))
        conn.commit()
        registrar_auditoria_usuario(usuario, "CAMBIO DE ESTADO", "ACTIVO" if estado_actual==1 else "SUSPENDIDO", "SUSPENDIDO" if nuevo_st==0 else "ACTIVO", ejecutor_id, comentario)
        conn.close()
    except Exception as e: st.error(f"Error: {e}")