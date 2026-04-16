import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral

def cargar_config_umbrales():
    """
    Carga los niveles de umbral desde la BD usando los nombres de columna 
    exactos de tu simpol.sql: 'parametro' y 'valor_nuevo'.
    """
    metricas_lista = ["CPU_ESTABLE", "CPU_PRECAUCION", "CPU_CRITICO", 
                      "RAM_ESTABLE", "RAM_PRECAUCION", "RAM_CRITICO"]
    
    # Inicializar session_state con valores base si no existen
    for m in metricas_lista:
        if m not in st.session_state:
            st.session_state[m] = 70 if "ESTABLE" in m else (80 if "PRECAUCION" in m else 90)

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            for m in metricas_lista:
                query = """
                    SELECT valor_nuevo 
                    FROM historico_umbrales 
                    WHERE parametro = %s 
                    ORDER BY fecha_cambio DESC LIMIT 1
                """
                cursor.execute(query, (m,))
                res = cursor.fetchone()
                if res: 
                    # Aseguramos que el valor sea numérico para los sliders
                    st.session_state[m] = float(res[0])
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error al sincronizar umbrales desde la base de datos: {e}")

@st.fragment(run_every=5)
def fragmento_alertas(user_id):
    """
    Interfaz de configuración con campo de texto limpio (fondo blanco) 
    y botón institucional.
    """
    # --- CSS DEFINITIVO ---
    st.markdown("""
        <style>
            /* 1. Fondo blanco y texto negro para el campo de auditoría */
            div[data-baseweb="textarea"] {
                background-color: white !important;
                border: 1px solid #d3d3d3 !important;
                border-radius: 4px !important;
            }
            
            textarea {
                background-color: white !important;
                color: black !important;
                -webkit-text-fill-color: black !important;
            }

            /* 2. Botón con identidad visual Banco Caroní */
            div.stButton > button:first-child {
                background-color: #003366 !important;
                color: white !important;
                border-radius: 5px !important;
                border: none !important;
                font-weight: bold !important;
                height: 3em !important;
                transition: background-color 0.3s ease !important;
            }
            
            div.stButton > button:first-child:hover {
                background-color: #00509d !important;
                color: #ffffff !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='color:#003366;'>⚠️ Gestión de Umbrales de Alerta</h4>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("Ajuste los parámetros de tolerancia para el monitoreo permanente:")
        
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
        
        # Campo de texto con fondo blanco y diseño limpio
        comentario = st.text_area(
            "Justificación del cambio (Auditoría):", 
            placeholder="Describa el motivo de la modificación...",
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
                        # Registro oficial en la tabla historico_umbrales
                        registrar_auditoria_umbral(metrica, val_anterior, val_nuevo, user_id, comentario)
                        st.session_state[metrica] = val_nuevo
                        cambios += 1
                
                if cambios > 0:
                    st.success(f"✅ Se han actualizado {cambios} parámetros exitosamente.")
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en los niveles actuales.")
            except Exception as e:
                st.error(f"Error técnico al guardar: {e}")

def mostrar_pantalla(user_id):
    """
    Punto de entrada para el orquestador app.py.
    """
    # Forzamos que los labels de los sliders sean negros para mejor legibilidad
    st.markdown("""
        <style>
            .stMarkdown p, .stSlider label { color: #000000 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    cargar_config_umbrales()
    fragmento_alertas(user_id)