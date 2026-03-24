import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import obtener_datos_historicos


def mostrar_pantalla():
    st.markdown(
        "<h2 style='color: #003366;'>📈 Planificación de Capacidad (Capacity Planning)</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #333;'>Análisis predictivo basado en regresión polinómica.</p>",
        unsafe_allow_html=True,
    )

    # 1. Obtención de datos
    df = obtener_datos_historicos()

    if df.empty:
        st.warning(
            "⚠️ No hay suficientes datos en 'monitoreo_nodos' para realizar una predicción."
        )
        return

    # 2. Configuración del análisis
    with st.container(border=True):
        st.markdown(
            "<b style='color: #003366;'>Parámetros de Predicción</b>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar hacia el futuro:", 1, 30, 7)
        metrica = col2.selectbox("Métrica a analizar:", ["uso_cpu", "uso_ram"])

    # 3. Lógica Matemática (NumPy)
    try:
        # Convertimos fechas a números para que NumPy pueda procesarlos
        df["timestamp"] = pd.to_datetime(df["fecha_registro"]).map(
            pd.Timestamp.timestamp
        )
        x = df["timestamp"].values
        y = df[metrica].values

        # Creamos el modelo (Polinomio de grado 2 para capturar curvas)
        modelo = np.poly1d(np.polyfit(x, y, 2))

        # Generamos la línea de tiempo futura
        ultima_fecha = x[-1]
        futuro_x = np.linspace(x[0], ultima_fecha + (dias_proyectar * 86400), 100)
        futuro_y = modelo(futuro_x)

        # 4. Visualización Proyectada
        fig = go.Figure()

        # Datos Reales
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(x, unit="s"),
                y=y,
                name="Datos Reales",
                mode="markers",
                marker=dict(color="#003366"),
            )
        )

        # Tendencia Predictiva
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(futuro_x, unit="s"),
                y=futuro_y,
                name="Tendencia Predictiva",
                line=dict(color="#e74c3c", width=3, dash="dash"),
            )
        )

        fig.update_layout(
            title=f"Predicción de {metrica.upper()} a {dias_proyectar} días",
            xaxis_title="Tiempo",
            yaxis_title="Porcentaje %",
            yaxis=dict(range=[0, 110]),
            plot_bgcolor="white",
        )

        st.plotly_chart(fig, use_container_width=True)

        # 5. Conclusión del Sistema
        valor_final = futuro_y[-1]
        if valor_final > 90:
            st.error(
                f"🚨 ALERTA CRÍTICA: Se estima que en {dias_proyectar} días el uso superará el 90%. Se recomienda ampliación de recursos."
            )
        elif valor_final > 75:
            st.warning(
                f"⚠️ PRECAUCIÓN: Tendencia creciente. El uso podría llegar al {valor_final:.2f}% en el periodo seleccionado."
            )
        else:
            st.success(
                f"✅ ESTABLE: La proyección a {dias_proyectar} días se mantiene bajo niveles controlados ({valor_final:.2f}%)."
            )

    except Exception as e:
        st.error(f"Error en el cálculo matemático: {e}")
