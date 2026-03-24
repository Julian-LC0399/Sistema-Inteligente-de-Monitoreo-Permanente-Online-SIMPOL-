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
            st.markdown(
                "<h2 style='color:#003366; text-align:center;'>SIMPOL</h2>",
                unsafe_allow_html=True,
            )

        # --- 1. APARTADO: ALERTAS DE SISTEMA ---
        st.markdown(
            '<p class="titulo-seccion-sidebar">Alertas de Sistema</p>',
            unsafe_allow_html=True,
        )
        try:
            c_sidebar, r_sidebar, _ = obtener_telemetria()
            # Usamos los umbrales guardados en la sesión
            u_cpu = st.session_state.get("u_cpu_perc", 85)
            u_ram = st.session_state.get("u_ram_perc", 90)

            if c_sidebar >= u_cpu or r_sidebar >= u_ram:
                st.error(
                    f"🚨 **ESTADO CRÍTICO**\n\nCPU: {c_sidebar}% | RAM: {r_sidebar}%"
                )
            else:
                st.success("✅ Operación Normal")
        except:
            st.warning("⚠️ Sin conexión a sensores")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- 2. APARTADO: IDENTIFICACIÓN ---
        st.markdown(
            '<p class="titulo-seccion-sidebar">Identificación</p>',
            unsafe_allow_html=True,
        )
        nombre_display = str(
            st.session_state.get("nombre_analista")
            or st.session_state.get("user_actual")
        ).upper()
        rol_display = str(st.session_state.get("rol", "USUARIO")).upper()

        st.markdown(
            f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - CSU</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # --- 3. APARTADO: ESTADO DE TELEMETRÍA (PRTG) ---
        st.markdown(
            '<p class="titulo-seccion-sidebar">Estado de Telemetría</p>',
            unsafe_allow_html=True,
        )
        msg_enlace = "MODO LOCAL"
        color_status = "#ffc107"
        nombre_sensor = "psutil (Sistema)"

        try:
            # Token de tu servidor PRTG
            url_prtg = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,sensor,lastvalue&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
            r = requests.get(url_prtg, timeout=0.8, verify=False)
            if r.status_code == 200:
                msg_enlace = "PRTG conectado"
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
                    <b>ORIGEN:</b> ID: 2094<br>
                    <b>SENSOR:</b> {nombre_sensor}
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # --- 4. MENÚ DE NAVEGACIÓN ---
        st.markdown(
            '<p class="titulo-seccion-sidebar">Menú Principal</p>',
            unsafe_allow_html=True,
        )
        opciones_menu = [
            "🏠 Inicio",
            "📊 Monitoreo en vivo",
            "📈 Capacity planning",
            "🔔 Alertas",
            "📄 Reportes",
        ]
        if st.session_state.get("rol") == "admin":
            opciones_menu.append("👥 Gestión de personal")

        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    return seleccion
