import streamlit as st
import traceback
import logging
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# PERSISTENCIA Y CONSULTA DE TELEMETRÍA Y UMBRALES
# =====================================================================

def obtener_ultimo_monitoreo(ip):
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
            cursor.execute(query, (ip,))
            registro = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo último monitoreo para {ip}: {e}")
    return registro

def obtener_umbrales_actuales(ip):
    umbrales = {
        "cpu_buen_estado": 69.0, "cpu_advertencia": 70.0, "cpu_critico": 85.0,
        "ram_buen_estado": 20.0, "ram_advertencia": 15.0, "ram_critico": 10.0,
        "red_limite_mbps": 100.0, "latencia_limite_ms": 150.0
    }
    for i in range(1, 7):
        umbrales[f"disco_{i}_buen_estado"] = 25.0
        umbrales[f"disco_{i}_advertencia"] = 15.0
        umbrales[f"disco_{i}_critico"] = 5.0

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM historico_umbrales 
                WHERE ip_servidor = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            fila = cursor.fetchone()
            if fila:
                for k in umbrales.keys():
                    if k in fila and fila[k] is not None:
                        umbrales[k] = float(fila[k])
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error cargando umbrales desde historico_umbrales: {e}")
    return umbrales

def guardar_nuevos_umbrales(ip, dict_umbrales, usuario_id, justificacion):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        columnas = [
            "ip_servidor", "usuario_id", "cpu_buen_estado", "cpu_advertencia", "cpu_critico",
            "ram_buen_estado", "ram_advertencia", "ram_critico"
        ]
        valores_sql = [
            str(ip).strip(), int(usuario_id),
            int(dict_umbrales["cpu_buen_estado"]), int(dict_umbrales["cpu_advertencia"]), int(dict_umbrales["cpu_critico"]),
            int(dict_umbrales["ram_buen_estado"]), int(dict_umbrales["ram_advertencia"]), int(dict_umbrales["ram_critico"])
        ]
        for i in range(1, 7):
            columnas.extend([f"disco_{i}_buen_estado", f"disco_{i}_advertencia", f"disco_{i}_critico"])
            valores_sql.extend([
                int(dict_umbrales[f"disco_{i}_buen_estado"]),
                int(dict_umbrales[f"disco_{i}_advertencia"]),
                int(dict_umbrales[f"disco_{i}_critico"])
            ])
        columnas.extend(["red_limite_mbps", "latencia_limite_ms", "justificacion", "fecha_change"])
        valores_sql.extend([
            int(dict_umbrales.get("red_limite_mbps", 100)),
            int(dict_umbrales.get("latencia_limite_ms", 150)),
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
        logging.error(f"Error persisting nuevos umbrales: {e}")
        if conn: conn.close()
        return False

# =====================================================================
# AUXILIARES DE RENDERIZADO SEMAFÓRICO
# =====================================================================
def renderizar_barra_estado(titulo, pct_libre, gb_libres, gb_totales, umbral_adv, umbral_crit):
    if pct_libre <= umbral_crit:
        color_fondo = "#FF4B4B"  
        color_texto = "#FFFFFF"
        texto_estado = "CRÍTICO"
        estilo_borde = "border: 1px solid #D32F2F;"
    elif pct_libre <= umbral_adv:
        color_fondo = "#F1C40F"  
        color_texto = "#111111"
        texto_estado = "ADVERTENCIA"
        estilo_borde = "border: 1px solid #D4AC0D;"
    else:
        color_fondo = "#2ECC71"  
        color_texto = "#FFFFFF"
        texto_estado = "NORMAL"
        estilo_borde = "border: 1px solid #27AE60;"

    html_barra = f"""
    <div style="margin-bottom: 15px;">
        <p style="margin: 0px; font-weight: bold; color: #333; font-size: 14px;">{titulo}</p>
        <div style="
            background-color: {color_fondo}; 
            color: {color_texto}; 
            {estilo_borde}
            padding: 10px; 
            border-radius: 5px; 
            text-align: center; 
            font-weight: bold; 
            font-size: 13px;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.08);
            letter-spacing: 0.5px;
        ">
            {texto_estado} ({pct_libre:.1f}% libre - {gb_libres:.1f} GB / {gb_totales:.1f} GB)
        </div>
    </div>
    """
    st.markdown(html_barra, unsafe_allow_html=True)

def renderizar_barra_cpu(titulo, pct_uso, umbral_adv, umbral_crit):
    """
    Renderizador semafórico adaptado al comportamiento del CPU.
    A mayor porcentaje de uso, mayor criticidad (Lógica inversa a RAM/Discos).
    """
    if pct_uso >= umbral_crit:
        color_fondo = "#FF4B4B"  
        color_texto = "#FFFFFF"
        texto_estado = "CRÍTICO"
        estilo_borde = "border: 1px solid #D32F2F;"
    elif pct_uso >= umbral_adv:
        color_fondo = "#F1C40F"  
        color_texto = "#111111"
        texto_estado = "ADVERTENCIA"
        estilo_borde = "border: 1px solid #D4AC0D;"
    else:
        color_fondo = "#2ECC71"  
        color_texto = "#FFFFFF"
        texto_estado = "NORMAL"
        estilo_borde = "border: 1px solid #27AE60;"

    html_barra = f"""
    <div style="margin-bottom: 15px;">
        <p style="margin: 0px; font-weight: bold; color: #333; font-size: 14px;">{titulo}</p>
        <div style="
            background-color: {color_fondo}; 
            color: {color_texto}; 
            {estilo_borde}
            padding: 10px; 
            border-radius: 5px; 
            text-align: center; 
            font-weight: bold; 
            font-size: 13px;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.08);
            letter-spacing: 0.5px;
        ">
            {texto_estado} ({pct_uso:.1f}% Uso de Procesamiento)
        </div>
    </div>
    """
    st.markdown(html_barra, unsafe_allow_html=True)

def renderizar_estado_servicio(nombre_servicio, estado_enum, id_sensor):
    if estado_enum == 'ACTIVO':
        color_fondo = "#E8F8F5"  
        color_texto = "#117A65"  
        estilo_borde = "border: 1px solid #A3E4D7;"
        status_dot = "🟢"
    elif estado_enum == 'OFF':
        color_fondo = "#F2F4F4"  
        color_texto = "#7F8C8D"  
        estilo_borde = "border: 1px solid #D5DBDB;"
        status_dot = "⚪"
    else:
        color_fondo = "#FADBD8"  
        color_texto = "#78281F"  
        estilo_borde = "border: 1px solid #F1948A;"
        status_dot = "🔴"

    html_servicio = f"""
    <div style="
        background-color: {color_fondo}; 
        color: {color_texto}; 
        {estilo_borde}
        padding: 10px 14px; 
        border-radius: 6px; 
        box-shadow: 0px 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="font-size: 10px; opacity: 0.7; font-weight: bold; letter-spacing: 0.3px;">SENSOR #{id_sensor}</div>
        <div style="font-size: 13px; font-weight: bold; margin: 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            {nombre_servicio}
        </div>
        <div style="font-size: 12px; font-weight: bold; margin-top: 1px;">
            {status_dot} {estado_enum}
        </div>
    </div>
    """
    st.markdown(html_servicio, unsafe_allow_html=True)


# =====================================================================
# VISTA PRINCIPAL (MÓDULO DE ALERTAS - SIMPOL V3.9.8)
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    
    st.markdown("""
        <style>
            [data-testid="stHorizontalBlock"] {
                padding-left: 0px !important;
                margin-left: 0px !important;
            }
            .stSlider {
                padding-left: 0px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<h2 style="color:#003366; margin-bottom:0px;">🛡️ Consola Operativa de Alertas y Políticas</h2>'
        f'<p style="color:#555; font-size:14px; margin-top:5px;">'
        f'Gestor de Monitoreo SIMPOL | <b>Analista:</b> {nombre_analista} ({usuario_login})</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    VALOR_DEFECTO_P1 = "-- Seleccione un Servidor para empezar --"
    VALOR_DEFECTO_P2 = "-- Seleccione un Servidor --"

    if "sb_alerta_srv" not in st.session_state:
        st.session_state["sb_alerta_srv"] = VALOR_DEFECTO_P1
    if "sb_conf_umbrales" not in st.session_state:
        st.session_state["sb_conf_umbrales"] = VALOR_DEFECTO_P2

    tab1, tab2 = st.tabs(["🚨 Monitoreo de Alertas (Sensores)", "⚙️ Configuración Avanzada de Umbrales"])

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores_p1 = [VALOR_DEFECTO_P1] + lista_nombres_bd
    opciones_servidores_p2 = [VALOR_DEFECTO_P2] + lista_nombres_bd

    # =====================================================================
    # PESTAÑA 1: INSPECCIÓN VISUAL DE SENSORES Y SERVICIOS
    # =====================================================================
    with tab1:
        st.markdown('<h4 style="color:#003366; font-size:14px; font-weight:bold; margin-top:15px;">SELECCIONE SERVIDOR PARA INSPECCIÓN DE ALERTAS:</h4>', unsafe_allow_html=True)
        
        if not servidores:
            st.info("💡 No hay servidores mapeados en el catálogo central.")
        else:
            col_sel_p1, col_btn_p1 = st.columns([5, 1])
            with col_sel_p1:
                seleccion_srv = st.selectbox(
                    "Selector de Servidores Activos para Monitoreo de Canales", 
                    options=opciones_servidores_p1, 
                    label_visibility="collapsed", 
                    key="sb_alerta_srv"
                )
            with col_btn_p1:
                if st.button("🧹 Limpiar", key="btn_limpiar_p1", use_container_width=True):
                    st.session_state["sb_alerta_srv"] = VALOR_DEFECTO_P1
                    st.rerun()

            if seleccion_srv == VALOR_DEFECTO_P1:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("🔍 Seleccione un nodo de red para evaluar el estado de hardware y servicios en tiempo real.")
            else:
                @st.fragment(run_every=15)
                def renderizar_sensores_tiempo_real(nombre_nodo):
                    st.markdown('<div style="text-align: right; color: #003366; font-size: 11px; font-weight: bold; margin-bottom: -15px;">🔄 Sincronizado con agente.py (Auto-refresh: 15s)</div>', unsafe_allow_html=True)
                    
                    serv_info = next((s for s in servidores if s['nombre_alias'] == nombre_nodo), None)
                    if serv_info:
                        ip_sel = str(serv_info['ip']).strip()
                        telemetria = obtener_ultimo_monitoreo(ip_sel)
                        umbrales = obtener_umbrales_actuales(ip_sel)

                        st.markdown(f'<h3 style="font-size:18px; color:#333; margin-top:20px;">🚦 Estado Actual de los Sensores Indexados <span style="font-size:13px; color:#999;">({datetime.now().strftime("%H:%M:%S")})</span></h3>', unsafe_allow_html=True)
                        st.markdown("---")

                        if not telemetria:
                            st.warning(f"⚠️ No se han recibido muestras recientes desde agente.py para el nodo `{ip_sel}`.")
                        else:
                            # Layout de dos columnas para CPU y RAM
                            tiene_cpu = int(serv_info.get('id_sensor_cpu') or 0) > 0
                            tiene_ram = int(serv_info.get('id_sensor_ram') or 0) > 0
                            
                            if tiene_cpu or tiene_ram:
                                col_cpu, col_ram = st.columns(2)
                                
                                with col_cpu:
                                    if tiene_cpu:
                                        pct_cpu_uso = float(telemetria.get('val_cpu') or 0.0)
                                        renderizar_barra_cpu(
                                            titulo="Carga de Procesamiento (CPU)",
                                            pct_uso=pct_cpu_uso,
                                            umbral_adv=umbrales["cpu_advertencia"],
                                            umbral_crit=umbrales["cpu_critico"]
                                        )
                                    else:
                                        st.caption("No hay sensor de CPU configurado.")
                                        
                                with col_ram:
                                    if tiene_ram:
                                        pct_ram_libre = float(telemetria.get('val_ram_disponible_pct') or 0.0)
                                        gb_ram_libres = float(telemetria.get('val_ram_disponible_gb') or 0.0)
                                        gb_ram_totales = float(telemetria.get('val_ram_total_gb') or 0.0)
                                        
                                        renderizar_barra_estado(
                                            titulo="Memoria Volátil Libre (RAM)",
                                            pct_libre=pct_ram_libre,
                                            gb_libres=gb_ram_libres,
                                            gb_totales=gb_ram_totales,
                                            umbral_adv=umbrales["ram_advertencia"],
                                            umbral_crit=umbrales["ram_critico"]
                                        )
                                    else:
                                        st.caption("No hay sensor de RAM configurado.")

                            # 2. Panel de Discos
                            st.markdown('<h3 style="font-size:17px; color:#003366; margin-top:25px; font-weight:bold;">💾 Unidades de Almacenamiento Estático (Libre)</h3>', unsafe_allow_html=True)
                            
                            discos_activos = []
                            letras_unidades = {1: "C:", 2: "D:", 3: "E:", 4: "F:", 5: "G:", 6: "Y:"}
                            
                            for d in range(1, 7):
                                if int(serv_info.get(f'id_sensor_disco_{d}') or 0) > 0:
                                    letra = serv_info.get(f'letra_disco_{d}') or letras_unidades[d]
                                    discos_activos.append({
                                        'num': d,
                                        'letra': letra,
                                        'pct': float(telemetria.get(f'val_disco_{d}_pct_libre') or 0.0),
                                        'libres': float(telemetria.get(f'val_disco_{d}_libres_gb') or 0.0),
                                        'total': float(telemetria.get(f'val_disco_{d}_total_gb') or 0.0)
                                    })

                            if discos_activos:
                                cols_discos = st.columns(len(discos_activos))
                                for idx, disco in enumerate(discos_activos):
                                    with cols_discos[idx]:
                                        renderizar_barra_estado(
                                            titulo=f"Disco {disco['num']} ({disco['letra']})",
                                            pct_libre=disco['pct'],
                                            gb_libres=disco['libres'],
                                            gb_totales=disco['total'],
                                            umbral_adv=umbrales[f"disco_{disco['num']}_advertencia"],
                                            umbral_crit=umbrales[f"disco_{disco['num']}_critico"]
                                        )
                            else:
                                st.caption("No se detectaron sensores de disco duro mapeados para este servidor.")

                            # 3. Apartado de Servicios
                            st.markdown("---")
                            servicios_registrados = []
                            for s in range(1, 9):
                                id_sensor_srv = int(serv_info.get(f'id_sensor_servicio_{s}') or 0)
                                if id_sensor_srv > 0:
                                    estado_enum = telemetria.get(f'estado_servicio_{s}', 'INACTIVO')
                                    servicios_registrados.append({
                                        "nombre": f"Servicio Integrado {s}",
                                        "estado": estado_enum,
                                        "sensor": id_sensor_srv
                                    })

                            if servicios_registrados:
                                st.markdown('<h3 style="font-size:17px; color:#003366; margin-top:25px; font-weight:bold;">⚙️ Estado de Alerta para Servicios</h3>', unsafe_allow_html=True)
                                cols_servicios = st.columns(len(servicios_registrados))
                                for idx, srv in enumerate(servicios_registrados):
                                    with cols_servicios[idx]:
                                        renderizar_estado_servicio(srv["nombre"], srv["estado"], srv["sensor"])

                renderizar_sensores_tiempo_real(st.session_state["sb_alerta_srv"])

    # =====================================================================
    # PESTAÑA 2: CONFIGURACIÓN AVANZADA DE UMBRALES
    # =====================================================================
    with tab2:
        st.markdown('<h4 style="color:#003366; font-size:14px; font-weight:bold; margin-top:15px;">SELECCIONE SERVIDOR A CONFIGURAR:</h4>', unsafe_allow_html=True)
        
        col_sel_p2, col_btn_p2 = st.columns([5, 1])
        with col_sel_p2:
            serv_seleccionado_conf = st.selectbox(
                "Selector de Servidores para Edición de Umbrales",
                options=opciones_servidores_p2, 
                label_visibility="collapsed",
                key="sb_conf_umbrales"
            )
        with col_btn_p2:
            if st.button("🧹 Limpiar", key="btn_limpiar_p2", use_container_width=True):
                st.session_state["sb_conf_umbrales"] = VALOR_DEFECTO_P2
                st.rerun()

        if serv_seleccionado_conf == VALOR_DEFECTO_P2:
            st.info("💡 Seleccione un nodo de la infraestructura para cargar sus límites transaccionales actuales.")
        else:
            serv_conf_info = next((s for s in servidores if s['nombre_alias'] == serv_seleccionado_conf), None)
            if serv_conf_info:
                ip_conf_sel = str(serv_conf_info['ip']).strip()
                umbrales_vivos = obtener_umbrales_actuales(ip_conf_sel)

                st.markdown(f'<h3 style="font-size:18px; color:#333; margin-top:20px;">⚙️ Matriz de Límites para <span style="color:#003366;">{serv_conf_info["nombre_alias"]}</span></h3>', unsafe_allow_html=True)
                st.markdown("---")

                dict_nuevos_valores = {}
                
                tiene_cpu = int(serv_conf_info.get('id_sensor_cpu') or 0) > 0
                tiene_ram = int(serv_conf_info.get('id_sensor_ram') or 0) > 0
                
                # Renderizar los controles deslizantes
                columnas_hw = st.columns(2)
                
                with columnas_hw[0]:
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:14px; margin-bottom:5px;">🧠 Procesamiento (CPU)</p>', unsafe_allow_html=True)
                    if tiene_cpu:
                        dict_nuevos_valores["cpu_buen_estado"] = st.slider("🟢 Estable (Uso % CPU Máx)", 1, 100, int(umbrales_vivos.get("cpu_buen_estado", 69)), key="p2_cpu_ok")
                        dict_nuevos_valores["cpu_advertencia"] = st.slider("⚠️ Advertencia (Uso % CPU)", 10, 100, int(umbrales_vivos.get("cpu_advertencia", 70)), key="p2_cpu_adv")
                        dict_nuevos_valores["cpu_critico"] = st.slider("🔴 Crítico (Uso % CPU)", 10, 100, int(umbrales_vivos.get("cpu_critico", 85)), key="p2_cpu_crit")
                    else:
                        st.caption("No habilitado en el catálogo para este servidor.")
                        dict_nuevos_valores["cpu_buen_estado"] = int(umbrales_vivos.get("cpu_buen_estado", 69))
                        dict_nuevos_valores["cpu_advertencia"] = int(umbrales_vivos.get("cpu_advertencia", 70))
                        dict_nuevos_valores["cpu_critico"] = int(umbrales_vivos.get("cpu_critico", 85))
                        
                with columnas_hw[1]:
                    st.markdown('<p style="color:#003366; font-weight:bold; font-size:14px; margin-bottom:5px;">🗲 Memoria Volátil (RAM)</p>', unsafe_allow_html=True)
                    if tiene_ram:
                        dict_nuevos_valores["ram_buen_estado"] = st.slider("🟢 Estable (% Disponible Mínimo)", 1, 100, int(umbrales_vivos.get("ram_buen_estado", 20)), key="p2_ram_ok")
                        dict_nuevos_valores["ram_advertencia"] = st.slider("⚠️ Advertencia (% Disponible Mínimo)", 1, 100, int(umbrales_vivos.get("ram_advertencia", 15)), key="p2_ram_adv")
                        dict_nuevos_valores["ram_critico"] = st.slider("🔴 Crítico (% Disponible Mínimo)", 1, 100, int(umbrales_vivos.get("ram_critico", 10)), key="p2_ram_crit")
                    else:
                        st.caption("No habilitado en el catálogo para este servidor.")
                        dict_nuevos_valores["ram_buen_estado"] = int(umbrales_vivos.get("ram_buen_estado", 20))
                        dict_nuevos_valores["ram_advertencia"] = int(umbrales_vivos.get("ram_advertencia", 15))
                        dict_nuevos_valores["ram_critico"] = int(umbrales_vivos.get("ram_critico", 10))

                # 2. CANALES DE ALMACENAMIENTO ESTÁTICO (Discos con las 3 variables)
                discos_configurables = []
                letras_unidades_conf = {1: "C:", 2: "D:", 3: "E:", 4: "F:", 5: "G:", 6: "Y:"}
                
                for d in range(1, 7):
                    if int(serv_conf_info.get(f'id_sensor_disco_{d}') or 0) > 0:
                        letra = serv_conf_info.get(f'letra_disco_{d}') or letras_unidades_conf[d]
                        discos_configurables.append({'num': d, 'letra': letra})

                if discos_configurables:
                    st.markdown('<h3 style="font-size:17px; color:#003366; margin-top:25px; font-weight:bold;">💾 Canales de Almacenamiento Masivo (Discos)</h3>', unsafe_allow_html=True)
                    cols_discos_conf = st.columns(len(discos_configurables))
                    
                    for idx, d_conf in enumerate(discos_configurables):
                        d_num = d_conf['num']
                        with cols_discos_conf[idx]:
                            st.markdown(f'<p style="color:#333; font-weight:bold; font-size:13px; margin-bottom:2px;">Unidad {d_conf["letra"]}</p>', unsafe_allow_html=True)
                            dict_nuevos_valores[f"disco_{d_num}_buen_estado"] = st.slider(f"🟢 Estable (% Libre)", 1, 100, int(umbrales_vivos.get(f"disco_{d_num}_buen_estado", 25)), key=f"p2_ok_{d_num}")
                            dict_nuevos_valores[f"disco_{d_num}_advertencia"] = st.slider(f"⚠️ Advertencia (% Libre)", 1, 100, int(umbrales_vivos.get(f"disco_{d_num}_advertencia", 15)), key=f"p2_adv_{d_num}")
                            dict_nuevos_valores[f"disco_{d_num}_critico"] = st.slider(f"🔴 Crítico (% Libre)", 1, 100, int(umbrales_vivos.get(f"disco_{d_num}_critico", 5)), key=f"p2_crit_{d_num}")

                st.markdown("---")
                
                # 3. AUDITORÍA Y CONFIRMACIÓN
                st.markdown('<p style="color:#003366; font-weight:bold; font-size:14px; margin-bottom:5px;">📝 Validación Operativa de Seguridad</p>', unsafe_allow_html=True)
                txt_justificacion = st.text_area("Justificación del Cambio de Umbrales (Requerido por Control Interno):", placeholder="Ej. Ajuste de capacidad transaccional por cierre de mes bancario...", key="p2_justificacion")
                
                col_submit = st.columns([1, 2, 1])
                with col_submit[1]:
                    btn_salvar = st.button(
                        "💾 ACTUALIZAR POLÍTICAS DE UMBRALES", 
                        key="p2_btn_salvar", 
                        use_container_width=True
                    )
                
                if btn_salvar:
                    if not txt_justificacion.strip():
                        st.warning("⚠️ Operación rechazada: Debe ingresar una justificación válida para la auditoría de sistemas.")
                    else:
                        for k, v in umbrales_vivos.items():
                            if k not in dict_nuevos_valores: 
                                dict_nuevos_valores[k] = v
                                
                        if guardar_nuevos_umbrales(ip_conf_sel, dict_nuevos_valores, usuario_id, txt_justificacion):
                            st.success("🎉 Umbrales actualizados con éxito. Historial relacional firmado.")
                            st.rerun()

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)