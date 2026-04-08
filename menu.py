import streamlit as st
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path

def obtener_ultimo_estado_db():
    """Consulta el último registro de CPU/RAM en la base de datos."""
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
    except:
        pass
    return 0, 0, "ESTABLE"

@st.fragment(run_every=5)
def mostrar_modulo_telemetria():
    """Alerta visual con tamaño mediano para evitar desbordamiento."""
    cpu, ram, estado = obtener_ultimo_estado_db()
    
    estilos = {
        "CRÍTICO": {"bg": "#ff4b4b", "txt": "black", "icon": "🔴"},
        "PRECAUCIÓN": {"bg": "#ffa500", "txt": "black", "icon": "🟠"},
        "ESTABLE": {"bg": "#28a745", "txt": "black", "icon": "🟢"}
    }
    
    conf = estilos.get(estado, estilos["ESTABLE"])

    st.markdown(f"""
        <div style="background-color:{conf['bg']}; padding:20px; border-radius:12px; color:{conf['txt']}; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 10px;">
            <div style="font-weight:900; font-size:20px; text-align:center;">{conf['icon']} {estado}</div>
            <div style="font-size:24px; font-weight:900; margin-top:10px; text-align:center;">CPU: {cpu}% | RAM: {ram}%</div>
        </div>
    """, unsafe_allow_html=True)

def generar_menu():
    """Estructura completa de la barra lateral con todas las funciones."""
    with st.sidebar:
        # 1. Logo Institucional
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='text-align:center; color:#003366;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        st.divider()

        # 2. Lógica del Enlace Core (Red)
        try:
            _, _, msg_enlace = obtener_telemetria() 
            color_enlace = "#2ecc71" if "UP" in msg_enlace.upper() else "#e74c3c"
            st.markdown(f"""
                <div style="display:flex; align-items:center; background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); margin-bottom:15px;">
                    <div style="width:10px; height:10px; background-color:{color_enlace}; border-radius:50%; margin-right:12px; box-shadow: 0 0 8px {color_enlace};"></div>
                    <span style="font-size:12px; font-weight:bold; color:white;">ENLACE CORE: {msg_enlace}</span>
                </div>
            """, unsafe_allow_html=True)
        except:
            pass

        # 3. Alerta de Telemetría (CPU/RAM)
        mostrar_modulo_telemetria()

        st.divider()

        # 4. Navegación por Roles
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        seleccion = st.radio("Navegación", opciones, key="seccion_actual", label_visibility="collapsed")
        
        # 5. Cierre de Sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.query_params.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        return seleccion