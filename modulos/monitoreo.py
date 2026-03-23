import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path
from streamlit_autorefresh import st_autorefresh

def mostrar_pantalla(user_actual):
    # Configurar refresco automático cada 15 segundos (15000ms)
    st_autorefresh(interval=15000, key="monitoreo_refresh")
    
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos instantáneos
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # Panel de información de cabecera
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">AGENTE DE CAPTURA ACTIVO</div>
                <h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Última sincronización: {fecha_actual} ({fuente_msg})</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col_status:
        # Indicadores rápidos (Métricas)
        c1, c2 = st.columns(2)
        c1.metric("CPU", f"{cpu_val}%")
        c2.metric("RAM", f"{ram_val}%")

    st.divider()

    # 2. Gráfico de tendencia histórica reciente
    try:
        conn = conectar_bd()
        query = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_log ORDER BY id DESC LIMIT 20"
        df_m = pd.read_sql(query, conn)
        conn.close()

        if not df_m.empty:
            df_m = df_m.sort_values("fecha_registro")
            
            fig = go.Figure()
            # Línea de CPU
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], y=df_m["uso_cpu"],
                mode='lines+markers', name='Carga CPU %',
                line=dict(color='#003366', width=3),
                fill='tozeroy', fillcolor='rgba(0, 51, 102, 0.1)'
            ))
            # Línea de RAM
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], y=df_m["uso_ram"],
                mode='lines', name='Carga RAM %',
                line=dict(color='#28a745', width=2, dash='dot')
            ))

            fig.update_layout(
                title="Tendencia de Telemetría (Últimas 20 lecturas)",
                xaxis_title="Tiempo", yaxis_title="Uso %",
                yaxis=dict(range=[0, 105]),
                margin=dict(l=10, r=10, t=40, b=10),
                height=400, template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay datos históricos suficientes para graficar.")
    except Exception as e:
        st.error(f"Error al conectar con el histórico: {e}")