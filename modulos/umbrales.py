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
# CALLBACKS
# =====================================================================
def callback_cambio_servidor():
    st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"


# =====================================================================
# VISTA PRINCIPAL
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
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
        </style>
    """, unsafe_allow_html=True)

    # Título
    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">⚙️ Configuración de Umbrales</h2>', unsafe_allow_html=True)
    
    # Mostrar analista
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-umbrales">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown('<p style="color:#666; font-size:13px; margin-top:-5px;">Seleccione un servidor y el componente a configurar (CPU, RAM o Discos)</p>', unsafe_allow_html=True)
    
    VALOR_DEFECTO = "-- Seleccione un Servidor --"
    VALOR_COMP_DEFECTO = "-- Seleccione un Componente --"

    # INICIALIZAR ESTADOS
    if "filtro_umbral_servidor" not in st.session_state:
        st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
    if "filtro_umbral_componente" not in st.session_state:
        st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO

    servidores = obtener_lista_servidores()
    lista_nombres_bd = sorted(list(set([s['nombre_alias'] for s in servidores if s.get('nombre_alias')])))
    opciones_servidores = [VALOR_DEFECTO] + lista_nombres_bd
    
    opciones_componentes = [
        VALOR_COMP_DEFECTO,
        "-- Todos los Componentes --",
        "🧠 CPU",
        "🗲 RAM",
        "💾 Discos"
    ]

    # =============================================================
    # FILA DE FILTROS
    # =============================================================
    col_u1, col_u2, col_u3 = st.columns([2, 2, 1])
    with col_u1:
        st.selectbox(
            "Servidor", 
            options=opciones_servidores, 
            key="filtro_umbral_servidor",
            on_change=callback_cambio_servidor,
            label_visibility="collapsed"
        )
    with col_u2:
        servidor_seleccionado_tab2 = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO) != VALOR_DEFECTO
        st.selectbox(
            "Componente", 
            options=opciones_componentes, 
            key="filtro_umbral_componente",
            label_visibility="collapsed",
            disabled=not servidor_seleccionado_tab2
        )
    with col_u3:
        if st.button("🧹 Limpiar", key="btn_limpiar_umbral", use_container_width=True):
            st.session_state["filtro_umbral_servidor"] = VALOR_DEFECTO
            st.session_state["filtro_umbral_componente"] = VALOR_COMP_DEFECTO
            st.rerun()

    filtro_umbral_servidor = st.session_state.get("filtro_umbral_servidor", VALOR_DEFECTO)
    filtro_componente = st.session_state.get("filtro_umbral_componente", VALOR_COMP_DEFECTO)

    servidor_seleccionado = filtro_umbral_servidor != VALOR_DEFECTO
    componente_seleccionado = filtro_componente not in [VALOR_COMP_DEFECTO]
    mostrar_todo = filtro_componente == "-- Todos los Componentes --"

    if not servidor_seleccionado:
        st.info("🔍 Seleccione un servidor para comenzar.")
        return
    
    if not componente_seleccionado:
        st.info("🎯 Seleccione un componente para configurar sus umbrales (CPU, RAM o Discos).")
        return

    # =============================================================
    # AMBOS FILTROS SELECCIONADOS - MOSTRAR CONFIGURACION
    # =============================================================
    serv_info = next((s for s in servidores if s['nombre_alias'] == filtro_umbral_servidor), None)
    if not serv_info:
        st.warning("⚠️ Servidor no encontrado en el catalogo.")
        return

    ip_servidor = serv_info['ip']
    umbrales_actuales = obtener_ultimos_umbrales(ip_servidor)
    
    # DETECTAR SENSORES ACTIVOS DEL SERVIDOR
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
        return
    
    # =============================================================
    # MOSTRAR INFORMACION DEL SERVIDOR
    # =============================================================
    st.markdown(f"""
        <div style="background-color: #F0F4F8; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #003366;">
            <p style="margin: 0; font-weight: bold; color: #003366; font-size: 16px;">
                🖥️ {serv_info['nombre_alias']} ({ip_servidor})
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # =============================================================
    # VALORES POR DEFECTO
    # =============================================================
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
    
    # =============================================================
    # RENDERIZAR CONTROLES SEGUN FILTRO
    # =============================================================
    
    # CPU GLOBAL
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
    
    # CPU CORES
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
    
    # RAM
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
    
    # DISCOS
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
    
    # MENSAJE SI EL FILTRO NO MUESTRA NADA
    if not mostrar_todo:
        componente_mostrar = filtro_componente.replace("🧠 ", "").replace("🗲 ", "").replace("💾 ", "")
        if not any([
            (tiene_cpu and filtro_componente == "🧠 CPU"),
            (tiene_ram and filtro_componente == "🗲 RAM"),
            (len(discos_activos) > 0 and filtro_componente == "💾 Discos")
        ]):
            st.warning(f"⚠️ El servidor no tiene sensores configurados para '{componente_mostrar}'.")
    
    # =============================================================
    # JUSTIFICACION Y GUARDAR
    # =============================================================
    st.markdown("---")
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
                
                # Discos no activos - valores por defecto
                for i in range(1, 7):
                    if f"disco_{i}_critico" not in dict_umbrales:
                        dict_umbrales[f"disco_{i}_buen_estado"] = 25
                        dict_umbrales[f"disco_{i}_advertencia"] = 15
                        dict_umbrales[f"disco_{i}_critico"] = 5
                
                if guardar_nuevos_umbrales(ip_servidor, dict_umbrales, usuario_id, justificacion):
                    st.success("✅ Umbrales actualizados correctamente. El agente detectara el cambio en el proximo ciclo.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Error al guardar los umbrales. Verifique los logs.")


if __name__ == "__main__":
    mostrar_pantalla()