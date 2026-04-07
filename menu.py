import streamlit as st
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path

def obtener_ultimo_estado_db():
    """Consulta el último estado real registrado por el agente en la BD."""
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            # Traemos el uso actual y el estado calculado por el agente
            query = "SELECT uso_cpu, uso_ram, estado_sistema FROM monitoreo ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            if res:
                return res[0], res[1], str(res[2]).upper()
    except:
        pass
    return 0, 0, "NORMAL"

def generar_menu():
    with st.sidebar:
        # --- LOGO ---
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='text-align:center; color:#003366;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        st.divider()

        # --- 1. ESTADO DE INFRAESTRUCTURA (PRTG) ---
        st.markdown('<p style="font-weight:bold; color:#555; margin-bottom:5px;">🌐 Enlace Core (PRTG)</p>', unsafe_allow_html=True)
        try:
            # Reintegramos la llamada a utils.py para PRTG
            c_prtg, r_prtg, msg_enlace = obtener_telemetria()
            
            color_circulo = "#28a745" if "UP" in msg_enlace.upper() else "#dc3545"
            
            st.markdown(f"""
                <div style="background-color:#ffffff; padding:10px; border-radius:8px; border:1px solid #ddd; margin-bottom:10px;">
                    <div style="display:flex; align-items:center;">
                        <div style="width:12px; height:12px; background-color:{color_circulo}; border-radius:50%; margin-right:10px;"></div>
                        <span style="font-size:13px; font-weight:bold; color:#333;">{msg_enlace}</span>
                    </div>
                    <div style="font-size:11px; color:#666; margin-top:5px;">
                        <b>Sensor:</b> Enlace Transaccional<br>
                        <b>ID PRTG:</b> 2094
                    </div>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.warning("No se pudo conectar con PRTG.")

        # --- 2. ESTADO DEL SERVIDOR (Base de Datos - Agente) ---
        st.markdown('<p style="font-weight:bold; color:#555; margin-bottom:5px;">🖥️ Carga del Servidor</p>', unsafe_allow_html=True)
        
        cpu, ram, estado = obtener_ultimo_estado_db()
        
        # Colores según el estado de la BD (Sincronía con Alertas)
        colores = {
            "CRÍTICO": {"bg": "#ff4b4b", "txt": "white", "icon": "🔴"},
            "PRECAUCIÓN": {"bg": "#ffa500", "txt": "black", "icon": "🟠"},
            "NORMAL": {"bg": "#f0f2f6", "txt": "#333", "icon": "🟢"}
        }
        
        config = colores.get(estado, colores["NORMAL"])
        
        st.markdown(f"""
            <div style="background-color:{config['bg']}; padding:12px; border-radius:8px; color:{config['txt']}; border: 1px solid rgba(0,0,0,0.1);">
                <div style="font-weight:bold; font-size:13px;">{config['icon']} {estado}</div>
                <div style="font-size:11px; margin-top:3px;">
                    CPU: {cpu}% | RAM: {ram}%
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # --- 3. NAVEGACIÓN ---
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        seleccion = st.radio("Navegación", opciones, label_visibility="collapsed")
        
        # Estilo para botones
        st.markdown("<style>div.stButton > button { color: black !important; }</style>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
        return seleccion