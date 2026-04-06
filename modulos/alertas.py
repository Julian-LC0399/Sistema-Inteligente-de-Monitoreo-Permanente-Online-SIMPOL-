import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    if "u_cpu_perc" not in st.session_state:
        st.session_state.u_cpu_perc = 85
        st.session_state.u_ram_perc = 90

@st.fragment(run_every=5)
def fragmento_log_alertas():
    # CSS para forzar bordes y visibilidad de columnas
    st.markdown("""
        <style>
            [data-testid="stTable"] td { 
                color: #000000 !important; 
                border: 1px solid #dddddd !important; 
            }
            [data-testid="stTable"] th {
                background-color: #f8f9fa !important;
                color: #333333 !important;
                border: 1px solid #dddddd !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📋 Registro de Eventos Recientes (5s)")
    
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            query = "SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 12"
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos:
                iconos = {"CRÍTICO": "🔴", "PRECAUCIÓN": "🟠", "NORMAL": "🟢"}
                tabla_nativa = []
                for f in datos:
                    estado = str(f[3]).upper()
                    tabla_nativa.append({
                        "TIEMPO": f[0].strftime('%H:%M:%S'),
                        "ESTADO": iconos.get(estado, "⚪") + " " + estado,
                        "CPU %": f"{f[1]}%",
                        "RAM %": f"{f[2]}%"
                    })
                st.table(tabla_nativa)
    except Exception as e:
        st.error(f"Error: {e}")

def mostrar_pantalla():
    cargar_config_umbrales()
    st.markdown("<h2 style='color:#003366;'>🚨 Centro de Alertas</h2>", unsafe_allow_html=True)

    with st.expander("⚙️ Configuración de Umbrales"):
        c1, c2 = st.columns(2)
        new_cpu = c1.number_input("Umbral CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        new_ram = c2.number_input("Umbral RAM (%)", 1, 100, st.session_state.u_ram_perc)
        if st.button("Actualizar Parámetros", use_container_width=True):
            st.session_state.u_cpu_perc, st.session_state.u_ram_perc = new_cpu, new_ram
            st.success("Configuración actualizada.")

    st.divider()
    fragmento_log_alertas()