import streamlit as st
from database import conectar_bd
from datetime import datetime

# --- INTENTO DE IMPORTACIÓN SEGURA ---
try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

def mostrar_pantalla(user_actual):
    rol_actual = st.session_state.get("rol", "operador")

    if rol_actual == "operador":
        st.error("🚫 Acceso denegado. No tiene permisos para ver este módulo.")
        return

    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    st.markdown("<h2 style='color:#003366; margin-top:0;'>👥 Gestión de Personal y Analistas</h2>", unsafe_allow_html=True)

    # --- 1. FORMULARIO DE REGISTRO (Código Nativo, siempre funciona) ---
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

    # --- 2. TABLA DE USUARIOS (Lógica Dual) ---
    try:
        conn = conectar_bd()
        if conn:
            # Extraemos datos de forma nativa (lista de diccionarios)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT usuario, nombre_completo, rol, estado FROM usuarios")
            usuarios_lista = cursor.fetchall()
            cursor.close()
            conn.close()

            if usuarios_lista:
                st.markdown("<h4 style='color:#333333;'>📋 Analistas Registrados</h4>", unsafe_allow_html=True)
                
                # --- MODO CON PANDAS (Interactivo) ---
                if PANDAS_OK:
                    df = pd.DataFrame(usuarios_lista)
                    df["ESTATUS"] = df["estado"].apply(lambda x: "🟢 ACTIVO" if x == 1 else "🔴 INACTIVO")
                    
                    event = st.dataframe(
                        df,
                        column_config={
                            "usuario": "ID USUARIO",
                            "nombre_completo": "NOMBRE Y APELLIDO",
                            "rol": "NIVEL",
                            "ESTATUS": "ESTADO",
                            "estado": None 
                        },
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row"
                    )

                    # Lógica de edición basada en selección
                    seleccion = event.get("selection", {}).get("rows", [])
                    if seleccion:
                        fila = df.iloc[seleccion[0]]
                        renderizar_formulario_edicion(fila, user_actual)

                # --- MODO SIN PANDAS (Servidor con Error) ---
                else:
                    st.warning("⚠️ Modo de compatibilidad: Selección deshabilitada (Sin Pandas)")
                    # Mostramos los datos en una tabla estática
                    st.table(usuarios_lista)
                    st.info("Para editar un usuario en el servidor, use la consola de base de datos mientras se resuelve el error de DLL.")
            else:
                st.markdown("<p style='color:#333333;'>No hay analistas registrados.</p>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error general: {e}")

# Función auxiliar para no ensuciar el código principal
def renderizar_formulario_edicion(fila, user_actual):
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"<h4 style='color:#333333;'>⚙️ Editar Analista: <span style='color:#003366;'>{fila['usuario']}</span></h4>", unsafe_allow_html=True)
        with st.form("form_edicion"):
            nuevo_nombre = st.text_input("Modificar Nombre Completo", value=fila["nombre_completo"])
            col_f1, col_f2 = st.columns(2)
            label_btn = "🗑️ DESACTIVAR" if fila["estado"] == 1 else "✅ ACTIVAR"
            btn_save = col_f1.form_submit_button("💾 GUARDAR", use_container_width=True)
            btn_state = col_f2.form_submit_button(label_btn, use_container_width=True)

            if btn_save:
                # ... (Lógica de UPDATE igual que tu original)
                ejecutar_update_nombre(fila['usuario'], nuevo_nombre, fila['nombre_completo'], user_actual)

            if btn_state:
                # ... (Lógica de UPDATE estado igual que tu original)
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
    if usuario_id == ejecutor:
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