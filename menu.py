import streamlit as st
import requests
from utils import obtener_telemetria, get_resource_path


def generar_menu():
    with st.sidebar:
        # --- 1. LOGO INSTITUCIONAL ---
        try:
            ruta_logo = get_resource_path("logo-banco.jpg")
            st.image(ruta_logo, use_container_width=True)
        except:
            st.markdown(
                "<h2 style='color:#003366; text-align:center;'>SIMPOL</h2>",
                unsafe_allow_html=True,
            )

        # --- 2. APARTADO: ESTADO DEL SISTEMA CSU (Semáforo corregido) ---
        st.markdown(
            '<p style="font-weight:bold; color:#555; margin-bottom:5px;">Estado del Sistema CSU</p>',
            unsafe_allow_html=True,
        )
        try:
            c_sidebar, r_sidebar, _ = obtener_telemetria()
            
            # Recuperar umbrales de la sesión
            u_cpu_crit = st.session_state.get("u_cpu_perc", 85)
            u_ram_crit = st.session_state.get("u_ram_perc", 90)
            u_cpu_warn = st.session_state.get("u_cpu_warn", 70)
            u_ram_warn = st.session_state.get("u_ram_warn", 75)

            # Definición de colores y textos para evitar que se vea blanco
            if c_sidebar >= u_cpu_crit or r_sidebar >= u_ram_crit:
                bg_color = "#ff4b4b"  # Rojo
                status_text = "🚨 ESTADO CRÍTICO"
                val_text = f"CPU: {c_sidebar}% | RAM: {r_sidebar}%"
            elif c_sidebar >= u_cpu_warn or r_sidebar >= u_ram_warn:
                bg_color = "#ffa500"  # Naranja
                status_text = "🟠 PRECAUCIÓN"
                val_text = f"CPU: {c_sidebar}% | RAM: {r_sidebar}%"
            else:
                bg_color = "#28a745"  # Verde
                status_text = "✅ OPERACIÓN NORMAL"
                val_text = "Sistemas estables"

            # Renderizado con CSS forzado (!important) para evitar fondos blancos
            st.markdown(f"""
                <div style="
                    background-color: {bg_color} !important; 
                    padding: 12px; 
                    border-radius: 8px; 
                    color: white !important; 
                    text-align: center; 
                    font-weight: bold;
                    box-shadow: 0px 2px 4px rgba(0,0,0,0.2);
                ">
                    <span style="font-size: 13px;">{status_text}</span><br>
                    <span style="font-size: 11px; font-weight: normal;">{val_text}</span>
                </div>
            """, unsafe_allow_html=True)

        except:
            st.warning("⚠️ Sin conexión a sensores")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- 3. APARTADO: IDENTIFICACIÓN (Estilo original recuperado) ---
        st.markdown(
            '<p style="font-weight:bold; color:#555; margin-bottom:5px;">Identificación</p>',
            unsafe_allow_html=True,
        )
        nombre_display = str(
            st.session_state.get("nombre_analista")
            or st.session_state.get("user_actual")
        ).upper()
        rol_display = str(st.session_state.get("rol", "USUARIO")).upper()

        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 10px; border-left: 5px solid #003366; margin-bottom: 20px;">
                <span style="color:#888; font-size:11px;">IDENTIFICACIÓN CSU:</span><br>
                <span style="font-weight:bold; color:#333; font-size:14px;">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - ACTIVO</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # --- 4. APARTADO: CANAL DE TELEMETRÍA (PRTG) ---
        st.markdown(
            '<p style="font-weight:bold; color:#555; margin-bottom:5px;">Canal de Telemetría</p>',
            unsafe_allow_html=True,
        )
        msg_enlace = "MODO LOCAL"
        color_status = "#ffc107"
        nombre_sensor = "psutil (Interno)"

        try:
            url_prtg = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,sensor,lastvalue&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
            r = requests.get(url_prtg, timeout=0.8, verify=False)
            if r.status_code == 200:
                msg_enlace = "PRTG Conectado"
                color_status = "#28a745"
                nombre_sensor = r.json()["sensors"][0].get("sensor", "Sensor 2094")
        except:
            pass

        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 10px; border-left: 5px solid {color_status}; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 12px; height: 12px; background-color: {color_status}; border-radius: 50%;"></div>
                    <span style="font-size: 13px; font-weight: bold; color: #333;">{msg_enlace}</span>
                </div>
                <hr style="margin: 8px 0; border: 0.5px solid #eee;">
                <div style="font-size: 11px; color: #666;">
                    <b>ORIGEN:</b> CSU Principal<br>
                    <b>SENSOR:</b> {nombre_sensor}
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # --- 5. MENÚ DE NAVEGACIÓN (Restricción exclusiva Seguridad) ---
        st.markdown(
            '<p style="font-weight:bold; color:#555; margin-bottom:5px;">Menú Principal</p>',
            unsafe_allow_html=True,
        )
        
        opciones_menu = [
            "🏠 Inicio",
            "📊 Monitoreo en vivo",
            "📈 Capacity planning",
            "🔔 Alertas",
            "📄 Reportes",
        ]
        
        # RESTRICCIÓN: Solo el rol 'seguridad' ve la gestión
        if st.session_state.get("rol") == "seguridad":
            opciones_menu.append("👥 Gestión de personal")

        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")

        # --- 6. CIERRE DE SESIÓN ---
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    return seleccion