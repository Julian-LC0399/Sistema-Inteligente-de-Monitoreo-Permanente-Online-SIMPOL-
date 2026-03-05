import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from database import conectar_bd

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366;'>Gestión de Analistas CSU</h2>", unsafe_allow_html=True)

    # --- 1. REGISTRO (Mantiene Popover con Formulario) ---
    with st.popover("➕ REGISTRAR NUEVO ANALISTA", use_container_width=True):
        with st.form("nuevo_user_form", border=False): 
            u = st.text_input("Usuario (ID / Cédula)")
            n = st.text_input("Nombre Completo")
            p = st.text_input("Contraseña", type="password")
            r = st.selectbox("Rol", ["operador", "admin"])
            
            if st.form_submit_button("REGISTRAR ANALISTA", use_container_width=True):
                if u and n and p:
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    try:
                        # Se inserta con estado = 1 (ACTIVO)
                        cursor.execute(
                            "INSERT INTO usuarios (usuario, clave, nombre_completo, rol, estado) VALUES (%s,%s,%s,%s, 1)", 
                            (u, p, n, r)
                        )
                        conn.commit()
                        st.success(f"✅ Usuario {u} creado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ Complete todos los campos")

    # --- 2. VISUALIZACIÓN DE TABLA ---
    conn = conectar_bd()
    df = pd.read_sql("SELECT usuario, nombre_completo, rol, estado FROM usuarios", conn)
    conn.close()

    if not df.empty:
        # Traducción de estado para la tabla
        df['estado_texto'] = df['estado'].apply(lambda x: "ACTIVO" if x == 1 else "DESACTIVADO")

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection(selection_mode="single", use_checkbox=True)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True)
        
        gb.configure_column("usuario", headerName="USUARIO", pinned='left')
        gb.configure_column("nombre_completo", headerName="NOMBRE COMPLETO")
        gb.configure_column("rol", headerName="ROL")
        gb.configure_column("estado", hide=True) # Oculto el número
        
        # Colores para el estado
        gb.configure_column("estado_texto", headerName="ESTADO", 
                            cellStyle={'styleConditions': [
                                {'condition': "params.value == 'ACTIVO'", 'style': {'color': 'green', 'fontWeight': 'bold'}},
                                {'condition': "params.value == 'DESACTIVADO'", 'style': {'color': 'red', 'fontWeight': 'bold'}}
                            ]})
        
        grid_response = AgGrid(
            df, 
            gridOptions=gb.build(), 
            theme='balham', 
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            key="grid_gestion_v4"
        )

        # --- 3. PANEL DE ACCIONES (Botones Directos para evitar bloqueos) ---
        seleccionados = grid_response['selected_rows']
        
        if seleccionados is not None and len(seleccionados) > 0:
            fila = seleccionados.iloc[0] if isinstance(seleccionados, pd.DataFrame) else seleccionados[0]
            
            st.markdown("---")
            with st.expander(f"⚙️ PANEL DE CONTROL: {fila['usuario']}", expanded=True):
                # Campos de edición directa
                nuevo_nombre = st.text_input("Modificar Nombre", value=fila['nombre_completo'])
                st.text_input("Rol de Sistema (Protegido)", value=fila['rol'].upper(), disabled=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_save, col_status = st.columns(2)
                
                with col_save:
                    # Guardar cambios en el nombre
                    if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                        conn = conectar_bd(); cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo_nombre, fila['usuario']))
                        conn.commit(); conn.close()
                        st.success("Nombre actualizado")
                        st.rerun()

                with col_status:
                    # Lógica de Desactivar / Reactivar
                    if fila['usuario'] != user_actual:
                        if fila['estado'] == 1:
                            # Interruptor de seguridad para habilitar el botón de borrado lógico
                            confirmar = st.toggle(f"Confirmar para Desactivar")
                            if confirmar:
                                if st.button("🗑️ EJECUTAR DESACTIVACIÓN", type="primary", use_container_width=True):
                                    conn = conectar_bd(); cursor = conn.cursor()
                                    cursor.execute("UPDATE usuarios SET estado = 0 WHERE usuario = %s", (fila['usuario'],))
                                    conn.commit(); conn.close()
                                    st.rerun()
                        else:
                            # Reactivación directa
                            if st.button("✅ REACTIVAR ACCESO", use_container_width=True):
                                conn = conectar_bd(); cursor = conn.cursor()
                                cursor.execute("UPDATE usuarios SET estado = 1 WHERE usuario = %s", (fila['usuario'],))
                                conn.commit(); conn.close()
                                st.rerun()
                    else:
                        st.info("Sesión activa (No editable)")
    else:
        st.info("No hay analistas registrados.")