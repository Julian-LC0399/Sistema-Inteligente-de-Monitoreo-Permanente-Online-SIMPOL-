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
    """
    # INYECCIÓN DE ESTILOS PARA AMPLIAR FORMULARIOS Y DARLE MÁS ESPACIO A LA TABLA
    st.markdown("""
        <style>
            /* ==========================================
               ESTILOS PARA LOS FORMULARIOS GRANDES 
               ========================================== */
            div[data-testid="stForm"] label p {
                font-size: 15px !important;
                font-weight: 600 !important;
                color: #333333 !important;
            }
            div[data-testid="stForm"] div[data-testid="element-container"] {
                margin-bottom: 6px;
            }
            div[data-testid="stForm"] input {
                padding: 10px 14px !important;
                font-size: 14px !important;
            }
            .subtitulo-formulario {
                color: #003366;
                margin-top: 25px;
                margin-bottom: 15px;
                border-bottom: 2px solid #ECEFF1;
                padding-bottom: 5px;
                font-size: 17px;
                font-weight: bold;
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
    
    # ==========================================================================
    # HOMOLOGACIÓN DE ESTADO UNIFICADO PARA AUTOLIMPIEZA DESDE APP.PY
    # ==========================================================================
    if "filtro_servidor_nombre" not in st.session_state:
        st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
    if "accion_infra" not in st.session_state:
        st.session_state.accion_infra = None

    conn = None
    cursor = None

    try:
        # Carga dinámica optimizada desde la función con Caché
        lista_nombres_bd = obtener_lista_nombres_servidores()
        opciones_selectbox = ["-- Seleccione un Servidor --"] + lista_nombres_bd

        # Determinar el índice actual en base al session_state de forma segura
        idx_actual = 0
        if st.session_state["filtro_servidor_nombre"] in opciones_selectbox:
            idx_actual = opciones_selectbox.index(st.session_state["filtro_servidor_nombre"])

        # ==========================================================================
        # SECCIÓN DE FILTRADO (Asistida por Index para permitir destrucción externa)
        # ==========================================================================
        col_f1, col_f2 = st.columns([3, 1])
        
        seleccion = col_f1.selectbox(
            "Filtrar Servidor por Nombre",
            options=opciones_selectbox,
            index=idx_actual
        )
        
        # Sincronización limpia de estados si el usuario cambia el selector manualmente
        if seleccion != st.session_state["filtro_servidor_nombre"]:
            st.session_state["filtro_servidor_nombre"] = seleccion
            st.session_state.accion_infra = None
            st.rerun()

        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        
        # AL DAR CLIC A LIMPIAR FILTRO MANUALMENTE:
        if col_f2.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_limpiar_filtro_srv"):
            st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
            st.session_state.accion_infra = None
            st.query_params.clear() 
            st.rerun()

        # Verificamos si se seleccionó un servidor válido
        hay_filtro = st.session_state["filtro_servidor_nombre"] != "-- Seleccione un Servidor --"
        servidores_filtrados = []

        if not hay_filtro:
            st.info("💡 Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus parámetros técnicos.")
        else:
            # Esta consulta es específica e indexada, no penaliza el rendimiento
            conn = conectar_bd()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ip, nombre_alias, sistema_operativo, estado_monitoreo, fecha_alta, 
                       id_sensor_cpu, id_sensor_ram, 
                       id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                       id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                       id_sensor_red, id_sensor_latencia 
                FROM servidores
                WHERE nombre_alias = %s
            """
            cursor.execute(query, (st.session_state["filtro_servidor_nombre"],))
            servidores_filtrados = cursor.fetchall()

            if not servidores_filtrados:
                st.warning("⚠️ No se encontraron registros detallados para el servidor seleccionado.")

        # ==========================================================================
        # RENDERIZADO DE TABLA DINÁMICA (OCULTA COLUMNAS SIN ASIGNAR)
        # ==========================================================================
        if hay_filtro and servidores_filtrados:
            
            # EVALUACIÓN DINÁMICA: ¿Tienen datos estas columnas en los registros actuales?
            tiene_cpu = any(s['id_sensor_cpu'] != 0 for s in servidores_filtrados)
            tiene_ram = any(s['id_sensor_ram'] != 0 for s in servidores_filtrados)
            tiene_red = any(s['id_sensor_red'] != 0 for s in servidores_filtrados)
            tiene_latencia = any(s['id_sensor_latencia'] != 0 for s in servidores_filtrados)
            
            # Mapear e identificar slots de discos individuales activos
            discos_activos = {}
            letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:", 6: "H:"}
            for i in range(1, 7):
                discos_activos[i] = any(s[f'id_sensor_disco_{i}'] != 0 for s in servidores_filtrados)
            
            # Mapear e identificar slots de servicios individuales activos
            servicios_activos = {}
            for i in range(1, 6):
                servicios_activos[i] = any(s[f'id_sensor_servicio_{i}'] != 0 for s in servidores_filtrados)

            # Estructura de diseño dividida: 84% Tabla Ampliada, 16% Botón de Acción
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
            
            # CONSTRUCCIÓN DINÁMICA DE CABECERAS (Solo columnas activas)
            html_lineas.append('<th>DIRECCIÓN IP</th>')
            html_lineas.append('<th>NOMBRE</th>')
            html_lineas.append('<th>SISTEMA OPERATIVO</th>')
            
            if tiene_cpu: html_lineas.append('<th>ID CPU</th>')
            if tiene_ram: html_lineas.append('<th>ID RAM</th>')
            
            # Columnas individuales de discos detectados
            for i in range(1, 7):
                if discos_activos[i]:
                    html_lineas.append(f'<th>DISCO {letras_unidades[i]}</th>')
                    
            # Columnas individuales de servicios detectados
            for i in range(1, 6):
                if servicios_activos[i]:
                    html_lineas.append(f'<th>SERVICIO {i}</th>')
                    
            if tiene_red: html_lineas.append('<th>ID RED</th>')
            if tiene_latencia: html_lineas.append('<th>ID LATENCIA</th>')
            
            html_lineas.append('<th>ESTADO</th>')
            html_lineas.append('<th>FECHA REGISTRO</th>')
            html_lineas.append('</tr></thead><tbody>')
            
            # GENERACIÓN DE FILAS (Mapeando solo datos de columnas activas)
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
                
                if tiene_cpu: html_lineas.append(f'<td>{s["id_sensor_cpu"]}</td>')
                if tiene_ram: html_lineas.append(f'<td>{s["id_sensor_ram"]}</td>')
                
                # Celdas dinámicas para cada disco asignado
                for i in range(1, 7):
                    if discos_activos[i]:
                        html_lineas.append(f'<td>ID {s[f"id_sensor_disco_{i}"]}</td>')
                        
                # Celdas dinámicas para cada servicio asignado
                for i in range(1, 6):
                    if servicios_activos[i]:
                        html_lineas.append(f'<td>ID {s[f"id_sensor_servicio_{i}"]}</td>')
                        
                if tiene_red: html_lineas.append(f'<td>{s["id_sensor_red"]}</td>')
                if tiene_latencia: html_lineas.append(f'<td>{s["id_sensor_latencia"]}</td>')
                
                html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                html_lineas.append(f'<td>{fecha_formateada}</td>')
                html_lineas.append('</tr>')
            
            html_lineas.append('<tbody></table>')
            html_final = "".join(html_lineas)
            
            # Renderizado de la tabla con la altura recalculada de forma holgada
            with col_tabla:
                altura_vista = max(180, len(servidores_filtrados) * 85 + 70)
                st.components.v1.html(html_final, height=altura_vista, scrolling=True)
            
            # INYECCIÓN DEL BOTÓN NATIVO AZUL CORPORATIVO EXCLUSIVO (Fuera de la tabla)
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
                        div[data-testid="stButton"] button[id*="btn_ver_datos_exclusivo"]:hover {
                            background-color: #002244 !important;
                            border: 1px solid #002244 !important;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                if st.button("🔍 Ver Datos", use_container_width=True, key="btn_ver_datos_exclusivo"):
                    servidor_elegido = st.session_state["filtro_servidor_nombre"]
                    
                    # Sincronización masiva de Estados de datos cruzados
                    st.session_state["servidor_seleccionado"] = servidor_elegido
                    st.session_state["filtro_monitoreo_nombre"] = servidor_elegido
                    st.session_state["filtro_monitoreo_sensor"] = "-- Seleccione un Sensor --"
                    st.session_state["navegacion_principal"] = "🖥️ Monitoreo en vivo"
                    
                    st.query_params["p"] = "🖥️ Monitoreo en vivo"
                    st.query_params["srv"] = servidor_elegido
                    st.rerun()

            st.markdown("---")

        # =====================================================================
        # FILTRO DE SEGURIDAD: CONTROL DE ACCESO PARA ESCRITURA
        # =====================================================================
        if not es_seguridad:
            st.info("ℹ️ **Modo Consulta Activo:** Su perfil de Operador permite verificar la infraestructura pero no dispone de privilegios para modificar el catálogo.")
            return

        # =====================================================================
        # INTERFAZ DE OPERACIONES CONDICIONAL (CRUD)
        # =====================================================================
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

        # --- FORMULARIO DE REGISTRO GRAN TAMAÑO ---
        if st.session_state.accion_infra == "registrar" and not hay_filtro:
            st.markdown("### 📥 Registrar Nuevo Servidor Institucional")
            with st.form("form_registro_srv"):
                
                st.markdown("<div class='subtitulo-formulario'>📋 Datos Principales del Nodo</div>", unsafe_allow_html=True)
                col_reg_p1, col_reg_p2 = st.columns(2)
                reg_ip = col_reg_p1.text_input("Dirección IP (Campo Requerido)", placeholder="Ej: 10.0.4.50")
                reg_alias = col_reg_p2.text_input("Nombre / Alias del Servidor (Requerido)", placeholder="Ej: SRV-PROD-BD")
                
                reg_so = st.selectbox("Sistema Operativo Base Instalado", ["Windows", "Linux"])
                
                st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                col_reg_e1, col_reg_e2 = st.columns(2)
                reg_cpu = col_reg_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=0, step=1)
                reg_ram = col_reg_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=0, step=1)
                
                col_reg_e3, col_reg_e4 = st.columns(2)
                reg_red = col_reg_e3.number_input("ID Sensor PRTG - Ancho de Banda Red", value=0, step=1)
                reg_lat = col_reg_e4.number_input("ID Sensor PRTG - Latencia de Respuesta (Ping)", value=0, step=1)
                
                st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                col_reg_d1, col_reg_d2, col_reg_d3 = st.columns(3)
                reg_d1 = col_reg_d1.number_input("Disco 1 (Unidad C:)", value=0, step=1)
                reg_d2 = col_reg_d2.number_input("Disco 2 (Unidad F:)", value=0, step=1)
                reg_d3 = col_reg_d3.number_input("Disco 3 (Unidad E:)", value=0, step=1)
                
                col_reg_d4, col_reg_d5, col_reg_d6 = st.columns(3)
                reg_d4 = col_reg_d4.number_input("Disco 4 (Unidad D:)", value=0, step=1)
                reg_d5 = col_reg_d5.number_input("Disco 5 (Unidad G:)", value=0, step=1)
                reg_d6 = col_reg_d6.number_input("Disco 6 (Unidad H:)", value=0, step=1)

                st.markdown("<div class='subtitulo-formulario'>⚙️ Monitoreo de Servicios del Sistema (Slots)</div>", unsafe_allow_html=True)
                col_reg_s1, col_reg_s2 = st.columns(2)
                reg_s1 = col_reg_s1.number_input("ID Sensor - Servicio del Sistema 1", value=0, step=1)
                reg_s2 = col_reg_s2.number_input("ID Sensor - Servicio del Sistema 2", value=0, step=1)
                
                col_reg_s3, col_reg_s4, col_reg_s5 = st.columns(3)
                reg_s3 = col_reg_s3.number_input("ID Sensor - Servicio 3", value=0, step=1)
                reg_s4 = col_reg_s4.number_input("ID Sensor - Servicio 4", value=0, step=1)
                reg_s5 = col_reg_s5.number_input("ID Sensor - Servicio 5", value=0, step=1)
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_btn_reg1, col_btn_reg2 = st.columns(2)
                
                if col_btn_reg1.form_submit_button("💾 Guardar Servidor", use_container_width=True):
                    if not reg_ip.strip() or not reg_alias.strip():
                        st.error("❌ Error: La Dirección IP y el nombre son campos obligatorios.")
                    elif not validar_ip(reg_ip):
                        st.error("❌ Error: El formato de la Dirección IP no es válido. Ejemplo: 10.0.4.50")
                    else:
                        conn_write = None
                        cursor_write = None
                        try:
                            conn_write = conectar_bd()
                            cursor_write = conn_write.cursor()
                            ins_query = """
                                INSERT INTO servidores (ip, nombre_alias, sistema_operativo, 
                                                        id_sensor_cpu, id_sensor_ram, 
                                                        id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5, id_sensor_disco_6,
                                                        id_sensor_servicio_1, id_sensor_servicio_2, id_sensor_servicio_3, id_sensor_servicio_4, id_sensor_servicio_5,
                                                        id_sensor_red, id_sensor_latencia, estado_monitoreo)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                            """
                            cursor_write.execute(ins_query, (
                                reg_ip.strip(), reg_alias.strip(), reg_so,
                                int(reg_cpu), int(reg_ram),
                                int(reg_d1), int(reg_d2), int(reg_d3), int(reg_d4), int(reg_d5), int(reg_d6),
                                int(reg_s1), int(reg_s2), int(reg_s3), int(reg_s4), int(reg_s5),
                                int(reg_red), int(reg_lat)
                            ))
                            conn_write.commit()
                            
                            st.success("Servidor añadido al catálogo institucional.")
                            st.session_state.accion_infra = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as ex:
                            if "Duplicate entry" in str(ex):
                                st.error("❌ Conflicto de Red: Esta dirección IP ya está asignada a otro servidor.")
                            else:
                                st.error(f"Error de persistencia: {ex}")
                        finally:
                            if cursor_write: cursor_write.close()
                            if conn_write: conn_write.close()
                            
                if col_btn_reg2.form_submit_button("❌ Cancelar Operación", use_container_width=True):
                    st.session_state.accion_infra = None
                    st.rerun()

        # --- FORMULARIO DE EDICIÓN GRAN TAMAÑO ---
        elif st.session_state.accion_infra == "editar" and hay_filtro:
            st.markdown("### 📝 Modificación de Parámetros Técnicos")
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
                    edit_alias = st.text_input("Alias / Nombre Comercial del Servidor", value=srv_actual['nombre_alias'])
                    
                    st.markdown("<div class='subtitulo-formulario'>🛠️ Configuración de Sensores Básicos (PRTG)</div>", unsafe_allow_html=True)
                    col_e1, col_e2 = st.columns(2)
                    edit_cpu = col_e1.number_input("ID Sensor PRTG - Rendimiento CPU", value=int(srv_actual['id_sensor_cpu']), step=1)
                    edit_ram = col_e2.number_input("ID Sensor PRTG - Consumo Memoria RAM", value=int(srv_actual['id_sensor_ram']), step=1)
                    
                    col_e3, col_e4 = st.columns(2)
                    edit_red = col_e3.number_input("ID Sensor PRTG - Tráfico de Red", value=int(srv_actual['id_sensor_red']), step=1)
                    edit_lat = col_e4.number_input("ID Sensor PRTG - Latencia (Ping)", value=int(srv_actual['id_sensor_latencia']), step=1)
                    
                    st.markdown("<div class='subtitulo-formulario'>💾 Matriz de Almacenamiento (PRTG Multidisco)</div>", unsafe_allow_html=True)
                    col_d1, col_d2, col_d3 = st.columns(3)
                    edit_d1 = col_d1.number_input("Disco 1 (Unidad C:)", value=int(srv_actual['id_sensor_disco_1']), step=1)
                    edit_d2 = col_d2.number_input("Disco 2 (Unidad F:)", value=int(srv_actual['id_sensor_disco_2']), step=1)
                    edit_d3 = col_d3.number_input("Disco 3 (Unidad E:)", value=int(srv_actual['id_sensor_disco_3']), step=1)
                    
                    col_d4, col_d5, col_d6 = st.columns(3)
                    edit_d4 = col_d4.number_input("Disco 4 (Unidad D:)", value=int(srv_actual['id_sensor_disco_4']), step=1)
                    edit_d5 = col_d5.number_input("Disco 5 (Unidad G:)", value=int(srv_actual['id_sensor_disco_5']), step=1)
                    edit_d6 = col_d6.number_input("Disco 6 (Unidad H:)", value=int(srv_actual.get('id_sensor_disco_6', 0)), step=1)

                    st.markdown("<div class='subtitulo-formulario'>⚙️ Sensores de Servicio Activos (Slots)</div>", unsafe_allow_html=True)
                    col_s1, col_s2 = st.columns(2)
                    edit_s1 = col_s1.number_input("ID Sensor - Servicio Sistema 1", value=int(srv_actual.get('id_sensor_servicio_1', 0)), step=1)
                    edit_s2 = col_s2.number_input("ID Sensor - Servicio Sistema 2", value=int(srv_actual.get('id_sensor_servicio_2', 0)), step=1)
                    
                    col_s3, col_s4, col_s5 = st.columns(3)
                    edit_s3 = col_s3.number_input("ID Sensor - Servicio 3", value=int(srv_actual.get('id_sensor_servicio_3', 0)), step=1)
                    edit_s4 = col_s4.number_input("ID Sensor - Servicio 4", value=int(srv_actual.get('id_sensor_servicio_4', 0)), step=1)
                    edit_s5 = col_s5.number_input("ID Sensor - Servicio 5", value=int(srv_actual.get('id_sensor_servicio_5', 0)), step=1)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_btn_edi1, col_btn_edi2 = st.columns(2)
                    
                    if col_btn_edi1.form_submit_button("📝 Aplicar Cambios Técnicos", use_container_width=True):
                        conn_edit = None
                        cursor_edit = None
                        try:
                            conn_edit = conectar_bd()
                            cursor_edit = conn_edit.cursor()
                            upd_query = """
                                UPDATE servidores 
                                SET nombre_alias=%s, id_sensor_cpu=%s, id_sensor_ram=%s, 
                                    id_sensor_disco_1=%s, id_sensor_disco_2=%s, id_sensor_disco_3=%s, id_sensor_disco_4=%s, id_sensor_disco_5=%s, id_sensor_disco_6=%s,
                                    id_sensor_servicio_1=%s, id_sensor_servicio_2=%s, id_sensor_servicio_3=%s, id_sensor_servicio_4=%s, id_sensor_servicio_5=%s,
                                    id_sensor_red=%s, id_sensor_latencia=%s
                                WHERE ip=%s
                            """
                            cursor_edit.execute(upd_query, (
                                edit_alias.strip(), int(edit_cpu), int(edit_ram), 
                                int(edit_d1), int(edit_d2), int(edit_d3), int(edit_d4), int(edit_d5), int(edit_d6),
                                int(edit_s1), int(edit_s2), int(edit_s3), int(edit_s4), int(edit_s5),
                                int(edit_red), int(edit_lat), ip_edit
                            ))
                            conn_edit.commit()
                            
                            st.success("Estructura multidisco y servicios modificada con éxito.")
                            st.session_state.accion_infra = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al actualizar: {ex}")
                        finally:
                            if cursor_edit: cursor_edit.close()
                            if conn_edit: conn_edit.close()
                            
                    if col_btn_edi2.form_submit_button("❌ Cancelar Modificación", use_container_width=True):
                        st.session_state.accion_infra = None
                        st.rerun()

        # --- FORMULARIO DE DESACTIVACIÓN ---
        elif st.session_state.accion_infra == "desactivar" and hay_filtro:
            st.markdown("### ❌ Suspensión Lógica de Monitoreo")
            with st.form("form_baja_srv"):
                ip_des = st.selectbox("Seleccione Servidor a cambio de estado", lista_ips)
                srv_baja = mapeo_servidores[ip_des]
                estado_actual_str = "ACTIVO" if srv_baja['estado_monitoreo'] == 1 else "INACTIVO"
                
                st.info(f"Estado de monitoreo actual en la granja: **{estado_actual_str}**")
                nuevo_est_bit = st.selectbox("Seleccione Nuevo Estado Lógico", ["Desactivar Monitoreo", "Activar Monitoreo"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_btn_des1, col_btn_des2 = st.columns(2)
                
                if col_btn_des1.form_submit_button("Confirmar Estado", use_container_width=True):
                    bit_val = 0 if "Desactivar" in nuevo_est_bit else 1
                    conn_status = None
                    cursor_status = None
                    try:
                        conn_status = conectar_bd()
                        cursor_status = conn_status.cursor()
                        cursor_status.execute("UPDATE servidores SET estado_monitoreo=%s WHERE ip=%s", (bit_val, ip_des))
                        conn_status.commit()
                        
                        st.success(f"Nodo {ip_des} actualizado con éxito.")
                        st.session_state.accion_infra = None
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error: {ex}")
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

if __name__ == "__main__":
    mostrar_tabla_servidores()