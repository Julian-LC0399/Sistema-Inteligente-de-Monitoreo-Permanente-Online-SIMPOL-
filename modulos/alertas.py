import streamlit as st
import traceback
import logging
import time
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# CALLBACKS PARA FILTROS
# =====================================================================

def callback_cambio_filtro_alerta():
    """Callback cuando cambia el filtro de servidor en alertas"""
    pass

def callback_cambio_filtro_umbral():
    """Callback cuando cambia el filtro de servidor en umbrales"""
    pass

# =====================================================================
# FUNCIONES PARA CONSULTAR Y GESTIONAR ALERTAS EN BD
# =====================================================================

def obtener_alertas_activas(ip_servidor=None, criticidad=None):
    """Obtiene alertas activas de la tabla alertas con filtros opcionales"""
    conn = conectar_bd()
    alertas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT a.*, s.nombre_alias 
                FROM alertas a
                LEFT JOIN servidores s ON a.ip_servidor = s.ip
                WHERE a.estado_alerta = 'ACTIVA'
            """
            params = []
            condiciones = []
            
            if ip_servidor:
                condiciones.append("a.ip_servidor = %s")
                params.append(ip_servidor)
            
            if criticidad and criticidad != "-- Todas --":
                condiciones.append("a.tipo_alerta = %s")
                params.append(criticidad)
            
            if condiciones:
                query += " AND " + " AND ".join(condiciones)
            
            query += " ORDER BY a.fecha_inicio DESC"
            cursor.execute(query, tuple(params))
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo alertas activas: {e}")
    return alertas

def obtener_ultimo_monitoreo(ip_servidor):
    """Obtiene el último registro de monitoreo para un servidor"""
    conn = conectar_bd()
    registro = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM monitoreo 
                WHERE ip_servidor = %s 
                ORDER BY fecha_registro DESC LIMIT 1
            """
            cursor.execute(query, (ip_servidor,))
            registro = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo último monitoreo: {e}")
    return registro

def obtener_estado_agente(ip_servidor):
    """Verifica si el agente está activo (último registro en los últimos 60 segundos)"""
    registro = obtener_ultimo_monitoreo(ip_servidor)
    if registro and registro.get('fecha_registro'):
        if isinstance(registro['fecha_registro'], datetime):
            diferencia = (datetime.now() - registro['fecha_registro']).total_seconds()
            return diferencia <= 60, registro
    return False, registro

def obtener_ultimos_umbrales(ip_servidor):
    """Obtiene los últimos umbrales configurados para un servidor"""
    conn = conectar_bd()
    umbrales = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM historico_umbrales 
                WHERE ip_servidor = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip_servidor,))
            umbrales = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo últimos umbrales: {e}")
    return umbrales

def guardar_nuevos_umbrales(ip, dict_umbrales, usuario_id, justificacion):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        columnas = [
            "ip_servidor", "usuario_id", "cpu_buen_estado", "cpu_advertencia", "cpu_critico",
            "cpu_p_buen_estado", "cpu_p_advertencia", "cpu_p_critico",
            "ram_buen_estado", "ram_advertencia", "ram_critico"
        ]
        valores_sql = [
            str(ip).strip(), int(usuario_id),
            int(dict_umbrales["cpu_buen_estado"]), int(dict_umbrales["cpu_advertencia"]), int(dict_umbrales["cpu_critico"]),
            int(dict_umbrales["cpu_p_buen_estado"]), int(dict_umbrales["cpu_p_advertencia"]), int(dict_umbrales["cpu_p_critico"]),
            int(dict_umbrales["ram_buen_estado"]), int(dict_umbrales["ram_advertencia"]), int(dict_umbrales["ram_critico"])
        ]
        
        for i in range(1, 7):
            columnas.extend([f"disco_{i}_buen_estado", f"disco_{i}_advertencia", f"disco_{i}_critico"])
            valores_sql.extend([
                int(dict_umbrales[f"disco_{i}_buen_estado"]),
                int(dict_umbrales[f"disco_{i}_advertencia"]),
                int(dict_umbrales[f"disco_{i}_critico"])
            ])
            
        columnas.extend([
            "red_limite_total_mbps", "red_limite_entrante_mbps", "red_limite_saliente_mbps", 
            "latencia_limite_ms", "perdida_limite_pct", "justificacion", "fecha_change"
        ])
        valores_sql.extend([
            int(dict_umbrales.get("red_limite_total_mbps", 100)),
            int(dict_umbrales.get("red_limite_entrante_mbps", 50)),
            int(dict_umbrales.get("red_limite_saliente_mbps", 50)),
            int(dict_umbrales.get("latencia_limite_ms", 150)),
            int(dict_umbrales.get("perdida_limite_pct", 1)),
            str(justificacion).strip(), datetime.now()
        ])
        
        placeholders = ", ".join(["%s"] * len(columnas))
        query = f"INSERT INTO historico_umbrales ({', '.join(columnas)}) VALUES ({placeholders})"
        cursor.execute(query, tuple(valores_sql))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error guardando nuevos umbrales: {e}")
        if conn: conn.close()
        return False

# =====================================================================
# FUNCIONES DE RENDERIZADO
# =====================================================================

def renderizar_alerta_card(alerta, agente_activo=False):
    """Renderiza una tarjeta de alerta individual con tamaños grandes"""
    nivel = alerta.get('tipo_alerta', 'ESTABLE')
    componente = alerta.get('componente', 'Desconocido')
    fecha_inicio = alerta.get('fecha_inicio', datetime.now())
    comentario = alerta.get('comentario', '')
    ip = alerta.get('ip_servidor', '')
    nombre_alias = alerta.get('nombre_alias', ip)
    val_pct = alerta.get('val_disponible_pct_momento', 0)
    val_gb = alerta.get('val_disponible_gb_momento', 0)
    val_total = alerta.get('val_total_gb_momento', 0)
    
    # Colores según nivel
    if nivel == "CRÍTICO":
        color_borde = "#FF4B4B"
        color_fondo = "#FFF5F5"
        color_texto = "#B71C1C"
        icono = "🔴"
        badge_color = "#FF4B4B"
        badge_texto = "#FFFFFF"
    elif nivel == "PRECAUCIÓN":
        color_borde = "#F1C40F"
        color_fondo = "#FFFDF5"
        color_texto = "#F57F17"
        icono = "🟡"
        badge_color = "#F1C40F"
        badge_texto = "#1A1A1A"
    else:
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        icono = "🟢"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
    
    if isinstance(fecha_inicio, datetime):
        fecha_str = fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_str = str(fecha_inicio)
    
    # Detalles adicionales
    detalles = f"Valor: {val_pct:.1f}%"
    if val_gb > 0 and val_total > 0:
        detalles += f" | Libre: {val_gb:.1f}/{val_total:.1f} GB"
    
    # Indicador de estado del agente
    estado_agente = "🟢 Agente Activo" if agente_activo else "🔴 Agente Offline (Últimos datos)"
    color_agente = "#2ECC71" if agente_activo else "#FF4B4B"
    
    html = f"""
    <div style="
        border-left: 8px solid {color_borde};
        background-color: {color_fondo};
        padding: 18px 22px;
        margin-bottom: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #E0E0E0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                <span style="font-size: 22px;">{icono}</span>
                <span style="font-weight: bold; font-size: 18px; color: {color_texto};">{componente}</span>
                <span style="color: #555; font-size: 15px; font-weight: 500;">{nombre_alias}</span>
                <span style="color: #888; font-size: 13px;">({ip})</span>
            </div>
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                <span style="font-size: 13px; color: {color_agente}; font-weight: bold;">{estado_agente}</span>
                <span style="
                    background-color: {badge_color};
                    color: {badge_texto};
                    padding: 4px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
                ">{nivel}</span>
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 15px; color: #444; display: flex; flex-wrap: wrap; gap: 20px;">
            <span>📅 <b>Inicio:</b> {fecha_str}</span>
            <span>📊 <b>{detalles}</b></span>
        </div>
        {f'<div style="margin-top: 10px; font-size: 14px; color: #555; background-color: #FFFFFF; padding: 10px 14px; border-radius: 6px; border: 1px solid #E8E8E8;">💬 <b>Comentario:</b> {comentario}</div>' if comentario else ''}
    </div>
    """
    return html

# =====================================================================
# VISTA PRINCIPAL
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    # Estilos
    st.markdown("""
        <style>
            [data-testid="stHorizontalBlock"] { padding-left: 0px !important; margin-left: 0px !important; }
            .stSlider { padding-left: 0px !important; }
            .stSelectbox label {
                font-weight: 600 !important;
                font-size: 14px !important;
            }
            .stButton button {
                font-weight: 600 !important;
                border-radius: 6px !important;
            }
            .stNumberInput input {
                font-size: 14px !important;
            }
            .stNumberInput label {
                font-size: 13px !important;
                font-weight: 500 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Título principal en azul
    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🛡️ Consola Operativa de Alertas y Políticas</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Gestor de Monitoreo SIMPOL | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_TODAS = "-- Todas --"

    # Inicialización de estados - IGUAL QUE MONITOREO.PY
    if "filtro_alerta_servidor" not in st.session_state:
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
    if "filtro_alerta_criticidad" not in st.session_state:
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
    if "filtro_umbral_servidor" not in st.session_state:
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
    if "ultima_actualizacion" not in st.session_state:
        st.session_state["ultima_actualizacion"] = datetime.now()

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
    opciones_criticidad = [VALOR_TODAS, "CRÍTICO", "PRECAUCIÓN", "ESTABLE"]

    # TABS - IGUAL QUE MONITOREO.PY
    tab1, tab2 = st.tabs(
        ["🚨 Alertas Activas", "⚙️ Configuración de Umbrales"],
        key="controlador_pestañas_alertas"
    )

    # =====================================================================
    # PESTAÑA 1: ALERTAS ACTIVAS - CON FILTROS ESTILO MONITOREO.PY
    # =====================================================================
    with tab1:
        st.markdown('<h4 style="color:#003366; font-size:16px; font-weight:bold;">📋 ALERTAS ACTIVAS EN EL SISTEMA</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Monitoreo en tiempo real de los componentes críticos</p>', unsafe_allow_html=True)
        
        # FILTROS - IGUAL QUE MONITOREO.PY (con columnas y on_change)
        col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
        with col_f1:
            st.selectbox(
                "Filtrar Servidor", 
                options=opciones_servidores, 
                key="filtro_alerta_servidor", 
                on_change=callback_cambio_filtro_alerta, 
                label_visibility="collapsed"
            )
        with col_f2:
            st.selectbox(
                "Filtrar Criticidad", 
                options=opciones_criticidad, 
                key="filtro_alerta_criticidad", 
                label_visibility="collapsed"
            )
        with col_f3:
            if st.button("🧹 Limpiar filtro", key="btn_limpiar_alerta", use_container_width=True):
                st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
                st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
                st.rerun()

        # Mostrar estado de actualización
        st.markdown(f"""
            <div style="text-align: right; color: #888; font-size: 12px; padding: 5px 0;">
                🔄 Auto-refresh: 15s | Última actualización: <b>{datetime.now().strftime("%H:%M:%S")}</b>
            </div>
        """, unsafe_allow_html=True)

        # Obtener valores de filtros desde session_state
        filtro_servidor = st.session_state["filtro_alerta_servidor"]
        filtro_criticidad = st.session_state["filtro_alerta_criticidad"]

        # Verificar si se seleccionó un servidor
        if filtro_servidor == VALOR_DEFECTO:
            st.info("🔍 Seleccione un servidor para visualizar sus alertas activas.")
        else:
            serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_servidor), None)
            if not serv_info:
                st.warning("⚠️ Servidor no encontrado en el catálogo.")
            else:
                ip_filtro = serv_info['ip']
                
                # Verificar estado del agente
                agente_activo, ultimo_registro = obtener_estado_agente(ip_filtro)
                
                # Mostrar estado del agente
                if agente_activo:
                    st.markdown(f"""
                        <div style="background-color: #E8F5E9; padding: 10px 16px; border-radius: 6px; border-left: 5px solid #2E7D32; margin-bottom: 15px;">
                            <span style="color: #2E7D32; font-weight: bold; font-size: 15px;">🟢 Agente Activo</span>
                            <span style="color: #555; font-size: 13px; margin-left: 10px;">Datos en tiempo real</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="background-color: #FFF5F5; padding: 10px 16px; border-radius: 6px; border-left: 5px solid #C62828; margin-bottom: 15px;">
                            <span style="color: #C62828; font-weight: bold; font-size: 15px;">🔴 Agente Inactivo</span>
                            <span style="color: #555; font-size: 13px; margin-left: 10px;">Mostrando últimos datos registrados</span>
                            {f'<span style="color: #888; font-size: 12px; margin-left: 10px;">| 📅 {ultimo_registro.get("fecha_registro", datetime.now()).strftime("%Y-%m-%d %H:%M:%S") if ultimo_registro else ""}</span>' if ultimo_registro else ''}
                        </div>
                    """, unsafe_allow_html=True)
                
                # Obtener alertas activas
                alertas_activas = obtener_alertas_activas(ip_filtro, filtro_criticidad)
                
                # Contador de alertas
                color_contador = "#C62828" if len(alertas_activas) > 0 else "#2E7D32"
                st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 8px 16px; border-radius: 6px; border: 1px solid #E0E0E0; margin-bottom: 15px; display: inline-block;">
                        <span style="color: #333333; font-weight: bold; font-size: 15px;">🔔 Alertas activas:</span>
                        <span style="color: {color_contador}; font-weight: bold; font-size: 18px; margin-left: 8px;">{len(alertas_activas)}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                if not alertas_activas:
                    st.success("✅ No hay alertas activas para este servidor. Todos los componentes están operativos.")
                else:
                    for alerta in alertas_activas:
                        html_card = renderizar_alerta_card(alerta, agente_activo)
                        st.markdown(html_card, unsafe_allow_html=True)
                
                # Auto-refresh cada 15 segundos (como en monitoreo.py)
                st.session_state["ultima_actualizacion"] = datetime.now()
                time.sleep(15)
                st.rerun()

    # =====================================================================
    # PESTAÑA 2: CONFIGURACIÓN DE UMBRALES - CON FILTROS ESTILO MONITOREO.PY
    # =====================================================================
    with tab2:
        st.markdown('<h4 style="color:#003366; font-size:16px; font-weight:bold;">⚙️ CONFIGURACIÓN DE UMBRALES POR SERVIDOR</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Configure los umbrales de alerta para cada componente (valores en %)</p>', unsafe_allow_html=True)
        
        # FILTROS - IGUAL QUE MONITOREO.PY
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            st.selectbox(
                "Seleccionar Servidor", 
                options=opciones_servidores, 
                key="filtro_umbral_servidor", 
                on_change=callback_cambio_filtro_umbral,
                label_visibility="collapsed"
            )
        with col_u2:
            if st.button("🧹 Limpiar", key="btn_limpiar_umbral", use_container_width=True):
                st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
                st.rerun()

        # Obtener valor del filtro desde session_state
        filtro_umbral_servidor = st.session_state["filtro_umbral_servidor"]

        if filtro_umbral_servidor == VALOR_DEFECTO:
            st.info("🔍 Seleccione un servidor para configurar sus umbrales.")
        else:
            serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_umbral_servidor), None)
            if not serv_info:
                st.warning("⚠️ Servidor no encontrado en el catálogo.")
            else:
                ip_servidor = serv_info['ip']
                umbrales_actuales = obtener_ultimos_umbrales(ip_servidor)
                
                # Valores por defecto
                valores = {
                    "cpu_buen_estado": 69, "cpu_advertencia": 70, "cpu_critico": 85,
                    "cpu_p_buen_estado": 69, "cpu_p_advertencia": 70, "cpu_p_critico": 85,
                    "ram_buen_estado": 20, "ram_advertencia": 15, "ram_critico": 10,
                }
                for i in range(1, 7):
                    valores[f"disco_{i}_buen_estado"] = 25
                    valores[f"disco_{i}_advertencia"] = 15
                    valores[f"disco_{i}_critico"] = 5
                valores["red_limite_total_mbps"] = 100
                valores["red_limite_entrante_mbps"] = 50
                valores["red_limite_saliente_mbps"] = 50
                valores["latencia_limite_ms"] = 150
                valores["perdida_limite_pct"] = 1
                
                if umbrales_actuales:
                    for k in valores.keys():
                        if k in umbrales_actuales and umbrales_actuales[k] is not None:
                            valores[k] = umbrales_actuales[k]
                
                st.markdown(f"""
                    <div style="background-color: #F0F4F8; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #003366;">
                        <p style="margin: 0; font-weight: bold; color: #003366; font-size: 16px;">🖥️ {serv_info['nombre_alias']} ({ip_servidor})</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # =============================================================
                # CPU GLOBAL
                # =============================================================
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:5px;">🧠 CPU - Procesamiento Global</p>', unsafe_allow_html=True)
                col_cpu_est, col_cpu_adv, col_cpu_crit = st.columns(3)
                with col_cpu_est:
                    st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_buen_estado"]), key="cpu_buen_estado", label_visibility="collapsed")
                with col_cpu_adv:
                    st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCIÓN</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_advertencia"]), key="cpu_advertencia", label_visibility="collapsed")
                with col_cpu_crit:
                    st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRÍTICO</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_critico"]), key="cpu_critico", label_visibility="collapsed")
                
                # =============================================================
                # CPU CORES
                # =============================================================
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🎛️ CPU - Núcleos (Cores)</p>', unsafe_allow_html=True)
                col_cp_est, col_cp_adv, col_cp_crit = st.columns(3)
                with col_cp_est:
                    st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_p_buen_estado"]), key="cpu_p_buen_estado", label_visibility="collapsed")
                with col_cp_adv:
                    st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCIÓN</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_p_advertencia"]), key="cpu_p_advertencia", label_visibility="collapsed")
                with col_cp_crit:
                    st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRÍTICO</p>', unsafe_allow_html=True)
                    st.number_input("Uso máximo %", min_value=0, max_value=100, value=int(valores["cpu_p_critico"]), key="cpu_p_critico", label_visibility="collapsed")
                
                # =============================================================
                # RAM
                # =============================================================
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🗲 RAM - Memoria (Espacio Libre)</p>', unsafe_allow_html=True)
                col_ram_est, col_ram_adv, col_ram_crit = st.columns(3)
                with col_ram_est:
                    st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                    st.number_input("Mínimo % libre", min_value=0, max_value=100, value=int(valores["ram_buen_estado"]), key="ram_buen_estado", label_visibility="collapsed")
                with col_ram_adv:
                    st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCIÓN</p>', unsafe_allow_html=True)
                    st.number_input("Mínimo % libre", min_value=0, max_value=100, value=int(valores["ram_advertencia"]), key="ram_advertencia", label_visibility="collapsed")
                with col_ram_crit:
                    st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRÍTICO</p>', unsafe_allow_html=True)
                    st.number_input("Mínimo % libre", min_value=0, max_value=100, value=int(valores["ram_critico"]), key="ram_critico", label_visibility="collapsed")
                
                # =============================================================
                # DISCOS
                # =============================================================
                discos_activos = []
                letras_unidades = {1: "C:", 2: "D:", 3: "E:", 4: "F:", 5: "G:", 6: "Y:"}
                for d in range(1, 7):
                    if int(serv_info.get(f'id_sensor_disco_{d}') or 0) > 0:
                        letra = serv_info.get(f'letra_disco_{d}') or letras_unidades[d]
                        discos_activos.append({'num': d, 'letra': letra})
                
                if discos_activos:
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">💾 Discos (Espacio Libre)</p>', unsafe_allow_html=True)
                    for disco in discos_activos:
                        d_num = disco['num']
                        st.markdown(f'<p style="font-weight:bold; font-size:14px; color:#555; margin-top:10px;">Disco {disco["letra"]}</p>', unsafe_allow_html=True)
                        col_d_est, col_d_adv, col_d_crit = st.columns(3)
                        with col_d_est:
                            st.markdown('<p style="color:#2E7D32; font-size:12px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                            st.number_input(f"Mínimo % libre", min_value=0, max_value=100, value=int(valores[f"disco_{d_num}_buen_estado"]), key=f"disco_{d_num}_buen_estado", label_visibility="collapsed")
                        with col_d_adv:
                            st.markdown('<p style="color:#F57F17; font-size:12px; margin-bottom:2px;">🟡 PRECAUCIÓN</p>', unsafe_allow_html=True)
                            st.number_input(f"Mínimo % libre", min_value=0, max_value=100, value=int(valores[f"disco_{d_num}_advertencia"]), key=f"disco_{d_num}_advertencia", label_visibility="collapsed")
                        with col_d_crit:
                            st.markdown('<p style="color:#C62828; font-size:12px; margin-bottom:2px;">🔴 CRÍTICO</p>', unsafe_allow_html=True)
                            st.number_input(f"Mínimo % libre", min_value=0, max_value=100, value=int(valores[f"disco_{d_num}_critico"]), key=f"disco_{d_num}_critico", label_visibility="collapsed")
                else:
                    st.info("📭 No hay discos configurados para este servidor.")
                
                # =============================================================
                # RED Y LATENCIA
                # =============================================================
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🌐 Red y Latencia</p>', unsafe_allow_html=True)
                col_red1, col_red2 = st.columns(2)
                with col_red1:
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:14px;">🌐 Red</p>', unsafe_allow_html=True)
                    st.number_input("Total (Mbps)", min_value=0, max_value=1000, value=int(valores["red_limite_total_mbps"]), key="red_limite_total_mbps")
                    st.number_input("Entrante (Mbps)", min_value=0, max_value=1000, value=int(valores["red_limite_entrante_mbps"]), key="red_limite_entrante_mbps")
                    st.number_input("Saliente (Mbps)", min_value=0, max_value=1000, value=int(valores["red_limite_saliente_mbps"]), key="red_limite_saliente_mbps")
                with col_red2:
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:14px;">⏱️ Latencia</p>', unsafe_allow_html=True)
                    st.number_input("Límite (ms)", min_value=0, max_value=500, value=int(valores["latencia_limite_ms"]), key="latencia_limite_ms")
                    st.number_input("Pérdida de Paquetes (%)", min_value=0, max_value=100, value=int(valores["perdida_limite_pct"]), key="perdida_limite_pct")
                
                # =============================================================
                # JUSTIFICACIÓN Y GUARDAR
                # =============================================================
                st.markdown("---")
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:15px;">📝 Justificación del Cambio</p>', unsafe_allow_html=True)
                justificacion = st.text_area(
                    "Justificación (requerido para auditoría):",
                    placeholder="Ej: Ajuste de umbrales por incremento de capacidad transaccional...",
                    key="justificacion_umbrales",
                    height=80
                )
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    if st.button("💾 GUARDAR CONFIGURACIÓN", use_container_width=True):
                        if not justificacion.strip():
                            st.warning("⚠️ Debe ingresar una justificación para guardar los cambios.")
                        else:
                            dict_umbrales = {
                                "cpu_buen_estado": st.session_state["cpu_buen_estado"],
                                "cpu_advertencia": st.session_state["cpu_advertencia"],
                                "cpu_critico": st.session_state["cpu_critico"],
                                "cpu_p_buen_estado": st.session_state["cpu_p_buen_estado"],
                                "cpu_p_advertencia": st.session_state["cpu_p_advertencia"],
                                "cpu_p_critico": st.session_state["cpu_p_critico"],
                                "ram_buen_estado": st.session_state["ram_buen_estado"],
                                "ram_advertencia": st.session_state["ram_advertencia"],
                                "ram_critico": st.session_state["ram_critico"],
                                "red_limite_total_mbps": st.session_state["red_limite_total_mbps"],
                                "red_limite_entrante_mbps": st.session_state["red_limite_entrante_mbps"],
                                "red_limite_saliente_mbps": st.session_state["red_limite_saliente_mbps"],
                                "latencia_limite_ms": st.session_state["latencia_limite_ms"],
                                "perdida_limite_pct": st.session_state["perdida_limite_pct"],
                            }
                            for d in range(1, 7):
                                dict_umbrales[f"disco_{d}_buen_estado"] = st.session_state.get(f"disco_{d}_buen_estado", 25)
                                dict_umbrales[f"disco_{d}_advertencia"] = st.session_state.get(f"disco_{d}_advertencia", 15)
                                dict_umbrales[f"disco_{d}_critico"] = st.session_state.get(f"disco_{d}_critico", 5)
                            
                            if guardar_nuevos_umbrales(ip_servidor, dict_umbrales, usuario_id, justificacion):
                                st.success("✅ Umbrales actualizados correctamente.")
                                st.rerun()
                            else:
                                st.error("❌ Error al guardar los umbrales.")

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("cargo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)