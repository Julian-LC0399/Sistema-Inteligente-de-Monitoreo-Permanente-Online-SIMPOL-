import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real():
    # 1. Obtención de métricas (vía SNMP/PSUTIL)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # Panel de indicadores visuales
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(
            f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">MONITOREO CRÍTICO (5s)</div>
                <h3 style="margin:0; color:#003366;">Infraestructura CSU - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Última actualización: <b>{fecha_actual}</b></p>
                <p style="margin:0; color:#999; font-size:11px;">Nodo: {fuente_msg}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_status:
        c1, c2 = st.columns(2)
        # Métricas nativas con delta (opcional si quieres comparar con el anterior)
        c1.metric("CPU", f"{cpu_val}%")
        c2.metric("RAM", f"{ram_val}%")

    st.divider()

    # 2. Gráfico de línea nativo (Sin Pandas/Numpy)
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Traemos los últimos 30 puntos para ver una ventana de tiempo decente
            query = "SELECT uso_cpu, uso_ram FROM monitoreo ORDER BY id DESC LIMIT 30"
            cursor.execute(query)
            datos_raw = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos_raw:
                st.markdown("### 📊 Gráfico de Carga Dinámica")
                chart_data = {
                    "CPU %": [d['uso_cpu'] for d in reversed(datos_raw)],
                    "RAM %": [d['uso_ram'] for d in reversed(datos_raw)]
                }
                st.line_chart(chart_data, height=350, use_container_width=True)
    except Exception as e:
        st.error(f"Error en flujo de datos: {e}")

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    
    # Ejecución del fragmento continuo
    fragmento_tiempo_real()