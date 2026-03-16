import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh

def mostrar_pantalla():
    st_autorefresh(interval=10000, key="alertas_sync_pro")
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    try:
        cpu_act, ram_act, fuente = obtener_telemetria()
        if cpu_act is not None:
            st.markdown(f'<div style="background-color: #f1f3f4; padding: 10px; border-radius: 5px; border-left: 5px solid #003366;">Lectura actual ({fuente}): <b>CPU: {cpu_act}%</b> | <b>RAM: {ram_act}%</b></div>', unsafe_allow_html=True)
    except: pass

    col1, col2 = st.columns(2)
    u_cpu = col1.number_input("Umbral Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc)
    u_ram = col2.number_input("Umbral Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc)
    st.session_state.u_cpu_perc, st.session_state.u_ram_perc = u_cpu, u_ram

    st.subheader("📋 Monitor de Eventos en Tiempo Real")
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT fecha_registro as 'Fecha', nodo_nombre as 'Nodo', uso_cpu as 'CPU %', uso_ram as 'RAM %' FROM monitoreo_nodos ORDER BY fecha_registro DESC LIMIT 20", conn)
        conn.close()

        if not df.empty:
            df['Alerta'] = df.apply(lambda r: "CRÍTICO" if r['CPU %'] >= u_cpu or r['RAM %'] >= u_ram else "NORMAL", axis=1)
            st.dataframe(
                df,
                column_config={
                    "CPU %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
                    "RAM %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
                    "Alerta": st.column_config.StatusColumn(mapping={"CRÍTICO": "red", "NORMAL": "green"})
                },
                use_container_width=True, hide_index=True
            )
    except Exception as e:
        st.error(f"Error: {e}")