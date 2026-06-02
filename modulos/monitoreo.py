import streamlit as st
from database import conectar_bd, obtener_datos_historicos

def mostrar_pantalla():
    """
    Controlador y vista principal del módulo de monitoreo por sensores.
    Usa una lógica de doble filtro limpio por indexación dinámica (sin llaves bloqueantes).
    Muestra el catálogo completo de sensores al elegir un servidor y filtra en detalle en el segundo nivel.
    Genera una gráfica de comportamiento interactiva con leyenda explicativa en SVG/HTML (100% nativo).
    Soporta redirección entrante en caliente compatible con parámetros de URL Case-Insensitive.
    """
    
    # 1. CONTROL DE ACCESO OPERATIVO (Matriz de Seguridad)
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Encabezado corporativo en Azul Institucional
    st.markdown('<h2 style="color:#003366;">🖥️ Monitoreo Dedicado por Sensores</h2>', unsafe_allow_html=True)
    st.markdown("---")

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
        
        # ==========================================================================
        # CARGA DEL CATÁLOGO DE SERVIDORES DESDE LA BASE DE DATOS
        # ==========================================================================
        cursor.execute("SELECT DISTINCT nombre_alias FROM servidores WHERE nombre_alias IS NOT NULL AND nombre_alias != '' ORDER BY nombre_alias ASC")
        lista_nombres_bd = [r['nombre_alias'] for r in cursor.fetchall()]
        opciones_servidores = ["-- Seleccione un Servidor --"] + lista_nombres_bd

        # ==========================================================================
        # CAPTURA DE PARÁMETROS URL BLINDADA (Normalización Case-Insensitive)
        # ==========================================================================
        srv_url = st.query_params.get("srv")
        
        if srv_url:
            srv_url_limpio = str(srv_url).strip().lower()
            for opcion in opciones_servidores:
                if opcion.strip().lower() == srv_url_limpio:
                    st.session_state["filtro_monitoreo_nombre"] = opcion
                    break
        elif "servidor_seleccionado" in st.session_state and st.session_state["servidor_seleccionado"] != "-- Seleccione un Servidor --":
            st.session_state["filtro_monitoreo_nombre"] = st.session_state["servidor_seleccionado"]

        # Determinar el índice actual para el primer selectbox de forma segura
        idx_srv_actual = 0
        if st.session_state.filtro_monitoreo_nombre in opciones_servidores:
            idx_srv_actual = opciones_servidores.index(st.session_state.filtro_monitoreo_nombre)

        # ==========================================================================
        # PRIMER FILTRO: SELECCIÓN DEL SERVIDOR (Solución: Sin Key fija que bloquee)
        # ==========================================================================
        col_f1, col_f2 = st.columns([3, 1])
        
        seleccion_srv = col_f1.selectbox(
            "1. Filtrar Servidor por Nombre",
            options=opciones_servidores,
            index=idx_srv_actual
        )
        
        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        
        # OPERACIÓN DEL BOTÓN LIMPIAR: Resetea limpiamente todas las variables de sesión asociadas
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
                parametros_actuales = dict(st.query_params)
                parametros_actuales["srv"] = seleccion_srv
                st.query_params.update(parametros_actuales)
            else:
                st.query_params.clear()
            st.rerun()

        # Si el lienzo está vacío (No hay servidor seleccionado)
        if st.session_state.filtro_monitoreo_nombre == "-- Seleccione un Servidor --":
            st.info("💡 Por favor, seleccione un servidor para estructurar el catálogo de sensores activos.")
            cursor.close()
            conn.close()
            return

        # Consulta de metadatos del servidor seleccionado (6 discos y 5 servicios)
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

        # ==========================================================================
        # MAPEO DINÁMICO DE LOS SENSORS CONFIGURADOS POR EL SERVIDOR SELECCIONADO
        # ==========================================================================
        dict_sensores_activos = {}
        
        if int(info_servidor.get('id_sensor_cpu') or 0) > 0:
            dict_sensores_activos["Métrica: CPU"] = {"tipo": "cpu", "campo": "val_cpu", "unidad": "%", "id": info_servidor['id_sensor_cpu']}
            
        if int(info_servidor.get('id_sensor_ram') or 0) > 0:
            dict_sensores_activos["Métrica: RAM Disponible"] = {"tipo": "ram", "campo": "val_ram", "unidad": "GB", "id": info_servidor['id_sensor_ram']}
            
        if int(info_servidor.get('id_sensor_red') or 0) > 0:
            dict_sensores_activos["Métrica: Tráfico Red"] = {"tipo": "red", "campo": "val_red", "unidad": "Mb/s", "id": info_servidor['id_sensor_red']}
            
        if int(info_servidor.get('id_sensor_latencia') or 0) > 0:
            dict_sensores_activos["Métrica: Latencia"] = {"tipo": "latencia", "campo": "val_latencia", "unidad": "ms", "id": info_servidor['id_sensor_latencia']}
        
        # Mapeo de almacenamiento extendido a 6 discos
        letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:", 6: "H:"}
        for i in range(1, 7):
            id_disco = int(info_servidor.get(f'id_sensor_disco_{i}') or 0)
            if id_disco > 0:
                dict_sensores_activos[f"Disco ({letras_unidades[i]})"] = {"tipo": f"disco_{i}", "campo": f"val_disco_{i}", "unidad": "GB", "id": id_disco}

        # Mapeo dinámico para los 5 sensores de Servicio
        for i in range(1, 6):
            id_servicio = int(info_servidor.get(f'id_sensor_servicio_{i}') or 0)
            if id_servicio > 0:
                dict_sensores_activos[f"Sensor Servicio {i}"] = {"tipo": f"servicio_{i}", "campo": f"estado_servicio_{i}", "unidad": "Estado", "id": id_servicio}

        if not dict_sensores_activos:
            st.warning("ℹ️ Este nodo no posee sensores activos configurados en el catálogo central.")
            cursor.close()
            conn.close()
            return

        # ==========================================================================
        # REQUERIMIENTO DEL BANCO: Mostrar todos los sensores registrados del servidor
        # ==========================================================================
        st.markdown(f"#### 📊 Sensores Registrados para el Servidor: `{st.session_state.filtro_monitoreo_nombre}` ({ip_objetivo})")
        
        # Se genera una cuadrícula compacta de credenciales técnicas mapeadas en base de datos
        columnas_sensores = st.columns(min(len(dict_sensores_activos), 4))
        for idx, (nombre_sensor, metadatos) in enumerate(dict_sensores_activos.items()):
            col_idx = idx % len(columnas_sensores)
            with columnas_sensores[col_idx]:
                st.info(f"**{nombre_sensor}**\n\nID PRTG: `{metadatos['id']}`\n\nUnidad: `{metadatos['unidad']}`")

        st.markdown("<br>", unsafe_allow_html=True)

        # ==========================================================================
        # SEGUNDO FILTRO: SELECCIÓN DEL SENSOR INDIVIDUAL (Solución: Sin Key fija que bloquee)
        # ==========================================================================
        opciones_sensores = ["-- Seleccione un Sensor --"] + list(dict_sensores_activos.keys())
        
        idx_sens_actual = 0
        if st.session_state.filtro_monitoreo_sensor in opciones_sensores:
            idx_sens_actual = opciones_sensores.index(st.session_state.filtro_monitoreo_sensor)

        seleccion_sensor = st.selectbox(
            f"2. Seleccione un Sensor Específico para graficar telemetría",
            options=opciones_sensores,
            index=idx_sens_actual
        )

        if seleccion_sensor != st.session_state.filtro_monitoreo_sensor:
            st.session_state.filtro_monitoreo_sensor = seleccion_sensor
            st.rerun()

        # Detener flujo si se muestra la lista pero aún no se elige un sensor específico
        if st.session_state.filtro_monitoreo_sensor == "-- Seleccione un Sensor --":
            st.info(f"💡 Por favor, elija uno de los sensores mapeados arriba en la lista desplegable (Paso 2) para procesar su telemetría e histórico de comportamiento.")
            cursor.close()
            conn.close()
            return

        # =====================================================================
        # DESPLIEGUE DE DATOS HISTÓRICOS Y GRÁFICA DEL SENSOR SELECCIONADO
        # =====================================================================
        meta_sensor = dict_sensores_activos[st.session_state.filtro_monitoreo_sensor]
        datos_historicos = obtener_datos_historicos(ip_objetivo)
        
        if not datos_historicos:
            st.error(f"❌ No se registran datos en la base de datos para el sensor ID {meta_sensor['id']}.")
            cursor.close()
            conn.close()
            return

        # Registro en índice 0 (más reciente)
        registro_reciente = datos_historicos[0]
        valor_actual = registro_reciente[meta_sensor["campo"]]
        
        delta_visual = None
        if len(datos_historicos) > 1 and meta_sensor["unidad"] != "Estado":
            try:
                diferencia = round(float(valor_actual) - float(datos_historicos[1][meta_sensor["campo"]]), 2)
                delta_visual = f"+{diferencia} {meta_sensor['unidad']}" if diferencia > 0 else f"{diferencia} {meta_sensor['unidad']}"
            except (ValueError, TypeError):
                pass

        st.markdown("---")
        col_kpi, col_status = st.columns([1, 2])
        
        with col_kpi:
            if meta_sensor["unidad"] == "Estado":
                txt_estado_svc = "ACTIVO" if int(valor_actual or 0) == 1 else "CAÍDO"
                st.metric(
                    label=f"Valor Actual: {st.session_state.filtro_monitoreo_sensor}",
                    value=txt_estado_svc,
                    delta=None
                )
            else:
                st.metric(
                    label=f"Valor Actual: {st.session_state.filtro_monitoreo_sensor}",
                    value=f"{valor_actual} {meta_sensor['unidad']}",
                    delta=delta_visual,
                    delta_color="inverse" if meta_sensor["tipo"] in ["cpu", "red", "latencia"] else "normal"
                )

        with col_status:
            estado_nodo = str(registro_reciente.get('estado_sistema', 'ÓPTIMO')).upper().strip()
            if "CRÍTICO" in estado_nodo or "CRITICO" in estado_nodo:
                st.error(f"🔴 **Estado General del Servidor: CRÍTICO**\n\nLímites operativos sobrepasados.")
            elif estado_nodo in ["PRECAUCIÓN", "PRECAUCION", "ADVERTENCIA", "AMARILLO"]:
                st.warning(f"🟡 **Estado General del Servidor: ADVERTENCIA**\n\nRangos preventivos alcanzados.")
            else:
                st.success(f"🟢 **Estado General del Servidor: ÓPTIMO**\n\nOperación dentro de rangos normales.")

        # CONSTRUCCIÓN DE LA GRÁFICA SVG
        st.write("### 📈 Gráfica de Comportamiento Histórico")
        
        valores_linea = []
        fechas_linea = []
        suma_valores = 0.0
        
        for reg in reversed(datos_historicos):
            try:
                val = float(reg[meta_sensor["campo"]] or 0.0)
                valores_linea.append(val)
                suma_valores += val
                
                f_reg = reg.get('fecha_registro')
                str_f = f_reg.strftime("%H:%M:%S") if hasattr(f_reg, 'strftime') else str(f_reg)
                fechas_linea.append(str_f)
            except (ValueError, TypeError):
                valores_linea.append(0.0)
                fechas_linea.append("N/A")

        puntos_totales = len(valores_linea)
        
        if puntos_totales > 0:
            ancho_svg = 900
            alto_svg = 260
            padding_x = 50
            padding_y = 40
            
            max_val = max(valores_linea)
            min_val = min(valores_linea)
            rango = (max_val - min_val) if (max_val - min_val) > 0 else 1
            
            promedio = round(suma_valores / puntos_totales, 2)
            y_promedio = (alto_svg - padding_y) - ((promedio - min_val) / rango) * (alto_svg - (2 * padding_y))
            paso_x = (ancho_svg - (2 * padding_x)) / (puntos_totales - 1) if puntos_totales > 1 else (ancho_svg - (2 * padding_x))
            
            lista_coordenadas = []
            circulos_svg_lista = []
            
            for i, val in enumerate(valores_linea):
                x = padding_x + (i * paso_x)
                y = (alto_svg - padding_y) - ((val - min_val) / rango) * (alto_svg - (2 * padding_y))
                lista_coordenadas.append(f"{x},{y}")
                
                txt_lbl_tooltip = f"{val} {meta_sensor['unidad']}" if meta_sensor["unidad"] != "Estado" else ("ACTIVO" if int(val) == 1 else "CAÍDO")
                
                circulos_svg_lista.append(f"""
                <circle cx="{x}" cy="{y}" r="4.5" class="punto-grafica">
                    <title>Muestra N°: {i+1}\nHora: {fechas_linea[i]}\nValor: {txt_lbl_tooltip}</title>
                </circle>
                """)
            
            puntos_str = " ".join(lista_coordenadas)
            circulos_html_final = "".join(circulos_svg_lista)
            
            lbl_max_grafica = f"{max_val} {meta_sensor['unidad']}" if meta_sensor["unidad"] != "Estado" else ("ACTIVO" if int(max_val) == 1 else "CAÍDO")
            lbl_min_grafica = f"{min_val} {meta_sensor['unidad']}" if meta_sensor["unidad"] != "Estado" else ("ACTIVO" if int(min_val) == 1 else "CAÍDO")
            lbl_prom_grafica = f"Promedio: {promedio} {meta_sensor['unidad']}" if meta_sensor["unidad"] != "Estado" else ""
            
            svg_html = f"""
            <style>
                .contenedor-grafica {{
                    background-color: #ffffff; 
                    padding: 20px; 
                    border-radius: 8px; 
                    border: 1px solid #dee2e6;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
                }}
                .punto-grafica {{
                    fill: #ff9900;
                    stroke: #ffffff;
                    stroke-width: 1.5;
                    cursor: pointer;
                    transition: all 0.15s ease-in-out;
                }}
                .punto-grafica:hover {{
                    fill: #d32f2f;
                    r: 7;
                }}
                .seccion-leyenda {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px dashed #e9ecef;
                    justify-content: center;
                }}
                .item-leyenda {{
                    display: flex;
                    align-items: center;
                    font-size: 12px;
                    color: #495057;
                }}
                .indicador-linea {{
                    width: 24px;
                    height: 3px;
                    background-color: #003366;
                    margin-right: 8px;
                    border-radius: 2px;
                }}
                .indicador-promedio {{
                    width: 24px;
                    height: 0px;
                    border-top: 2px dashed #003366;
                    opacity: 0.6;
                    margin-right: 8px;
                }}
                .indicador-punto {{
                    width: 10px;
                    height: 10px;
                    background-color: #ff9900;
                    border: 1.5px solid #ffffff;
                    border-radius: 50%;
                    margin-right: 8px;
                    box-shadow: 0 0 0 1px #ff9900;
                }}
            </style>

            <div class="contenedor-grafica">
                <svg viewBox="0 0 {ancho_svg} {alto_svg}" width="100%" height="{alto_svg}" xmlns="http://www.w3.org/2000/svg">
                    <line x1="{padding_x}" y1="{alto_svg - padding_y}" x2="{ancho_svg - padding_x}" y2="{alto_svg - padding_y}" stroke="#f1f3f5" stroke-width="2" />
                    <line x1="{padding_x}" y1="{padding_y}" x2="{ancho_svg - padding_x}" y2="{padding_y}" stroke="#f1f3f5" stroke-width="1.5" />
                    
                    {" " if meta_sensor["unidad"] == "Estado" else f'<line x1="{padding_x}" y1="{y_promedio}" x2="{ancho_svg - padding_x}" y2="{y_promedio}" stroke="#003366" stroke-width="1.5" stroke-dasharray="5,5" opacity="0.6"/>'}
                    {" " if meta_sensor["unidad"] == "Estado" else f'<text x="{ancho_svg - padding_x - 140}" y="{y_promedio - 6}" fill="#003366" font-size="11" font-family="Arial" font-weight="bold" opacity="0.75">{lbl_prom_grafica}</text>'}
                    
                    <polyline points="{puntos_str}" fill="none" stroke="#003366" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                    
                    {circulos_html_final}
                    
                    <text x="{padding_x}" y="{padding_y - 12}" fill="#2E7D32" font-size="11" font-family="Arial" font-weight="bold">▲ MÁX: {lbl_max_grafica}</text>
                    <text x="{padding_x}" y="{alto_svg - padding_y + 20}" fill="#C62828" font-size="11" font-family="Arial" font-weight="bold">▼ MÍN: {lbl_min_grafica}</text>
                    
                    <text x="{padding_x}" y="{alto_svg - padding_y + 35}" fill="#868e96" font-size="10" font-family="Arial">Primera Muestra ({fechas_linea[0]})</text>
                    <text x="{ancho_svg - padding_x - 130}" y="{alto_svg - padding_y + 35}" fill="#868e96" font-size="10" font-family="Arial">Última Muestra ({fechas_linea[-1]})</text>
                </svg>

                <div class="seccion-leyenda">
                    <div class="item-leyenda">
                        <div class="indicador-linea"></div>
                        <span><b>Curva Temporal:</b> Variación secuencial de las lecturas recibidas.</span>
                    </div>
                    {"" if meta_sensor["unidad"] == "Estado" else f"""<div class="item-leyenda">
                        <div class="indicador-promedio"></div>
                        <span><b>Línea de Media:</b> Valor promedio del sensor durante esta ventana ({promedio} {meta_sensor['unidad']}).</span>
                    </div>"""}
                    <div class="item-leyenda">
                        <div class="indicador-punto"></div>
                        <span><b>Punto de Captura (Muestra):</b> Registro instantáneo. <i>Pasa el cursor encima para inspeccionar hora y valor exacto.</i></span>
                    </div>
                </div>
            </div>
            """
            st.components.v1.html(svg_html, height=alto_svg + 95)
        else:
            st.warning("Muestras insuficientes para diagramar la curva.")
            
        st.caption(f"📅 Ventana de visualización: {len(valores_linea)} muestras analizadas consecutivas.")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de monitoreo: {e}")

if __name__ == "__main__":
    st.set_page_config(page_title="SIMPOL - Monitoreo", layout="wide")
    mostrar_pantalla()