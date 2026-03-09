import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from database import conectar_bd

def mostrar_pantalla(user_actual):
    # --- CONFIGURACIÓN DE ESTADO INICIAL ---
    if "mostrar_registro" not in st.session_state:
        st.session_state.mostrar_registro = False

    # --- ENCABEZADO Y BOTÓN DE CREACIÓN ---
    col_tit, col_btn = st.columns([3, 1])
    with col_tit:
        st.markdown("<h2 style='color:#003366; margin-top:0;'>Gestión de Analistas CSU</h2>", unsafe_allow_html=True)
    
    with col_btn:
        label = "❌ CANCELAR" if st.session_state.mostrar_registro else "➕ NUEVO ANALISTA"
        if st.button(label, use_container_width=True, type="primary" if not st.session_state.mostrar_registro else "secondary"):
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
                
                if st.form_submit_button("CONFIRMAR REGISTRO", use_container_width=True):
                    if u and n and p:
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s, 1)", 
                                (u, p, n, r)
                            )
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Analista {n} registrado")
                            # Cerramos el formulario y refrescamos
                            st.session_state.mostrar_registro = False
                            st.rerun()
                        except Exception as e:
                            st.error("Error: El ID de usuario ya existe o hubo un fallo en la base de datos.")
                    else:
                        st.warning("Complete todos los campos.")

    # --- 2. CARGA Y VISUALIZACIÓN DE TABLA ---
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT usuario, nombre_completo, rol, estado FROM usuarios", conn)
        conn.close()

        if not df.empty:
            # Texto para el borrado lógico
            df['estado_visual'] = df['estado'].apply(lambda x: "ACTIVO" if x == 1 else "INACTIVO")

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection(selection_mode="single", use_checkbox=True)
            gb.configure_default_column(filterable=True, sortable=True, resizable=True)
            
            # Formateo de columnas
            gb.configure_column("usuario", headerName="ID USUARIO", pinned='left')
            gb.configure_column("nombre_completo", headerName="NOMBRE Y APELLIDO", width=250)
            gb.configure_column("estado", hide=True) # Ocultamos el 0/1 original
            
            # JS para colores de estado
            color_js = JsCode("""
            function(params) {
                if (params.value === 'ACTIVO') {
                    return {'color': 'white', 'backgroundColor': '#27ae60', 'fontWeight': 'bold'};
                } else {
                    return {'color': 'white', 'backgroundColor': '#e74c3c', 'fontWeight': 'bold'};
                }
            }
            """)
            gb.configure_column("estado_visual", headerName="ESTADO", cellStyle=color_js)

            grid_response = AgGrid(
                df, 
                gridOptions=gb.build(), 
                theme='balham', 
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                allow_unsafe_jscode=True,
                height=350
            )

            # --- 3. FORMULARIO DE EDICIÓN (Aparece al seleccionar fila) ---
            seleccion = grid_response['selected_rows']
            
            # Validación de selección según versión de AgGrid
            if seleccion is not None and len(seleccion) > 0:
                fila = seleccion.iloc[0] if isinstance(seleccion, pd.DataFrame) else seleccion[0]
                
                st.markdown("---")
                with st.container(border=True):
                    st.markdown(f"#### ⚙️ Editar Perfil: {fila['usuario']}")
                    
                    with st.form("form_edicion_dinamica"):
                        col_e1, col_e2 = st.columns(2)
                        nuevo_nombre = col_e1.text_input("Nombre Completo", value=fila['nombre_completo'])
                        col_e2.info(f"Rol: {fila['rol'].upper()}")
                        
                        btn_col1, btn_col2 = st.columns(2)
                        
                        # Acción 1: Actualizar Datos
                        if btn_col1.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                            if nuevo_nombre:
                                conn = conectar_bd(); cursor = conn.cursor()
                                cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo_nombre, fila['usuario']))
                                conn.commit(); conn.close()
                                st.success("Cambios aplicados")
                                st.rerun() # Esto limpia la selección y cierra el form
                        
                        # Acción 2: Borrado Lógico (Cambiar Estado)
                        label_borrado = "🗑️ DESACTIVAR" if fila['estado'] == 1 else "✅ REACTIVAR"
                        if btn_col2.form_submit_button(label_borrado, use_container_width=True):
                            if fila['usuario'] != user_actual:
                                nuevo_estado = 0 if fila['estado'] == 1 else 1
                                conn = conectar_bd(); cursor = conn.cursor()
                                cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (nuevo_estado, fila['usuario']))
                                conn.commit(); conn.close()
                                st.success("Estado actualizado")
                                st.rerun()
                            else:
                                st.warning("No puedes desactivar tu propio usuario.")
            else:
                st.info("💡 Seleccione un analista de la tabla para editar o gestionar su estado.")

        else:
            st.warning("No hay usuarios registrados en la base de datos.")

    except Exception as e:
        st.error(f"Error en el módulo de gestión: {e}")