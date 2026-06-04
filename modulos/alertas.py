import streamlit as st
import traceback
from datetime import datetime
from database import obtener_lista_servidores, conectar_bd
from utils import obtener_telemetria_total

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
        except Exception:
            pass
    return registro

def obtener_umbrales_actuales(ip):
    # Umbrales por defecto expresados en PORCENTAJE (%)
    umbrales = {
        "ram_advertencia": 15.0, "ram_critico": 10.0,
        "cpu_advertencia": 70.0, "cpu_critico": 85.0
    }
    for i in range(1, 7):
        umbrales[f"disco_{i}_advertencia"] = 25.0  # Menor o igual a 25% libre -> Amarillo
        umbrales[f"disco_{i}_critico"] = 5.0      # Menor o igual a 5% libre  -> Rojo

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
            res = cursor.fetchone()
            if res:
                for k, v in res.items():
                    if v is not None:
                        try:
                            umbrales[k] = float(v)
                        except ValueError:
                            umbrales[k] = v
            cursor.close()
            conn.close()
        except Exception:
            pass 
    return umbrales

def guardar_nuevos_umbrales(ip, datos_umbrales, usuario_id):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_umbrales (
                    ip_servidor, cpu_advertencia, cpu_critico, 
                    ram_advertencia, ram_critico,
                    disco_1_advertencia, disco_1_critico, disco_2_advertencia, disco_2_critico,
                    disco_3_advertencia, disco_3_critico, disco_4_advertencia, disco_4_critico,
                    disco_5_advertencia, disco_5_critico, disco_6_advertencia, disco_6_critico,
                    justificacion, usuario_id, fecha_change
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """
            params = (
                ip, 
                int(datos_umbrales.get("cpu_advertencia", 70.0)), int(datos_umbrales.get("cpu_critico", 85.0)),
                int(datos_umbrales.get("ram_advertencia", 15.0)), int(datos_umbrales.get("ram_critico", 10.0)),
                int(datos_umbrales.get("disco_1_advertencia", 25.0)), int(datos_umbrales.get("disco_1_critico", 5.0)),
                int(datos_umbrales.get("disco_2_advertencia", 25.0)), int(datos_umbrales.get("disco_2_critico", 5.0)),
                int(datos_umbrales.get("disco_3_advertencia", 25.0)), int(datos_umbrales.get("disco_3_critico", 5.0)),
                int(datos_umbrales.get("disco_4_advertencia", 25.0)), int(datos_umbrales.get("disco_4_critico", 5.0)),
                int(datos_umbrales.get("disco_5_advertencia", 25.0)), int(datos_umbrales.get("disco_5_critico", 5.0)),
                int(datos_umbrales.get("disco_6_advertencia", 25.0)), int(datos_umbrales.get("disco_6_critico", 5.0)),
                "Actualización de políticas de umbrales en porcentaje (%) según normas del Banco",
                usuario_id
            )
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            with open("simpol_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] Error guardando umbrales porcentuales para {ip}: {e}\n")
    return False

def evaluar_color_por_umbrales(pct_actual, adv, crit, es_inverso=False):
    """
    Evaluación matemática basada estrictamente en Porcentajes (%).
    Para RAM y Discos Libres: Menos porcentaje disponible es peor (es_inverso=False)
    Para CPU Carga: Mayor porcentaje consumido es peor (es_inverso=True)
    """
    PRTG_GREEN = "#2ecc71"   
    PRTG_YELLOW = "#f1c40f"  
    PRTG_RED = "#e74c3c"     

    if es_inverso:
        if pct_actual >= crit:
            return PRTG_RED, "PRTG CRITICAL"
        elif pct_actual >= adv:
            return PRTG_YELLOW, "PRTG WARNING"
        return PRTG_GREEN, "PRTG OK"
    else:
        if pct_actual <= crit:
            return PRTG_RED, "PRTG CRITICAL"
        elif pct_actual <= adv:
            return PRTG_YELLOW, "PRTG WARNING"
        return PRTG_GREEN, "PRTG OK"

def renderizar_semaforo_dinamico(valor_abs, unidad_abs, pct_mostrar, color, texto):
    color_texto = '#000000' if color == "#f1c40f" else '#ffffff'
    return f"""
    <div style="background-color: {color}; padding: 9px; border-radius: 6px; text-align: center; color: {color_texto}; font-weight: bold; font-size: 13px; border: 1px solid rgba(0,0,0,0.1);">
        {texto} ({valor_abs} {unidad_abs} -> {pct_mostrar}%)
    </div>
    """

def mostrar_pantalla(nombre_analista, usuario_id, usuario_login):
    if "servidor_seleccionado_alertas" not in st.session_state:
        st.session_state["servidor_seleccionado_alertas"] = "-- Seleccione un Servidor --"

    if "key_semilla_alertas" not in st.session_state:
        st.session_state["key_semilla_alertas"] = 0

    st.markdown('<h2 style="color:#003366;">🔔 Panel de Control de Semáforos y Alertas (Métricas %)</h2>', unsafe_allow_html=True)
    st.markdown(f"👤 **Cargo Responsable:** {nombre_analista} (`usuario: {usuario_login}`)", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("⚠️ No hay servidores activos registrados en la plataforma.")
        return

    lista_opciones = ["-- Seleccione un Servidor --"] + [f"{s['nombre_alias']} ({s['ip']})" for s in servidores]
    
    try:
        default_index = lista_opciones.index(st.session_state["servidor_seleccionado_alertas"])
    except ValueError:
        default_index = 0

    col_filtro, col_limpieza = st.columns([4, 1])
    with col_filtro:
        sel_global = st.selectbox(
            "Seleccione Servidor de la Infraestructura Corporativa:", 
            lista_opciones, 
            index=default_index,
            key=f"sb_alertas_global_dyn_{st.session_state['key_semilla_alertas']}"
        )
    with col_limpieza:
        st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
        btn_limpiar = st.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_limpiar_alertas_modulo")

    if btn_limpiar:
        st.session_state["servidor_seleccionado_alertas"] = "-- Seleccione un Servidor --"
        st.session_state["key_semilla_alertas"] += 1
        st.rerun()

    st.session_state["servidor_seleccionado_alertas"] = sel_global

    tab_alertas_vivo, tab_config_umbrales = st.tabs(["🚨 Monitoreo de Alertas (Sensores %)", "⚙️ Configuración Avanzada de Umbrales (%)"])

    # =====================================================================
    # PESTAÑA 1: INSPECCIÓN VIVA DE SENSORES EN BASE A PORCENTAJES (%)
    # =====================================================================
    with tab_alertas_vivo:
        if sel_global == "-- Seleccione un Servidor --":
            st.info("💡 Por favor, seleccione un servidor en el control superior para desplegar el estado de alertas de sus sensores indexados.")
        else:
            serv_alr_info = next(s for s in servidores if f"{s['nombre_alias']} ({s['ip']})" == sel_global)
            ip_alr_sel = serv_alr_info['ip']

            telemetria_viva = obtener_telemetria_total(serv_alr_info)
            umbrales_vivos = obtener_umbrales_actuales(ip_alr_sel)

            st.markdown("---")
            st.markdown("#### 🚥 Estado Real de los Sensores en PRTG")

            # VALIDACIÓN ESTRICTA DE REGISTRO EN LA CONFIGURACIÓN DEL SERVIDOR
            tiene_cpu = int(serv_alr_info.get('id_sensor_cpu', 0)) > 0
            tiene_ram = int(serv_alr_info.get('id_sensor_ram', 0)) > 0

            val_cpu = float(telemetria_viva.get('cpu', 0.0))
            val_ram = float(telemetria_viva.get('ram', 0.0))

            # Ambos sensores están explícitamente registrados
            if tiene_cpu and tiene_ram:
                c_cpu, c_ram = st.columns(2)
                with c_cpu:
                    st.markdown("**Procesador (CPU)**")
                    hex_c, txt_c = evaluar_color_por_umbrales(val_cpu, umbrales_vivos["cpu_advertencia"], umbrales_vivos["cpu_critico"], es_inverso=True)
                    st.markdown(renderizar_semaforo_dinamico(val_cpu, "%", val_cpu, hex_c, txt_c), unsafe_allow_html=True)
                with c_ram:
                    st.markdown("**Memoria Volátil Libre (RAM)**")
                    pct_ram_libre = float(telemetria_viva.get('pct_ram', 0.0))
                    hex_r, txt_r = evaluar_color_por_umbrales(pct_ram_libre, umbrales_vivos["ram_advertencia"], umbrales_vivos["ram_critico"], es_inverso=False)
                    st.markdown(renderizar_semaforo_dinamico(val_ram, "GB", pct_ram_libre, hex_r, txt_r), unsafe_allow_html=True)
            
            # Solo la CPU está registrada
            elif tiene_cpu:
                st.markdown("**Procesador (CPU)**")
                hex_c, txt_c = evaluar_color_por_umbrales(val_cpu, umbrales_vivos["cpu_advertencia"], umbrales_vivos["cpu_critico"], es_inverso=True)
                st.markdown(renderizar_semaforo_dinamico(val_cpu, "%", val_cpu, hex_c, txt_c), unsafe_allow_html=True)
            
            # Solo la RAM está registrada (Caso UAP Compensación - Se alinea a la izquierda de forma limpia)
            elif tiene_ram:
                st.markdown("**Memoria Volátil Libre (RAM)**")
                pct_ram_libre = float(telemetria_viva.get('pct_ram', 0.0))
                hex_r, txt_r = evaluar_color_por_umbrales(pct_ram_libre, umbrales_vivos["ram_advertencia"], umbrales_vivos["ram_critico"], es_inverso=False)
                st.markdown(renderizar_semaforo_dinamico(val_ram, "GB", pct_ram_libre, hex_r, txt_r), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 💾 Unidades de Almacenamiento Estático (Libre)")
            
            columnas_discos = st.columns(3)
            col_idx_actual = 0
            
            for i in range(1, 7):
                if serv_alr_info.get(f'id_sensor_disco_{i}', 0) > 0:
                    val_disco = float(telemetria_viva.get(f'disco_{i}', 0.0))
                    if val_disco == 0.0:
                        continue
                    
                    pct_disco_libre = float(telemetria_viva.get(f'pct_disco_{i}', 0.0))
                    
                    adv_d = umbrales_vivos.get(f"disco_{i}_advertencia", 25.0)
                    crit_d = umbrales_vivos.get(f"disco_{i}_critico", 5.0)
                    
                    hex_d, txt_d = evaluar_color_por_umbrales(pct_disco_libre, adv_d, crit_d, es_inverso=False)
                    
                    idx_col = col_idx_actual % 3
                    with columnas_discos[idx_col]:
                        st.markdown(f"**Disco {i} ({serv_alr_info.get(f'letra_disco_{i}', 'U:')})**")
                        st.markdown(renderizar_semaforo_dinamico(val_disco, "GB", pct_disco_libre, hex_d, txt_d), unsafe_allow_html=True)
                        st.markdown("### ")
                    col_idx_actual += 1

            st.markdown("---")
            st.markdown("##### ⚙️ Estado de Servicios del Sistema (Monitoreo Activo PRTG)")
            
            columnas_servicios = st.columns(4)
            srv_idx_actual = 0
            
            for s in range(1, 9):
                if serv_alr_info.get(f'id_sensor_servicio_{s}', 0) > 0:
                    raw_srv = telemetria_viva.get(f'servicio_{s}', 'OFF')
                    estado_srv = "ON" if (raw_srv == 1 or raw_srv in ["ON", "OK", "UP"]) else "OFF"
                    color_srv = "#2ecc71" if estado_srv == "ON" else "#e74c3c"
                    
                    idx_srv_col = srv_idx_actual % 4
                    with columnas_servicios[idx_srv_col]:
                        st.markdown(f"**Servicio {s}**")
                        st.markdown(renderizar_semaforo_dinamico(estado_srv, "", "", color_srv, f"PRTG {estado_srv}"), unsafe_allow_html=True)
                        st.markdown("### ")
                    srv_idx_actual += 1
            
            if srv_idx_actual == 0:
                st.caption("ℹ️ No se encuentran sensores de servicios asociados a este nodo de red.")

    # =====================================================================
    # PESTAÑA 2: CONFIGURACIÓN DE UMBRALES EN PORCENTAJE (%)
    # =====================================================================
    with tab_config_umbrales:
        if sel_global == "-- Seleccione un Servidor --":
            st.warning("💡 Por favor, elija un servidor válido en el control superior para parametrizar sus umbrales.")
        else:
            serv_conf_info = next(s for s in servidores if f"{s['nombre_alias']} ({s['ip']})" == sel_global)
            ip_conf_sel = serv_conf_info['ip']
            umbrales_vivos = obtener_umbrales_actuales(ip_conf_sel)
            
            st.markdown(f"#### 🛠️ Modificando Parámetros de Nodo: `{serv_conf_info['nombre_alias']} ({ip_conf_sel})`")
            st.info("🏛️ **Normativa Institucional:** Los valores ingresados a continuación representan límites en Porcentaje Mínimo Libre (%)")
            
            with st.form(key=f"form_umbrales_global_{ip_conf_sel}"):
                dict_nuevos_valores = {}
                
                if int(serv_conf_info.get('id_sensor_cpu', 0)) > 0:
                    st.markdown("---")
                    st.markdown("📊 **Umbrales del Procesador (CPU %)**")
                    c_cpu1, c_cpu2 = st.columns(2)
                    with c_cpu1:
                        dict_nuevos_valores["cpu_advertencia"] = st.number_input(
                            "Límite Advertencia (%)", min_value=1.0, max_value=100.0,
                            value=float(umbrales_vivos.get("cpu_advertencia", 70.0)), step=1.0
                        )
                    with c_cpu2:
                        dict_nuevos_valores["cpu_critico"] = st.number_input(
                            "Límite Crítico (%)", min_value=1.0, max_value=100.0,
                            value=float(umbrales_vivos.get("cpu_critico", 85.0)), step=1.0
                        )
                
                if int(serv_conf_info.get('id_sensor_ram', 0)) > 0:
                    st.markdown("---")
                    st.markdown("🧠 **Umbrales de Memoria Volátil Libre (RAM %)**")
                    c_ram1, c_ram2 = st.columns(2)
                    with c_ram1:
                        dict_nuevos_valores["ram_advertencia"] = st.number_input(
                            "Límite Advertencia (% Mínimo Libre)", min_value=1.0, max_value=100.0,
                            value=float(umbrales_vivos.get("ram_advertencia", 15.0)), step=1.0
                        )
                    with c_ram2:
                        dict_nuevos_valores["ram_critico"] = st.number_input(
                            "Límite Crítico (% Mínimo Libre)", min_value=1.0, max_value=100.0,
                            value=float(umbrales_vivos.get("ram_critico", 10.0)), step=1.0
                        )

                tiene_discos = any(int(serv_conf_info.get(f'id_sensor_disco_{d}', 0)) > 0 for d in range(1, 7))
                if tiene_discos:
                    st.markdown("---")
                    st.markdown("💾 **Umbrales de Unidades de Almacenamiento (Discos % Libres)**")
                    
                    for d in range(1, 7):
                        if int(serv_conf_info.get(f'id_sensor_disco_{d}', 0)) > 0:
                            st.markdown(f"**Disco {d}:**")
                            c_d1, c_d2 = st.columns(2)
                            with c_d1:
                                dict_nuevos_valores[f"disco_{d}_advertencia"] = st.number_input(
                                    f"Advertencia Disco {d} (% Libre)", min_value=1.0, max_value=100.0,
                                    value=float(umbrales_vivos.get(f"disco_{d}_advertencia", 25.0)), step=1.0, key=f"inp_d_adv_gl_{d}_{ip_conf_sel}"
                                )
                            with c_d2:
                                dict_nuevos_valores[f"disco_{d}_critico"] = st.number_input(
                                    f"Crítico Disco {d} (% Libre)", min_value=1.0, max_value=100.0,
                                    value=float(umbrales_vivos.get(f"disco_{d}_critico", 5.0)), step=1.0, key=f"inp_d_crit_gl_{d}_{ip_conf_sel}"
                                )

                st.markdown("<br>", unsafe_allow_html=True)
                btn_salvar = st.form_submit_button("💾 ACTUALIZAR POLÍTICAS DE UMBRALES PORCENTUALES", use_container_width=True)
                
                if btn_salvar:
                    for k, v in umbrales_vivos.items():
                        if k not in dict_nuevos_valores:
                            dict_nuevos_valores[k] = v
                            
                    exito = guardar_nuevos_umbrales(ip_conf_sel, dict_nuevos_valores, usuario_id)
                    if exito:
                        st.success(f"🎉 Umbrales operacionales del banco guardados en % con éxito para el servidor {serv_conf_info['nombre_alias']}.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Error interno de persistencia. Revise el archivo 'simpol_debug.log'.")

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Nombre Completo")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "Usuario")
    
    mostrar_pantalla(cargo_usuario, id_usuario, login_usuario)