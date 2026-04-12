import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral

def cargar_config_umbrales():
    """Carga los niveles de umbral desde la BD para asegurar consistencia institucional."""
    metricas = ["CPU_ESTABLE", "CPU_PRECAUCION", "CPU_CRITICO", 
                "RAM_ESTABLE", "RAM_PRECAUCION", "RAM_CRITICO"]
    
    # Inicializar session_state con valores base si no existen
    for m in metricas:
        if m not in st.session_state:
            st.session_state[m] = 70 if "ESTABLE" in m else (80 if "PRECAUCION" in m else 90)

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            for m in metricas:
                # Recuperar el último valor registrado para cada métrica
                query = "SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
                cursor.execute(query, (m,))
                res = cursor.fetchone()
                if res: 
                    st.session_state[m] = res[0]
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error al sincronizar umbrales desde la base de datos: {e}")

@st.fragment(run_every=5)
def fragmento_log_alertas():
    """Muestra los últimos 10 eventos de monitoreo con estilo limpio y sin índices."""
    st.markdown("""
        <style>
            [data-testid="stTable"] td { color: black !important; border-bottom: 1px solid #eee !important; font-weight: 500; }
            [data-testid="stTable"] th { background-color: #003366 !important; color: white !important; font-family: sans-serif; }
            [data-testid="stTable"] td:nth-child(1), [data-testid="stTable"] th:nth-child(1) { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT fecha_registro, uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 10")
            datos = cursor.fetchall()
            cursor.close()
            conn.close()
            if datos:
                tabla = [{
                    "HORA": f[0].strftime('%H:%M:%S') if hasattr(f[0], 'strftime') else str(f[0]), 
                    "ESTADO": f" {'🔴' if 'CRÍT' in str(f[3]).upper() else '🟠' if 'PREC' in str(f[3]).upper() else '🟢'} {f[3]}",
                    "CPU %": f"{f[1]}%", 
                    "RAM %": f"{f[2]}%"
                } for f in datos]
                st.table(tabla)
    except:
        pass

def mostrar_pantalla(user_id):
    """Pantalla de administración de umbrales SIMPOL."""
    cargar_config_umbrales()
    
    st.markdown("<h2 style='color:#003366;'>🚨 Configuración de Umbrales SIMPOL</h2>", unsafe_allow_html=True)
    
    # Estilos CSS institucionales
    st.markdown("""<style>
        .stButton>button { background-color: #003366; color: white; border-radius: 5px; font-weight: bold; width: 100%; height: 45px; }
        .stButton>button:hover { color: #ffcc00; background-color: #002244; border: 1px solid #ffcc00; }
        .label-banco { color: #003366; font-weight: bold; font-size: 16px; margin-bottom: 10px; display: inline-block; }
    </style>""", unsafe_allow_html=True)

    # Contenedores de inputs para los valores de las políticas
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

    st.markdown("<br>", unsafe_allow_html=True)
    
    # FORMULARIO DE REGISTRO: Limpia el comentario automáticamente al enviar
    with st.form("form_gestion_umbrales", clear_on_submit=True):
        comentario = st.text_input("Justificación del cambio (Auditoría)")
        btn_aplicar = st.form_submit_button("💾 APLICAR POLÍTICA DE SEGURIDAD", use_container_width=True)

        if btn_aplicar:
            if not comentario.strip():
                st.error("❌ Debe ingresar una justificación para registrar el cambio en la auditoría.")
            else:
                cambios_realizados = 0
                dict_nuevos = {
                    "CPU_ESTABLE": n_cpu_e, "CPU_PRECAUCION": n_cpu_p, "CPU_CRITICO": n_cpu_c,
                    "RAM_ESTABLE": n_ram_e, "RAM_PRECAUCION": n_ram_p, "RAM_CRITICO": n_ram_c
                }
                
                try:
                    for metrica, val_nuevo in dict_nuevos.items():
                        val_anterior = st.session_state.get(metrica)
                        
                        if val_nuevo != val_anterior:
                            # Sincronizado con database.py: (metrica, anterior, nuevo, user_id, comentario)
                            registrar_auditoria_umbral(metrica, val_anterior, val_nuevo, user_id, comentario)
                            st.session_state[metrica] = val_nuevo
                            cambios_realizados += 1
                    
                    if cambios_realizados > 0:
                        st.success(f"✅ Se han registrado exitosamente {cambios_realizados} cambios en el historial.")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios en los valores actuales.")
                except Exception as e:
                    st.error(f"Error crítico al guardar en la base de datos: {e}")

    st.divider()
    st.markdown("<h4 style='color:#003366;'>📋 Registros Recientes del Sensor 2094</h4>", unsafe_allow_html=True)
    fragmento_log_alertas()