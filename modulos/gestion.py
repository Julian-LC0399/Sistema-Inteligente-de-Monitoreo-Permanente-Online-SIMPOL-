import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def limpiar_filtros_y_cerrar():
    """Elimina las claves de los widgets para resetearlos y cierra el formulario"""
    if "sel_usuario_edit" in st.session_state:
        del st.session_state["sel_usuario_edit"]
    
    if "filtro_busqueda_csu" in st.session_state:
        del st.session_state["filtro_busqueda_csu"]
    
    st.session_state.mostrar_registro = False

def mostrar_pantalla(user_actual, user_id):
    # Verificación de permisos
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ESTILOS CSS (PROTEGIENDO EL SIDEBAR) ---
    st.markdown("""
        <style>
            /* Solo aplicar a la parte central, no al sidebar */
            [data-testid="stMain"] h2, [data-testid="stMain"] h4 {
                color: #003366 !important;
                font-weight: bold !important;
            }
            
            /* Encabezados de la tabla manual */
            .header-tabla {
                color: #003366 !important;
                font-weight: bold !important;
                border-bottom: 2px solid #003366;
                padding-bottom: 5px;
                font-size: 14px;
            }

            /* Texto de los datos en negro sólido SOLO EN LA TABLA */
            .dato-fila {
                color: #000000 !important;
                font-weight: 500 !important;
                font-size: 14px;
                margin-top: 8px;
            }

            /* Botones del área principal únicamente */
            [data-testid="stMain"] div.stButton > button {
                color: #ffffff !important;
                background-color: #003366 !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 5px !important;
            }
            
            [data-testid="stMain"] div.stButton > button:hover {
                color: #ffcc00 !important;
                background-color: #002244 !important;
                border: 1px solid #ffcc00 !important;
            }
            
            /* Evitar que el sidebar se ponga en negrita o cambie color */
            [data-testid="stSidebar"] * {
                font-weight: normal !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👥 Gestión de Personal CSU")

    # --- 1. FILTRO Y BOTÓN NUEVO ---
    col_f, col_b = st.columns([3, 1])
    with col_f:
        filtro = st.text_input("🔍 BUSCAR ANALISTA POR ID O NOMBRE:", key="filtro_busqueda_csu")
    
    with col_b:
        label_btn = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        if st.button(label_btn, use_container_width=True):
            st.session_state.mostrar_registro = not st.session_state.mostrar_registro
            st.rerun()

    # --- 2. FORMULARIO DE REGISTRO ---
    if st.session_state.mostrar_registro:
        with st.container(border=True):
            st.markdown("#### 📝 Registro de Nuevo Usuario")
            with st.form("form_alta_usuario", clear_on_submit=True):
                f1, f2 = st.columns(2)
                u_id = f1.text_input("ID Usuario (Login)")
                u_nom = f2.text_input("Nombre Completo")
                u_pass = f1.text_input("Contraseña Temporal", type="password")
                u_rol = f2.selectbox("Rol de Acceso", ["operador", "admin", "seguridad"])
                
                if st.form_submit_button("REGISTRAR ANALISTA", use_container_width=True):
                    if u_id and u_nom and u_pass:
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s,1)",
                                (u_id, u_pass, u_nom, u_rol)
                            )
                            conn.commit()
                            registrar_auditoria_usuario(u_id, "ALTA", "N/A", "ACTIVO", user_id, "Registro inicial")
                            conn.close()
                            st.success(f"Usuario {u_id} registrado.")
                            limpiar_filtros_y_cerrar()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.warning("Por favor rellene todos los campos.")

    # --- 3. TABLA DE DATOS ---
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()

        if usuarios:
            if filtro:
                usuarios = [u for u in usuarios if filtro.lower() in u['usuario'].lower() or filtro.lower() in u['nombre_completo'].lower()]

            st.write("")
            h1, h2, h3, h4, h5 = st.columns([1.5, 3, 1.5, 1.5, 1])
            h1.markdown("<div class='header-tabla'>USUARIO</div>", unsafe_allow_html=True)
            h2.markdown("<div class='header-tabla'>NOMBRE COMPLETO</div>", unsafe_allow_html=True)
            h3.markdown("<div class='header-tabla'>ROL</div>", unsafe_allow_html=True)
            h4.markdown("<div class='header-tabla'>ESTADO</div>", unsafe_allow_html=True)
            h5.markdown("<div class='header-tabla'>ACCION</div>", unsafe_allow_html=True)

            for u in usuarios:
                r1, r2, r3, r4, r5 = st.columns([1.5, 3, 1.5, 1.5, 1])
                r1.markdown(f"<div class='dato-fila'>{u['usuario']}</div>", unsafe_allow_html=True)
                r2.markdown(f"<div class='dato-fila'>{u['nombre_completo'].upper()}</div>", unsafe_allow_html=True)
                r3.markdown(f"<div class='dato-fila'>{str(u['rol']).upper()}</div>", unsafe_allow_html=True)
                
                est_label = "🟢 ACTIVO" if u['estado'] == 1 else "🔴 SUSPENDIDO"
                r4.markdown(f"<div class='dato-fila'>{est_label}</div>", unsafe_allow_html=True)
                
                if r5.button("📝", key=f"edit_{u['usuario']}", use_container_width=True):
                    st.session_state["sel_usuario_edit"] = u['usuario']
                    st.rerun()
                st.markdown("<hr style='margin:0; border:0.5px solid #eee;'>", unsafe_allow_html=True)

            # --- 4. FORMULARIO DE EDICIÓN ---
            usuario_a_editar = st.session_state.get("sel_usuario_edit")
            if usuario_a_editar:
                st.divider()
                datos_u = next(u for u in usuarios if u['usuario'] == usuario_a_editar)
                st.markdown(f"#### ⚙️ Modificar Analista: {usuario_a_editar}")
                
                with st.container(border=True):
                    with st.form("form_edit_analista"):
                        n_nombre = st.text_input("Nombre / Cargo Actualizado", value=datos_u['nombre_completo'])
                        justificacion = st.text_input("Justificación del Cambio (Auditoría)")
                        
                        b_col1, b_col2 = st.columns(2)
                        
                        if b_col1.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                            if justificacion.strip():
                                ejecutar_update_nombre(datos_u['usuario'], datos_u['nombre_completo'], n_nombre, user_id, justificacion)
                            else: st.error("Debe ingresar una justificación.")
                        
                        label_estado = "🔒 SUSPENDER ACCESO" if datos_u['estado'] == 1 else "🔓 ACTIVAR ACCESO"
                        if b_col2.form_submit_button(label_estado, use_container_width=True):
                            if justificacion.strip():
                                ejecutar_update_estado(datos_u['usuario'], datos_u['estado'], user_id, user_actual, justificacion)
                            else: st.error("Debe ingresar una justificación.")
        else:
            st.info("No se encontraron registros.")
            
    except Exception as e:
        st.error(f"Error: {e}")

def ejecutar_update_nombre(u_login, viejo, nuevo, ejecutor_id, comentario):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, u_login))
        conn.commit()
        registrar_auditoria_usuario(u_login, "CAMBIO NOMBRE", viejo, nuevo, ejecutor_id, comentario)
        conn.close()
        limpiar_filtros_y_cerrar()
        st.rerun()
    except Exception as e: st.error(f"Error SQL: {e}")

def ejecutar_update_estado(u_login, estado_act, ejecutor_id, ejecutor_login, comentario):
    if str(u_login) == str(ejecutor_login):
        st.error("No puede suspender su propia cuenta.")
        return
    nuevo_est = 0 if estado_act == 1 else 1
    v_ant = "ACTIVO" if estado_act == 1 else "SUSPENDIDO"
    v_nue = "SUSPENDIDO" if nuevo_est == 0 else "ACTIVO"
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_est, u_login))
        conn.commit()
        registrar_auditoria_usuario(u_login, "CAMBIO ESTADO", v_ant, v_nue, ejecutor_id, comentario)
        conn.close()
        limpiar_filtros_y_cerrar()
        st.rerun()
    except Exception as e: st.error(f"Error SQL: {e}")