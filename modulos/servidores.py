import streamlit as st
from database import conectar_bd
import re

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

def mostrar_tabla_servidores(rol_usuario=None):
    """
    Renderiza el catálogo de servidores de forma optimizada.
    Filtra mediante un menú desplegable ágil asistido por caché de datos.
    Oculta dinámicamente las columnas cuyos sensores no estén asignados (valor 0).
    Redirecciona limpiamente mediante un botón corporativo externo exclusivo.
    Soporta estructuralmente hasta 6 discos (con Disco 6 mapeado a Y:), 8 sensores de servicios y la columna tipo V3.6.
    Pestaña 2 interactiva: Permite listar, registrar y editar la tabla datos_adicionales de forma exacta,
    asistido por un filtro obligatorio que no muestra datos hasta ser seleccionado.
    """
    # INYECCIÓN DE ESTILOS PERFECCIONADA: ELIMINA LOS BOTONES + Y - DE LOS INPUTS NUMÉRICOS
    st.markdown("""
        <style>
            /* Ajustes de etiquetas dentro de formularios */
            div[data-testid="stForm"] label p {
                font-size: 14px !important;
                font-weight: 600 !important;
                color: #333333 !important;
                margin-bottom: 2px !important;
            }
            
            /* Inputs estilizados con padding interno seguro */
            div[data-testid="stForm"] input {
                padding: 8px 12px !important;
                font-size: 14px !important;
                border-radius: 6px !important;
                height: 42px !important;
            }
            
            /* OCULTAR LOS BOTONES DE + Y - (STEPPER) EN INPUTS NUMÉRICOS DE STREAMLIT */
            input[type=number]::-webkit-inner-spin-button, 
            input[type=number]::-webkit-outer-spin-button { 
                -webkit-appearance: none; 
                margin: 0; 
            }
            input[type=number] {
                -moz-appearance: textfield;
            }
            
            /* Ocultar los botones de incremento específicos creados por Streamlit en versiones recientes */
            div[data-testid="stNumberInput"] button {
                display: none !important;
            }
            
            /* Separadores de sección internos del formulario claramente distanciados */
            .subtitulo-formulario {
                color: #003366;
                margin-top: 25px;
                margin-bottom: 15px;
                border-bottom: 2px solid #ECEFF1;
                padding-bottom: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            
            /* Captura global y homogénea para TODOS los botones internos del formulario */
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
            
            /* Espaciado extra para mitigar colisiones en rejillas densas */
            div[data-testid="stForm"] .stHorizontalBlock {
                padding: 6px 0px !important;
                gap: 12px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # ENCABEZADO CON LA SINTAXIS HOMOLOGADA EN AZUL CORPORATIVO
    # ==========================================================================
    st.markdown('<h2 style="color:#003366;">🖥️ Gestión Servidores</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Normalizamos el rol a mayúsculas para evitar fallas de acceso
    rol_sanitizado = str(rol_usuario).strip().upper() if rol_usuario else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado

    # CREACIÓN DE LAS PESTAÑAS (Con sus iconos originales de vuelta)
    tab1, tab2 = st.tabs(["📊 Infraestructura y Sensores", "⚙️ Datos Adicionales"])

    # ==========================================================================
    # PESTAÑA 1: CONTROL TOTAL DE INFRAESTRUCTURA
    # ==========================================================================
    with tab1:
        if "filtro_servidor_nombre" not in st.session_state:
            st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
        if "accion_infra" not in st.session_state:
            st.session_state.accion_infra = None

        conn = None
        cursor = None

        try:
            lista_nombres_bd = obtener_lista_nombres_servidores()
            opciones_selectbox = ["-- Seleccione un Servidor --"] + lista_nombres_bd

            idx_actual = 0
            if st.session_state["filtro_servidor_nombre"] in opciones_selectbox:
                idx_actual = opciones_selectbox.index(st.session_state["filtro_servidor_nombre"])

            col_f1, col_f2 = st.columns([3, 1])
            
            seleccion = col_f1.selectbox(
                "Filtrar Servidor por Nombre",
                options=opciones_selectbox,
                index=idx_actual,
                key="sb_filtro_p1"
            )
            
            if seleccion != st.session_state["filtro_servidor_nombre"]:
                st.session_state["filtro_servidor_nombre"] = seleccion
                st.session_state.accion_infra = None
                st.rerun()

            col_f2.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
            
            if col_f2.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_limpiar_filtro_srv"):
                st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
                st.session_state.accion_infra = None
                st.query_params.clear() 
                st.rerun()

            hay_filtro = st.session_state["filtro_servidor_nombre"] != "-- Seleccione un Servidor --"
            servidores_filtrados = []

            if not hay_filtro:
                st.info("💡 Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus parámetros técnicos.")
            else:
                conn = conectar_bd()
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT ip, nombre_alias, sistema_operativo, tipo, estado_monitoreo, fecha_alta, 
                           id_sensor_cpu, id_sensor_ram, 
                           id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                           id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                           id_sensor_servicio_6, id_sensor_servicio_7, id_sensor_servicio_8,
                           id_sensor_red, id_sensor_latencia 
                    FROM servidores
                    WHERE nombre_alias = %s
                """
                cursor.execute(query, (st.session_state["filtro_servidor_nombre"],))
                servidores_filtrados = cursor.fetchall()

                if not servidores_filtrados:
                    st.warning("⚠️ No se encontraron registros detallados para el servidor seleccionado.")

            if hay_filtro and servidores_filtrados:
                tiene_cpu = any(s['id_sensor_cpu'] != 0 for s in servidores_filtrados)
                tiene_ram = any(s['id_sensor_ram'] != 0 for s in servidores_filtrados)
                tiene_red = any(s['id_sensor_red'] != 0 for s in servidores_filtrados)
                tiene_latencia = any(s['id_sensor_latencia'] != 0 for s in servidores_filtrados)
                
                discos_activos = {}
                letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:", 6: "Y:"}
                for i in range(1, 7):
                    discos_activos[i] = any(s[f'id_sensor_disco_{i}'] != 0 for s in servidores_filtrados)
                
                servicios_activos = {}
                for i in range(1, 9):
                    servicios_activos[i] = any(s.get(f'id_sensor_servicio_{i}', 0) != 0 for s in servidores_filtrados)

                col_tabla, col_accion_btn = st.columns([5.2, 0.8])
                
                html_lineas = ["""
                <style>
                    .tabla-banco {
                        width: 100%;
                        table-layout: auto !important;
                        border-collapse: collapse;
                        font-family: Arial, sans-serif;
                    }
                    .tabla-banco th {
                        background-color: #003366 !important;
                        color: white !important;
                        font-weight: bold !important;
                        text-align: center !important;
                        padding: 14px 16px;
                        border: 1px solid #dee2e6 !important;
                        font-size: 11px;
                        text-transform: uppercase;
                        white-space: nowrap !important;
                    }
                    .tabla-banco td { 
                        color: #000000 !important; 
                        border: 1px solid #dee2e6 !important; 
                        padding: 12px 14px;
                        text-align: left;
                        font-size: 13px;
                        white-space: nowrap !important;
                    }
                    .tabla-banco tr:nth-child(even) {
                        background-color: #f8f9fa;
                    }
                </style>
                """]
                html_lineas.append('<table class="tabla-banco"><thead><tr>')
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
                        
                if tiene_red: html_lineas.append('<th>ID RED</th>')
                if tiene_latencia: html_lineas.append('<th>ID LATENCIA</th>')
                
                html_lineas.append('<th>ESTADO</th>')
                html_lineas.append('<th>FECHA REGISTRO</th>')
                html_lineas.append('</tr></thead><tbody>')
                
                lista_ips = []
                mapeo_servidores = {}
                
                for s in servidores_filtrados:
                    lista_ips.append(s['ip'])
                    mapeo_servidores[s['ip']] = s
                    
                    estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>' if s['estado_monitoreo'] == 1 else '<span style="color: #C62828; font-weight: bold;">INACTIVO</span>'
                    fecha_formateada = s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"
                    
                    html_lineas.append('<tr>')
                    html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                    html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                    html_lineas.append(f'<td>{s["sistema_operativo"]}</td>')
                    html_lineas.append(f'<td>{s.get("tipo", "No definido")}</td>')
                    
                    if tiene_cpu: html_lineas.append(f'<td>{s["id_sensor_cpu"]}</td>')
                    if tiene_ram: html_lineas.append(f'<td>{s["id_sensor_ram"]}</td>')
                    
                    for i in range(1, 7):
                        if discos_activos[i]:
                            html_lineas.append(f'<td>ID {s[f"id_sensor_disco_{i}"]}</td>')
                            
                    for i in range(1, 9):
                        if servicios_activos[i]:
                            html_lineas.append(f'<td>ID {s.get(f"id_sensor_servicio_{i}", 0)}</td>')
                            
                    if tiene_red: html_lineas.append(f'<td>{s["id_sensor_red"]}</td>')
                    if tiene_latencia: html_lineas.append(f'<td>{s["id_sensor_latencia"]}</td>')
                    
                    html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                    html_lineas.append(f'<td>{fecha_formateada}</td>')
                    html_lineas.append('</tr>')
                
                html_lineas.append('<tbody></table>')
                html_final = "".join(html_lineas)
                
                with col_tabla:
                    altura_vista = max(180, len(servidores_filtrados) * 85 + 70)
                    st.components.v1.html(html_final, height=altura_vista, scrolling=True)
                
                with col_accion_btn:
                    st.markdown("""
                        <style>
                            div[data-testid="stButton"] button[id*="btn_ver_datos_exclusivo"] {
                                background-color: #003366 !important;
                                color: white !important;
                                border: 1px solid #003366 !important;
                                margin-top: 42px;
                                font-weight: bold;
                                height: 45px;
                            }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🔍 Ver Datos", use_container_width=True, key="btn_ver_datos_exclusivo"):
                        servidor_elegido = st.session_state["filtro_servidor_nombre"]
                        st.session_state["servidor_seleccionado"] = servidor_elegido
                        st.session_state["filtro_monitoreo_nombre"] = servidor_elegido
                        st.session_state["filtro_monitoreo_sensor"] = "-- Seleccione un Sensor --"
                        st.session_state["navegacion_principal"] = "🖥️ Monitoreo en vivo"
                        st.query_params["p"] = "🖥️ Monitoreo en vivo"
                        st.query_params["srv"] = servidor_elegido
                        st.rerun()

                st.markdown("---")

            if not es_seguridad:
                st.info("ℹ️ **Modo Consulta Activo:** Su perfil de Operador permite verificar la infraestructura pero no dispone de privilegios para modificar el catálogo.")
            else:
                if not hay_filtro:
                    if st.button("➕ Registrar Servidor", use_container_width=True, key="btn_crud_registrar"):
                        st.session_state.accion_infra = "registrar"
                        st.rerun()
                else:
                    col_b1, col_b2 = st.columns(2)
                    if col_b1.button("📝 Editar Servidor Filtrado", use_container_width=True, key="btn_crud_editar"):
                        st.session_state.accion_infra = "editar"
                        st.rerun()
                    if col_b2.button("❌ Cambiar Estado / Desactivar", use_container_width=True, key="btn_crud_desactivar"):
                        st.session_state.accion_infra = "desactivar"
                        st.rerun()

                # Formulario de Registro Servidores
                if st.session_state.accion_infra == "registrar" and not hay_filtro:
                    st.markdown("### 📥 Registrar Nuevo Servidor Institucional")
                    with st.form("form_registro_srv"):
                        st.markdown("<div class='subtitulo-formulario'>📋 Datos Principales del Nodo</div>", unsafe_allow_html=True)
                        col_reg_p1, col_reg_p2 = st.columns(2)
                        reg_ip = col_reg_p1.text_input("Dirección IP (Campo Requerido)", placeholder="Ej: 10.0.4.50")
                        reg_alias = col_reg_p2.text_input("Nombre / Alias del Servidor (Requerido)", placeholder="Ej: SRV-PROD-BD")
                        
                        col_reg_p3, col_reg_p4 = st.columns(2)
                        reg_so = col_reg_p3.selectbox("Sistema Operativo Base Instalado", ["Windows", "Linux"])
                        
                        # MODIFICACIÓN REQUERIDA: Tipo exclusivo en "Virtual"
                        reg_tipo = col_reg_p4.selectbox("Tipo de Infraestructura V3.6", ["Virtual"])
                        
                        st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                        col_reg_e1, col_reg_e2 = st.columns(2)
                        reg_cpu = col_reg_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=0, step=None)
                        reg_ram = col_reg_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=0, step=None)
                        
                        col_reg_e3, col_reg_e4 = st.columns(2)
                        reg_red = col_reg_e3.number_input("ID Sensor PRTG - Ancho de Banda Red", value=0, step=None)
                        reg_lat = col_reg_e4.number_input("ID Sensor PRTG - Latencia de Respuesta (Ping)", value=0, step=None)
                        
                        st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                        col_reg_d1, col_reg_d2, col_reg_d3 = st.columns(3)
                        reg_d1 = col_reg_d1.number_input("Disco 1 (Unidad C:)", value=0, step=None)
                        reg_d2 = col_reg_d2.number_input("Disco 2 (Unidad F:)", value=0, step=None)
                        reg_d3 = col_reg_d3.number_input("Disco 3 (Unidad E:)", value=0, step=None)
                        
                        col_reg_d4, col_reg_d5, col_reg_d6 = st.columns(3)
                        reg_d4 = col_reg_d4.number_input("Disco 4 (Unidad D:)", value=0, step=None)
                        reg_d5 = col_reg_d5.number_input("Disco 5 (Unidad G:)", value=0, step=None)
                        reg_d6 = col_reg_d6.number_input("Disco 6 (Unidad Y:)", value=0, step=None)

                        st.markdown("<div class='subtitulo-formulario'>⚙️ Monitoreo de Servicios del Sistema (8 Slots Activos)</div>", unsafe_allow_html=True)
                        col_reg_s1, col_reg_s2 = st.columns(2)
                        reg_s1 = col_reg_s1.number_input("ID Sensor - Servicio del Sistema 1", value=0, step=None)
                        reg_s2 = col_reg_s2.number_input("ID Sensor - Servicio del Sistema 2", value=0, step=None)
                        
                        col_reg_s3, col_reg_s4, col_reg_s5 = st.columns(3)
                        reg_s3 = col_reg_s3.number_input("ID Sensor - Servicio 3", value=0, step=None)
                        reg_s4 = col_reg_s4.number_input("ID Sensor - Servicio 4", value=0, step=None)
                        reg_s5 = col_reg_s5.number_input("ID Sensor - Servicio 5", value=0, step=None)
                        
                        col_reg_s6, col_reg_s7, col_reg_s8 = st.columns(3)
                        reg_s6 = col_reg_s6.number_input("ID Sensor - Servicio 6", value=0, step=None)
                        reg_s7 = col_reg_s7.number_input("ID Sensor - Servicio 7", value=0, step=None)
                        reg_s8 = col_reg_s8.number_input("ID Sensor - Servicio 8", value=0, step=None)
                        
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
                                        INSERT INTO servidores (ip, nombre_alias, sistema_operativo, tipo,
                                                                id_sensor_cpu, id_sensor_ram, 
                                                                id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                                                                id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                                                                id_sensor_servicio_6, id_sensor_servicio_7, id_sensor_servicio_8,
                                                                id_sensor_red, id_sensor_latencia, estado_monitoreo)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                                    """
                                    cursor_write.execute(ins_query, (
                                        reg_ip.strip(), reg_alias.strip(), reg_so, reg_tipo,
                                        int(reg_cpu), int(reg_ram),
                                        int(reg_d1), int(reg_d2), int(reg_d3), int(reg_d4), int(reg_d5), int(reg_d6),
                                        int(reg_s1), int(reg_s2), int(reg_s3), int(reg_s4), int(reg_s5),
                                        int(reg_s6), int(reg_s7), int(reg_s8),
                                        int(reg_red), int(reg_lat)
                                    ))
                                    conn_write.commit()
                                    st.success("🎉 Servidor añadido al catálogo institucional con éxito.")
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

                # Formulario de Edición Servidores
                elif st.session_state.accion_infra == "editar" and hay_filtro:
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
                            
                            # MODIFICACIÓN REQUERIDA: Campo bloqueado con disabled=True
                            edit_tipo = col_edi_p2.text_input("Tipo de Infraestructura V3.6", value=srv_actual.get('tipo', 'Virtual'), disabled=True)
                            
                            st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                            col_e1, col_e2 = st.columns(2)
                            edit_cpu = col_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=int(srv_actual['id_sensor_cpu']), step=None)
                            edit_ram = col_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=int(srv_actual['id_sensor_ram']), step=None)
                            
                            col_e3, col_e4 = st.columns(2)
                            edit_red = col_e3.number_input("ID Sensor PRTG - Tráfico de Red", value=int(srv_actual['id_sensor_red']), step=None)
                            edit_lat = col_e4.number_input("ID Sensor PRTG - Latencia (Ping)", value=int(srv_actual['id_sensor_latencia']), step=None)
                            
                            st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                            col_d1, col_d2, col_d3 = st.columns(3)
                            edit_d1 = col_d1.number_input("Disco 1 (Unidad C:)", value=int(srv_actual['id_sensor_disco_1']), step=None)
                            edit_d2 = col_d2.number_input("Disco 2 (Unidad F:)", value=int(srv_actual['id_sensor_disco_2']), step=None)
                            edit_d3 = col_d3.number_input("Disco 3 (Unidad E:)", value=int(srv_actual['id_sensor_disco_3']), step=None)
                            
                            col_d4, col_d5, col_d6 = st.columns(3)
                            edit_d4 = col_d4.number_input("Disco 4 (Unidad D:)", value=int(srv_actual['id_sensor_disco_4']), step=None)
                            edit_d5 = col_d5.number_input("Disco 5 (Unidad G:)", value=int(srv_actual['id_sensor_disco_5']), step=None)
                            edit_d6 = col_d6.number_input("Disco 6 (Unidad Y:)", value=int(srv_actual.get('id_sensor_disco_6', 0)), step=None)

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
                                        SET nombre_alias=%s, id_sensor_cpu=%s, id_sensor_ram=%s, 
                                            id_sensor_disco_1=%s, id_sensor_disco_2=%s, id_sensor_disco_3=%s, id_sensor_disco_4=%s, id_sensor_disco_5=%s, id_sensor_disco_6=%s,
                                            id_sensor_servicio_1=%s, id_sensor_servicio_2=%s, id_sensor_servicio_3=%s, id_sensor_servicio_4=%s, id_sensor_servicio_5=%s,
                                            id_sensor_servicio_6=%s, id_sensor_servicio_7=%s, id_sensor_servicio_8=%s,
                                            id_sensor_red=%s, id_sensor_latencia=%s
                                        WHERE ip=%s
                                    """
                                    cursor_edit.execute(upd_query, (
                                        edit_alias.strip(), int(edit_cpu), int(edit_ram), 
                                        int(edit_d1), int(edit_d2), int(edit_d3), int(edit_d4), int(edit_d5), int(edit_d6),
                                        int(edit_s1), int(edit_s2), int(edit_s3), int(edit_s4), int(edit_s5),
                                        int(edit_s6), int(edit_s7), int(edit_s8),
                                        int(edit_red), int(edit_lat), ip_edit
                                    ))
                                    conn_edit.commit()
                                    st.success("🎉 Estructura modificada con éxito en la base de datos.")
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

                # Formulario de Desactivación Servidores
                elif st.session_state.accion_infra == "desactivar" and hay_filtro:
                    st.markdown("### ⚠️ Suspensión Lógica de Monitoreo")
                    with st.form("form_baja_srv"):
                        ip_des = st.selectbox("Seleccione Servidor a cambio de estado", lista_ips)
                        srv_baja = mapeo_servidores[ip_des]
                        estado_actual_str = "ACTIVO" if srv_baja['estado_monitoreo'] == 1 else "INACTIVO"
                        
                        st.info(f"Estado de monitoreo actual en la granja: **{estado_actual_str}**")
                        nuevo_est_bit = st.selectbox("Seleccione Nuevo Estado Lógico", ["Desactivar Monitoreo", "Activar Monitoreo"])
                        
                        col_btn_des1, col_btn_des2 = st.columns(2)
                        if col_btn_des1.form_submit_button("⚖️ Confirmar Estado", use_container_width=True):
                            bit_val = 0 if "Desactivar" in nuevo_est_bit else 1
                            try:
                                conn_status = conectar_bd()
                                cursor_status = conn_status.cursor()
                                cursor_status.execute("UPDATE servidores SET estado_monitoreo=%s WHERE ip=%s", (bit_val, ip_des))
                                conn_status.commit()
                                st.success(f"🚀 Nodo {ip_des} actualizado con éxito.")
                                st.session_state.accion_infra = None
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ Error: {ex}")
                            finally:
                                if cursor_status: cursor_status.close()
                                if conn_status: conn_status.close()
                                
                        if col_btn_des2.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.accion_infra = None
                            st.rerun()
                
        except Exception as e:
            st.error(f"Fallo técnico al procesar el módulo de servidores: {e}")
        finally:
            if cursor:
                try: cursor.close()
                except: pass
            if conn:
                try: conn.close()
                except: pass

    # ==========================================================================
    # PESTAÑA 2: GESTIÓN INTEGRAL Y EXACTA DE `datos_adicionales`
    # ==========================================================================
    with tab2:
        st.markdown('<h3 style="color:#003366;">📋 Control de Máquinas Virtuales y Parámetros Adicionales</h3>', unsafe_allow_html=True)
        
        # Inicialización de estados para la Pestaña 2
        if "filtro_adicional_nombre" not in st.session_state:
            st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
        if "accion_adicional" not in st.session_state:
            st.session_state.accion_adicional = None

        conn_ad = None
        cursor_ad = None
        
        try:
            # 1. COMPONENTE DE FILTRADO OBLIGATORIO
            lista_nombres_bd_ad = obtener_lista_nombres_servidores()
            opciones_selectbox_ad = ["-- Seleccione un Servidor Base --"] + lista_nombres_bd_ad

            idx_actual_ad = 0
            if st.session_state["filtro_adicional_nombre"] in opciones_selectbox_ad:
                idx_actual_ad = opciones_selectbox_ad.index(st.session_state["filtro_adicional_nombre"])

            col_f_ad1, col_f_ad2 = st.columns([3, 1])
            
            seleccion_ad = col_f_ad1.selectbox(
                "Filtrar Entornos por Servidor Base",
                options=opciones_selectbox_ad,
                index=idx_actual_ad,
                key="sb_filter_p2"
            )
            
            if seleccion_ad != st.session_state["filtro_adicional_nombre"]:
                st.session_state["filtro_adicional_nombre"] = seleccion_ad
                st.session_state.accion_adicional = None
                st.rerun()

            col_f_ad2.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
            
            if col_f_ad2.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_limpiar_filtro_ad"):
                st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
                st.session_state.accion_adicional = None
                st.rerun()

            hay_filtro_ad = st.session_state["filtro_adicional_nombre"] != "-- Seleccione un Servidor Base --"
            registros_adicionales = []

            conn_ad = conectar_bd()
            cursor_ad = conn_ad.cursor(dictionary=True)
            
            cursor_ad.execute("SELECT id_servidor, ip, nombre_alias FROM servidores ORDER BY nombre_alias ASC")
            servidores_maestros = cursor_ad.fetchall()
            opciones_srv_map = {f"{s['nombre_alias']} ({s['ip']})": s['id_servidor'] for s in servidores_maestros}
            opciones_srv_reverse = {s['id_servidor']: f"{s['nombre_alias']} ({s['ip']})" for s in servidores_maestros}

            if not hay_filtro_ad:
                st.info("💡 Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus máquinas virtuales y entornos adicionales.")
            else:
                query_select_ad = """
                    SELECT da.id, da.id_servidor, s.nombre_alias, s.ip AS ip_maestra, da.host, da.nombre_vm, 
                           da.estado, da.uso_cpu_pct, da.memoria_asignada_mb, da.tiempo_encendido, 
                           da.nombre_switch, da.direccion_mac, da.direcciones_ip, da.version, 
                           da.tamano_gb, da.cantidad_vhd, da.funcion
                    FROM datos_adicionales da
                    INNER JOIN servidores s ON da.id_servidor = s.id_servidor
                    WHERE s.nombre_alias = %s
                    ORDER BY da.id DESC
                """
                cursor_ad.execute(query_select_ad, (st.session_state["filtro_adicional_nombre"],))
                registros_adicionales = cursor_ad.fetchall()
            
                if not registros_adicionales:
                    st.warning("⚠️ No se encuentran entornos o máquinas virtuales registradas para el servidor seleccionado.")
                else:
                    html_ad = ["""
                    <style>
                        .tabla-banco {
                            width: 100%;
                            table-layout: auto !important;
                            border-collapse: collapse;
                            font-family: Arial, sans-serif;
                        }
                        .tabla-banco th {
                            background-color: #003366 !important;
                            color: white !important;
                            font-weight: bold !important;
                            text-align: center !important;
                            padding: 14px 16px;
                            border: 1px solid #dee2e6 !important;
                            font-size: 11px;
                            text-transform: uppercase;
                            white-space: nowrap !important;
                        }
                        .tabla-banco td { 
                            color: #000000 !important; 
                            border: 1px solid #dee2e6 !important; 
                            padding: 12px 14px;
                            text-align: left;
                            font-size: 13px;
                            white-space: nowrap !important;
                        }
                        .tabla-banco tr:nth-child(even) {
                            background-color: #f8f9fa;
                        }
                    </style>
                    <div style="overflow-x: auto; width: 100%;">
                    <table class="tabla-banco">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>SERVIDOR BASE</th>
                                <th>HOST FISICO</th>
                                <th>MÁQUINA VIRTUAL</th>
                                <th>ESTADO</th>
                                <th>CPU</th>
                                <th>RAM</th>
                                <th>UPTIME</th>
                                <th>SWITCH/VLAN</th>
                                <th>MAC ADDRESS</th>
                                <th>IPS ASIGNADAS</th>
                                <th>VER.</th>
                                <th>DISCO</th>
                                <th>VHDs</th>
                                <th>FUNCIÓN ROL</th>
                            </tr>
                        </thead>
                        <tbody>
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
                                <td style="text-align: center;"><b>{r['id']}</b></td>
                                <td>{r['nombre_alias']} ({r['ip_maestra']})</td>
                                <td>{r['host']}</td>
                                <td><b>{r['nombre_vm']}</b></td>
                                <td style="text-align: center;">{estado_html}</td>
                                <td style="text-align: right;">{r['uso_cpu_pct']}%</td>
                                <td style="text-align: right;">{r['memoria_asignada_mb']} MB</td>
                                <td>{r['tiempo_encendido'] if r['tiempo_encendido'] else 'N/A'}</td>
                                <td>{r['nombre_switch'] if r['nombre_switch'] else 'N/A'}</td>
                                <td><code>{r['direccion_mac'] if r['direccion_mac'] else 'N/A'}</code></td>
                                <td>{r['direcciones_ip'] if r['direcciones_ip'] else 'N/A'}</td>
                                <td>{r['version'] if r['version'] else 'N/A'}</td>
                                <td style="text-align: right;">{r['tamano_gb']} GB</td>
                                <td style="text-align: center;">{r['cantidad_vhd']}</td>
                                <td>{r['funcion'] if r['funcion'] else 'N/A'}</td>
                            </tr>
                        """)
                    html_ad.append("</tbody></table></div>")
                    
                    altura_ad = max(180, len(registros_adicionales) * 60 + 70)
                    st.components.v1.html("".join(html_ad), height=altura_ad, scrolling=True)

            st.markdown("---")

            # ACCIONES CRUD PESTAÑA 2
            if not es_seguridad:
                st.info("ℹ️ **Modo Consulta Activo:** Su cuenta operativa actual no posee permisos para alterar la matriz de datos adicionales.")
            else:
                if st.session_state.accion_adicional is None:
                    c_ab1, c_ab2 = st.columns(2)
                    if c_ab1.button("➕ Registrar Parámetro Adicional", use_container_width=True, key="btn_ad_crear"):
                        st.session_state.accion_adicional = "registrar"
                        st.rerun()
                        
                    if hay_filtro_ad and registros_adicionales and c_ab2.button("✏️ Editar Parámetro Adicional", use_container_width=True, key="btn_ad_editar"):
                        st.session_state.accion_adicional = "editar"
                        st.rerun()

                # FORMULARIO DE REGISTRO
                if st.session_state.accion_adicional == "registrar":
                    st.markdown("### 📥 Registrar Parámetro VM / Extensión de Infraestructura")
                    if not servidores_maestros:
                        st.error("❌ No es posible registrar datos adicionales porque la tabla de servidores está vacía.")
                    else:
                        with st.form("form_registro_adicional"):
                            st.markdown("<div class='subtitulo-formulario'>🔗 Vínculo e Identificación</div>", unsafe_allow_html=True)
                            col_r1, col_r2, col_r3 = st.columns(3)
                            
                            idx_defecto_srv = 0
                            if hay_filtro_ad:
                                for i, k in enumerate(opciones_srv_map.keys()):
                                    if st.session_state["filtro_adicional_nombre"] in k:
                                        idx_defecto_srv = i
                                        break
                                        
                            srv_combo = col_r1.selectbox("Servidor Maestro Relacionado", list(opciones_srv_map.keys()), index=idx_defecto_srv)
                            ad_host = col_r2.text_input("Host Físico Hospedador", placeholder="Ej: CMSRV001")
                            ad_vm = col_r3.text_input("Nombre Máquina Virtual", placeholder="Ej: BD_APP_CLD_193")
                            
                            st.markdown("<div class='subtitulo-formulario'>⚡ Rendimiento y Estado Operacional</div>", unsafe_allow_html=True)
                            col_r4, col_r5, col_r6, col_r7 = st.columns(4)
                            ad_estado = col_r4.selectbox("Estado Actual", ["Running", "OFF", "Suspended"])
                            ad_cpu = col_r5.number_input("Uso de CPU (%)", min_value=0, max_value=100, value=0, step=None)
                            ad_ram = col_r6.number_input("Memoria RAM Asignada (MB)", min_value=0, value=2048, step=None)
                            ad_uptime = col_r7.text_input("Tiempo Encendido (Uptime)", placeholder="Ej: 15 days, 4 hours")
                            
                            st.markdown("<div class='subtitulo-formulario'>🌐 Conectividad Red e Identificación Lógica</div>", unsafe_allow_html=True)
                            col_r8, col_r9, col_r10, col_r11 = st.columns(4)
                            ad_switch = col_r8.text_input("Virtual Switch / VLAN", placeholder="Ej: vSwitch-Prod")
                            ad_mac = col_r9.text_input("Dirección MAC Física", max_chars=17, placeholder="Ej: 00:1A:2B:3C:4D:5E")
                            ad_ips = col_r10.text_input("IPs Asignadas", placeholder="Ej: {10.10.1.218}")
                            ad_version = col_r11.text_input("Versión Componente", placeholder="Ej: v3.6")
                            
                            st.markdown("<div class='subtitulo-formulario'>💾 Dimensionamiento de Almacenamiento y Función</div>", unsafe_allow_html=True)
                            col_r12, col_r13, col_r14 = st.columns(3)
                            ad_tamano = col_r12.number_input("Espacio Total Asignado (GB)", min_value=0.0, value=50.0, step=None, format="%.2f")
                            ad_vhd = col_r13.number_input("Cantidad Discos Virtuales (VHD)", min_value=0, value=1, step=None)
                            ad_funcion = col_r14.text_input("Rol / Función Operativa", placeholder="Ej: CALDES")
                            
                            col_btn_ar1, col_btn_ar2 = st.columns(2)
                            if col_btn_ar1.form_submit_button("💾 CONSERVAR REGISTRO EN BD", use_container_width=True):
                                if not ad_host.strip() or not ad_vm.strip():
                                    st.error("❌ Los campos Host Físico y Nombre Máquina Virtual son estrictamente requeridos.")
                                else:
                                    try:
                                        id_srv_target = opciones_srv_map[srv_combo]
                                        query_ins = """
                                            INSERT INTO datos_adicionales (id_servidor, host, nombre_vm, estado, uso_cpu_pct, 
                                                                          memoria_asignada_mb, tiempo_encendido, nombre_switch, 
                                                                          direccion_mac, direcciones_ip, version, tamano_gb, 
                                                                          cantidad_vhd, funcion) 
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """
                                        cursor_ad.execute(query_ins, (
                                            id_srv_target, ad_host.strip(), ad_vm.strip(), ad_estado, int(ad_cpu),
                                            int(ad_ram), ad_uptime.strip() if ad_uptime.strip() else None,
                                            ad_switch.strip() if ad_switch.strip() else None,
                                            ad_mac.strip() if ad_mac.strip() else None,
                                            ad_ips.strip() if ad_ips.strip() else None,
                                            ad_version.strip() if ad_version.strip() else None,
                                            float(ad_tamano), int(ad_vhd),
                                            ad_funcion.strip() if ad_funcion.strip() else None
                                        ))
                                        conn_ad.commit()
                                        st.success("🎉 Mapeo adicional registrado exitosamente.")
                                        st.session_state.accion_adicional = None
                                        st.rerun()
                                    except Exception as ex_ins:
                                        st.error(f"❌ Fallo de inserción: {ex_ins}")
                                        
                            if col_btn_ar2.form_submit_button("❌ CANCELAR", use_container_width=True):
                                st.session_state.accion_adicional = None
                                st.rerun()

                # FORMULARIO DE EDICIÓN
                if st.session_state.accion_adicional == "editar" and hay_filtro_ad and registros_adicionales:
                    st.markdown("### ✏️ Modificar Registro de Extensión Técnico")
                    id_ad_edit = st.selectbox("Seleccione el ID del Registro Adicional a Modificar", lista_ids_adicionales, key="sb_id_ad_edit")
                    
                    if id_ad_edit:
                        ad_actual = mapeo_adicionales[id_ad_edit]
                        
                        with st.form("form_edicion_adicional"):
                            st.markdown("<div class='subtitulo-formulario'>🔗 Vínculo e Identificación</div>", unsafe_allow_html=True)
                            col_e1, col_e2, col_e3 = st.columns(3)
                            
                            srv_actual_str = opciones_srv_reverse.get(ad_actual['id_servidor'], list(opciones_srv_map.keys())[0])
                            lista_combos_srv = list(opciones_srv_map.keys())
                            idx_srv_act = lista_combos_srv.index(srv_actual_str) if srv_actual_str in lista_combos_srv else 0
                            
                            edit_srv_combo = col_e1.selectbox("Servidor Maestro Relacionado", lista_combos_srv, index=idx_srv_act)
                            edit_host = col_e2.text_input("Host Físico Hospedador", value=ad_actual['host'])
                            edit_vm = col_e3.text_input("Nombre Máquina Virtual", value=ad_actual['nombre_vm'])
                            
                            st.markdown("<div class='subtitulo-formulario'>⚡ Rendimiento y Estado Operacional</div>", unsafe_allow_html=True)
                            col_e4, col_e5, col_e6, col_e7 = st.columns(4)
                            
                            estados_opciones = ["Running", "OFF", "Suspended"]
                            idx_est = estados_opciones.index(ad_actual['estado']) if ad_actual['estado'] in estados_opciones else 0
                            edit_estado = col_e4.selectbox("Estado Actual", estados_opciones, index=idx_est)
                            
                            edit_cpu = col_e5.number_input("Uso de CPU (%)", min_value=0, max_value=100, value=int(ad_actual['uso_cpu_pct']), step=None)
                            edit_ram = col_e6.number_input("Memoria RAM Asignada (MB)", min_value=0, value=int(ad_actual['memoria_assigned_mb'] if 'memoria_assigned_mb' in ad_actual else ad_actual['memoria_asignada_mb']), step=None)
                            edit_uptime = col_e7.text_input("Tiempo Encendido (Uptime)", value=ad_actual['tiempo_encendido'] if ad_actual['tiempo_encendido'] else "")
                            
                            st.markdown("<div class='subtitulo-formulario'>🌐 Conectividad Red e Identificación Lógica</div>", unsafe_allow_html=True)
                            col_e8, col_e9, col_e10, col_e11 = st.columns(4)
                            edit_switch = col_e8.text_input("Virtual Switch / VLAN", value=ad_actual['nombre_switch'] if ad_actual['nombre_switch'] else "")
                            edit_mac = col_e9.text_input("Dirección MAC Física", max_chars=17, value=ad_actual['direccion_mac'] if ad_actual['direccion_mac'] else "")
                            edit_ips = col_e10.text_input("IPs Asignadas", value=ad_actual['direcciones_ip'] if ad_actual['direcciones_ip'] else "")
                            edit_version = col_e11.text_input("Versión Componente", value=ad_actual['version'] if ad_actual['version'] else "")
                            
                            st.markdown("<div class='subtitulo-formulario'>💾 Dimensionamiento de Almacenamiento y Función</div>", unsafe_allow_html=True)
                            col_e12, col_e13, col_e14 = st.columns(3)
                            edit_tamano = col_e12.number_input("Espacio Total Asignado (GB)", min_value=0.0, value=float(ad_actual['tamano_gb']), step=None, format="%.2f")
                            edit_vhd = col_e13.number_input("Cantidad Discos Virtuales (VHD)", min_value=0, value=int(ad_actual['cantidad_vhd']), step=None)
                            edit_funcion = col_e14.text_input("Rol / Función Operativa", value=ad_actual['funcion'] if ad_actual['funcion'] else "")
                            
                            col_btn_ae1, col_btn_ae2 = st.columns(2)
                            if col_btn_ae1.form_submit_button("✏️ COMPROMETER CAMBIOS", use_container_width=True):
                                if not edit_host.strip() or not edit_vm.strip():
                                    st.error("❌ Los campos Host Físico y Nombre Máquina Virtual no pueden quedar vacíos.")
                                else:
                                    try:
                                        id_srv_target = opciones_srv_map[edit_srv_combo]
                                        query_upd = """
                                            UPDATE datos_adicionales 
                                            SET id_servidor=%s, host=%s, nombre_vm=%s, estado=%s, uso_cpu_pct=%s, 
                                                memoria_asignada_mb=%s, tiempo_encendido=%s, nombre_switch=%s, 
                                                direccion_mac=%s, direcciones_ip=%s, version=%s, tamano_gb=%s, 
                                                cantidad_vhd=%s, funcion=%s 
                                            WHERE id=%s
                                        """
                                        cursor_ad.execute(query_upd, (
                                            id_srv_target, edit_host.strip(), edit_vm.strip(), edit_estado, int(edit_cpu),
                                            int(edit_ram), edit_uptime.strip() if edit_uptime.strip() else None,
                                            edit_switch.strip() if edit_switch.strip() else None,
                                            edit_mac.strip() if edit_mac.strip() else None,
                                            edit_ips.strip() if edit_ips.strip() else None,
                                            edit_version.strip() if edit_version.strip() else None,
                                            float(edit_tamano), int(edit_vhd),
                                            edit_funcion.strip() if edit_funcion.strip() else None,
                                            int(id_ad_edit)
                                        ))
                                        conn_ad.commit()
                                        st.success("🎉 Parámetro consolidado y actualizado de forma segura.")
                                        st.session_state.accion_adicional = None
                                        st.rerun()
                                    except Exception as ex_upd:
                                        st.error(f"❌ Fallo de actualización: {ex_upd}")
                                        
                            if col_btn_ae2.form_submit_button("❌ CANCELAR", use_container_width=True):
                                st.session_state.accion_adicional = None
                                st.rerun()
                                
        except Exception as e_ad:
            st.error(f"⚠️ Error al procesar la pestaña de datos adicionales: {e_ad}")
        finally:
            if cursor_ad: cursor_ad.close()
            if conn_ad: conn_ad.close()

if __name__ == "__main__":
    mostrar_tabla_servidores()