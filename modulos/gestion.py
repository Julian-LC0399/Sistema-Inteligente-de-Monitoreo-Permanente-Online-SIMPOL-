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

    st.markdown("<h2 style='color:#003366; margin-top:0;'>👥 Gestión de Personal y Analistas</h2>", unsafe_allow_html=True)

    # Inyección de CSS para corregir letras blancas en las tablas
    st.markdown("""
        <style>
            [data-testid="stTable"] td, [data-testid="stTable"] th { color: #000000 !important; }
            table { background-color: #ffffff !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. FORMULARIO DE REGISTRO ---
    if rol_actual == "seguridad":
        col_tit, col_btn = st.columns([3, 1])
        with col_btn:
            label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
            if st.button(label, use_container_width=True, type="primary" if not st.session_state.mostrar_registro else "secondary"):
                st.session_state.mostrar_registro = not st.session_state.mostrar_registro
                st.rerun()

        if st.session_state.mostrar_registro:
            with st.container(border=True):
                st.markdown("<h4 style='color:#333333;'>📝 Registro de Nuevo Personal</h4>", unsafe_allow_html=True)
                with st.form("form_nuevo_usuario", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    u = c1.text_input("Usuario (Cédula o ID)")
                    n = c2.text_input("Nombre Completo")
                    p = c1.text_input("Contraseña Temporal", type="password")
                    r = c2.selectbox("Rol", ["operador", "admin", "seguridad"])

                    if st.form_submit_button("REGISTRAR ANALISTA", use_container_width=True):
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
                                st.success(f"Analista {n} creado exitosamente.")
                                st.session_state.mostrar_registro = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Complete todos los campos.")

    # --- 2. TABLA DE USUARIOS (Nativa por índices) ---
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
            usuarios_lista = cursor.fetchall()
            cursor.close()
            conn.close()

            if usuarios_lista:
                st.markdown("<h4 style='color:#333333;'>📋 Analistas Registrados</h4>", unsafe_allow_html=True)
                
                datos_para_tabla = []
                ids_disponibles = []
                
                for u in usuarios_lista:
                    id_user = str(u[0])
                    ids_disponibles.append(id_user)
                    datos_para_tabla.append({
                        "ID USUARIO": id_user,
                        "NOMBRE Y APELLIDO": u[1],
                        "NIVEL": str(u[2]).upper(),
                        "ESTADO": "🟢 ACTIVO" if u[3] == 1 else "🔴 INACTIVO"
                    })
                
                st.table(datos_para_tabla)

                # --- 3. PANEL DE EDICIÓN ---
                st.markdown("---")
                st.subheader("⚙️ Panel de Edición")
                usuario_a_editar = st.selectbox("Seleccione un ID para modificar:", [""] + ids_disponibles)

                if usuario_a_editar:
                    fila_raw = next(item for item in usuarios_lista if str(item[0]) == usuario_a_editar)
                    fila_dict = {"usuario": fila_raw[0], "nombre_completo": fila_raw[1], "rol": fila_raw[2], "estado": fila_raw[3]}
                    
                    with st.container(border=True):
                        st.markdown(f"#### Editando: {fila_dict['nombre_completo']}")
                        with st.form("form_edicion"):
                            nuevo_nombre = st.text_input("Modificar Nombre Completo", value=fila_dict["nombre_completo"])
                            col_f1, col_f2 = st.columns(2)
                            if col_f1.form_submit_button("💾 GUARDAR NOMBRE", use_container_width=True):
                                ejecutar_update_nombre(fila_dict['usuario'], nuevo_nombre, fila_dict['nombre_completo'], user_actual)
                            label_btn = "🗑️ DESACTIVAR" if fila_dict["estado"] == 1 else "✅ ACTIVAR"
                            if col_f2.form_submit_button(label_btn, use_container_width=True):
                                ejecutar_update_estado(fila_dict['usuario'], fila_dict['estado'], user_actual)
            else:
                st.info("No hay analistas registrados.")
    except Exception as e:
        st.error(f"Error de visualización: {e}")

def ejecutar_update_nombre(usuario_id, nuevo, anterior, ejecutor):
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