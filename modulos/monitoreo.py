import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual):
    # 1. OBTENCIÓN DE TELEMETRÍA
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 2. PANEL DE INDICADORES (Tu diseño original)
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
        # Lógica de colores basada en session_state
        def get_color(val, crit, prec):
            if val >= crit: return "#d32f2f" # Rojo
            if val >= prec: return "#fbc02d" # Amarillo
            return "#388e3c" # Verde

        color_cpu = get_color(cpu_val, st.session_state.get('CPU_CRITICO', 90), st.session_state.get('CPU_PRECAUCION', 80))
        st.markdown(f"""
            <div style="background-color:{color_cpu}; color:white; padding:15px; border-radius:5px; text-align:center;">
                <span style="font-size:12px; font-weight:bold;">ESTADO DEL SISTEMA</span><br>
                <span style="font-size:20px; font-weight:bold;">{"CRÍTICO" if cpu_val >= 80 else "OPERATIVO"}</span>
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
            [data-testid="stMetricValue"] { color: #000000 !important; }
            .stMarkdown p { color: #000000 !important; }
            .stAlert p { color: #000000 !important; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h2 style='color:#003366;'>📈 Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    fragmento_tiempo_real(user_actual)