import streamlit as st
from database import conectar_bd, obtener_datos_historicos, obtener_lista_servidores, obtener_umbrales_actuales

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    """
    Controlador y vista principal del módulo de monitoreo por sensores - Banco Caroní.
    - Sincronizado dinámicamente con los umbrales centralizados en la Base de Datos.
    - Estilo visual de gráficas clonado fielmente de la interfaz modular de PRTG Network Monitor.
    - Identificación explícita y detallada de sensores en alerta basado en la única fuente de la verdad.
    - Autolimpieza automática de filtros al abandonar el módulo.
    - Protegido contra valores None (NULL) para soportar dinámicamente hasta 8 servicios y 6 discos.
    """
    
    # 1. CONTROL DE ACCESO OPERATIVO (Matriz de Seguridad)
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Encabezado corporativo en Azul Institucional
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🖥️ Monitoreo Dedicado por Sensores</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Gestión de Telemetría Operativa | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    # REGLA DE AUTOLIMPIEZA: Registrar que estuvimos aquí en este ciclo de ejecución
    st.session_state["modulo_actual_monitoreo"] = True

    # Inicialización estándar de estados si están completamente vacíos
    if "filtro_monitoreo_nombre" not in st.session_state:
        st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
    if "filtro_monitoreo_sensor" not in st.session_state:
        st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"

    try:
        # CARGA DEL CATÁLOGO DE SERVIDORES DESDE FUNCIÓN CACHADA DE DATABASE.PY
        servidores_activos = obtener_lista_servidores()
        if not servidores_activos:
            st.info("💡 No hay servidores activos mapeados en el catálogo central.")
            return
            
        lista_nombres_bd = sorted(list(set([r['nombre_alias'] for r in servidores_activos if r['nombre_alias']])))
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
            return

        # Extraer metadatos localmente del servidor seleccionado desde la lista cargada
        info_servidor = next((srv for srv in servidores_activos if srv['nombre_alias'] == st.session_state.filtro_monitoreo_nombre), None)

        if not info_servidor:
            st.warning("⚠️ No se encontraron parámetros de red para el nodo seleccionado.")
            return

        ip_objetivo = str(info_servidor['ip']).strip()
        
        # CONSULTA MATRIZ DE UMBRALES EN VIVO DESDE LA BASE DE DATOS
        matriz_umbrales = obtener_umbrales_actuales(ip_objetivo)

        # MAPEO DINÁMICO DE LOS SENSORES CONFIGURADOS UTILIZANDO LA TABLA HISTÓRICO DE UMBRALES
        dict_sensores_activos = {}
        
        if int(info_servidor.get('id_sensor_cpu') or 0) > 0:
            dict_sensores_activos["Métrica: CPU"] = {
                "tipo": "cpu", "campo": "val_cpu", "unidad": "%", 
                "id": info_servidor['id_sensor_cpu'], 
                "umbral_advertencia": float(matriz_umbrales.get("cpu_advertencia", 70)), 
                "direccion_critica": "alta"
            }
        if int(info_servidor.get('id_sensor_ram') or 0) > 0:
            dict_sensores_activos["Métrica: RAM Disponible"] = {
                "tipo": "ram", "campo": "val_ram", "unidad": "GB", 
                "id": info_servidor['id_sensor_ram'], 
                "umbral_advertencia": float(matriz_umbrales.get("ram_advertencia", 8)), 
                "direccion_critica": "baja"
            }
        if int(info_servidor.get('id_sensor_red') or 0) > 0:
            dict_sensores_activos["Métrica: Tráfico Red"] = {
                "tipo": "red", "campo": "val_red", "unidad": "Mb/s", 
                "id": info_servidor['id_sensor_red']
            }
        if int(info_servidor.get('id_sensor_latencia') or 0) > 0:
            dict_sensores_activos["Métrica: Latencia"] = {
                "tipo": "latencia", "campo": "val_latencia", "unidad": "ms", 
                "id": info_servidor['id_sensor_latencia'], 
                "umbral_advertencia": 150.0, # Latencia estándar de red interna bancaria
                "direccion_critica": "alta"
            }
        
        # Sincronización analítica para los 6 discos desde la matriz centralizada
        letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:", 6: "Y:"}
        for i in range(1, 7):
            id_disco = int(info_servidor.get(f'id_sensor_disco_{i}') or 0)
            if id_disco > 0:
                dict_sensores_activos[f"Disco ({letras_unidades[i]})"] = {
                    "tipo": f"disco_{i}", "campo": f"val_disco_{i}", "unidad": "GB", 
                    "id": id_disco, 
                    "umbral_advertencia": float(matriz_umbrales.get(f"disco_{i}_advertencia", 40)), 
                    "direccion_critica": "baja"
                }

        # Sensores de servicios activos (1 al 8)
        for i in range(1, 9):
            id_servicio = int(info_servidor.get(f'id_sensor_servicio_{i}') or 0)
            if id_servicio > 0:
                dict_sensores_activos[f"Sensor Servicio {i}"] = {
                    "tipo": f"servicio_{i}", "campo": f"estado_servicio_{i}", 
                    "unidad": "Estado", "id": id_servicio
                }

        datos_historicos = obtener_datos_historicos(ip_objetivo)
        registro_reciente = datos_historicos[0] if datos_historicos else None

        # ==========================================================================
        # PANEL GENERAL EN TIEMPO REAL + EVALUACIÓN PRECISA DE ALERTAS
        # ==========================================================================
        tipo_srv = info_servidor.get('tipo', 'No definido')
        st.markdown(f"#### 📊 Panel General de Telemetría Real: `{st.session_state.filtro_monitoreo_nombre}` ({ip_objetivo}) — *Tipo: {tipo_srv}*")
        
        if not registro_reciente:
            st.warning("⚠️ Conexión establecida pero no se hallaron muestras telemetráles recientes.")
        else:
            # AUDITORÍA DE SENSORES BASADA EN LOS UMBRALES DE LA BASE DE DATOS
            lista_alertas_detectadas = []
            
            for nombre_s, metadatos_s in dict_sensores_activos.items():
                val_f = registro_reciente.get(metadatos_s["campo"])
                if val_f is None: # Si el sensor está mapeado pero la telemetría vino NULL, se ignora con seguridad
                    continue
                
                if metadatos_s["unidad"] == "Estado":
                    # Adaptación al estándar de mapeo PRTG ('3'=OK, '4'=CRIT, '5'=WARN)
                    val_str = str(val_f).strip()
                    if val_str not in ['1', '3', 'OK']: 
                        lista_alertas_detectadas.append(f"🔴 **{nombre_s}** se encuentra desatendido o caído (`🔴 CRIT/ALERT`).")
                elif "umbral_advertencia" in metadatos_s:
                    umb = metadatos_s["umbral_advertencia"]
                    val_calc = float(val_f)
                    if metadatos_s["direccion_critica"] == "alta" and val_calc >= umb:
                        lista_alertas_detectadas.append(f"⚠️ **{nombre_s}** superó el umbral dinámico de alerta ({val_calc}{metadatos_s['unidad']} >= {umb}{metadatos_s['unidad']}).")
                    elif metadatos_s["direccion_critica"] == "baja" and val_calc <= umb:
                        lista_alertas_detectadas.append(f"⚠️ **{nombre_s}** presenta almacenamiento/recurso escaso bajo umbral ({val_calc}{metadatos_s['unidad']} <= {umb}{metadatos_s['unidad']}).")

            if lista_alertas_detectadas:
                st.error("🚨 **Incidencias Activas Detectadas en los Siguientes Componentes:**")
                for alerta in lista_alertas_detectadas:
                    st.markdown(f"• {alerta}")
            else:
                st.success("✅ **Operación Normal:** Todos los canales analizados operan dentro de los umbrales de seguridad establecidos en la base de datos.")

            # Cuadrícula masiva de KPIs (4 columnas)
            columnas_kpi_masivas = st.columns(4)
            for idx, (nombre_sensor, metadatos) in enumerate(dict_sensores_activos.items()):
                col_idx = idx % 4
                with columnas_kpi_masivas[col_idx]:
                    val_actual_kpi = registro_reciente.get(metadatos["campo"])
                    
                    if metadatos["unidad"] == "Estado":
                        if val_actual_kpi is None:
                            txt_display = "⚪ N/D"
                        else:
                            val_str = str(val_actual_kpi).strip()
                            txt_display = "🟢 ACTIVO" if val_str in ['1', '3', 'OK'] else "🔴 CRÍTICO"
                        st.metric(label=nombre_sensor, value=txt_display, help=f"ID PRTG: {metadatos['id']}")
                    else:
                        delta_v = None
                        if len(datos_historicos) > 1 and val_actual_kpi is not None:
                            try:
                                val_antiguo = datos_historicos[1].get(metadatos["campo"])
                                if val_antiguo is not None:
                                    diff = round(float(val_actual_kpi) - float(val_antiguo), 2)
                                    delta_v = f"+{diff} {metadatos['unidad']}" if diff > 0 else f"{diff} {metadatos['unidad']}"
                            except (ValueError, TypeError):
                                pass
                        
                        st.metric(
                            label=nombre_sensor,
                            value=f"{val_actual_kpi} {metadatos['unidad']}" if val_actual_kpi is not None else "N/D",
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
            return

        meta_sensor = dict_sensores_activos[st.session_state.filtro_monitoreo_sensor]
        valor_individual_actual = registro_reciente.get(meta_sensor["campo"]) if registro_reciente else None
        
        color_estado_prtg = "#77ab13"
        icono_estado_prtg = "🟢"
        
        if valor_individual_actual is not None:
            if "umbral_advertencia" in meta_sensor:
                umb = meta_sensor["umbral_advertencia"]
                val_f = float(valor_individual_actual or 0.0)
                if meta_sensor["direccion_critica"] == "alta" and val_f >= umb:
                    color_estado_prtg = "#ff9900"
                    icono_estado_prtg = "🟡"
                elif meta_sensor["direccion_critica"] == "baja" and val_f <= umb:
                    color_estado_prtg = "#ff9900"
                    icono_estado_prtg = "🟡"
            elif meta_sensor["unidad"] == "Estado":
                val_str = str(valor_individual_actual).strip()
                if val_str not in ['1', '3', 'OK']:
                    color_estado_prtg = "#d32f2f"
                    icono_estado_prtg = "🔴"
        else:
            color_estado_prtg = "#6c757d"
            icono_estado_prtg = "⚪"

        col_individual_kpi, col_individual_status = st.columns([1, 2])
        with col_individual_kpi:
            if meta_sensor["unidad"] == "Estado":
                if valor_individual_actual is None:
                    st.metric(label=f"Estado del Canal", value="⚪ N/D")
                else:
                    val_str = str(valor_individual_actual).strip()
                    st.metric(label=f"Estado del Canal", value="🟢 OK" if val_str in ['1', '3', 'OK'] else "🔴 ERROR")
            else:
                delta_individual = None
                if len(datos_historicos) > 1 and valor_individual_actual is not None:
                    try:
                        val_antiguo = datos_historicos[1].get(meta_sensor["campo"])
                        if val_antiguo is not None:
                            diferencia = round(float(valor_individual_actual) - float(val_antiguo), 2)
                            delta_individual = f"+{diferencia} {meta_sensor['unidad']}" if diferencia > 0 else f"{diferencia} {meta_sensor['unidad']}"
                    except (ValueError, TypeError):
                        pass

                st.metric(
                    label=f"Último Escaneo ({meta_sensor['unidad']})",
                    value=f"{valor_individual_actual} {meta_sensor['unidad']}" if valor_individual_actual is not None else "N/D",
                    delta=delta_individual,
                    delta_color="inverse" if meta_sensor["tipo"] in ["cpu", "red", "latencia"] else "normal"
                )

        with col_individual_status:
            fecha_sync = registro_reciente.get("fecha_registro") if registro_reciente else "N/D"
            # SOLUCIÓN DEL ERROR CRÍTICO: Extraemos de forma segura el texto para evitar la inyección rota en el f-string
            txt_umbral_prtg = "N/A" if "umbral_advertencia" not in meta_sensor else f"{meta_sensor['umbral_advertencia']} {meta_sensor['unidad']}"
            
            st.markdown(
                f'<div style="background-color: #ffffff; border: 1px solid #dee2e6; border-left: 5px solid {color_estado_prtg}; padding: 14px; border-radius: 4px; margin-top:5px; font-family:Arial;">'
                f'<span style="color:#444444; font-weight:bold; font-size:15px;">{icono_estado_prtg} Canal: {st.session_state.filtro_monitoreo_sensor}</span><br>'
                f'<span style="font-size:12px; color:#666;">• <b>Sensor ID:</b> {meta_sensor["id"]} | <b>Sincronización:</b> {fecha_sync}</span><br>'
                f'<span style="font-size:12px; color:#666;">• <b>Límite Alerta (BD):</b> {txt_umbral_prtg}</span>'
                f'</div>', 
                unsafe_allow_html=True
            )

        valores_linea = []
        fechas_linea = []
        
        # Filtrado preventivo de Nones para no romper la curva analítica del SVG
        for reg in reversed(datos_historicos):
            raw_val = reg.get(meta_sensor["campo"])
            if raw_val is None:
                continue # Evita caídas a 0 artificiales por culpa de baches telemetráles
            try:
                if meta_sensor["unidad"] == "Estado":
                    # Si es un estado mapeado de PRTG ('3'=OK, '4'=CRIT), lo guardamos numérico para escalarlo
                    val_str = str(raw_val).strip()
                    val = 100.0 if val_str in ['1', '3', 'OK'] else 10.0
                else:
                    val = float(raw_val)
                valores_linea.append(val)
                f_reg = reg.get('fecha_registro')
                str_f = f_reg.strftime("%H:%M") if hasattr(f_reg, 'strftime') else str(f_reg)
                fechas_linea.append(str_f)
            except (ValueError, TypeError):
                pass

        puntos_totales = len(valores_linea)
        
        if puntos_totales > 1: # Se requieren al menos dos puntos válidos para tirar una línea SVG
            ancho_svg = 850
            alto_svg = 280
            padding_left = 60
            padding_right = 40
            padding_top = 40
            padding_bottom = 50
            
            max_val = max(valores_linea) if valores_linea else 0
            
            if meta_sensor["unidad"] == "%":
                max_escala = 100.0
                min_escala = 0.0
            elif meta_sensor["unidad"] == "Estado":
                max_escala = 120.0
                min_escala = 0.0
            else:
                max_escala = max_val * 1.2 if max_val > 0 else 10.0
                min_escala = 0.0

            rango_escala = (max_escala - min_escala) if (max_escala - min_escala) > 0 else 1
            paso_x = (ancho_svg - padding_left - padding_right) / (puntos_totales - 1)
            
            lineas_grid_html = ""
            divisiones_y = 4
            for d in range(divisiones_y + 1):
                val_grid = min_escala + (rango_escala * (d / divisiones_y))
                y_grid = (alto_svg - padding_bottom) - ((val_grid - min_escala) / rango_escala) * (alto_svg - padding_top - padding_bottom)
                
                # Formatear la etiqueta de la escala según el tipo de canal
                if meta_sensor["unidad"] == "Estado":
                    lbl_grid = "OK" if val_grid >= 100.0 else ("CRIT" if val_grid >= 10.0 and val_grid < 30.0 else "")
                else:
                    lbl_grid = int(val_grid) if val_grid.is_integer() else round(val_grid, 1)
                    
                if lbl_grid != "":
                    lineas_grid_html += f"""
                    <line x1="{padding_left}" y1="{y_grid}" x2="{ancho_svg - padding_right}" y2="{y_grid}" stroke="#e9ecef" stroke-width="1" />
                    <text x="{padding_left - 12}" y="{y_grid + 4}" fill="#6c757d" font-size="11" text-anchor="end">{lbl_grid}</text>
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
                    <text x="{ancho_svg - padding_right - 5}" y="{y_umb - 6}" fill="#e01a53" font-size="10" font-weight="bold" text-anchor="end">Límite Sincronizado ({val_umb} {meta_sensor['unidad']})</text>
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
            st.warning("⚠️ Muestras históricas insuficientes o nulas en la ventana de tiempo para diagramar la curva analítica.")

    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de monitoreo: {e}")

# ==========================================================================
# LÓGICA DE LIMPIEZA AUTOMÁTICA (GARANTÍA AL SALIR DEL MÓDULO)
# ==========================================================================
def limpiar_filtros_monitoreo():
    if "modulo_actual_monitoreo" in st.session_state:
        del st.session_state["modulo_actual_monitoreo"]
    else:
        if "filtro_monitoreo_nombre" in st.session_state:
            st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
        if "filtro_monitoreo_sensor" in st.session_state:
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
        if "servidor_seleccionado" in st.session_state:
            st.session_state["servidor_seleccionado"] = "-- Seleccione un Servidor --"