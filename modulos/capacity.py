import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.info("🔄 Sincronizando datos históricos para proyección...")
        return None, None, None

    try:
        # 1. PREPARACIÓN DE DATOS PUROS
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores_y = [float(d.get(metrica, 0)) for d in datos_grafica]
        
        # 2. LÓGICA DE PROYECCIÓN (Matemática nativa)
        v_actual = valores_y[-1]
        delta = (v_actual - valores_y[0]) / len(valores_y)
        v_futuro = round(max(0.0, min(100.0, v_actual + (delta * dias_p))), 2)

        # 3. CONSTRUCCIÓN DEL GRÁFICO SVG PROFESIONAL
        def generar_svg_capacidad(historico, proyectado, color):
            ancho = 500
            alto = 150
            total_puntos = len(historico) + 1
            paso_x = ancho / total_puntos
            
            # Dibujar área de historial
            puntos_area = f"0,{alto} "
            puntos_linea = ""
            for i, v in enumerate(historico):
                x = i * paso_x
                y = alto - (v * alto / 100)
                puntos_area += f"{x},{y} "
                puntos_linea += f"{x},{y} "
            
            # Punto proyectado
            x_f = (len(historico)) * paso_x
            y_f = alto - (proyectado * alto / 100)
            puntos_area += f"{x_f},{y_f} {x_f},{alto}"
            
            return f"""
            <svg width="100%" height="180" viewBox="0 0 500 160" preserveAspectRatio="none">
                <polygon points="{puntos_area}" fill="{color}" fill-opacity="0.2" />
                <polyline points="{puntos_linea}" fill="none" stroke="{color}" stroke-width="3" />
                <line x1="{(len(historico)-1)*paso_x}" y1="{alto - (historico[-1]*alto/100)}" 
                      x2="{x_f}" y2="{y_f}" stroke="{color}" stroke-width="3" stroke-dasharray="5,5" />
                <circle cx="{x_f}" cy="{y_f}" r="5" fill="{color}" />
                <text x="{x_f - 40}" y="{y_f - 10}" font-family="Arial" font-size="12" fill="{color}" font-weight="bold">{proyectado}%</text>
            </svg>
            """

        color_metrica = "#003366" if "ram" in metrica else "#dc3545"
        st.markdown(f"### 📈 Proyección de {metrica.replace('uso_', '').upper()}")
        st.markdown(generar_svg_capacidad(valores_y, v_futuro, color_metrica), unsafe_allow_html=True)

        veredicto = "ESTABLE"
        if v_futuro > 85: veredicto = "CRÍTICO"
        elif v_futuro > 65: veredicto = "ADVERTENCIA"

        return v_futuro, round(v_actual, 2), veredicto

    except Exception as e:
        st.error(f"Error en motor gráfico: {e}")
        return None, None, None

def mostrar_pantalla():
    st.markdown("<h1 style='color:#003366;'>📊 Análisis de Capacidad</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        dias_p = c1.slider("Días a proyectar:", 1, 30, 7)
        metrica = c2.selectbox("Recurso:", ["uso_cpu", "uso_ram"])

    v_futuro, v_actual, veredicto = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("VALOR ACTUAL", f"{v_actual}%")
        col2.metric("PROYECCIÓN", f"{v_futuro}%")
        
        # Estilo de alerta para el banco
        if "CRÍTICO" in veredicto:
            col3.error(f"ESTADO: {veredicto}")
        elif "ADVERTENCIA" in veredicto:
            col3.warning(f"ESTADO: {veredicto}")
        else:
            col3.success(f"ESTADO: {veredicto}")

        # LÓGICA DE GUARDADO (Se mantiene intacta)
        if st.button("💾 GUARDAR INFORME DE CAPACIDAD"):
            user_id = st.session_state.get('user_id', 1)
            exito = registrar_proyeccion(user_id, metrica, v_actual, v_futuro, veredicto)
            if exito:
                st.success("Análisis guardado exitosamente en el servidor.")
            else:
                st.error("Error al persistir los datos en la base de datos.")