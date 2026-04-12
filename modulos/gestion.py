import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def limpiar_filtros_y_cerrar():
    if "sel_usuario_edit" in st.session_state:
        del st.session_state["sel_usuario_edit"]
    st.session_state.mostrar_registro = False

def mostrar_pantalla(user_actual, user_id):
    # 1. VERIFICACIÓN DE PERMISOS
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    # 2. CSS AVANZADO: REPARACIÓN DE TEXTO EN BLANCO Y UNIFICACIÓN
    st.markdown("""
        <style>
            /* Forzar visibilidad de títulos (Evita que se vean en blanco) */
            .titulo-gestion {
                color: #003366 !important;
                font-size: 28px !important;
                font-weight: bold !important;
                margin-bottom: 20px !important;
                display: block !important;
            }

            /* Eliminar espacios entre columnas */
            [data-testid="stHorizontalBlock"] {
                gap: 0px !important;
                align-items: center !important;
            }
            
            /* Quitar fondos blancos de contenedores internos de Streamlit */
            [data-testid="column"] {
                background-color: transparent !important;
            }

            /* Marco de la Tabla Única */
            .main-table-container {
                border: 1px solid #003366;
                border-radius: 4px;
                overflow: hidden;
                background-color: white;
            }

            /* Cabecera Azul */
            .header-banco {
                background-color: #003366 !important;
                color: white !important;
                text-align: center;
                padding: 12px 5px;
                font-weight: bold;
                font-size: 13px;
                border-right: 1px solid rgba(255,255,255,0.1);
            }

            /* Fila de Datos Unificada (Sin cuadros blancos sueltos) */
            .fila-datos {
                background-color: white !important;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                width: 100%;
            }
            
            .fila-datos:hover {
                background-color: #f1f5f9 !important;
            }

            .celda-banco {
                color: #333 !important;
                font-size: 13px;
                padding: 10px 5px;
                text-align: center;
                border-right: 1px solid #eee;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 50px;
            }

            /* Botones estilo Caroní */
            .stButton > button {
                background-color: #003366 !important;
                color: white !important;
                border-radius: 4px !important;
                border: none !important;
                font-weight: bold !important;
                transition: 0.3s !important;
            }
            
            .stButton > button:hover {
                background-color: #FFCC00 !important;
                color: #003366 !important;
            }

            /* Contenedor de botón editar para que no genere cuadros blancos */
            .btn-table-wrapper {
                background-color: transparent !important;
                padding: 5px !important;
                width: 100%;
            }
        </style>
    """, unsafe_allow_html=True)

    # Título con clase específica para asegurar color
    st.markdown('<p class="titulo-gestion">👥 Gestión de Personal CSU</p>', unsafe_allow_html=True)

    # --- ACCIONES ---
    col_busq, col_btn = st.columns([3, 1])
    with col_busq:
        filtro = st.text_input("🔍 Buscar analista...", key="filtro_csu")
    with col_btn:
        label = "❌ CANCELAR" if st.session_state.get("mostrar_registro") else "➕ NUEVO ANALISTA"
        if st.button(label, use_container_width=True):
            st.session_state.mostrar_registro = not st.session_state.get("mostrar_registro", False)
            st.rerun()

    # Formulario Registro
    if st.session_state.get("mostrar_registro"):
        with st.container(border=True):
            st.markdown("<h4 style='color:#003366;'>📝 Registrar Analista</h4>", unsafe_allow_html=True)
            with st.form("nuevo_u"):
                f1, f2 = st.columns(2)
                r_id = f1.text_input("Usuario")
                r_nom = f2.text_input("Nombre")
                r_pw = f1.text_input("Clave", type="password")
                r_rl = f2.selectbox("Rol", ["operador", "admin", "seguridad"])
                if st.form_submit_button("REGISTRAR"):
                    if r_id and r_nom:
                        # Lógica de guardado...
                        st.success("Registrado")
                        limpiar_filtros_y_cerrar()
                        st.rerun()

    # --- TABLA PROFESIONAL ---
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()

        if usuarios:
            if filtro:
                usuarios = [u for u in usuarios if filtro.lower() in u['usuario'].lower() or filtro.lower() in u['nombre_completo'].lower()]

            st.markdown('<div class="main-table-container">', unsafe_allow_html=True)
            
            # Cabecera
            h = st.columns([1.5, 3, 1.2, 1.3, 1])
            h[0].markdown("<div class='header-banco'>USUARIO</div>", unsafe_allow_html=True)
            h[1].markdown("<div class='header-banco'>NOMBRE COMPLETO</div>", unsafe_allow_html=True)
            h[2].markdown("<div class='header-banco'>ROL</div>", unsafe_allow_html=True)
            h[3].markdown("<div class='header-banco'>ESTADO</div>", unsafe_allow_html=True)
            h[4].markdown("<div class='header-banco' style='border-right:none;'>ACCIÓN</div>", unsafe_allow_html=True)

            for u in usuarios:
                # Cada fila se envuelve en un div para mantener el fondo blanco unificado
                st.markdown('<div class="fila-datos">', unsafe_allow_html=True)
                r = st.columns([1.5, 3, 1.2, 1.3, 1])
                r[0].markdown(f"<div class='celda-banco'>{u['usuario']}</div>", unsafe_allow_html=True)
                r[1].markdown(f"<div class='celda-banco'>{u['nombre_completo'].upper()}</div>", unsafe_allow_html=True)
                r[2].markdown(f"<div class='celda-banco'>{str(u['rol']).upper()}</div>", unsafe_allow_html=True)
                
                est = "🟢 ACTIVO" if u['estado'] == 1 else "🔴 SUSPENDIDO"
                r[3].markdown(f"<div class='celda-banco'>{est}</div>", unsafe_allow_html=True)
                
                with r[4]:
                    st.markdown('<div class="btn-table-wrapper">', unsafe_allow_html=True)
                    if st.button("EDITAR", key=f"e_{u['usuario']}", use_container_width=True):
                        st.session_state["sel_usuario_edit"] = u['usuario']
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

            # Sección de edición (aparece abajo si se selecciona)
            if st.session_state.get("sel_usuario_edit"):
                st.divider()
                st.info(f"Editando a: {st.session_state.sel_usuario_edit}")
                # Formulario de edición aquí...

    except Exception as e:
        st.error(f"Error: {e}")