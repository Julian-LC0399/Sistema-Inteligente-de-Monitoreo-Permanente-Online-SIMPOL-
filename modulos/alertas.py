import streamlit as st
import pandas as pd
from database import conectar_bd, registrar_auditoria_umbral
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh


def mostrar_pantalla():
    st_autorefresh(interval=10000, key="alertas_sync_runtime")

    st.markdown(
        "<h2 style='color:#003366;'>🚨 Panel de alertas y notificaciones</h2>",
        unsafe_allow_html=True,
    )

    # 1. ESTADO ACTUAL (Lectura rápida)
    try:
        cpu_act, ram_act, fuente = obtener_telemetria()
        st.info(f"Estado actual CSU: CPU {cpu_act}% | RAM {ram_act}% (Fuente: {fuente})")
    except:
        st.warning("No se pudo obtener la telemetría en tiempo real.")

    # 2. CONFIGURACIÓN DE UMBRALES (MODIFICADO PARA TRES NIVELES)
    st.markdown("### ⚙️ Configuración de límites del Semáforo")
    with st.expander("Ajustar sensibilidad de alertas", expanded=True):
        
        # --- NUEVA LÓGICA DE SESIÓN PARA ADVERTENCIA ---
        # Si no existen, definimos valores por defecto para precaución
        if "u_cpu_warn" not in st.session_state: st.session_state.u_cpu_warn = 70
        if "u_ram_warn" not in st.session_state: st.session_state.u_ram_warn = 75

        # Obtenemos valores previos
        u_cpu_crit_ant = st.session_state.get("u_cpu_perc", 85)
        u_ram_crit_ant = st.session_state.get("u_ram_perc", 90)
        u_cpu_warn_ant = st.session_state.u_cpu_warn
        u_ram_warn_ant = st.session_state.u_ram_warn

        # Visualización en columnas: Crítico vs Precaución
        st.markdown("<b style='color:#e74c3c;'>🔴 Nivel Crítico (Alto Riesgo)</b>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        u_cpu_crit = col1.number_input("CPU Crítico (%)", 1, 100, u_cpu_crit_ant, key="crit_cpu")
        u_ram_crit = col2.number_input("RAM Crítica (%)", 1, 100, u_ram_crit_ant, key="crit_ram")

        st.markdown("<b style='color:#f39c12;'>🟠 Nivel Precaución (Advertencia)</b>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        u_cpu_warn = col3.number_input("CPU Precaución (%)", 1, 100, u_cpu_warn_ant, key="warn_cpu")
        u_ram_warn = col4.number_input("RAM Precaución (%)", 1, 100, u_ram_warn_ant, key="warn_ram")

        # Validación básica: Precaución no puede ser mayor que Crítico
        if u_cpu_warn >= u_cpu_crit or u_ram_warn >= u_ram_crit:
            st.error("⚠️ Error de configuración: El umbral de **Precaución** debe ser menor que el umbral **Crítico**.")
            bot_bloqueado = True
        else:
            bot_bloqueado = False

        if st.button("Guardar cambios y auditar", use_container_width=True, disabled=bot_bloqueado):
            # --- AUDITORÍA DE LOS 4 VALORES ---
            # Auditamos Críticos
            if u_cpu_crit != u_cpu_crit_ant:
                registrar_auditoria_umbral("CPU_CRIT", u_cpu_crit_ant, u_cpu_crit, st.session_state.user_actual)
            if u_ram_crit != u_ram_crit_ant:
                registrar_auditoria_umbral("RAM_CRIT", u_ram_crit_ant, u_ram_crit, st.session_state.user_actual)
            
            # Auditamos Advertencias (Usamos nombres de métrica claros para el Oficial de Seguridad)
            if u_cpu_warn != u_cpu_warn_ant:
                registrar_auditoria_umbral("CPU_WARN", u_cpu_warn_ant, u_cpu_warn, st.session_state.user_actual)
            if u_ram_warn != u_ram_warn_ant:
                registrar_auditoria_umbral("RAM_WARN", u_ram_warn_ant, u_ram_warn, st.session_state.user_actual)

            # Actualizamos la sesión
            st.session_state["u_cpu_perc"] = u_cpu_crit
            st.session_state["u_ram_perc"] = u_ram_crit
            st.session_state["u_cpu_warn"] = u_cpu_warn
            st.session_state["u_ram_warn"] = u_ram_warn
            st.success("Configuración del Semáforo actualizada y registrada en auditoría.")

    st.divider()

    # 3. HISTORIAL DE ALERTAS (Desde tabla monitoreo con visualización de 3 niveles)
    st.markdown("### 📋 Registro de eventos recientes")
    try:
        conn = conectar_bd()
        query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %' FROM monitoreo ORDER BY id DESC LIMIT 20"
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            # Función interna para clasificar en TRES niveles (Semáforo)
            def evaluar_semaforo(row):
                # Obtenemos los límites configurados en la sesión actual
                l_cpu_c = st.session_state.get("u_cpu_perc", 85)
                l_ram_c = st.session_state.get("u_ram_perc", 90)
                l_cpu_w = st.session_state.get("u_cpu_warn", 70)
                l_ram_w = st.session_state.get("u_ram_warn", 75)

                # 1. Evaluamos lo más grave (Crítico - Rojo)
                if row["CPU %"] >= l_cpu_c or row["RAM %"] >= l_ram_c:
                    return "🔴 CRÍTICO"
                
                # 2. Evaluamos la precaución (Advertencia - Amarillo)
                elif row["CPU %"] >= l_cpu_w or row["RAM %"] >= l_ram_w:
                    return "🟠 PRECAUCIÓN"
                
                # 3. Todo está bien (Normal - Verde)
                return "🟢 NORMAL"

            df["ESTATUS"] = df.apply(evaluar_semaforo, axis=1)

            st.dataframe(
                df,
                column_config={
                    "Fecha": st.column_config.DatetimeColumn("Hora", format="hh:mm:ss a"),
                    "CPU %": st.column_config.ProgressColumn("CPU", min_value=0, max_value=100, format="%d%%"),
                    "RAM %": st.column_config.ProgressColumn("RAM", min_value=0, max_value=100, format="%d%%"),
                    "ESTATUS": st.column_config.TextColumn("Estado del Sistema")
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No se encontraron registros previos en la tabla 'monitoreo'.")

    except Exception as e:
        st.error(f"Error al procesar el historial: {e}")