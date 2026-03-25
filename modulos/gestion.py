import streamlit as st
import pandas as pd
from database import conectar_bd
from datetime import datetime

def mostrar_pantalla(user_actual):
    # --- CONFIGURACIÓN DE ESTADO INICIAL ---
    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ENCABEZADO Y BOTÓN DE CREACIÓN ---
    col_tit, col_btn = st.columns([3, 1])
    with col_tit:
        st.markdown(
            "<h2 style='color:#003366; margin-top:0;'>👥 Gestión de Personal y Auditoría</h2>",
            unsafe_allow_html=True,
        )

    with col_btn:
        label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        if st.button(label, use_container_width=True, type="primary" if not st.session_state.mostrar_registro else "secondary"):
            st.session_state.mostrar_registro = not st.session_state.mostrar_registro
            st.rerun()

    # --- 1. FORMULARIO PARA REGISTRAR NUEVO ANALISTA ---
    if st.session_state.mostrar_registro:
        with st.container(border=True):
            st.markdown("#### 📝 Registro de Nuevo Personal")
            with st.form("form_nuevo_usuario", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nuevo_user = c1.text_input("ID de Usuario (Ej: operador2)")
                nuevo_nombre = c2.text_input("Nombre Completo")
                
                c3, c4 = st.columns(2)
                nueva_clave = c3.text_input("Contraseña Temporal", type="password")
                nuevo_rol = c4.selectbox("Rol en el Sistema", ["operador", "admin", "seguridad"])
                
                if st.form_submit_button("🚀 REGISTRAR E INICIAR AUDITORÍA", use_container_width=True):
                    if nuevo_user and nueva_clave and nuevo_nombre:
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            
                            # Insertar Usuario
                            cursor.execute(
                                "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s, %s, %s, %s, 1)",
                                (nuevo_user, nueva_clave, nuevo_nombre, nuevo_rol)
                            )
                            
                            # Registrar en historico_usuarios
                            query_audit = """
                                INSERT INTO historico_usuarios 
                                (fecha_cambio, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(query_audit, (datetime.now(), nuevo_user, "CREACIÓN", "N/A", "ACTIVO", user_actual))
                            
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Usuario {nuevo_user} creado y auditado correctamente.")
                            st.session_state.mostrar_registro = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: El usuario ya existe o hubo un fallo en BD: {e}")
                    else:
                        st.warning("Por favor complete todos los campos.")

    # --- 2. VISUALIZACIÓN Y GESTIÓN DE ESTADOS ---
    try:
        conn = conectar_bd()
        if conn:
            query = "SELECT usuario, nombre_completo, rol, estado, fecha_creacion FROM usuarios"
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                st.markdown("### 📋 Analistas Registrados")
                # Mostrar tabla interactiva
                df_mostrar = df.copy()
                df_mostrar["estado"] = df_mostrar["estado"].apply(lambda x: "🟢 ACTIVO" if x == 1 else "🔴 INACTIVO")
                
                event = st.dataframe(
                    df_mostrar,
                    column_config={
                        "usuario": "ID Usuario",
                        "nombre_completo": "Nombre y Apellido",
                        "rol": "Permisos",
                        "estado": "Estatus Actual",
                        "fecha_creacion": st.column_config.DatetimeColumn("Alta en Sistema", format="DD/MM/YYYY")
                    },
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )

                # --- 3. LÓGICA DE ACTIVACIÓN / DESACTIVACIÓN ---
                if len(event.selection.rows) > 0:
                    idx = event.selection.rows[0]
                    fila = df.iloc[idx]
                    
                    st.divider()
                    with st.container(border=True):
                        st.markdown(f"#### ⚙️ Acciones para: {fila['nombre_completo']}")
                        
                        col_info, col_btn = st.columns([2, 1])
                        with col_info:
                            st.write(f"**Usuario:** {fila['usuario']} | **Rol:** {fila['rol'].upper()}")
                        
                        with col_btn:
                            label_accion = "🗑️ DESACTIVAR" if fila["estado"] == 1 else "✅ ACTIVAR"
                            color_btn = "primary" if fila["estado"] == 0 else "secondary"
                            
                            if st.button(label_accion, use_container_width=True, type=color_btn):
                                if fila["usuario"] == user_actual:
                                    st.error("❌ No puedes desactivar tu propio usuario administrativo.")
                                else:
                                    nuevo_estado = 0 if fila["estado"] == 1 else 1
                                    v_ant = "ACTIVO" if fila["estado"] == 1 else "INACTIVO"
                                    v_nue = "INACTIVO" if nuevo_estado == 0 else "ACTIVO"
                                    
                                    try:
                                        conn = conectar_bd()
                                        cursor = conn.cursor()
                                        
                                        # 1. Actualizar estado
                                        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, fila["usuario"]))
                                        
                                        # 2. Insertar en tabla de auditoría (historico_usuarios)
                                        query_audit = """
                                            INSERT INTO historico_usuarios 
                                            (fecha_cambio, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, ejecutado_por)
                                            VALUES (%s, %s, %s, %s, %s, %s)
                                        """
                                        cursor.execute(query_audit, (datetime.now(), fila["usuario"], "CAMBIO DE ESTADO", v_ant, v_nue, user_actual))
                                        
                                        conn.commit()
                                        conn.close()
                                        st.success(f"Cambiado a {v_nue} con éxito.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error en BD: {e}")
                else:
                    st.info("💡 Selecciona una fila en la tabla para activar o desactivar un analista.")
            else:
                st.warning("No hay usuarios registrados.")
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")