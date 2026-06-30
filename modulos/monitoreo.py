import streamlit as st
import time
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
# FUNCIÓN PARA OBTENER SENSORES DISPONIBLES DE UN SERVIDOR
# =========================================================================
def obtener_sensores_disponibles(info_srv):
    """
    Retorna un diccionario con todos los sensores disponibles para un servidor.
    Solo incluye sensores con ID > 0.
    """
    sensores = {}
    
    # CPU
    if int(info_srv.get('id_sensor_cpu', 0) or 0) > 0:
        sensores['id_sensor_cpu'] = {'nombre': 'CPU', 'columna': 'val_cpu', 'id': int(info_srv.get('id_sensor_cpu', 0))}
    
    # RAM
    if int(info_srv.get('id_sensor_ram', 0) or 0) > 0:
        sensores['id_sensor_ram'] = {'nombre': 'RAM', 'columna': 'val_ram_disponible_pct', 'id': int(info_srv.get('id_sensor_ram', 0))}
    
    # RED - Total
    if int(info_srv.get('id_sensor_red_total', 0) or 0) > 0:
        sensores['id_sensor_red_total'] = {'nombre': 'Red Total', 'columna': 'val_red_total', 'id': int(info_srv.get('id_sensor_red_total', 0))}
    
    # RED - Entrante
    if int(info_srv.get('id_sensor_red_entrante', 0) or 0) > 0:
        sensores['id_sensor_red_entrante'] = {'nombre': 'Red Entrante', 'columna': 'val_red_entrante', 'id': int(info_srv.get('id_sensor_red_entrante', 0))}
    
    # RED - Saliente
    if int(info_srv.get('id_sensor_red_saliente', 0) or 0) > 0:
        sensores['id_sensor_red_saliente'] = {'nombre': 'Red Saliente', 'columna': 'val_red_saliente', 'id': int(info_srv.get('id_sensor_red_saliente', 0))}
    
    # LATENCIA
    if int(info_srv.get('id_sensor_latencia', 0) or 0) > 0:
        sensores['id_sensor_latencia'] = {'nombre': 'Latencia', 'columna': 'val_latencia_ping', 'id': int(info_srv.get('id_sensor_latencia', 0))}
    
    # DISCOS (C, D, E, F, G, Y)
    discos = ['disco_1', 'disco_2', 'disco_3', 'disco_4', 'disco_5', 'disco_6']
    letras_discos = ['C', 'D', 'E', 'F', 'G', 'Y']
    for idx, (disco, letra) in enumerate(zip(discos, letras_discos), 1):
        id_sensor = int(info_srv.get(f'id_sensor_{disco}', 0) or 0)
        if id_sensor > 0:
            sensores[f'id_sensor_{disco}'] = {
                'nombre': f'Disco {letra}',
                'columna': f'val_{disco}_pct_libre',
                'id': id_sensor,
                'letra': letra
            }
    
    # SERVICIOS (1-8)
    for i in range(1, 9):
        id_sensor = int(info_srv.get(f'id_sensor_servicio_{i}', 0) or 0)
        if id_sensor > 0:
            sensores[f'id_sensor_servicio_{i}'] = {
                'nombre': f'Servicio {i}',
                'columna': f'estado_servicio_{i}',
                'id': id_sensor
            }
    
    return sensores


# =========================================================================
# FUNCIÓN PARA OBTENER OPCIONES DE MÉTRICAS DISPONIBLES
# =========================================================================
def obtener_opciones_metricas(info_srv):
    """Retorna una lista de opciones de métricas disponibles para un servidor"""
    opciones = []
    
    if not info_srv:
        return opciones
    
    # RAM
    if int(info_srv.get('id_sensor_ram', 0) or 0) > 0:
        opciones.append("🧠 Variables de Memoria (RAM)")
    
    # CPU
    if int(info_srv.get('id_sensor_cpu', 0) or 0) > 0:
        opciones.append("⚙️ Variables de Procesamiento (CPU Cores)")
    
    # RED - si tiene al menos uno de los tres sensores
    if (int(info_srv.get('id_sensor_red_total', 0) or 0) > 0 or
        int(info_srv.get('id_sensor_red_entrante', 0) or 0) > 0 or
        int(info_srv.get('id_sensor_red_saliente', 0) or 0) > 0):
        opciones.append("🌐 Variables de Red")
    
    # LATENCIA
    if int(info_srv.get('id_sensor_latencia', 0) or 0) > 0:
        opciones.append("⏱️ Variables de Ping/Latencia")
    
    # DISCOS (C, D, E, F, G, Y) - cada disco es una opción separada
    discos = ['disco_1', 'disco_2', 'disco_3', 'disco_4', 'disco_5', 'disco_6']
    letras_discos = ['C', 'D', 'E', 'F', 'G', 'Y']
    for disco, letra in zip(discos, letras_discos):
        if int(info_srv.get(f'id_sensor_{disco}', 0) or 0) > 0:
            opciones.append(f"💽 Variables de Almacenamiento (Disco {letra})")
    
    return opciones


# =========================================================================
# FUNCIÓN PARA OBTENER COLUMNAS DE UNA MÉTRICA
# =========================================================================
def obtener_columnas_metrica(info_srv, seleccion_metrica):
    """Retorna la lista de columnas a mostrar para una métrica seleccionada"""
    columnas = []
    
    if seleccion_metrica == "🧠 Variables de Memoria (RAM)":
        if int(info_srv.get('id_sensor_ram', 0) or 0) > 0:
            columnas = ["val_ram_disponible_pct", "val_ram_disponible_gb", "val_ram_total_gb"]
    
    elif seleccion_metrica == "⚙️ Variables de Procesamiento (CPU Cores)":
        if int(info_srv.get('id_sensor_cpu', 0) or 0) > 0:
            columnas = ["val_cpu", "val_cpu_p1", "val_cpu_p2", "val_cpu_p3", "val_cpu_p4", 
                       "val_cpu_p5", "val_cpu_p6", "val_cpu_p7", "val_cpu_p8"]
    
    elif seleccion_metrica == "🌐 Variables de Red":
        # Mostrar TODOS los sensores de red registrados
        if int(info_srv.get('id_sensor_red_total', 0) or 0) > 0:
            columnas.append("val_red_total")
        if int(info_srv.get('id_sensor_red_entrante', 0) or 0) > 0:
            columnas.append("val_red_entrante")
        if int(info_srv.get('id_sensor_red_saliente', 0) or 0) > 0:
            columnas.append("val_red_saliente")
    
    elif seleccion_metrica == "⏱️ Variables de Ping/Latencia":
        if int(info_srv.get('id_sensor_latencia', 0) or 0) > 0:
            columnas = ["val_latencia_ping", "val_latencia_max", "val_latencia_min", "val_latencia_perdida"]
    
    elif seleccion_metrica.startswith("💽 Variables de Almacenamiento (Disco"):
        # Extraer la letra del disco de la selección
        import re
        match = re.search(r'Disco ([A-Z])', seleccion_metrica)
        if match:
            letra = match.group(1)
            # Mapear letra a índice de disco
            discos_map = {'C': 'disco_1', 'D': 'disco_2', 'E': 'disco_3', 
                         'F': 'disco_4', 'G': 'disco_5', 'Y': 'disco_6'}
            disco_key = discos_map.get(letra)
            if disco_key and int(info_srv.get(f'id_sensor_{disco_key}', 0) or 0) > 0:
                columnas = [f"val_{disco_key}_pct_libre", f"val_{disco_key}_libres_gb", f"val_{disco_key}_total_gb"]
    
    return columnas


# =========================================================================
# PESTAÑA 2 ENCAPSULADA EN UN FRAGMENTO (TIEMPO REAL DINÁMICO)
# =========================================================================
@st.fragment(run_every=30)
def renderizar_pestaña_analitica_completa(opciones_servidores_tab2, opciones_componentes, servidores_activos):
    # =============================================================
    # PROCESAR LIMPIEZA INMEDIATA DESDE SESSION_STATE
    # =============================================================
    if st.session_state.get("_limpiar_tab2", False):
        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"
        st.session_state["_limpiar_tab2"] = False
        st.rerun(scope="fragment")
        return

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
            st.session_state["_limpiar_tab2"] = True
            st.rerun(scope="fragment")
            return

    if not servidor_seleccionado_tab2:
        st.info("🖥️ Por favor, seleccione primero un Servidor Bajo Análisis para habilitar la selección de componentes.")
        return
    elif componente_sel == "-- Seleccione un Componente --":
        st.info("📈 Servidor listo. Ahora elija un área o componente del listado para proyectar sus métricas analíticas.")
        return

    info_srv = next((s for s in servidores_activos if s['nombre_alias'] == nombre_srv), None)
    if not info_srv:
        return

    # Obtener todos los sensores disponibles
    sensores = obtener_sensores_disponibles(info_srv)
    
    id_cpu = int(info_srv.get("id_sensor_cpu") or 0)
    id_ram = int(info_srv.get("id_sensor_ram") or 0)
    id_red_total = int(info_srv.get("id_sensor_red_total") or info_srv.get("id_sensor_red") or 0)
    id_red_entrante = int(info_srv.get("id_sensor_red_entrante") or 0)
    id_red_saliente = int(info_srv.get("id_sensor_red_saliente") or 0)
    id_latencia = int(info_srv.get("id_sensor_latencia") or 0)
    
    # Obtener IDs de discos
    discos_ids = {}
    for i in range(1, 7):
        discos_ids[f'disco_{i}'] = int(info_srv.get(f'id_sensor_disco_{i}') or 0)

    conexion = conectar_bd()
    datos_raw = []
    ultimo_registro = None
    if conexion:
        rango_desde = datetime.now() - timedelta(hours=4)
        cursor = None
        try:
            cursor = conexion.cursor(dictionary=True)
            
            cursor.execute(
                "SELECT fecha_registro FROM monitoreo WHERE ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 1",
                (info_srv['ip'],)
            )
            ultimo_registro = cursor.fetchone()
            
            # Construir query dinámica para incluir todas las columnas de discos
            columnas_discos = []
            for i in range(1, 7):
                if discos_ids.get(f'disco_{i}', 0) > 0:
                    columnas_discos.extend([
                        f'val_disco_{i}_total_gb',
                        f'val_disco_{i}_pct_libre',
                        f'val_disco_{i}_libres_gb'
                    ])
            
            query_graficas = (
                "SELECT fecha_registro, val_cpu, val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb, "
                + (", ".join(columnas_discos) if columnas_discos else "") +
                "val_red_total, val_red_entrante, val_red_saliente, "
                "val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida, "
                "val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8 "
                "FROM monitoreo WHERE ip_servidor = %s AND fecha_registro >= %s "
                "ORDER BY fecha_registro ASC LIMIT 50;"
            )
            cursor.execute(query_graficas, (info_srv['ip'], rango_desde))
            datos_raw = cursor.fetchall()
            
            if not datos_raw:
                query_historico_graficas = (
                    "SELECT fecha_registro, val_cpu, val_ram_total_gb, val_ram_disponible_pct, val_ram_disponible_gb, "
                    + (", ".join(columnas_discos) if columnas_discos else "") +
                    "val_red_total, val_red_entrante, val_red_saliente, "
                    "val_latencia_ping, val_latencia_max, val_latencia_min, val_latencia_perdida, "
                    "val_cpu_p1, val_cpu_p2, val_cpu_p3, val_cpu_p4, val_cpu_p5, val_cpu_p6, val_cpu_p7, val_cpu_p8 "
                    "FROM monitoreo WHERE ip_servidor = %s "
                    "ORDER BY fecha_registro DESC LIMIT 50;"
                )
                cursor.execute(query_historico_graficas, (info_srv['ip'],))
                datos_descendentes = cursor.fetchall()
                datos_raw = list(reversed(datos_descendentes))

        finally:
            if cursor:
                cursor.close()
            conexion.close()

    if not datos_raw:
        st.warning("⚠️ Sin registros de telemetría disponibles en la base de datos para este servidor.")
        return

    agente_activo = False
    if ultimo_registro and ultimo_registro.get('fecha_registro'):
        if isinstance(ultimo_registro['fecha_registro'], datetime):
            diferencia_tiempo = datetime.now() - ultimo_registro['fecha_registro']
            agente_activo = diferencia_tiempo.total_seconds() <= 60
            ultima_fecha = ultimo_registro['fecha_registro']
        else:
            ultima_fecha = datetime.now()
    else:
        ultima_fecha = datetime.now()

    config_sensores = []
    explicacion_comun = ""
    
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
            "* Muestra el desglose de velocidad y carga de paquetes según los sensores registrados (Total, Entrante o Saliente) en Mbit/s."
        )
        if id_red_total > 0:
            config_sensores.append({"col": "val_red_total", "titulo": "Tráfico Red Total", "sufijo": " Mbit/s", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#00b2b2"})
        if id_red_entrante > 0:
            config_sensores.append({"col": "val_red_entrante", "titulo": "Tráfico Entrante (RX)", "sufijo": " Mbit/s", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#32cd32"})
        if id_red_saliente > 0:
            config_sensores.append({"col": "val_red_saliente", "titulo": "Tráfico Saliente (TX)", "sufijo": " Mbit/s", "max_y": 120, "umbral": 90, "color_u": "#ffb600", "color_linea": "#1e90ff"})
        
        if not config_sensores:
            st.warning("📴 No hay sensores de red registrados para este servidor.")
            return

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

    elif componente_sel.startswith("💽 Almacenamiento (Disco"):
        # Extraer la letra del disco
        import re
        match = re.search(r'Disco ([A-Z])', componente_sel)
        if match:
            letra = match.group(1)
            discos_map = {'C': 'disco_1', 'D': 'disco_2', 'E': 'disco_3', 
                         'F': 'disco_4', 'G': 'disco_5', 'Y': 'disco_6'}
            disco_key = discos_map.get(letra)
            id_disco = int(info_srv.get(f'id_sensor_{disco_key}', 0) or 0)
            
            if id_disco > 0:
                explicacion_comun = (
                    f"💡 **¿Qué estamos midiendo aquí?** Estado del disco {letra} del servidor.\n\n"
                    f"* **Gráfica 1 (Disco {letra}: Espacio Libre %):** Cuota disponible de forma porcentual.\n"
                    f"* **Gráfica 2 (Disco {letra}: Gigabytes Libres):** Almacenamiento físico bruto disponible."
                )
                total_gb = float(datos_raw[-1].get(f'val_{disco_key}_total_gb') or 100)
                config_sensores = [
                    {"col": f"val_{disco_key}_pct_libre", "titulo": f"Disco {letra}: Espacio Libre %", "sufijo": "%", "max_y": 100, "umbral": 20, "color_u": "#ffb600", "color_linea": "#712cb0"},
                    {"col": f"val_{disco_key}_libres_gb", "titulo": f"Disco {letra}: Gigabytes Libres", "sufijo": " GB", "max_y": int(total_gb) + 20, "umbral": 15, "color_u": "#d40000", "color_linea": "#d40000"}
                ]

    num_sensores = len(config_sensores)
    if num_sensores == 0:
        st.warning("📴 Este componente no posee sensores registrados o activos en la tabla servidores para este nodo.")
        return

    cols_dashboard = st.columns(num_sensores)
    
    if agente_activo:
        st.markdown('<p style="font-size: 11px; color: #47a323; margin-bottom: 5px; text-align: right;">🟢 <b>Live Feed Activo</b> — Actualizando datos cada 30s</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="font-size: 11px; color: #d40000; margin-bottom: 5px; text-align: right;">⚠️ <b>Agente Desconectado (Offline)</b> — Mostrando últimos datos estáticos ({ultima_fecha.strftime("%Y-%m-%d %H:%M:%S")})</p>', unsafe_allow_html=True)

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
# FUNCIÓN PARA RENDERIZAR LA TABLA DE HISTÓRICO CON AUTO-REFRESH
# =========================================================================
@st.fragment(run_every=30)
def renderizar_tabla_historico(seleccion_srv, seleccion_metrica, servidores_activos, dict_ip_a_nombre, mapa_columnas):
    """Renderiza la tabla de histórico con auto-refresh cada 30 segundos"""
    
    info_srv_actual = next((s for s in servidores_activos if s['nombre_alias'] == seleccion_srv), None)
    es_vista_global = (seleccion_srv == "-- Todos los Servidores --")
    
    if not info_srv_actual and not es_vista_global:
        st.warning("⚠️ Servidor no encontrado.")
        return
    
    # Obtener columnas a mostrar según la métrica seleccionada
    columnas_mostrar = obtener_columnas_metrica(info_srv_actual, seleccion_metrica)
    
    if not columnas_mostrar:
        st.warning("⚠️ No hay sensores registrados para las métricas seleccionadas en este servidor.")
        return
    
    conexion = conectar_bd()
    registros_dinamicos = []
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor(dictionary=True)
            
            # Construir la consulta SQL
            columnas_sql = ["fecha_registro"]
            if es_vista_global:
                columnas_sql.insert(0, "ip_servidor")
            
            columnas_sql.extend(columnas_mostrar)
            
            query = f"SELECT {', '.join(columnas_sql)} FROM monitoreo "
            
            if es_vista_global:
                query += "ORDER BY fecha_registro DESC LIMIT 150;"
            else:
                query += "WHERE ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 150;"
                cursor.execute(query, (info_srv_actual['ip'],))
            
            registros_dinamicos = cursor.fetchall()
            
        except Exception as e:
            st.error(f"❌ Error al consultar la base de datos: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            conexion.close()

    if registros_dinamicos:
        # Construir columnas para la tabla
        columnas_tabla = []
        if es_vista_global:
            columnas_tabla.append("identificador_servidor")
        columnas_tabla.append("fecha_registro")
        columnas_tabla.extend(columnas_mostrar)

        html_tabla = """<div style="overflow: auto; max-height: 480px; width: 100%; border: 1px solid #d1d8e0; border-radius: 4px;"><table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', sans-serif; font-size: 12px; background-color: white;"><thead><tr>"""
        for col in columnas_tabla:
            html_tabla += f'<th style="position: sticky; top: 0; background-color: #002244; padding: 11px 14px; color: #ffffff; text-align: left; font-weight: 600; font-size: 11px; white-space: nowrap; z-index: 10; border-bottom: 2px solid #001122;">{mapa_columnas.get(col, col.upper())}</th>'
        html_tabla += "</tr></thead><tbody>"
        
        for idx, fila in enumerate(registros_dinamicos):
            bg = "#ffffff" if idx % 2 == 0 else "#fcfdfe"
            html_tabla += f'<tr style="background-color: {bg}; border-bottom: 1px solid #ebf0f5;">'
            for col in columnas_tabla:
                if col == "identificador_servidor":
                    ip_raw = fila.get("ip_servidor", "-")
                    alias_srv = dict_ip_a_nombre.get(ip_raw, "Desconocido")
                    val = f"🖥️ {alias_srv} ({ip_raw})"
                else:
                    val = fila.get(col)
                    
                try:
                    if val is not None and isinstance(val, (int, float)):
                        txt = f"{float(val):.2f}" if "pct" in col or "gb" in col or "red" in col or "_p" in col or "latencia" in col else f"{int(val)}"
                    else:
                        txt = val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(val, "strftime") else str(val if val is not None else "-")
                except (ValueError, TypeError):
                    txt = "-"
                
                align_style = 'text-align: left;'
                if val is not None and isinstance(val, (int, float)):
                    align_style = 'text-align: right; font-family: monospace;'
                elif col == "identificador_servidor":
                    align_style = 'text-align: left; font-weight: bold; color: #003366;'
                
                html_tabla += f'<td style="padding: 9px 14px; color: #333333; white-space: nowrap; {align_style}">{txt}</td>'
            html_tabla += "</tr>"
        st.markdown(html_tabla + "</tbody></table></div>", unsafe_allow_html=True)
    else:
        st.warning("🚫 No hay datos de telemetría registrados para este servidor.")


# =========================================================================
# VISTA PRINCIPAL DEL MÓDULO
# =========================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    # Estilos
    st.markdown("""
        <style>
            /* Estilo para el texto del analista - MÁS GRANDE */
            .info-analista-monitoreo {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-monitoreo span {
                color: #003366;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    st.markdown('<h3 style="color:#003366; margin:0px; font-size:20px;">🖥️ Centro de Control y Telemetría</h3>', unsafe_allow_html=True)
    
    # ==========================================================================
    # MOSTRAR ANALISTA EN SESIÓN - DEBAJO DEL TÍTULO, MÁS GRANDE
    # ==========================================================================
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-monitoreo">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # =========================================================================
    # INICIALIZAR ESTADOS BASE - SIEMPRE PRIMERO
    # =========================================================================
    if "sb_srv_tab1" not in st.session_state:
        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
    if "sb_metrica_tab1" not in st.session_state:
        st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
    if "sb_graf_srv" not in st.session_state:
        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
    if "sb_graf_sensor" not in st.session_state:
        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"

    # =========================================================================
    # PROCESAR REDIRECCIÓN DESDE QUERY_PARAMS
    # =========================================================================
    if "srv" in st.query_params:
        srv_redireccionado = st.query_params.get("srv")
        try:
            del st.query_params["srv"]
        except:
            pass
        
        if srv_redireccionado:
            servidores_temp = obtener_lista_servidores()
            nombres_validos = [s['nombre_alias'] for s in servidores_temp if s.get('nombre_alias')]
            
            if srv_redireccionado in nombres_validos:
                st.session_state["sb_srv_tab1"] = srv_redireccionado
                st.session_state["sb_graf_srv"] = srv_redireccionado
                st.session_state["sb_graf_sensor"] = "🧠 Memoria (RAM)"
                st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
                
                if not st.session_state.get("_srv_mensaje_mostrado", False):
                    st.success(f"✅ Redirigido al servidor: **{srv_redireccionado}**")
                    st.session_state["_srv_mensaje_mostrado"] = True
            else:
                st.warning(f"⚠️ El servidor '{srv_redireccionado}' no existe en la base de datos.")

    servidores_activos = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores_activos if s.get('nombre_alias')])))
    
    opciones_servidores_tab1 = ["-- Seleccione un Servidor para empezar --", "-- Todos los Servidores --"] + lista_nombres_bd
    opciones_servidores_tab2 = ["-- Seleccione un Servidor --"] + lista_nombres_bd
    
    dict_ip_a_nombre = {s['ip']: s['nombre_alias'] for s in servidores_activos if s.get('ip')}

    mapa_columnas = {
        "identificador_servidor": "SERVIDOR (ALIAS / IP)",
        "fecha_registro": "FECHA REGISTRO", 
        "val_cpu": "USO CPU GLOBAL (%)",
        "val_ram_total_gb": "RAM TOTAL (GB)",
        "val_ram_disponible_pct": "RAM DISPONIBLE (%)",
        "val_ram_disponible_gb": "RAM LIBRE (GB)",
        "val_disco_1_pct_libre": "DISCO C LIBRE (%)",
        "val_disco_1_libres_gb": "DISCO C LIBRE (GB)",
        "val_disco_1_total_gb": "DISCO C TOTAL (GB)",
        "val_disco_2_pct_libre": "DISCO D LIBRE (%)",
        "val_disco_2_libres_gb": "DISCO D LIBRE (GB)",
        "val_disco_2_total_gb": "DISCO D TOTAL (GB)",
        "val_disco_3_pct_libre": "DISCO E LIBRE (%)",
        "val_disco_3_libres_gb": "DISCO E LIBRE (GB)",
        "val_disco_3_total_gb": "DISCO E TOTAL (GB)",
        "val_disco_4_pct_libre": "DISCO F LIBRE (%)",
        "val_disco_4_libres_gb": "DISCO F LIBRE (GB)",
        "val_disco_4_total_gb": "DISCO F TOTAL (GB)",
        "val_disco_5_pct_libre": "DISCO G LIBRE (%)",
        "val_disco_5_libres_gb": "DISCO G LIBRE (GB)",
        "val_disco_5_total_gb": "DISCO G TOTAL (GB)",
        "val_disco_6_pct_libre": "DISCO Y LIBRE (%)",
        "val_disco_6_libres_gb": "DISCO Y LIBRE (GB)",
        "val_disco_6_total_gb": "DISCO Y TOTAL (GB)",
        "val_red_total": "RED TOTAL (Mbit/s)",
        "val_red_entrante": "RED ENTRANTE (Mbit/s)",
        "val_red_saliente": "RED SALIENTE (Mbit/s)",
        "val_latencia_ping": "LATENCIA PROMEDIO (ms)",
        "val_latencia_max": "LATENCIA MAXIMA (ms)",
        "val_latencia_min": "LATENCIA MINIMA (ms)",
        "val_latencia_perdida": "PERDIDA PAQUETES (%)",
        "val_cpu_p1": "CPU CORE 1 (%)",
        "val_cpu_p2": "CPU CORE 2 (%)",
        "val_cpu_p3": "CPU CORE 3 (%)",
        "val_cpu_p4": "CPU CORE 4 (%)",
        "val_cpu_p5": "CPU CORE 5 (%)",
        "val_cpu_p6": "CPU CORE 6 (%)",
        "val_cpu_p7": "CPU CORE 7 (%)",
        "val_cpu_p8": "CPU CORE 8 (%)"
    }

    # Opciones de componentes para la pestaña de gráficas
    opciones_componentes_base = [
        "-- Seleccione un Componente --", 
        "🧠 Memoria (RAM)", 
        "⚙️ Procesamiento (Solo CPU)", 
        "🌐 Tráfico de Red",
        "⏳ Latencia de Respuesta (Ping)"
    ]
    
    # Agregar discos dinámicamente según el servidor seleccionado
    # Esto se hace en la pestaña de gráficas directamente

    tab_historico, tab_graficas = st.tabs(
        ["📊 Histórico Telemetría", "📈 Variables por Componente"],
        key="controlador_pestañas_monitoreo"
    )

    with tab_historico:
        if not servidores_activos:
            st.info("💡 No hay servidores activos mapeados en la base de datos.")
        else:
            col_srv, col_metrica, col_limpiar = st.columns([3, 2, 1])
            
            with col_srv:
                st.selectbox(
                    "Filtrar Servidor Historial", 
                    options=opciones_servidores_tab1, 
                    key="sb_srv_tab1", 
                    on_change=callback_cambio_servidor_tab1, 
                    label_visibility="collapsed"
                )
            
            with col_limpiar:
                if st.button("🧹 Limpiar filtro", key="btn_limpiar_tab1", use_container_width=True):
                    if "_srv_mensaje_mostrado" in st.session_state:
                        del st.session_state["_srv_mensaje_mostrado"]
                    st.rerun()
            
            seleccion_srv = st.session_state["sb_srv_tab1"]
            servidor_seleccionado_tab1 = (seleccion_srv != "-- Seleccione un Servidor para empezar --")
            
            with col_metrica:
                if servidor_seleccionado_tab1:
                    info_srv_metricas = next((s for s in servidores_activos if s['nombre_alias'] == seleccion_srv), None)
                    
                    opciones_metricas_disponibles = obtener_opciones_metricas(info_srv_metricas)
                    
                    if not opciones_metricas_disponibles:
                        st.selectbox(
                            "Filtrar Métrica Rejilla", 
                            options=["-- Sin sensores registrados --"], 
                            key="sb_metrica_tab1", 
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    else:
                        opciones_metricas_con_placeholder = ["📊 Todas las Métricas"] + opciones_metricas_disponibles
                        st.selectbox(
                            "Filtrar Métrica Rejilla", 
                            options=opciones_metricas_con_placeholder, 
                            key="sb_metrica_tab1", 
                            label_visibility="collapsed"
                        )
                else:
                    st.selectbox(
                        "Filtrar Métrica Rejilla", 
                        options=["-- Seleccione un Servidor primero --"], 
                        key="sb_metrica_tab1", 
                        disabled=True,
                        label_visibility="collapsed"
                    )

            seleccion_metrica = st.session_state["sb_metrica_tab1"]
            metrica_seleccionada = (seleccion_metrica != "📊 Todas las Métricas" and 
                                   seleccion_metrica != "-- Seleccione un Servidor primero --" and
                                   seleccion_metrica != "-- Sin sensores registrados --")
            
            if not servidor_seleccionado_tab1:
                st.info("🔍 Por favor, seleccione un servidor del listado para habilitar los filtros de métricas.")
            
            elif seleccion_metrica == "-- Sin sensores registrados --":
                st.warning("⚠️ Este servidor no tiene sensores registrados en la base de datos.")
            
            elif not metrica_seleccionada:
                st.info("📊 Por favor, seleccione una métrica específica para desplegar la rejilla de datos.")
            
            else:
                renderizar_tabla_historico(seleccion_srv, seleccion_metrica, servidores_activos, dict_ip_a_nombre, mapa_columnas)

    with tab_graficas:
        # Construir opciones de componentes incluyendo discos detectados
        opciones_componentes_dinamicas = opciones_componentes_base.copy()
        
        # Si hay un servidor seleccionado, agregar sus discos
        nombre_srv_graf = st.session_state.get("sb_graf_srv", "-- Seleccione un Servidor --")
        if nombre_srv_graf != "-- Seleccione un Servidor --":
            info_srv_graf = next((s for s in servidores_activos if s['nombre_alias'] == nombre_srv_graf), None)
            if info_srv_graf:
                # Agregar discos disponibles
                discos_map = {'disco_1': 'C', 'disco_2': 'D', 'disco_3': 'E', 
                             'disco_4': 'F', 'disco_5': 'G', 'disco_6': 'Y'}
                for disco_key, letra in discos_map.items():
                    if int(info_srv_graf.get(f'id_sensor_{disco_key}', 0) or 0) > 0:
                        opciones_componentes_dinamicas.append(f"💽 Almacenamiento (Disco {letra})")
        
        renderizar_pestaña_analitica_completa(
            opciones_servidores_tab2, 
            opciones_componentes_dinamicas, 
            servidores_activos
        )