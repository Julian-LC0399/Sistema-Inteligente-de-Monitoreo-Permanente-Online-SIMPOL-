import streamlit as st
import pandas as pd
from database import conectar_bd
from datetime import datetime

def mostrar_pantalla(user_actual):
    # Obtener el rol de la sesión
    rol_actual = st.session_state.get("rol", "operador")

    # --- 0. RESTRICCIÓN PARA OPERADORES ---
    if rol_actual == "operador":
        st.error("🚫 Acceso denegado. No tiene permisos para ver este módulo.")
        return

    # --- CONFIGURACIÓN DE ESTADO INICIAL ---
    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ENCABEZADO ---
    st.markdown("<h2 style='color:#003366; margin-top:0;'>👥 Gestión de Personal y Analistas</h2>", unsafe_allow_html=True)

    # --- 1. FORMULARIO DE REGISTRO (SOLO SEGURIDAD) ---
    if rol_actual == "seguridad":
        col_tit, col_btn = st.columns([3, 1])
        with col_btn:
            label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
            if st.button(label, use_container_width=True, type="primary" if not st.session_state.mostrar_registro else "secondary"):
                st.session_state.mostrar_registro = not st.session_state.mostrar_registro
                st.rerun()

        if st.session_state.mostrar_registro:
            with st.container(border=True):
                st.markdown("#### 📝 Registro de Nuevo Personal")
                with st.form("form_nuevo_usuario", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    nuevo_user = c1.text_input("ID de Usuario")
                    nuevo_nombre = c2.text_input("Nombre Completo")
                    c3, c4 = st.columns(2)
                    nueva_clave = c3.text_input("Contraseña", type="password")
                    nuevo_rol = c4.selectbox("Rol", ["operador", "admin", "seguridad"])
                    
                    if st.form_submit_button("🚀 REGISTRAR", use_container_width=True):
                        if nuevo_user and nueva_clave and nuevo_nombre:
                            try:
                                conn = conectar_bd()
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s, %s, %s, %s, 1)",
                                              (nuevo_user, nueva_clave, nuevo_nombre, nuevo_rol))
                                # Auditoría de creación
                                cursor.execute("INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_nuevo, ejecutado_por) VALUES (%s, %s, %s, %s)",
                                              (nuevo_user, "CREACIÓN", "ACTIVO", user_actual))
                                conn.commit()
                                conn.close()
                                st.success("Usuario registrado.")
                                st.rerun()
                            except: st.error("Error al registrar.")
    else:
        st.info("ℹ️ **Modo Lectura:** Como Administrador, puede visualizar el personal pero no realizar cambios.")

    # --- 2. TABLA DE PERSONAL (ADMIN Y SEGURIDAD) ---
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT usuario, nombre_completo, rol, estado, fecha_creacion FROM usuarios", conn)
        conn.close()

        if not df.empty:
            df_mostrar = df.copy()
            df_mostrar["estado"] = df_mostrar["estado"].apply(lambda x: "🟢 ACTIVO" if x == 1 else "🔴 INACTIVO")
            
            # Si es admin, no permitimos selección para evitar que intente editar
            seleccion_mode = "single-row" if rol_actual == "seguridad" else "none"
            
            event = st.dataframe(
                df_mostrar,
                column_config={
                    "usuario": "ID", "nombre_completo": "Nombre", "rol": "Perfil",
                    "estado": "Estatus", "fecha_creacion": st.column_config.DatetimeColumn("Alta")
                },
                use_container_width=True,
                hide_index=True,
                on_select="rerun" if rol_actual == "seguridad" else None,
                selection_mode=seleccion_mode
            )

            # --- 3. ACCIONES DE EDICIÓN (SOLO SEGURIDAD) ---
            if rol_actual == "seguridad" and len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                fila = df.iloc[idx]
                
                st.divider()
                with st.container(border=True):
                    st.markdown(f"#### ⚙️ Cambiar estado: {fila['usuario']}")
                    label_btn = "🗑️ DESACTIVAR" if fila["estado"] == 1 else "✅ ACTIVAR"
                    
                    if st.button(label_btn, use_container_width=True):
                        if fila["usuario"] == user_actual:
                            st.error("No puedes desactivarte a ti mismo.")
                        else:
                            nuevo_estado = 0 if fila["estado"] == 1 else 1
                            try:
                                conn = conectar_bd()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, fila["usuario"]))
                                # Auditoría
                                cursor.execute("INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por) VALUES (%s, %s, %s, %s, %s)",
                                              (fila["usuario"], "CAMBIO DE ESTADO", "ACTIVO" if nuevo_estado==0 else "INACTIVO", "INACTIVO" if nuevo_estado==0 else "ACTIVO", user_actual))
                                conn.commit()
                                conn.close()
                                st.rerun()
                            except: st.error("Fallo en BD.")
        else:
            st.warning("No hay analistas en la base de datos.")
    except Exception as e:
        st.error(f"Error: {e}")