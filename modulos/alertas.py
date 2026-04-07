import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

def cargar_config_umbrales():
    """Carga los umbrales desde la BD para que los cambios sean persistentes."""
    defaults = {"u_cpu_perc": 85, "u_ram_perc": 90}
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            # Se busca el último cambio para CPU y RAM
            for metrica, key in [("CPU", "u_cpu_perc"), ("RAM", "u_ram_perc")]:
                query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
                cursor.execute(query, (metrica,))
                res = cursor.fetchone()
                if res:
                    st.session_state[key] = res[0]
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error cargando persistencia: {e}")

@st.fragment(run_every=5)
def fragmento_log_alertas():
    # Estilos para tablas y botones
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: #000000 !important; border: 1px solid #dddddd !important; }
            [data-testid="stTable"] th { background-color: #f8f9fa !important; color: #333333 !important; border: 1px solid #dddddd !important; }
            .stButton button { color: #000000 !important; border: 1px solid #003366 !important; }
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
        st.error(f"Error de actualización: {e}")

def mostrar_pantalla(user_actual):
    # IMPORTANTE: Ahora la función recibe 'user_actual'
    cargar_config_umbrales()
    
    st.markdown("<h2 style='color:#003366;'>🚨 Centro de Alertas y Umbrales</h2>", unsafe_allow_html=True)

    with st.expander("⚙️ Configuración de Parámetros Críticos", expanded=True):
        c1, c2 = st.columns(2)
        new_cpu = c1.number_input("Umbral Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc)
        new_ram = c2.number_input("Umbral Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc)
        
        if st.button("💾 GUARDAR Y APLICAR CAMBIOS", use_container_width=True):
            try:
                # Auditoría para CPU
                if new_cpu != st.session_state.u_cpu_perc:
                    registrar_auditoria_umbral("CPU", st.session_state.u_cpu_perc, new_cpu, user_actual)
                    st.session_state.u_cpu_perc = new_cpu
                
                # Auditoría para RAM
                if new_ram != st.session_state.u_ram_perc:
                    registrar_auditoria_umbral("RAM", st.session_state.u_ram_perc, new_ram, user_actual)
                    st.session_state.u_ram_perc = new_ram
                
                st.success("Umbrales actualizados y registrados.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")

    st.divider()
    fragmento_log_alertas()