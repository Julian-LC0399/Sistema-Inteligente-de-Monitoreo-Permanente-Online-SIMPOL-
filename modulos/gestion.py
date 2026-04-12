import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def limpiar_filtros_y_cerrar():
    """Limpia el estado de la sesión para resetear la interfaz"""
    if "sel_usuario_edit" in st.session_state:
        del st.session_state["sel_usuario_edit"]
    if "filtro_busqueda_csu" in st.session_state:
        del st.session_state["filtro_busqueda_csu"]
    st.session_state.mostrar_registro = False

def mostrar_pantalla(user_actual, user_id):
    # 1. VERIFICACIÓN DE PERMISOS
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # 2. ESTILOS CSS AVANZADOS (ELIMINACIÓN DE ESPACIOS Y UNIFICACIÓN)
    st.markdown("""
        <style>
            /* Eliminar el espacio (gap) entre columnas de Streamlit en la tabla */
            [data-testid="stHorizontalBlock"] {
                gap: 0px !important;
            }

            .gestion-container h2, .gestion-container h4 {
                color: #003366 !important;
                font-weight: bold !important;
            }

            /* Marco de la Tabla */
            .tabla-banco-marco {
                border: 2px solid #003366;
                border-radius: 8px;
                overflow: hidden;
                background-color: white;
            }

            /* Cabecera Azul */
            .cabecera-azul {
                background-color: #003366 !important;
                color: white !important;
                font-weight: bold !important;
                text-align: center;
                padding: 15px 5px;
                font-size: 14px;
                border-right: 1px solid rgba(255,255,255,0.3);
            }

            /* Celdas de Datos */
            .celda-datos {
                color: #333 !important;
                font-weight: 500 !important;
                font-size: 13px;
                padding: 10px 5px;
                text-align: center;
                border-right: 1px solid #ddd;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 55px;
                background-color: transparent !important; /* Forzamos transparencia */
            }

            .celda-fin { border-right: none !important; }

            /* Fila Unificada */
            .fila-contenedor {
                border-bottom: 1px solid #ddd;
                background-color: white !important;
                display: flex;
                width: 100%;
            }
            
            .fila-contenedor:hover {
                background-color: #f1f5f9 !important;
            }

            /* Quitar el recuadro blanco que Streamlit pone a los widgets en columnas */
            [data-testid="stVerticalBlock"] > div:has(div.btn-tabla-editar) {
                background-color: transparent !important;
            }

            /* Botones Institucionales */
            .gestion-container div.stButton > button {
                color: #ffffff !important;
                background-color: #003366 !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 4px !important;
            }
            
            .gestion-container div.stButton > button:hover {
                color: #003366 !important;
                background-color: #FFCC00 !important;
            }

            .btn-tabla-editar button {
                height: 30px !important;
                font-size: 11px !important;
                width: 90% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="gestion-container">', unsafe_allow_html=True)
    st.markdown("## 👥 Gestión de Personal CSU")

    # Acciones superiores
    col_busq, col_btn = st.columns([3, 1])
    with col_busq:
        filtro = st.text_input("🔍 FILTRAR ANALISTA:", key="filtro_busqueda_csu")
    with col_btn:
        lbl = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        if st.button(lbl, use_container_width=True):
            st.session_state.mostrar_registro = not st.session_state.mostrar_registro
            st.rerun()

    # Formulario Registro
    if st.session_state.mostrar_registro:
        with st.container(border=True):
            st.markdown("#### 📝 Registro de Nuevo Usuario")
            with st.form("form_nuevo_u", clear_on_submit=True):
                c1, c2 = st.columns(2)
                reg_id = c1.text_input("ID Usuario")
                reg_nom = c2.text_input("Nombre Completo")
                reg_pass = c1.text_input("Clave Temporal", type="password")
                reg_rol = c2.selectbox("Rol", ["operador", "admin", "seguridad"])
                if st.form_submit_button("GUARDAR ANALISTA", use_container_width=True):
                    if reg_id and reg_nom and reg_pass:
                        try:
                            conn = conectar_bd(); cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s,1)", (reg_id, reg_pass, reg_nom, reg_rol))
                            conn.commit()
                            registrar_auditoria_usuario(reg_id, "ALTA", "N/A", "ACTIVO", user_id, "Alta sistema")
                            conn.close(); st.success("Registrado."); limpiar_filtros_y_cerrar(); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

    # --- TABLA DE REGISTRO ---
    try:
        conn = conectar_bd(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
        usuarios = cursor.fetchall(); conn.close()

        if usuarios:
            if filtro:
                usuarios = [u for u in usuarios if filtro.lower() in u['usuario'].lower() or filtro.lower() in u['nombre_completo'].lower()]

            st.write("")
            st.markdown('<div class="tabla-banco-marco">', unsafe_allow_html=True)
            
            # Cabecera
            h = st.columns([1.5, 3, 1.2, 1.3, 1])
            h[0].markdown("<div class='cabecera-azul'>USUARIO</div>", unsafe_allow_html=True)
            h[1].markdown("<div class='cabecera-azul'>NOMBRE COMPLETO</div>", unsafe_allow_html=True)
            h[2].markdown("<div class='cabecera-azul'>ROL</div>", unsafe_allow_html=True)
            h[3].markdown("<div class='cabecera-azul'>ESTADO</div>", unsafe_allow_html=True)
            h[4].markdown("<div class='cabecera-azul celda-fin'>ACCIÓN</div>", unsafe_allow_html=True)

            # Filas
            for u in usuarios:
                st.markdown('<div class="fila-contenedor">', unsafe_allow_html=True)
                r = st.columns([1.5, 3, 1.2, 1.3, 1])
                r[0].markdown(f"<div class='celda-datos'>{u['usuario']}</div>", unsafe_allow_html=True)
                r[1].markdown(f"<div class='celda-datos'>{u['nombre_completo'].upper()}</div>", unsafe_allow_html=True)
                r[2].markdown(f"<div class='celda-datos'>{str(u['rol']).upper()}</div>", unsafe_allow_html=True)
                est_t = "🟢 ACTIVO" if u['estado'] == 1 else "🔴 SUSPENDIDO"
                r[3].markdown(f"<div class='celda-datos'>{est_t}</div>", unsafe_allow_html=True)
                
                with r[4]:
                    # Usamos una clase envolvente para detectar y quitar el fondo blanco de Streamlit
                    st.markdown('<div class="btn-tabla-editar">', unsafe_allow_html=True)
                    if st.button("EDITAR", key=f"btn_{u['usuario']}", use_container_width=True):
                        st.session_state["sel_usuario_edit"] = u['usuario']
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Edición
            if st.session_state.get("sel_usuario_edit"):
                st.divider()
                u_ed = st.session_state.sel_usuario_edit
                dt = next(u for u in usuarios if u['usuario'] == u_ed)
                st.markdown(f"#### ⚙️ Modificar: {u_ed}")
                with st.container(border=True):
                    with st.form("form_ed"):
                        n_n = st.text_input("Nombre", value=dt['nombre_completo'])
                        jt = st.text_input("Justificación")
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("💾 GUARDAR"):
                            if jt.strip(): ejecutar_update_nombre(dt['usuario'], dt['nombre_completo'], n_n, user_id, jt)
                            else: st.error("Falta justificación.")
                        if b2.form_submit_button("🔒 CAMBIAR ESTADO"):
                            if jt.strip(): ejecutar_update_estado(dt['usuario'], dt['estado'], user_id, user_actual, jt)
                            else: st.error("Falta justificación.")
    except Exception as e:
        st.error(f"Error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# Funciones SQL (Update nombre y estado como en el código anterior)...
def ejecutar_update_nombre(login, viejo, nuevo, ejecutor, comentario):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, login))
        conn.commit(); registrar_auditoria_usuario(login, "NOMBRE", viejo, nuevo, ejecutor, comentario)
        conn.close(); limpiar_filtros_y_cerrar(); st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(login, est, ejecutor_id, ejecutor_login, comentario):
    if str(login) == str(ejecutor_login):
        st.error("No puedes suspender tu cuenta."); return
    n_est = 0 if est == 1 else 1
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (n_est, login))
        conn.commit(); registrar_auditoria_usuario(login, "ESTADO", str(est), str(n_est), ejecutor_id, comentario)
        conn.close(); limpiar_filtros_y_cerrar(); st.rerun()
    except Exception as e: st.error(f"Error: {e}")