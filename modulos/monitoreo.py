import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual): # Ahora recibe el usuario
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 1. PANEL DE INDICADORES
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">SESIÓN ACTIVA: {user_actual.upper()}</div>
                <h3 style="margin:0; color:#003366;">Infraestructura CSU - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Analista encargado: <b>{user_actual}</b></p>
                <p style="margin:0; color:#999; font-size:11px;">Lectura de Telemetría: {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        st.metric("LECTURA CPU", f"{cpu_val}%")
        st.metric("LECTURA RAM", f"{ram_val}%")

    # 2. LÓGICA DE ESTADO (Alertas visuales)
    if cpu_val > 90 or ram_val > 90:
        st.error(f"⚠️ **ALERTA CRÍTICA:** Desbordamiento de recursos detectado.")
    elif cpu_val > 70 or ram_val > 70:
        st.warning(f"⚠️ **AVISO:** Carga moderada detectada.")
    else:
        st.success(f"✅ **SISTEMA ESTABLE:** Niveles operando normalmente.")

    # 3. GRÁFICO (Consulta actualizada a simpol.sql)
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Se ordena por fecha_registro y id para manejar la clave compuesta de simpol.sql
            query = "SELECT uso_cpu, uso_ram FROM monitoreo ORDER BY fecha_registro DESC, id DESC LIMIT 30"
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
    st.markdown("<h2 style='color: #003366;'>🖥️ Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    fragmento_tiempo_real(user_actual)