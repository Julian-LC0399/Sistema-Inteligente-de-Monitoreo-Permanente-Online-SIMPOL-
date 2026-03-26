import streamlit as st
import requests
from utils import obtener_telemetria, get_resource_path

def generar_menu():
    with st.sidebar:
        # --- LOGO INSTITUCIONAL ---
        try:
            ruta_logo = get_resource_path("logo-banco.jpg")
            st.image(ruta_logo, use_container_width=True)
        except:
            st.markdown("<h2 style='color:#003366; text-align:center;'>SIMPOL</h2>", unsafe_allow_html=True)
        
        # --- 1. APARTADO: ALERTAS DE SISTEMA ---
        st.markdown('<p class="titulo-seccion-sidebar">Alertas de Sistema</p>', unsafe_allow_html=True)
        try:
            c_sidebar, r_sidebar, _ = obtener_telemetria()
            u_cpu = st.session_state.get("u_cpu_perc", 85)
            u_ram = st.session_state.get("u_ram_perc", 90)
            u_cpu_w = st.session_state.get("u_cpu_warn", 70)
            u_ram_w = st.session_state.get("u_ram_warn", 75)
            
            if c_sidebar >= u_cpu or r_sidebar >= u_ram:
                st.markdown(f"""
                    <div style="background-color:#ff4b4b; padding:15px; border-radius:5px; color:white; border:1px solid #ff4b4b;">
                        <strong>🚨 ESTADO CRÍTICO</strong><br>
                        <small>CPU: {c_sidebar}% | RAM: {r_sidebar}%</small>
                    </div>
                """, unsafe_allow_html=True)
            elif c_sidebar >= u_cpu_w or r_sidebar >= u_ram_w:
                st.markdown(f"""
                    <div style="background-color:#ffa500; padding:15px; border-radius:5px; color:#1a1a1a; border:1px solid #cc8400;">
                        <strong>🟠 PRECAUCIÓN</strong><br>
                        <small>CPU: {c_sidebar}% | RAM: {r_sidebar}%</small>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="background-color:#28a745; padding:15px; border-radius:5px; color:white; border:1px solid #28a745;">
                        <strong>✅ Operación Normal</strong>
                    </div>
                """, unsafe_allow_html=True)
        except:
            st.warning("⚠️ Sin conexión a sensores")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- 2. APARTADO: IDENTIFICACIÓN ---
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        nombre_display = str(st.session_state.get("nombre_analista") or st.session_state.get("user_actual")).upper()
        rol_display = str(st.session_state.get("rol", "USUARIO")).upper()
        
        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        # --- 3. APARTADO: ESTADO DE TELEMETRÍA (PRTG) ---
        st.markdown('<p class="titulo-seccion-sidebar">Estado de Telemetría</p>', unsafe_allow_html=True)
        msg_enlace = "MODO LOCAL"
        color_status = "#ffc107"
        nombre_sensor = "psutil (Sistema)"
        
        try:
            url_prtg = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,sensor,lastvalue&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
            r = requests.get(url_prtg, timeout=0.8, verify=False)
            if r.status_code == 200:
                msg_enlace = "PRTG conectado"
                color_status = "#28a745"
                nombre_sensor = r.json()["sensors"][0].get("sensor", "Sensor 2094")
        except:
            pass

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 10px; border-left: 5px solid {color_status}; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 12px; height: 12px; background-color: {color_status}; border-radius: 50%;"></div>
                    <span style="font-size: 13px; font-weight: bold; color: #333;">{msg_enlace}</span>
                </div>
                <hr style="margin: 8px 0; border: 0.5px solid #eee;">
                <div style="font-size: 11px; color: #666;">
                    <b>ORIGEN:</b> ID: 2094<br>
                    <b>SENSOR:</b> {nombre_sensor}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- 4. MENÚ DE NAVEGACIÓN ---
        st.markdown('<p class="titulo-seccion-sidebar">Menú Principal</p>', unsafe_allow_html=True)
        
        # Opciones base para todos los usuarios
        opciones_menu = ["🏠 Inicio", "📊 Monitoreo en vivo", "📈 Capacity planning", "🔔 Alertas", "📄 Reportes"]
        
        # Obtener el rol actual
        rol_actual = st.session_state.get("rol")
        
        # Lógica de visibilidad solicitada:
        # Admin y Seguridad ven Gestión y Auditoría. Operador no.
        if rol_actual in ["admin", "seguridad"]:
            opciones_menu.append("👥 Gestión de personal")
            opciones_menu.append("🕵️ Auditoría")
            
        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
            
    return seleccion