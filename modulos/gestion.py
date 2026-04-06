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

    # --- 1. FORMULARIO DE REGISTRO (Código Nativo) ---
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

    # --- 2. TABLA DE USUARIOS (100% Nativa - Sin Pandas) ---
    try:
        conn = conectar_bd()
        if conn:
            # Extraemos datos usando el cursor de diccionario de MySQL
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
            usuarios_lista = cursor.fetchall()
            cursor.close()
            conn.close()

            if usuarios_lista:
                st.markdown("<h4 style='color:#333333;'>📋 Analistas Registrados</h4>", unsafe_allow_html=True)
                
                # Formateamos los datos manualmente para st.table
                datos_para_tabla = []
                ids_disponibles = []
                
                for u in usuarios_lista:
                    ids_disponibles.append(u['usuario'])
                    datos_para_tabla.append({
                        "ID USUARIO": u['usuario'],
                        "NOMBRE Y APELLIDO": u['nombre_completo'],
                        "NIVEL": u['rol'].upper(),
                        "ESTADO": "🟢 ACTIVO" if u['estado'] == 1 else "🔴 INACTIVO"
                    })
                
                # Visualización Nativa
                st.table(datos_para_tabla)

                # --- 3. LÓGICA DE EDICIÓN NATIVA ---
                st.markdown("---")
                st.subheader("⚙️ Panel de Edición")
                col_sel, col_esp = st.columns([2, 2])
                
                usuario_a_editar = col_sel.selectbox(
                    "Seleccione un ID para modificar:", 
                    [""] + ids_disponibles,
                    help="Elija el ID del analista que desea editar o cambiar de estado"
                )

                if usuario_a_editar:
                    # Buscamos los datos del usuario seleccionado en la lista nativa
                    fila_seleccionada = next(item for item in usuarios_lista if item["usuario"] == usuario_a_editar)
                    renderizar_formulario_edicion(fila_seleccionada, user_actual)
            else:
                st.markdown("<p style='color:#333333;'>No hay analistas registrados.</p>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error de acceso a datos: {e}")

def renderizar_formulario_edicion(fila, user_actual):
    with st.container(border=True):
        st.markdown(f"#### Editando: {fila['nombre_completo']} ({fila['usuario']})")
        with st.form("form_edicion"):
            nuevo_nombre = st.text_input("Modificar Nombre Completo", value=fila["nombre_completo"])
            col_f1, col_f2 = st.columns(2)
            
            estado_texto = "ACTIVO" if fila["estado"] == 1 else "INACTIVO"
            label_btn = "🗑️ DESACTIVAR" if fila["estado"] == 1 else "✅ ACTIVAR"
            
            st.info(f"Estado actual: {estado_texto}")
            
            btn_save = col_f1.form_submit_button("💾 GUARDAR NOMBRE", use_container_width=True)
            btn_state = col_f2.form_submit_button(label_btn, use_container_width=True)

            if btn_save:
                ejecutar_update_nombre(fila['usuario'], nuevo_nombre, fila['nombre_completo'], user_actual)

            if btn_state:
                ejecutar_update_estado(fila['usuario'], fila['estado'], user_actual)

def ejecutar_update_nombre(usuario_id, nuevo, anterior, ejecutor):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo, usuario_id))
        cursor.execute("INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por) VALUES (%s,%s,%s,%s,%s)", 
                       (usuario_id, "EDICIÓN NOMBRE", anterior, nuevo, ejecutor))
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
    v_ant, v_nue = ("ACTIVO", "INACTIVO") if nuevo_estado == 0 else ("INACTIVO", "ACTIVO")
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, usuario_id))
        cursor.execute("INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por) VALUES (%s,%s,%s,%s,%s)", 
                       (usuario_id, "CAMBIO DE ESTADO", v_ant, v_nue, ejecutor))
        conn.commit()
        conn.close()
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")