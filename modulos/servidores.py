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

def limpiar_estados_servidores():
    """Limpia los estados de los filtros de servidores"""
    keys_to_clear = [
        'filtro_servidor_nombre',
        'filtro_aplicado_srv',
        'accion_infra',
        'filtro_adicional_nombre',
        'accion_adicional',
        'tab_servidores_activa',
        'sb_filtro_p1',
        'sb_filtro_ad',
        '_widget_key_srv',
        '_widget_key_ad'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Resetear valores por defecto
    st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
    st.session_state["filtro_aplicado_srv"] = False
    st.session_state["accion_infra"] = None
    st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
    st.session_state["accion_adicional"] = None
    st.session_state["tab_servidores_activa"] = 0

def limpiar_estado_capacity():
    keys_to_clear = [
        'p1_servidor', 'p1_metrica', 'p1_dias', 'p1_ajuste',
        'p1_filtros_aplicados', 'p1_reporte_generado',
        'p2_servidor_seleccionado', 'p2_metrica_filtro',
        'p2_formato_filtro', 'p2_mostrar_tabla',
        'modulo_capacity_activo'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# ==========================================================================
# FRAGMENTO PARA LA PESTAÑA 2 - DATOS ADICIONALES
# ==========================================================================
@st.fragment
def renderizar_pestana_datos_adicionales(es_seguridad):
    """Fragmento independiente para la pestaña de datos adicionales"""
    
    if "_widget_key_ad" not in st.session_state:
        st.session_state["_widget_key_ad"] = f"sb_filtro_ad_{int(time.time() * 1000)}"
    
    st.markdown('<h3 style="color:#003366;">📋 Control de Parámetros Adicionales</h3>', unsafe_allow_html=True)
    
    if "filtro_adicional_nombre" not in st.session_state:
        st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
    if "filtro_aplicado_ad" not in st.session_state:
        st.session_state.filtro_aplicado_ad = False
    if "accion_adicional" not in st.session_state:
        st.session_state.accion_adicional = None

    conn_ad = None
    cursor_ad = None
    
    try:
        lista_nombres_bd_ad = obtener_lista_nombres_servidores()
        opciones_selectbox_ad = ["-- Seleccione un Servidor Base --", "-- Ver Todos los Servidores Base --"] + lista_nombres_bd_ad

        conn_ad = conectar_bd()
        cursor_ad = conn_ad.cursor(dictionary=True)
        
        col_f_ad1, col_f_ad2, col_f_ad3 = st.columns([3, 1, 1])
        
        with col_f_ad1:
            current_value = st.session_state.get("filtro_adicional_nombre", "-- Seleccione un Servidor Base --")
            current_index = 0
            
            if current_value in opciones_selectbox_ad:
                current_index = opciones_selectbox_ad.index(current_value)
            else:
                st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
                current_index = 0
            
            selected_value = st.selectbox(
                "Filtrar Servidor Base",
                options=opciones_selectbox_ad,
                index=current_index,
                key=st.session_state["_widget_key_ad"],
                label_visibility="collapsed"
            )
            st.session_state["filtro_adicional_nombre"] = selected_value
        
        with col_f_ad2:
            if st.button("🔍 Filtrar", key="btn_filtrar_ad", use_container_width=True):
                st.session_state.filtro_aplicado_ad = True
                st.rerun(scope="fragment")
        
        with col_f_ad3:
            if st.button("🧹 Limpiar", key="btn_limpiar_filtro_ad", use_container_width=True):
                st.session_state["_widget_key_ad"] = f"sb_filtro_ad_{int(time.time() * 1000)}"
                st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
                st.session_state.filtro_aplicado_ad = False
                st.session_state.accion_adicional = None
                st.rerun(scope="fragment")

        st.markdown("---")

        hay_filtro_ad = st.session_state.filtro_aplicado_ad and st.session_state["filtro_adicional_nombre"] != "-- Seleccione un Servidor Base --"
        ver_todos_ad = st.session_state["filtro_adicional_nombre"] == "-- Ver Todos los Servidores Base --"
        
        registros_adicionales = []
        mapeo_adicionales = {}
        lista_ids_adicionales = []
        
        cursor_ad.execute("SELECT id_servidor, ip, nombre_alias FROM servidores ORDER BY nombre_alias ASC")
        servidores_maestros = cursor_ad.fetchall()
        opciones_srv_map = {f"{s['nombre_alias']} ({s['ip']})": s['id_servidor'] for s in servidores_maestros}

        if not st.session_state.filtro_aplicado_ad:
            st.info("🔍 Seleccione un servidor y presione 'Filtrar' para visualizar los parámetros adicionales.")
        elif not hay_filtro_ad:
            st.info("📋 Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus parámetros adicionales.")
        else:
            query_base = """
                SELECT da.id, da.id_servidor, s.nombre_alias, s.ip AS ip_maestra, da.host, da.nombre_vm, 
                       da.estado, da.uso_cpu_pct, da.memoria_asignada_mb, da.tiempo_encendido, 
                       da.nombre_switch, da.direccion_mac, da.direcciones_ip, da.version, 
                       da.tamano_gb, da.amount_vhd, da.funcion
                FROM datos_adicionales da
                INNER JOIN servidores s ON da.id_servidor = s.id_servidor
                WHERE 1=1
            """
            params = []
            
            if hay_filtro_ad and not ver_todos_ad:
                query_base += " AND s.nombre_alias = %s"
                params.append(st.session_state["filtro_adicional_nombre"])
            
            query_base += " ORDER BY s.nombre_alias ASC, da.id DESC"
            
            cursor_ad.execute(query_base, params)
            registros_adicionales = cursor_ad.fetchall()
            
            for r in registros_adicionales:
                str_id = str(r['id'])
                lista_ids_adicionales.append(str_id)
                mapeo_adicionales[str_id] = r
        
        if st.session_state.filtro_aplicado_ad and hay_filtro_ad:
            if not registros_adicionales:
                st.warning("📭 No se encuentran datos registrados para el servidor seleccionado.")
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
                
                for r in registros_adicionales:
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
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                if st.session_state.accion_adicional is None:
                    if st.button("➕ Registrar Parámetro", use_container_width=True, key="btn_ad_crear"):
                        st.session_state.accion_adicional = "registrar"
                        st.rerun(scope="fragment")
            
            with col_b2:
                if registros_adicionales and st.session_state.accion_adicional is None:
                    if st.button("✏️ Editar Parámetro", use_container_width=True, key="btn_ad_editar"):
                        st.session_state.accion_adicional = "editar"
                        st.rerun(scope="fragment")

        if st.session_state.accion_adicional == "registrar":
            st.markdown("### 📥 Registrar Extensión de Infraestructura")
            with st.form("form_registro_adicional"):
                col_r1, col_r2 = st.columns(2)
                srv_combo = col_r1.selectbox("Servidor Maestro Relacionado", list(opciones_srv_map.keys()))
                
                col_r3, col_r4 = st.columns(2)
                ad_host = col_r3.text_input("Host Físico Hospedador", placeholder="Ej: SRV-HOST-01")
                ad_servidor = col_r4.text_input("Nombre del Servidor", placeholder="Ej: SRV-WEB-01")
                
                col_r5, col_r6 = st.columns(2)
                ad_estado = col_r5.selectbox("Estado Actual", ["Running", "OFF", "ACTIVO", "INACTIVO"])
                ad_funcion = col_r6.text_input("Rol / Función Operativa", placeholder="Ej: Servidor Web")
                
                st.markdown("---")
                st.markdown("#### 📊 Métricas de Rendimiento")
                
                st.markdown("""
                <style>
                    div[data-testid="column"] .stNumberInput {
                        margin-top: 0px !important;
                        padding-top: 0px !important;
                    }
                    div[data-testid="column"] .stTextInput {
                        margin-top: 0px !important;
                        padding-top: 0px !important;
                    }
                    div[data-testid="column"] .stNumberInput > div {
                        margin-top: 0px !important;
                    }
                    div[data-testid="column"] .stTextInput > div {
                        margin-top: 0px !important;
                    }
                    div[data-testid="column"] label {
                        display: block !important;
                        margin-bottom: 4px !important;
                        font-weight: 500 !important;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                col_r7, col_r8, col_r9 = st.columns(3)
                with col_r7:
                    ad_cpu = st.number_input("Uso CPU (%)", value=0, min_value=0, max_value=100, step=1)
                with col_r8:
                    ad_ram = st.number_input("Memoria Asignada (MB)", value=0, min_value=0, step=100)
                with col_r9:
                    ad_tiempo = st.text_input("Tiempo Encendido", placeholder="Ej: 30 días 5 horas")
                
                st.markdown("---")
                st.markdown("#### 🌐 Configuración de Red")
                
                col_r10, col_r11 = st.columns(2)
                ad_switch = col_r10.text_input("Nombre del Switch", placeholder="Ej: SW-CORE-01")
                ad_mac = col_r11.text_input("Dirección MAC", placeholder="Ej: 00:1A:2B:3C:4D:5E")
                
                col_r12, col_r13 = st.columns(2)
                ad_ips = col_r12.text_input("Direcciones IP", placeholder="Ej: 10.10.1.100, 10.10.1.101")
                ad_version = col_r13.text_input("Versión", placeholder="Ej: v1.0, 2023.1")
                
                st.markdown("---")
                st.markdown("#### 💾 Almacenamiento")
                
                col_r14, col_r15 = st.columns(2)
                ad_tamano = col_r14.number_input("Tamaño (GB)", value=0.00, min_value=0.00, step=1.00, format="%.2f")
                ad_amount_vhd = col_r15.number_input("Cantidad VHD", value=0, min_value=0, step=1)
                
                col_btn_ar1, col_btn_ar2 = st.columns(2)
                if col_btn_ar1.form_submit_button("💾 Registrar", use_container_width=True):
                    if not ad_host.strip() or not ad_servidor.strip():
                        st.error("❌ Los campos Host Físico y Nombre del Servidor son obligatorios.")
                    else:
                        try:
                            id_srv_target = opciones_srv_map[srv_combo]
                            query_ins = """
                                INSERT INTO datos_adicionales (
                                    id_servidor, host, nombre_vm, estado, uso_cpu_pct, 
                                    memoria_asignada_mb, tiempo_encendido, nombre_switch, 
                                    direccion_mac, direcciones_ip, version, tamano_gb, 
                                    amount_vhd, funcion
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """
                            cursor_ad.execute(query_ins, (
                                id_srv_target, 
                                ad_host.strip(), 
                                ad_servidor.strip(), 
                                ad_estado, 
                                int(ad_cpu),
                                int(ad_ram), 
                                ad_tiempo.strip() if ad_tiempo else None,
                                ad_switch.strip() if ad_switch else None,
                                ad_mac.strip() if ad_mac else None,
                                ad_ips.strip() if ad_ips else None,
                                ad_version.strip() if ad_version else None,
                                float(ad_tamano),
                                int(ad_amount_vhd),
                                ad_funcion.strip() if ad_funcion else None
                            ))
                            conn_ad.commit()
                            st.success("✅ Registro adicional completado exitosamente.")
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
                    col_e1, col_e2 = st.columns(2)
                    edit_host = col_e1.text_input("Host Físico Hospedador", value=ad_actual['host'] or '')
                    edit_servidor = col_e2.text_input("Nombre del Servidor", value=ad_actual['nombre_vm'] or '')
                    
                    col_e3, col_e4 = st.columns(2)
                    edit_estado = col_e3.selectbox("Estado Actual", ["Running", "OFF", "ACTIVO", "INACTIVO"], 
                                                   index=["Running", "OFF", "ACTIVO", "INACTIVO"].index(ad_actual['estado']) if ad_actual['estado'] in ["Running", "OFF", "ACTIVO", "INACTIVO"] else 0)
                    edit_funcion = col_e4.text_input("Rol / Función Operativa", value=ad_actual['funcion'] or '')
                    
                    st.markdown("---")
                    st.markdown("#### 📊 Métricas de Rendimiento")
                    
                    st.markdown("""
                    <style>
                        div[data-testid="column"] .stNumberInput {
                            margin-top: 0px !important;
                            padding-top: 0px !important;
                        }
                        div[data-testid="column"] .stTextInput {
                            margin-top: 0px !important;
                            padding-top: 0px !important;
                        }
                        div[data-testid="column"] .stNumberInput > div {
                            margin-top: 0px !important;
                        }
                        div[data-testid="column"] .stTextInput > div {
                            margin-top: 0px !important;
                        }
                        div[data-testid="column"] label {
                            display: block !important;
                            margin-bottom: 4px !important;
                            font-weight: 500 !important;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    col_e5, col_e6, col_e7 = st.columns(3)
                    with col_e5:
                        edit_cpu = st.number_input("Uso CPU (%)", value=int(ad_actual['uso_cpu_pct'] or 0), min_value=0, max_value=100, step=1)
                    with col_e6:
                        edit_ram = st.number_input("Memoria Asignada (MB)", value=int(ad_actual['memoria_asignada_mb'] or 0), min_value=0, step=100)
                    with col_e7:
                        edit_tiempo = st.text_input("Tiempo Encendido", value=ad_actual['tiempo_encendido'] or '')
                    
                    st.markdown("---")
                    st.markdown("#### 🌐 Configuración de Red")
                    
                    col_e8, col_e9 = st.columns(2)
                    edit_switch = col_e8.text_input("Nombre del Switch", value=ad_actual['nombre_switch'] or '')
                    edit_mac = col_e9.text_input("Dirección MAC", value=ad_actual['direccion_mac'] or '')
                    
                    col_e10, col_e11 = st.columns(2)
                    edit_ips = col_e10.text_input("Direcciones IP", value=ad_actual['direcciones_ip'] or '')
                    edit_version = col_e11.text_input("Versión", value=ad_actual['version'] or '')
                    
                    st.markdown("---")
                    st.markdown("#### 💾 Almacenamiento")
                    
                    col_e12, col_e13 = st.columns(2)
                    edit_tamano = col_e12.number_input("Tamaño (GB)", value=float(ad_actual['tamano_gb'] or 0.00), min_value=0.00, step=1.00, format="%.2f")
                    edit_amount_vhd = col_e13.number_input("Cantidad VHD", value=int(ad_actual['amount_vhd'] or 0), min_value=0, step=1)
                    
                    col_btn_ae1, col_btn_ae2 = st.columns(2)
                    if col_btn_ae1.form_submit_button("✏️ Actualizar", use_container_width=True):
                        try:
                            query_upd = """
                                UPDATE datos_adicionales 
                                SET host=%s, nombre_vm=%s, estado=%s, uso_cpu_pct=%s, 
                                    memoria_asignada_mb=%s, tiempo_encendido=%s, 
                                    nombre_switch=%s, direccion_mac=%s, direcciones_ip=%s, 
                                    version=%s, tamano_gb=%s, amount_vhd=%s, funcion=%s 
                                WHERE id=%s
                            """
                            cursor_ad.execute(query_upd, (
                                edit_host.strip(), 
                                edit_servidor.strip(), 
                                edit_estado, 
                                int(edit_cpu),
                                int(edit_ram), 
                                edit_tiempo.strip() if edit_tiempo else None,
                                edit_switch.strip() if edit_switch else None,
                                edit_mac.strip() if edit_mac else None,
                                edit_ips.strip() if edit_ips else None,
                                edit_version.strip() if edit_version else None,
                                float(edit_tamano),
                                int(edit_amount_vhd),
                                edit_funcion.strip() if edit_funcion else None,
                                int(id_ad_edit)
                            ))
                            conn_ad.commit()
                            st.success("✅ Registro actualizado exitosamente.")
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

    if "redirigir_servidor" in st.session_state and st.session_state["redirigir_servidor"]:
        servidor = st.session_state["redirigir_servidor"]
        if servidor and servidor != "-- Seleccione un Servidor --":
            logging.info(f"🔍 Redirigiendo a servidor: {servidor}")
            st.session_state["redirigir_servidor"] = None
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

    if "_widget_key_srv" not in st.session_state:
        st.session_state["_widget_key_srv"] = f"sb_filtro_p1_{int(time.time() * 1000)}"
    
    if "filtro_servidor_nombre" not in st.session_state:
        st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
    if "accion_infra" not in st.session_state:
        st.session_state.accion_infra = None
    if "filtro_aplicado_srv" not in st.session_state:
        st.session_state.filtro_aplicado_srv = False

    tab1, tab2 = st.tabs(["📊 Infraestructura y Sensores", "⚙️ Datos Adicionales"])

    with tab1:
        st.session_state.tab_servidores_activa = 0
        if not st.session_state.get("_en_monitoreo", False):
            if st.query_params.get("tab_servidores") != "1":
                st.query_params["tab_servidores"] = "1"

        conn = None
        cursor = None

        try:
            lista_nombres_bd = obtener_lista_nombres_servidores()
            opciones_selectbox = ["-- Seleccione un Servidor --", "-- Ver Todos los Servidores --"] + lista_nombres_bd

            col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
            
            with col_f1:
                current_value = st.session_state.get("filtro_servidor_nombre", "-- Seleccione un Servidor --")
                current_index = 0
                
                if current_value in opciones_selectbox:
                    current_index = opciones_selectbox.index(current_value)
                else:
                    st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
                    current_index = 0
                
                selected_value = st.selectbox(
                    "Filtrar Servidor por Nombre",
                    options=opciones_selectbox,
                    index=current_index,
                    key=st.session_state["_widget_key_srv"],
                    label_visibility="collapsed"
                )
                st.session_state["filtro_servidor_nombre"] = selected_value
            
            with col_f2:
                if st.button("🔍 Filtrar", key="btn_filtrar_srv", use_container_width=True):
                    st.session_state.filtro_aplicado_srv = True
                    st.rerun()
            
            with col_f3:
                if st.button("🧹 Limpiar", key="btn_limpiar_filtro_srv", use_container_width=True):
                    st.session_state["_widget_key_srv"] = f"sb_filtro_p1_{int(time.time() * 1000)}"
                    st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
                    st.session_state.filtro_aplicado_srv = False
                    st.session_state.accion_infra = None
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
                html_lineas.append('<th>SERVICIOS</th>')
                
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
                    
                    servicios_valor = s.get('servicios', 'Ninguno') or 'Ninguno'
                    servicios_mostrar = servicios_valor

                    html_lineas.append('<tr>')
                    html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                    html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                    html_lineas.append(f'<td>{s["sistema_operativo"]}</td>')
                    html_lineas.append(f'<td>{s.get("tipo", "Virtual")}</td>')
                    html_lineas.append(f'<td>{servicios_mostrar}</td>')
                    
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
                st.markdown("### 📊 Ver Monitoreo")
                
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
                            limpiar_estados_servidores()
                            
                            st.session_state["_srv_redirect_pending"] = nombre_servidor
                            st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
                            st.query_params.clear()
                            st.query_params["srv"] = nombre_servidor
                            st.query_params["p"] = "🖥️ Monitoreo en vivo"
                            st.query_params["s"] = "1"
                            st.query_params["rol"] = st.session_state.get("rol", "seguridad")
                            st.query_params["uid"] = str(st.session_state.get("user_id", 1))
                            st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
                            st.query_params["c"] = st.session_state.get("cargo", "Analista")
                            st.rerun()

                st.markdown("---")

                if not es_seguridad:
                    st.info("ℹ️ **Modo Consulta Activo:** Su perfil de Operador permite verificar la infraestructura pero no dispone de privilegios para modificar el catálogo.")
                else:
                    if not ver_todos:
                        col_b1, col_b2 = st.columns(2)
                        if col_b1.button("✏️ Editar Servidor", use_container_width=True, key="btn_crud_editar"):
                            st.session_state.accion_infra = "editar"
                            st.rerun()
                        if col_b2.button("❌ Desactivar", use_container_width=True, key="btn_crud_desactivar"):
                            st.session_state.accion_infra = "desactivar"
                            st.rerun()

                if st.session_state.accion_infra == "editar" and hay_filtro and not ver_todos:
                    st.markdown("### ✏️ Modificación de Parámetros Técnicos")
                    
                    # Usar el servidor filtrado directamente (solo hay uno)
                    srv_actual = servidores_filtrados[0]
                    fecha_act = srv_actual['fecha_alta'].strftime("%Y-%m-%d %H:%M") if srv_actual['fecha_alta'] else "N/A"
                    
                    with st.form("form_edicion_srv"):
                        # ✅ CAMBIO: Sección de información base bloqueada con 3 columnas (agregado "Tipo")
                        st.markdown("<div class='subtitulo-formulario'>🔒 Información Base Bloqueada</div>", unsafe_allow_html=True)
                        col_lock1, col_lock2, col_lock3 = st.columns(3)
                        col_lock1.text_input("Fecha de Alta Institucional", value=fecha_act, disabled=True)
                        col_lock2.text_input("Sistema Operativo Asignado", value=srv_actual['sistema_operativo'], disabled=True)
                        col_lock3.text_input("Tipo de Infraestructura", value=srv_actual.get('tipo', 'Virtual'), disabled=True)
                        
                        st.markdown("<div class='subtitulo-formulario'>📋 Identificación Comercial</div>", unsafe_allow_html=True)
                        col_edi_p1, col_edi_p2 = st.columns(2)
                        edit_alias = col_edi_p1.text_input("Alias / Nombre Comercial del Servidor", value=srv_actual['nombre_alias'])
                        edit_servicios = col_edi_p2.text_input("Servicios del Servidor", value=srv_actual.get('servicios', 'Ninguno'))
                        
                        st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                        col_e1, col_e2 = st.columns(2)
                        edit_cpu = col_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=int(srv_actual['id_sensor_cpu']), step=None)
                        edit_ram = col_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=int(srv_actual['id_sensor_ram']), step=None)
                        edit_lat = st.number_input("ID Sensor PRTG - Latencia (Ping)", value=int(srv_actual['id_sensor_latencia']), step=None)
                        
                        st.markdown("<div class='subtitulo-formulario'>🌐 Sensor de Red Unificado</div>", unsafe_allow_html=True)
                        edit_red_unica = st.number_input("ID Sensor PRTG - Red (Total/Entrada/Salida)", value=int(srv_actual.get('id_sensor_red_total', 0)), step=None)

                        st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                        col_d1, col_d2, col_d3 = st.columns(3)
                        edit_d1 = col_d1.number_input(r"Disco 1 (Unidad C:\)", value=int(srv_actual['id_sensor_disco_1']), step=None)
                        edit_d2 = col_d2.number_input(r"Disco 2 (Unidad D:\)", value=int(srv_actual['id_sensor_disco_2']), step=None)
                        edit_d3 = col_d3.number_input(r"Disco 3 (Unidad E:\)", value=int(srv_actual['id_sensor_disco_3']), step=None)
                        
                        col_d4, col_d5, col_d6 = st.columns(3)
                        edit_d4 = col_d4.number_input(r"Disco 4 (Unidad F:\)", value=int(srv_actual['id_sensor_disco_4']), step=None)
                        edit_d5 = col_d5.number_input(r"Disco 5 (Unidad G:\)", value=int(srv_actual['id_sensor_disco_5']), step=None)
                        edit_d6 = col_d6.number_input(r"Disco 6 (Unidad Y:\)", value=int(srv_actual.get('id_sensor_disco_6', 0)), step=None)

                        st.markdown("<div class='subtitulo-formulario'>⚙️ Sensores de Servicio Activos (8 Slots Ampliados)</div>", unsafe_allow_html=True)
                        col_s1, col_s2 = st.columns(2)
                        edit_s1 = col_s1.number_input("ID Sensor - Servicio 1", value=int(srv_actual.get('id_sensor_servicio_1', 0)), step=None)
                        edit_s2 = col_s2.number_input("ID Sensor - Servicio 2", value=int(srv_actual.get('id_sensor_servicio_2', 0)), step=None)
                        
                        col_s3, col_s4, col_s5 = st.columns(3)
                        edit_s3 = col_s3.number_input("ID Sensor - Servicio 3", value=int(srv_actual.get('id_sensor_servicio_3', 0)), step=None)
                        edit_s4 = col_s4.number_input("ID Sensor - Servicio 4", value=int(srv_actual.get('id_sensor_servicio_4', 0)), step=None)
                        edit_s5 = col_s5.number_input("ID Sensor - Servicio 5", value=int(srv_actual.get('id_sensor_servicio_5', 0)), step=None)
                        
                        col_s6, col_s7, col_s8 = st.columns(3)
                        edit_s6 = col_s6.number_input("ID Sensor - Servicio 6", value=int(srv_actual.get('id_sensor_servicio_6', 0)), step=None)
                        edit_s7 = col_s7.number_input("ID Sensor - Servicio 7", value=int(srv_actual.get('id_sensor_servicio_7', 0)), step=None)
                        edit_s8 = col_s8.number_input("ID Sensor - Servicio 8", value=int(srv_actual.get('id_sensor_servicio_8', 0)), step=None)
                        
                        col_btn_edi1, col_btn_edi2 = st.columns(2)
                        if col_btn_edi1.form_submit_button("💾 Actualizar", use_container_width=True):
                            try:
                                conn_edit = conectar_bd()
                                cursor_edit = conn_edit.cursor()
                                ip_edit = srv_actual['ip']
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
                                    int(edit_red_unica), int(edit_red_unica), int(edit_red_unica), int(edit_lat), ip_edit
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
                                
                        if col_btn_edi2.form_submit_button("❌ Cancelar", use_container_width=True):
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
                    
                    # ✅ CAMBIO: Selector de Tipo de Infraestructura (Virtual/físico)
                    col_reg_p3, col_reg_p4 = st.columns(2)
                    reg_so = col_reg_p3.selectbox("Sistema Operativo Base Instalado", ["Windows", "Linux", "No especificado"])
                    reg_tipo = col_reg_p4.selectbox("Tipo de Infraestructura", ["Virtual", "físico"], index=0)
                    
                    st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                    col_reg_e1, col_reg_e2 = st.columns(2)
                    reg_cpu = col_reg_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=0, step=None)
                    reg_ram = col_reg_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=0, step=None)
                    
                    col_reg_e3, col_reg_e4 = st.columns(2)
                    reg_lat = col_reg_e3.number_input("ID Sensor PRTG - Latencia de Respuesta (Ping)", value=0, step=None)
                    reg_servicios_str = col_reg_e4.text_input("Servicios del Servidor", value="Ninguno")
                    
                    st.markdown("<div class='subtitulo-formulario'>🌐 Sensor de Red Unificado</div>", unsafe_allow_html=True)
                    reg_red_unica = st.number_input("ID Sensor PRTG - Red (Total/Entrada/Salida)", value=0, step=None)

                    st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                    col_d1, col_d2, col_d3 = st.columns(3)
                    reg_d1 = col_d1.number_input(r"Disco 1 (Unidad C:\)", value=0, step=None)
                    reg_d2 = col_d2.number_input(r"Disco 2 (Unidad D:\)", value=0, step=None)
                    reg_d3 = col_d3.number_input(r"Disco 3 (Unidad E:\)", value=0, step=None)
                    
                    col_d4, col_d5, col_d6 = st.columns(3)
                    reg_d4 = col_d4.number_input(r"Disco 4 (Unidad F:\)", value=0, step=None)
                    reg_d5 = col_d5.number_input(r"Disco 5 (Unidad G:\)", value=0, step=None)
                    reg_d6 = col_d6.number_input(r"Disco 6 (Unidad Y:\)", value=0, step=None)

                    st.markdown("<div class='subtitulo-formulario'>⚙️ Sensores de Servicio Activos (8 Slots)</div>", unsafe_allow_html=True)
                    col_s1, col_s2 = st.columns(2)
                    reg_s1 = col_s1.number_input("ID Sensor - Servicio 1", value=0, step=None)
                    reg_s2 = col_s2.number_input("ID Sensor - Servicio 2", value=0, step=None)
                    
                    col_s3, col_s4, col_s5 = st.columns(3)
                    reg_s3 = col_s3.number_input("ID Sensor - Servicio 3", value=0, step=None)
                    reg_s4 = col_s4.number_input("ID Sensor - Servicio 4", value=0, step=None)
                    reg_s5 = col_s5.number_input("ID Sensor - Servicio 5", value=0, step=None)
                    
                    col_s6, col_s7, col_s8 = st.columns(3)
                    reg_s6 = col_s6.number_input("ID Sensor - Servicio 6", value=0, step=None)
                    reg_s7 = col_s7.number_input("ID Sensor - Servicio 7", value=0, step=None)
                    reg_s8 = col_s8.number_input("ID Sensor - Servicio 8", value=0, step=None)
                    
                    col_btn_reg1, col_btn_reg2 = st.columns(2)
                    
                    if col_btn_reg1.form_submit_button("💾 Registrar", use_container_width=True):
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
                                    int(reg_red_unica), int(reg_red_unica), int(reg_red_unica),
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