import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""<div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;"><div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">DISPOSITIVO ACTIVO</div><h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Nodo CSU</h3><p style="margin:0; color:#666; font-size:13px;"><b>Origen:</b> {fuente_msg} | <b>ID Sensor:</b> 2094<br><b>Última Lectura:</b> {fecha_actual}</p></div>""", unsafe_allow_html=True)
    with col_status:
        st.write(f"**Uptime:** 14d 06h 22m")
        st.progress(cpu_val / 100, text=f"Carga CPU: {cpu_val}%")

    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("USO DE CPU", f"{cpu_val}%", delta=fuente_msg)
    m2.metric("MEMORIA RAM", f"{ram_val}%")
    m3.metric("ESTADO LÓGICO", "OPERATIVO")
    m4.metric("SESIONES CSU", "12 Activas")

    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)", (datetime.now(), user_actual, cpu_val, ram_val, "ESTABLE"))
        conn.commit()
        df_m = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
        conn.close()
        if not df_m.empty:
            df_m = df_m.sort_values("fecha_registro")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_m["fecha_registro"], y=df_m["uso_cpu"], mode='lines', name='CPU %', line=dict(color='#003366', width=3), fill='tozeroy'))
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)
    except: st.error("Error en telemetría.")
    
    time.sleep(5)
    st.rerun()