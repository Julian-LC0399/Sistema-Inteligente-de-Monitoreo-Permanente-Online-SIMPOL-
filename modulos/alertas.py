import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    """Sincroniza los umbrales de la sesión con los últimos guardados en BD."""
    if "u_cpu_perc" not in st.session_state:
        st.session_state.u_cpu_perc = 85
        st.session_state.u_ram_perc = 90

    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        for metrica, key in [("CPU", "u_cpu_perc"), ("RAM", "u_ram_perc")]:
            cursor.execute("SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1", (metrica,))
            res = cursor.fetchone()
            if res: st.session_state[key] = res[0]
        cursor.close()
        conn.close()
    except: pass

@st.fragment(run_every=5)
def fragmento_log_alertas():
    # Estilo de tabla con bordes y texto negro
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: black !important; border: 1px solid #eee !important; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📋 Registro de Eventos (Cada 5s)")
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 10")
        datos = cursor.fetchall()
        conn.close()

        if datos:
            iconos = {"CRÍTICO": "🔴", "PRECAUCIÓN": "🟠", "NORMAL": "🟢"}
            tabla = []
            for f in datos:
                est = str(f[3]).upper()
                tabla.append({
                    "HORA": f[0].strftime('%H:%M:%S'),
                    "ESTADO": iconos.get(est, "⚪") + " " + est,
                    "CPU %": f"{f[1]}%",
                    "RAM %": f"{f[2]}%"
                })
            st.table(tabla)
    except Exception as e:
        st.error(f"Error de sincronía: {e}")

def mostrar_pantalla(user_actual):
    cargar_config_umbrales()
    st.markdown("<h2 style='color:#003366;'>🚨 Centro de Alertas y Umbrales</h2>", unsafe_allow_html=True)

    with st.expander("⚙️ Ajustar Umbrales de Detección", expanded=True):
        c1, c2 = st.columns(2)
        n_cpu = c1.number_input("Umbral CPU", 1, 100, st.session_state.u_cpu_perc)
        n_ram = c2.number_input("Umbral RAM", 1, 100, st.session_state.u_ram_perc)
        
        st.markdown("<style>div.stButton > button { color: black !important; }</style>", unsafe_allow_html=True)
        if st.button("💾 GUARDAR Y NOTIFICAR AL AGENTE", use_container_width=True):
            if n_cpu != st.session_state.u_cpu_perc:
                registrar_auditoria_umbral("CPU", st.session_state.u_cpu_perc, n_cpu, user_actual)
                st.session_state.u_cpu_perc = n_cpu
            if n_ram != st.session_state.u_ram_perc:
                registrar_auditoria_umbral("RAM", st.session_state.u_ram_perc, n_ram, user_actual)
                st.session_state.u_ram_perc = n_ram
            st.success("Configuración enviada a la base de datos.")
            st.rerun()

    st.divider()
    fragmento_log_alertas()