import streamlit as st
import plotly.graph_objects as go
from database import obtener_datos_historicos
from datetime import datetime, timedelta

# --- PROTECCIÓN DE LIBRERÍAS CRÍTICAS ---
# Intentamos importar las librerías que suelen fallar en el servidor
try:
    import pandas as pd
    import numpy as np
    MODO_PREDICTIVO_ACTIVO = True
except ImportError:
    MODO_PREDICTIVO_ACTIVO = False

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    
    # 1. Verificación de infraestructura (Resiliencia)
    if not MODO_PREDICTIVO_ACTIVO:
        st.error("⚠️ El motor de predicción matemática no está disponible en este servidor.")
        st.info("""
            **Nota Técnica para el Analista:** Este módulo requiere componentes de C++ (Numpy/Pandas) que están restringidos por las políticas de seguridad del Windows Server 2019.
            \n- El monitoreo en tiempo real y las auditorías siguen funcionando.
            \n- Para ver proyecciones, ejecute SIMPOL desde una estación de trabajo con las librerías completas.
        """)
        
        # Intentamos mostrar al menos los datos históricos en una tabla simple
        datos_raw = obtener_datos_historicos()
        if datos_raw:
            st.markdown("### Histórico de Carga (Datos Crudos)")
            st.table(datos_raw[:10])
        return

    # --- 2. LÓGICA CON PANDAS/NUMPY (Solo si están disponibles) ---
    datos_bd = obtener_datos_historicos()

    # Convertimos la lista de la BD a DataFrame
    if isinstance(datos_bd, list):
        df = pd.DataFrame(datos_bd)
    else:
        df = datos_bd

    if df.empty or len(df) < 5:
        st.warning("⚠️ Se requieren al menos 5 registros históricos para generar una tendencia confiable.")
        return

    # 3. Configuración de la Proyección
    with st.container(border=True):
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar hacia el futuro:", 1, 30, 7)
        metrica = col2.selectbox("Métrica a analizar:", ["uso_cpu", "uso_ram"], 
                                format_func=lambda x: x.replace("_", " ").upper())

    try:
        # Preparación de datos para la regresión
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro'])
        df['timestamp'] = df['fecha_registro'].map(pd.Timestamp.timestamp)
        
        x_real = df['timestamp'].values
        y_real = df[metrica].values

        # Cálculo de la tendencia (Regresión Polinómica Grado 2)
        # Aquí es donde Numpy podría fallar si las DLLs no están
        z = np.polyfit(x_real, y_real, 2)
        modelo = np.poly1d(z)

        # Generar puntos futuros
        ultimo_ts = x_real[-1]
        paso_segundos = 3600 * 6 # Proyectamos cada 6 horas
        puntos_futuros = (dias_proyectar * 24) // 6
        x_futuro_unix = np.linspace(ultimo_ts, ultimo_ts + (dias_proyectar * 86400), puntos_futuros)
        y_futuro = modelo(x_futuro_unix)

        # 4. Construcción del Gráfico Plotly
        fig = go.Figure()

        # Datos Reales
        fig.add_trace(go.Scatter(
            x=df['fecha_registro'], y=y_real,
            mode='lines+markers', name='Histórico Real',
            line=dict(color='#003366', width=2)
        ))

        # Línea de Proyección
        fechas_futuras = [datetime.fromtimestamp(ts) for ts in x_futuro_unix]
        fig.add_trace(go.Scatter(
            x=fechas_futuras, y=y_futuro,
            name='Proyección de Tendencia',
            line=dict(color='#e74c3c', width=3, dash='dash')
        ))

        fig.update_layout(
            title=f"Análisis de Crecimiento: {metrica.upper()}",
            xaxis_title="Tiempo",
            yaxis_title="Porcentaje %",
            yaxis=dict(range=[0, 110]),
            plot_bgcolor="white",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        # 5. Conclusión Inteligente
        valor_final = y_futuro[-1]
        fecha_meta = fechas_futuras[-1].strftime('%d/%m/%Y')
        
        with st.expander("📝 Interpretación del Análisis", expanded=True):
            if valor_final > 90:
                st.error(f"🚨 **ALERTA DE CAPACIDAD:** La tendencia indica que el recurso podría saturarse ({valor_final:.1f}%) para el {fecha_meta}.")
            elif valor_final > 75:
                st.warning(f"⚠️ **PRECAUCIÓN:** Se prevé un incremento sostenido hasta el {valor_final:.1f}% en la fecha indicada.")
            else:
                st.success(f"✅ **ESTABILIDAD:** Los recursos proyectan un uso saludable del {valor_final:.1f}% para la próxima semana.")

    except Exception as e:
        st.error(f"Error en el cálculo matemático: {e}")