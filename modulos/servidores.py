import streamlit as st
from database import conectar_bd
import re
import urllib.parse
import time
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================================================
# OPTIMIZACIÓN DE RENDIMIENTO: Caché para evitar consultas pesadas recurrentes
# ==========================================================================
@st.cache_data(ttl=60)
def obtener_lista_nombres_servidores():
    try:
        conn = conectar_bd()
        if conn is None:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT nombre_alias FROM servidores WHERE nombre_alias IS NOT NULL AND nombre_alias != '' ORDER BY nombre_alias ASC")
        nombres = [r['nombre_alias'] for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return nombres
    except Exception:
        return []

def validar_ip(ip_str):
    """Valida que el formato de la IP sea estructuralmente correcto (IPv4)."""
    patron = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    return bool(re.match(patron, ip_str.strip()))

# ==========================================================================
# FRAGMENTO PARA LA PESTAÑA 2 - DATOS ADICIONALES
# ==========================================================================
@st.fragment
def renderizar_pestana_datos_adicionales(es_seguridad):
    """Fragmento independiente para la pestaña de datos adicionales"""
    
    st.markdown('<h3 style="color:#003366;">📋 Control de Máquinas Virtuales y Parámetros Adicionales</h3>', unsafe_allow_html=True)
    
    if "filtro_adicional_nombre" not in st.session_state:
        st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
    if "accion_adicional" not in st.session_state:
        st.session_state.accion_adicional = None

    conn_ad = None
    cursor_ad = None
    
    try:
        lista_nombres_bd_ad = obtener_lista_nombres_servidores()
        opciones_selectbox_ad = ["-- Seleccione un Servidor Base --", "-- Ver Todos los Servidores Base --"] + lista_nombres_bd_ad

        conn_ad = conectar_bd()
        cursor_ad = conn_ad.cursor(dictionary=True)
        
        cursor_ad.execute("SELECT COUNT(*) as total FROM datos_adicionales")
        total_registros = cursor_ad.fetchone()['total']
        hay_registros = total_registros > 0

        if hay_registros:
            col_f_ad1, col_f_ad2, col_f_ad3 = st.columns([3, 1, 1])
            
            with col_f_ad1:
                st.selectbox(
                    "Filtrar Entornos por Servidor Base",
                    options=opciones_selectbox_ad,
                    key="filtro_adicional_nombre",
                    label_visibility="collapsed"
                )
            
            with col_f_ad2:
                if st.button("🔍 Filtrar", key="btn_filtrar_filtro_ad", use_container_width=True):
                    st.rerun(scope="fragment")
            
            with col_f_ad3:
                if st.button("🧹 Limpiar", key="btn_limpiar_filtro_ad", use_container_width=True):
                    st.query_params["_limpiar_filtro_ad"] = "1"
                    st.rerun(scope="fragment")
        else:
            st.info("📭 No hay registros de máquinas virtuales o parámetros adicionales en la base de datos.")
            st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"

        if "_limpiar_filtro_ad" in st.query_params and st.query_params["_limpiar_filtro_ad"] == "1":
            st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
            st.session_state.accion_adicional = None
            del st.query_params["_limpiar_filtro_ad"]
            st.rerun(scope="fragment")

        filtro_adicional = st.session_state["filtro_adicional_nombre"]
        
        hay_filtro_ad = filtro_adicional != "-- Seleccione un Servidor Base --"
        ver_todos_ad = filtro_adicional == "-- Ver Todos los Servidores Base --"
        registros_adicionales = []
        
        cursor_ad.execute("SELECT id_servidor, ip, nombre_alias FROM servidores ORDER BY nombre_alias ASC")
        servidores_maestros = cursor_ad.fetchall()
        opciones_srv_map = {f"{s['nombre_alias']} ({s['ip']})": s['id_servidor'] for s in servidores_maestros}

        if hay_filtro_ad and hay_registros:
            if ver_todos_ad:
                query_select_ad = """
                    SELECT da.id, da.id_servidor, s.nombre_alias, s.ip AS ip_maestra, da.host, da.nombre_vm, 
                           da.estado, da.uso_cpu_pct, da.memoria_asignada_mb, da.tiempo_encendido, 
                           da.nombre_switch, da.direccion_mac, da.direcciones_ip, da.version, 
                           da.tamano_gb, da.amount_vhd, da.funcion
                    FROM datos_adicionales da
                    INNER JOIN servidores s ON da.id_servidor = s.id_servidor
                    ORDER BY s.nombre_alias ASC, da.id DESC
                """
                cursor_ad.execute(query_select_ad)
            else:
                query_select_ad = """
                    SELECT da.id, da.id_servidor, s.nombre_alias, s.ip AS ip_maestra, da.host, da.nombre_vm, 
                           da.estado, da.uso_cpu_pct, da.memoria_asignada_mb, da.tiempo_encendido, 
                           da.nombre_switch, da.direccion_mac, da.direcciones_ip, da.version, 
                           da.tamano_gb, da.amount_vhd, da.funcion
                    FROM datos_adicionales da
                    INNER JOIN servidores s ON da.id_servidor = s.id_servidor
                    WHERE s.nombre_alias = %s
                    ORDER BY da.id DESC
                """
                cursor_ad.execute(query_select_ad, (filtro_adicional,))
            
            registros_adicionales = cursor_ad.fetchall()
        
            if not registros_adicionales:
                st.warning("📭 No se encuentran entornos o máquinas virtuales registradas para la selección.")
            else:
                html_ad = ["""
                <style>
                    .tabla-banco { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
                    .tabla-banco th { background-color: #003366 !important; color: white !important; font-weight: bold !important; text-align: center !important; padding: 14px 16px; border: 1px solid #dee2e6 !important; font-size: 11px; text-transform: uppercase; white-space: nowrap !important; }
                    .tabla-banco td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 12px 14px; text-align: left; font-size: 13px; white-space: nowrap !important; }
                    .tabla-banco tr:nth-child(even) { background-color: #f8f9fa; }
                </style>
                <div style="overflow-x: auto; width: 100%;"><table class="tabla-banco"><thead><tr>
                    <th>SERVIDOR BASE</th><th>HOST FISICO</th><th>MÁQUINA VIRTUAL</th><th>ESTADO</th><th>CPU</th><th>RAM</th><th>FUNCIÓN ROL</th>
                </tr></thead><tbody>
                """]
                
                mapeo_adicionales = {}
                lista_ids_adicionales = []
                
                for r in registros_adicionales:
                    str_id = str(r['id'])
                    lista_ids_adicionales.append(str_id)
                    mapeo_adicionales[str_id] = r
                    
                    est = str(r['estado']).upper()
                    color_est = "#2E7D32" if est in ["RUNNING", "ON", "ACTIVO"] else "#C62828"
                    estado_html = f'<span style="color: {color_est}; font-weight: bold;">{est}</span>'
                    
                    html_ad.append(f"""
                        <tr>
                            <td>{r['nombre_alias']} ({r['ip_maestra']})</td>
                            <td>{r['host']}</td>
                            <td><b>{r['nombre_vm']}</b></td>
                            <td style="text-align: center;">{estado_html}</td>
                            <td style="text-align: right;">{r['uso_cpu_pct']}%</td>
                            <td style="text-align: right;">{r['memoria_asignada_mb']} MB</td>
                            <td>{r['funcion'] if r['funcion'] else 'N/A'}</td>
                        </tr>
                    """)
                html_ad.append("</tbody></table></div>")
                
                altura_ad = max(180, len(registros_adicionales) * 55 + 75)
                st.components.v1.html("".join(html_ad), height=altura_ad, scrolling=True)

            st.markdown("---")

            if not es_seguridad:
                st.info("ℹ️ **Modo Consulta Activo:** Su cuenta operativa actual no posee permisos para alterar la matriz de datos adicionales.")
            else:
                if st.session_state.accion_adicional is None and not ver_todos_ad:
                    c_ab1, c_ab2 = st.columns(2)
                    if c_ab1.button("➕ Registrar Parámetro Adicional", use_container_width=True, key="btn_ad_crear"):
                        st.session_state.accion_adicional = "registrar"
                        st.rerun(scope="fragment")
                        
                    if registros_adicionales and c_ab2.button("✏️ Editar Parámetro Adicional", use_container_width=True, key="btn_ad_editar"):
                        st.session_state.accion_adicional = "editar"
                        st.rerun(scope="fragment")

        if not hay_registros:
            st.markdown("---")
            if es_seguridad:
                if st.button("➕ Registrar Primer Parámetro Adicional", use_container_width=True, key="btn_ad_crear_primero"):
                    st.session_state.accion_adicional = "registrar"
                    st.rerun(scope="fragment")
            else:
                st.info("ℹ️ **Modo Consulta Activo:** Su cuenta operativa actual no posee permisos para alterar la matriz de datos adicionales.")

        if st.session_state.accion_adicional == "registrar":
            st.markdown("### 📥 Registrar Parámetro VM / Extensión de Infraestructura")
            with st.form("form_registro_adicional"):
                col_r1, col_r2, col_r3 = st.columns(3)
                srv_combo = col_r1.selectbox("Servidor Maestro Relacionado", list(opciones_srv_map.keys()))
                ad_host = col_r2.text_input("Host Físico Hospedador")
                ad_vm = col_r3.text_input("Nombre Máquina Virtual")
                
                col_r4, col_r5 = st.columns(2)
                ad_estado = col_r4.selectbox("Estado Actual", ["Running", "OFF"])
                ad_funcion = col_r5.text_input("Rol / Función Operativa")
                
                col_btn_ar1, col_btn_ar2 = st.columns(2)
                if col_btn_ar1.form_submit_button("💾 CONSERVAR REGISTRO EN BD", use_container_width=True):
                    if not ad_host.strip() or not ad_vm.strip():
                        st.error("❌ Los campos Host Físico y Nombre Máquina Virtual son estrictamente requeridos.")
                    else:
                        try:
                            id_srv_target = opciones_srv_map[srv_combo]
                            query_ins = "INSERT INTO datos_adicionales (id_servidor, host, nombre_vm, estado, funcion) VALUES (%s, %s, %s, %s, %s)"
                            cursor_ad.execute(query_ins, (id_srv_target, ad_host.strip(), ad_vm.strip(), ad_estado, ad_funcion.strip()))
                            conn_ad.commit()
                            st.success("✅ Mapeo adicional registrado exitosamente.")
                            st.session_state.accion_adicional = None
                            st.rerun(scope="fragment")
                        except Exception as ex_ins:
                            st.error(f"❌ Fallo de inserción: {ex_ins}")
                                    
                if col_btn_ar2.form_submit_button("❌ CANCELAR", use_container_width=True):
                    st.session_state.accion_adicional = None
                    st.rerun(scope="fragment")

        if st.session_state.accion_adicional == "editar" and registros_adicionales:
            st.markdown("### ✏️ Modificar Registro de Extensión Técnico")
            id_ad_edit = st.selectbox("Seleccione el ID del Registro Adicional a Modificar", lista_ids_adicionales, key="sb_id_ad_edit")
            
            if id_ad_edit:
                ad_actual = mapeo_adicionales[id_ad_edit]
                with st.form("form_edicion_adicional"):
                    edit_host = st.text_input("Host Físico Hospedador", value=ad_actual['host'])
                    edit_vm = st.text_input("Nombre Máquina Virtual", value=ad_actual['nombre_vm'])
                    edit_funcion = st.text_input("Rol / Función Operativa", value=ad_actual['funcion'] if ad_actual['funcion'] else "")
                    
                    col_btn_ae1, col_btn_ae2 = st.columns(2)
                    if col_btn_ae1.form_submit_button("✏️ COMPROMETER CAMBIOS", use_container_width=True):
                        try:
                            query_upd = "UPDATE datos_adicionales SET host=%s, nombre_vm=%s, funcion=%s WHERE id=%s"
                            cursor_ad.execute(query_upd, (edit_host.strip(), edit_vm.strip(), edit_funcion.strip(), int(id_ad_edit)))
                            conn_ad.commit()
                            st.success("✅ Parámetro consolidado y actualizado de forma segura.")
                            st.session_state.accion_adicional = None
                            st.rerun(scope="fragment")
                        except Exception as ex_upd:
                            st.error(f"❌ Fallo de actualización: {ex_upd}")
                                        
                    if col_btn_ae2.form_submit_button("❌ CANCELAR", use_container_width=True):
                        st.session_state.accion_adicional = None
                        st.rerun(scope="fragment")
                                
    except Exception as e_ad:
        st.error(f"❌ Error al procesar la pestaña de datos adicionales: {e_ad}")
    finally:
        if cursor_ad: cursor_ad.close()
        if conn_ad: conn_ad.close()


def mostrar_tabla_servidores(rol_usuario=None):
    """
    Renderiza el catálogo de servidores en una tabla HTML pura y profesional.
    Permite filtrar por un servidor o seleccionar la opción global para verlos todos.
    """
    st.markdown("""
        <style>
            div[data-testid="stForm"] label p {
                font-size: 14px !important;
                font-weight: 600 !important;
                color: #333333 !important;
                margin-bottom: 2px !important;
            }
            div[data-testid="stForm"] input {
                padding: 8px 12px !important;
                font-size: 14px !important;
                border-radius: 6px !important;
                height: 42px !important;
            }
            input[type=number]::-webkit-inner-spin-button, 
            input[type=number]::-webkit-outer-spin-button { 
                -webkit-appearance: none; 
                margin: 0; 
            }
            input[type=number] {
                -moz-appearance: textfield;
            }
            div[data-testid="stNumberInput"] button {
                display: none !important;
            }
            .subtitulo-formulario {
                color: #003366;
                margin-top: 25px;
                margin-bottom: 15px;
                border-bottom: 2px solid #ECEFF1;
                padding-bottom: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            div[data-testid="stForm"] button, 
            div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button,
            .stFormSubmitButton > button {
                height: 44px !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                font-size: 14px !important;
                margin-top: 10px !important;
                transition: all 0.3s ease !important;
            }
            [data-testid="stTextInputInstructions"] {
                display: none !important;
            }
            .info-analista {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista span {
                color: #003366;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366;">🖥️ Gestión Servidores</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    rol_sanitizado = str(rol_usuario).strip().upper() if rol_usuario else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado

    # ==========================================================================
    # PROCESAR REDIRECCIÓN A MONITOREO (USANDO SESSION_STATE)
    # ==========================================================================
    if "redirigir_servidor" in st.session_state and st.session_state["redirigir_servidor"]:
        servidor = st.session_state["redirigir_servidor"]
        if servidor and servidor != "-- Seleccione un Servidor --":
            logging.info(f"🔍 Redirigiendo a servidor: {servidor}")
            st.session_state["redirigir_servidor"] = None
            # Usar flag en lugar de modificar widgets directamente
            st.session_state["_srv_redirect_pending"] = servidor
            st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
            st.rerun()
        else:
            st.session_state["redirigir_servidor"] = None

    if "tab_servidores_activa" not in st.session_state:
        st.session_state.tab_servidores_activa = 0
    
    tab_param = st.query_params.get("tab_servidores")
    if tab_param == "2":
        st.session_state.tab_servidores_activa = 1
    elif tab_param == "1":
        st.session_state.tab_servidores_activa = 0

    if "_limpiar_filtro_srv" in st.query_params and st.query_params["_limpiar_filtro_srv"] == "1":
        st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
        st.session_state.accion_infra = None
        st.session_state.filtro_aplicado_srv = False
        del st.query_params["_limpiar_filtro_srv"]
        st.rerun()

    if "filtro_servidor_nombre" not in st.session_state:
        st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
    if "accion_infra" not in st.session_state:
        st.session_state.accion_infra = None
    if "filtro_aplicado_srv" not in st.session_state:
        st.session_state.filtro_aplicado_srv = False

    tab1, tab2 = st.tabs(["📊 Infraestructura y Sensores", "⚙️ Datos Adicionales"])

    with tab1:
        st.session_state.tab_servidores_activa = 0
        # IMPORTANTE: Solo establecer tab_servidores si NO estamos en monitoreo
        # El flag _en_monitoreo se establece en monitoreo.py
        if not st.session_state.get("_en_monitoreo", False):
            if st.query_params.get("tab_servidores") != "1":
                st.query_params["tab_servidores"] = "1"

        conn = None
        cursor = None

        try:
            lista_nombres_bd = obtener_lista_nombres_servidores()
            opciones_selectbox = ["-- Seleccione un Servidor --", "-- Ver Todos los Servidores --"] + lista_nombres_bd

            idx_actual = 0
            if st.session_state["filtro_servidor_nombre"] in opciones_selectbox:
                idx_actual = opciones_selectbox.index(st.session_state["filtro_servidor_nombre"])

            col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
            
            with col_f1:
                st.selectbox(
                    "Filtrar Servidor por Nombre",
                    options=opciones_selectbox,
                    index=idx_actual,
                    key="sb_filtro_p1",
                    label_visibility="collapsed"
                )
                st.session_state["filtro_servidor_nombre"] = st.session_state["sb_filtro_p1"]
            
            with col_f2:
                if st.button("🔍 Filtrar", key="btn_filtrar_srv", use_container_width=True):
                    st.session_state.filtro_aplicado_srv = True
                    st.rerun()
            
            with col_f3:
                if st.button("🧹 Limpiar", key="btn_limpiar_filtro_srv", use_container_width=True):
                    st.query_params["_limpiar_filtro_srv"] = "1"
                    st.rerun()

            hay_filtro = st.session_state.filtro_aplicado_srv and st.session_state["filtro_servidor_nombre"] != "-- Seleccione un Servidor --"
            ver_todos = st.session_state["filtro_servidor_nombre"] == "-- Ver Todos los Servidores --"
            servidores_filtrados = []

            if not st.session_state.filtro_aplicado_srv:
                st.info("🔍 Seleccione un servidor y presione 'Filtrar' para visualizar sus parámetros técnicos.")
            elif not hay_filtro:
                st.info("🖥️ Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus parámetros técnicos.")
            else:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                
                if ver_todos:
                    query = """
                        SELECT id_servidor, ip, nombre_alias, sistema_operativo, tipo, servicios, estado_monitoreo, fecha_alta, 
                               id_sensor_cpu, id_sensor_ram, 
                               id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                               id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                               id_sensor_servicio_6, id_sensor_servicio_7, id_sensor_servicio_8,
                               id_sensor_red_total, id_sensor_red_entrante, id_sensor_red_saliente, id_sensor_latencia 
                        FROM servidores
                        ORDER BY nombre_alias ASC
                    """
                    cursor.execute(query)
                else:
                    query = """
                        SELECT id_servidor, ip, nombre_alias, sistema_operativo, tipo, servicios, estado_monitoreo, fecha_alta, 
                               id_sensor_cpu, id_sensor_ram, 
                               id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                               id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                               id_sensor_servicio_6, id_sensor_servicio_7, id_sensor_servicio_8,
                               id_sensor_red_total, id_sensor_red_entrante, id_sensor_red_saliente, id_sensor_latencia 
                        FROM servidores
                        WHERE nombre_alias = %s
                    """
                    cursor.execute(query, (st.session_state["filtro_servidor_nombre"],))
                
                servidores_filtrados = cursor.fetchall()

                if not servidores_filtrados:
                    st.warning("📭 No se encontraron registros detallados para la selección actual.")

            if hay_filtro and servidores_filtrados:
                tiene_cpu = any(s['id_sensor_cpu'] != 0 for s in servidores_filtrados)
                tiene_ram = any(s['id_sensor_ram'] != 0 for s in servidores_filtrados)
                tiene_red_tot = any(s['id_sensor_red_total'] != 0 for s in servidores_filtrados)
                tiene_red_ent = any(s['id_sensor_red_entrante'] != 0 for s in servidores_filtrados)
                tiene_red_sal = any(s['id_sensor_red_saliente'] != 0 for s in servidores_filtrados)
                tiene_latencia = any(s['id_sensor_latencia'] != 0 for s in servidores_filtrados)
                
                discos_activos = {}
                letras_unidades = {1: "C:", 2: "D:", 3: "E:", 4: "F:", 5: "G:", 6: "Y:"}
                for i in range(1, 7):
                    discos_activos[i] = any(s[f'id_sensor_disco_{i}'] != 0 for s in servidores_filtrados)
                
                servicios_activos = {}
                for i in range(1, 9):
                    servicios_activos[i] = any(s.get(f'id_sensor_servicio_{i}', 0) != 0 for s in servidores_filtrados)

                html_lineas = ["""
                <style>
                    .tabla-banco { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
                    .tabla-banco th { background-color: #003366 !important; color: white !important; font-weight: bold !important; text-align: center !important; padding: 14px 16px; border: 1px solid #dee2e6 !important; font-size: 11px; text-transform: uppercase; white-space: nowrap !important; }
                    .tabla-banco td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 12px 14px; text-align: left; font-size: 13px; white-space: nowrap !important; vertical-align: middle; }
                    .tabla-banco tr:nth-child(even) { background-color: #f8f9fa; }
                </style>
                <div style="overflow-x: auto;"><table class="tabla-banco"><thead><tr>
                """]
                html_lineas.append('<th>DIRECCIÓN IP</th>')
                html_lineas.append('<th>NOMBRE</th>')
                html_lineas.append('<th>SISTEMA OPERATIVO</th>')
                html_lineas.append('<th>TIPO</th>')
                
                if tiene_cpu: html_lineas.append('<th>ID CPU</th>')
                if tiene_ram: html_lineas.append('<th>ID RAM</th>')
                
                for i in range(1, 7):
                    if discos_activos[i]: 
                        html_lineas.append(f'<th>DISCO {letras_unidades[i]}</th>')
                        
                for i in range(1, 9):
                    if servicios_activos[i]: 
                        html_lineas.append(f'<th>SERVICIO {i}</th>')
                        
                if tiene_red_tot: html_lineas.append('<th>RED TOTAL</th>')
                if tiene_red_ent: html_lineas.append('<th>RED ENTRANTE</th>')
                if tiene_red_sal: html_lineas.append('<th>RED SALIENTE</th>')
                if tiene_latencia: html_lineas.append('<th>ID LATENCIA</th>')
                
                html_lineas.append('<th>ESTADO</th>')
                html_lineas.append('<th>FECHA REGISTRO</th>')
                html_lineas.append('</tr></thead><tbody>')
                
                lista_ips = []
                mapeo_servidores = {}
                servidores_para_botones = []
                
                for s in servidores_filtrados:
                    lista_ips.append(s['ip'])
                    mapeo_servidores[s['ip']] = s
                    servidores_para_botones.append(s)
                    
                    estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>' if s['estado_monitoreo'] == 1 else '<span style="color: #C62828; font-weight: bold;">INACTIVO</span>'
                    fecha_formateada = s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"

                    html_lineas.append('<tr>')
                    html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                    html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                    html_lineas.append(f'<td>{s["sistema_operativo"]}</td>')
                    html_lineas.append(f'<td>{s.get("tipo", "Virtual")}</td>')
                    
                    if tiene_cpu: 
                        val = s["id_sensor_cpu"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    if tiene_ram: 
                        val = s["id_sensor_ram"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    
                    for i in range(1, 7):
                        if discos_activos[i]: 
                            val = s[f"id_sensor_disco_{i}"]
                            html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                            
                    for i in range(1, 9):
                        if servicios_activos[i]: 
                            val = s.get(f"id_sensor_servicio_{i}", 0)
                            html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                            
                    if tiene_red_tot: 
                        val = s["id_sensor_red_total"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    if tiene_red_ent: 
                        val = s["id_sensor_red_entrante"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    if tiene_red_sal: 
                        val = s["id_sensor_red_saliente"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    if tiene_latencia: 
                        val = s["id_sensor_latencia"]
                        html_lineas.append(f'<td>{"No asignado" if val == 0 else val}</td>')
                    
                    html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                    html_lineas.append(f'<td>{fecha_formateada}</td>')
                    html_lineas.append('</tr>')
                
                html_lineas.append('<tbody></table></div>')
                html_final = "".join(html_lineas)
                
                altura_vista = max(180, len(servidores_filtrados) * 55 + 85)
                st.components.v1.html(html_final, height=altura_vista, scrolling=True)
                
                st.markdown("---")
                st.markdown("### 📊 Ver en Vivo - Seleccione un Servidor")
                
                num_columnas = min(4, len(servidores_para_botones))
                cols_botones = st.columns(num_columnas)
                for idx, s in enumerate(servidores_para_botones):
                    col_idx = idx % num_columnas
                    with cols_botones[col_idx]:
                        nombre_servidor = s['nombre_alias']
                        if st.button(
                            f"📊 {nombre_servidor}", 
                            key=f"btn_vivo_{nombre_servidor}", 
                            use_container_width=True
                        ):
                            # Guardar en session_state y query_params para redirección
                            st.session_state["_srv_redirect_pending"] = nombre_servidor
                            st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
                            # Limpiar query params anteriores y establecer nuevos
                            st.query_params.clear()
                            st.query_params["srv"] = nombre_servidor
                            st.query_params["p"] = "🖥️ Monitoreo en vivo"
                            st.query_params["s"] = "1"
                            st.query_params["rol"] = st.session_state.get("rol", "seguridad")
                            st.query_params["uid"] = str(st.session_state.get("user_id", 1))
                            st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
                            st.query_params["c"] = st.session_state.get("cargo", "Analista")
                            # Forzar rerun para aplicar los cambios
                            st.rerun()

                st.markdown("---")

                if not es_seguridad:
                    st.info("ℹ️ **Modo Consulta Activo:** Su perfil de Operador permite verificar la infraestructura pero no dispone de privilegios para modificar el catálogo.")
                else:
                    if not ver_todos:
                        col_b1, col_b2 = st.columns(2)
                        if col_b1.button("📝 Editar Servidor Filtrado", use_container_width=True, key="btn_crud_editar"):
                            st.session_state.accion_infra = "editar"
                            st.rerun()
                        if col_b2.button("❌ Cambiar Estado / Desactivar", use_container_width=True, key="btn_crud_desactivar"):
                            st.session_state.accion_infra = "desactivar"
                            st.rerun()

                if st.session_state.accion_infra == "editar" and hay_filtro and not ver_todos:
                    st.markdown("### ✏️ Modificación de Parámetros Técnicos")
                    ip_edit = st.selectbox("Seleccione la IP del Servidor a Modificar", lista_ips)
                    
                    if ip_edit:
                        srv_actual = mapeo_servidores[ip_edit]
                        fecha_act = srv_actual['fecha_alta'].strftime("%Y-%m-%d %H:%M") if srv_actual['fecha_alta'] else "N/A"
                        
                        with st.form("form_edicion_srv"):
                            st.markdown("<div class='subtitulo-formulario'>🔒 Información Base Bloqueada</div>", unsafe_allow_html=True)
                            col_lock1, col_lock2 = st.columns(2)
                            col_lock1.text_input("Fecha de Alta Institucional", value=fecha_act, disabled=True)
                            col_lock2.text_input("Sistema Operativo Asignado", value=srv_actual['sistema_operativo'], disabled=True)
                            
                            st.markdown("<div class='subtitulo-formulario'>📋 Identificación Comercial</div>", unsafe_allow_html=True)
                            col_edi_p1, col_edi_p2 = st.columns(2)
                            edit_alias = col_edi_p1.text_input("Alias / Nombre Comercial del Servidor", value=srv_actual['nombre_alias'])
                            edit_servicios = col_edi_p2.text_input("Servicios Core descritos", value=srv_actual.get('servicios', 'Ninguno'))
                            
                            st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                            col_e1, col_e2 = st.columns(2)
                            edit_cpu = col_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=int(srv_actual['id_sensor_cpu']), step=None)
                            edit_ram = col_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=int(srv_actual['id_sensor_ram']), step=None)
                            edit_lat = st.number_input("ID Sensor PRTG - Latencia (Ping)", value=int(srv_actual['id_sensor_latencia']), step=None)
                            
                            st.markdown("<div class='subtitulo-formulario'>🌐 Sensores de Red Distribuidos</div>", unsafe_allow_html=True)
                            col_edr1, col_edr2, col_edr3 = st.columns(3)
                            edit_red_tot = col_edr1.number_input("ID Red - Tráfico Total", value=int(srv_actual.get('id_sensor_red_total', 0)), step=None)
                            edit_red_ent = col_edr2.number_input("ID Red - Tráfico Entrante", value=int(srv_actual.get('id_sensor_red_entrante', 0)), step=None)
                            edit_red_sal = col_edr3.number_input("ID Red - Tráfico Saliente", value=int(srv_actual.get('id_sensor_red_saliente', 0)), step=None)

                            st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                            col_d1, col_d2, col_d3 = st.columns(3)
                            edit_d1 = col_d1.number_input("Disco 1 (Unidad C:\\)", value=int(srv_actual['id_sensor_disco_1']), step=None)
                            edit_d2 = col_d2.number_input("Disco 2 (Unidad D:\\)", value=int(srv_actual['id_sensor_disco_2']), step=None)
                            edit_d3 = col_d3.number_input("Disco 3 (Unidad E:\\)", value=int(srv_actual['id_sensor_disco_3']), step=None)
                            
                            col_d4, col_d5, col_d6 = st.columns(3)
                            edit_d4 = col_d4.number_input("Disco 4 (Unidad F:\\)", value=int(srv_actual['id_sensor_disco_4']), step=None)
                            edit_d5 = col_d5.number_input("Disco 5 (Unidad G:\\)", value=int(srv_actual['id_sensor_disco_5']), step=None)
                            edit_d6 = col_d6.number_input("Disco 6 (Unidad Y:\\)", value=int(srv_actual.get('id_sensor_disco_6', 0)), step=None)

                            st.markdown("<div class='subtitulo-formulario'>⚙️ Sensores de Servicio Activos (8 Slots Ampliados)</div>", unsafe_allow_html=True)
                            col_s1, col_s2 = st.columns(2)
                            edit_s1 = col_s1.number_input("ID Sensor - Servicio Sistema 1", value=int(srv_actual.get('id_sensor_servicio_1', 0)), step=None)
                            edit_s2 = col_s2.number_input("ID Sensor - Servicio Sistema 2", value=int(srv_actual.get('id_sensor_servicio_2', 0)), step=None)
                            
                            col_s3, col_s4, col_s5 = st.columns(3)
                            edit_s3 = col_s3.number_input("ID Sensor - Servicio 3", value=int(srv_actual.get('id_sensor_servicio_3', 0)), step=None)
                            edit_s4 = col_s4.number_input("ID Sensor - Servicio 4", value=int(srv_actual.get('id_sensor_servicio_4', 0)), step=None)
                            edit_s5 = col_s5.number_input("ID Sensor - Servicio 5", value=int(srv_actual.get('id_sensor_servicio_5', 0)), step=None)
                            
                            col_s6, col_s7, col_s8 = st.columns(3)
                            edit_s6 = col_s6.number_input("ID Sensor - Servicio 6", value=int(srv_actual.get('id_sensor_servicio_6', 0)), step=None)
                            edit_s7 = col_s7.number_input("ID Sensor - Servicio 7", value=int(srv_actual.get('id_sensor_servicio_7', 0)), step=None)
                            edit_s8 = col_s8.number_input("ID Sensor - Servicio 8", value=int(srv_actual.get('id_sensor_servicio_8', 0)), step=None)
                            
                            col_btn_edi1, col_btn_edi2 = st.columns(2)
                            if col_btn_edi1.form_submit_button("✏️ Aplicar Cambios", use_container_width=True):
                                try:
                                    conn_edit = conectar_bd()
                                    cursor_edit = conn_edit.cursor()
                                    upd_query = """
                                        UPDATE servidores 
                                        SET nombre_alias=%s, servicios=%s, id_sensor_cpu=%s, id_sensor_ram=%s, 
                                            id_sensor_disco_1=%s, id_sensor_disco_2=%s, id_sensor_disco_3=%s, id_sensor_disco_4=%s, id_sensor_disco_5=%s, id_sensor_disco_6=%s,
                                            id_sensor_servicio_1=%s, id_sensor_servicio_2=%s, id_sensor_servicio_3=%s, id_sensor_servicio_4=%s, id_sensor_servicio_5=%s,
                                            id_sensor_servicio_6=%s, id_sensor_servicio_7=%s, id_sensor_servicio_8=%s,
                                            id_sensor_red_total=%s, id_sensor_red_entrante=%s, id_sensor_red_saliente=%s, id_sensor_latencia=%s
                                        WHERE ip=%s
                                    """
                                    cursor_edit.execute(upd_query, (
                                        edit_alias.strip(), edit_servicios.strip(), int(edit_cpu), int(edit_ram), 
                                        int(edit_d1), int(edit_d2), int(edit_d3), int(edit_d4), int(edit_d5), int(edit_d6),
                                        int(edit_s1), int(edit_s2), int(edit_s3), int(edit_s4), int(edit_s5),
                                        int(edit_s6), int(edit_s7), int(edit_s8),
                                        int(edit_red_tot), int(edit_red_ent), int(edit_red_sal), int(edit_lat), ip_edit
                                    ))
                                    conn_edit.commit()
                                    st.success("✅ Estructura modificada con éxito en la base de datos.")
                                    st.session_state.accion_infra = None
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"❌ Error al actualizar: {ex}")
                                finally:
                                    if cursor_edit: cursor_edit.close()
                                    if conn_edit: conn_edit.close()
                                    
                            if col_btn_edi2.form_submit_button("❌ Cancelar Modificación", use_container_width=True):
                                st.session_state.accion_infra = None
                                st.rerun()

                elif st.session_state.accion_infra == "desactivar" and hay_filtro and not ver_todos:
                    st.markdown("### ⚠️ Suspensión Lógica de Monitoreo")
                    with st.form("form_baja_srv"):
                        ip_des = st.selectbox("Seleccione Servidor a cambio de estado", lista_ips)
                        srv_baja = mapeo_servidores[ip_des]
                        estado_actual_str = "ACTIVO" if srv_baja['estado_monitoreo'] == 1 else "INACTIVO"
                        
                        st.info(f"ℹ️ Estado de monitoreo actual en la granja: **{estado_actual_str}**")
                        nuevo_est_bit = st.selectbox("Seleccione Nuevo Estado Lógico", ["Desactivar Monitoreo", "Activar Monitoreo"])
                        
                        col_btn_des1, col_btn_des2 = st.columns(2)
                        if col_btn_des1.form_submit_button("⚖️ Confirmar Estado", use_container_width=True):
                            bit_val = 0 if "Desactivar" in nuevo_est_bit else 1
                            try:
                                conn_status = conectar_bd()
                                cursor_status = conn_status.cursor()
                                cursor_status.execute("UPDATE servidores SET estado_monitoreo=%s WHERE ip=%s", (bit_val, ip_des))
                                conn_status.commit()
                                st.success(f"✅ Nodo {ip_des} actualizado con éxito.")
                                st.session_state.accion_infra = None
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ Error: {ex}")
                            finally:
                                if cursor_status: cursor_status.close()
                                if conn_status: conn_status.close()

            if es_seguridad and not hay_filtro:
                if st.button("➕ Registrar Servidor", use_container_width=True, key="btn_crud_registrar"):
                    st.session_state.accion_infra = "registrar"
                    st.rerun()

            if st.session_state.accion_infra == "registrar" and not hay_filtro:
                st.markdown("### 📥 Registrar Nuevo Servidor Institucional")
                with st.form("form_registro_srv"):
                    st.markdown("<div class='subtitulo-formulario'>📋 Datos Principales del Nodo</div>", unsafe_allow_html=True)
                    
                    col_reg_p1, col_reg_p2 = st.columns(2)
                    reg_ip = col_reg_p1.text_input("Dirección IP (Campo Requerido)", placeholder="Ej: 10.10.1.50")
                    reg_alias = col_reg_p2.text_input("Nombre / Alias del Servidor (Requerido)", placeholder="Ej: SRV-PROD-BD")
                    
                    col_reg_p3, col_reg_p4 = st.columns(2)
                    reg_so = col_reg_p3.selectbox("Sistema Operativo Base Instalado", ["Windows", "Linux", "No especificado"])
                    reg_tipo = col_reg_p4.selectbox("Tipo de Infraestructura", ["Virtual", "Fisico", "No especificado"])
                    
                    st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                    col_reg_e1, col_reg_e2 = st.columns(2)
                    reg_cpu = col_reg_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=0, step=None)
                    reg_ram = col_reg_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=0, step=None)
                    
                    col_reg_e3, col_reg_e4 = st.columns(2)
                    reg_lat = col_reg_e3.number_input("ID Sensor PRTG - Latencia de Respuesta (Ping)", value=0, step=None)
                    reg_servicios_str = col_reg_e4.text_input("Descripción de Servicios Core", value="Ninguno")
                    
                    st.markdown("<div class='subtitulo-formulario'>🌐 Sensores de Red Distribuidos</div>", unsafe_allow_html=True)
                    col_red1, col_red2, col_red3 = st.columns(3)
                    reg_red_tot = col_red1.number_input("ID Red - Tráfico Total", value=0, step=None)
                    reg_red_ent = col_red2.number_input("ID Red - Tráfico Entrante", value=0, step=None)
                    reg_red_sal = col_red3.number_input("ID Red - Tráfico Saliente", value=0, step=None)

                    st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                    col_d1, col_d2, col_d3 = st.columns(3)
                    reg_d1 = col_d1.number_input("Disco 1 (Unidad C:\\)", value=0, step=None)
                    reg_d2 = col_d2.number_input("Disco 2 (Unidad D:\\)", value=0, step=None)
                    reg_d3 = col_d3.number_input("Disco 3 (Unidad E:\\)", value=0, step=None)
                    
                    col_d4, col_d5, col_d6 = st.columns(3)
                    reg_d4 = col_d4.number_input("Disco 4 (Unidad F:\\)", value=0, step=None)
                    reg_d5 = col_d5.number_input("Disco 5 (Unidad G:\\)", value=0, step=None)
                    reg_d6 = col_d6.number_input("Disco 6 (Unidad Y:\\)", value=0, step=None)

                    st.markdown("<div class='subtitulo-formulario'>⚙️ Sensores de Servicio Activos (8 Slots)</div>", unsafe_allow_html=True)
                    col_s1, col_s2 = st.columns(2)
                    reg_s1 = col_s1.number_input("ID Sensor - Servicio Sistema 1", value=0, step=None)
                    reg_s2 = col_s2.number_input("ID Sensor - Servicio Sistema 2", value=0, step=None)
                    
                    col_s3, col_s4, col_s5 = st.columns(3)
                    reg_s3 = col_s3.number_input("ID Sensor - Servicio 3", value=0, step=None)
                    reg_s4 = col_s4.number_input("ID Sensor - Servicio 4", value=0, step=None)
                    reg_s5 = col_s5.number_input("ID Sensor - Servicio 5", value=0, step=None)
                    
                    col_s6, col_s7, col_s8 = st.columns(3)
                    reg_s6 = col_s6.number_input("ID Sensor - Servicio 6", value=0, step=None)
                    reg_s7 = col_s7.number_input("ID Sensor - Servicio 7", value=0, step=None)
                    reg_s8 = col_s8.number_input("ID Sensor - Servicio 8", value=0, step=None)
                    
                    col_btn_reg1, col_btn_reg2 = st.columns(2)
                    
                    if col_btn_reg1.form_submit_button("💾 Guardar Servidor", use_container_width=True):
                        if not reg_ip.strip() or not reg_alias.strip():
                            st.error("❌ Error: La Dirección IP y el nombre son campos obligatorios.")
                        elif not validar_ip(reg_ip):
                            st.error("❌ Error: El formato de la Dirección IP no es válido.")
                        else:
                            try:
                                conn_write = conectar_bd()
                                cursor_write = conn_write.cursor()
                                ins_query = """
                                    INSERT INTO servidores (
                                        ip, nombre_alias, sistema_operativo, tipo, servicios,
                                        id_sensor_cpu, id_sensor_ram, id_sensor_latencia,
                                        id_sensor_red_total, id_sensor_red_entrante, id_sensor_red_saliente,
                                        id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3,
                                        id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                                        id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3,
                                        id_sensor_servicio_4, id_sensor_servicio_5, id_sensor_servicio_6,
                                        id_sensor_servicio_7, id_sensor_servicio_8,
                                        estado_monitoreo
                                    ) VALUES (
                                        %s, %s, %s, %s, %s,
                                        %s, %s, %s,
                                        %s, %s, %s,
                                        %s, %s, %s, %s, %s, %s,
                                        %s, %s, %s, %s, %s, %s, %s, %s,
                                        1
                                    )
                                """
                                cursor_write.execute(ins_query, (
                                    reg_ip.strip(), reg_alias.strip(), reg_so, reg_tipo, reg_servicios_str.strip(),
                                    int(reg_cpu), int(reg_ram), int(reg_lat),
                                    int(reg_red_tot), int(reg_red_ent), int(reg_red_sal),
                                    int(reg_d1), int(reg_d2), int(reg_d3), int(reg_d4), int(reg_d5), int(reg_d6),
                                    int(reg_s1), int(reg_s2), int(reg_s3), int(reg_s4), int(reg_s5),
                                    int(reg_s6), int(reg_s7), int(reg_s8)
                                ))
                                conn_write.commit()
                                st.success("✅ Servidor añadido al catálogo institucional con éxito.")
                                st.session_state.accion_infra = None
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ Error de persistencia: {ex}")
                            finally:
                                if cursor_write: cursor_write.close()
                                if conn_write: conn_write.close()
                                
                    if col_btn_reg2.form_submit_button("❌ Cancelar Operación", use_container_width=True):
                        st.session_state.accion_infra = None
                        st.rerun()
                
        except Exception as e:
            st.error(f"❌ Fallo técnico al procesar el módulo de servidores: {e}")
        finally:
            if cursor:
                try: cursor.close()
                except: pass
            if conn:
                try: conn.close()
                except: pass

    with tab2:
        renderizar_pestana_datos_adicionales(es_seguridad)


if __name__ == "__main__":
    mostrar_tabla_servidores()