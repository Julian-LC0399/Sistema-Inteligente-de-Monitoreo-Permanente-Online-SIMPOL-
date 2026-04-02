import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from streamlit_autorefresh import st_autorefresh

# --- INTENTO DE IMPORTACIÓN SEGURA ---
try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

def cargar_configuracion_inicial():
    """Busca la última configuración usando cursores nativos."""
    defaults = {
        "u_cpu_perc": 85, "u_ram_perc": 90,
        "u_cpu_warn": 70, "u_ram_warn": 75
    }
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            mapa = {
                "CPU_CRIT": "u_cpu_perc", "RAM_CRIT": "u_ram_perc",
                "CPU_WARN": "u_cpu_warn", "RAM_WARN": "u_ram_warn"
            }
            
            for metrica_db, key_st in mapa.items():
                query = f"SELECT umbral_nuevo FROM historico_umbrales WHERE metrica = %s ORDER BY fecha_cambio DESC LIMIT 1"
                cursor.execute(query, (metrica_db,))
                res = cursor.fetchone()
                if res:
                    st.session_state[key_st] = int(res['umbral_nuevo'])
            
            cursor.close()
            conn.close()
    except:
        pass # Mantiene defaults si la BD falla

def mostrar_pantalla():
    cargar_configuracion_inicial()
    
    st_autorefresh(interval=10000, key="refresco_alertas")
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Control de Alertas</h2>", unsafe_allow_html=True)

    # --- SECCIÓN DE CONFIGURACIÓN (Nativa, no usa Pandas) ---
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
                
                # Guardamos usando la función de database.py (que ya limpiamos)
                registrar_auditoria_umbral("CPU_CRIT", st.session_state.u_cpu_perc, u_cpu_crit, user)
                registrar_auditoria_umbral("RAM_CRIT", st.session_state.u_ram_perc, u_ram_crit, user)
                registrar_auditoria_umbral("CPU_WARN", st.session_state.u_cpu_warn, u_cpu_warn, user)
                registrar_auditoria_umbral("RAM_WARN", st.session_state.u_ram_warn, u_ram_warn, user)

                st.session_state.u_cpu_perc, st.session_state.u_ram_perc = u_cpu_crit, u_ram_crit
                st.session_state.u_cpu_warn, st.session_state.u_ram_warn = u_cpu_warn, u_ram_warn
                
                st.success("✅ Configuración guardada permanentemente.")
                st.rerun()

    # --- REGISTRO HISTÓRICO (Lógica Dual) ---
    st.markdown("### 📋 Historial Inmutable de Eventos")
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %', estado_sistema as ESTATUS FROM monitoreo ORDER BY id DESC LIMIT 15"
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos:
                iconos = {"CRÍTICO": "🔴 CRÍTICO", "PRECAUCIÓN": "🟠 PRECAUCIÓN", "NORMAL": "🟢 NORMAL"}
                
                if PANDAS_OK:
                    df = pd.DataFrame(datos)
                    df["ESTATUS"] = df["ESTATUS"].apply(lambda x: iconos.get(str(x).upper(), x))
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Modo de compatibilidad activa (Sin Pandas)")
                    # Formateamos un poco la lista para que se vea bien en st.table
                    for d in datos:
                        d["ESTATUS"] = iconos.get(str(d["ESTATUS"]).upper(), d["ESTATUS"])
                    st.table(datos)
    except:
        st.warning("No se pudo cargar el historial de telemetría.")