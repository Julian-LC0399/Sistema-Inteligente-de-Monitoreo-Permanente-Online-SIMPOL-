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
                <p style="margin:0; color:#666; font-size:12px;">Estado del Servidor Central | {fuente_msg}</p>
                <p style="margin-top:5px; font-weight:bold; color:#003366;">Última actualización: {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col_status:
        # Lógica de semáforo simple
        if cpu_val > 80 or ram_val > 80:
            st.error("🚨 ESTADO: CRÍTICO")
            st.warning("⚠️ AVISO: Carga moderada detectada. Monitorear procesos de fin de mes.")
        elif cpu_val > 50 or ram_val > 50:
            st.warning("⚠️ ESTADO: ADVERTENCIA")
        else:
            st.success("✅ ESTADO: ÓPTIMO")

    st.write("") # Espaciador

    # 3. MÉTRICAS VISUALES
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("USO CPU", f"{cpu_val}%", delta=None)
    m2.metric("USO RAM", f"{ram_val}%", delta=None)
    m3.metric("LATENCIA", "5 ms", delta="-2ms")
    m4.metric("RED (SBA)", "150 Mbps", delta="Activo")

    # 4. GRÁFICO HISTÓRICO (Últimos 30 registros)
    st.markdown("---")
    st.markdown("<h4 style='color: #003366;'>Gráfico de Rendimiento (Histórico Reciente)</h4>", unsafe_allow_html=True)
    
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT uso_cpu, uso_ram, fecha_registro 
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
    # Estilos CSS específicos corregidos para asegurar legibilidad en alertas
    st.markdown("""
        <style>
            /* Fuerza el color negro en métricas y textos generales */
            [data-testid="stMetricValue"] { color: #000000 !important; }
            .stMarkdown p { color: #000000 !important; }
            
            /* FIX: Asegura que las alertas (warning/error) no hereden el color blanco y sean legibles */
            .stAlert p {
                color: #000000 !important;
                font-weight: 500;
            }

            [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='color: #003366;'>🖥️ Monitoreo en Tiempo Real</h2>", unsafe_allow_html=True)
    
    # Invocación del fragmento autorefrescante
    fragmento_tiempo_real(user_actual)