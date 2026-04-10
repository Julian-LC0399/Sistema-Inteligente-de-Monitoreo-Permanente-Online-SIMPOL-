import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    """Refresco automático cada 5s para sincronía total con agente.py"""
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
        
        st.markdown(f"""
            <p style='color: black; font-weight: bold; font-size: 0.9rem;'>
                ⏱️ Rango de Monitoreo: {h_inicio} ➔ {h_fin}
            </p>
        """, unsafe_allow_html=True)

        # 2. CÁLCULO TÉCNICO
        n = len(valores_y)
        tendencia = (valores_y[-1] - valores_y[0]) / (n - 1) if n > 1 else 0
        puntos_futuros = dias_p * 17280 
        valor_futuro = max(0, min(100, valores_y[-1] + (tendencia * puntos_futuros)))

        # 3. MÉTRICAS Y VEREDICTO
        fecha_meta = datetime.now() + timedelta(days=dias_p)
        veredicto = "ALERTA" if valor_futuro >= 90 else ("PRECAUCIÓN" if valor_futuro >= 75 else "ESTABLE")

        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric("Valor Actual", f"{valores_y[-1]:.2f}%")
            c2.metric(f"Proyección ({dias_p} d)", f"{valor_futuro:.2f}%", 
                      delta=f"{valor_futuro - valores_y[-1]:.2f}%", delta_color="inverse")
            
            if veredicto == "ALERTA":
                st.error(f"🚨 **{veredicto}:** Agotamiento previsto el {fecha_meta.strftime('%d/%m/%Y')}")
            else:
                st.success(f"✅ **{veredicto}:** Estado previsto el {fecha_meta.strftime('%d/%m/%Y')}")

        # 4. TABLA TÉCNICA Y ESTILOS (INCLUYE EL TOAST PERSONALIZADO)
        st.divider()
        st.markdown("### 📋 Registro de Telemetría (Últimos registros primero)")
        
        st.markdown("""
            <style>
                [data-testid="stTable"] td { color: black !important; border: 1px solid #eee !important; text-align: center; }
                [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; text-align: center; }
                [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) { display: none !important; }
                
                /* ESTILO PARA EL BOTÓN DE GUARDAR */
                div.stButton > button {
                    background-color: #003366 !important;
                    color: white !important;
                    border: 2px solid #003366 !important;
                    font-weight: bold !important;
                }
                
                /* PERSONALIZACIÓN DEL TOAST (ALERTA DE GUARDADO) */
                [data-testid="stToast"] {
                    background-color: #003366 !important;
                    color: white !important;
                    border: 1px solid #FFD700 !important; /* Borde dorado para resaltar */
                }
                [data-testid="stToast"] p {
                    color: white !important;
                    font-weight: bold !important;
                }
            </style>
        """, unsafe_allow_html=True)

        datos_recientes = sorted(datos_raw, key=lambda x: x['fecha_registro'], reverse=True)
        tabla_out = []
        for d in datos_recientes[:15]:
            h_formateada = d['fecha_registro'].strftime('%H:%M:%S')
            tabla_out.append({
                "HORA": h_formateada,
                "USO CPU": f"{d.get('uso_cpu')}%",
                "USO RAM": f"{d.get('uso_ram')}%",
                "ESTADO": "OK"
            })
        
        st.table(tabla_out)
        return valor_futuro, valores_y[-1], veredicto

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

    usuario_actual = st.session_state.get('usuario', 'Sistema-CSU')
    v_futuro, v_actual, veredicto = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        if st.button("💾 REGISTRAR PROYECCIÓN EN BASE DE DATOS", use_container_width=True):
            fecha_meta_dt = datetime.now() + timedelta(days=dias_p)
            exito = registrar_proyeccion(
                metrica.upper(), 
                v_actual, 
                v_futuro, 
                fecha_meta_dt.date(), 
                dias_p, 
                veredicto, 
                usuario_actual
            )
            if exito: 
                # Este toast ahora saldrá en azul con letras blancas gracias al CSS de arriba
                st.toast(f"✅ Proyección registrada por {usuario_actual}")