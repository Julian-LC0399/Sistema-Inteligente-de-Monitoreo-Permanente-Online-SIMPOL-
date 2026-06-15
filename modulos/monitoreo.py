import streamlit as st
from database import conectar_bd, obtener_lista_servidores

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    """
    Vista del módulo de monitoreo - Banco Caroní (SIMPOL V3.9.8)
    - Sincronizado al 100% con el esquema oficial de la Base de Datos.
    - Filosofía: Métricas basadas en disponibilidad y espacio libre.
    - Autorefresco Nativo Automático cada 15 segundos mediante fragmentos.
    - 100% LIBRE DE PANDAS Y NUMPY: Evita colisiones de dependencias en el servidor.
    - Presentación: Métricas nativas agrupadas por componente con color Azul Institucional (#003366).
    - Scroll Avanzado: Rejilla con desplazamiento de doble eje y cabecera 'sticky' inmovilizada.
    """
    
    # 1. CONTROL DE ACCESO OPERATIVO
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Encabezado corporativo institucional
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🖥️ Centro de Control y Telemetría</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Plataforma Global de Observabilidad | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Inicializar selectores globales en Session State para mantener sincronización entre pestañas
    if "sb_srv_tab1" not in st.session_state:
        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
    if "sb_graf_srv" not in st.session_state:
        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
    if "sb_graf_sensor" not in st.session_state:
        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"

    tab_historico, tab_graficas = st.tabs(["📊 Histórico Telemetría", "📈 Variables por Componente"])

    # DICCIONARIO MAESTRO SIMPOL V3.9.8 PARA TRADUCCIÓN DE ENCABEZADOS DE REJILLA HTML
    DICCIONARIO_COLUMNAS = {
        "fecha_registro": "FECHA Y HORA",
        "ip_servidor": "DIRECCIÓN IP",
        "val_cpu": "CPU (%)",
        "val_ram_total_gb": "RAM TOTAL (GB)",
        "val_ram_disponible_pct": "RAM DISPONIBLE (%)",
        "val_ram_disponible_gb": "RAM DISPONIBLE (GB)",
        "val_disco_1_total_gb": "DISCO C TOTAL (GB)", "val_disco_1_pct_libre": "DISCO C LIBRE (%)", "val_disco_1_libres_gb": "DISCO C LIBRE (GB)",
        "val_disco_2_total_gb": "DISCO D TOTAL (GB)", "val_disco_2_pct_libre": "DISCO D LIBRE (%)", "val_disco_2_libres_gb": "DISCO D LIBRE (GB)",
        "val_disco_3_total_gb": "DISCO E TOTAL (GB)", "val_disco_3_pct_libre": "DISCO E LIBRE (%)", "val_disco_3_libres_gb": "DISCO E LIBRE (GB)",
        "val_disco_4_total_gb": "DISCO F TOTAL (GB)", "val_disco_4_pct_libre": "DISCO F LIBRE (%)", "val_disco_4_libres_gb": "DISCO F LIBRE (GB)",
        "val_disco_5_total_gb": "DISCO G TOTAL (GB)", "val_disco_5_pct_libre": "DISCO G LIBRE (%)", "val_disco_5_libres_gb": "DISCO G LIBRE (GB)",
        "val_disco_6_total_gb": "DISCO Y TOTAL (GB)", "val_disco_6_pct_libre": "DISCO Y LIBRE (%)", "val_disco_6_libres_gb": "DISCO Y LIBRE (GB)",
        "estado_servicio_1": "ESTADO SERVICIO 1", "val_servicio_1": "MÉTRICA SERVICIO 1",
        "estado_servicio_2": "ESTADO SERVICIO 2", "val_servicio_2": "MÉTRICA SERVICIO 2",
        "estado_servicio_3": "ESTADO SERVICIO 3", "val_servicio_3": "MÉTRICA SERVICIO 3",
        "estado_servicio_4": "ESTADO SERVICIO 4", "val_servicio_4": "MÉTRICA SERVICIO 4",
        "estado_servicio_5": "ESTADO SERVICIO 5", "val_servicio_5": "MÉTRICA SERVICIO 5",
        "estado_servicio_6": "ESTADO SERVICIO 6", "val_servicio_6": "MÉTRICA SERVICIO 6",
        "estado_servicio_7": "ESTADO SERVICIO 7", "val_servicio_7": "MÉTRICA SERVICIO 7",
        "estado_servicio_8": "ESTADO SERVICIO 8", "val_servicio_8": "MÉTRICA SERVICIO 8",
        "val_red": "TRÁFICO RED (MBPS)", "val_latencia": "LATENCIA (MS)", "estado_sistema": "ESTADO SIS."
    }

    servidores_activos = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores_activos if s.get('nombre_alias')])))
    opciones_servidores = ["-- Seleccione un Servidor para empezar --", "-- Todos los Servidores --"] + lista_nombres_bd

    # FUNCIONES CALLBACK PARA BI-SINCRONIZACIÓN SEGURA ENTRE PESTAÑAS
    def on_change_tab1():
        val = st.session_state["sb_srv_tab1"]
        if val in ["-- Seleccione un Servidor para empezar --", "-- Todos los Servidores --"]:
            st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
        else:
            st.session_state["sb_graf_srv"] = val

    def on_change_tab2():
        val = st.session_state["sb_graf_srv"]
        if val == "-- Seleccione un Servidor --":
            st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
        else:
            st.session_state["sb_srv_tab1"] = val

    # =========================================================================
    # PESTAÑA 1: HISTÓRICO DE TELEMETRÍA (TABLA HTML PURA CON AUTO-REFRESCO Y SCROLL)
    # =========================================================================
    with tab_historico:
        try:
            if not servidores_activos:
                st.info("💡 No hay servidores activos mapeados en el catálogo central.")
            else:
                col_sel, col_limpiar = st.columns([4, 1])
                with col_sel:
                    if st.session_state.get("sb_srv_tab1") not in opciones_servidores:
                        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
                    
                    seleccion_srv = st.selectbox(
                        "Filtrar por Servidor", 
                        options=opciones_servidores, 
                        key="sb_srv_tab1",
                        on_change=on_change_tab1
                    )
                
                with col_limpiar:
                    st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🧹 Limpiar Filtro", key="btn_limpiar_tab1", use_container_width=True):
                        st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
                        st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
                        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"
                        st.rerun()

                if seleccion_srv == "-- Seleccione un Servidor para empezar --":
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("🔍 Seleccione un nodo de red para evaluar el histórico global en tiempo real.")
                else:
                    @st.fragment(run_every=15)
                    def renderizar_rejilla_tiempo_real(seleccion):
                        st.markdown('<div style="text-align: right; color: #003366; font-size: 11px; font-weight: bold; margin-bottom: -15px;">🔄 Sincronizado con SIMPOL Core (Auto-refresh: 15s)</div>', unsafe_allow_html=True)
                        
                        conexion = conectar_bd()
                        if not conexion:
                            st.error("❌ Error de conexión con el servidor de Base de Datos SIMPOL.")
                            return
                        
                        registros = []
                        try:
                            with conexion.cursor(dictionary=True) as cursor:
                                if seleccion == "-- Todos los Servidores --":
                                    cursor.execute("SELECT * FROM monitoreo ORDER BY fecha_registro DESC LIMIT 300;")
                                else:
                                    info_srv = next((s for s in servidores_activos if s['nombre_alias'] == seleccion), None)
                                    if info_srv:
                                        cursor.execute("SELECT * FROM monitoreo WHERE ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 300;", (info_srv['ip'],))
                                    else:
                                        cursor.execute("SELECT * FROM monitoreo ORDER BY fecha_registro DESC LIMIT 300;")
                                registros = cursor.fetchall()
                        finally:
                            conexion.close()

                        if not registros:
                            st.info("💡 No se encontraron muestras de telemetría.")
                        else:
                            todas_las_columnas = list(registros[0].keys())
                            columnas_visibles = []

                            for col in todas_las_columnas:
                                if col == "id": continue
                                tiene_datos_validos = False
                                for fila in registros:
                                    val = fila.get(col)
                                    if val is not None:
                                        try:
                                            if isinstance(val, (int, float)) and float(val) > 0:
                                                tiene_datos_validos = True
                                                break
                                            elif isinstance(val, str) and val.strip() not in ["0", "0.0", "0.00", "INACTIVO", "OFF"]:
                                                tiene_datos_validos = True
                                                break
                                            elif not isinstance(val, (int, float, str)):
                                                tiene_datos_validos = True
                                                break
                                        except (ValueError, TypeError):
                                            pass
                                
                                if col in ["fecha_registro", "ip_servidor", "estado_sistema"]:
                                    tiene_datos_validos = True

                                if tiene_datos_validos:
                                    columnas_visibles.append(col)

                            # CONTENEDOR MAESTRO DE REJILLA CON SCROLL MULTIDIRECCIONAL Y CABECERA FLOTANTE CONGELADA
                            html_tabla = """
                            <div style="overflow: auto; max-height: 480px; width: 100%; border: 1px solid #003366; border-radius: 4px; margin-top: 8px;">
                                <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                                    <thead>
                                        <tr style="text-align: left;">
                            """
                            for col in columnas_visibles:
                                col_label = DICCIONARIO_COLUMNAS.get(col, col.replace('_', ' ').upper())
                                html_tabla += f'<th style="position: sticky; top: 0; background-color: #003366; padding: 12px 14px; color: #FFFFFF; font-weight: bold; white-space: nowrap; z-index: 2;">{col_label}</th>'
                            html_tabla += "</tr></thead><tbody>"

                            for idx, fila in enumerate(registros):
                                bg_color = "#ffffff" if idx % 2 == 0 else "#f4f7f9"
                                html_tabla += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #e0e6ed;">'
                                for col in columnas_visibles:
                                    valor = fila.get(col)
                                    valor_str = valor.strftime("%Y-%m-%d %H:%M:%S") if hasattr(valor, "strftime") else str(valor if valor is not None else "")
                                    html_tabla += f'<td style="padding: 10px 14px; white-space: nowrap;">{valor_str}</td>'
                                html_tabla += "</tr>"
                            html_tabla += "</tbody></table></div>"
                            st.markdown(html_tabla, unsafe_allow_html=True)
                    
                    renderizar_rejilla_tiempo_real(st.session_state["sb_srv_tab1"])
        except Exception as e:
            st.error(f"⚠️ Error al procesar la rejilla: {e}")

    # =========================================================================
    # PESTAÑA 2: VISTA MULTI-VARIABLE (NATIVO AZUL INSTITUCIONAL)
    # =========================================================================
    with tab_graficas:
        st.markdown("""
            <style>
                div[data-testid="stMetricValue"] {
                    color: #003366 !important;
                    font-family: monospace !important;
                    font-weight: bold !important;
                }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<h3 style="color:#003366; margin-top:10px;">📊 Inspección de Componentes Globales</h3>', unsafe_allow_html=True)
        
        @st.fragment(run_every=15)
        def renderizar_bloque_analitico():
            if not servidores_activos:
                st.info("💡 Catálogo de infraestructura vacío.")
                return

            opciones_srv_graf = ["-- Seleccione un Servidor --"] + lista_nombres_bd

            # Distribución adaptativa de columnas según la selección
            filtro_1_activo = (st.session_state.get("sb_graf_srv") != "-- Seleccione un Servidor --")
            
            if filtro_1_activo:
                col_g1, col_g2, col_g3 = st.columns([3, 3, 1])
            else:
                col_g1, col_g3 = st.columns([6, 1])

            with col_g1:
                srv_elegido = st.selectbox(
                    "1. Servidor Institucional", 
                    options=opciones_srv_graf, 
                    key="sb_graf_srv",
                    on_change=on_change_tab2
                )

            filtro_1_activo = (srv_elegido != "-- Seleccione un Servidor --")
            opciones_dinamicas_componentes = ["-- Seleccione un Componente --"]
            historico_muestras = []

            if filtro_1_activo:
                info_srv = next((s for s in servidores_activos if s['nombre_alias'] == srv_elegido), None)
                if info_srv:
                    conexion = conectar_bd()
                    if conexion:
                        try:
                            with conexion.cursor(dictionary=True) as cursor:
                                cursor.execute("""
                                    SELECT * FROM monitoreo 
                                    WHERE TRIM(ip_servidor) = %s 
                                    ORDER BY fecha_registro DESC LIMIT 1;
                                """, (str(info_srv['ip']).strip(),))
                                historico_muestras = cursor.fetchall()
                        except Exception as err:
                            st.error(f"❌ Error analítico de BD: {err}")
                        finally:
                            conexion.close()

            ultimo_registro = historico_muestras[0] if historico_muestras else None

            # DETECCIÓN DINÁMICA DE COMPONENTES ACTIVOS
            if ultimo_registro and filtro_1_activo:
                if ultimo_registro.get('val_cpu') is not None:
                    opciones_dinamicas_componentes.append("🔥 Procesador (CPU)")
                
                if ultimo_registro.get('val_ram_total_gb') is not None and float(ultimo_registro.get('val_ram_total_gb', 0)) > 0:
                    opciones_dinamicas_componentes.append("🧠 Memoria RAM")
                
                mapeo_letras = {1: "C:\\", 2: "D:\\", 3: "E:\\", 4: "F:\\", 5: "G:\\", 6: "Y:\\"}
                for i in range(1, 7):
                    val_total_disco = ultimo_registro.get(f'val_disco_{i}_total_gb')
                    if val_total_disco is not None and float(val_total_disco) > 0:
                        opciones_dinamicas_componentes.append(f"💾 Almacenamiento Disco {mapeo_letras[i]}")
                
                if ultimo_registro.get('val_red') is not None or ultimo_registro.get('val_latencia') is not None:
                    opciones_dinamicas_componentes.append("🌐 Conectividad y Red")

                for i in range(1, 9):
                    st_serv = ultimo_registro.get(f"estado_servicio_{i}")
                    if st_serv and str(st_serv).strip().upper() not in ["", "NONE", "NULL", "OFF"]:
                        opciones_dinamicas_componentes.append(f"⚙️ Servicio Core {i}")

            if filtro_1_activo:
                with col_g2:
                    if st.session_state.get("sb_graf_sensor") not in opciones_dinamicas_componentes:
                        st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"
                    
                    componente_elegido = st.selectbox("2. Componente de Infraestructura", options=opciones_dinamicas_componentes, key="sb_graf_sensor")
            else:
                componente_elegido = "-- Seleccione un Componente --"
                st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"

            with col_g3:
                st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🧹 Limpiar", key="btn_limpiar_tab2", use_container_width=True):
                    st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor para empezar --"
                    st.session_state["sb_graf_srv"] = "-- Seleccione un Servidor --"
                    st.session_state["sb_graf_sensor"] = "-- Seleccione un Componente --"
                    st.rerun()

            st.markdown("---")

            if not filtro_1_activo:
                st.info("💡 Seleccione un Servidor Institucional para habilitar el análisis de variables de red.")
            elif componente_elegido == "-- Seleccione un Componente --":
                st.info("💡 Servidor enlazado correctamente. Despliegue el Filtro 2 para analizar un componente.")
            elif not ultimo_registro:
                st.warning(f"⚠️ No hay muestras de telemetría disponibles para este nodo.")
            else:
                fecha_srv = ultimo_registro.get('fecha_registro')
                fecha_str = fecha_srv.strftime("%Y-%m-%d %H:%M:%S") if hasattr(fecha_srv, "strftime") else str(fecha_srv)
                
                st.write(f"📍 **Nodo IP:** `{ultimo_registro.get('ip_servidor')}` | ⏱ **Estampa Temporal:** `{fecha_str}`")
                st.markdown("<br>", unsafe_allow_html=True)

                # RENDERIZADO DE MÉTRICAS SEGÚN EL COMPONENTE SELECCIONADO
                if "Procesador (CPU)" in componente_elegido:
                    val_cpu = float(ultimo_registro.get('val_cpu', 0.0))
                    st.metric(label="Carga Actual del Procesamiento", value=f"{val_cpu:.2f} %")

                elif "Memoria RAM" in componente_elegido:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="Capacidad Física Total", value=f"{float(ultimo_registro.get('val_ram_total_gb', 0.0)):.2f} GB")
                    with col2:
                        st.metric(label="Espacio Disponible (Absoluto)", value=f"{float(ultimo_registro.get('val_ram_disponible_gb', 0.0)):.2f} GB")
                    with col3:
                        st.metric(label="Espacio Disponible (Relativo)", value=f"{float(ultimo_registro.get('val_ram_disponible_pct', 0.0)):.2f} %")

                elif "Almacenamiento Disco" in componente_elegido:
                    letra_disco = componente_elegido.split()[-1]
                    mapeo_letras_rev = {"C:\\": 1, "D:\\": 2, "E:\\": 3, "F:\\": 4, "G:\\": 5, "Y:\\": 6}
                    idx_d = mapeo_letras_rev.get(letra_disco, 1)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label=f"Tamaño Total ({letra_disco})", value=f"{float(ultimo_registro.get(f'val_disco_{idx_d}_total_gb', 0.0)):.2f} GB")
                    with col2:
                        st.metric(label=f"Espacio Libre ({letra_disco} GB)", value=f"{float(ultimo_registro.get(f'val_disco_{idx_d}_libres_gb', 0.0)):.2f} GB")
                    with col3:
                        st.metric(label=f"Espacio Libre ({letra_disco} %)", value=f"{float(ultimo_registro.get(f'val_disco_{idx_d}_pct_libre', 0.0)):.2f} %")

                elif "Conectividad y Red" in componente_elegido:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="Tráfico de Interfaz de Red", value=f"{float(ultimo_registro.get('val_red', 0.0)):.2f} Mbps")
                    with col2:
                        st.metric(label="Latencia de Enlace (ICMP Ping)", value=f"{float(ultimo_registro.get('val_latencia', 0.0)):.2f} ms")

                elif "Servicio Core" in componente_elegido:
                    num_s = componente_elegido.split()[-1]
                    val_estado = str(ultimo_registro.get(f"estado_servicio_{num_s}", "DESCONOCIDO")).strip().upper()
                    val_metrica = float(ultimo_registro.get(f"val_servicio_{num_s}", 0.0))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label=f"Estado Operativo - Servicio {num_s}", value=val_estado)
                    with col2:
                        st.metric(label=f"Última Métrica del Proceso", value=f"{val_metrica:.2f}")

        renderizar_bloque_analitico()

def limpiar_filtros_monitoreo():
    if "modulo_actual_monitoreo" in st.session_state:
        del st.session_state["modulo_actual_monitoreo"]