import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

@st.fragment(run_every=5)
def fragmento_capacidad(dias_p, metrica):
    """Refresco automático cada 5s para sincronía total con agente.py"""
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 2:
        st.info("🔄 Sincronizando con el flujo del agente...")
        return None, None

    try:
        # 1. DATOS PARA GRÁFICA (Orden cronológico)
        datos_grafica = sorted(datos_raw, key=lambda x: x['fecha_registro'])
        valores = [float(d.get(metrica, 0)) for d in datos_grafica]
        
        st.subheader(f"Tendencia: {metrica.upper()}")
        st.line_chart(valores, height=250)

        # 2. CÁLCULO TÉCNICO (1 registro/5s = 17,280 registros/día)
        n = len(valores)
        tendencia = (valores[-1] - valores[0]) / (n - 1) if n > 1 else 0
        puntos_futuros = dias_p * 17280 
        valor_futuro = max(0, min(100, valores[-1] + (tendencia * puntos_futuros)))

        # 3. MÉTRICAS Y VEREDICTO
        fecha_meta = datetime.now() + timedelta(days=dias_p)
        veredicto = "ALERTA" if valor_futuro >= 90 else ("PRECAUCIÓN" if valor_futuro >= 75 else "ESTABLE")

        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric("Valor Actual", f"{valores[-1]:.2f}%")
            c2.metric(f"Proyección ({dias_p} d)", f"{valor_futuro:.2f}%", 
                      delta=f"{valor_futuro - valores[-1]:.2f}%", delta_color="inverse")
            
            if veredicto == "ALERTA":
                st.error(f"🚨 **{veredicto}:** Agotamiento previsto el {fecha_meta.strftime('%d/%m/%Y')}")
            else:
                st.success(f"✅ **{veredicto}:** Estado previsto el {fecha_meta.strftime('%d/%m/%Y')}")

        # 4. TABLA TÉCNICA (Estilos de alertas.py y orden inverso)
        st.divider()
        st.markdown("### 📋 Registro de Telemetría (Sincronía 5s)")
        
        st.markdown("""
            <style>
                [data-testid="stTable"] td { 
                    color: black !important; 
                    border: 1px solid #eee !important; 
                    font-weight: 500; 
                    text-align: center;
                }
                [data-testid="stTable"] th { 
                    background-color: #003366 !important; 
                    color: white !important; 
                    text-align: center;
                }
                /* Ocultar columna de índice nativa */
                [data-testid="stTable"] td:nth-child(1), 
                [data-testid="stTable"] th:nth-child(1) { 
                    display: none !important; 
                }
            </style>
        """, unsafe_allow_html=True)

        # Inversión de orden para la tabla (Último registro arriba)
        datos_recientes = sorted(datos_raw, key=lambda x: x['fecha_registro'], reverse=True)
        
        tabla_out = []
        for d in datos_recientes[:15]:
            f = d.get('fecha_registro')
            h = f.strftime('%H:%M:%S') if isinstance(f, datetime) else str(f)
            tabla_out.append({
                "HORA": h,
                "USO CPU": f"{d.get('uso_cpu')}%",
                "USO RAM": f"{d.get('uso_ram')}%",
                "ESTADO": "OK"
            })
        
        st.table(tabla_out)
        return valor_futuro, valores[-1]

    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None, None

def mostrar_pantalla():
    # Título con el color original del banco
    st.markdown("<h1 style='color: #003366;'>📈 Capacity Planning</h1>", unsafe_allow_html=True)
    
    # Controles originales restituidos
    with st.container(border=True):
        col_ctrl1, col_ctrl2 = st.columns(2)
        dias_p = col_ctrl1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col_ctrl2.selectbox("Recurso a analizar:", ["uso_cpu", "uso_ram"],
                                     format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    # Ejecución del fragmento sincronizado
    v_futuro, v_actual = fragmento_capacidad(dias_p, metrica)

    if v_futuro is not None:
        st.divider()
        if st.button("💾 REGISTRAR PROYECCIÓN EN BD"):
            fecha_p = datetime.now() + timedelta(days=dias_p)
            exito = registrar_proyeccion(
                recurso_analizado=metrica.upper(),
                valor_actual=v_actual,
                valor_proyectado=v_futuro,
                fecha_proyeccion=fecha_p.date(),
                dias_proyectados=dias_p,
                veredicto="ALERTA" if v_futuro >= 90 else "ESTABLE",
                ejecutado_por="Julian"
            )
            if exito: 
                st.toast("✅ Proyección registrada exitosamente.")