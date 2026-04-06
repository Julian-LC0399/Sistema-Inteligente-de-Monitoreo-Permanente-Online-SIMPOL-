import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    """Carga inicial de umbrales desde BD o Session State."""
    if "u_cpu_perc" not in st.session_state:
        st.session_state.u_cpu_perc = 85
        st.session_state.u_ram_perc = 90
    # Aquí podrías añadir la lógica de consulta a historico_umbrales si es necesario

@st.fragment(run_every=5)
def fragmento_log_alertas():
    st.markdown("### 📋 Registro de Eventos Recientes")
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Consultamos los últimos eventos detectados por el agente
            query = "SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 12"
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos:
                iconos = {"CRÍTICO": "🔴", "PRECAUCIÓN": "🟠", "NORMAL": "🟢"}
                tabla_nativa = []
                for f in datos:
                    estado = str(f['estado_sistema']).upper()
                    tabla_nativa.append({
                        "TIEMPO": f['fecha_registro'].strftime('%H:%M:%S'),
                        "INDICADOR": iconos.get(estado, "⚪") + " " + estado,
                        "CPU": f"{f['uso_cpu']}%",
                        "RAM": f"{f['uso_ram']}%"
                    })
                # st.table es lo más seguro para el servidor del banco
                st.table(tabla_nativa)
                st.caption(f"Sincronizado con el servidor: {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        st.error(f"Error de enlace: {e}")

def mostrar_pantalla():
    cargar_config_umbrales()
    st.markdown("<h2 style='color:#003366; margin-top:-20px;'>🚨 Centro de Alertas</h2>", unsafe_allow_html=True)

    # Configuración Manual (No se refresca para no borrar lo que el usuario escribe)
    with st.expander("⚙️ Configuración de Umbrales Críticos"):
        c1, c2 = st.columns(2)
        new_cpu = c1.number_input("Umbral CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        new_ram = c2.number_input("Umbral RAM (%)", 1, 100, st.session_state.u_ram_perc)
        
        if st.button("Actualizar Parámetros", use_container_width=True):
            st.session_state.u_cpu_perc = new_cpu
            st.session_state.u_ram_perc = new_ram
            st.success("Umbrales actualizados en memoria.")

    st.divider()

    # Registro de alertas auto-actualizable
    fragmento_log_alertas()