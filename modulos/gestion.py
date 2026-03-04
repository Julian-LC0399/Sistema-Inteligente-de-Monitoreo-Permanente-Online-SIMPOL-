import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from database import conectar_bd

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366;'>Gestión de Analistas CSU</h2>", unsafe_allow_html=True)

    # --- SECCIÓN A: REGISTRO NUEVO ---
    with st.popover("➕ REGISTRAR NUEVO ANALISTA", use_container_width=True):
        # Usamos border=False para eliminar el recuadro gris/negro innecesario
        with st.form("nuevo_user", border=False): 
            col1, col2 = st.columns(2)
            u = col1.text_input("Usuario (ID)")
            n = col2.text_input("Nombre Completo")
            p = col1.text_input("Contraseña", type="password")
            r = col2.selectbox("Rol", ["operador", "admin"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Botón con color explícito para evitar el texto en blanco
            if st.form_submit_button("REGISTRAR EN BASE DE DATOS", use_container_width=True):
                if u and n and p:
                    conn = conectar_bd(); cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol) VALUES (%s,%s,%s,%s)", (u, p, n, r))
                        conn.commit()
                        st.success("✅ Registrado"); st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        conn.close()

    # --- SECCIÓN B: TABLA DE DATOS ---
    conn = conectar_bd()
    df = pd.read_sql("SELECT usuario, nombre_completo, rol FROM usuarios", conn)
    conn.close()

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_default_column(filterable=True, sortable=True)
    
    grid_response = AgGrid(
        df, 
        gridOptions=gb.build(), 
        theme='balham', 
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        key="gestion_table_v2"
    )

    # --- SECCIÓN C: LÓGICA DE EDICIÓN ---
    seleccionados = grid_response['selected_rows']
    
    if seleccionados is not None and len(seleccionados) > 0:
        fila = seleccionados.iloc[0] if isinstance(seleccionados, pd.DataFrame) else seleccionados[0]
        
        st.markdown("---")
        # Forzamos el color del texto del expander para que sea visible
        with st.expander(f"📝 EDITAR DATOS DE: {fila['usuario']}", expanded=True):
            with st.form("form_edit", border=False):
                nuevo_nombre = st.text_input("Nombre Completo", value=fila['nombre_completo'])
                nuevo_rol = st.selectbox("Cambiar Rol", ["operador", "admin"], 
                                       index=0 if fila['rol'] == 'operador' else 1)
                
                # Agregamos una columna para los botones de acción
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                        conn = conectar_bd(); cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET nombre_completo=%s, rol=%s WHERE usuario=%s", 
                                     (nuevo_nombre, nuevo_rol, fila['usuario']))
                        conn.commit(); conn.close()
                        st.success("Actualizado"); st.rerun()