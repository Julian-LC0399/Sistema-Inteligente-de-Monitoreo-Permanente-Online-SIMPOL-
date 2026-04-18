import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

@st.fragment(run_every=5)
def fragmento_tiempo_real(user_actual):
    # 1. OBTENCIÓN DE DATOS
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # 2. PANEL DE CABECERA (Probado que funciona en tu servidor)
    st.markdown(f"""
        <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:15px; border-left:5px solid #003366; border-radius: 5px; margin-bottom: 20px;">
            <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:5px; border-radius:3px;">
                USUARIO: {user_actual.upper()}
            </div>
            <h3 style="margin:0; color:#003366; font-family:Arial;">Infraestructura CSU - Banco Caroní</h3>
            <p style="margin:0; color:#666; font-size:12px;">Sincronización: {fecha_actual} | Fuente: {fuente_msg}</p>
        </div>
    """, unsafe_allow_html=True)

    # 3. VISUALIZACIÓN DE CARGA (Sin Gráficas de Librería)
    st.markdown("### ⚡ Estado de Recursos")
    
    # Función interna para crear termómetros en HTML
    def crear_barra(nombre, valor, color):
        return f"""
        <div style="margin-bottom:15px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="font-weight:bold; color:#333;">{nombre}</span>
                <span style="font-weight:bold; color:{color};">{valor}%</span>
            </div>
            <div style="background-color:#eee; border-radius:10px; height:20px; width:100%;">
                <div style="background-color:{color}; width:{valor}%; height:20px; border-radius:10px; transition: width 0.5s ease-in-out;"></div>
            </div>
        </div>
        """

    col_izq, col_der = st.columns(2)
    
    with col_izq:
        color_cpu = "#28a745" if cpu_val < 70 else "#ffc107" if cpu_val < 90 else "#dc3545"
        st.markdown(crear_barra("PROCESADOR (CPU)", cpu_val, color_cpu), unsafe_allow_html=True)

    with col_der:
        color_ram = "#003366" if ram_val < 80 else "#dc3545"
        st.markdown(crear_barra("MEMORIA (RAM)", ram_val, color_ram), unsafe_allow_html=True)

    # 4. HISTÓRICO SIMPLE EN TEXTO (Para ver la tendencia sin gráficas)
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT uso_cpu, uso_ram, fecha_registro FROM monitoreo ORDER BY id DESC LIMIT 5")
            logs = cursor.fetchall()
            cursor.close()
            conn.close()

            if logs:
                st.markdown("---")
                st.markdown("**Últimos cambios detectados:**")
                for l in logs:
                    f_log = l['fecha_registro'].strftime("%H:%M:%S")
                    st.markdown(f"• `{f_log}` → CPU: **{l['uso_cpu']}%** | RAM: **{l['uso_ram']}%**")
    except:
        pass

def mostrar_pantalla(user_actual):
    fragmento_tiempo_real(user_actual)