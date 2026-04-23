import streamlit as st
import base64
import os
from database import conectar_bd
from utils import obtener_telemetria_total, get_resource_path

def get_base64_image(image_path):
    """Convierte la imagen a string para evitar errores de procesamiento en el servidor."""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except:
        pass
    return None

def obtener_estados_por_ip():
    """Consulta el último estado de cada IP en la tabla monitoreo."""
    estados = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT m.ip_servidor, m.val_cpu, m.val_ram, m.estado_sistema, s.nombre_alias
                FROM monitoreo m
                INNER JOIN (
                    SELECT ip_servidor, MAX(fecha_registro) as max_fecha
                    FROM monitoreo
                    GROUP BY ip_servidor
                ) m2 ON m.ip_servidor = m2.ip_servidor AND m.fecha_registro = m2.max_fecha
                INNER JOIN servidores_it s ON m.ip_servidor = s.ip
                WHERE s.estado_monitoreo = 1
            """
            cursor.execute(query)
            estados = cursor.fetchall()
            cursor.close()
            conn.close()
    except Exception as e:
        st.error(f"Error cargando estados: {e}")
    return estados

def mostrar_indicador_prtg():
    """Estado de conexión con el sensor maestro."""
    try:
        estado = obtener_telemetria_total({})
        msg_sensor = estado.get("msg", "Offline")
    except:
        msg_sensor = "Error de Enlace"
        
    color = "#28a745" if "PRTG" in msg_sensor else "#ff4b4b"
    st.markdown(f"""
        <div style="background:{color}; color:white; padding:5px; border-radius:5px; 
                    text-align:center; font-size:10px; font-weight:bold; margin-bottom:10px;">
            PRTG: {msg_sensor}
        </div>
    """, unsafe_allow_html=True)

@st.fragment(run_every=5)
def mostrar_indicadores_ip():
    """Muestra la lista de servidores y sus alertas en tiempo real."""
    servidores = obtener_estados_por_ip()
    if not servidores:
        st.caption("Esperando telemetría...")
        return

    st.markdown("<p style='font-size:11px; font-weight:bold; color:grey; margin-top:10px;'>SERVIDORES:</p>", unsafe_allow_html=True)
    for s in servidores:
        color = "#ff4b4b" if s['estado_sistema'] == "CRÍTICO" else "#28a745"
        icon = "🔴" if s['estado_sistema'] == "CRÍTICO" else "🟢"
        st.markdown(f"""
            <div style="border-left: 3px solid {color}; background: #f0f2f6; padding: 5px; 
                        border-radius: 3px; margin-bottom: 2px; font-size: 11px;">
                {icon} <b>{s['nombre_alias']}</b> | CPU: {s['val_cpu']}%
            </div>
        """, unsafe_allow_html=True)

def generar_menu():
    with st.sidebar:
        img_path = get_resource_path("logo-banco.jpg")
        img_b64 = get_base64_image(img_path)
        
        if img_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/jpeg;base64,{img_b64}" style="width:100%; border-radius:10px; margin-bottom:15px;"></div>', unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='text-align:center; color:#003366;'>BANCO CARONÍ</h2>", unsafe_allow_html=True)

        mostrar_indicador_prtg()
        mostrar_indicadores_ip()
        st.divider()

        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        seleccion = st.radio("Menú", opciones, key="seccion_actual", label_visibility="collapsed")
        
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="primary"):
            st.query_params.clear() # Limpia la URL (?session=active...)
            for key in list(st.session_state.keys()):
                del st.session_state[key] # Borra memoria de sesión
            st.session_state["autenticado"] = False
            st.rerun()
            
        return seleccion