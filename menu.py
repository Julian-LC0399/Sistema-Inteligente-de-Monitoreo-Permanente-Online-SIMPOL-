import streamlit as st
from utils import obtener_telemetria, get_resource_path

def generar_menu():
    with st.sidebar:
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.title("🏦 SIMPOL")
            
        st.markdown(f"**Analista:** {st.session_state.get('nombre_analista', 'Usuario')}")
        st.caption(f"Rol: {st.session_state.get('rol', 'operador').upper()}")
        
        st.divider()
        
        # Telemetría segura para el Server
        try:
            cpu, ram, fuente = obtener_telemetria()
            st.metric("CPU Server", f"{cpu}%", help=f"Fuente: {fuente}")
            st.metric("RAM Server", f"{ram}%")
        except:
            st.warning("⚠️ Telemetría no disponible")
            
        st.divider()
        
        opciones = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📈 Capacity Planning", "🔔 Alertas", "📄 Reportes PDF"]
        
        # Validación de rol unificada
        if st.session_state.get("rol") == "admin":
            opciones.append("👥 Gestión de Personal")
            
        seleccion = st.radio("Navegación:", opciones)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
            
    return seleccion