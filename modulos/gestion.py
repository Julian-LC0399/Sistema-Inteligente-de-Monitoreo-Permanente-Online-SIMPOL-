import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def limpiar_filtros_y_cerrar():
    if "sel_usuario_edit" in st.session_state:
        del st.session_state["sel_usuario_edit"]
    st.session_state.filtro_ejecutado = ""
    st.session_state.mostrar_registro = False

def mostrar_pantalla(user_actual, user_id):
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    # --- CSS PROFESIONAL DE ALTA PRECISIÓN ---
    st.markdown("""
        <style>
            .titulo-gestion {
                color: #003366 !important;
                font-size: 28px !important;
                font-weight: bold !important;
                margin-bottom: 20px !important;
                display: block !important;
            }
            
            /* Eliminación de gaps y bordes residuales en columnas */
            [data-testid="stHorizontalBlock"] { 
                gap: 0px !important; 
                align-items: center !important; 
            }
            [data-testid="column"] { background-color: transparent !important; }

            /* Contenedor principal de la tabla */
            .main-table-container {
                border: 1px solid #003366;
                border-top: none !important; 
                border-radius: 0px 0px 4px 4px;
                overflow: hidden;
                background-color: white;
                margin-top: 15px; /* Espacio para evitar solapamiento con buscador */
            }

            /* Encabezados con centrado vertical corregido */
            .header-banco {
                background-color: #003366 !important;
                color: white !important;
                text-align: center;
                padding: 14px 5px 12px 5px; 
                font-weight: bold;
                font-size: 13px;
                border-right: 1px solid rgba(255,255,255,0.1);
            }

            /* Filas de datos */
            .fila-datos {
                background-color: white !important;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                width: 100%;
            }
            .fila-datos:hover { background-color: #f1f5f9 !important; }

            .celda-banco {
                color: #333 !important;
                font-size: 13px;
                padding: 10px 5px;
                text-align: center;
                border-right: 1px solid #eee;
                display: flex; align-items: center; justify-content: center;
                min-height: 50px;
            }

            /* Estilos de botones de acción agrupados */
            .btn-edit button { 
                background-color: #003366 !important; 
                color: white !important; 
                border-radius: 4px 0px 0px 4px !important; 
                font-size: 11px !important; 
                height: 30px !important; 
                border: none !important; 
            }
            .btn-status button { 
                background-color: #d32f2f !important; 
                color: white !important; 
                border-radius: 0px 4px 4px 0px !important; 
                font-size: 11px !important; 
                height: 30px !important; 
                border: none !important; 
            }
            .btn-status-active button { 
                background-color: #455a64 !important; 
                color: white !important; 
                border-radius: 0px 4px 4px 0px !important; 
                font-size: 11px !important; 
                height: 30px !important; 
                border: none !important; 
            }

            /* Botones generales de Streamlit */
            .stButton > button {
                background-color: #003366 !important;
                color: white !important;
                border-radius: 4px !important;
                font-weight: bold !important;
            }
            
            .text-form-label {
                color: #003366 !important;
                font-weight: bold !important;
                font-size: 18px !important;
                margin-top: 10px !important;
                margin-bottom: 10px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="titulo-gestion">👥 Gestión de Personal CSU</p>', unsafe_allow_html=True)

    # --- LÓGICA DE BÚSQUEDA ---
    if "filtro_ejecutado" not in st.session_state:
        st.session_state.filtro_ejecutado = ""

    if st.session_state.filtro_ejecutado:
        c_busq, c_fill, c_clear = st.columns([2.6, 0.7, 0.7])
    else:
        c_busq, c_fill = st.columns([3.3, 0.7])
        c_clear = None

    with c_busq:
        busqueda_input = st.text_input("Buscar...", value=st.session_state.filtro_ejecutado, key="input_busq_widget", label_visibility="collapsed", placeholder="Buscar por usuario o nombre...")
    
    with c_fill:
        if st.button("FILTRAR", use_container_width=True):
            st.session_state.filtro_ejecutado = busqueda_input
            st.rerun()
            
    if c_clear:
        with c_clear:
            if st.button("🧹 LIMPIAR", use_container_width=True):
                st.session_state.filtro_ejecutado = ""
                st.rerun()

    # --- RENDERIZADO DE TABLA ---
    try:
        conn = conectar_bd(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
        usuarios = cursor.fetchall(); conn.close()

        if usuarios:
            usuarios_f = [u for u in usuarios if st.session_state.filtro_ejecutado.lower() in u['usuario'].lower() or st.session_state.filtro_ejecutado.lower() in u['nombre_completo'].lower()]

            st.markdown('<div class="main-table-container">', unsafe_allow_html=True)
            # Fila de Encabezados
            h = st.columns([1.5, 3, 1, 1.2, 1.8])
            h[0].markdown("<div class='header-banco'>USUARIO</div>", unsafe_allow_html=True)
            h[1].markdown("<div class='header-banco'>NOMBRE COMPLETO</div>", unsafe_allow_html=True)
            h[2].markdown("<div class='header-banco'>ROL</div>", unsafe_allow_html=True)
            h[3].markdown("<div class='header-banco'>ESTADO</div>", unsafe_allow_html=True)
            h[4].markdown("<div class='header-banco' style='border-right:none;'>ACCIONES</div>", unsafe_allow_html=True)

            for u in usuarios_f:
                st.markdown('<div class="fila-datos">', unsafe_allow_html=True)
                r = st.columns([1.5, 3, 1, 1.2, 1.8])
                r[0].markdown(f"<div class='celda-banco'>{u['usuario']}</div>", unsafe_allow_html=True)
                r[1].markdown(f"<div class='celda-banco'>{u['nombre_completo'].upper()}</div>", unsafe_allow_html=True)
                r[2].markdown(f"<div class='celda-banco'>{str(u['rol']).upper()}</div>", unsafe_allow_html=True)
                r[3].markdown(f"<div class='celda-banco'>{'🟢 ACTIVO' if u['estado'] == 1 else '🔴 SUSPENDIDO'}</div>", unsafe_allow_html=True)
                
                # Columna de Acciones con botones pegados
                c_edit, c_stat = r[4].columns(2)
                with c_edit:
                    st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                    if st.button("EDITAR", key=f"e_{u['usuario']}", use_container_width=True):
                        st.session_state["sel_usuario_edit"] = u['usuario']
                        st.session_state.mostrar_registro = False 
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c_stat:
                    clase_css = "btn-status" if u['estado'] == 1 else "btn-status-active"
                    label_btn = "SUSPENDER" if u['estado'] == 1 else "ACTIVAR"
                    st.markdown(f'<div class="{clase_css}">', unsafe_allow_html=True)
                    if st.button(label_btn, key=f"s_{u['usuario']}", use_container_width=True):
                        ejecutar_update_estado(u['usuario'], u['estado'], user_id, user_actual, "Cambio rápido de estado")
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # --- BOTÓN REGISTRO ---
            st.write("")
            if not st.session_state.get("mostrar_registro") and not st.session_state.get("sel_usuario_edit"):
                if st.button("➕ REGISTRAR NUEVO ANALISTA", use_container_width=True):
                    st.session_state.mostrar_registro = True
                    st.rerun()

            # --- FORMULARIO DE REGISTRO ---
            if st.session_state.get("mostrar_registro"):
                with st.container(border=True):
                    st.markdown('<p class="text-form-label">📝 Registro de Nuevo Analista</p>', unsafe_allow_html=True)
                    with st.form("nuevo_u"):
                        f1, f2 = st.columns(2)
                        r_id = f1.text_input("Usuario (Login)")
                        r_nom = f2.text_input("Nombre Completo")
                        r_pw = f1.text_input("Clave Temporal", type="password")
                        r_rl = f2.selectbox("Rol", ["operador", "admin", "seguridad"])
                        if st.form_submit_button("GUARDAR ANALISTA", use_container_width=True):
                            if r_id and r_nom and r_pw:
                                try:
                                    conn = conectar_bd(); cursor = conn.cursor()
                                    cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s,1)", (r_id, r_pw, r_nom, r_rl))
                                    conn.commit()
                                    registrar_auditoria_usuario(r_id, "ALTA", "N/A", "ACTIVO", user_id, f"Alta por {user_actual}")
                                    conn.close(); st.success("Analista registrado correctamente."); limpiar_filtros_y_cerrar(); st.rerun()
                                except Exception as e: st.error(f"Error al registrar: {e}")
                            else: st.warning("Por favor complete todos los campos.")
                    if st.button("❌ CANCELAR REGISTRO", use_container_width=True):
                        st.session_state.mostrar_registro = False
                        st.rerun()

            # --- FORMULARIO DE EDICIÓN ---
            if st.session_state.get("sel_usuario_edit"):
                u_sel = st.session_state.sel_usuario_edit
                datos = next(u for u in usuarios if u['usuario'] == u_sel)
                st.markdown(f"<p class='text-form-label'>⚙️ Modificar Analista: {u_sel}</p>", unsafe_allow_html=True)
                with st.container(border=True):
                    with st.form("form_edicion"):
                        n_nombre = st.text_input("Nombre / Cargo", value=datos['nombre_completo'])
                        justif = st.text_input("Justificación de Auditoría", placeholder="Motivo del cambio...")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                                if justif.strip():
                                    ejecutar_update_nombre(u_sel, datos['nombre_completo'], n_nombre, user_id, justif)
                                else: st.error("Debe ingresar una justificación.")
                        with c2:
                            if st.form_submit_button("❌ CERRAR EDICIÓN", use_container_width=True):
                                st.session_state.sel_usuario_edit = None
                                st.rerun()

    except Exception as e: st.error(f"Error: {e}")

# --- FUNCIONES DE BASE DE DATOS ---

def ejecutar_update_nombre(login, viejo, nuevo, id_ejecutor, comentario):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, login))
        conn.commit()
        registrar_auditoria_usuario(login, "CAMBIO NOMBRE", viejo, nuevo, id_ejecutor, comentario)
        conn.close(); st.session_state.sel_usuario_edit = None; st.rerun()
    except Exception as e: st.error(f"Error al actualizar nombre: {e}")

def ejecutar_update_estado(login, est_ant, id_ejecutor, login_ejecutor, comentario):
    if str(login) == str(login_ejecutor): 
        st.error("No puede suspender su propia cuenta."); return
    
    n_est = 0 if est_ant == 1 else 1
    v_ant, v_nue = ("ACTIVO", "SUSPENDIDO") if est_ant == 1 else ("SUSPENDIDO", "ACTIVO")
    
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (n_est, login))
        conn.commit()
        registrar_auditoria_usuario(login, "CAMBIO ESTADO", v_ant, v_nue, id_ejecutor, comentario)
        conn.close(); st.rerun()
    except Exception as e: st.error(f"Error al cambiar estado: {e}")