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
    """Alerta visual de CPU/RAM con estado alineado a la izquierda."""
    cpu, ram, estado = obtener_ultimo_estado_db()
    
    estilos = {
        "CRÍTICO": {"bg": "#ff4b4b", "txt": "black", "icon": "🔴"},
        "PRECAUCIÓN": {"bg": "#ffa500", "txt": "black", "icon": "🟠"},
        "ESTABLE": {"bg": "#28a745", "txt": "black", "icon": "🟢"}
    }
    
    conf = estilos.get(estado, estilos["ESTABLE"])

    st.markdown(f"""
        <div style="background-color:{conf['bg']}; padding:15px; border-radius:12px; color:{conf['txt']}; border: 1px solid rgba(0,0,0,0.1); margin: 0 auto 10px auto; width: 95%;">
            <div style="font-weight:900; font-size:18px; text-align:left; padding-left:10px;">{conf['icon']} {estado}</div>
            <div style="font-size:18px; font-weight:900; margin-top:8px; text-align:center; white-space: nowrap;">CPU:{cpu}%|RAM:{ram}%</div>
        </div>
    """, unsafe_allow_html=True)

@st.fragment(run_every=10)
def mostrar_indicador_prtg():
    """Indicador de PRTG con colores institucionales (Azul Banco)."""
    try:
        # Obtenemos los datos reales desde utils.py
        _, _, msg_sensor = obtener_telemetria()
        
        es_prtg = "PRTG" in msg_sensor.upper()
        color_led = "#2ecc71" if es_prtg else "#ffa500" 
        texto_estado = "CONECTADO" if es_prtg else "MODO LOCAL"
        
        # COLORES INSTITUCIONALES DEL BANCO
        bg_banco = "#003366"    # Azul Marino Institucional
        texto_banco = "#E0E0E0" # Gris Platino (Legible y profesional)

        st.markdown(f"""
            <div style="background:{bg_banco}; padding:12px; border-radius:10px; border:1px solid #002244; margin: 0 auto 10px auto; width: 95%; box-shadow: 2px 2px 8px rgba(0,0,0,0.2);">
                <div style="display:flex; align-items:center; justify-content:flex-start;">
                    <div style="width:10px; height:10px; background-color:{color_led}; border-radius:50%; margin-right:10px; box-shadow: 0 0 5px {color_led};"></div>
                    <span style="font-size:12px; font-weight:900; color:{texto_banco} !important; letter-spacing:0.5px;">API PRTG: {texto_estado}</span>
                </div>
                <div style="font-size:10px; color:{texto_banco} !important; opacity:0.8; margin-top:6px; text-align:left; padding-left:20px; font-weight:600; font-style: italic;">
                    {msg_sensor}
                </div>
            </div>
        """, unsafe_allow_html=True)
    except:
        pass

def generar_menu():
    """Estructura completa de la barra lateral."""
    with st.sidebar:
        # 1. Logo Institucional
        try:
            st.image(get_resource_path("logo-banco.jpg"), use_container_width=True)
        except:
            st.markdown("<h2 style='text-align:center; color:#003366;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        st.divider()

        # 2. Indicador PRTG (Colores Banco + Datos utils.py)
        mostrar_indicador_prtg()

        # 3. Alerta de Telemetría (CPU/RAM)
        mostrar_modulo_telemetria()

        st.divider()

        # 4. Navegación
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        seleccion = st.radio("Navegación", opciones, key="seccion_actual", label_visibility="collapsed")
        
        # 5. Botón Cerrar Sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.query_params.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        return seleccion