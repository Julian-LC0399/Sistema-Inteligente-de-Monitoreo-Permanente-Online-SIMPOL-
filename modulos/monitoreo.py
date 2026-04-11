import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual):
    """
    Fragmento que actualiza los indicadores y gráficos cada 5 segundos
    sin recargar toda la página.
    """
    # 1. OBTENCIÓN DE TELEMETRÍA (Desde utils.py)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 2. PANEL DE INDICADORES INSTITUCIONALES
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366; border-radius: 5px;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px; border-radius:3px;">
                    SESIÓN ACTIVA: {user_actual.upper()}
                </div>
                <h3 style="margin:0; color:#003366; font-family:Arial;">Infraestructura CSU - Banco Caroní</h3>
                <p style="margin:5px 0; color:#444; font-size:14px;">Analista encargado: <b>{user_actual}</b></p>
                <p style="margin:0; color:#888; font-size:12px;">Fuente de datos: <span style="color:#003366;">{fuente_msg}</span></p>
                <p style="margin:0; color:#999; font-size:11px;">Última actualización: {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_status:
        st.metric("LECTURA CPU", f"{cpu_val}%")
        st.metric("LECTURA RAM", f"{ram_val}%")

    st.markdown("---")

    # 3. LÓGICA DE ESTADO (Alertas Visuales)
    if cpu_val > 90 or ram_val > 90:
        st.error(f"⚠️ **ALERTA CRÍTICA:** Se ha detectado un desbordamiento de recursos en el servidor.")
    elif cpu_val > 70 or ram_val > 70:
        st.warning(f"⚠️ **AVISO:** Carga moderada detectada. Monitorear procesos de fin de mes.")
    else:
        st.success(f"✅ **SISTEMA ESTABLE:** Los niveles de telemetría operan dentro de los umbrales normales.")

    # 4. GRÁFICO HISTÓRICO (Sincronizado con simpol.sql)
    st.markdown("<h4 style='color: #003366;'>📈 Tendencia de Carga (Últimos 30 registros)</h4>", unsafe_allow_html=True)
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # CORRECCIÓN SQL: Ordenamos por fecha_registro e ID para manejar la clave compuesta de simpol.sql
            query = """
                SELECT uso_cpu, uso_ram 
                FROM monitoreo 
                ORDER BY fecha_registro DESC, id DESC 
                LIMIT 30
            """
            cursor.execute(query)
            datos_raw = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos_raw:
                # Preparamos los datos invirtiendo el orden para que el gráfico fluya de izquierda a derecha
                chart_data = {
                    "CPU %": [d['uso_cpu'] for d in reversed(datos_raw)],
                    "RAM %": [d['uso_ram'] for d in reversed(datos_raw)]
                }
                st.line_chart(chart_data, height=300)
            else:
                st.info("Esperando datos del agente para generar gráfico...")
    except Exception as e:
        st.error(f"Error de base de datos en módulo monitoreo: {e}")

def mostrar_pantalla(user_actual):
    """
    Función principal llamada por el orquestador (app.py)
    """
    # Estilos CSS específicos para esta pantalla (Texto negro y sin índices)
    st.markdown("""
        <style>
            [data-testid="stMetricValue"] { color: #000000 !important; }
            .stMarkdown p { color: #000000 !important; }
            [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='color: #003366;'>🖥️ Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    
    # Invocación del fragmento autorefrescante
    fragmento_tiempo_real(user_actual)