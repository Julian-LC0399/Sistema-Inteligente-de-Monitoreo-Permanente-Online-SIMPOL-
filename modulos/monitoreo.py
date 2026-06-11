import streamlit as st
from database import conectar_bd, obtener_lista_servidores
import time

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    """
    Vista del módulo de monitoreo - Banco Caroní.
    - Sincronizado al 100% con la totalidad de campos de SIMPOL V3.9.
    - Autorefresco Nativo Automático cada 15 segundos en sincronía con agente.py.
    - Mapeo EDITABLE de TODAS las variables de la tabla para personalización visual.
    - Oculta de forma automática las columnas sin actividad (puros ceros / INACTIVO) según el servidor.
    - Paleta de colores corporativos del Banco Caroní.
    - 100% libre de Pandas y Numpy.
    """
    
    # 1. CONTROL DE ACCESO OPERATIVO (Matriz de Seguridad)
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no cuenta con el privilegio [VER_SISTEMA].")
            return

    # Encabezado corporativo
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🖥️ Centro de Control y Telemetría</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Plataforma Global de Observabilidad | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Sistema multi-pestaña corporativo
    tab_historico, tab_graficas = st.tabs(["📊 Histórico Telemetría", "📈 Gráficas Analíticas"])

    # =========================================================================
    # PESTAÑA 1: HISTÓRICO DE TELEMETRÍA (Estructura Totalmente Desplegada)
    # =========================================================================
    with tab_historico:
        
        # =========================================================================
        # 📝 DICCIONARIO MAESTRO DE COLUMNAS (Mapeo Completo SIMPOL V3.9)
        # =========================================================================
        DICCIONARIO_COLUMNAS = {
            # Identidad y Núcleo
            "fecha_registro": "FECHA Y HORA",
            "ip_servidor": "DIRECCIÓN IP",
            "val_cpu": "CPU (%)",
            
            # Memoria RAM
            "val_ram_bytes": "RAM (BYTES)",
            "val_ram_gb": "RAM USADA (GB)",
            "val_ram_pct": "RAM USADA (%)",
            "val_ram_total_gb": "RAM TOTAL (GB)",
            
            # Almacenamiento - DISCO C
            "val_disco_1_bytes": "DISCO C (BYTES)",
            "val_disco_1_gb": "DISCO C USADO (GB)",
            "val_disco_1_pct": "DISCO C USADO (%)",
            "val_disco_1_total_gb": "DISCO C TOTAL (GB)",
            
            # Almacenamiento - DISCO D
            "val_disco_2_bytes": "DISCO D (BYTES)",
            "val_disco_2_gb": "DISCO D USADO (GB)",
            "val_disco_2_pct": "DISCO D USADO (%)",
            "val_disco_2_total_gb": "DISCO D TOTAL (GB)",
            
            # Almacenamiento - DISCO E
            "val_disco_3_bytes": "DISCO E (BYTES)",
            "val_disco_3_gb": "DISCO E USADO (GB)",
            "val_disco_3_pct": "DISCO E USADO (%)",
            "val_disco_3_total_gb": "DISCO E TOTAL (GB)",
            
            # Almacenamiento - DISCO F
            "val_disco_4_bytes": "DISCO F (BYTES)",
            "val_disco_4_gb": "DISCO F USADO (GB)",
            "val_disco_4_pct": "DISCO F USADO (%)",
            "val_disco_4_total_gb": "DISCO F TOTAL (GB)",
            
            # Almacenamiento - DISCO G
            "val_disco_5_bytes": "DISCO G (BYTES)",
            "val_disco_5_gb": "DISCO G USADO (GB)",
            "val_disco_5_pct": "DISCO G USADO (%)",
            "val_disco_5_total_gb": "DISCO G TOTAL (GB)",
            
            # Almacenamiento - DISCO Y
            "val_disco_6_bytes": "DISCO Y (BYTES)",
            "val_disco_6_gb": "DISCO Y USADO (GB)",
            "val_disco_6_pct": "DISCO Y USADO (%)",
            "val_disco_6_total_gb": "DISCO Y TOTAL (GB)",
            
            # Monitoreo de Servicios Corporativos (Estados y Métricas)
            "estado_servicio_1": "ESTADO SERVICIO 1", "val_servicio_1": "MÉTRICA SERVICIO 1",
            "estado_servicio_2": "ESTADO SERVICIO 2", "val_servicio_2": "MÉTRICA SERVICIO 2",
            "estado_servicio_3": "ESTADO SERVICIO 3", "val_servicio_3": "MÉTRICA SERVICIO 3",
            "estado_servicio_4": "ESTADO SERVICIO 4", "val_servicio_4": "MÉTRICA SERVICIO 4",
            "estado_servicio_5": "ESTADO SERVICIO 5", "val_servicio_5": "MÉTRICA SERVICIO 5",
            "estado_servicio_6": "ESTADO SERVICIO 6", "val_servicio_6": "MÉTRICA SERVICIO 6",
            "estado_servicio_7": "ESTADO SERVICIO 7", "val_servicio_7": "MÉTRICA SERVICIO 7",
            "estado_servicio_8": "ESTADO SERVICIO 8", "val_servicio_8": "MÉTRICA SERVICIO 8",
            
            # Red, Conectividad e Integridad
            "val_red": "TRÁFICO RED",
            "val_latencia": "LATENCIA (MS)",
            "estado_sistema": "ESTADO SIS."
        }

        try:
            # Cargar catálogo de servidores para el Filtro
            servidores_activos = obtener_lista_servidores()
            if not servidores_activos:
                st.info("💡 No hay servidores activos mapeados en el catálogo central.")
            else:
                lista_nombres_bd = sorted(list(set([r['nombre_alias'] for r in servidores_activos if r['nombre_alias']])))
                opciones_servidores = ["-- Seleccione un Servidor para empezar --", "-- Todos los Servidores --"] + lista_nombres_bd

                # Control superior del filtro (Fuera del fragmento para no perder el foco)
                seleccion_srv = st.selectbox("Filtrar por Servidor", options=opciones_servidores, key="sb_monitoreo_srv_v39_maestro")
                
                if seleccion_srv == "-- Seleccione un Servidor para empezar --":
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("🔍 Por favor, utilice el menú desplegable superior para seleccionar un nodo de red o evaluar el histórico global.")
                else:
                    
                    # =========================================================================
                    # 🔄 FRAGMENTO DINÁMICO DE AUTOREFRESCO (Sincronizado a 15s con el agente)
                    # =========================================================================
                    @st.fragment(run_every=15)
                    def renderizar_rejilla_tiempo_real(seleccion):
                        # Indicador sutil de actualización en la esquina superior de la rejilla
                        st.markdown(
                            f'<div style="text-align: right; color: #003366; font-size: 11px; font-weight: bold; margin-bottom: -15px;">'
                            f'🔄 Sincronizado con SIMPOL Core (Auto-refresh: 15s)</div>', 
                            unsafe_allow_html=True
                        )
                        
                        conexion = conectar_bd()
                        if not conexion:
                            st.error("❌ Error de conexión con el servidor de Base de Datos SIMPOL.")
                            return
                        
                        registros = []
                        try:
                            with conexion.cursor(dictionary=True) as cursor:
                                if seleccion == "-- Todos los Servidores --":
                                    query = "SELECT * FROM monitoreo ORDER BY fecha_registro DESC LIMIT 300;"
                                    cursor.execute(query)
                                else:
                                    info_srv = next((s for s in servidores_activos if s['nombre_alias'] == seleccion), None)
                                    if info_srv:
                                        query = "SELECT * FROM monitoreo WHERE ip_servidor = %s ORDER BY fecha_registro DESC LIMIT 300;"
                                        cursor.execute(query, (info_srv['ip'],))
                                    else:
                                        query = "SELECT * FROM monitoreo ORDER BY fecha_registro DESC LIMIT 300;"
                                        cursor.execute(query)
                                
                                registros = cursor.fetchall()
                        finally:
                            conexion.close()

                        if not registros:
                            st.info(f"💡 No se encontraron muestras de telemetría para la selección actual.")
                        else:
                            # FILTRADO DINÁMICO VERTICAL: Evalúa qué columnas tienen datos reales
                            todas_las_columnas = list(registros[0].keys())
                            columnas_visibles = []

                            for col in todas_las_columnas:
                                if col == "id":
                                    continue

                                tiene_datos_validos = False
                                for fila in registros:
                                    val = fila.get(col)
                                    if val is not None:
                                        if isinstance(val, (int, float)) and val != 0 and val != 0.0:
                                            tiene_datos_validos = True
                                            break
                                        elif isinstance(val, str) and val.strip() not in ["0", "0.0", "0.00", "INACTIVO", "OFF"]:
                                            tiene_datos_validos = True
                                            break
                                        elif not isinstance(val, (int, float, str)):
                                            tiene_datos_validos = True
                                            break
                                
                                # Columnas base persistentes
                                if col in ["fecha_registro", "ip_servidor", "estado_sistema"]:
                                    tiene_datos_validos = True

                                if tiene_datos_validos:
                                    columnas_visibles.append(col)

                            st.markdown(f"📊 **Result Grid Dinámico:** Mostrando {len(registros)} muestras bajo el estándar visual del Banco.", unsafe_allow_html=True)

                            # Renderizado de Tabla HTML/CSS con Colores Corporativos
                            html_tabla = """
                            <div style="overflow-x: auto; width: 100%; border: 1px solid #003366; border-radius: 4px; margin-top: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                                <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;">
                                    <thead>
                                        <tr style="background-color: #003366; border-bottom: 3px solid #002244; text-align: left;">
                            """

                            # Traducir los nombres usando el Diccionario Maestro Completo
                            for col in columnas_visibles:
                                col_label = DICCIONARIO_COLUMNAS.get(col, col.replace('_', ' ').upper())
                                html_tabla += f'<th style="padding: 12px 14px; color: #FFFFFF; font-weight: bold; border-right: 1px solid #004488; white-space: nowrap; letter-spacing: 0.5px;">{col_label}</th>'
                            
                            html_tabla += "</tr></thead><tbody>"

                            for idx, fila in enumerate(registros):
                                bg_color = "#ffffff" if idx % 2 == 0 else "#f4f7f9"
                                html_tabla += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #e0e6ed;">'
                                
                                for col in columnas_visibles:
                                    valor = fila.get(col)
                                    if valor is None:
                                        valor_str = '<span style="color: #a0aec0; font-style: italic;">NULL</span>'
                                    elif hasattr(valor, "strftime"):
                                        valor_str = valor.strftime("%Y-%m-%d %H:%M:%S")
                                    else:
                                        valor_str = str(valor)
                                    
                                    html_tabla += f'<td style="padding: 10px 14px; color: #2d3748; border-right: 1px solid #e0e6ed; white-space: nowrap;">{valor_str}</td>'
                                
                                html_tabla += "</tr>"

                            html_tabla += "</tbody></table></div>"
                            st.markdown(html_tabla, unsafe_allow_html=True)
                    
                    # Invocar la ejecución del fragmento en tiempo real
                    renderizar_rejilla_tiempo_real(seleccion_srv)

        except Exception as e:
            st.error(f"⚠️ Error al procesar la rejilla de telemetría corporativa: {e}")

    # =========================================================================
    # PESTAÑA 2: GRÁFICAS ANALÍTICAS (Resguardada para uso posterior)
    # =========================================================================
    with tab_graficas:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="border-left: 5px solid #003366; background-color: #f4f7f9; padding: 20px; border-radius: 4px;">'
            f'<h4 style="color: #003366; margin-top: 0px; margin-bottom: 8px;">📈 Módulo de Gráficas de Rendimiento (En Reserva)</h4>'
            f'<p style="color: #4a5568; font-size: 14px; margin: 0px;">'
            f'Esta sección está reservada para el despliegue posterior de diagramas de tendencias temporales, '
            f'comportamiento de sensores PRTG y análisis de carga crítica de CPU/RAM. '
            f'<br><br><b>Estado actual:</b> Esperando asignación de componentes visuales (Plotly / Streamlit native charts).</p>'
            f'</div>',
            unsafe_allow_html=True
        )

def limpiar_filtros_monitoreo():
    if "modulo_actual_monitoreo" in st.session_state:
        del st.session_state["modulo_actual_monitoreo"]