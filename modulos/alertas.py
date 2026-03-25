import streamlit as st
import pandas as pd
from database import conectar_bd, registrar_auditoria_umbral
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh

def cargar_configuracion_inicial():
    """Busca la última configuración real en la tabla historico_umbrales."""
    # 1. Valores por defecto si la tabla está vacía
    defaults = {
        "u_cpu_perc": 85, "u_ram_perc": 90,
        "u_cpu_warn": 70, "u_ram_warn": 75
    }
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # 2. Sincronización con los nombres de columna de tu SQL
    try:
        conn = conectar_bd()
        # Mapeamos lo que hay en la BD con las variables de Streamlit
        mapa = {
            "CPU_CRIT": "u_cpu_perc", "RAM_CRIT": "u_ram_perc",
            "CPU_WARN": "u_cpu_warn", "RAM_WARN": "u_ram_warn"
        }
        
        for metrica_db, key_st in mapa.items():
            # CORRECCIÓN: Usamos 'umbral_nuevo' y 'fecha_cambio' según tu .sql
            query = f"""
                SELECT umbral_nuevo 
                FROM historico_umbrales 
                WHERE metrica = '{metrica_db}' 
                ORDER BY fecha_cambio DESC LIMIT 1
            """
            df = pd.read_sql(query, conn)
            if not df.empty:
                st.session_state[key_st] = int(df.iloc[0]['umbral_nuevo'])
        conn.close()
    except Exception as e:
        # Si hay error de conexión, se mantienen los valores por defecto
        pass

def mostrar_pantalla():
    # Esta llamada al inicio garantiza que al recargar (F5) se lea la BD
    cargar_configuracion_inicial()
    
    st_autorefresh(interval=10000, key="refresco_alertas")
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Control de Alertas</h2>", unsafe_allow_html=True)

    # --- SECCIÓN DE REGULACIÓN ---
    with st.expander("⚙️ Ajustar Umbrales de Sensibilidad", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<b style='color:#d9534f;'>🔴 NIVELES CRÍTICOS</b>", unsafe_allow_html=True)
            u_cpu_crit = st.number_input("CPU Crítico (%)", 1, 100, st.session_state.u_cpu_perc)
            u_ram_crit = st.number_input("RAM Crítica (%)", 1, 100, st.session_state.u_ram_perc)

        with col2:
            st.markdown("<b style='color:#ffa500;'>🟠 NIVELES PRECAUCIÓN</b>", unsafe_allow_html=True)
            u_cpu_warn = st.number_input("CPU Precaución (%)", 1, 100, st.session_state.u_cpu_warn)
            u_ram_warn = st.number_input("RAM Precaución (%)", 1, 100, st.session_state.u_ram_warn)

        if st.button("💾 Guardar Configuración en Base de Datos", use_container_width=True):
            if u_cpu_warn >= u_cpu_crit or u_ram_warn >= u_ram_crit:
                st.error("Los niveles de precaución deben ser menores a los críticos.")
            else:
                user = st.session_state.get("user_actual", "Admin_CSU")
                
                # Guardamos los 4 valores en la tabla historico_umbrales
                registrar_auditoria_umbral("CPU_CRIT", st.session_state.u_cpu_perc, u_cpu_crit, user)
                registrar_auditoria_umbral("RAM_CRIT", st.session_state.u_ram_perc, u_ram_crit, user)
                registrar_auditoria_umbral("CPU_WARN", st.session_state.u_cpu_warn, u_cpu_warn, user)
                registrar_auditoria_umbral("RAM_WARN", st.session_state.u_ram_warn, u_ram_warn, user)

                # Actualizamos la sesión para que el cambio sea instantáneo
                st.session_state.u_cpu_perc = u_cpu_crit
                st.session_state.u_ram_perc = u_ram_crit
                st.session_state.u_cpu_warn = u_cpu_warn
                st.session_state.u_ram_warn = u_ram_warn
                
                st.success("✅ Configuración guardada permanentemente.")
                st.rerun()

    # --- REGISTRO HISTÓRICO ---
    st.markdown("### 📋 Historial Inmutable de Eventos")
    try:
        conn = conectar_bd()
        query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %', estado_sistema as ESTATUS FROM monitoreo ORDER BY id DESC LIMIT 15"
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            iconos = {"CRÍTICO": "🔴 CRÍTICO", "PRECAUCIÓN": "🟠 PRECAUCIÓN", "NORMAL": "🟢 NORMAL"}
            df["ESTATUS"] = df["ESTATUS"].apply(lambda x: iconos.get(str(x).upper(), x))
            st.dataframe(df, use_container_width=True, hide_index=True)
    except:
        st.warning("No se pudo cargar el historial de telemetría.")