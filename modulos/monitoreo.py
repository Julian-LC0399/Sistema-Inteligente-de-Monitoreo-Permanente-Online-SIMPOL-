import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from database import conectar_bd

def mostrar_pantalla(user_actual):
    # Título con estilo original
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
    
    # --- 1. OBTENCIÓN DE DATOS DESDE LA BASE DE DATOS (SENSOR 2094) ---
    try:
        conn = conectar_bd()
        query_last = "SELECT uso_cpu, uso_ram, fecha_registro FROM monitoreo_30_nodos WHERE nodo_nombre = 'SISTEMA_AUTO' ORDER BY id DESC LIMIT 1"
        df_last = pd.read_sql(query_last, conn)
        
        if not df_last.empty:
            cpu_val = df_last['uso_cpu'].iloc[0]
            ram_val = df_last['uso_ram'].iloc[0]
            fecha_actual = df_last['fecha_registro'].iloc[0].strftime("%H:%M:%S")
            fuente_msg = "Sincronizado con PRTG"
        else:
            cpu_val, ram_val, fecha_actual, fuente_msg = 0, 0, "--:--:--", "Esperando Agente..."
            
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        cpu_val, ram_val, fecha_actual, fuente_msg = 0, 0, "Error", "Desconectado"

    # --- 2. HEADER CON USER ACTUAL Y SEMÁFORO ---
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">SESIÓN ACTIVA: {user_actual.upper()}</div>
                <h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Nodo CSU</h3>
                <p style="margin:0; color:#666; font-size:13px;"><b>Sensor PRTG:</b> 2094 | <b>Última Lectura:</b> {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        color_alert = "#28a745" if cpu_val < 75 else ("#ffc107" if cpu_val < 90 else "#dc3545")
        st.markdown(f"""
            <div style="background-color:{color_alert}; color:white; padding:15px; border-radius:10px; text-align:center;">
                <h2 style="margin:0;">{cpu_val}%</h2>
                <p style="margin:0; font-size:12px;">CARGA ACTUAL</p>
            </div>
        """, unsafe_allow_html=True)

    st.write("---")

    # --- 3. MÉTRICAS TRIPLES ---
    m1, m2, m3 = st.columns(3)
    m1.metric("CARGA CPU", f"{cpu_val}%")
    m2.metric("USO RAM", f"{ram_val}%")
    m3.metric("OPERADOR", user_actual)

    # --- 4. GRÁFICO DE TENDENCIA (ORIGINAL CON FILL) ---
    try:
        query_hist = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos WHERE nodo_nombre = 'SISTEMA_AUTO' ORDER BY id DESC LIMIT 50"
        df_m = pd.read_sql(query_hist, conn)
        conn.close()

        if not df_m.empty:
            df_m = df_m.sort_values("fecha_registro")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], y=df_m["uso_cpu"], 
                mode='lines', name='CPU %',
                line=dict(color='#003366', width=3),
                fill='tozeroy', fillcolor='rgba(0, 51, 102, 0.1)'
            ))
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], y=df_m["uso_ram"], 
                mode='lines', name='RAM %',
                line=dict(color='#28a745', width=2, dash='dot')
            ))

            fig.update_layout(
                title="Historial Sincronizado (PRTG -> DB)",
                yaxis=dict(range=[0, 105]),
                plot_bgcolor="white",
                height=400,
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except:
        pass
    
    time.sleep(5)
    st.rerun()