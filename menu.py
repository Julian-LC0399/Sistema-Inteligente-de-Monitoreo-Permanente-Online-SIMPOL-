import streamlit as st
from utils import obtener_telemetria, get_resource_path

def generar_menu():
    with st.sidebar:
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='color: #003366;'>🏦 SIMPOL</h2>", unsafe_allow_html=True)
            
        st.markdown(f"**Analista:** {st.session_state.get('nombre_analista', 'Usuario')}")
        st.caption(f"Rol: {st.session_state.get('rol', 'operador').upper()}")
        
        st.divider()
        
        # --- INDICADORES DE ALERTA EN TIEMPO REAL ---
        try:
            cpu, ram, _ = obtener_telemetria()
            
            # Lógica de colores según umbrales de la sesión
            u_cpu = st.session_state.get("u_cpu_perc", 85)
            u_ram = st.session_state.get("u_ram_perc", 90)
            
            col_cpu = "normal" if cpu < u_cpu else "inverse"
            col_ram = "normal" if ram < u_ram else "inverse"
            
            st.metric("CPU Server", f"{cpu}%", delta=f"{cpu - u_cpu}%" if cpu > u_cpu else None, delta_color="inverse")
            st.metric("RAM Server", f"{ram}%", delta=f"{ram - u_ram}%" if ram > u_ram else None, delta_color="inverse")
            
            if cpu >= u_cpu or ram >= u_ram:
                st.error("⚠️ ALERTA DE CAPACIDAD")
        except:
            st.warning("⚠️ Telemetría no disponible")
            
        st.divider()
        
        opciones = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📈 Capacity Planning", "🔔 Alertas", "📄 Reportes PDF"]
        if st.session_state.get("rol") == "admin":
            opciones.append("👥 Gestión de Personal")
            
        seleccion = st.radio("Navegación:", opciones)
        
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
            
    return seleccion