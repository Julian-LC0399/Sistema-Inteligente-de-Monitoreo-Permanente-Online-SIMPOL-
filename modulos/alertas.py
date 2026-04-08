import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    if "u_cpu_perc" not in st.session_state:
        st.session_state.u_cpu_perc = 90
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
    except: pass

@st.fragment(run_every=5)
def fragmento_log_alertas():
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: black !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; }
            [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 10")
        datos = cursor.fetchall()
        conn.close()

        if datos:
            tabla = []
            for f in datos:
                est = str(f[3]).upper()
                ico = "🔴" if "CRÍT" in est else "🟠" if "PREC" in est else "🟢"
                tabla.append({
                    "HORA": f[0].strftime('%H:%M:%S'),
                    "ESTADO": f"{ico} {est}",
                    "CPU %": f"{f[1]}%",
                    "RAM %": f"{f[2]}%"
                })
            st.table(tabla)
    except: pass

def mostrar_pantalla(user_actual):
    cargar_config_umbrales()
    st.markdown("<h2 style='color:#003366;'>🚨 Centro de Alertas y Umbrales</h2>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<h4 style='color:black;'>⚙️ CONFIGURACIÓN DE UMBRAL CRÍTICO</h4>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        n_cpu = c1.number_input("Límite Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        n_ram = c2.number_input("Límite Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc)
        
        # --- LEYENDA DE ESTADOS SOLICITADA ---
        st.info("💡 **Rangos de Operación:**\n"
                "- **CRÍTICO:** Mayor a los límites definidos arriba (Recomendado: 90%)\n"
                "- **PRECAUCIÓN:** Mayor al 70%\n"
                "- **ESTABLE:** 70% o inferior")

        if st.button("💾 GUARDAR Y NOTIFICAR AL AGENTE", use_container_width=True):
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
                st.success(f"✅ Umbrales actualizados. Analista responsable: {user_actual}")
                st.rerun()

    st.write("")
    fragmento_log_alertas()