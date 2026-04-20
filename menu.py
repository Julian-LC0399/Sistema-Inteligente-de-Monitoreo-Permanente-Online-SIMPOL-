import streamlit as st
import base64
import os
from database import conectar_bd
from utils import obtener_telemetria, get_resource_path

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
    """Consulta el último estado de cada IP en la tabla servidores_it."""
    estados = []
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Trae el último estado de monitoreo cruzado con el nombre del servidor
            query = """
                SELECT m.ip_servidor, m.uso_cpu, m.uso_ram, m.estado_sistema, s.nombre_alias
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
    except:
        pass
    return estados

@st.fragment(run_every=5)
def mostrar_indicadores_ip():
    """Muestra la lista de servidores y sus alertas en tiempo real."""
    servidores = obtener_estados_por_ip()
    
    if not servidores:
        st.caption("Esperando telemetría...")
        return

    st.markdown("<p style='font-size:11px; font-weight:bold; color:grey; margin-top:10px; margin-bottom:8px;'>ESTADO DE SERVIDORES:</p>", unsafe_allow_html=True)
    
    for s in servidores:
        # Lógica de colores del Banco
        if s['estado_sistema'] == "CRÍTICO":
            color, icon = "#ff4b4b", "🔴"
        elif s['estado_sistema'] == "PRECAUCIÓN":
            color, icon = "#ffa500", "🟠"
        else:
            color, icon = "#28a745", "🟢"

        st.markdown(f"""
            <div style="border-left: 4px solid {color}; background: #f0f2f6; padding: 6px 10px; 
                        border-radius: 4px; margin-bottom: 4px; display: flex; 
                        justify-content: space-between; align-items: center;">
                <div style="font-size: 11px; font-weight: bold; color: #333;">
                    {icon} {s['nombre_alias']}
                </div>
                <div style="font-size: 10px; color: #666;">
                    {s['uso_cpu']}% CPU
                </div>
            </div>
        """, unsafe_allow_html=True)

def mostrar_indicador_prtg():
    """Estado de conexión con el sensor maestro."""
    _, _, msg_sensor = obtener_telemetria(id_sensor=None)
    color = "#28a745" if "📡" in msg_sensor else "#ff4b4b"
    st.markdown(f"""
        <div style="background:{color}; color:white; padding:5px; border-radius:5px; 
                    text-align:center; font-size:10px; font-weight:bold; margin-bottom:10px;">
            PRTG: {msg_sensor}
        </div>
    """, unsafe_allow_html=True)

def generar_menu():
    with st.sidebar:
        # 1. Logo Institucional (Carga segura)
        img_path = get_resource_path("logo-banco.jpg")
        img_b64 = get_base64_image(img_path)
        
        if img_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/jpeg;base64,{img_b64}" style="width:100%; border-radius:10px; margin-bottom:15px;"></div>', unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='text-align:center; color:#003366;'>BANCO CARONÍ</h2>", unsafe_allow_html=True)

        # 2. Status PRTG
        mostrar_indicador_prtg()

        # 3. Alertas por cada IP (Dinámico)
        mostrar_indicadores_ip()

        st.divider()

        # 4. Navegación
        opciones = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        if st.session_state.get("rol") in ["admin", "seguridad"]:
            opciones += ["👥 Gestión de usuarios", "🕵️ Auditoría"]
            
        seleccion = st.radio("Menú", opciones, key="seccion_actual", label_visibility="collapsed")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.query_params.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        return seleccion