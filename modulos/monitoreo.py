import streamlit as st
from database import conectar_bd, obtener_datos_historicos

def mostrar_pantalla():
    """
    Controlador y vista principal del módulo de monitoreo por sensores.
    Usa una lógica de doble filtro limpio por selectbox y genera una gráfica 
    de comportamiento histórica usando SVG nativo en HTML (100% sin pandas ni numpy).
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

    # Inicialización de estados de sesión para sostener los filtros limpios desde el inicio
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
        # PRIMER FILTRO: SELECCIÓN DEL SERVIDOR (Lógica de servidores.py)
        # ==========================================================================
        cursor.execute("SELECT DISTINCT nombre_alias FROM servidores WHERE nombre_alias IS NOT NULL AND nombre_alias != '' ORDER BY nombre_alias ASC")
        lista_nombres_bd = [r['nombre_alias'] for r in cursor.fetchall()]
        opciones_servidores = ["-- Seleccione un Servidor --"] + lista_nombres_bd

        idx_srv_actual = 0
        if st.session_state.filtro_monitoreo_nombre in opciones_servidores:
            idx_srv_actual = opciones_servidores.index(st.session_state.filtro_monitoreo_nombre)

        col_f1, col_f2 = st.columns([3, 1])
        
        seleccion_srv = col_f1.selectbox(
            "1. Filtrar Servidor por Nombre",
            options=opciones_servidores,
            index=idx_srv_actual,
            key="sb_mon_servidor"
        )
        
        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        
        if col_f2.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_clear_mon_all"):
            st.session_state.filtro_monitoreo_nombre = "-- Seleccione un Servidor --"
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
            st.rerun()
            
        # Si cambia el servidor, reiniciamos el segundo filtro de forma estricta
        if seleccion_srv != st.session_state.filtro_monitoreo_nombre:
            st.session_state.filtro_monitoreo_nombre = seleccion_srv
            st.session_state.filtro_monitoreo_sensor = "-- Seleccione un Sensor --"
            st.rerun()

        # Control de flujo si el lienzo debe permanecer vacío
        if st.session_state.filtro_monitoreo_nombre == "-- Seleccione un Servidor --":
            st.info("💡 Por favor, seleccione un servidor para estructurar el catálogo de sensores activos.")
            cursor.close()
            conn.close()
            return

        # Consulta de metadatos del servidor seleccionado
        query = """
            SELECT ip, nombre_alias, sistema_operativo, 
                   id_sensor_cpu, id_sensor_ram, 
                   id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5,
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
        # SEGUNDO FILTRO: MAPEO DINÁMICO Y SELECCIÓN DEL SENSOR
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
        
        letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:"}
        for i in range(1, 6):
            id_disco = int(info_servidor.get(f'id_sensor_disco_{i}') or 0)
            if id_disco > 0:
                dict_sensores_activos[f"Disco ({letras_unidades[i]})"] = {"tipo": f"disco_{i}", "campo": f"val_disco_{i}", "unidad": "GB", "id": id_disco}

        if not dict_sensores_activos:
            st.warning("ℹ️ Este nodo no posee sensores activos configurados en el catálogo central.")
            cursor.close()
            conn.close()
            return

        opciones_sensores = ["-- Seleccione un Sensor --"] + list(dict_sensores_activos.keys())
        
        idx_sens_actual = 0
        if st.session_state.filtro_monitoreo_sensor in opciones_sensores:
            idx_sens_actual = opciones_sensores.index(st.session_state.filtro_monitoreo_sensor)

        seleccion_sensor = st.selectbox(
            "2. Seleccione el Sensor Específico para Análisis Temporal",
            options=opciones_sensores,
            index=idx_sens_actual,
            key="sb_mon_sensor"
        )

        if seleccion_sensor != st.session_state.filtro_monitoreo_sensor:
            st.session_state.filtro_monitoreo_sensor = seleccion_sensor
            st.rerun()

        # Control de flujo si no se ha elegido un sensor definitivo
        if st.session_state.filtro_monitoreo_sensor == "-- Seleccione un Sensor --":
            st.info("💡 Seleccione un sensor específico del menú desplegable para procesar la telemetría.")
            cursor.close()
            conn.close()
            return

        meta_sensor = dict_sensores_activos[st.session_state.filtro_monitoreo_sensor]

        # =====================================================================
        # EXTRACTOR DE BACKEND Y PROCESAMIENTO NATIVO
        # =====================================================================
        datos_historicos = obtener_datos_historicos(ip_objetivo)
        
        if not datos_historicos:
            st.error(f"❌ No se registran datos en la base de datos para el sensor ID {meta_sensor['id']}.")
            cursor.close()
            conn.close()
            return

        # Despliegue de métrica actual (Registro en índice 0, el más reciente)
        registro_reciente = datos_historicos[0]
        valor_actual = registro_reciente[meta_sensor["campo"]]
        
        delta_visual = None
        if len(datos_historicos) > 1:
            try:
                diferencia = round(float(valor_actual) - float(datos_historicos[1][meta_sensor["campo"]]), 2)
                delta_visual = f"+{diferencia} {meta_sensor['unidad']}" if diferencia > 0 else f"{diferencia} {meta_sensor['unidad']}"
            except (ValueError, TypeError):
                pass

        st.markdown("---")
        col_kpi, col_status = st.columns([1, 2])
        
        with col_kpi:
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

        # =====================================================================
        # CONSTRUCCIÓN DE LA GRÁFICA MEDIANTE SVG / HTML (100% LIBRE DE PANDAS)
        # =====================================================================
        st.write("### 📈 Gráfica de Comportamiento Histórico")
        
        # Procesamos la lista invertida cronológicamente
        valores_linea = []
        for reg in reversed(datos_historicos):
            try:
                valores_linea.append(float(reg[meta_sensor["campo"]] or 0.0))
            except (ValueError, TypeError):
                valores_linea.append(0.0)

        if len(valores_linea) > 0:
            # Dimensiones fijas para el lienzo SVG gráfico
            ancho_svg = 800
            alto_svg = 250
            padding = 30
            
            # Buscamos extremos usando funciones nativas (max/min)
            max_val = max(valores_linea) if max(valores_linea) != min(valores_linea) else max(valores_linea) + 1
            min_val = min(valores_linea)
            rango = (max_val - min_val) if (max_val - min_val) > 0 else 1
            
            puntos_totales = len(valores_linea)
            paso_x = (ancho_svg - (2 * padding)) / (puntos_totales - 1) if puntos_totales > 1 else (ancho_svg - (2 * padding))
            
            # Generar coordenadas de puntos para la polilínea SVG
            lista_coordenadas = []
            for i, val in enumerate(valores_linea):
                x = padding + (i * paso_x)
                # Invertimos el eje Y porque en SVG el origen (0,0) está arriba a la izquierda
                y = (alto_svg - padding) - ((val - min_val) / rango) * (alto_svg - (2 * padding))
                lista_coordenadas.append(f"{x},{y}")
            
            puntos_str = " ".join(lista_coordenadas)
            
            # Construcción dinámica del componente SVG en un string
            svg_html = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                <svg viewBox="0 0 {ancho_svg} {alto_svg}" width="100%" height="{alto_svg}" xmlns="http://www.w3.org/2000/svg">
                    <line x1="{padding}" y1="{alto_svg - padding}" x2="{ancho_svg - padding}" y2="{alto_svg - padding}" stroke="#e9ecef" stroke-width="1" />
                    <line x1="{padding}" y1="{padding}" x2="{ancho_svg - padding}" y2="{padding}" stroke="#e9ecef" stroke-width="1" />
                    
                    <polyline points="{puntos_str}" fill="none" stroke="#003366" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                    
                    <text x="{padding}" y="{padding - 10}" fill="#777777" font-size="11" font-family="Arial">Máx: {max_val} {meta_sensor['unidad']}</text>
                    <text x="{padding}" y="{alto_svg - padding + 18}" fill="#777777" font-size="11" font-family="Arial">Mín: {min_val} {meta_sensor['unidad']}</text>
                </svg>
            </div>
            """
            # Renderizado por inyección directa HTML en la UI
            st.components.v1.html(svg_html, height=alto_svg + 40)
        else:
            st.warning("No hay suficientes muestras puntuales para diagramar la curva.")
            
        st.caption(f"📅 Ventana de visualización: {len(valores_linea)} muestras analizadas consecutivamente.")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de monitoreo: {e}")

if __name__ == "__main__":
    st.set_page_config(page_title="SIMPOL - Monitoreo", layout="wide")
    mostrar_pantalla()