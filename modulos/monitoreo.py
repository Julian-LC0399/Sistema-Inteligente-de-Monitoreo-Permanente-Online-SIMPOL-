import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos instantáneos (Para los indicadores visuales)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # Header de información institucional
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">AGENTE DE CAPTURA ACTIVO</div>
                <h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Nodo CSU</h3>
                <p style="margin:0; color:#666; font-size:13px;"><b>Origen:</b> {fuente_msg} | <b>Analista en sesión:</b> {user_actual}<br><b>Sincronización:</b> {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        # Un indicador de estado que cambia de color según la carga
        color_alert = "#28a745" if cpu_val < 80 else "#dc3545"
        st.markdown(f"""
            <div style="background-color:{color_alert}; color:white; padding:15px; border-radius:10px; text-align:center;">
                <h2 style="margin:0;">{cpu_val}%</h2>
                <p style="margin:0; font-size:12px;">CARGA DE CPU</p>
            </div>
        """, unsafe_allow_html=True)

    st.write("---")
    
    # Métricas principales
    m1, m2, m3 = st.columns(3)
    m1.metric("USO DE CPU", f"{cpu_val}%")
    m2.metric("MEMORIA RAM", f"{ram_val}%")
    m3.metric("ESTADO LÓGICO", "OPERATIVO" if cpu_val < 90 else "CRÍTICO")

    # 2. Lógica de CONSULTA (Leemos lo que el Agente de Captura está guardando)
    
    try:
        conn = conectar_bd()
        # SE ELIMINÓ EL INSERT: Ahora solo consultamos el historial generado por el agente
        df_m = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 50", conn)
        conn.close()

        if not df_m.empty:
            df_m = df_m.sort_values("fecha_registro") 
            
            fig = go.Figure()
            # Línea de CPU
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], 
                y=df_m["uso_cpu"], 
                mode='lines',
                name='Carga CPU %',
                line=dict(color='#003366', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 51, 102, 0.1)'
            ))
            
            # Línea de RAM
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], 
                y=df_m["uso_ram"], 
                mode='lines',
                name='Carga RAM %',
                line=dict(color='#28a745', width=2, dash='dot')
            ))

            fig.update_layout(
                title="Tendencia de Telemetría (Datos en Tiempo Real)",
                xaxis_title="Registro Cronológico",
                yaxis_title="Porcentaje de Uso",
                yaxis=dict(range=[0, 105]),
                plot_bgcolor="white",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=40, b=10),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Esperando datos del Agente de Captura...")

    except Exception as e:
        st.error(f"Error al consultar el historial: {e}")
    
    # 3. Ciclo de refresco de pantalla
    time.sleep(5)
    st.rerun()