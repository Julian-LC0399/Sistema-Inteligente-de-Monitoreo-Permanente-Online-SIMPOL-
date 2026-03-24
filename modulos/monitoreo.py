import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh


def mostrar_pantalla(user_actual):
    # 1. Sincronización: Refresco automático cada 15 segundos
    st_autorefresh(interval=15000, key="monitoreo_nodos_refresh")

    st.markdown(
        "<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>",
        unsafe_allow_html=True,
    )

    # 2. Captura de datos instantáneos (Sensores actuales)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # Panel de indicadores superiores
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(
            f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">CAPTURA EN VIVO</div>
                <h3 style="margin:0; color:#003366;">Infraestructura de Red - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Última lectura: {fecha_actual} | Origen: {fuente_msg}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with col_status:
        c1, c2 = st.columns(2)
        c1.metric("CPU", f"{cpu_val}%")
        c2.metric("RAM", f"{ram_val}%")

    st.divider()

    # 3. Visualización de Tendencia Histórica (Tabla monitoreo_nodos)
    try:
        conn = conectar_bd()
        # Consulta a la tabla especificada por el usuario
        query = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_nodos ORDER BY id DESC LIMIT 20"
        df_m = pd.read_sql(query, conn)
        conn.close()

        if not df_m.empty:
            # Ordenar para que el gráfico fluya de izquierda a derecha (tiempo ascendente)
            df_m = df_m.sort_values("fecha_registro")

            fig = go.Figure()

            # Traza para CPU
            fig.add_trace(
                go.Scatter(
                    x=df_m["fecha_registro"],
                    y=df_m["uso_cpu"],
                    mode="lines+markers",
                    name="Carga CPU %",
                    line=dict(color="#003366", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(0, 51, 102, 0.1)",
                )
            )

            # Traza para RAM
            fig.add_trace(
                go.Scatter(
                    x=df_m["fecha_registro"],
                    y=df_m["uso_ram"],
                    mode="lines+markers",
                    name="Carga RAM %",
                    line=dict(color="#28a745", width=2, dash="dot"),
                )
            )

            fig.update_layout(
                title="Análisis de Tendencia Reciente",
                xaxis_title="Registro de Tiempo",
                yaxis_title="Porcentaje de Carga",
                yaxis=dict(range=[0, 105]),
                plot_bgcolor="white",
                hovermode="x unified",
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                margin=dict(l=10, r=10, t=50, b=10),
                height=450,
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info(
                "💡 No se encontraron registros en la tabla 'monitoreo_nodos'. Verifique que el agente de base de datos esté activo."
            )

    except Exception as e:
        st.error(f"⚠️ Error de base de datos (monitoreo_nodos): {e}")

    # 4. Panel de sugerencias proactivas
    with st.expander("Ver recomendaciones de optimización"):
        if cpu_val > 80:
            st.warning(
                "Se detecta una carga alta de CPU. Considere revisar los procesos de PRTG o cierres de tareas pendientes."
            )
        else:
            st.success(
                "El rendimiento del procesador se mantiene dentro de los parámetros estables."
            )
