import streamlit as st
from database import obtener_datos_historicos
from datetime import datetime, timedelta

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos nativa (Lista de diccionarios)
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.warning("⚠️ Se requieren al menos 5 registros históricos para generar un análisis de tendencia.")
        return

    # 2. Configuración de la Proyección
    with st.container(border=True):
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar hacia el futuro:", 1, 30, 7)
        metrica = col2.selectbox("Métrica a analizar:", ["uso_cpu", "uso_ram"], 
                                format_func=lambda x: x.replace("_", " ").upper())

    # --- 3. LÓGICA MATEMÁTICA NATIVA (Sin Numpy ni Pandas) ---
    try:
        # Extraemos solo los valores numéricos de la métrica seleccionada
        valores = [d[metrica] for d in datos_raw]
        n = len(valores)
        
        # Cálculo de tendencia: Diferencia entre el último y el primer registro
        # Esto nos da el crecimiento total en el periodo capturado
        cambio_total = valores[-1] - valores[0]
        tendencia_por_registro = cambio_total / n
        
        # Estimación: Asumimos que el agente registra datos cada hora (24 al día)
        puntos_a_proyectar = dias_proyectar * 24
        valor_estimado_futuro = valores[-1] + (tendencia_por_registro * puntos_a_proyectar)
        
        # Aseguramos que el porcentaje se mantenga en límites reales (0-100)
        valor_estimado_futuro = max(0, min(100, valor_estimado_futuro))

        # --- 4. VISUALIZACIÓN NATIVA (st.line_chart) ---
        st.markdown(f"### 📊 Histórico y Tendencia: {metrica.upper()}")
        
        # Preparamos los datos para el gráfico nativo de Streamlit
        # st.line_chart es extremadamente rápido y no depende de Plotly
        chart_data = {
            "Carga Real %": valores
        }
        st.line_chart(chart_data, height=300)

        # --- 5. CONCLUSIÓN Y FECHA ESTIMADA ---
        fecha_meta = (datetime.now() + timedelta(days=dias_proyectar)).strftime('%d/%m/%Y')
        
        with st.expander("📝 Interpretación del Análisis (Modo Nativo)", expanded=True):
            st.write(f"Basado en el comportamiento de los últimos **{n} registros**:")
            
            if valor_estimado_futuro > 90:
                st.error(f"🚨 **ALERTA DE CAPACIDAD:** Se estima una saturación del **{valor_estimado_futuro:.1f}%** para el {fecha_meta}.")
                st.info("Sugerencia: Revisar procesos en segundo plano o ampliar recursos de hardware.")
            elif valor_estimado_futuro > 75:
                st.warning(f"⚠️ **PRECAUCIÓN:** El uso proyectado asciende al **{valor_estimado_futuro:.1f}%** en la fecha indicada.")
            else:
                st.success(f"✅ **ESTABILIDAD:** Los recursos proyectan un uso saludable del **{valor_estimado_futuro:.1f}%** para la próxima semana.")

        # 6. Tabla de soporte (Datos Crudos)
        with st.expander("📄 Ver registros históricos detallados"):
            # Mostramos los últimos 15 de forma elegante
            st.table(datos_raw[:15])

    except Exception as e:
        st.error(f"Error en el cálculo de capacidad: {e}")