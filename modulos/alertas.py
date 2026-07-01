import streamlit as st
import traceback
import logging
import time
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# CALLBACKS NATIVOS
# =====================================================================
def callback_cambio_servidor_tab2():
    st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"


# =====================================================================
# FUNCIONES PARA CONSULTAR Y GESTIONAR ALERTAS EN BD
# =====================================================================

def obtener_alertas_activas(ip_servidor=None, criticidad=None):
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

def obtener_ultimos_umbrales(ip_servidor):
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
            logging.error(f"Error obteniendo ultimos umbrales: {e}")
    return umbrales

def guardar_nuevos_umbrales(ip, dict_umbrales, usuario_id, justificacion):
    conn = conectar_bd()
    if not conn:
        logging.error("No se pudo conectar a la BD para guardar umbrales")
        return False
    
    try:
        cursor = conn.cursor()
        
        columnas = [
            "ip_servidor", "usuario_id",
            "cpu_buen_estado", "cpu_advertencia", "cpu_critico",
            "cpu_p_buen_estado", "cpu_p_advertencia", "cpu_p_critico",
            "ram_buen_estado", "ram_advertencia", "ram_critico"
        ]
        
        valores = [
            str(ip).strip(),
            int(usuario_id),
            int(dict_umbrales.get("cpu_buen_estado", 69)),
            int(dict_umbrales.get("cpu_advertencia", 70)),
            int(dict_umbrales.get("cpu_critico", 85)),
            int(dict_umbrales.get("cpu_p_buen_estado", 69)),
            int(dict_umbrales.get("cpu_p_advertencia", 70)),
            int(dict_umbrales.get("cpu_p_critico", 85)),
            int(dict_umbrales.get("ram_buen_estado", 20)),
            int(dict_umbrales.get("ram_advertencia", 15)),
            int(dict_umbrales.get("ram_critico", 10))
        ]
        
        for i in range(1, 7):
            columnas.extend([
                f"disco_{i}_buen_estado",
                f"disco_{i}_advertencia",
                f"disco_{i}_critico"
            ])
            valores.extend([
                int(dict_umbrales.get(f"disco_{i}_buen_estado", 25)),
                int(dict_umbrales.get(f"disco_{i}_advertencia", 15)),
                int(dict_umbrales.get(f"disco_{i}_critico", 5))
            ])
        
        columnas.extend([
            "red_limite_total_mbps",
            "red_limite_entrante_mbps",
            "red_limite_saliente_mbps",
            "latencia_limite_ms",
            "perdida_limite_pct",
            "justificacion",
            "fecha_change"
        ])
        
        valores.extend([
            int(dict_umbrales.get("red_limite_total_mbps", 100)),
            int(dict_umbrales.get("red_limite_entrante_mbps", 50)),
            int(dict_umbrales.get("red_limite_saliente_mbps", 50)),
            int(dict_umbrales.get("latencia_limite_ms", 150)),
            int(dict_umbrales.get("perdida_limite_pct", 1)),
            str(justificacion).strip(),
            datetime.now()
        ])
        
        if len(columnas) != len(valores):
            logging.error(f"Error: {len(columnas)} columnas vs {len(valores)} valores")
            return False
        
        placeholders = ", ".join(["%s"] * len(columnas))
        query = f"INSERT INTO historico_umbrales ({', '.join(columnas)}) VALUES ({placeholders})"
        
        logging.info(f"Guardando umbrales para {ip}")
        cursor.execute(query, tuple(valores))
        conn.commit()
        
        logging.info(f"Umbrales guardados correctamente para {ip}")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Error guardando nuevos umbrales: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False

# =====================================================================
# FUNCIONES DE RENDERIZADO
# =====================================================================

def renderizar_alerta_card(alerta):
    nivel = alerta.get('tipo_alerta', 'ESTABLE').upper().strip()
    componente = alerta.get('componente', 'Desconocido')
    fecha_inicio = alerta.get('fecha_inicio', datetime.now())
    comentario = alerta.get('comentario', '')
    ip = alerta.get('ip_servidor', '')
    nombre_alias = alerta.get('nombre_alias', ip)
    val_pct = alerta.get('val_disponible_pct_momento', 0)
    val_gb = alerta.get('val_disponible_gb_momento', 0)
    val_total = alerta.get('val_total_gb_momento', 0)
    
    nivel_normalizado = nivel.upper()
    
    if nivel_normalizado in ["CRITICO", "CRITICAL"]:
        color_borde = "#FF4B4B"
        color_fondo = "#FFF5F5"
        color_texto = "#B71C1C"
        icono = "🔴"
        badge_color = "#FF4B4B"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "CRITICO"
    elif nivel_normalizado in ["PRECAUCION", "WARNING", "PRECAUCIÓN"]:
        color_borde = "#F1C40F"
        color_fondo = "#FFFDF5"
        color_texto = "#F57F17"
        icono = "🟡"
        badge_color = "#F1C40F"
        badge_texto = "#1A1A1A"
        nivel_mostrar = "PRECAUCION"
    elif nivel_normalizado == "ACTIVO":
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        icono = "🟢"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "ACTIVO"
    else:
        color_borde = "#2ECC71"
        color_fondo = "#F5FFF8"
        color_texto = "#1B5E20"
        icono = "🟢"
        badge_color = "#2ECC71"
        badge_texto = "#FFFFFF"
        nivel_mostrar = "ESTABLE"
    
    if isinstance(fecha_inicio, datetime):
        fecha_str = fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_str = str(fecha_inicio)
    
    detalles = f"Valor: {val_pct:.1f}%"
    if val_gb > 0 and val_total > 0:
        detalles += f" | Libre: {val_gb:.1f}/{val_total:.1f} GB"
    
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
                <span style="
                    background-color: {badge_color};
                    color: {badge_texto};
                    padding: 4px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
                ">{nivel_mostrar}</span>
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
# PESTAÑA 1: ALERTAS ACTIVAS (ENCAPSULADA EN FRAGMENTO)
# =====================================================================
@st.fragment(run_every=15)
def renderizar_alertas_fragment(filtro_servidor, filtro_criticidad, servidores):
    if filtro_servidor == "-- Seleccione un Servidor --":
        st.info("🔍 Seleccione un servidor para visualizar las alertas.")
        return
    elif filtro_criticidad == "-- Todas --":
        st.info("🎯 Seleccione una criticidad para filtrar las alertas.")
        return
    
    serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_servidor), None)
    if not serv_info:
        st.warning("⚠️ Servidor no encontrado en el catalogo.")
        return
    
    ip_filtro = serv_info['ip']
    alertas_activas = obtener_alertas_activas(ip_filtro, filtro_criticidad)
    
    color_contador = "#C62828" if len(alertas_activas) > 0 else "#2E7D32"
    st.markdown(f"""
        <div style="background-color: #FFFFFF; padding: 8px 16px; border-radius: 6px; border: 1px solid #E0E0E0; margin-bottom: 15px; display: inline-block;">
            <span style="color: #333333; font-weight: bold; font-size: 15px;">🔔 Alertas activas:</span>
            <span style="color: {color_contador}; font-weight: bold; font-size: 18px; margin-left: 8px;">{len(alertas_activas)}</span>
        </div>
    """, unsafe_allow_html=True)
    
    if not alertas_activas:
        st.success("✅ No hay alertas activas para este servidor con la criticidad seleccionada.")
    else:
        for alerta in alertas_activas:
            html_card = renderizar_alerta_card(alerta)
            st.markdown(html_card, unsafe_allow_html=True)
    
    st.session_state["ultima_actualizacion"] = datetime.now()


# =====================================================================
# VISTA PRINCIPAL
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
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
            .info-analista-alertas {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-alertas span {
                color: #003366;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">🛡️ Consola Operativa de Alertas y Politicas</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-alertas">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_TODAS = "-- Todas --"
    VALOR_COMP_DEFECTO = "-- Seleccione un Componente --"

    # INICIALIZAR ESTADOS BASE
    if "filtro_alerta_servidor" not in st.session_state:
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
    if "filtro_alerta_criticidad" not in st.session_state:
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
    if "filtro_umbral_servidor" not in st.session_state:
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
    if "filtro_umbral_componente" not in st.session_state:
        st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO
    if "ultima_actualizacion" not in st.session_state:
        st.session_state["ultima_actualizacion"] = datetime.now()
    if "tab_alertas_index" not in st.session_state:
        st.session_state["tab_alertas_index"] = 0

    # PROCESAR LIMPIEZA DE FILTROS DE LA PESTAÑA 1
    if "_limpiar_alerta" in st.query_params and st.query_params["_limpiar_alerta"] == "1":
        st.session_state["filtro_alerta_servidor"] = VALOR_DEFECTO
        st.session_state["filtro_alerta_criticidad"] = VALOR_TODAS
        del st.query_params["_limpiar_alerta"]
        st.rerun()

    # PROCESAR LIMPIEZA DE FILTROS DE LA PESTAÑA 2
    if "_limpiar_umbral" in st.query_params and st.query_params["_limpiar_umbral"] == "1":
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
        st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO
        del st.query_params["_limpiar_umbral"]
        st.rerun()

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
    opciones_criticidad = [VALOR_TODAS, "CRITICO", "PRECAUCION", "ESTABLE", "ACTIVO"]

    # =====================================================================
    # CONTROL DE PESTAÑA ACTIVA CON SESSION_STATE
    # =====================================================================
    tab_alertas_index = st.session_state.get("tab_alertas_index", 0)

    tab1, tab2 = st.tabs(
        ["🚨 Alertas Activas", "⚙️ Configuracion de Umbrales"],
        key="controlador_pestanas_alertas"
    )

    # =====================================================================
    # PESTAÑA 1: ALERTAS ACTIVAS
    # =====================================================================
    with tab1:
        st.session_state["tab_alertas_index"] = 0
        
        st.markdown('<h4 style="color:#003366; font-size:16px; font-weight:bold;">📋 ALERTAS ACTIVAS EN EL SISTEMA</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Monitoreo en tiempo real de los componentes criticos</p>', unsafe_allow_html=True)
        
        # FILTROS - FUERA DEL FRAGMENTO
        col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
        with col_f1:
            st.selectbox(
                "Filtrar Servidor", 
                options=opciones_servidores, 
                key="filtro_alerta_servidor", 
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
                st.query_params["_limpiar_alerta"] = "1"
                st.session_state["tab_alertas_index"] = 0
                st.rerun()

        # Mostrar hora de ultima actualizacion
        st.markdown(f"""
            <div style="text-align: right; color: #888; font-size: 12px; padding: 5px 0;">
                🔄 Auto-refresh: 15s | Ultima actualizacion: <b>{st.session_state.get("ultima_actualizacion", datetime.now()).strftime("%H:%M:%S")}</b>
            </div>
        """, unsafe_allow_html=True)

        # FRAGMENTO CON AUTO-REFRESH - SOLO los datos de alertas
        renderizar_alertas_fragment(
            st.session_state.get("filtro_alerta_servidor", VALOR_DEFECTO),
            st.session_state.get("filtro_alerta_criticidad", VALOR_TODAS),
            servidores
        )

    # =====================================================================
    # PESTAÑA 2: CONFIGURACION DE UMBRALES (SIN AUTO-REFRESH)
    # =====================================================================
    with tab2:
        st.session_state["tab_alertas_index"] = 1
        
        st.markdown('<h4 style="color:#003366; font-size:16px; font-weight:bold;">⚙️ CONFIGURACION DE UMBRALES POR SERVIDOR</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Seleccione un servidor y el componente a configurar (CPU, RAM o Discos)</p>', unsafe_allow_html=True)
        
        col_u1, col_u2, col_u3 = st.columns([2, 2, 1])
        with col_u1:
            st.selectbox(
                "Servidor", 
                options=opciones_servidores, 
                key="filtro_umbral_servidor",
                on_change=callback_cambio_servidor_tab2,
                label_visibility="collapsed"
            )
        with col_u2:
            opciones_componentes = [
                VALOR_COMP_DEFECTO,
                "-- Todos los Componentes --",
                "🧠 CPU",
                "🗲 RAM",
                "💾 Discos"
            ]
            servidor_seleccionado_tab2 = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO) != VALOR_DEFECTO
            st.selectbox(
                "Componente", 
                options=opciones_componentes, 
                key="filtro_umbral_componente",
                label_visibility="collapsed",
                disabled=not servidor_seleccionado_tab2
            )
        with col_u3:
            if st.button("🧹 Limpiar", key="btn_limpiar_umbral_tab2", use_container_width=True):
                st.query_params["_limpiar_umbral"] = "1"
                st.session_state["tab_alertas_index"] = 1
                st.rerun()

        filtro_umbral_servidor = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO)
        filtro_componente = st.session_state.get("filtro_umbral_componente", VALOR_COMP_DEFECTO)

        servidor_seleccionado = filtro_umbral_servidor != VALOR_DEFECTO
        componente_seleccionado = filtro_componente not in [VALOR_COMP_DEFECTO]
        mostrar_todo = filtro_componente == "-- Todos los Componentes --"

        if not servidor_seleccionado:
            st.info("🔍 Seleccione un servidor para comenzar.")
        elif not componente_seleccionado:
            st.info("🎯 Seleccione un componente para configurar sus umbrales (CPU, RAM o Discos).")
        else:
            serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_umbral_servidor), None)
            if not serv_info:
                st.warning("⚠️ Servidor no encontrado en el catalogo.")
            else:
                ip_servidor = serv_info['ip']
                umbrales_actuales = obtener_ultimos_umbrales(ip_servidor)
                
                tiene_cpu = int(serv_info.get('id_sensor_cpu') or 0) > 0
                tiene_ram = int(serv_info.get('id_sensor_ram') or 0) > 0
                
                discos_activos = []
                letras_unidades = {1: "C:", 2: "D:", 3: "E:", 4: "F:", 5: "G:", 6: "Y:"}
                for d in range(1, 7):
                    if int(serv_info.get(f'id_sensor_disco_{d}') or 0) > 0:
                        letra = serv_info.get(f'letra_disco_{d}') or letras_unidades[d]
                        discos_activos.append({'num': d, 'letra': letra})
                
                tiene_sensores = tiene_cpu or tiene_ram or len(discos_activos) > 0
                
                if not tiene_sensores:
                    st.warning("⚠️ Este servidor no tiene sensores configurados para CPU, RAM o Discos.")
                    st.stop()
                
                valores = {}
                
                if tiene_cpu:
                    valores["cpu_buen_estado"] = 69
                    valores["cpu_advertencia"] = 70
                    valores["cpu_critico"] = 85
                    valores["cpu_p_buen_estado"] = 69
                    valores["cpu_p_advertencia"] = 70
                    valores["cpu_p_critico"] = 85
                
                if tiene_ram:
                    valores["ram_buen_estado"] = 20
                    valores["ram_advertencia"] = 15
                    valores["ram_critico"] = 10
                
                for disco in discos_activos:
                    d_num = disco['num']
                    valores[f"disco_{d_num}_buen_estado"] = 25
                    valores[f"disco_{d_num}_advertencia"] = 15
                    valores[f"disco_{d_num}_critico"] = 5
                
                if umbrales_actuales:
                    for k in valores.keys():
                        if k in umbrales_actuales and umbrales_actuales[k] is not None:
                            valores[k] = umbrales_actuales[k]
                
                if tiene_cpu and (mostrar_todo or filtro_componente == "🧠 CPU"):
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:5px;">🧠 CPU - Procesamiento Global</p>', unsafe_allow_html=True)
                    col_cpu_est, col_cpu_adv, col_cpu_crit = st.columns(3)
                    with col_cpu_est:
                        st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_buen_estado", 69)), key="cpu_buen_estado", label_visibility="collapsed")
                    with col_cpu_adv:
                        st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_advertencia", 70)), key="cpu_advertencia", label_visibility="collapsed")
                    with col_cpu_crit:
                        st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_critico", 85)), key="cpu_critico", label_visibility="collapsed")
                
                if tiene_cpu and (mostrar_todo or filtro_componente == "🧠 CPU"):
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🎛️ CPU - Nucleos (Cores)</p>', unsafe_allow_html=True)
                    col_cp_est, col_cp_adv, col_cp_crit = st.columns(3)
                    with col_cp_est:
                        st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_buen_estado", 69)), key="cpu_p_buen_estado", label_visibility="collapsed")
                    with col_cp_adv:
                        st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_advertencia", 70)), key="cpu_p_advertencia", label_visibility="collapsed")
                    with col_cp_crit:
                        st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                        st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_critico", 85)), key="cpu_p_critico", label_visibility="collapsed")
                
                if tiene_ram and (mostrar_todo or filtro_componente == "🗲 RAM"):
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🗲 RAM - Memoria (Espacio Libre)</p>', unsafe_allow_html=True)
                    col_ram_est, col_ram_adv, col_ram_crit = st.columns(3)
                    with col_ram_est:
                        st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                        st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_buen_estado", 20)), key="ram_buen_estado", label_visibility="collapsed")
                    with col_ram_adv:
                        st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                        st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_advertencia", 15)), key="ram_advertencia", label_visibility="collapsed")
                    with col_ram_crit:
                        st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                        st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_critico", 10)), key="ram_critico", label_visibility="collapsed")
                
                if discos_activos and (mostrar_todo or filtro_componente == "💾 Discos"):
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">💾 Discos (Espacio Libre)</p>', unsafe_allow_html=True)
                    for disco in discos_activos:
                        d_num = disco['num']
                        st.markdown(f'<p style="font-weight:bold; font-size:14px; color:#555; margin-top:10px;">Disco {disco["letra"]}</p>', unsafe_allow_html=True)
                        col_d_est, col_d_adv, col_d_crit = st.columns(3)
                        with col_d_est:
                            st.markdown('<p style="color:#2E7D32; font-size:12px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                            st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_buen_estado", 25)), key=f"disco_{d_num}_buen_estado", label_visibility="collapsed")
                        with col_d_adv:
                            st.markdown('<p style="color:#F57F17; font-size:12px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                            st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_advertencia", 15)), key=f"disco_{d_num}_advertencia", label_visibility="collapsed")
                        with col_d_crit:
                            st.markdown('<p style="color:#C62828; font-size:12px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                            st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_critico", 5)), key=f"disco_{d_num}_critico", label_visibility="collapsed")
                
                if not mostrar_todo:
                    componente_mostrar = filtro_componente.replace("🧠 ", "").replace("🗲 ", "").replace("💾 ", "")
                    if not any([
                        (tiene_cpu and filtro_componente == "🧠 CPU"),
                        (tiene_ram and filtro_componente == "🗲 RAM"),
                        (len(discos_activos) > 0 and filtro_componente == "💾 Discos")
                    ]):
                        st.warning(f"⚠️ El servidor no tiene sensores configurados para '{componente_mostrar}'.")
                
                st.markdown("---")
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:15px;">📝 Justificacion del Cambio</p>', unsafe_allow_html=True)
                justificacion = st.text_area(
                    "Justificacion (requerido para auditoria):",
                    placeholder="Ej: Ajuste de umbrales por incremento de capacidad transaccional...",
                    key="justificacion_umbrales_tab2",
                    height=80
                )
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    if st.button("💾 GUARDAR CONFIGURACION", key="btn_guardar_umbrales_tab2", use_container_width=True):
                        if not justificacion.strip():
                            st.warning("⚠️ Debe ingresar una justificacion para guardar los cambios.")
                        else:
                            dict_umbrales = {}
                            
                            if tiene_cpu:
                                dict_umbrales["cpu_buen_estado"] = st.session_state.get("cpu_buen_estado", 69)
                                dict_umbrales["cpu_advertencia"] = st.session_state.get("cpu_advertencia", 70)
                                dict_umbrales["cpu_critico"] = st.session_state.get("cpu_critico", 85)
                                dict_umbrales["cpu_p_buen_estado"] = st.session_state.get("cpu_p_buen_estado", 69)
                                dict_umbrales["cpu_p_advertencia"] = st.session_state.get("cpu_p_advertencia", 70)
                                dict_umbrales["cpu_p_critico"] = st.session_state.get("cpu_p_critico", 85)
                            
                            if tiene_ram:
                                dict_umbrales["ram_buen_estado"] = st.session_state.get("ram_buen_estado", 20)
                                dict_umbrales["ram_advertencia"] = st.session_state.get("ram_advertencia", 15)
                                dict_umbrales["ram_critico"] = st.session_state.get("ram_critico", 10)
                            
                            for disco in discos_activos:
                                d_num = disco['num']
                                dict_umbrales[f"disco_{d_num}_buen_estado"] = st.session_state.get(f"disco_{d_num}_buen_estado", 25)
                                dict_umbrales[f"disco_{d_num}_advertencia"] = st.session_state.get(f"disco_{d_num}_advertencia", 15)
                                dict_umbrales[f"disco_{d_num}_critico"] = st.session_state.get(f"disco_{d_num}_critico", 5)
                            
                            for i in range(1, 7):
                                if f"disco_{i}_critico" not in dict_umbrales:
                                    dict_umbrales[f"disco_{i}_buen_estado"] = 25
                                    dict_umbrales[f"disco_{i}_advertencia"] = 15
                                    dict_umbrales[f"disco_{i}_critico"] = 5
                            
                            if guardar_nuevos_umbrales(ip_servidor, dict_umbrales, usuario_id, justificacion):
                                st.success("✅ Umbrales actualizados correctamente. El agente detectara el cambio en el proximo ciclo.")
                                st.session_state["tab_alertas_index"] = 1
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Error al guardar los umbrales. Verifique los logs.")

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("cargo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)