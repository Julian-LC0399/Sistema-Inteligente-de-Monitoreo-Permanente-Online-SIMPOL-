import streamlit as st
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path

def obtener_ultimo_estado_db():
    """Consulta el último registro insertado por el agente para sincronizar la alerta."""
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            # Obtenemos el registro más reciente para mostrar la realidad del servidor
            query = "SELECT uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            if res:
                # Retornamos CPU, RAM y el Estado (ESTABLE, PRECAUCIÓN, CRÍTICO)
                return res[0], res[1], str(res[2]).upper()
    except Exception as e:
        pass
    return 0, 0, "ESTABLE"

@st.fragment(run_every=5)
def mostrar_modulo_telemetria():
    """Componente que se refresca cada 5 segundos sin recargar toda la página."""
    cpu, ram, estado = obtener_ultimo_estado_db()
    
    # Configuración de estilos visuales según el estado dictado por el agente
    estilos = {
        "CRÍTICO": {"bg": "#ff4b4b", "txt": "black", "icon": "🔴"},
        "PRECAUCIÓN": {"bg": "#ffa500", "txt": "black", "icon": "🟠"},
        "ESTABLE": {"bg": "#28a745", "txt": "black", "icon": "🟢"}
    }
    
    # Si el estado no coincide, por defecto es ESTABLE
    conf = estilos.get(estado, estilos["ESTABLE"])

    st.markdown(f"""
        <div style="background-color:{conf['bg']}; padding:25px; border-radius:12px; color:{conf['txt']}; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 10px;">
            <div style="font-weight:900; font-size:26px; text-align:center;">{conf['icon']} {estado}</div>
            <div style="font-size:40px; font-weight:900; margin-top:10px; text-align:center;">CPU: {cpu}% | RAM: {ram}%</div>
            <div style="font-size:12px; font-weight:bold; opacity:0.8; margin-top:10px; text-align:center;">Sincronizado (5s)</div>
        </div>
    """, unsafe_allow_html=True)

def generar_menu():
    """Genera la barra lateral de navegación y estados del sistema."""
    with st.sidebar:
        # --- LOGO DEL BANCO ---
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='text-align:center; color:#003366;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        st.divider()

        # --- ESTADO ENLACE CORE (PRTG) ---
        try:
            _, _, msg_enlace = obtener_telemetria() 
            color_enlace = "#28a745" if "UP" in msg_enlace.upper() else "#dc3545"
            st.markdown(f"""
                <div style="background-color:#ffffff; padding:10px; border-radius:8px; border:1px solid #ddd; margin-bottom:15px;">
                    <div style="display:flex; align-items:center;">
                        <div style="width:10px; height:10px; background-color:{color_enlace}; border-radius:50%; margin-right:10px;"></div>
                        <span style="font-size:12px; font-weight:bold; color:#333;">ENLACE CORE: {msg_enlace}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.warning("Enlace Core: No disponible")

        # --- MÓDULO DE TELEMETRÍA (Auto-actualizable cada 5s) ---
        mostrar_modulo_telemetria()

        st.divider()

        # --- NAVEGACIÓN ---
        # Definición de opciones según el rol del usuario
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        # Radio de navegación con persistencia de estado
        seleccion = st.radio(
            "Menú de Navegación",
            opciones,
            key="seccion_actual",
            label_visibility="collapsed"
        )
        
        st.write("") # Espaciador
        
        # --- BOTÓN DE CIERRE DE SESIÓN ---
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.query_params.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        return seleccion