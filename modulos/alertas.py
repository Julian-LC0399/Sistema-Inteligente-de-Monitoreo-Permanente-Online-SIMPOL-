import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    """Carga los niveles de umbral desde la BD para asegurar consistencia institucional."""
    metricas = ["CPU_ESTABLE", "CPU_PRECAUCION", "CPU_CRITICO", 
                "RAM_ESTABLE", "RAM_PRECAUCION", "RAM_CRITICO"]
    
    for m in metricas:
        if m not in st.session_state:
            # Valores base de seguridad bancaria
            st.session_state[m] = 70 if "ESTABLE" in m else (80 if "PRECAUCION" in m else 90)

    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        for m in metricas:
            # Consulta al histórico más reciente
            query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
            cursor.execute(query, (m,))
            res = cursor.fetchone()
            if res: st.session_state[m] = res[0]
        cursor.close()
        conn.close()
    except: pass

@st.fragment(run_every=5)
def fragmento_log_alertas():
    """Muestra los últimos 10 eventos de monitoreo con estilo de tabla del Banco."""
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: black !important; border-bottom: 1px solid #eee !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; font-family: sans-serif; }
        </style>
    """, unsafe_allow_html=True)

    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 10")
        datos = cursor.fetchall()
        conn.close()
        if datos:
            tabla = [{"HORA": f[0].strftime('%H:%M:%S'), 
                      "ESTADO": f" {'🔴' if 'CRÍT' in str(f[3]).upper() else '🟠' if 'PREC' in str(f[3]).upper() else '🟢'} {f[3]}",
                      "CPU %": f"{f[1]}%", "RAM %": f"{f[2]}%"} for f in datos]
            st.table(tabla)
    except: pass

def mostrar_pantalla(user_actual, user_id):
    """
    Pantalla de administración de políticas de umbrales.
    Requiere user_actual para el log visual y user_id para la BD.
    """
    cargar_config_umbrales()
    st.markdown("<h2 style='color:#003366;'>🚨 Configuración de Umbrales SIMPOL</h2>", unsafe_allow_html=True)
    
    # Estilos CSS del Banco Caroní
    st.markdown("""<style>
        .stButton>button { background-color: #003366; color: white; border-radius: 5px; font-weight: bold; width: 100%; height: 45px; transition: 0.3s; }
        .stButton>button:hover { color: #ffcc00; background-color: #002244; border: 1px solid #ffcc00; }
        .label-banco { color: #003366; font-weight: bold; font-size: 16px; margin-bottom: 10px; border-bottom: 2px solid #ffcc00; display: inline-block; }
        .container-estilo { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #d3d3d3; margin-bottom: 20px; }
    </style>""", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='label-banco'>🖥️ POLÍTICA DE CARGA CPU</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        n_cpu_e = c1.number_input("Nivel Estable (%)", 1, 100, st.session_state.CPU_ESTABLE, key="cpu_e")
        n_cpu_p = c2.number_input("Nivel Precaución (%)", 1, 100, st.session_state.CPU_PRECAUCION, key="cpu_p")
        n_cpu_c = c3.number_input("Nivel Crítico (%)", 1, 100, st.session_state.CPU_CRITICO, key="cpu_c")

    with st.container():
        st.markdown("<div class='label-banco'>🧠 POLÍTICA DE MEMORIA RAM</div>", unsafe_allow_html=True)
        c4, c5, c6 = st.columns(3)
        n_ram_e = c4.number_input("Nivel Estable (%)", 1, 100, st.session_state.RAM_ESTABLE, key="ram_e")
        n_ram_p = c5.number_input("Nivel Precaución (%)", 1, 100, st.session_state.RAM_PRECAUCION, key="ram_p")
        n_ram_c = c6.number_input("Nivel Crítico (%)", 1, 100, st.session_state.RAM_CRITICO, key="ram_c")

    # Nueva sección de justificación obligatoria según simpol.sql
    st.markdown("<br>", unsafe_allow_html=True)
    comentario = st.text_area("🗒️ JUSTIFICACIÓN DEL CAMBIO (Auditoría Obligatoria)", 
                              placeholder="Ej: Ajuste por incremento de transacciones de fin de mes...")

    if st.button("💾 APLICAR POLÍTICA DE SEGURIDAD"):
        if not comentario.strip():
            st.error("❌ Debe ingresar una justificación para registrar el cambio en la auditoría.")
        else:
            cambios = False
            dict_n = {"CPU_ESTABLE": n_cpu_e, "CPU_PRECAUCION": n_cpu_p, "CPU_CRITICO": n_cpu_c,
                      "RAM_ESTABLE": n_ram_e, "RAM_PRECAUCION": n_ram_p, "RAM_CRITICO": n_ram_c}
            
            for m, val in dict_n.items():
                if val != st.session_state[m]:
                    # Se envía usuario_id y comentario a la BD
                    registrar_auditoria_umbral(m, st.session_state[m], val, user_id, comentario)
                    st.session_state[m] = val
                    cambios = True
            
            if cambios:
                st.success(f"✅ Política actualizada correctamente por {user_actual.upper()}")
                st.rerun()
            else:
                st.info("No se detectaron cambios en los valores actuales.")

    st.divider()
    st.markdown("<h4 style='color:#003366;'>📋 Registros Recientes del Sensor 2094</h4>", unsafe_allow_html=True)
    fragmento_log_alertas()