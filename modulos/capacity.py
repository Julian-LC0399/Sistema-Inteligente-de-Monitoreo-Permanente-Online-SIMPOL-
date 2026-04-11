import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    """Refresco automático sincronizado con los datos del agente"""
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 2:
        st.info("🔄 Sincronizando con el flujo del agente... Esperando datos.")
        return None, None, None

    try:
        # 1. PREPARACIÓN DE DATOS
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores_y = [float(d.get(metrica, 0)) for d in datos_grafica]
        h_inicio = datos_grafica[0]['fecha_registro'].strftime('%H:%M:%S')
        h_fin = datos_grafica[-1]['fecha_registro'].strftime('%H:%M:%S')

        st.subheader(f"Tendencia Temporal: {metrica.upper()}")
        st.area_chart(valores_y, height=250, use_container_width=True)
        
        # 2. CÁLCULO DE PROYECCIÓN LINEAL SIMPLE
        v_actual = valores_y[-1]
        factor_crecimiento = (dias_p * 0.01) # Simulación de tendencia
        v_futuro = round(v_actual * (1 + factor_crecimiento), 2)
        
        # Veredicto de capacidad
        if v_futuro < 70: veredicto = "ESTABLE"
        elif v_futuro < 90: veredicto = "PRECAUCIÓN"
        else: veredicto = "ALERTA"

        # 3. TABLA DE RESULTADOS
        tabla_out = {
            "Métrica": [metrica.upper()],
            "Valor Actual": [f"{v_actual}%"],
            "Proyección (+{0} días)".format(dias_p): [f"{v_futuro}%"],
            "Veredicto": [veredicto]
        }
        st.table(tabla_out)
        return v_futuro, v_actual, veredicto

    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None, None, None

def mostrar_pantalla():
    st.markdown("<h1 style='color: #003366;'>📈 Capacity Planning</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        col_ctrl1, col_ctrl2 = st.columns(2)
        dias_p = col_ctrl1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col_ctrl2.selectbox("Recurso a analizar:", ["uso_cpu", "uso_ram"],
                                     format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    # Obtenemos el ID del usuario de la sesión para la FK (Foreign Key)
    # Si no existe, usamos 1 (admin) por defecto para evitar errores
    user_id_actual = st.session_state.get('user_id', 1)
    
    v_futuro, v_actual, veredicto = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        if st.button("💾 REGISTRAR PROYECCIÓN EN BASE DE DATOS", use_container_width=True):
            fecha_meta_dt = datetime.now() + timedelta(days=dias_p)
            
            # CAMBIO CLAVE: Enviamos user_id (INT) en lugar de nombre_usuario (STR)
            exito = registrar_proyeccion(
                metrica.upper(),
                v_actual,
                v_futuro,
                fecha_meta_dt.date(),
                dias_p,
                veredicto,
                user_id_actual 
            )
            if exito:
                st.success(f"✅ Proyección guardada bajo el ID de analista: {user_id_actual}")
            else:
                st.error("❌ Error al guardar: Verifique la conexión o estructura de la tabla 'proyecciones'.")