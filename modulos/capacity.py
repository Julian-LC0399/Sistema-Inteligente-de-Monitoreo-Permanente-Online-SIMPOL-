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
        # 1. PREPARACIÓN DE DATOS (Ordenados cronológicamente)
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores_y = [float(d.get(metrica, 0)) for d in datos_grafica]

        st.subheader(f"Tendencia Temporal: {metrica.upper()}")
        st.area_chart(valores_y, height=250, use_container_width=True)
        
        # 2. CÁLCULO DE PROYECCIÓN BASADO EN TENDENCIA REAL
        # Calculamos la diferencia entre el último y el primer valor capturado
        v_actual = valores_y[-1]
        v_inicial = valores_y[0]
        
        # Cambio total observado en el periodo actual
        delta_total = v_actual - v_inicial
        
        # Proyectamos ese cambio según los días seleccionados (ajuste de escala)
        # Esto asume que el historial (100 registros) representa una ventana de tiempo significativa
        ajuste_escala = dias_p / 2  # Factor de ponderación para la simulación
        v_futuro = v_actual + (delta_total * ajuste_escala * 0.1)
        
        # Limitar valores entre 0 y 100%
        v_futuro = max(0.0, min(100.0, v_futuro))

        # 3. DETERMINAR VEREDICTO
        if v_futuro > 90:
            veredicto = "CRÍTICO: Saturación inminente"
            color = "red"
        elif v_futuro > 75:
            veredicto = "ADVERTENCIA: Capacidad limitada"
            color = "orange"
        else:
            veredicto = "ESTABLE: Capacidad suficiente"
            color = "green"

        # Visualización de resultados
        c1, c2 = st.columns(2)
        c1.metric("Valor Actual", f"{v_actual:.1f}%")
        c2.metric("Proyección a {0} días".format(dias_p), f"{v_futuro:.1f}%", 
                  delta=f"{v_futuro - v_actual:.1f}%", delta_color="inverse")
        
        st.markdown(f"**Veredicto:** :{color}[{veredicto}]")
        
        return round(v_futuro, 2), round(v_actual, 2), veredicto

    except Exception as e:
        st.error(f"Error en cálculo de capacidad: {e}")
        return None, None, None

def mostrar_pantalla():
    """Interfaz principal del Módulo de Capacidad"""
    st.markdown("<h1 style='color:#003366;'>📊 Análisis de Capacidad (Capacity Planning)</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        col_ctrl1, col_ctrl2 = st.columns(2)
        dias_p = col_ctrl1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col_ctrl2.selectbox("Recurso a analizar:", ["uso_cpu", "uso_ram"],
                                     format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    # Obtenemos el ID del usuario de la sesión de forma segura
    user_id_actual = st.session_state.get('user_id')
    
    if user_id_actual is None:
        st.warning("⚠️ No se detectó ID de sesión. Los registros se guardarán bajo el perfil de administrador (ID: 1).")
        user_id_actual = 1

    v_futuro, v_actual, veredicto = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        if st.button("💾 REGISTRAR PROYECCIÓN EN BASE DE DATOS", use_container_width=True):
            fecha_meta_dt = datetime.now() + timedelta(days=dias_p)
            
            # Persistencia con la función corregida de database.py
            exito = registrar_proyeccion(
                metrica.upper(),
                v_actual,
                v_futuro,
                fecha_meta_dt.date(),
                dias_p,
                veredicto,
                int(user_id_actual)
            )
            
            if exito:
                st.success(f"✅ Proyección de {metrica.upper()} guardada correctamente en el historial de capacidad.")
            else:
                st.error("❌ Error al guardar en la base de datos. Verifique la conexión.")