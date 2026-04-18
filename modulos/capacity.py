import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.info("🔄 Sincronizando datos... Se requieren al menos 5 registros para proyectar.")
        return None, None, None

    try:
        # 1. PREPARACIÓN DE DATOS (Nativo sin Pandas)
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores_y = [float(d.get(metrica, 0)) for d in datos_grafica]

        st.subheader(f"Tendencia Temporal: {metrica.replace('uso_', '').upper()}")
        
        # Corrección para servidor: Diccionario de datos
        st.area_chart({metrica.upper(): valores_y}, height=250)
        
        # 2. CÁLCULO DE PROYECCIÓN (Matemática nativa)
        v_actual = valores_y[-1]
        v_inicial = valores_y[0]
        delta_total = (v_actual - v_inicial) / len(valores_y)
        v_futuro = max(0.0, min(100.0, v_actual + (delta_total * dias_p)))

        # 3. VEREDICTO
        if v_futuro > 85:
            veredicto = "CRÍTICO: Riesgo de agotamiento"
        elif v_futuro > 65:
            veredicto = "ADVERTENCIA: Crecimiento sostenido"
        else:
            veredicto = "ESTABLE: Capacidad suficiente"

        return round(v_futuro, 2), round(v_actual, 2), veredicto

    except Exception as e:
        st.error(f"Error en proyección: {e}")
        return None, None, None

def mostrar_pantalla():
    st.markdown("""
        <style>
            .stButton > button { background-color: #003366 !important; color: white !important; font-weight: bold !important; }
            .stButton > button:hover { border: 2px solid #ffcc00 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='color:#003366;'>📊 Análisis de Capacidad</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        col_ctrl1, col_ctrl2 = st.columns(2)
        dias_p = col_ctrl1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col_ctrl2.selectbox("Recurso:", ["uso_cpu", "uso_ram"],
                                     format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    user_id_actual = st.session_state.get('user_id', 1)
    v_futuro, v_actual, veredicto = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("VALOR ACTUAL", f"{v_actual}%")
        c2.metric("PROYECCIÓN", f"{v_futuro}%", delta=f"{v_futuro-v_actual}%", delta_color="inverse")
        c3.warning(f"ESTADO: {veredicto}")

        if st.button("💾 GUARDAR INFORME DE CAPACIDAD", use_container_width=True):
            registrar_proyeccion(metrica, v_actual, v_futuro, dias_p, veredicto, user_id_actual)
            st.success("Análisis guardado en base de datos.")