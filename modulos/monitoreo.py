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
# FUNCIÓN PARA OBTENER OPCIONES DE MÉTRICAS GLOBALES
# =========================================================================
def obtener_opciones_metricas_globales(servidores_activos):
    """
    Retorna las opciones de métricas que están disponibles en AL MENOS UN servidor
    para la vista global.
    """
    opciones_set = set()
    
    for srv in servidores_activos:
        # RAM
        if int(srv.get('id_sensor_ram', 0) or 0) > 0:
            opciones_set.add("🧠 Variables de Memoria (RAM)")
        
        # CPU
        if int(srv.get('id_sensor_cpu', 0) or 0) > 0:
            opciones_set.add("⚙️ Variables de Procesamiento (CPU Cores)")
        
        # RED
        if (int(srv.get('id_sensor_red_total', 0) or 0) > 0 or
            int(srv.get('id_sensor_red_entrante', 0) or 0) > 0 or
            int(srv.get('id_sensor_red_saliente', 0) or 0) > 0):
            opciones_set.add("🌐 Variables de Red")
        
        # LATENCIA
        if int(srv.get('id_sensor_latencia', 0) or 0) > 0:
            opciones_set.add("⏱️ Variables de Ping/Latencia")
        
        # DISCOS
        discos = ['disco_1', 'disco_2', 'disco_3', 'disco_4', 'disco_5', 'disco_6']
        letras_discos = ['C', 'D', 'E', 'F', 'G', 'Y']
        for disco, letra in zip(discos, letras_discos):
            if int(srv.get(f'id_sensor_{disco}', 0) or 0) > 0:
                opciones_set.add(f"💽 Variables de Almacenamiento (Disco {letra})")
    
    return sorted(list(opciones_set))


# =========================================================================
# FUNCIÓN PARA OBTENER COLUMNAS DE UNA MÉTRICA
# =========================================================================
def obtener_columnas_metrica(info_srv, seleccion_metrica):
    """Retorna la lista de columnas a mostrar para una métrica seleccionada"""
    columnas = []
    
    # =============================================================
    # CASO: "Todas las Métricas" - devolver TODAS las columnas
    # =============================================================
    if seleccion_metrica == "📊 Todas las Métricas":
        # CPU
        if int(info_srv.get('id_sensor_cpu', 0) or 0) > 0:
            columnas.append("val_cpu")
            for i in range(1, 9):
                columnas.append(f"val_cpu_p{i}")
        
        # RAM
        if int(info_srv.get('id_sensor_ram', 0) or 0) > 0:
            columnas.extend(["val_ram_total_gb", "val_ram_disponible_gb", "val_ram_disponible_pct"])
        
        # RED
        if int(info_srv.get('id_sensor_red_total', 0) or 0) > 0:
            columnas.append("val_red_total")
        if int(info_srv.get('id_sensor_red_entrante', 0) or 0) > 0:
            columnas.append("val_red_entrante")
        if int(info_srv.get('id_sensor_red_saliente', 0) or 0) > 0:
            columnas.append("val_red_saliente")
        
        # LATENCIA
        if int(info_srv.get('id_sensor_latencia', 0) or 0) > 0:
            columnas.extend(["val_latencia_ping", "val_latencia_max", "val_latencia_min", "val_latencia_perdida"])
        
        # DISCOS
        for i in range(1, 7):
            if int(info_srv.get(f'id_sensor_disco_{i}', 0) or 0) > 0:
                columnas.extend([
                    f"val_disco_{i}_total_gb",
                    f"val_disco_{i}_pct_libre",
                    f"val_disco_{i}_libres_gb"
                ])
        
        return columnas
    
    # =============================================================
    # CASOS ESPECÍFICOS
    # =============================================================
    if seleccion_metrica == "🧠 Variables de Memoria (RAM)":
        if int(info_srv.get('id_sensor_ram', 0) or 0) > 0:
            columnas = ["val_ram_disponible_pct", "val_ram_disponible_gb", "val_ram_total_gb"]
    
    elif seleccion_metrica == "⚙️ Variables de Procesamiento (CPU Cores)":
        if int(info_srv.get('id_sensor_cpu', 0) or 0) > 0:
            columnas = ["val_cpu", "val_cpu_p1", "val_cpu_p2", "val_cpu_p3", "val_cpu_p4", 
                       "val_cpu_p5", "val_cpu_p6", "val_cpu_p7", "val_cpu_p8"]
    
    elif seleccion_metrica == "🌐 Variables de Red":
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
        import re
        match = re.search(r'Disco ([A-Z])', seleccion_metrica)
        if match:
            letra = match.group(1)
            discos_map = {'C': 'disco_1', 'D': 'disco_2', 'E': 'disco_3', 
                         'F': 'disco_4', 'G': 'disco_5', 'Y': 'disco_6'}
            disco_key = discos_map.get(letra)
            if disco_key and int(info_srv.get(f'id_sensor_{disco_key}', 0) or 0) > 0:
                columnas = [f"val_{disco_key}_pct_libre", f"val_{disco_key}_libres_gb", f"val_{disco_key}_total_gb"]
    
    return columnas


# =========================================================================
# FUNCIÓN PARA OBTENER COLUMNAS GLOBALES (PARA VISTA "TODOS LOS SERVIDORES")
# =========================================================================
def obtener_columnas_globales(servidores_activos):
    """
    Retorna todas las columnas de métricas disponibles en cualquier servidor
    para la vista "-- Todos los Servidores --"
    """
    columnas = set()
    
    for srv in servidores_activos:
        # CPU
        if int(srv.get('id_sensor_cpu', 0) or 0) > 0:
            columnas.add("val_cpu")
            for i in range(1, 9):
                columnas.add(f"val_cpu_p{i}")
        
        # RAM
        if int(srv.get('id_sensor_ram', 0) or 0) > 0:
            columnas.add("val_ram_total_gb")
            columnas.add("val_ram_disponible_gb")
            columnas.add("val_ram_disponible_pct")
        
        # RED
        if int(srv.get('id_sensor_red_total', 0) or 0) > 0:
            columnas.add("val_red_total")
        if int(srv.get('id_sensor_red_entrante', 0) or 0) > 0:
            columnas.add("val_red_entrante")
        if int(srv.get('id_sensor_red_saliente', 0) or 0) > 0:
            columnas.add("val_red_saliente")
        
        # LATENCIA
        if int(srv.get('id_sensor_latencia', 0) or 0) > 0:
            columnas.add("val_latencia_ping")
            columnas.add("val_latencia_max")
            columnas.add("val_latencia_min")
            columnas.add("val_latencia_perdida")
        
        # DISCOS
        for i in range(1, 7):
            if int(srv.get(f'id_sensor_disco_{i}', 0) or 0) > 0:
                columnas.add(f"val_disco_{i}_total_gb")
                columnas.add(f"val_disco_{i}_pct_libre")
                columnas.add(f"val_disco_{i}_libres_gb")
    
    return sorted(list(columnas))


# =========================================================================
# PESTAÑA 2 ENCAPSULADA EN UN FRAGMENTO (SIN FILTROS INTERNOS)
# =========================================================================
@st.fragment(run_every=30)
def renderizar_pestaña_analitica_completa(opciones_servidores_tab2, opciones_componentes, servidores_activos):
    """
    Renderiza las gráficas de la pestaña 2 usando los filtros ya aplicados.
    Este fragmento NO tiene filtros internos para evitar duplicación.
    """
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
            
            # =============================================================
            # CONSTRUIR QUERY CORRECTAMENTE
            # =============================================================
            # Columnas fijas siempre presentes
            columnas_fijas = [
                "fecha_registro", "val_cpu", "val_ram_total_gb", 
                "val_ram_disponible_pct", "val_ram_disponible_gb",
                "val_red_total", "val_red_entrante", "val_red_saliente",
                "val_latencia_ping", "val_latencia_max", "val_latencia_min", "val_latencia_perdida",
                "val_cpu_p1", "val_cpu_p2", "val_cpu_p3", "val_cpu_p4", 
                "val_cpu_p5", "val_cpu_p6", "val_cpu_p7", "val_cpu_p8"
            ]
            
            # Agregar columnas de discos si existen
            columnas_discos = []
            for i in range(1, 7):
                if discos_ids.get(f'disco_{i}', 0) > 0:
                    columnas_discos.extend([
                        f'val_disco_{i}_total_gb',
                        f'val_disco_{i}_pct_libre',
                        f'val_disco_{i}_libres_gb'
                    ])
            
            if columnas_discos:
                columnas_fijas.extend(columnas_discos)
            
            # Construir query final
            query_graficas = (
                f"SELECT {', '.join(columnas_fijas)} "
                "FROM monitoreo WHERE ip_servidor = %s AND fecha_registro >= %s "
                "ORDER BY fecha_registro ASC LIMIT 50;"
            )
            
            cursor.execute(query_graficas, (info_srv['ip'], rango_desde))
            datos_raw = cursor.fetchall()
            
            if not datos_raw:
                # Query histórica (sin filtro de fecha)
                query_historico_graficas = (
                    f"SELECT {', '.join(columnas_fijas)} "
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
    es_todas_metricas = (seleccion_metrica == "📊 Todas las Métricas")
    
    # =============================================================
    # OBTENER COLUMNAS A MOSTRAR
    # =============================================================
    if es_vista_global:
        if es_todas_metricas:
            # Todas las métricas de todos los servidores
            columnas_mostrar = obtener_columnas_globales(servidores_activos)
        else:
            # Métrica específica en vista global
            # Obtener columnas para cada servidor y unirlas
            columnas_set = set()
            for srv in servidores_activos:
                columnas_srv = obtener_columnas_metrica(srv, seleccion_metrica)
                columnas_set.update(columnas_srv)
            columnas_mostrar = sorted(list(columnas_set))
        
        # Filtrar solo columnas que existen en la tabla
        try:
            conexion = conectar_bd()
            if conexion:
                cursor = conexion.cursor()
                cursor.execute("SHOW COLUMNS FROM monitoreo")
                columnas_tabla = [row[0] for row in cursor.fetchall()]
                cursor.close()
                conexion.close()
                
                columnas_mostrar = [col for col in columnas_mostrar if col in columnas_tabla]
        except:
            pass
    else:
        if not info_srv_actual:
            st.warning("⚠️ Servidor no encontrado.")
            return
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
            if es_vista_global:
                columnas_sql = ["ip_servidor", "fecha_registro"]
                columnas_sql.extend(columnas_mostrar)
                
                query = f"SELECT {', '.join(columnas_sql)} FROM monitoreo ORDER BY fecha_registro DESC LIMIT 200;"
                cursor.execute(query)
            else:
                columnas_sql = ["fecha_registro"]
                columnas_sql.extend(columnas_mostrar)
                query = f"SELECT {', '.join(columnas_sql)} FROM monitoreo WHERE ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 150;"
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

        # Crear la tabla HTML
        html_tabla = """
        <div style="overflow: auto; max-height: 480px; width: 100%; border: 1px solid #d1d8e0; border-radius: 4px;">
            <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', sans-serif; font-size: 12px; background-color: white;">
                <thead><tr>
        """
        
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
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-monitoreo">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # =========================================================================
    # INICIALIZAR ESTADOS BASE
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
    # ESTADOS PARA FILTROS APLICADOS
    # =========================================================================
    if "filtro_aplicado_tab1" not in st.session_state:
        st.session_state["filtro_aplicado_tab1"] = False
    if "filtro_aplicado_tab2" not in st.session_state:
        st.session_state["filtro_aplicado_tab2"] = False
    if "sb_srv_tab1_temp" not in st.session_state:
        st.session_state["sb_srv_tab1_temp"] = "-- Seleccione un Servidor para empezar --"
    if "sb_metrica_tab1_temp" not in st.session_state:
        st.session_state["sb_metrica_tab1_temp"] = "📊 Todas las Métricas"
    if "sb_graf_srv_temp" not in st.session_state:
        st.session_state["sb_graf_srv_temp"] = "-- Seleccione un Servidor --"
    if "sb_graf_sensor_temp" not in st.session_state:
        st.session_state["sb_graf_sensor_temp"] = "-- Seleccione un Componente --"
    if "tab_servidores_activa" not in st.session_state:
        st.session_state.tab_servidores_activa = 0

    # =========================================================================
    # PROCESAR LIMPIEZA DE FILTROS VIA QUERY_PARAMS
    # =========================================================================
    if "_limpiar_tab1" in st.query_params and st.query_params["_limpiar_tab1"] == "1":
        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
        st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
        st.session_state["filtro_aplicado_tab1"] = False
        if "_srv_mensaje_mostrado" in st.session_state:
            del st.session_state["_srv_mensaje_mostrado"]
        if "_srv_select" in st.query_params:
            del st.query_params["_srv_select"]
        if "_metrica_select" in st.query_params:
            del st.query_params["_metrica_select"]
        del st.query_params["_limpiar_tab1"]
        st.rerun()

    if "_limpiar_tab2_global" in st.query_params and st.query_params["_limpiar_tab2_global"] == "1":
        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"
        st.session_state["filtro_aplicado_tab2"] = False
        if "_srv_mensaje_mostrado" in st.session_state:
            del st.session_state["_srv_mensaje_mostrado"]
        del st.query_params["_limpiar_tab2_global"]
        st.rerun()

    # =========================================================================
    # DETECTAR REDIRECCIÓN DESDE SERVIDORES (PARÁMETRO "srv" EN URL)
    # =========================================================================
    srv_desde_url = st.query_params.get("srv")
    if srv_desde_url and not st.session_state.get("_srv_redirect_pending"):
        st.session_state["_srv_redirect_pending"] = srv_desde_url

    # =========================================================================
    # PROCESAR REDIRECCIÓN DESDE SERVIDORES.PY
    # =========================================================================
    if "_srv_redirect_pending" in st.session_state and st.session_state["_srv_redirect_pending"]:
        srv_redireccionado = st.session_state["_srv_redirect_pending"]
        
        # Verificar que el servidor existe
        try:
            conn = conectar_bd()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT nombre_alias FROM servidores WHERE nombre_alias = %s", (srv_redireccionado,))
                existe = cursor.fetchone()
                cursor.close()
                conn.close()
            else:
                existe = None
        except Exception as e:
            st.error(f"Error al verificar servidor: {e}")
            existe = None
        
        if existe:
            # Establecer los estados (NO modificar widgets)
            st.session_state["sb_srv_tab1"] = srv_redireccionado
            st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
            st.session_state["filtro_aplicado_tab1"] = True
            st.session_state["_srv_mensaje_mostrado"] = True
            
            # Limpiar el flag
            st.session_state["_srv_redirect_pending"] = False
            
            # Eliminar el parámetro de la URL
            if "srv" in st.query_params:
                del st.query_params["srv"]
            
            # Forzar actualización
            st.rerun()
        else:
            st.warning(f"⚠️ El servidor '{srv_redireccionado}' no existe en la base de datos.")
            st.session_state["_srv_redirect_pending"] = False
            if "srv" in st.query_params:
                del st.query_params["srv"]

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

    # =========================================================================
    # CREAR PESTAÑAS
    # =========================================================================
    tab_historico, tab_graficas = st.tabs(
        ["📊 Histórico Telemetría", "📈 Variables por Componente"],
        key="controlador_pestañas_monitoreo"
    )

    with tab_historico:
        if not servidores_activos:
            st.info("💡 No hay servidores activos mapeados en la base de datos.")
        else:
            # =============================================================
            # FILTROS CON BOTON "FILTRAR" - PESTAÑA 1
            # =============================================================
            col_srv, col_metrica, col_filtrar, col_limpiar = st.columns([3, 2, 1, 1])
            
            with col_srv:
                # Determinar el índice basado en el valor actual
                default_index = 0
                if st.session_state.get("sb_srv_tab1_temp") in opciones_servidores_tab1:
                    default_index = opciones_servidores_tab1.index(st.session_state["sb_srv_tab1_temp"])
                else:
                    default_index = 0
                
                if default_index >= len(opciones_servidores_tab1):
                    default_index = 0
                
                st.selectbox(
                    "Filtrar Servidor Historial", 
                    options=opciones_servidores_tab1, 
                    key="sb_srv_tab1_temp",
                    label_visibility="collapsed",
                    index=default_index
                )
            
            with col_metrica:
                seleccion_srv_temp = st.session_state["sb_srv_tab1_temp"]
                servidor_seleccionado_temp = (seleccion_srv_temp != "-- Seleccione un Servidor para empezar --")
                es_vista_global_temp = (seleccion_srv_temp == "-- Todos los Servidores --")
                
                # Determinar el índice de métrica
                default_metrica_index = 0
                
                # Si es vista global, mostrar opciones de métricas globales
                if es_vista_global_temp:
                    opciones_metricas_globales = obtener_opciones_metricas_globales(servidores_activos)
                    opciones_metricas_con_placeholder = ["📊 Todas las Métricas"] + opciones_metricas_globales
                    
                    if st.session_state.get("sb_metrica_tab1_temp") in opciones_metricas_con_placeholder:
                        default_metrica_index = opciones_metricas_con_placeholder.index(st.session_state["sb_metrica_tab1_temp"])
                    
                    st.selectbox(
                        "Filtrar Métrica Rejilla", 
                        options=opciones_metricas_con_placeholder, 
                        key="sb_metrica_tab1_temp",
                        label_visibility="collapsed",
                        index=default_metrica_index
                    )
                elif servidor_seleccionado_temp:
                    info_srv_metricas = next((s for s in servidores_activos if s['nombre_alias'] == seleccion_srv_temp), None)
                    opciones_metricas_disponibles = obtener_opciones_metricas(info_srv_metricas)
                    
                    if not opciones_metricas_disponibles:
                        st.selectbox(
                            "Filtrar Métrica Rejilla", 
                            options=["-- Sin sensores registrados --"], 
                            key="sb_metrica_tab1_temp",
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    else:
                        opciones_metricas_con_placeholder = ["📊 Todas las Métricas"] + opciones_metricas_disponibles
                        
                        if st.session_state.get("sb_metrica_tab1_temp") in opciones_metricas_con_placeholder:
                            default_metrica_index = opciones_metricas_con_placeholder.index(st.session_state["sb_metrica_tab1_temp"])
                        
                        st.selectbox(
                            "Filtrar Métrica Rejilla", 
                            options=opciones_metricas_con_placeholder, 
                            key="sb_metrica_tab1_temp",
                            label_visibility="collapsed",
                            index=default_metrica_index
                        )
                else:
                    st.selectbox(
                        "Filtrar Métrica Rejilla", 
                        options=["-- Seleccione un Servidor primero --"], 
                        key="sb_metrica_tab1_temp",
                        disabled=True,
                        label_visibility="collapsed"
                    )
            
            with col_filtrar:
                if st.button("🔍 Filtrar", key="btn_filtrar_tab1", use_container_width=True):
                    st.session_state["sb_srv_tab1"] = st.session_state["sb_srv_tab1_temp"]
                    st.session_state["sb_metrica_tab1"] = st.session_state["sb_metrica_tab1_temp"]
                    st.session_state["filtro_aplicado_tab1"] = True
                    # IMPORTANTE: NO forzar tab_servidores aquí
                    st.rerun()
            
            with col_limpiar:
                if st.button("🧹 Limpiar", key="btn_limpiar_tab1", use_container_width=True):
                    st.query_params["_limpiar_tab1"] = "1"
                    # IMPORTANTE: NO forzar tab_servidores aquí
                    st.rerun()

            # =============================================================
            # MOSTRAR DATOS SOLO SI SE APLICARON FILTROS
            # =============================================================
            if not st.session_state.get("filtro_aplicado_tab1", False):
                st.info("🔍 Seleccione un servidor y presione **'Filtrar'** para visualizar los datos.")
            else:
                seleccion_srv = st.session_state["sb_srv_tab1"]
                seleccion_metrica = st.session_state["sb_metrica_tab1"]
                servidor_seleccionado_tab1 = (seleccion_srv != "-- Seleccione un Servidor para empezar --")
                es_vista_global = (seleccion_srv == "-- Todos los Servidores --")
                
                if es_vista_global:
                    renderizar_tabla_historico(seleccion_srv, seleccion_metrica, servidores_activos, dict_ip_a_nombre, mapa_columnas)
                elif not servidor_seleccionado_tab1:
                    st.info("🔍 Por favor, seleccione un servidor del listado para habilitar los filtros de métricas.")
                elif seleccion_metrica == "-- Sin sensores registrados --":
                    st.warning("⚠️ Este servidor no tiene sensores registrados en la base de datos.")
                else:
                    renderizar_tabla_historico(seleccion_srv, seleccion_metrica, servidores_activos, dict_ip_a_nombre, mapa_columnas)

    with tab_graficas:
        # =============================================================
        # FILTROS CON BOTON "FILTRAR" - PESTAÑA 2
        # =============================================================
        col_g_srv_2, col_g_sensor_2, col_filtrar_2, col_limpiar_2 = st.columns([3, 2, 1, 1])
        
        with col_g_srv_2:
            current_srv_index = 0
            if st.session_state["sb_graf_srv_temp"] in opciones_servidores_tab2:
                current_srv_index = opciones_servidores_tab2.index(st.session_state["sb_graf_srv_temp"])
            
            st.selectbox(
                "Servidor Gráficas", 
                options=opciones_servidores_tab2, 
                key="sb_graf_srv_temp",
                label_visibility="collapsed",
                index=current_srv_index
            )
        
        with col_g_sensor_2:
            nombre_srv_temp = st.session_state.get("sb_graf_srv_temp", "-- Seleccione un Servidor --")
            opciones_temp = opciones_componentes_base.copy()
            
            if nombre_srv_temp != "-- Seleccione un Servidor --":
                info_srv_temp = next((s for s in servidores_activos if s['nombre_alias'] == nombre_srv_temp), None)
                if info_srv_temp:
                    discos_map = {'disco_1': 'C', 'disco_2': 'D', 'disco_3': 'E', 
                                 'disco_4': 'F', 'disco_5': 'G', 'disco_6': 'Y'}
                    for disco_key, letra in discos_map.items():
                        if int(info_srv_temp.get(f'id_sensor_{disco_key}', 0) or 0) > 0:
                            opciones_temp.append(f"💽 Almacenamiento (Disco {letra})")
            
            current_sensor_index = 0
            if st.session_state["sb_graf_sensor_temp"] in opciones_temp:
                current_sensor_index = opciones_temp.index(st.session_state["sb_graf_sensor_temp"])
            
            st.selectbox(
                "Componente Gráficas", 
                options=opciones_temp, 
                key="sb_graf_sensor_temp",
                label_visibility="collapsed",
                disabled=(nombre_srv_temp == "-- Seleccione un Servidor --"),
                index=current_sensor_index
            )
        
        with col_filtrar_2:
            if st.button("🔍 Filtrar", key="btn_filtrar_tab2", use_container_width=True):
                st.session_state["sb_graf_srv"] = st.session_state["sb_graf_srv_temp"]
                st.session_state["sb_graf_sensor"] = st.session_state["sb_graf_sensor_temp"]
                st.session_state["filtro_aplicado_tab2"] = True
                # IMPORTANTE: NO forzar tab_servidores aquí
                st.rerun()
        
        with col_limpiar_2:
            if st.button("🧹 Limpiar", key="btn_limpiar_tab2", use_container_width=True):
                st.query_params["_limpiar_tab2_global"] = "1"
                # IMPORTANTE: NO forzar tab_servidores aquí
                st.rerun()

        # =============================================================
        # MOSTRAR DATOS SOLO SI SE APLICARON FILTROS
        # =============================================================
        if not st.session_state.get("filtro_aplicado_tab2", False):
            st.info("🔍 Seleccione un servidor y componente, luego presione **'Filtrar'** para visualizar las gráficas.")
        else:
            opciones_componentes_render = opciones_componentes_base.copy()
            nombre_srv_real = st.session_state.get("sb_graf_srv", "-- Seleccione un Servidor --")
            
            if nombre_srv_real != "-- Seleccione un Servidor --":
                info_srv_real = next((s for s in servidores_activos if s['nombre_alias'] == nombre_srv_real), None)
                if info_srv_real:
                    discos_map = {'disco_1': 'C', 'disco_2': 'D', 'disco_3': 'E', 
                                 'disco_4': 'F', 'disco_5': 'G', 'disco_6': 'Y'}
                    for disco_key, letra in discos_map.items():
                        if int(info_srv_real.get(f'id_sensor_{disco_key}', 0) or 0) > 0:
                            opciones_componentes_render.append(f"💽 Almacenamiento (Disco {letra})")
            
            renderizar_pestaña_analitica_completa(
                opciones_servidores_tab2, 
                opciones_componentes_render, 
                servidores_activos
            )


if __name__ == "__main__":
    mostrar_pantalla()