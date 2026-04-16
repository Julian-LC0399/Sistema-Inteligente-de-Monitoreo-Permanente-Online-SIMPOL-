import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral

def cargar_config_umbrales():
    """Carga los niveles de umbral desde la base de datos."""
    metricas_lista = ["CPU_ESTABLE", "CPU_PRECAUCION", "CPU_CRITICO", 
                      "RAM_ESTABLE", "RAM_PRECAUCION", "RAM_CRITICO"]
    
    for m in metricas_lista:
        if m not in st.session_state:
            st.session_state[m] = 70 if "ESTABLE" in m else (80 if "PRECAUCION" in m else 90)

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            for m in metricas_lista:
                query = "SELECT valor_nuevo FROM historico_umbrales WHERE parametro = %s ORDER BY fecha_cambio DESC LIMIT 1"
                cursor.execute(query, (m,))
                res = cursor.fetchone()
                if res: 
                    st.session_state[m] = float(res[0])
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error de sincronización: {e}")

@st.fragment(run_every=5)
def fragmento_alertas(user_id):
    # --- CSS AISLADO Y CORRECCIÓN DE COLOR DE TEXTO ---
    st.markdown("""
        <style>
            /* 1. Área de texto blanca con letras negras (Solo en Main) */
            [data-testid="stMain"] div[data-baseweb="textarea"] {
                background-color: white !important;
                border: 1px solid #d3d3d3 !important;
            }
            [data-testid="stMain"] textarea {
                color: black !important;
                -webkit-text-fill-color: black !important;
                background-color: white !important;
            }

            /* 2. Botón Azul con TEXTO BLANCO (Solo en Main) */
            [data-testid="stMain"] .stButton > button {
                background-color: #003366 !important;
                color: white !important; /* Fuerza el texto a blanco */
                border-radius: 5px !important;
                font-weight: bold !important;
                border: none !important;
            }
            
            /* Forzar el color blanco en el texto del botón incluso en hover/foco */
            [data-testid="stMain"] .stButton > button p {
                color: white !important;
            }

            [data-testid="stMain"] .stButton > button:hover {
                background-color: #00509d !important;
                color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='color:#003366;'>⚠️ Gestión de Umbrales de Alerta</h4>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("Ajuste los parámetros de tolerancia institucional:")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Procesamiento (CPU)**")
            n_cpu_e = st.slider("Estable (%)", 0, 100, int(st.session_state.get('CPU_ESTABLE', 70)), key="s_cpu_e")
            n_cpu_p = st.slider("Precaución (%)", 0, 100, int(st.session_state.get('CPU_PRECAUCION', 80)), key="s_cpu_p")
            n_cpu_c = st.slider("Crítico (%)", 0, 100, int(st.session_state.get('CPU_CRITICO', 90)), key="s_cpu_c")

        with c2:
            st.markdown("**Memoria (RAM)**")
            n_ram_e = st.slider("Estable (%)", 0, 100, int(st.session_state.get('RAM_ESTABLE', 70)), key="s_ram_e")
            n_ram_p = st.slider("Precaución (%)", 0, 100, int(st.session_state.get('RAM_PRECAUCION', 80)), key="s_ram_p")
            n_ram_c = st.slider("Crítico (%)", 0, 100, int(st.session_state.get('RAM_CRITICO', 90)), key="s_ram_c")

        st.write("")
        
        comentario = st.text_area(
            "Justificación del cambio (Auditoría):", 
            placeholder="Describa el motivo...",
            height=100
        )

        if st.button("💾 GUARDAR Y ACTUALIZAR SISTEMA", use_container_width=True):
            dict_nuevos = {
                "CPU_ESTABLE": n_cpu_e, "CPU_PRECAUCION": n_cpu_p, "CPU_CRITICO": n_cpu_c,
                "RAM_ESTABLE": n_ram_e, "RAM_PRECAUCION": n_ram_p, "RAM_CRITICO": n_ram_c
            }
            try:
                cambios = 0
                for metrica, val_nuevo in dict_nuevos.items():
                    val_anterior = st.session_state.get(metrica)
                    if val_nuevo != val_anterior:
                        registrar_auditoria_umbral(metrica, val_anterior, val_nuevo, user_id, comentario)
                        st.session_state[metrica] = val_nuevo
                        cambios += 1
                if cambios > 0:
                    st.success(f"✅ Se han actualizado {cambios} parámetros.")
                    st.rerun()
                else:
                    st.info("No se detectaron cambios.")
            except Exception as e:
                st.error(f"Error técnico: {e}")

def mostrar_pantalla(user_id):
    # Forzar negro en etiquetas del cuerpo principal solamente
    st.markdown("<style>[data-testid='stMain'] p, [data-testid='stMain'] label { color: black !important; }</style>", unsafe_allow_html=True)
    cargar_config_umbrales()
    fragmento_alertas(user_id)