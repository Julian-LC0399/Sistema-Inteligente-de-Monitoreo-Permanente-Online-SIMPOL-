import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh

def mostrar_pantalla():
    # Refresco automático cada 10 segundos para detectar estados críticos
    st_autorefresh(interval=10000, key="alertas_sync_runtime")
    
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    # 1. ESTADO ACTUAL (Lectura rápida)
    try:
        cpu_act, ram_act, fuente = obtener_telemetria()
        st.info(f"Estado actual del Nodo CSU: CPU {cpu_act}% | RAM {ram_act}% (Fuente: {fuente})")
    except:
        st.warning("No se pudo obtener la telemetría en tiempo real.")

    # 2. CONFIGURACIÓN DE UMBRALES
    st.markdown("### ⚙️ Configuración de Límites Críticos")
    with st.expander("Ajustar sensibilidad de alertas", expanded=True):
        col1, col2 = st.columns(2)
        
        # Usamos .get() para evitar el error si la llave no existe
        u_cpu = col1.number_input(
            "Umbral Crítico CPU (%)", 
            1, 100, 
            st.session_state.get("u_cpu_perc", 85)
        )
        u_ram = col2.number_input(
            "Umbral Crítico RAM (%)", 
            1, 100, 
            st.session_state.get("u_ram_perc", 90)
        )
        
        if st.button("Guardar Cambios y Re-evaluar", use_container_width=True):
            st.session_state["u_cpu_perc"] = u_cpu
            st.session_state["u_ram_perc"] = u_ram
            st.success("Umbrales actualizados correctamente.")

    st.divider()

    # 3. HISTORIAL DE ALERTAS (Desde monitoreo_nodos)
    st.markdown("### 📋 Registro de Eventos Recientes")
    try:
        conn = conectar_bd()
        # Nota: Usamos tu tabla real 'monitoreo_nodos'
        query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %' FROM monitoreo_nodos ORDER BY id DESC LIMIT 20"
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            # Función interna para clasificar según los umbrales de la sesión
            def evaluar(row):
                limite_cpu = st.session_state.get("u_cpu_perc", 85)
                limite_ram = st.session_state.get("u_ram_perc", 90)
                
                if row['CPU %'] >= limite_cpu or row['RAM %'] >= limite_ram:
                    return "🔴 CRÍTICO"
                return "🟢 NORMAL"

            df['ESTATUS'] = df.apply(evaluar, axis=1)

            # Tabla con formato profesional
            st.dataframe(
                df,
                column_config={
                    "Fecha": st.column_config.DatetimeColumn("Hora del Evento", format="hh:mm:ss a"),
                    "CPU %": st.column_config.ProgressColumn("Carga CPU", min_value=0, max_value=100),
                    "RAM %": st.column_config.ProgressColumn("Carga RAM", min_value=0, max_value=100)
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No se encontraron registros previos para analizar.")

    except Exception as e:
        st.error(f"Error al procesar el historial: {e}")