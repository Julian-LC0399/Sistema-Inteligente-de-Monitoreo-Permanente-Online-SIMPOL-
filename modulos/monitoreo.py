import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual): # Ahora recibe el usuario
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 1. PANEL DE INDICADORES (USANDO EL NOMBRE DEL ANALISTA)
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">SESIÓN ACTIVA: {user_actual.upper()}</div>
                <h3 style="margin:0; color:#003366;">Infraestructura CSU - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Analista encargado: <b>{user_actual}</b></p>
                <p style="margin:0; color:#999; font-size:11px;">Último barrido de red: {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        # Colores dinámicos para las métricas
        cpu_color = "normal" if cpu_val < 70 else "inverse"
        st.metric("Carga CPU", f"{cpu_val}%", delta_color=cpu_color)
        st.metric("Uso RAM", f"{ram_val}%")

    st.divider()

    # 2. SECCIÓN DE ANÁLISIS AUTOMÁTICO (ESTO ES LO NUEVO)
    st.subheader("🔍 Análisis de Capacidad Actual")
    
    # Lógica de interpretación de datos
    if cpu_val > 80 or ram_val > 85:
        st.error(f"⚠️ **ALERTA CRÍTICA:** {user_actual}, se detecta saturación en el nodo {fuente_msg}. Riesgo de latencia en transacciones.")
    elif cpu_val > 60:
        st.warning(f"🟠 **AVISO:** Carga moderada detectada. Monitorear procesos de fin de mes.")
    else:
        st.success(f"✅ **SISTEMA ESTABLE:** Los niveles de telemetría operan dentro de los umbrales del Banco Caroní.")

    # 3. GRÁFICO (Manteniendo tu lógica original)
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT uso_cpu, uso_ram FROM monitoreo ORDER BY id DESC LIMIT 30"
            cursor.execute(query)
            datos_raw = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos_raw:
                chart_data = {
                    "CPU %": [d['uso_cpu'] for d in reversed(datos_raw)],
                    "RAM %": [d['uso_ram'] for d in reversed(datos_raw)]
                }
                st.line_chart(chart_data, height=300)
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

def mostrar_pantalla(user_actual):
    # Forzamos los textos a negro y quitamos índices (Consistencia visual)
    st.markdown("""
        <style>
            [data-testid="stMetricValue"] { color: #000000 !important; }
            .stMarkdown p { color: #000000 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    
    # Pasamos el user_actual al fragmento
    fragmento_tiempo_real(user_actual)