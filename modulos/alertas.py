import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode

def mostrar_pantalla():
    # 1. Sincronización permanente (10 segundos)
    st_autorefresh(interval=10000, key="alertas_sync_pro")

    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    # --- VISUALIZACIÓN DE TELEMETRÍA ACTUAL ---
    try:
        cpu_act, ram_act, fuente = obtener_telemetria()
        if cpu_act is not None:
            st.markdown(f"""
                <div style="background-color: #f1f3f4; padding: 10px; border-radius: 5px; margin-bottom: 15px; display: flex; align-items: center; gap: 15px; border-left: 5px solid #003366;">
                    <span style="color: #555; font-size: 14px;">Lectura actual (<b>{fuente}</b>):</span>
                    <span style="background-color: #000; color: #4ade80; padding: 3px 10px; border-radius: 4px; font-family: monospace;">CPU: {cpu_act}%</span>
                    <span style="background-color: #000; color: #4ade80; padding: 3px 10px; border-radius: 4px; font-family: monospace;">RAM: {ram_act}%</span>
                </div>
            """, unsafe_allow_html=True)
    except: pass

    # --- CONFIGURACIÓN DE UMBRALES ---
    col1, col2 = st.columns(2)
    with col1:
        u_cpu = st.number_input("Umbral Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        st.session_state.u_cpu_perc = u_cpu
    with col2:
        u_ram = st.number_input("Umbral Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc)
        st.session_state.u_ram_perc = u_ram

    st.divider()

    # --- TABLA ESTILO REPORTES CON COLOR DINÁMICO ---
    st.subheader("📋 Monitor de Eventos en Tiempo Real")
    
    try:
        conn = conectar_bd()
        query = """
            SELECT fecha_registro as 'Fecha', 
                   nodo_nombre as 'Nodo', 
                   uso_cpu as 'CPU %', 
                   uso_ram as 'RAM %'
            FROM monitoreo_30_nodos 
            ORDER BY fecha_registro DESC LIMIT 20
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            # 1. Configurar Opciones de la Tabla (Igual que en reportes)
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
            gb.configure_side_bar()
            gb.configure_default_column(resizable=True, filterable=True, sortable=True)

            # 2. Lógica JavaScript para colores (Rojo si supera umbral, Verde si no)
            # Usamos los umbrales definidos en el session_state
            row_style_jscode = JsCode(f"""
            function(params) {{
                if (params.data['CPU %'] >= {st.session_state.u_cpu_perc} || params.data['RAM %'] >= {st.session_state.u_ram_perc}) {{
                    return {{
                        'color': 'white',
                        'backgroundColor': '#e74c3c'  // Rojo Alerta
                    }}
                }} else {{
                    return {{
                        'color': 'white',
                        'backgroundColor': '#27ae60'  // Verde Estable
                    }}
                }}
            }};
            """)

            gridOptions = gb.build()
            gridOptions['getRowStyle'] = row_style_jscode # Inyectamos el estilo

            # 3. Renderizar la tabla exactamente como en reportes.py
            AgGrid(
                df,
                gridOptions=gridOptions,
                allow_unsafe_jscode=True, # Obligatorio para los colores
                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                theme="streamlit", # O "balham" para estilo más bancario
                height=400,
                width='100%'
            )
        else:
            st.warning("Esperando ráfaga de datos del agente...")

    except Exception as e:
        st.error(f"Error en sincronía de tabla: {e}")