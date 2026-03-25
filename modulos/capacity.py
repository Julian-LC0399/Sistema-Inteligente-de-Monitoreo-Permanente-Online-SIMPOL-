import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import obtener_datos_historicos

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #333;'>Análisis predictivo basado en regresión polinómica.</p>", unsafe_allow_html=True)

    # 1. Obtención de datos (Llamada a la tabla 'monitoreo' en database.py)
    df = obtener_datos_historicos()

    if df.empty:
        st.warning("⚠️ No hay suficientes datos en 'monitoreo' para realizar una predicción.")
        return

    # 2. Configuración del análisis
    with st.container(border=True):
        st.markdown("<b style='color: #003366;'>Parámetros de Predicción</b>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar hacia el futuro:", 1, 30, 7)
        metrica = col2.selectbox("Métrica a analizar:", ["uso_cpu", "uso_ram"])

    # 3. Lógica Matemática
    try:
        df['timestamp'] = pd.to_datetime(df['fecha_registro']).map(pd.Timestamp.timestamp)
        x = df['timestamp'].values
        y = df[metrica].values

        modelo = np.poly1d(np.polyfit(x, y, 2))

        ultima_fecha = x[-1]
        futuro_x = np.linspace(x[0], ultima_fecha + (dias_proyectar * 86400), 100)
        futuro_y = modelo(futuro_x)

        # 4. Visualización
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pd.to_datetime(x, unit='s'), y=y, name='Datos Reales', mode='markers', marker=dict(color='#003366')))
        fig.add_trace(go.Scatter(x=pd.to_datetime(futuro_x, unit='s'), y=futuro_y, name='Tendencia Predictiva', line=dict(color='#e74c3c', width=3, dash='dash')))

        fig.update_layout(
            title=f"Predicción de {metrica.upper()} - CSU Principal",
            xaxis_title="Tiempo",
            yaxis_title="Porcentaje %",
            yaxis=dict(range=[0, 110]),
            plot_bgcolor="white"
        )

        st.plotly_chart(fig, use_container_width=True)

        # 5. Conclusión
        valor_final = futuro_y[-1]
        if valor_final > 90:
            st.error(f"🚨 ALERTA CRÍTICA: Se estima un uso del {valor_final:.2f}% en {dias_proyectar} días.")
        elif valor_final > 75:
            st.warning(f"⚠️ PRECAUCIÓN: Tendencia creciente hacia el {valor_final:.2f}%.")
        else:
            st.success(f"✅ ESTABLE: Proyección controlada ({valor_final:.2f}%).")

    except Exception as e:
        st.error(f"Error en el cálculo: {e}")