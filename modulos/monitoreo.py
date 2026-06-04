import streamlit as st
from database import conectar_bd, obtener_datos_historicos

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    """
    Controlador y vista principal del módulo de monitoreo por sensores - Banco Caroní.
    - Sincronizado con los parámetros de sesión del flujo principal.
    - Estilo visual de gráficas clonado fielmente de la interfaz modular de PRTG Network Monitor.
    - Identificación explícita y detallada de sensores en alerta.
    - Autolimpieza automática de filtros al abandonar el módulo.
    """
    
    # 1. CONTROL DE ACCESO OPERATIVO (Matriz de Seguridad)
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Encabezado corporativo adaptado en Azul Institucional
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🖥️ Monitoreo Dedicado por Sensores</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Gestión de Telemetría Operativa | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    # REGRA DE AUTOLIMPIEZA: Registrar que estuvimos aquí para limpiar si cambiamos de módulo
    st.session_state["modulo_actual_monitoreo"] = True

    # Inicialización estándar de estados si están completamente vacíos
    if "filtro_monitoreo_nombre" not in st.session_state:
        st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
    if "filtro_monitoreo_sensor" not in st.session_state:
        st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"

    try:
        conn = conectar_bd()
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL.")
            return
            
        cursor = conn.cursor(dictionary=True)
        
        # CARGA DEL CATÁLOGO DE SERVIDORES DESDE LA BASE DE DATOS
        cursor.execute("SELECT DISTINCT nombre_alias FROM servidores WHERE nombre_alias IS NOT NULL AND nombre_alias != '' ORDER BY nombre_alias ASC")
        lista_nombres_bd = [r['nombre_alias'] for r in cursor.fetchall()]
        opciones_servidores = ["-- Seleccione un Servidor --"] + lista_nombres_bd

        # CAPTURA DE PARÁMETROS URL BLINDADA
        srv_url = st.query_params.get("srv")
        if srv_url:
            srv_url_limpio = str(srv_url).strip().lower()
            for opcion in opciones_servidores:
                if opcion.strip().lower() == srv_url_limpio:
                    st.session_state["filtro_monitoreo_nombre"] = opcion
                    break
        elif "servidor_seleccionado" in st.session_state and st.session_state["servidor_seleccionado"] != "-- Seleccione un Servidor --":
            st.session_state["filtro_monitoreo_nombre"] = st.session_state["servidor_seleccionado"]

        idx_srv_actual = 0
        if st.session_state.filtro_monitoreo_nombre in opciones_servidores:
            idx_srv_actual = opciones_servidores.index(st.session_state.filtro_monitoreo_nombre)

        # PRIMER FILTRO: SELECCIÓN DEL SERVIDOR
        col_f1, col_f2 = st.columns([3, 1])
        seleccion_srv = col_f1.selectbox("1. Filtrar Servidor por Nombre", options=opciones_servidores, index=idx_srv_actual)
        
        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        if col_f2.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_clear_mon_all"):
            st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
            if "servidor_seleccionado" in st.session_state:
                st.session_state["servidor_seleccionado"] = "-- Seleccione un Servidor --"
            st.query_params.clear()
            st.rerun()
            
        if seleccion_srv != st.session_state.filtro_monitoreo_nombre:
            st.session_state.filtro_monitoreo_nombre = seleccion_srv
            st.session_state["servidor_seleccionado"] = seleccion_srv
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
            if seleccion_srv != "-- Seleccione un Servidor --":
                st.query_params["srv"] = seleccion_srv
            else:
                st.query_params.clear()
            st.rerun()

        if st.session_state.filtro_monitoreo_nombre == "-- Seleccione un Servidor --":
            st.info("💡 Por favor, seleccione un servidor para estructurar el catálogo de sensores activos.")
            cursor.close()
            conn.close()
            return

        # Consulta de metadatos del servidor seleccionado
        query = """
            SELECT ip, nombre_alias, sistema_operativo, 
                   id_sensor_cpu, id_sensor_ram, 
                   id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                   id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                   id_sensor_red, id_sensor_latencia 
            FROM servidores
            WHERE nombre_alias = %s
        """
        cursor.execute(query, (st.session_state.filtro_monitoreo_nombre,))
        info_servidor = cursor.fetchone()

        if not info_servidor:
            st.warning("⚠️ No se encontraron parámetros para el nodo seleccionado.")
            cursor.close()
            conn.close()
            return

        ip_objetivo = str(info_servidor['ip']).strip()

        # MAPEO DINÁMICO DE LOS SENSORS CONFIGURADOS POR EL SERVIDOR
        dict_sensores_activos = {}
        if int(info_servidor.get('id_sensor_cpu') or 0) > 0:
            dict_sensores_activos["Métrica: CPU"] = {"tipo": "cpu", "campo": "val_cpu", "unidad": "%", "id": info_servidor['id_sensor_cpu'], "umbral_advertencia": 80.0, "direccion_critica": "alta"}
        if int(info_servidor.get('id_sensor_ram') or 0) > 0:
            dict_sensores_activos["Métrica: RAM Disponible"] = {"tipo": "ram", "campo": "val_ram", "unidad": "GB", "id": info_servidor['id_sensor_ram'], "umbral_advertencia": 1.5, "direccion_critica": "baja"}
        if int(info_servidor.get('id_sensor_red') or 0) > 0:
            dict_sensores_activos["Métrica: Tráfico Red"] = {"tipo": "red", "campo": "val_red", "unidad": "Mb/s", "id": info_servidor['id_sensor_red']}
        if int(info_servidor.get('id_sensor_latencia') or 0) > 0:
            dict_sensores_activos["Métrica: Latencia"] = {"tipo": "latencia", "campo": "val_latencia", "unidad": "ms", "id": info_servidor['id_sensor_latencia'], "umbral_advertencia": 150.0, "direccion_critica": "alta"}
        
        letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:", 6: "H:"}
        for i in range(1, 7):
            id_disco = int(info_servidor.get(f'id_sensor_disco_{i}') or 0)
            if id_disco > 0:
                dict_sensores_activos[f"Disco ({letras_unidades[i]})"] = {"tipo": f"disco_{i}", "campo": f"val_disco_{i}", "unidad": "GB", "id": id_disco, "umbral_advertencia": 10.0, "direccion_critica": "baja"}

        for i in range(1, 6):
            id_servicio = int(info_servidor.get(f'id_sensor_servicio_{i}') or 0)
            if id_servicio > 0:
                dict_sensores_activos[f"Sensor Servicio {i}"] = {"tipo": f"servicio_{i}", "campo": f"estado_servicio_{i}", "unidad": "Estado", "id": id_servicio}

        datos_historicos = obtener_datos_historicos(ip_objetivo)
        registro_reciente = datos_historicos[0] if datos_historicos else None

        # ==========================================================================
        # FILTRO 1: PANEL GENERAL EN TIEMPO REAL + EVALUACIÓN PRECISA DE ALERTAS
        # ==========================================================================
        st.markdown(f"#### 📊 Panel General de Telemetría Real: `{st.session_state.filtro_monitoreo_nombre}` ({ip_objetivo})")
        
        if not registro_reciente:
            st.warning("⚠️ Conexión establecida pero no se hallaron muestras telemetráles recientes.")
        else:
            # AUDITORÍA DETALLADA DE SENSORES EN ALERTA (Eliminación de ambigüedad)
            lista_alertas_detectadas = []
            
            for nombre_s, metadatos_s in dict_sensores_activos.items():
                val_f = registro_reciente.get(metadatos_s["campo"])
                if val_f is None:
                    continue
                
                if metadatos_s["unidad"] == "Estado":
                    if int(val_f) != 1:
                        lista_alertas_detectadas.append(f"🔴 **{nombre_s}** se encuentra desatendido o caído (`🔴 CAÍDO`).")
                elif "umbral_advertencia" in metadatos_s:
                    umb = metadatos_s["umbral_advertencia"]
                    val_calc = float(val_f)
                    if metadatos_s["direccion_critica"] == "alta" and val_calc >= umb:
                        lista_alertas_detectadas.append(f"⚠️ **{nombre_s}** superó el umbral crítico establecido ({val_calc}{metadatos_s['unidad']} >= {umb}{metadatos_s['unidad']}).")
                    elif metadatos_s["direccion_critica"] == "baja" and val_calc <= umb:
                        lista_alertas_detectadas.append(f"⚠️ **{nombre_s}** presenta almacenamiento/recurso escaso ({val_calc}{metadatos_s['unidad']} <= {umb}{metadatos_s['unidad']}).")

            # Despliegue inteligente de diagnósticos
            if lista_alertas_detectadas:
                st.error("🚨 **Incidencias Activas Detectadas en los Siguientes Componentes:**")
                for alerta in lista_alertas_detectadas:
                    st.markdown(f"• {alerta}")
            else:
                st.success("✅ **Operación Normal:** Todos los canales analizados operan dentro de los umbrales de seguridad establecidos.")

            # Cuadrícula masiva de KPIs (4 columnas)
            columnas_kpi_masivas = st.columns(4)
            for idx, (nombre_sensor, metadatos) in enumerate(dict_sensores_activos.items()):
                col_idx = idx % 4
                with columnas_kpi_masivas[col_idx]:
                    val_actual_kpi = registro_reciente.get(metadatos["campo"])
                    
                    if metadatos["unidad"] == "Estado":
                        txt_display = "🟢 ACTIVO" if int(val_actual_kpi or 0) == 1 else "🔴 CAÍDO"
                        st.metric(label=nombre_sensor, value=txt_display, help=f"ID PRTG: {metadatos['id']}")
                    else:
                        delta_v = None
                        if len(datos_historicos) > 1:
                            try:
                                diff = round(float(val_actual_kpi) - float(datos_historicos[1][metadatos["campo"]]), 2)
                                delta_v = f"+{diff} {metadatos['unidad']}" if diff > 0 else f"{diff} {metadatos['unidad']}"
                            except (ValueError, TypeError):
                                pass
                        
                        st.metric(
                            label=nombre_sensor,
                            value=f"{val_actual_kpi} {metadatos['unidad']}",
                            delta=delta_v,
                            delta_color="inverse" if metadatos["tipo"] in ["cpu", "red", "latencia"] else "normal",
                            help=f"ID PRTG: {metadatos['id']}"
                        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        # ==========================================================================
        # FILTRO 2: SELECCIÓN Y DESPLIEGUE DEL SENSOR CONFIGURADO + ESTILO PRTG
        # ==========================================================================
        opciones_sensores = ["-- Seleccione un Sensor --"] + list(dict_sensores_activos.keys())
        idx_sens_actual = 0
        if st.session_state.filtro_monitoreo_sensor in opciones_sensores:
            idx_sens_actual = opciones_sensores.index(st.session_state.filtro_monitoreo_sensor)

        seleccion_sensor = st.selectbox(
            f"2. Seleccione un Sensor Específico para aislar telemetría y ver gráfica histórica",
            options=opciones_sensores,
            index=idx_sens_actual
        )

        if seleccion_sensor != st.session_state.filtro_monitoreo_sensor:
            st.session_state.filtro_monitoreo_sensor = seleccion_sensor
            st.rerun()

        if st.session_state.filtro_monitoreo_sensor == "-- Seleccione un Sensor --":
            st.info(f"💡 Panel masivo cargado con éxito. Seleccione un componente para clonar la curva analítica PRTG.")
            cursor.close()
            conn.close()
            return

        meta_sensor = dict_sensores_activos[st.session_state.filtro_monitoreo_sensor]
        
        valor_individual_actual = registro_reciente.get(meta_sensor["campo"])
        
        color_estado_prtg = "#77ab13"
        icono_estado_prtg = "🟢"
        
        if "umbral_advertencia" in meta_sensor:
            umb = meta_sensor["umbral_advertencia"]
            val_f = float(valor_individual_actual or 0.0)
            if meta_sensor["direccion_critica"] == "alta" and val_f >= umb:
                color_estado_prtg = "#ff9900"
                icono_estado_prtg = "🟡"
            elif meta_sensor["direccion_critica"] == "baja" and val_f <= umb:
                color_estado_prtg = "#ff9900"
                icono_estado_prtg = "🟡"
        elif meta_sensor["unidad"] == "Estado" and int(valor_individual_actual or 0) != 1:
            color_estado_prtg = "#d32f2f"
            icono_estado_prtg = "🔴"

        col_individual_kpi, col_individual_status = st.columns([1, 2])
        with col_individual_kpi:
            if meta_sensor["unidad"] == "Estado":
                st.metric(label=f"Estado del Canal", value="🟢 OK" if int(valor_individual_actual or 0) == 1 else "🔴 ERROR")
            else:
                delta_individual = None
                if len(datos_historicos) > 1:
                    try:
                        diferencia = round(float(valor_individual_actual) - float(datos_historicos[1][meta_sensor["campo"]]), 2)
                        delta_individual = f"+{diferencia} {meta_sensor['unidad']}" if diferencia > 0 else f"{diferencia} {meta_sensor['unidad']}"
                    except (ValueError, TypeError):
                        pass

                st.metric(
                    label=f"Último Escaneo ({meta_sensor['unidad']})",
                    value=f"{valor_individual_actual} {meta_sensor['unidad']}",
                    delta=delta_individual,
                    delta_color="inverse" if meta_sensor["tipo"] in ["cpu", "red", "latencia"] else "normal"
                )

        with col_individual_status:
            st.markdown(
                f'<div style="background-color: #ffffff; border: 1px solid #dee2e6; border-left: 5px solid {color_estado_prtg}; padding: 14px; border-radius: 4px; margin-top:5px; font-family:Arial;">'
                f'<span style="color:#444444; font-weight:bold; font-size:15px;">{icono_estado_prtg} Canal: {st.session_state.filtro_monitoreo_sensor}</span><br>'
                f'<span style="font-size:12px; color:#666;">• <b>Sensor ID:</b> {meta_sensor["id"]} | <b>Sincronización:</b> {registro_reciente.get("fecha_registro")}</span><br>'
                f'<span style="font-size:12px; color:#666;">• <b>Intervalo de Escaneo:</b> 60s (Tiempo Real Activo)</span>'
                f'</div>', 
                unsafe_allow_html=True
            )

        valores_linea = []
        fechas_linea = []
        
        for reg in reversed(datos_historicos):
            try:
                val = float(reg[meta_sensor["campo"]] or 0.0)
                valores_linea.append(val)
                f_reg = reg.get('fecha_registro')
                str_f = f_reg.strftime("%H:%M") if hasattr(f_reg, 'strftime') else str(f_reg)
                fechas_linea.append(str_f)
            except (ValueError, TypeError):
                valores_linea.append(0.0)
                fechas_linea.append("--:--")

        puntos_totales = len(valores_linea)
        
        if puntos_totales > 0:
            ancho_svg = 850
            alto_svg = 280
            padding_left = 60
            padding_right = 40
            padding_top = 40
            padding_bottom = 50
            
            max_val = max(valores_linea)
            min_val = min(valores_linea)
            
            if meta_sensor["unidad"] == "%":
                max_escala = 100.0
                min_escala = 0.0
            else:
                max_escala = max_val * 1.2 if max_val > 0 else 10.0
                min_escala = 0.0

            rango_escala = (max_escala - min_escala) if (max_escala - min_escala) > 0 else 1
            paso_x = (ancho_svg - padding_left - padding_right) / (puntos_totales - 1) if puntos_totales > 1 else (ancho_svg - padding_left - padding_right)
            
            lineas_grid_html = ""
            divisiones_y = 4
            for d in range(divisiones_y + 1):
                val_grid = min_escala + (rango_escala * (d / divisiones_y))
                y_grid = (alto_svg - padding_bottom) - ((val_grid - min_escala) / rango_escala) * (alto_svg - padding_top - padding_bottom)
                lineas_grid_html += f"""
                <line x1="{padding_left}" y1="{y_grid}" x2="{ancho_svg - padding_right}" y2="{y_grid}" stroke="#e9ecef" stroke-width="1" />
                <text x="{padding_left - 12}" y="{y_grid + 4}" fill="#6c757d" font-size="11" text-anchor="end">{int(val_grid) if val_grid.is_integer() else round(val_grid, 1)}</text>
                """

            lista_coordenadas = []
            for i, val in enumerate(valores_linea):
                x = padding_left + (i * paso_x)
                y = (alto_svg - padding_bottom) - ((val - min_escala) / rango_escala) * (alto_svg - padding_top - padding_bottom)
                lista_coordenadas.append(f"{x},{y}")
            puntos_str = " ".join(lista_coordenadas)

            linea_umbral_html = ""
            if "umbral_advertencia" in meta_sensor:
                val_umb = meta_sensor["umbral_advertencia"]
                y_umb = (alto_svg - padding_bottom) - ((val_umb - min_escala) / rango_escala) * (alto_svg - padding_top - padding_bottom)
                if padding_top <= y_umb <= (alto_svg - padding_bottom):
                    linea_umbral_html = f"""
                    <line x1="{padding_left}" y1="{y_umb}" x2="{ancho_svg - padding_right}" y2="{y_umb}" stroke="#e01a53" stroke-width="1.5" stroke-dasharray="4,3" />
                    <text x="{ancho_svg - padding_right - 5}" y="{y_umb - 6}" fill="#e01a53" font-size="10" font-weight="bold" text-anchor="end">Umbral Límite ({val_umb} {meta_sensor['unidad']})</text>
                    """

            idx_mitad = puntos_totales // 2
            txt_eje_x_html = f"""
            <text x="{padding_left}" y="{alto_svg - padding_bottom + 20}" fill="#6c757d" font-size="11" text-anchor="start">{fechas_linea[0]}</text>
            <text x="{padding_left + (idx_mitad * paso_x)}" y="{alto_svg - padding_bottom + 20}" fill="#6c757d" font-size="11" text-anchor="middle">{fechas_linea[idx_mitad]}</text>
            <text x="{ancho_svg - padding_right}" y="{alto_svg - padding_bottom + 20}" fill="#6c757d" font-size="11" text-anchor="end">{fechas_linea[-1]}</text>
            """

            color_canal_grafica = "#3f51b5" if color_estado_prtg == "#77ab13" else "#ff9900"

            prtg_html = f"""
            <style>
                .tarjeta-grafica-prtg {{
                    background-color: #ffffff;
                    border: 1px solid #dcdcdc;
                    border-radius: 3px;
                    padding: 16px;
                    font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }}
                .titulo-canal-prtg {{
                    font-size: 14px;
                    font-weight: bold;
                    color: #333333;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}
                .indicador-circular {{
                    width: 9px;
                    height: 9px;
                    border-radius: 50%;
                    border: 2px solid {color_estado_prtg};
                    background-color: transparent;
                    display: inline-block;
                }}
            </style>

            <div class="tarjeta-grafica-prtg">
                <div class="titulo-canal-prtg">
                    <span class="indicador-circular"></span> 
                    {st.session_state.filtro_monitoreo_sensor}
                </div>
                <svg viewBox="0 0 {ancho_svg} {alto_svg}" width="100%" height="{alto_svg}" xmlns="http://www.w3.org/2000/svg">
                    <rect x="{padding_left}" y="{padding_top}" width="{ancho_svg - padding_left - padding_right}" height="{alto_svg - padding_top - padding_bottom}" fill="none" stroke="#e9ecef" stroke-width="1"/>
                    {lineas_grid_html}
                    {linea_umbral_html}
                    <polyline points="{puntos_str}" fill="none" stroke="{color_canal_grafica}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    {txt_eje_x_html}
                    <text x="{padding_left}" y="{padding_top - 12}" fill="#868e96" font-size="11" font-weight="500">{meta_sensor['unidad']}</text>
                </svg>
            </div>
            """
            st.components.v1.html(prtg_html, height=alto_svg + 60)
        else:
            st.warning("Muestras históricas insuficientes para diagramar la curva analítica.")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de monitoreo: {e}")


# ==========================================================================
# LÓGICA DE LIMPIEZA AUTOMÁTICA (GARANTÍA AL SALIR DEL MÓDULO)
# ==========================================================================
def limpiar_filtros_monitoreo():
    """
    Evalúa si el analista cambió de sección/módulo en la barra lateral para 
    destruir la persistencia de las cajas de selección de forma inmediata.
    """
    if "modulo_actual_monitoreo" in st.session_state:
        # Si la bandera existía pero ya no estamos renderizando activamente esta función
        del st.session_state["modulo_actual_monitoreo"]
    else:
        # El analista abandonó la sección: Reset total
        if "filtro_monitoreo_nombre" in st.session_state:
            st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
        if "filtro_monitoreo_sensor" in st.session_state:
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
        if "servidor_seleccionado" in st.session_state:
            st.session_state["servidor_seleccionado"] = "-- Seleccione un Servidor --"

# Ejecución pasiva de recolección de memoria
limpiar_filtros_monitoreo()