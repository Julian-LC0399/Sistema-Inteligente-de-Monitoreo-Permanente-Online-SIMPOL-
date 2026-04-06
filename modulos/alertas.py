import streamlit as st
from database import conectar_bd, registrar_auditoria_umbral
from datetime import datetime

# --- ELIMINACIÓN DE DEPENDENCIAS EXTERNAS ---
# Ya no importamos streamlit_autorefresh ni pandas para evitar errores de DLL y ModuleNotFound

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
    
    # --- CABECERA CON BOTÓN DE REFRESCO NATIVO ---
    col_t, col_refresh = st.columns([4, 1])
    with col_t:
        st.markdown("<h2 style='color:#003366; margin-top:-20px;'>🚨 Panel de Control de Alertas</h2>", unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 ACTUALIZAR", use_container_width=True):
            st.rerun()

    # --- SECCIÓN DE CONFIGURACIÓN (Nativa) ---
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
                
                # Guardamos usando la función de database.py
                registrar_auditoria_umbral("CPU_CRIT", st.session_state.u_cpu_perc, u_cpu_crit, user)
                registrar_auditoria_umbral("RAM_CRIT", st.session_state.u_ram_perc, u_ram_crit, user)
                registrar_auditoria_umbral("CPU_WARN", st.session_state.u_cpu_warn, u_cpu_warn, user)
                registrar_auditoria_umbral("RAM_WARN", st.session_state.u_ram_warn, u_ram_warn, user)

                st.session_state.u_cpu_perc, st.session_state.u_ram_perc = u_cpu_crit, u_ram_crit
                st.session_state.u_cpu_warn, st.session_state.u_ram_warn = u_cpu_warn, u_ram_warn
                
                st.success("✅ Configuración guardada permanentemente.")
                st.rerun()

    # --- REGISTRO HISTÓRICO (100% Nativo - Sin Pandas) ---
    st.markdown("### 📋 Historial Inmutable de Eventos")
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT fecha_registro as Fecha, uso_cpu as 'CPU %', uso_ram as 'RAM %', estado_sistema as ESTATUS FROM monitoreo ORDER BY id DESC LIMIT 15"
            cursor.execute(query)
            datos_raw = cursor.fetchall()
            cursor.close()
            conn.close()

            if datos_raw:
                iconos = {"CRÍTICO": "🔴 CRÍTICO", "PRECAUCIÓN": "🟠 PRECAUCIÓN", "NORMAL": "🟢 NORMAL"}
                
                # Procesamiento nativo para st.table
                # No usamos st.dataframe para evitar que Streamlit intente llamar a Pandas por debajo
                tabla_final = []
                for fila in datos_raw:
                    # Formateamos la fecha para que se vea bien
                    f_str = fila['Fecha'].strftime('%d/%m/%Y %H:%M:%S') if isinstance(fila['Fecha'], datetime) else str(fila['Fecha'])
                    
                    tabla_final.append({
                        "FECHA": f_str,
                        "CPU %": f"{fila['CPU %']}%",
                        "RAM %": f"{fila['RAM %']}%",
                        "ESTADO": iconos.get(str(fila["ESTATUS"]).upper(), fila["ESTATUS"])
                    })
                
                # Visualización robusta para el servidor
                st.table(tabla_final)
            else:
                st.info("No hay registros de telemetría recientes.")
    except Exception as e:
        st.warning(f"Error al cargar el historial: {e}")