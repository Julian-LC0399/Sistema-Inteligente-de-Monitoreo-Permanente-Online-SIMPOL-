import streamlit as st
import pandas as pd
import time
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from database import conectar_bd

# Diálogo de confirmación para eliminar
@st.dialog("⚠️ Confirmar Acción Crítica")
def confirmar_borrado(usuario_id):
    st.warning(f"¿Está seguro de eliminar al analista {usuario_id}?")
    if st.button("SÍ, ELIMINAR DEFINITIVAMENTE", type="primary"):
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE usuario = %s", (usuario_id,))
        conn.commit(); conn.close()
        st.success("Analista removido."); time.sleep(1); st.rerun()

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366;'>Gestión de Analistas CSU</h2>", unsafe_allow_html=True)
    
    # --- Formulario de Registro (Pop-over) ---
    with st.popover("➕ REGISTRAR NUEVO ANALISTA", use_container_width=True):
        with st.form("nuevo_user"):
            n_u = st.text_input("Usuario (ID)")
            n_n = st.text_input("Nombre Completo")
            n_p = st.text_input("Clave", type="password")
            if st.form_submit_button("REGISTRAR"):
                conn = conectar_bd(); cursor = conn.cursor()
                cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol) VALUES (%s,%s,%s,'operador')", (n_u, n_p, n_n))
                conn.commit(); conn.close(); st.rerun()

    # --- Tabla de Datos ---
    conn = conectar_bd()
    df = pd.read_sql("SELECT usuario, nombre_completo, rol FROM usuarios", conn)
    conn.close()

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_response = AgGrid(df, gridOptions=gb.build(), theme='balham', key="grid_v2", update_mode=GridUpdateMode.SELECTION_CHANGED)

    # --- Lógica de Edición ---
    seleccionados = grid_response['selected_rows']
    if seleccionados is not None and len(seleccionados) > 0:
        fila = seleccionados.iloc[0] if isinstance(seleccionados, pd.DataFrame) else seleccionados[0]
        
        with st.form("edit_form_v2"):
            st.subheader(f"Editando: {fila['usuario']}")
            nuevo_nombre = st.text_input("Nombre", value=fila['nombre_completo'])
            if st.form_submit_button("GUARDAR"):
                conn = conectar_bd(); cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nuevo_nombre, fila['usuario']))
                conn.commit(); conn.close(); st.rerun()
        
        if st.button("🗑️ ELIMINAR ANALISTA"):
            if fila['usuario'] != user_actual:
                confirmar_borrado(fila['usuario'])
            else:
                st.error("No puedes auto-eliminarte.")