import streamlit as st
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path

def obtener_ultimo_estado_db():
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            query = "SELECT uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            if res:
                return res[0], res[1], str(res[2]).upper()
    except: pass
    return 0, 0, "NORMAL"

def generar_menu():
    with st.sidebar:
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='text-align:center; color:#003366;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        st.divider()

        # --- TELEMETRÍA (CPU/RAM) ---
        cpu, ram, estado = obtener_ultimo_estado_db()
        st.markdown(f'<div style="background-color:#f0f2f6; padding:10px; border-radius:8px; border:1px solid #ddd; color:black;"><b>🟢 {estado}</b><br><small>CPU: {cpu}% | RAM: {ram}%</small></div>', unsafe_allow_html=True)

        st.divider()

        # --- NAVEGACIÓN ---
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        # IMPORTANTE: Al usar 'key="seccion_actual"', Streamlit vincula el radio
        # directamente al valor que recuperamos de la URL en app.py
        seleccion = st.radio(
            "Navegación", 
            opciones, 
            key="seccion_actual", 
            label_visibility="collapsed"
        )
        
        st.write("")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
            
        return seleccion