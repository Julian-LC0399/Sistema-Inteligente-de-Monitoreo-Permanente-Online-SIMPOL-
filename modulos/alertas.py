import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>🚨 Configuración de Alertas</h2>", unsafe_allow_html=True)
    
    st.info("Define los límites de tolerancia. Si se superan, se activará la alerta roja en la barra lateral.")
    
    # 1. Ajuste de Umbrales
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        # Se guarda en st.session_state para que app.py lo vea al instante
        st.session_state.u_cpu_perc = st.number_input(
            "Umbral Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc
        )
    with col_conf2:
        st.session_state.u_ram_perc = st.number_input(
            "Umbral Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc
        )

    st.divider()

    # 2. Diagnóstico de DB (Tu lógica original)
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM monitoreo_30_nodos")
        total = cursor.fetchone()[0]
        conn.close()
        with st.expander("🔍 Estado de la Base de Datos"):
            st.write(f"Registros totales: **{total}**")
    except:
        st.error("Error al diagnosticar la base de datos.")

    # 3. Historial (Tu lógica original)
    st.subheader("📋 Últimos Eventos")
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT fecha_registro, nodo_nombre, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY fecha_registro DESC LIMIT 15", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("No se pudo cargar el historial.")