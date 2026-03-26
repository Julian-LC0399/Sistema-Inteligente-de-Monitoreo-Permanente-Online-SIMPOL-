import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import obtener_datos_historicos

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos
    df = obtener_datos_historicos()

    if df.empty or len(df) < 5:
        st.warning("⚠️ Se requieren al menos 5 registros en 'monitoreo' para generar una tendencia confiable.")
        return

    # 2. Configuración
    with st.container(border=True):
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col2.selectbox("Métrica:", ["uso_cpu", "uso_ram"], format_func=lambda x: x.replace("_", " ").upper())

    # 3. Lógica Matemática Mejorada
    try:
        # Convertimos fechas a números para la regresión
        df['timestamp'] = pd.to_datetime(df['fecha_registro']).map(pd.Timestamp.timestamp)
        x_real = df['timestamp'].values
        y_real = df[metrica].values

        # Grado 2 para capturar curvas de crecimiento/descenso
        modelo = np.poly1d(np.polyfit(x_real, y_real, 2))

        # --- CAMBIO CLAVE: Generar solo el tramo futuro ---
        ultima_fecha_unix = x_real[-1]
        # Creamos puntos desde el ÚLTIMO dato real hasta N días después
        x_futuro_unix = np.linspace(ultima_fecha_unix, ultima_fecha_unix + (dias_proyectar * 86400), 50)
        y_futuro = modelo(x_futuro_unix)

        # 4. Visualización Profesional
        fig = go.Figure()

        # Datos Históricos (Puntos azules)
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(x_real, unit='s'), 
            y=y_real, 
            name='Histórico Real', 
            mode='markers', 
            marker=dict(color='#003366', size=8)
        ))

        # Línea de Predicción (Línea roja discontinua que nace del último punto)
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(x_futuro_unix, unit='s'), 
            y=y_futuro, 
            name='Proyección', 
            line=dict(color='#e74c3c', width=3, dash='dash')
        ))

        fig.update_layout(
            title=f"Análisis de Tendencia: {metrica.replace('_', ' ').upper()}",
            xaxis_title="Línea de Tiempo",
            yaxis_title="Carga del Sistema %",
            yaxis=dict(range=[0, 110], gridcolor='#eee'),
            plot_bgcolor="white",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        # 5. Panel de Conclusión Predictiva
        valor_proyectado = y_futuro[-1]
        fecha_proyectada = pd.to_datetime(x_futuro_unix[-1], unit='s').strftime('%d/%m/%Y')
        
        with st.chat_message("assistant"):
            if valor_proyectado > 90:
                st.error(f"🚨 **RIESGO DE SATURACIÓN:** Se estima un uso del **{valor_proyectado:.1f}%** para el {fecha_proyectada}.")
            elif valor_proyectado > 75:
                st.warning(f"⚠️ **ADVERTENCIA:** Tendencia al alza (**{valor_proyectado:.1f}%**) para el {fecha_proyectada}.")
            else:
                st.success(f"✅ **ESTABILIDAD:** Proyección bajo control (**{valor_proyectado:.1f}%**) para el {fecha_proyectada}.")

    except Exception as e:
        st.error(f"Error en el motor predictivo: {e}")