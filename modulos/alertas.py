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
            query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
            cursor.execute(query, (metrica,))
            res = cursor.fetchone()
            if res: st.session_state[key] = res[0]
        cursor.close()
        conn.close()
    except: 
        pass

@st.fragment(run_every=5)
def fragmento_log_alertas():
    # Estilo de tabla con alto contraste y OCULTAR COLUMNA DE ÍNDICE (0,1,2...)
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: black !important; border: 1px solid #eee !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
            
            /* OCULTA LA PRIMERA COLUMNA (EL ÍNDICE 0,1,2...) */
            [data-testid="stTable"] td:nth-child(1), 
            [data-testid="stTable"] th:nth-child(1) {
                display: none !important;
            }
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
    # --- ESTILOS ENCAPSULADOS PARA EVITAR AFECTAR EL MENÚ ---
    st.markdown("""
        <style>
            .titulo-seccion {
                color: #003366 !important;
                font-weight: bold !important;
                margin-bottom: 15px;
            }

            [data-testid="stMain"] [data-testid="stWidgetLabel"] p {
                color: #000000 !important;
                font-weight: bold !important;
            }

            [data-testid="stMain"] [data-testid="stNumberInput"] input {
                color: black !important;
                font-weight: bold !important;
            }

            div.stButton > button {
                color: #ffffff !important;
                background-color: #003366 !important;
                border: none !important;
                font-weight: bold !important;
                width: 100% !important;
                height: 3.5em !important;
                border-radius: 8px !important;
                text-transform: uppercase;
            }
            
            div.stButton > button:hover {
                background-color: #00509d !important;
                color: #ffffff !important;
            }
        </style>
    """, unsafe_allow_html=True)

    cargar_config_umbrales()
    st.markdown("<h2 class='titulo-seccion'>🚨 Centro de Alertas y Umbrales</h2>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<h4 style='color:#000000; margin-bottom:5px;'>⚙️ CONFIGURACIÓN DE LÍMITES</h4>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            n_cpu = st.number_input("Umbral CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        with c2:
            n_ram = st.number_input("Umbral RAM (%)", 1, 100, st.session_state.u_ram_perc)
        
        st.write("") 
        
        if st.button("💾 GUARDAR Y ACTUALIZAR"):
            cambio = False
            if n_cpu != st.session_state.u_cpu_perc:
                registrar_auditoria_umbral("CPU", st.session_state.u_cpu_perc, n_cpu, user_actual)
                st.session_state.u_cpu_perc = n_cpu
                cambio = True
            if n_ram != st.session_state.u_ram_perc:
                registrar_auditoria_umbral("RAM", st.session_state.u_ram_perc, n_ram, user_actual)
                st.session_state.u_ram_perc = n_ram
                cambio = True
            
            if cambio:
                st.success("✅ Configuración guardada exitosamente.")
                st.rerun()
            else:
                st.info("No hay cambios detectados.")

    st.divider()
    fragmento_log_alertas()