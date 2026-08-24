import streamlit as st
import logging
import time
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# FUNCIONES PARA CONSULTAR Y GESTIONAR UMBRALES
# =====================================================================

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

def obtener_historico_umbrales(ip_servidor=None, limite=150):
    """Obtiene el historial de umbrales con filtro opcional por servidor"""
    conn = conectar_bd()
    registros = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            if ip_servidor and ip_servidor != "-- Todos los Servidores --" and ip_servidor != "-- Seleccione un Servidor --":
                serv_info = next((s for s in obtener_lista_servidores() if s['nombre_alias'] == ip_servidor), None)
                if serv_info:
                    query = """
                        SELECT h.*, s.nombre_alias 
                        FROM historico_umbrales h
                        LEFT JOIN servidores s ON h.ip_servidor = s.ip
                        WHERE h.ip_servidor = %s
                        ORDER BY h.id_historico DESC 
                        LIMIT %s
                    """
                    cursor.execute(query, (serv_info['ip'], limite))
                else:
                    query = """
                        SELECT h.*, s.nombre_alias 
                        FROM historico_umbrales h
                        LEFT JOIN servidores s ON h.ip_servidor = s.ip
                        ORDER BY h.id_historico DESC 
                        LIMIT %s
                    """
                    cursor.execute(query, (limite,))
            else:
                query = """
                    SELECT h.*, s.nombre_alias 
                    FROM historico_umbrales h
                    LEFT JOIN servidores s ON h.ip_servidor = s.ip
                    ORDER BY h.id_historico DESC 
                    LIMIT %s
                """
                cursor.execute(query, (limite,))
            
            registros = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo historico umbrales: {e}")
    return registros

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

def obtener_opciones_umbrales(servidor_seleccionado, servidores):
    """Retorna las opciones de umbrales disponibles según el servidor seleccionado"""
    opciones = ["-- Seleccione un Umbral --"]
    
    if not servidor_seleccionado or servidor_seleccionado == "-- Seleccione un Servidor --":
        return opciones
    
    serv_info = next((s for s in servidores if s['nombre_alias'] == servidor_seleccionado), None)
    if not serv_info:
        return opciones
    
    tiene_cpu = int(serv_info.get('id_sensor_cpu') or 0) > 0
    tiene_ram = int(serv_info.get('id_sensor_ram') or 0) > 0
    
    if tiene_cpu or tiene_ram:
        opciones.append("-- Todos los Umbrales --")
    
    if tiene_cpu:
        opciones.append("🧠 CPU")
        opciones.append("🎛️ CPU Cores")
    
    if tiene_ram:
        opciones.append("🗲 RAM")
    
    letras = {1: 'C', 2: 'D', 3: 'E', 4: 'F', 5: 'G', 6: 'Y'}
    for d in range(1, 7):
        if int(serv_info.get(f'id_sensor_disco_{d}') or 0) > 0:
            opciones.append(f"💾 Disco {letras[d]}")
    
    if (int(serv_info.get('id_sensor_red_total') or 0) > 0 or
        int(serv_info.get('id_sensor_red_entrante') or 0) > 0 or
        int(serv_info.get('id_sensor_red_saliente') or 0) > 0):
        opciones.append("🌐 Red")
    
    if int(serv_info.get('id_sensor_latencia') or 0) > 0:
        opciones.append("⏱️ Latencia")
    
    return opciones

def renderizar_tabla_historico_umbrales(filtro_servidor, filtro_umbral, servidores):
    """Renderiza la tabla de histórico con filtros de servidor y umbral"""
    
    registros = obtener_historico_umbrales(filtro_servidor, limite=150)
    
    if not registros:
        st.warning(f"🚫 No hay registros de umbrales para '{filtro_servidor}'.")
        return
    
    serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_servidor), None)
    
    mapa_columnas = {
        "id_historico": "ID",
        "ip_servidor": "IP SERVIDOR",
        "nombre_alias": "SERVIDOR",
        "usuario_id": "USUARIO ID",
        "fecha_change": "FECHA CAMBIO",
        "cpu_buen_estado": "CPU ESTABLE",
        "cpu_advertencia": "CPU PRECAUCION",
        "cpu_critico": "CPU CRITICO",
        "cpu_p_buen_estado": "CPU CORE ESTABLE",
        "cpu_p_advertencia": "CPU CORE PRECAUCION",
        "cpu_p_critico": "CPU CORE CRITICO",
        "ram_buen_estado": "RAM ESTABLE (%)",
        "ram_advertencia": "RAM PRECAUCION (%)",
        "ram_critico": "RAM CRITICO (%)",
        "disco_1_buen_estado": "DISCO C ESTABLE",
        "disco_1_advertencia": "DISCO C PRECAUCION",
        "disco_1_critico": "DISCO C CRITICO",
        "disco_2_buen_estado": "DISCO D ESTABLE",
        "disco_2_advertencia": "DISCO D PRECAUCION",
        "disco_2_critico": "DISCO D CRITICO",
        "disco_3_buen_estado": "DISCO E ESTABLE",
        "disco_3_advertencia": "DISCO E PRECAUCION",
        "disco_3_critico": "DISCO E CRITICO",
        "disco_4_buen_estado": "DISCO F ESTABLE",
        "disco_4_advertencia": "DISCO F PRECAUCION",
        "disco_4_critico": "DISCO F CRITICO",
        "disco_5_buen_estado": "DISCO G ESTABLE",
        "disco_5_advertencia": "DISCO G PRECAUCION",
        "disco_5_critico": "DISCO G CRITICO",
        "disco_6_buen_estado": "DISCO Y ESTABLE",
        "disco_6_advertencia": "DISCO Y PRECAUCION",
        "disco_6_critico": "DISCO Y CRITICO",
        "red_limite_total_mbps": "RED TOTAL (Mbps)",
        "red_limite_entrante_mbps": "RED ENTRANTE (Mbps)",
        "red_limite_saliente_mbps": "RED SALIENTE (Mbps)",
        "latencia_limite_ms": "LATENCIA LIMITE (ms)",
        "perdida_limite_pct": "PERDIDA PAQUETES (%)",
        "justificacion": "JUSTIFICACION"
    }
    
    columnas_base = ["fecha_change", "nombre_alias"]
    columnas_umbral = []
    
    if filtro_umbral == "-- Todos los Umbrales --":
        if serv_info:
            if int(serv_info.get('id_sensor_cpu') or 0) > 0:
                columnas_umbral.extend(["cpu_buen_estado", "cpu_advertencia", "cpu_critico"])
                columnas_umbral.extend(["cpu_p_buen_estado", "cpu_p_advertencia", "cpu_p_critico"])
            if int(serv_info.get('id_sensor_ram') or 0) > 0:
                columnas_umbral.extend(["ram_buen_estado", "ram_advertencia", "ram_critico"])
            for d in range(1, 7):
                if int(serv_info.get(f'id_sensor_disco_{d}') or 0) > 0:
                    columnas_umbral.extend([f"disco_{d}_buen_estado", f"disco_{d}_advertencia", f"disco_{d}_critico"])
            columnas_umbral.extend(["red_limite_total_mbps", "red_limite_entrante_mbps", "red_limite_saliente_mbps"])
            columnas_umbral.extend(["latencia_limite_ms", "perdida_limite_pct"])
    
    elif filtro_umbral == "🧠 CPU":
        columnas_umbral = ["cpu_buen_estado", "cpu_advertencia", "cpu_critico"]
    
    elif filtro_umbral == "🎛️ CPU Cores":
        columnas_umbral = ["cpu_p_buen_estado", "cpu_p_advertencia", "cpu_p_critico"]
    
    elif filtro_umbral == "🗲 RAM":
        columnas_umbral = ["ram_buen_estado", "ram_advertencia", "ram_critico"]
    
    elif filtro_umbral.startswith("💾 Disco"):
        letra = filtro_umbral.replace("💾 Disco ", "")
        discos_map = {'C': '1', 'D': '2', 'E': '3', 'F': '4', 'G': '5', 'Y': '6'}
        d_num = discos_map.get(letra)
        if d_num:
            columnas_umbral = [f"disco_{d_num}_buen_estado", f"disco_{d_num}_advertencia", f"disco_{d_num}_critico"]
    
    elif filtro_umbral == "🌐 Red":
        columnas_umbral = ["red_limite_total_mbps", "red_limite_entrante_mbps", "red_limite_saliente_mbps"]
    
    elif filtro_umbral == "⏱️ Latencia":
        columnas_umbral = ["latencia_limite_ms", "perdida_limite_pct"]
    
    if not columnas_umbral:
        columnas_umbral = ["cpu_critico", "ram_critico"]
    
    columnas_final = columnas_base + columnas_umbral + ["justificacion"]
    
    html_tabla = """<div style="overflow: auto; max-height: 480px; width: 100%; border: 1px solid #d1d8e0; border-radius: 4px;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', sans-serif; font-size: 12px; background-color: white;">
        <thead><tr>"""
    
    for col in columnas_final:
        html_tabla += f'<th style="position: sticky; top: 0; background-color: #002244; padding: 11px 14px; color: #ffffff; text-align: left; font-weight: 600; font-size: 11px; white-space: nowrap; z-index: 10; border-bottom: 2px solid #001122;">{mapa_columnas.get(col, col.upper())}</th>'
    
    html_tabla += "</tr></thead><tbody>"
    
    for idx, fila in enumerate(registros):
        bg = "#ffffff" if idx % 2 == 0 else "#fcfdfe"
        html_tabla += f'<tr style="background-color: {bg}; border-bottom: 1px solid #ebf0f5;">'
        
        for col in columnas_final:
            val = fila.get(col)
            
            if col == "nombre_alias" and not val:
                val = fila.get("ip_servidor", "-")
            
            try:
                if val is not None and isinstance(val, (int, float)):
                    txt = f"{float(val):.2f}" if "pct" in col or "gb" in col or "red" in col or "latencia" in col else f"{int(val)}"
                else:
                    txt = val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(val, "strftime") else str(val if val is not None else "-")
            except (ValueError, TypeError):
                txt = "-"
            
            align_style = 'text-align: left;'
            if val is not None and isinstance(val, (int, float)):
                align_style = 'text-align: right; font-family: monospace;'
            elif col == "nombre_alias":
                align_style = 'text-align: left; font-weight: bold; color: #003366;'
            
            html_tabla += f'<td style="padding: 9px 14px; color: #333333; white-space: nowrap; {align_style}">{txt}</td>'
        
        html_tabla += "</tr>"
    
    html_tabla += "</tbody></table></div>"
    
    st.markdown(html_tabla, unsafe_allow_html=True)
    st.caption(f"📊 Mostrando {len(registros)} registros - Umbral: {filtro_umbral}")


# =====================================================================
# 🔥 VISTA PRINCIPAL - SOLO ELIMINA time.sleep(1)
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    
    # =============================================================
    # LIMPIEZA AL ENTRAR AL MÓDULO
    # =============================================================
    if st.session_state.get("_seccion_anterior") != "⚙️ Umbrales":
        st.session_state["filtro_umbral_servidor"] = "-- Seleccione un Servidor --"
        st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"
        st.session_state["filtro_historico_servidor"] = "-- Seleccione un Servidor --"
        st.session_state["filtro_historico_umbral"] = "-- Seleccione un Umbral --"
        st.session_state["umbrales_modificados"] = False
        st.session_state["aplicar_filtro_config"] = False
        st.session_state["aplicar_filtro_historico"] = False
        if "_limpiar_config" in st.query_params:
            del st.query_params["_limpiar_config"]
        if "_limpiar_historico" in st.query_params:
            del st.query_params["_limpiar_historico"]
    
    st.markdown("""
        <style>
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
            .info-analista-umbrales {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-umbrales span {
                color: #003366;
                font-weight: 700;
            }
            div[data-testid="stTabs"] {
                margin-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">⚙️ Configuración de Umbrales</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-umbrales">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    servidores = obtener_lista_servidores()
    
    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_COMP_DEFECTO = "-- Seleccione un Componente --"
    VALOR_UMBRAL_DEFECTO = "-- Seleccione un Umbral --"

    if "filtro_umbral_servidor" not in st.session_state:
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
    if "filtro_umbral_componente" not in st.session_state:
        st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO
    if "umbrales_modificados" not in st.session_state:
        st.session_state["umbrales_modificados"] = False
    if "aplicar_filtro_config" not in st.session_state:
        st.session_state["aplicar_filtro_config"] = False
    if "config_servidor_seleccionado" not in st.session_state:
        st.session_state["config_servidor_seleccionado"] = VALOR_DEFECTO
    if "config_componente_seleccionado" not in st.session_state:
        st.session_state["config_componente_seleccionado"] = VALOR_COMP_DEFECTO
    
    if "filtro_historico_servidor" not in st.session_state:
        st.session_state["filtro_historico_servidor"] = VALOR_DEFECTO
    if "filtro_historico_umbral" not in st.session_state:
        st.session_state["filtro_historico_umbral"] = VALOR_UMBRAL_DEFECTO
    if "aplicar_filtro_historico" not in st.session_state:
        st.session_state["aplicar_filtro_historico"] = False
    if "historico_servidor_seleccionado" not in st.session_state:
        st.session_state["historico_servidor_seleccionado"] = VALOR_DEFECTO
    if "historico_umbral_seleccionado" not in st.session_state:
        st.session_state["historico_umbral_seleccionado"] = VALOR_UMBRAL_DEFECTO

    if "_limpiar_config" in st.query_params and st.query_params["_limpiar_config"] == "1":
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
        st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO
        st.session_state["umbrales_modificados"] = False
        st.session_state["aplicar_filtro_config"] = False
        st.session_state["config_servidor_seleccionado"] = VALOR_DEFECTO
        st.session_state["config_componente_seleccionado"] = VALOR_COMP_DEFECTO
        del st.query_params["_limpiar_config"]
        st.rerun()
    
    if "_limpiar_historico" in st.query_params and st.query_params["_limpiar_historico"] == "1":
        st.session_state["filtro_historico_servidor"] = VALOR_DEFECTO
        st.session_state["filtro_historico_umbral"] = VALOR_UMBRAL_DEFECTO
        st.session_state["aplicar_filtro_historico"] = False
        st.session_state["historico_servidor_seleccionado"] = VALOR_DEFECTO
        st.session_state["historico_umbral_seleccionado"] = VALOR_UMBRAL_DEFECTO
        del st.query_params["_limpiar_historico"]
        st.rerun()

    tab1, tab2 = st.tabs(
        ["⚙️ Configuración", "📋 Histórico de Umbrales"],
        key="tabs_umbrales"
    )

    with tab1:
        lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
        opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
        
        opciones_componentes = [
            VALOR_COMP_DEFECTO,
            "-- Todos los Componentes --",
            "🧠 CPU",
            "🗲 RAM",
            "💾 Discos"
        ]

        col_u1, col_u2, col_u3, col_u4 = st.columns([2, 2, 1, 1])
        with col_u1:
            st.selectbox(
                "Servidor", 
                options=opciones_servidores, 
                key="filtro_umbral_servidor",
                label_visibility="collapsed"
            )
        with col_u2:
            servidor_seleccionado = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO) != VALOR_DEFECTO
            st.selectbox(
                "Componente", 
                options=opciones_componentes, 
                key="filtro_umbral_componente",
                label_visibility="collapsed",
                disabled=not servidor_seleccionado
            )
        with col_u3:
            if st.button("🔍 Filtrar", key="btn_filtrar_config", use_container_width=True):
                servidor = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO)
                componente = st.session_state.get("filtro_umbral_componente", VALOR_COMP_DEFECTO)
                
                st.session_state["config_servidor_seleccionado"] = servidor
                st.session_state["config_componente_seleccionado"] = componente
                st.session_state["aplicar_filtro_config"] = True
                st.rerun()
        with col_u4:
            if st.button("🧹 Limpiar", key="btn_limpiar_config", use_container_width=True):
                st.query_params["_limpiar_config"] = "1"
                st.rerun()

        if st.session_state.get("aplicar_filtro_config", False):
            filtro_umbral_servidor = st.session_state.get("config_servidor_seleccionado", VALOR_DEFECTO)
            filtro_componente = st.session_state.get("config_componente_seleccionado", VALOR_COMP_DEFECTO)
        else:
            filtro_umbral_servidor = VALOR_DEFECTO
            filtro_componente = VALOR_COMP_DEFECTO

        servidor_seleccionado = filtro_umbral_servidor != VALOR_DEFECTO
        componente_seleccionado = filtro_componente not in [VALOR_COMP_DEFECTO]
        mostrar_todo = filtro_componente == "-- Todos los Componentes --"

        if not servidor_seleccionado:
            if st.session_state.get("aplicar_filtro_config", False):
                st.warning("⚠️ Debe seleccionar un servidor para configurar.")
                st.session_state["aplicar_filtro_config"] = False
                st.rerun()
            else:
                st.info("🔍 Seleccione un servidor y presione 'Filtrar' para comenzar.")
        elif not componente_seleccionado:
            if st.session_state.get("aplicar_filtro_config", False):
                st.warning("⚠️ Debe seleccionar un componente para configurar.")
                st.session_state["aplicar_filtro_config"] = False
                st.rerun()
            else:
                st.info("🎯 Seleccione un componente y presione 'Filtrar' para configurar sus umbrales.")
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
                else:
                    st.caption(f"🔎 Configurando: Servidor: {filtro_umbral_servidor} | Componente: {filtro_componente}")
                    
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
                    
                    if not st.session_state.get("_guardando", False):
                        st.session_state["umbrales_modificados"] = False
                    
                    if tiene_cpu and (mostrar_todo or filtro_componente == "🧠 CPU"):
                        st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:5px;">🧠 CPU - Procesamiento Global</p>', unsafe_allow_html=True)
                        col_cpu_est, col_cpu_adv, col_cpu_crit = st.columns(3)
                        with col_cpu_est:
                            st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_buen_estado", 69)), key="cpu_buen_estado", label_visibility="collapsed")
                            if val != valores.get("cpu_buen_estado", 69):
                                st.session_state["umbrales_modificados"] = True
                        with col_cpu_adv:
                            st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_advertencia", 70)), key="cpu_advertencia", label_visibility="collapsed")
                            if val != valores.get("cpu_advertencia", 70):
                                st.session_state["umbrales_modificados"] = True
                        with col_cpu_crit:
                            st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_critico", 85)), key="cpu_critico", label_visibility="collapsed")
                            if val != valores.get("cpu_critico", 85):
                                st.session_state["umbrales_modificados"] = True
                    
                    if tiene_cpu and (mostrar_todo or filtro_componente == "🧠 CPU"):
                        st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🎛️ CPU - Nucleos (Cores)</p>', unsafe_allow_html=True)
                        col_cp_est, col_cp_adv, col_cp_crit = st.columns(3)
                        with col_cp_est:
                            st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_buen_estado", 69)), key="cpu_p_buen_estado", label_visibility="collapsed")
                            if val != valores.get("cpu_p_buen_estado", 69):
                                st.session_state["umbrales_modificados"] = True
                        with col_cp_adv:
                            st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_advertencia", 70)), key="cpu_p_advertencia", label_visibility="collapsed")
                            if val != valores.get("cpu_p_advertencia", 70):
                                st.session_state["umbrales_modificados"] = True
                        with col_cp_crit:
                            st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                            val = st.number_input("Uso maximo %", min_value=0, max_value=100, value=int(valores.get("cpu_p_critico", 85)), key="cpu_p_critico", label_visibility="collapsed")
                            if val != valores.get("cpu_p_critico", 85):
                                st.session_state["umbrales_modificados"] = True
                    
                    if tiene_ram and (mostrar_todo or filtro_componente == "🗲 RAM"):
                        st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">🗲 RAM - Memoria (Espacio Libre)</p>', unsafe_allow_html=True)
                        col_ram_est, col_ram_adv, col_ram_crit = st.columns(3)
                        with col_ram_est:
                            st.markdown('<p style="color:#2E7D32; font-weight:bold; font-size:14px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                            val = st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_buen_estado", 20)), key="ram_buen_estado", label_visibility="collapsed")
                            if val != valores.get("ram_buen_estado", 20):
                                st.session_state["umbrales_modificados"] = True
                        with col_ram_adv:
                            st.markdown('<p style="color:#F57F17; font-weight:bold; font-size:14px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                            val = st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_advertencia", 15)), key="ram_advertencia", label_visibility="collapsed")
                            if val != valores.get("ram_advertencia", 15):
                                st.session_state["umbrales_modificados"] = True
                        with col_ram_crit:
                            st.markdown('<p style="color:#C62828; font-weight:bold; font-size:14px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                            val = st.number_input("Minimo % libre", min_value=0, max_value=100, value=int(valores.get("ram_critico", 10)), key="ram_critico", label_visibility="collapsed")
                            if val != valores.get("ram_critico", 10):
                                st.session_state["umbrales_modificados"] = True
                    
                    if discos_activos and (mostrar_todo or filtro_componente == "💾 Discos"):
                        st.markdown('<p style="color:#003366; font-weight:bold; font-size:16px; margin-top:20px;">💾 Discos (Espacio Libre)</p>', unsafe_allow_html=True)
                        for disco in discos_activos:
                            d_num = disco['num']
                            st.markdown(f'<p style="font-weight:bold; font-size:14px; color:#555; margin-top:10px;">Disco {disco["letra"]}</p>', unsafe_allow_html=True)
                            col_d_est, col_d_adv, col_d_crit = st.columns(3)
                            with col_d_est:
                                st.markdown('<p style="color:#2E7D32; font-size:12px; margin-bottom:2px;">🟢 ESTABLE</p>', unsafe_allow_html=True)
                                val = st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_buen_estado", 25)), key=f"disco_{d_num}_buen_estado", label_visibility="collapsed")
                                if val != valores.get(f"disco_{d_num}_buen_estado", 25):
                                    st.session_state["umbrales_modificados"] = True
                            with col_d_adv:
                                st.markdown('<p style="color:#F57F17; font-size:12px; margin-bottom:2px;">🟡 PRECAUCION</p>', unsafe_allow_html=True)
                                val = st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_advertencia", 15)), key=f"disco_{d_num}_advertencia", label_visibility="collapsed")
                                if val != valores.get(f"disco_{d_num}_advertencia", 15):
                                    st.session_state["umbrales_modificados"] = True
                            with col_d_crit:
                                st.markdown('<p style="color:#C62828; font-size:12px; margin-bottom:2px;">🔴 CRITICO</p>', unsafe_allow_html=True)
                                val = st.number_input(f"Minimo % libre", min_value=0, max_value=100, value=int(valores.get(f"disco_{d_num}_critico", 5)), key=f"disco_{d_num}_critico", label_visibility="collapsed")
                                if val != valores.get(f"disco_{d_num}_critico", 5):
                                    st.session_state["umbrales_modificados"] = True
                    
                    if not mostrar_todo:
                        componente_mostrar = filtro_componente.replace("🧠 ", "").replace("🗲 ", "").replace("💾 ", "")
                        if not any([
                            (tiene_cpu and filtro_componente == "🧠 CPU"),
                            (tiene_ram and filtro_componente == "🗲 RAM"),
                            (len(discos_activos) > 0 and filtro_componente == "💾 Discos")
                        ]):
                            st.warning(f"⚠️ El servidor no tiene sensores configurados para '{componente_mostrar}'.")
                    
                    st.markdown("---")
                    
                    if st.session_state["umbrales_modificados"]:
                        st.markdown('<p style="color:#003366; font-weight:bold; font-size:15px;">📝 Justificacion del Cambio</p>', unsafe_allow_html=True)
                        justificacion = st.text_area(
                            "Justificacion (requerido para auditoria):",
                            placeholder="Ej: Ajuste de umbrales por incremento de capacidad transaccional...",
                            key="justificacion_umbrales",
                            height=80
                        )
                        
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                        with col_btn2:
                            if st.button("💾 GUARDAR CONFIGURACION", key="btn_guardar_umbrales", use_container_width=True):
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
                                        st.session_state["_guardando"] = True
                                        st.session_state["umbrales_modificados"] = False
                                        # ✅ time.sleep(1) ELIMINADO
                                        st.rerun()
                                    else:
                                        st.error("❌ Error al guardar los umbrales. Verifique los logs.")
                    else:
                        st.info("ℹ️ No hay cambios pendientes. Modifique algún valor para habilitar el guardado.")

    with tab2:
        lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
        opciones_servidores = ["-- Seleccione un Servidor --"] + lista_nombres_bd
        
        servidor_actual = st.session_state.get("filtro_historico_servidor", VALOR_DEFECTO)
        opciones_umbrales = obtener_opciones_umbrales(servidor_actual, servidores)
        
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 1, 1])
        with col_f1:
            st.selectbox(
                "Seleccione un Servidor",
                options=opciones_servidores,
                key="filtro_historico_servidor",
                label_visibility="collapsed"
            )
        with col_f2:
            disabled = servidor_actual == VALOR_DEFECTO
            st.selectbox(
                "Seleccione un Umbral",
                options=opciones_umbrales,
                key="filtro_historico_umbral",
                label_visibility="collapsed",
                disabled=disabled
            )
        with col_f3:
            if st.button("🔍 Filtrar", key="btn_filtrar_historico", use_container_width=True):
                servidor_seleccionado = st.session_state.get("filtro_historico_servidor", VALOR_DEFECTO)
                umbral_seleccionado = st.session_state.get("filtro_historico_umbral", VALOR_UMBRAL_DEFECTO)
                
                st.session_state["historico_servidor_seleccionado"] = servidor_seleccionado
                st.session_state["historico_umbral_seleccionado"] = umbral_seleccionado
                st.session_state["aplicar_filtro_historico"] = True
                st.rerun()
        with col_f4:
            if st.button("🧹 Limpiar", key="btn_limpiar_historico_umbrales", use_container_width=True):
                st.query_params["_limpiar_historico"] = "1"
                st.rerun()
        
        if st.session_state.get("aplicar_filtro_historico", False):
            filtro_servidor = st.session_state.get("historico_servidor_seleccionado", VALOR_DEFECTO)
            filtro_umbral = st.session_state.get("historico_umbral_seleccionado", VALOR_UMBRAL_DEFECTO)
        else:
            filtro_servidor = VALOR_DEFECTO
            filtro_umbral = VALOR_UMBRAL_DEFECTO
        
        if filtro_servidor == VALOR_DEFECTO:
            if st.session_state.get("aplicar_filtro_historico", False):
                st.warning("⚠️ Debe seleccionar un servidor para filtrar.")
                st.session_state["aplicar_filtro_historico"] = False
                st.rerun()
            else:
                st.info("🔍 Seleccione un servidor y presione 'Filtrar' para ver los registros.")
        elif filtro_umbral == VALOR_UMBRAL_DEFECTO:
            if st.session_state.get("aplicar_filtro_historico", False):
                st.warning("⚠️ Debe seleccionar un tipo de umbral para filtrar.")
                st.session_state["aplicar_filtro_historico"] = False
                st.rerun()
            else:
                st.info("🎯 Seleccione un tipo de umbral y presione 'Filtrar' para ver los registros.")
        else:
            renderizar_tabla_historico_umbrales(filtro_servidor, filtro_umbral, servidores)
            st.caption(f"🔎 Filtros aplicados: Servidor: {filtro_servidor} | Umbral: {filtro_umbral}")


if __name__ == "__main__":
    mostrar_pantalla()