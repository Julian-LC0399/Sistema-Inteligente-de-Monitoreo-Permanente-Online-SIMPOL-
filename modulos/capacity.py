import streamlit as st
import plotly.graph_objects as go
from database import obtener_datos_historicos # Asumiendo que tienes esta función

def mostrar_pantalla():
    st.title("📈 Capacity Planning (IA Predictiva)")
    st.markdown("""
        Este módulo utiliza **Regresión Polinómica** para proyectar el crecimiento 
        de los recursos del servidor en los próximos 30, 60 y 90 días.
    """)

    try:
        # IMPORTACIÓN LOCAL: Solo carga NumPy cuando se entra a esta pantalla
        import numpy as np
        
        # Simulación de datos (Sustituir por llamada a database.py)
        # dias = np.array([1, 2, 3, 4, 5, 6, 7])
        # carga = np.array([45, 48, 50, 49, 52, 55, 58])
        
        # 1. Obtención de datos
        datos = obtener_datos_historicos(limit=30)
        if not datos:
            st.warning("No hay suficientes datos históricos para realizar la proyección.")
            return

        # Ejemplo de lógica de cálculo
        x = np.array([d[0] for d in datos]) # Días
        y = np.array([d[1] for d in datos]) # % Carga
        
        # 2. Cálculo de tendencia (Polinomio de grado 2)
        modelo = np.polyfit(x, y, 2)
        p = np.poly1d(modelo)
        
        # 3. Proyección a futuro
        x_futuro = np.linspace(max(x), max(x) + 30, 10)
        y_futuro = p(x_futuro)

        # 4. Visualización con Plotly
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, name="Histórico", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=x_futuro, y=y_futuro, name="Proyección 30d", line=dict(dash='dash', color='red')))
        
        fig.update_layout(title="Predicción de Carga de CPU", xaxis_title="Días", yaxis_title="% Utilización")
        st.plotly_chart(fig, use_container_width=True)

        # 5. Diagnóstico
        if y_futuro[-1] > 85:
            st.error(f"⚠️ ALERTA: Según la tendencia, el servidor superará el 85% de carga en 30 días.")
        else:
            st.success("✅ La capacidad proyectada se mantiene dentro de los límites operativos.")

    except ImportError:
        st.error("❌ Error: NumPy no está disponible o es incompatible con la arquitectura del servidor.")
        st.info("Por favor, verifica la instalación de la versión 1.26.4 como Administrador.")
    except Exception as e:
        st.error(f"Ocurrió un error en el cálculo: {e}")