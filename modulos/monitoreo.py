import streamlit as st
from datetime import datetime, timedelta
from database import conectar_bd, obtener_lista_servidores

# =========================================================================
# CALLBACKS NATIVOS: PROCESAMIENTO DE ESTADOS PRE-RENDERIZADO
# =========================================================================
def callback_cambio_servidor_tab1():
    st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"

def callback_cambio_servidor_tab2():
    st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"


# =========================================================================
# PESTAÑA 2 ENCAPSULADA EN UN FRAGMENTO (RETIENE EL FOCO Y EL TIEMPO REAL)
# =========================================================================
@st.fragment(run_every=10)
def renderizar_pestaña_analitica_completa(opciones_servidores_tab2, opciones_componentes, servidores_activos):
    nombre_srv = st.session_state["sb_graf_srv"]
    componente_sel = st.session_state["sb_graf_sensor"]
    servidor_seleccionado_tab2 = (nombre_srv != "-- Seleccione un Servidor --")

    # Filtros Propios de la Pestaña 2
    col_g_srv_2, col_g_sensor_2, col_g_limpiar_2 = st.columns([3, 2, 1])
    with col_g_srv_2:
        st.selectbox(
            "Servidor Gráficas", 
            options=opciones_servidores_tab2, 
            key="sb_graf_srv", 
            on_change=callback_cambio_servidor_tab2, 
            label_visibility="collapsed"
        )
    with col_g_sensor_2:
        st.selectbox(
            "Componente Gráficas", 
            options=opciones_componentes, 
            key="sb_graf_sensor", 
            label_visibility="collapsed", 
            disabled=not servidor_seleccionado_tab2
        )
    with col_g_limpiar_2:
        if st.button("🧹 Limpiar filtro", key="btn_limpiar_tab2_inner", use_container_width=True):
            st.session_state.pop("sb_graf_srv", None)
            st.session_state.pop("sb_graf_sensor", None)
            st.rerun(scope="fragment")

    if not servidor_seleccionado_tab2:
        st.markdown('<p style="color:#666; font-size:13px; margin-top:10px;">🖥️ Por favor, seleccione primero un <b>Servidor Bajo Análisis</b> para habilitar la selección de componentes.</p>', unsafe_allow_html=True)
        return
    elif componente_sel == "-- Seleccione un Componente --":
        st.markdown('<p style="color:#666; font-size:13px; margin-top:10px;">📈 Servidor listo. Ahora elija un área o componente del listado para proyectar sus métricas analíticas.</p>', unsafe_allow_html=True)
        return

    info_srv = next((s for s in servidores_activos if s['nombre_alias'] == nombre_srv), None)
    if not info_srv:
        return

    # Extracción de la configuración de sensores registrados en este servidor específico
    id_cpu = int(info_srv.get("id_sensor_cpu") or 0)
    id_ram = int(info_srv.get("id_sensor_ram") or 0)
    id_red_total = int(info_srv.get("id_sensor_red_total") or info_srv.get("id_sensor_red") or 0)
    id_red_entrante = int(info_srv.get("id_sensor_red_entrante") or 0)
    id_red_saliente = int(info_srv.get("id_sensor_red_saliente") or 0)
    id_latencia = int(info_srv.get("id_sensor_latencia") or 0)
    id_disco_1 = int(info_srv.get("id_sensor_disco_1") or 0)

    conexion = conectar_bd()
    datos_raw = []
    if conexion:
        rango_desde = datetime.now() - timedelta(hours=4)
        try:
            with conexion.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT fecha_registro, val_cpu, val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb, "
                    "val_disco_1_total_gb, val_disco_1_pct_libre, val_disco_1_libres_gb, "
                    "val_red_total, val_red_entrante, val_red_saliente, "
                    "val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida, "
                    "val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8 "
                    "FROM monitoreo WHERE ip_servidor = %s AND fecha_registro >= %s "
                    "ORDER BY fecha_registro ASC LIMIT 50;", (info_srv['ip'], rango_desde)
                )
                datos_raw = cursor.fetchall()
        finally:
            conexion.close()

    if not datos_raw:
        st.warning("⚠️ Esperando paquetes de telemetría del agente activo...")
        return

    config_sensores = []
    explicacion_comun = ""
    
    # =========================================================================
    # CONFIGURACIÓN DINÁMICA FILTRADA POR SENSOR REGISTRADO
    # =========================================================================
    if componente_sel == "🧠 Memoria (RAM)" and id_ram > 0:
        explicacion_comun = (
            "💡 **¿Qué estamos midiendo aquí?** La memoria RAM es el espacio de trabajo inmediato del servidor.\n\n"
            "* **Gráfica 1 (RAM Disponible %):** Muestra el porcentaje neto de memoria libre sobre la marcha.\n"
            "* **Gráfica 2 (RAM Libre en GB):** Espacio físico real medible que le queda al nodo.\n"
            "* **Gráfica 3 (RAM Total Instalada):** Línea base fija del hardware."
        )
        config_sensores = [
            {"col": "val_ram_disponible_pct", "titulo": "RAM Disponible %", "sufijo": "%", "max_y": 100, "umbral": 25, "color_u": "#ffb600", "color_linea": "#712cb0"},
            {"col": "val_ram_disponible_gb", "titulo": "RAM Libre (Espacio Real)", "sufijo": " GB", "max_y": int(float(datos_raw[-1].get("val_ram_total_gb") or 16)) + 4, "umbral": 4, "color_u": "#ffb600", "color_linea": "#0066cc"},
            {"col": "val_ram_total_gb", "titulo": "RAM Total Instalada", "sufijo": " GB", "max_y": int(float(datos_raw[-1].get("val_ram_total_gb") or 16)) + 4, "umbral": 0, "color_u": "#47a323", "color_linea": "#47a323"}
        ]

    elif componente_sel == "⚙️ Procesamiento (Solo CPU)" and id_cpu > 0:
        explicacion_comun = (
            "💡 **¿Qué estamos midiendo aquí?** Rendimiento bruto del procesador central del servidor.\n\n"
            "* **Gráfica Principal (Carga de CPU Total):** Uso porcentual ponderado general de todo el encapsulado."
        )
        config_sensores = [
            {"col": "val_cpu", "titulo": "Carga de CPU Total", "sufijo": "%", "max_y": 100, "umbral": 85, "color_u": "#d40000", "color_linea": "#712cb0"}
        ]

    elif componente_sel == "🌐 Tráfico de Red":
        explicacion_comun = (
            "💡 **¿Qué estamos midiendo aquí?** Rendimiento e intensidad del flujo de datos en las interfaces del servidor.\n\n"
            "* Muestra el desglose de velocidad y carga de paquetes según los sensores registrados (Total, Entrante o Saliente) en Mbps."
        )
        if id_red_total > 0:
            config_sensores.append({"col": "val_red_total", "titulo": "Tráfico Red Total", "sufijo": " Mbps", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#00b2b2"})
        if id_red_entrante > 0:
            config_sensores.append({"col": "val_red_entrante", "titulo": "Tráfico Entrante (RX)", "sufijo": " Mbps", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#32cd32"})
        if id_red_saliente > 0:
            config_sensores.append({"col": "val_red_saliente", "titulo": "Tráfico Saliente (TX)", "sufijo": " Mbps", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#1e90ff"})

    elif componente_sel == "⏳ Latencia de Respuesta (Ping)" and id_latencia > 0:
        explicacion_comun = (
            "💡 **¿Qué estamos midiendo aquí?** Estabilidad de la conectividad y tiempos de respuesta de la red.\n\n"
            "* **Ping Promedio / Mínimo / Máximo:** Tiempos medidos en milisegundos (ms).\n"
            "* **Pérdida de Paquetes:** Porcentaje bruto de fallas en el canal de control."
        )
        config_sensores = [
            {"col": "val_latencia_ping", "titulo": "Latencia Promedio (Ping)", "sufijo": " ms", "max_y": 150, "umbral": 80, "color_u": "#ffb600", "color_linea": "#ff5500"},
            {"col": "val_latencia_max", "titulo": "Latencia Máxima Detectada", "sufijo": " ms", "max_y": 200, "umbral": 150, "color_u": "#d40000", "color_linea": "#b22222"},
            {"col": "val_latencia_perdida", "titulo": "Pérdida de Paquetes", "sufijo": "%", "max_y": 100, "umbral": 5, "color_u": "#d40000", "color_linea": "#ff4500"}
        ]

    elif componente_sel == "💽 Almacenamiento (Disco C)" and id_disco_1 > 0:
        explicacion_comun = (
            "💡 **¿Qué estamos midiendo aquí?** Estado del disco de arranque del sistema operativo.\n\n"
            "* **Gráfica 1 (Disco C: Espacio Libre %):** Cuota disponible de forma porcentual.\n"
            "* **Gráfica 2 (Disco C: Gigabytes Libres):** Almacenamiento físico bruto disponible."
        )
        config_sensores = [
            {"col": "val_disco_1_pct_libre", "titulo": "Disco C: Espacio Libre %", "sufijo": "%", "max_y": 100, "umbral": 20, "color_u": "#ffb600", "color_linea": "#712cb0"},
            {"col": "val_disco_1_libres_gb", "titulo": "Disco C: Gigabytes Libres", "sufijo": " GB", "max_y": int(float(datos_raw[-1].get("val_disco_1_total_gb") or 100)) + 20, "umbral": 15, "color_u": "#d40000", "color_linea": "#d40000"}
        ]

    num_sensores = len(config_sensores)
    if num_sensores == 0:
        st.warning("📴 Este componente no posee sensores registrados o activos en la tabla servidores para este nodo.")
        return

    cols_dashboard = st.columns(num_sensores)
    st.markdown('<p style="font-size: 11px; color: #47a323; margin-bottom: 5px; text-align: right;">🟢 <b>Live Feed Activo</b> — Sincronizando flujos cada 10s</p>', unsafe_allow_html=True)

    for idx_sensor, cfg in enumerate(config_sensores):
        with cols_dashboard[idx_sensor]:
            w_canvas, h_canvas = 270, 180  
            m_izq, m_der, m_sup, m_inf = 35, 15, 20, 25
            w_util, h_util = w_canvas - m_izq - m_der, h_canvas - m_sup - m_inf
            suelo_y = m_sup + h_util

            puntos = []
            total_pt = len(datos_raw)
            for idx_pt, r in enumerate(datos_raw):
                val = float(r[cfg["col"]]) if r.get(cfg["col"]) is not None else 0.0
                cx = m_izq + (idx_pt / max(1, total_pt - 1)) * w_util
                cy = suelo_y - (val / cfg["max_y"]) * h_util
                puntos.append((cx, cy, val))

            path_linea = ""
            for i, p in enumerate(puntos):
                path_linea += f"{'M' if i == 0 else 'L'} {p[0]:.1f} {p[1]:.1f} "

            grid_lines = [0, int(cfg["max_y"]/2), cfg["max_y"]]
            html_grid = ""
            for g in grid_lines:
                gy = suelo_y - (g / cfg["max_y"]) * h_util
                html_grid += f'<line x1="{m_izq}" y1="{gy:.1f}" x2="{w_canvas - m_der}" y2="{gy:.1f}" stroke="#eeeeee" stroke-width="1"/>'
                html_grid += f'<text x="{m_izq - 6}" y="{gy + 4:.1f}" font-size="9" fill="#777777" text-anchor="end" font-family="sans-serif">{g}</text>'

            html_umbral = ""
            if cfg["umbral"] > 0:
                uy = suelo_y - (cfg["umbral"] / cfg["max_y"]) * h_util
                html_umbral = f'<line x1="{m_izq}" y1="{uy:.1f}" x2="{w_canvas - m_der}" y2="{uy:.1f}" stroke="{cfg["color_u"]}" stroke-width="1" stroke-dasharray="3,2"/>'

            t_init = datos_raw[0]["fecha_registro"].strftime("%H:%M") if datos_raw else "00:00"
            t_end = datos_raw[-1]["fecha_registro"].strftime("%H:%M") if datos_raw else "23:59"
            ultimo_val = puntos[-1][2] if puntos else 0.0

            html_sensor_box = (
                f'<div style="background-color: #ffffff; padding: 12px; border: 1px solid #dcdcdc; border-radius: 4px; font-family: \'Segoe UI\', sans-serif; min-height: 290px;">'
                f'<div style="border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; margin-bottom: 8px;">'
                f'<h5 style="margin: 0; color: #222; font-size: 13px; font-weight: 600;">{cfg["titulo"]}</h5>'
                f'<span style="font-size: 9.5px; color: #999;">Canal de Telemetría Activo</span></div>'
                f'<svg viewBox="0 0 {w_canvas} {h_canvas}" width="100%" height="auto" style="overflow: visible; background-color: #ffffff;">'
                f'{html_grid}{html_umbral}'
                f'<line x1="{m_izq}" y1="{suelo_y}" x2="{w_canvas - m_der}" y2="{suelo_y}" stroke="#b5b5b5" stroke-width="1"/>'
                f'<path d="{path_linea}" fill="none" stroke="{cfg["color_linea"]}" stroke-width="1.8" stroke-linejoin="round"/>'
                f'<text x="{m_izq}" y="{suelo_y + 14}" font-size="9" fill="#888" text-anchor="start">{t_init}</text>'
                f'<text x="{w_canvas - m_der}" y="{suelo_y + 14}" font-size="9" fill="#888" text-anchor="end">{t_end}</text></svg>'
                f'<div style="margin-top: 10px; background-color: #fafdff; border: 1px solid #e1edf5; padding: 8px; border-radius: 3px; font-size: 11px;">'
                f'<div><span style="color:{cfg["color_linea"]}; font-weight:bold;">■</span> <b>Último valor:</b> {ultimo_val:.1f}{cfg["sufijo"]}</div>'
                f'<div style="color:#777; margin-top:3px;"><b>Límite asignado:</b> ' + (f"{cfg['umbral']:.1f}{cfg['sufijo']}" if cfg['umbral'] > 0 else "N/A") + f'</div>'
                f'</div></div>'
            )
            st.components.v1.html(html_sensor_box, height=310, scrolling=False)

    # --- REJILLA MULTICORE EXCLUSIVA CUANDO SE SELECCIONA CPU ---
    if componente_sel == "⚙️ Procesamiento (Solo CPU)" and id_cpu > 0:
        st.markdown('<h4 style="color:#003366; font-size:15px; margin-top:20px; margin-bottom:10px; border-bottom:1px solid #ddd; padding-bottom:4px;">🎛️ Desglose de Rendimiento por Procesador (8 Cores)</h4>', unsafe_allow_html=True)
        
        cols_cores = st.columns(4)
        for core_id in range(1, 9):
            idx_col_core = (core_id - 1) % 4
            with cols_cores[idx_col_core]:
                w_c, h_c = 220, 110
                m_l, m_r, m_t, m_b = 25, 10, 15, 15
                w_u, h_u = w_c - m_l - m_r, h_c - m_t - m_b
                suelo_yc = m_t + h_u

                pts_core = []
                for idx_pt, r in enumerate(datos_raw):
                    val_c = float(r[f"val_cpu_p{core_id}"]) if r.get(f"val_cpu_p{core_id}") is not None else 0.0
                    cx_c = m_l + (idx_pt / max(1, len(datos_raw) - 1)) * w_u
                    cy_c = suelo_yc - (val_c / 100.0) * h_u
                    pts_core.append((cx_c, cy_c, val_c))

                path_core = ""
                for i, p in enumerate(pts_core):
                    path_core += f"{'M' if i == 0 else 'L'} {p[0]:.1f} {p[1]:.1f} "

                ultimo_val_core = pts_core[-1][2] if pts_core else 0.0
                color_trazo_core = "#2bc473"
                if ultimo_val_core >= 85.0: color_trazo_core = "#d40000"
                elif ultimo_val_core >= 70.0: color_trazo_core = "#ffb600"

                html_core_grid = f'<line x1="{m_l}" y1="{suelo_yc - h_u}" x2="{w_c - m_r}" y2="{suelo_yc - h_u}" stroke="#f3f3f3" stroke-width="1"/>'
                html_core_grid += f'<text x="{m_l - 4}" y="{suelo_yc - h_u + 3}" font-size="8" fill="#aaa" text-anchor="end">100</text>'
                html_core_grid += f'<text x="{m_l - 4}" y="{suelo_yc + 3}" font-size="8" fill="#aaa" text-anchor="end">0</text>'

                html_core_box = (
                    f'<div style="background-color: #ffffff; padding: 8px; border: 1px solid #e0e0e0; border-radius: 4px; font-family: \'Segoe UI\', sans-serif; margin-bottom:10px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #f9f9f9; padding-bottom:3px; margin-bottom:5px;">'
                    f'<span style="font-size:11px; font-weight:600; color:#333;">Procesador {core_id}</span>'
                    f'<span style="font-size:11px; font-weight:bold; color:{color_trazo_core};">{ultimo_val_core:.1f}%</span></div>'
                    f'<svg viewBox="0 0 {w_c} {h_c}" width="100%" height="auto" style="overflow: visible;">'
                    f'{html_core_grid}'
                    f'<line x1="{m_l}" y1="{suelo_yc}" x2="{w_c - m_r}" y2="{suelo_yc}" stroke="#cccccc" stroke-width="1"/>'
                    f'<path d="{path_core}" fill="none" stroke="{color_trazo_core}" stroke-width="1.3" stroke-linejoin="round"/>'
                    f'</svg></div>'
                )
                st.components.v1.html(html_core_box, height=155, scrolling=False)

    st.markdown("---")
    st.info(explicacion_comun)


# =========================================================================
# VISTA PRINCIPAL DEL MÓDULO
# =========================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    """
    Módulo de monitoreo - SIMPOL V4.1.0
    - FIX: Desacoplamiento estructural de CPU y Red en vistas independientes.
    """
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Cabecera
    st.markdown(
        f'<div style="background-color:#f8f9fa; padding:10px 15px; border-left:4px solid #003366; border-radius:4px; margin-bottom:10px;">'
        f'<h3 style="color:#003366; margin:0px; font-size:20px;">🖥️ Centro de Control y Telemetría</h3>'
        f'<p style="color:#555; font-size:12.5px; margin:2px 0px 0px 0px;">'
        f'Plataforma Global de Observabilidad | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>'
        f'</div>', 
        unsafe_allow_html=True
    )

    # Inicialización Segura
    if "sb_srv_tab1" not in st.session_state:
        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
    if "sb_metrica_tab1" not in st.session_state:
        st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
    if "sb_graf_srv" not in st.session_state:
        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
    if "sb_graf_sensor" not in st.session_state:
        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"

    # Carga de Configuraciones
    servidores_activos = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores_activos if s.get('nombre_alias')])))
    
    opciones_servidores_tab1 = ["-- Seleccione un Servidor para empezar --", "-- Todos los Servidores --"] + lista_nombres_bd
    opciones_servidores_tab2 = ["-- Seleccione un Servidor --"] + lista_nombres_bd
    
    mapa_columnas = {
        "fecha_registro": "FECHA REGISTRO", "val_cpu": "USO CPU GLOBAL (%)", "val_ram_total_gb": "RAM TOTAL (GB)",
        "val_ram_disponible_pct": "RAM DISPONIBLE (%)", "val_ram_disponible_gb": "RAM LIBRE (GB)",
        "val_disco_1_pct_libre": "DISCO C LIBRE (%)", "val_disco_1_libres_gb": "DISCO C LIBRE (GB)",
        "val_disco_1_total_gb": "DISCO C TOTAL (GB)", 
        "val_red_total": "RED TOTAL (Mbps)", "val_red_entrante": "RED ENTRANTE (Mbps)", "val_red_saliente": "RED SALIENTE (Mbps)",
        "val_latencia_ping": "LATENCIA PROMEDIO (ms)", "val_latencia_max": "LATENCIA MAXIMA (ms)", "val_latencia_min": "LATENCIA MINIMA (ms)", "val_latencia_perdida": "PERDIDA PAQUETES (%)",
        "val_cpu_p1": "CPU CORE 1 (%)", "val_cpu_p2": "CPU CORE 2 (%)", "val_cpu_p3": "CPU CORE 3 (%)", "val_cpu_p4": "CPU CORE 4 (%)",
        "val_cpu_p5": "CPU CORE 5 (%)", "val_cpu_p6": "CPU CORE 6 (%)", "val_cpu_p7": "CPU CORE 7 (%)", "val_cpu_p8": "CPU CORE 8 (%)"
    }

    opciones_metricas_tab1 = [
        "📊 Todas las Métricas", 
        "🧠 Variables de Memoria (RAM)",
        "⚙️ Variables de Procesamiento (CPU Cores)", 
        "🌐 Variables de Conectividad (Red y Ping)",
        "💽 Variables de Almacenamiento (Disco C)"
    ]

    opciones_componentes = [
        "-- Seleccione un Componente --", 
        "🧠 Memoria (RAM)", 
        "⚙️ Procesamiento (Solo CPU)", 
        "🌐 Tráfico de Red",
        "⏳ Latencia de Respuesta (Ping)",
        "💽 Almacenamiento (Disco C)"
    ]

    tab_historico, tab_graficas = st.tabs(
        ["📊 Histórico Telemetría", "📈 Variables por Componente"],
        key="controlador_pestañas_monitoreo"
    )

    # =========================================================================
    # TAB 1: REJILLA HISTÓRICA (Acoplada con el nuevo pool de columnas)
    # =========================================================================
    with tab_historico:
        if not servidores_activos:
            st.info("💡 No hay servidores activos mapeados en la base de datos.")
        else:
            seleccion_srv = st.session_state["sb_srv_tab1"]
            seleccion_metrica = st.session_state["sb_metrica_tab1"]
            servidor_seleccionado_tab1 = (seleccion_srv != "-- Seleccione un Servidor para empezar --")
            
            col_srv, col_metrica, col_limpiar = st.columns([3, 2, 1])
            with col_srv:
                st.selectbox("Filtrar Servidor Historial", options=opciones_servidores_tab1, key="sb_srv_tab1", on_change=callback_cambio_servidor_tab1, label_visibility="collapsed")
            with col_metrica:
                st.selectbox("Filtrar Métrica Rejilla", options=opciones_metricas_tab1, key="sb_metrica_tab1", label_visibility="collapsed", disabled=not servidor_seleccionado_tab1)
            with col_limpiar:
                if st.button("🧹 Limpiar filtro", key="btn_limpiar_tab1", use_container_width=True):
                    st.session_state.pop("sb_srv_tab1", None)
                    st.session_state.pop("sb_metrica_tab1", None)
                    st.rerun()

            if not servidor_seleccionado_tab1:
                st.markdown('<p style="color:#666; font-size:13px; margin-top:10px;">🔍 Por favor, elija un servidor del listado para desplegar la rejilla de datos.</p>', unsafe_allow_html=True)
            else:
                conexion = conectar_bd()
                registros_dinamicos = []
                if conexion:
                    try:
                        with conexion.cursor(dictionary=True) as cursor:
                            query_base = (
                                "SELECT fecha_registro, val_cpu, val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb, "
                                "val_disco_1_total_gb, val_disco_1_pct_libre, val_disco_1_libres_gb, "
                                "val_red_total, val_red_entrante, val_red_saliente, "
                                "val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida, "
                                "val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8 FROM monitoreo "
                                "WHERE val_cpu IS NOT NULL AND val_ram_disponible_pct IS NOT NULL "
                            )
                            if seleccion_srv == "-- Todos los Servidores --":
                                cursor.execute(query_base + "ORDER BY fecha_registro DESC LIMIT 150;")
                            else:
                                info_srv = next((s for s in servidores_activos if s['nombre_alias'] == seleccion_srv), None)
                                if info_srv:
                                    cursor.execute(query_base + "AND ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 150;", (info_srv['ip'],))
                            registros_dinamicos = cursor.fetchall()
                    finally:
                        conexion.close()

                if registros_dinamicos:
                    columnas_db = ["fecha_registro"]
                    if seleccion_metrica == "📊 Todas las Métricas":
                        columnas_db += ["val_cpu", "val_ram_disponible_pct", "val_disco_1_pct_libre", "val_red_total", "val_latencia_ping"]
                    elif seleccion_metrica == "🧠 Variables de Memoria (RAM)":
                        columnas_db += ["val_ram_disponible_pct", "val_ram_disponible_gb", "val_ram_total_gb"]
                    elif seleccion_metrica == "⚙️ Variables de Procesamiento (CPU Cores)":
                        columnas_db += ["val_cpu", "val_cpu_p1", "val_cpu_p2", "val_cpu_p3", "val_cpu_p4", "val_cpu_p5", "val_cpu_p6", "val_cpu_p7", "val_cpu_p8"]
                    elif seleccion_metrica == "🌐 Variables de Conectividad (Red y Ping)":
                        columnas_db += ["val_red_total", "val_red_entrante", "val_red_saliente", "val_latencia_ping", "val_latencia_perdida"]
                    elif seleccion_metrica == "💽 Variables de Almacenamiento (Disco C)":
                        columnas_db += ["val_disco_1_pct_libre", "val_disco_1_libres_gb", "val_disco_1_total_gb"]

                    html_tabla = """<div style="overflow: auto; max-height: 480px; width: 100%; border: 1px solid #d1d8e0; border-radius: 4px;"><table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', sans-serif; font-size: 12px; background-color: white;"><thead><tr>"""
                    for col in columnas_db:
                        html_tabla += f'<th style="position: sticky; top: 0; background-color: #002244; padding: 11px 14px; color: #ffffff; text-align: left; font-weight: 600; font-size: 11px; white-space: nowrap; z-index: 10; border-bottom: 2px solid #001122;">{mapa_columnas.get(col, col.upper())}</th>'
                    html_tabla += "</tr></thead><tbody>"
                    
                    for idx, fila in enumerate(registros_dinamicos):
                        bg = "#ffffff" if idx % 2 == 0 else "#fcfdfe"
                        html_tabla += f'<tr style="background-color: {bg}; border-bottom: 1px solid #ebf0f5;">'
                        for col in columnas_db:
                            val = fila.get(col)
                            try:
                                if val is not None and isinstance(val, (int, float)):
                                    txt = f"{float(val):.2f}" if "pct" in col or "gb" in col or "red" in col or "_p" in col or "latencia" in col else f"{int(val)}"
                                else:
                                    txt = val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(val, "strftime") else str(val if val is not None else "-")
                            except (ValueError, TypeError):
                                txt = "-"
                            html_tabla += f'<td style="padding: 9px 14px; color: #333333; white-space: nowrap;">{txt}</td>'
                        html_tabla += "</tr>"
                    st.markdown(html_tabla + "</tbody></table></div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: ANALÍTICA (MÓDULO FRAGMENTADO COMPLETAMENTE SEGURO)
    # =========================================================================
    with tab_graficas:
        renderizar_pestaña_analitica_completa(opciones_servidores_tab2, opciones_componentes, servidores_activos)