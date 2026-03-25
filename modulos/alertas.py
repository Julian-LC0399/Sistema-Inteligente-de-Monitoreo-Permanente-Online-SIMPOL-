import streamlit as st
import pandas as pd
from database import conectar_bd, registrar_auditoria_umbral
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh

def cargar_configuracion_inicial():
    try:
        conn = conectar_bd()
        metricas = {"CPU_CRIT": "u_cpu_perc", "RAM_CRIT": "u_ram_perc", "CPU_WARN": "u_cpu_warn", "RAM_WARN": "u_ram_warn"}
        for db_name, session_key in metricas.items():
            if session_key not in st.session_state:
                query = f"SELECT valor_nuevo FROM historico_umbrales WHERE metrica = '{db_name}' ORDER BY id_hist_umb DESC LIMIT 1"
                df = pd.read_sql(query, conn)
                st.session_state[session_key] = int(df.iloc[0]['valor_nuevo']) if not df.empty else 85 # fallback
        conn.close()
    except:
        pass

def mostrar_pantalla():
    cargar_configuracion_inicial()
    st_autorefresh(interval=10000, key="alertas_sync_runtime")
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de alertas e historial</h2>", unsafe_allow_html=True)

    # 1. ESTADO ACTUAL (Mantiene el tiempo real)
    cpu_act, ram_act, _ = obtener_telemetria()
    st.info(f"Estado actual: CPU {cpu_act}% | RAM {ram_act}%")

    # 2. CONFIGURACIÓN (Sliders para el futuro)
    with st.expander("⚙️ Ajustar umbrales del sistema"):
        # [Código de Sliders e inputs igual al anterior para guardar en historico_umbrales]
        # ... (Mantener lógica de st.button que llama a registrar_auditoria_umbral)
        if st.button("Guardar cambios"):
            # Al guardar aquí, el agente los tomará en su próximo ciclo
            st.success("Configuración guardada.")
            st.rerun()

    # 3. HISTORIAL INMUTABLE
    st.markdown("### 📋 Registro Histórico (Datos Fijos)")
    try:
        conn = conectar_bd()
        # Leemos 'estado_sistema' que ya fue calculado por el agente
        query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %', estado_sistema as ESTATUS FROM monitoreo ORDER BY id DESC LIMIT 20"
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            # Solo agregamos iconos visuales sin cambiar el texto de la BD
            iconos = {"CRÍTICO": "🔴 CRÍTICO", "PRECAUCIÓN": "🟠 PRECAUCIÓN", "NORMAL": "🟢 NORMAL", "ADVERTENCIA": "🟠 PRECAUCIÓN", "CRITICO": "🔴 CRÍTICO"}
            df["ESTATUS"] = df["ESTATUS"].apply(lambda x: iconos.get(str(x).upper(), x))
            
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error: {e}")