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

    # --- ENCABEZADO (Texto Visible) ---
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

    # --- 2. TABLA DE USUARIOS ---
    try:
        conn = conectar_bd()
        if conn:
            df = pd.read_sql("SELECT usuario, nombre_completo, rol, estado FROM usuarios", conn)
            conn.close()

            if not df.empty:
                st.markdown("<h4 style='color:#333333;'>📋 Analistas Registrados</h4>", unsafe_allow_html=True)
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

                # --- 3. FORMULARIO DE EDICIÓN RESTAURADO ---
                seleccion = event.get("selection", {}).get("rows", [])
                if seleccion:
                    fila = df.iloc[seleccion[0]]
                    st.markdown("---")
                    
                    with st.container(border=True):
                        st.markdown(f"<h4 style='color:#333333;'>⚙️ Editar Analista: <span style='color:#003366;'>{fila['usuario']}</span></h4>", unsafe_allow_html=True)
                        
                        # Formulario para actualizar datos
                        with st.form("form_edicion"):
                            nuevo_nombre = st.text_input("Modificar Nombre Completo", value=fila["nombre_completo"])
                            
                            col_f1, col_f2 = st.columns(2)
                            label_btn = "🗑️ DESACTIVAR USUARIO" if fila["estado"] == 1 else "✅ ACTIVAR USUARIO"
                            
                            btn_save = col_f1.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True)
                            btn_state = col_f2.form_submit_button(label_btn, use_container_width=True)

                            if btn_save:
                                try:
                                    conn = conectar_bd()
                                    cursor = conn.cursor()
                                    # Actualización de nombre
                                    cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo_nombre, fila["usuario"]))
                                    # Auditoría de nombre
                                    cursor.execute("""
                                        INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por) 
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (fila["usuario"], "EDICIÓN NOMBRE", fila["nombre_completo"], nuevo_nombre, user_actual))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                    st.success("Cambios guardados.")
                                    st.rerun()
                                except Exception as e:
                                    if "RerunData" in str(type(e)): raise e
                                    st.error(f"Fallo en BD: {e}")

                            if btn_state:
                                if fila["usuario"] == user_actual:
                                    st.error("No puedes cambiar tu propio estado.")
                                else:
                                    nuevo_estado = 0 if fila["estado"] == 1 else 1
                                    v_ant, v_nue = ("ACTIVO", "INACTIVO") if nuevo_estado == 0 else ("INACTIVO", "ACTIVO")
                                    try:
                                        conn = conectar_bd()
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, fila["usuario"]))
                                        cursor.execute("""
                                            INSERT INTO historico_usuarios (usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por) 
                                            VALUES (%s, %s, %s, %s, %s)
                                        """, (fila["usuario"], "CAMBIO DE ESTADO", v_ant, v_nue, user_actual))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                        st.rerun()
                                    except Exception as e:
                                        if "RerunData" in str(type(e)): raise e
                                        st.error(f"Fallo en BD: {e}")
            else:
                st.markdown("<p style='color:#333333;'>No hay analistas registrados.</p>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error general: {e}")