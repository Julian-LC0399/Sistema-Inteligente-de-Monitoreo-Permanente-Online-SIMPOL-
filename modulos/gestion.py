import streamlit as st
import pandas as pd
from database import conectar_bd


def mostrar_pantalla(user_actual):
    # --- CONFIGURACIÓN DE ESTADO INICIAL ---
    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ENCABEZADO Y BOTÓN DE CREACIÓN ---
    col_tit, col_btn = st.columns([3, 1])
    with col_tit:
        st.markdown(
            "<h2 style='color:#003366; margin-top:0;'>Gestión de Analistas </h2>",
            unsafe_allow_html=True,
        )

    with col_btn:
        label = (
            "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        )
        if st.button(
            label,
            use_container_width=True,
            type="primary" if not st.session_state.mostrar_registro else "secondary",
        ):
            st.session_state.mostrar_registro = not st.session_state.mostrar_registro
            st.rerun()

    # --- 1. FORMULARIO PARA REGISTRAR NUEVO ANALISTA ---
    if st.session_state.mostrar_registro:
        with st.container(border=True):
            st.markdown("#### 📝 Registro de Personal")
            with st.form("form_nuevo_usuario", clear_on_submit=True):
                c1, c2 = st.columns(2)
                u = c1.text_input("Usuario (ID / Cédula)")
                n = c2.text_input("Nombre Completo")
                p = c1.text_input("Contraseña Temporal", type="password")
                r = c2.selectbox("Rol de Acceso", ["operador", "admin"])

                if st.form_submit_button(
                    "CONFIRMAR REGISTRO", use_container_width=True
                ):
                    if u and n and p:
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s, 1)",
                                (u, p, n, r),
                            )
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Analista {n} registrado con éxito")
                            st.session_state.mostrar_registro = False
                            st.rerun()
                        except Exception as e:
                            st.error(
                                "Error: El ID de usuario ya existe o hubo un fallo en la base de datos."
                            )
                    else:
                        st.warning("Por favor, complete todos los campos obligatorios.")

    # --- 2. CARGA Y VISUALIZACIÓN DE TABLA ---
    try:
        conn = conectar_bd()
        if conn:
            # Consulta a la tabla de usuarios
            df = pd.read_sql(
                "SELECT usuario, nombre_completo, rol, estado FROM usuarios", conn
            )
            conn.close()

            if not df.empty:
                st.markdown("#### 👥 Listado de Personal")

                # --- SOLUCIÓN VISUAL PARA ESTADO (Sin StatusColumn) ---
                df["ESTADO_VISUAL"] = df["estado"].apply(
                    lambda x: "🟢 ACTIVO" if x == 1 else "🔴 INACTIVO"
                )

                # Configuración de columnas compatible con Streamlit actual
                config_columnas = {
                    "usuario": st.column_config.TextColumn("ID USUARIO"),
                    "nombre_completo": st.column_config.TextColumn("NOMBRE Y APELLIDO"),
                    "rol": st.column_config.TextColumn("ROL"),
                    "ESTADO_VISUAL": st.column_config.TextColumn("ESTADO"),
                    "estado": None,  # Ocultamos la columna numérica original
                }

                # --- TABLA CON SELECCIÓN CORREGIDA ---
                event = st.dataframe(
                    df,
                    column_config=config_columnas,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",  # <-- Corregido: single-row es el parámetro válido
                )

                # --- 3. LÓGICA DE EDICIÓN / DESACTIVACIÓN ---
                # Extraemos la fila seleccionada del evento de la tabla
                indices_seleccionados = event.get("selection", {}).get("rows", [])

                if indices_seleccionados:
                    idx = indices_seleccionados[0]
                    fila = df.iloc[idx]

                    st.markdown("---")
                    with st.container(border=True):
                        st.markdown(f"#### ⚙️ Gestionar Analista: `{fila['usuario']}`")

                        with st.form("form_edicion_usuario"):
                            col_e1, col_e2 = st.columns(2)
                            nuevo_nombre = col_e1.text_input(
                                "Modificar Nombre", value=fila["nombre_completo"]
                            )
                            col_e2.info(
                                f"Rol actual del usuario: **{fila['rol'].upper()}**"
                            )

                            btn_col1, btn_col2 = st.columns(2)

                            # Botón 1: Actualizar Nombre
                            if btn_col1.form_submit_button(
                                "💾 GUARDAR CAMBIOS", use_container_width=True
                            ):
                                if nuevo_nombre:
                                    conn = conectar_bd()
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s",
                                        (nuevo_nombre, fila["usuario"]),
                                    )
                                    conn.commit()
                                    conn.close()
                                    st.success("Información actualizada")
                                    st.rerun()

                            # Botón 2: Activar / Desactivar
                            label_accion = (
                                "🗑️ DESACTIVAR"
                                if fila["estado"] == 1
                                else "✅ REACTIVAR"
                            )
                            if btn_col2.form_submit_button(
                                label_accion, use_container_width=True
                            ):
                                if fila["usuario"] != user_actual:
                                    nuevo_estado = 0 if fila["estado"] == 1 else 1
                                    conn = conectar_bd()
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "UPDATE usuarios SET estado=%s WHERE usuario=%s",
                                        (nuevo_estado, fila["usuario"]),
                                    )
                                    conn.commit()
                                    conn.close()
                                    st.success(
                                        f"Estado de {fila['usuario']} actualizado correctamente"
                                    )
                                    st.rerun()
                                else:
                                    st.warning(
                                        "⚠️ Acción bloqueada: No puedes desactivar tu propio usuario administrativo."
                                    )
                else:
                    st.info(
                        "💡 **Instrucción:** Para editar a un analista o cambiar su estado, haz clic en cualquier celda de su fila en la tabla superior."
                    )
            else:
                st.warning("No se encontraron analistas registrados.")
        else:
            st.error("No se pudo establecer conexión con la base de datos.")

    except Exception as e:
        st.error(f"Error crítico en el módulo de gestión: {e}")
