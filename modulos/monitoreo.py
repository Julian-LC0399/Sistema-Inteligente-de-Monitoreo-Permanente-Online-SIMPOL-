import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual):
    # 1. OBTENCIÓN DE TELEMETRÍA
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 2. PANEL DE INDICADORES (Diseño Banco Caroní)
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366; border-radius: 5px;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px; border-radius:3px;">
                    SESIÓN ACTIVA: {user_actual.upper()}
                </div>
                <h3 style="margin:0; color:#003366; font-family:Arial;">Infraestructura CSU - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:12px;">Última sincronización: {fecha_actual} ({fuente_msg})</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        st.markdown(f"""
            <div style="text-align:center; padding:15px; border:1px solid #d3d3d3; border-radius:5px; background-color:#f9f9f9;">
                <p style="margin:0; font-size:11px; color:#333;">ESTADO DEL NODO</p>
                <h2 style="margin:0; color:#28a745;">ONLINE</h2>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    m1, m2 = st.columns(2)
    m1.metric("USO DE CPU", f"{cpu_val}%", delta=f"{cpu_val-50}%", delta_color="inverse")
    m2.metric("MEMORIA RAM", f"{ram_val}%", delta=f"{ram_val-40}%", delta_color="inverse")

    # 3. GRÁFICO DE TENDENCIA (Nativo sin Pandas)
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT uso_cpu, uso_ram FROM monitoreo ORDER BY id DESC LIMIT 20")
        datos_raw = cursor.fetchall()
        conn.close()

        if datos_raw:
            st.subheader("Tendencia de los últimos 20 registros")
            # Forzamos listas de floats para asegurar compatibilidad en servidor
            chart_data = {
                "CPU %": [float(d['uso_cpu']) for d in reversed(datos_raw)],
                "RAM %": [float(d['uso_ram']) for d in reversed(datos_raw)]
            }
            st.line_chart(chart_data, height=300)
        else:
            st.info("Esperando datos del agente...")
    except Exception as e:
        st.error(f"Error de BD: {e}")

def mostrar_pantalla(user_actual):
    st.markdown("""
        <style>
            [data-testid="stMetricValue"] { color: #003366 !important; font-weight: bold; }
            .stSubheader { color: #003366 !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
    
    fragmento_tiempo_real(user_actual)