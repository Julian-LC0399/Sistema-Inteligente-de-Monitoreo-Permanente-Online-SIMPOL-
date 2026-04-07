import streamlit as st
from database import conectar_bd
from datetime import datetime

def mostrar_pantalla(user_actual):
    rol_actual = st.session_state.get("rol", "operador")

    if rol_actual == "operador":
        st.error("🚫 Acceso denegado. No tiene permisos para ver este módulo.")
        return

    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- BLOQUE DE ESTILOS UNIFICADOS (ALTO CONTRASTE) ---
    st.markdown("""
        <style>
            /* 1. Títulos y etiquetas en negro puro */
            [data-testid="stMain"] h2, [data-testid="stMain"] h4, [data-testid="stMain"] label p {
                color: #000000 !important;
                font-weight: bold !important;
            }

            /* 2. Estilo de la Tabla (Sin índice y con cabecera institucional) */
            [data-testid="stTable"] td { color: black !important; border: 1px solid #eee !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
            
            /* Ocultar columna de índice (0, 1, 2...) */
            [data-testid="stTable"] td:nth-child(1), 
            [data-testid="stTable"] th:nth-child(1) {
                display: none !important;
            }

            /* 3. Botones Estilo Banco Caroní */
            div.stButton > button {
                color: #ffffff !important;
                background-color: #003366 !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                text-transform: uppercase;
            }
            
            div.stButton > button:hover {
                background-color: #00509d !important;
                color: #ffffff !important;
            }

            /* Botón Secundario (Cancelar) */
            div.stButton > button[kind="secondary"] {
                color: #000000 !important;
                background-color: #f0f2f6 !important;
                border: 1px solid #d1d3d8 !important;
            }

            /* 4. Inputs con texto negro */
            input, select {
                color: black !important;
                font-weight: bold !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#003366; margin-top:0;'>👥 Gestión de usuarios</h2>", unsafe_allow_html=True)

    # --- 1. FORMULARIO DE REGISTRO ---
    if rol_actual == "seguridad":
        col_tit, col_btn = st.columns([3, 1])
        with col_btn:
            label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ AGREGAR NUEVO USUARIO"
            if st.button(label, use_container_width=True):
                st.session_state.mostrar_registro = not st.session_state.mostrar_registro
                st.rerun()

        if st.session_state.mostrar_registro:
            with st.container(border=True):
                st.markdown("#### 📝 Registro de usuario")
                with st.form("form_nuevo_usuario", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    u = c1.text_input("Usuario (Cédula o ID)")
                    n = c2.text_input("Nombre Completo")
                    p = c1.text_input("Contraseña Temporal", type="password")
                    r = c2.selectbox("Rol", ["operador", "admin", "seguridad"])

                    if st.form_submit_button("REGISTRAR", use_container_width=True):
                        if u and n and p:
                            try:
                                conn = conectar_bd()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s,1)",
                                    (u, p, n, r)
                                )
                                conn.commit()
                                cursor.close()
                                conn.close()
                                st.success(f"Registro {n} creado exitosamente.")
                                st.session_state.mostrar_registro = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Complete todos los campos.")

    # --- 2. TABLA DE USUARIOS ---
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
            usuarios_lista = cursor.fetchall()
            cursor.close()
            conn.close()

            if usuarios_lista:
                st.markdown("#### 📋 Usuarios Registrados")
                
                datos_para_tabla = []
                ids_disponibles = []
                
                for u in usuarios_lista:
                    id_user = str(u[0])
                    ids_disponibles.append(id_user)
                    datos_para_tabla.append({
                        "USUARIO": id_user,
                        "CARGO": u[1],
                        "ROL": str(u[2]).upper(),
                        "ESTADO": "🟢 ACTIVO" if u[3] == 1 else "🔴 INACTIVO"
                    })
                
                st.table(datos_para_tabla)

                # --- 3. PANEL DE EDICIÓN ---
                st.divider()
                st.markdown("#### ⚙️ Edición de usuarios")
                usuario_a_editar = st.selectbox("Seleccione un usuario para modificar:", [""] + ids_disponibles)

                if usuario_a_editar:
                    fila_raw = next(item for item in usuarios_lista if str(item[0]) == usuario_a_editar)
                    fila_dict = {"usuario": fila_raw[0], "nombre_completo": fila_raw[1], "rol": fila_raw[2], "estado": fila_raw[3]}
                    
                    with st.container(border=True):
                        st.markdown(f"**Editando a:** {fila_dict['nombre_completo']}")
                        with st.form("form_edicion"):
                            nuevo_nombre = st.text_input("Modificar cargo", value=fila_dict["nombre_completo"])
                            col_f1, col_f2 = st.columns(2)
                            
                            if col_f1.form_submit_button("💾 GUARDAR", use_container_width=True):
                                ejecutar_update_nombre(fila_dict['usuario'], nuevo_nombre)
                            
                            label_btn = "🗑️ DESACTIVAR" if fila_dict["estado"] == 1 else "✅ ACTIVAR"
                            if col_f2.form_submit_button(label_btn, use_container_width=True):
                                ejecutar_update_estado(fila_dict['usuario'], fila_dict['estado'], user_actual)
            else:
                st.info("No hay analistas registrados.")
    except Exception as e:
        st.error(f"Error de visualización: {e}")

def ejecutar_update_nombre(usuario_id, nuevo):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, usuario_id))
        conn.commit()
        conn.close()
        st.success("Cambios guardados.")
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(usuario_id, estado_actual, ejecutor):
    if str(usuario_id) == str(ejecutor):
        st.error("No puedes cambiar tu propio estado.")
        return
    nuevo_estado = 0 if estado_actual == 1 else 1
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, usuario_id))
        conn.commit()
        conn.close()
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")