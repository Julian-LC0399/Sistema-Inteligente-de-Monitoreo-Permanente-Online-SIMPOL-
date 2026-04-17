import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def mostrar_pantalla(user_actual, user_id):
    # 1. SEGURIDAD DE ROL
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad.")
        return

    # 2. CSS INSTITUCIONAL REFORZADO
    st.markdown("""
        <style>
            .titulo-gestion { 
                color: #003366 !important; 
                font-size: 24px !important; 
                font-weight: bold !important; 
                margin-bottom: 15px;
                display: block;
            }
            
            /* TABLA NATIVA */
            [data-testid="stTable"] { background-color: white !important; }
            [data-testid="stTable"] th {
                background-color: #003366 !important;
                color: #FFFFFF !important;
                font-weight: bold !important;
                text-align: center !important;
            }
            [data-testid="stTable"] td { color: #000000 !important; border: 1px solid #dee2e6 !important; }

            /* OCULTAR ÍNDICE NATIVO */
            [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) {
                display: none !important;
            }

            /* --- AJUSTE DEL EXPANDER (ADMINISTRAR CUENTAS) --- */
            [data-testid="stExpander"] {
                border: 1px solid #003366 !important;
                background-color: white !important;
            }
            
            /* Título en blanco sobre el fondo azul del expander */
            [data-testid="stExpander"] summary {
                background-color: #003366 !important;
                color: #FFFFFF !important;
            }
            
            /* Forzar la palabra ADMINISTRAR CUENTAS SELECCIONADAS a blanco */
            [data-testid="stExpander"] summary span [data-testid="stMarkdownContainer"] p {
                color: #FFFFFF !important;
                font-weight: bold !important;
            }

            [data-testid="stExpander"] summary svg {
                fill: #FFFFFF !important;
            }
            
            /* Etiquetas internas en negro */
            [data-testid="stExpander"] label p, [data-testid="stExpander"] .stMarkdown p {
                color: #000000 !important;
                font-weight: bold !important;
            }

            /* BOTONES: FONDO AZUL Y TEXTO BLANCO */
            .stButton > button { 
                background-color: #003366 !important; 
                color: #FFFFFF !important; 
                border: 1px solid #003366 !important;
            }
            
            /* Forzar texto de botones a blanco */
            .stButton > button p {
                color: #FFFFFF !important;
            }

            .stButton > button:hover { 
                border: 1px solid #FFCC00 !important;
                color: #FFCC00 !important;
            }
            .stButton > button:hover p {
                color: #FFCC00 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<span class='titulo-gestion'>GESTIÓN DE PERSONAL</span>", unsafe_allow_html=True)

    # 3. FORMULARIO DE REGISTRO
    if st.session_state.get("mostrar_registro", False):
        with st.container(border=True):
            st.markdown("<h3 style='color:#003366;'>📝 Alta de Nuevo Usuario</h3>", unsafe_allow_html=True)
            with st.form("form_alta"):
                c1, c2 = st.columns(2)
                f_user = c1.text_input("Usuario (Login):")
                f_pass = c2.text_input("Contraseña:", type="password")
                f_nombre = c1.text_input("Nombre Completo:")
                f_rol = c2.selectbox("Rol:", ["operador", "seguridad", "admin"])
                
                if st.form_submit_button("💾 GUARDAR EN SISTEMA"):
                    if f_user and f_pass and f_nombre:
                        crear_nuevo_usuario(f_user, f_pass, f_nombre, f_rol, user_id)
            if st.button("⬅️ CANCELAR"):
                st.session_state.mostrar_registro = False
                st.rerun()
        st.divider()

    # 4. BUSCADOR Y TABLA
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            busqueda = st.text_input("🔍 Filtrar lista:", placeholder="Nombre o usuario...")

            query = "SELECT id, usuario, nombre_completo, rol, estado FROM usuarios"
            params = []
            if busqueda:
                query += " WHERE LOWER(usuario) LIKE LOWER(%s) OR LOWER(nombre_completo) LIKE LOWER(%s)"
                params = [f"%{busqueda}%", f"%{busqueda}%"]
            
            cursor.execute(query, params)
            datos = cursor.fetchall()

            if datos:
                # TABLA SIN COLUMNA TÉCNICA
                tabla_nativa = []
                for u in datos:
                    tabla_nativa.append({
                        "ID": u['id'],
                        "USUARIO": u['usuario'],
                        "NOMBRE": u['nombre_completo'],
                        "ROL": str(u['rol']).upper(),
                        "ESTADO": "🟢 ACTIVO" if u['estado'] == 1 else "🔴 SUSPENDIDO"
                    })
                
                st.table(tabla_nativa)

                # BOTÓN AGREGAR AL FINAL
                if st.button("➕ AGREGAR NUEVO INTEGRANTE", use_container_width=True):
                    st.session_state.mostrar_registro = True
                    st.rerun()

                st.write("")

                # 5. SECCIÓN ADMINISTRAR CUENTAS
                with st.expander("🛠️ ADMINISTRAR CUENTAS SELECCIONADAS", expanded=False):
                    lista_ids = [item['id'] for item in datos]
                    id_edit = st.selectbox("Seleccione ID del empleado:", lista_ids)
                    u_sel = next((i for i in datos if i['id'] == id_edit), None)
                    
                    if u_sel:
                        st.write(f"Gestionando acceso de: **{u_sel['usuario']}**")
                        
                        c1, c2, c3 = st.columns([2, 2, 1])
                        with c1:
                            nuevo_nom = st.text_input("Nombre:", value=u_sel['nombre_completo'], label_visibility="collapsed")
                        with c2:
                            # CAMPO JUSTIFICACIÓN
                            justificacion = st.text_input("Justificación:", placeholder="Justificación de auditoría", label_visibility="collapsed")
                        with c3:
                            if st.button("💾 ACTUALIZAR", use_container_width=True):
                                if justificacion:
                                    ejecutar_update_nombre(u_sel['usuario'], u_sel['nombre_completo'], nuevo_nom, user_id, justificacion)
                                else:
                                    st.error("Indique motivo")

                        st.markdown("<hr style='margin:10px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)
                        
                        ec1, ec2 = st.columns([3, 1])
                        with ec1:
                            est_txt = "🟢 ACTIVO" if u_sel['estado']==1 else "🔴 SUSPENDIDO"
                            st.write(f"Estatus actual: **{est_txt}**")
                        with ec2:
                            lbl = "SUSPENDER" if u_sel['estado'] == 1 else "ACTIVAR"
                            if st.button(lbl, use_container_width=True):
                                if justificacion:
                                    ejecutar_update_estado(u_sel['usuario'], u_sel['estado'], user_id, user_actual, justificacion)
                                else:
                                    st.error("Indique motivo")

            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Fallo técnico: {e}")

# --- BACKEND ---
def crear_nuevo_usuario(u, c, n, r, ejecutor_id):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol) VALUES (%s, %s, %s, %s)", (u, c, n, r))
        conn.commit()
        registrar_auditoria_usuario(u, "REGISTRO", "N/A", f"ROL:{r}", ejecutor_id, "Alta institucional")
        conn.close(); st.success("Registrado."); st.session_state.mostrar_registro = False; st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_nombre(log, v, n, ejecutor_id, mot):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (n, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_NOMBRE", v, n, ejecutor_id, mot)
        conn.close(); st.success("Nombre actualizado."); st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(log, est_v, ejecutor_id, ejecutor_log, mot):
    if str(log) == str(ejecutor_log): st.error("No puede auto-suspenderse."); return
    n_est = 0 if est_v == 1 else 1
    v_v, v_n = ("ACTIVO", "SUSPENDIDO") if est_v == 1 else ("SUSPENDIDO", "ACTIVO")
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (n_est, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_ESTADO", v_v, v_n, ejecutor_id, mot)
        conn.close(); st.success(f"Estatus: {v_n}."); st.rerun()
    except Exception as e: st.error(f"Error: {e}")