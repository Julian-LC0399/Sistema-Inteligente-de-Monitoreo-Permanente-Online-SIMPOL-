import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def mostrar_pantalla(user_actual, user_id):
    # Verificación de permisos institucional
    if st.session_state.get("rol") == "operador":
        st.error("🚫 Acceso denegado. No tiene permisos de Oficial de Seguridad para este módulo.")
        return

    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ESTILOS INSTITUCIONALES ---
    st.markdown("""
        <style>
            [data-testid="stMain"] h2, [data-testid="stMain"] h4, [data-testid="stMain"] label p {
                color: #003366 !important; font-weight: bold !important;
            }
            [data-testid="stTable"] td { color: black !important; border-bottom: 1px solid #eee !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; font-family: sans-serif; }
            [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) { display: none !important; }
            
            div.stButton > button {
                color: #ffffff !important; background-color: #003366 !important;
                border: none !important; font-weight: bold !important;
                border-radius: 5px !important; transition: 0.3s;
            }
            div.stButton > button:hover { color: #ffcc00 !important; background-color: #002244 !important; border: 1px solid #ffcc00 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366; margin-top:0;'>👥 Gestión de Personal CSU</h2>", unsafe_allow_html=True)

    # --- 1. REGISTRO DE NUEVO PERSONAL ---
    _, col_btn = st.columns([3, 1])
    with col_btn:
        label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        if st.button(label, use_container_width=True):
            st.session_state.mostrar_registro = not st.session_state.mostrar_registro
            st.rerun()

    if st.session_state.mostrar_registro:
        with st.container(border=True):
            st.markdown("#### 📝 Registro de nuevo usuario")
            with st.form("form_nuevo_usuario", clear_on_submit=True):
                c1, c2 = st.columns(2)
                u = c1.text_input("Usuario")
                n = c2.text_input("Nombre Completo")
                p = c1.text_input("Clave", type="password")
                r = c2.selectbox("Rol", ["operador", "admin", "seguridad"])
                
                if st.form_submit_button("REGISTRAR EN SISTEMA", use_container_width=True):
                    if u and n and p:
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s,1)",
                                (u, p, n, r)
                            )
                            conn.commit()
                            # CORREGIDO: 6 argumentos
                            registrar_auditoria_usuario(u, "ALTA DE USUARIO", "N/A", r, user_id, "Alta inicial de personal")
                            cursor.close(); conn.close()
                            st.success(f"Analista {n} registrado exitosamente.")
                            st.session_state.mostrar_registro = False
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.warning("Complete todos los campos.")

    # --- 2. VISTA Y EDICIÓN ---
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
            usuarios_lista = cursor.fetchall()
            cursor.close(); conn.close()

            if usuarios_lista:
                st.markdown("#### 📋 Personal Registrado")
                datos_tabla = [{
                    "USUARIO": u['usuario'],
                    "NOMBRE": u['nombre_completo'].upper(),
                    "ROL": str(u['rol']).upper(),
                    "ESTADO": "🟢 ACTIVO" if u['estado'] == 1 else "🔴 SUSPENDIDO"
                } for u in usuarios_lista]
                st.table(datos_tabla)

                st.divider()
                st.markdown("#### ⚙️ Modificar Analista")
                
                usuario_sel = st.selectbox("Seleccione ID para editar:", [""] + [u['usuario'] for u in usuarios_lista])

                if usuario_sel:
                    user_data = next(u for u in usuarios_lista if u['usuario'] == usuario_sel)
                    with st.container(border=True):
                        with st.form(key=f"edicion_{usuario_sel}"):
                            nuevo_nombre = st.text_input("Modificar Nombre/Cargo", value=user_data["nombre_completo"])
                            comentario = st.text_input("Justificación del cambio (Auditoría)")
                            
                            col_f1, col_f2 = st.columns(2)
                            if col_f1.form_submit_button("💾 ACTUALIZAR DATOS", use_container_width=True):
                                if not comentario.strip():
                                    st.error("Debe ingresar una justificación.")
                                else:
                                    ejecutar_update_nombre(user_data['usuario'], user_data['nombre_completo'], nuevo_nombre, user_id, comentario)
                            
                            label_btn = "🗑️ DESACTIVAR" if user_data["estado"] == 1 else "✅ ACTIVAR"
                            if col_f2.form_submit_button(label_btn, use_container_width=True):
                                if not comentario.strip():
                                    st.error("Debe ingresar una justificación.")
                                else:
                                    ejecutar_update_estado(user_data['usuario'], user_data['estado'], user_id, user_actual, comentario)
            else:
                st.info("No hay analistas registrados.")
    except Exception as e:
        st.error(f"Error: {e}")

def ejecutar_update_nombre(usuario_login, viejo, nuevo, ejecutor_id, comentario):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, usuario_login))
        conn.commit()
        # CORREGIDO: 6 argumentos
        registrar_auditoria_usuario(usuario_login, "CAMBIO DE NOMBRE", viejo, nuevo, ejecutor_id, comentario)
        conn.close()
        st.success("Cambios registrados.")
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(usuario_login, estado_actual, ejecutor_id, ejecutor_login, comentario):
    if str(usuario_login) == str(ejecutor_login):
        st.error("No puedes suspender tu propia cuenta.")
        return
    nuevo_estado = 0 if estado_actual == 1 else 1
    est_v = "ACTIVO" if estado_actual == 1 else "SUSPENDIDO"
    est_n = "SUSPENDIDO" if nuevo_estado == 0 else "ACTIVO"
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, usuario_login))
        conn.commit()
        # CORREGIDO: 6 argumentos
        registrar_auditoria_usuario(usuario_login, "CAMBIO DE ESTADO", est_v, est_n, ejecutor_id, comentario)
        conn.close()
        st.success(f"Estado: {est_n}")
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")