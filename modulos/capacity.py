import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    """Refresco automático sincronizado con los datos reales del agente"""
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.info("🔄 Sincronizando con el flujo del agente... Se requieren al menos 5 registros para proyectar.")
        return None, None, None

    try:
        # 1. PREPARACIÓN DE DATOS
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores_y = [float(d.get(metrica, 0)) for d in datos_grafica]

        st.subheader(f"Tendencia Temporal: {metrica.upper()}")
        st.area_chart(valores_y, height=250, use_container_width=True)
        
        # 2. CÁLCULO DE PROYECCIÓN
        v_actual = valores_y[-1]
        v_inicial = valores_y[0]
        delta_total = v_actual - v_inicial
        ajuste_escala = dias_p / 2  
        v_futuro = max(0.0, min(100.0, v_actual + (delta_total * ajuste_escala * 0.1)))

        # 3. DISEÑO DE VEREDICTO
        if v_futuro > 90:
            veredicto, icon, bg, border, text = "CRÍTICO: Saturación", "🚨", "#FFE5E5", "#FF0000", "#B71C1C"
        elif v_futuro > 75:
            veredicto, icon, bg, border, text = "ADVERTENCIA: Limitada", "⚠️", "#FFF4E5", "#FFA500", "#E65100"
        else:
            veredicto, icon, bg, border, text = "ESTABLE: Suficiente", "✅", "#E5F9E5", "#28A745", "#1B5E20"

        # Métricas principales
        c1, c2 = st.columns(2)
        c1.metric("Uso Actual", f"{v_actual:.1f}%")
        c2.metric(f"Proyección ({dias_p} días)", f"{v_futuro:.1f}%", 
                  delta=f"{v_futuro - v_actual:.1f}%", delta_color="inverse")
        
        # Tarjeta de Veredicto
        st.markdown(f"""
            <div style="background-color: {bg}; border: 2px solid {border}; padding: 15px; border-radius: 10px; text-align: center; margin-top: 10px;">
                <span style="font-size: 20px;">{icon}</span>
                <b style="color: {text}; font-size: 18px; margin-left: 10px;">{veredicto}</b>
            </div>
        """, unsafe_allow_html=True)
        
        return round(v_futuro, 2), round(v_actual, 2), veredicto

    except Exception as e:
        st.error(f"Error en análisis: {e}")
        return None, None, None

def mostrar_pantalla():
    """Interfaz con sidebar restaurado al color original"""
    
    st.markdown("""
        <style>
            /* 1. CONTENIDO PRINCIPAL (AZUL CARONÍ) */
            [data-testid="stMain"] h1, [data-testid="stMain"] h3, [data-testid="stMain"] label p {
                color: #003366 !important; font-weight: bold !important;
            }
            
            /* 2. RESTAURAR SIDEBAR (Eliminamos el color blanco forzado) */
            [data-testid="stSidebar"] label p, 
            [data-testid="stSidebar"] span {
                font-weight: normal !important;
                /* Eliminamos 'color: white' para que use el tema original */
            }
            
            /* 3. BOTÓN INSTITUCIONAL */
            div.stButton > button {
                color: #ffffff !important; 
                background-color: #003366 !important;
                border: 2px solid #003366 !important;
                font-weight: bold !important;
                border-radius: 5px !important; 
                height: 48px !important;
                transition: all 0.3s ease;
            }
            div.stButton > button:hover { 
                color: #ffcc00 !important; 
                border: 2px solid #ffcc00 !important;
                background-color: #002244 !important;
            }
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
        if st.button("💾 GUARDAR ANÁLISIS EN HISTORIAL", use_container_width=True):
            fecha_meta_dt = datetime.now() + timedelta(days=dias_p)
            exito = registrar_proyeccion(
                metrica.upper(), v_actual, v_futuro, 
                fecha_meta_dt.date(), dias_p, veredicto, int(user_id_actual)
            )
            
            if exito:
                st.toast(f"Análisis de {metrica.upper()} guardado", icon="✅")
                st.success("✅ Registro completado exitosamente.")
            else:
                st.error("❌ Error al persistir los datos.")