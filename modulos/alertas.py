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
                # CORRECCIÓN: Usamos 'parametro' y 'valor_nuevo' según tu SQL
                query = """
                    SELECT valor_nuevo 
                    FROM historico_umbrales 
                    WHERE parametro = %s 
                    ORDER BY fecha_cambio DESC LIMIT 1
                """
                cursor.execute(query, (m,))
                res = cursor.fetchone()
                if res: 
                    # Aseguramos que el valor sea numérico
                    st.session_state[m] = float(res[0])
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error al sincronizar umbrales desde la base de datos: {e}")

@st.fragment(run_every=5)
def fragmento_alertas(user_id):
    """
    Interfaz de configuración con los controles de slider.
    """
    st.markdown("<h4 style='color:#003366;'>⚠️ Configuración de Alertas Críticas</h4>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("Ajuste los niveles de tolerancia institucional para el monitoreo:")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("**Umbrales de Procesamiento (CPU)**")
            n_cpu_e = st.slider("Estado Estable (%)", 0, 100, int(st.session_state.get('CPU_ESTABLE', 70)), key="s_cpu_e")
            n_cpu_p = st.slider("Estado Precaución (%)", 0, 100, int(st.session_state.get('CPU_PRECAUCION', 80)), key="s_cpu_p")
            n_cpu_c = st.slider("Estado Crítico (%)", 0, 100, int(st.session_state.get('CPU_CRITICO', 90)), key="s_cpu_c")

        with c2:
            st.markdown("**Umbrales de Memoria (RAM)**")
            n_ram_e = st.slider("Estado Estable (%)", 0, 100, int(st.session_state.get('RAM_ESTABLE', 70)), key="s_ram_e")
            n_ram_p = st.slider("Estado Precaución (%)", 0, 100, int(st.session_state.get('RAM_PRECAUCION', 80)), key="s_ram_p")
            n_ram_c = st.slider("Estado Crítico (%)", 0, 100, int(st.session_state.get('RAM_CRITICO', 90)), key="s_ram_c")

        st.write("")
        comentario = st.text_area("Motivo del ajuste (Auditoría obligatoria):", 
                                 "Ajuste de parámetros de control interno", 
                                 height=80)

        if st.button("💾 GUARDAR Y APLICAR CAMBIOS", use_container_width=True):
            dict_nuevos = {
                "CPU_ESTABLE": n_cpu_e, "CPU_PRECAUCION": n_cpu_p, "CPU_CRITICO": n_cpu_c,
                "RAM_ESTABLE": n_ram_e, "RAM_PRECAUCION": n_ram_p, "RAM_CRITICO": n_ram_c
            }
            
            try:
                cambios_realizados = 0
                for metrica, val_nuevo in dict_nuevos.items():
                    val_anterior = st.session_state.get(metrica)
                    
                    if val_nuevo != val_anterior:
                        # Se registra usando la función corregida de database.py
                        registrar_auditoria_umbral(metrica, val_anterior, val_nuevo, user_id, comentario)
                        st.session_state[metrica] = val_nuevo
                        cambios_realizados += 1
                
                if cambios_realizados > 0:
                    st.success(f"✅ Se han actualizado {cambios_realizados} umbrales en la base de datos.")
                    st.rerun()
                else:
                    st.info("No se detectaron cambios respecto a los valores actuales.")
            except Exception as e:
                st.error(f"Error crítico al intentar guardar: {e}")

    st.divider()
    st.info("Nota: Todo cambio en los umbrales es registrado con su usuario para auditoría.")

def mostrar_pantalla(user_id):
    """
    Punto de entrada principal llamado desde el orquestador app.py.
    """
    # Estilo para forzar legibilidad de textos en Sliders y Markdown
    st.markdown("""
        <style>
            .stMarkdown p, .stSlider label { color: #000000 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    cargar_config_umbrales()
    fragmento_alertas(user_id)