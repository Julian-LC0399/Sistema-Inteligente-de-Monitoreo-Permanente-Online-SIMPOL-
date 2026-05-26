import streamlit as st
from database import conectar_bd

def mostrar_tabla_servidores(rol_usuario=None):
    """
    Renderiza el catálogo de servidores del Banco Caroní de forma optimizada.
    Filtra mediante un menú desplegable (selectbox) cargado desde la BD.
    Condiciona la visibilidad de la tabla y los botones según la selección.
    """
    # ==========================================================================
    # ENCABEZADO CON LA SINTAXIS HOMOLOGADA EN AZUL CORPORATIVO
    # ==========================================================================
    st.markdown('<h2 style="color:#003366;">🖥️ Gestión Servidores</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Normalizamos el rol a mayúsculas para evitar fallas de acceso
    rol_sanitizado = str(rol_usuario).strip().upper() if rol_usuario else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado
    
    # Inicializar estados de sesión para filtros y acciones si no existen
    if "filtro_nombre" not in st.session_state:
        st.session_state.filtro_nombre = ""
    if "accion_infra" not in st.session_state:
        st.session_state.accion_infra = None

    try:
        conn = conectar_bd()
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL. Verifica el servicio de base de datos.")
            return
            
        cursor = conn.cursor(dictionary=True)
        
        # 1. CARGA DINÁMICA DE SERVIDORES PARA EL SELECTBOX
        cursor.execute("SELECT DISTINCT nombre_alias FROM servidores WHERE nombre_alias IS NOT NULL AND nombre_alias != '' ORDER BY nombre_alias ASC")
        lista_nombres_bd = [r['nombre_alias'] for r in cursor.fetchall()]
        
        # Agregamos la opción por defecto para mantener la tabla oculta al inicio
        opciones_selectbox = ["-- Seleccione un Servidor --"] + lista_nombres_bd

        # Determinar el índice actual en base al session_state
        idx_actual = 0
        if st.session_state.filtro_nombre in opciones_selectbox:
            idx_actual = opciones_selectbox.index(st.session_state.filtro_nombre)

        # ==========================================================================
        # SECCIÓN DE FILTRADO (Alineación simétrica de componentes)
        # ==========================================================================
        col_f1, col_f2 = st.columns([3, 1])
        
        # Desplegable de selección directa
        seleccion = col_f1.selectbox(
            "Filtrar Servidor por Nombre",
            options=opciones_selectbox,
            index=idx_actual
        )
        
        # Empujamos el botón hacia abajo insertando un espacio HTML para alinearlo al selectbox
        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        
        # Botón dedicado a limpiar el filtro
        if col_f2.button("🧹 Limpiar Filtro", use_container_width=True):
            st.session_state.filtro_nombre = "-- Seleccione un Servidor --"
            st.session_state.accion_infra = None
            st.rerun()
            
        # Si la selección cambia, actualizamos el estado e invalidamos formularios previos
        if seleccion != st.session_state.filtro_nombre:
            st.session_state.filtro_nombre = seleccion
            st.session_state.accion_infra = None
            st.rerun()

        # Verificamos si se seleccionó un servidor válido
        hay_filtro = st.session_state.filtro_nombre != "-- Seleccione un Servidor --"
        servidores_filtrados = []

        if not hay_filtro:
            st.info("💡 Por favor, seleccione un servidor de la lista desplegable superior para visualizar sus parámetros técnicos.")
        else:
            # Consulta exacta para el servidor seleccionado
            query = """
                SELECT ip, nombre_alias, sistema_operativo, estado_monitoreo, fecha_alta, 
                       id_sensor_cpu, id_sensor_ram, 
                       id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5,
                       id_sensor_red, id_sensor_latencia 
                FROM servidores
                WHERE nombre_alias = %s
            """
            cursor.execute(query, (st.session_state.filtro_nombre,))
            servidores_filtrados = cursor.fetchall()

        # ==========================================================================
        # RENDERIZADO DE TABLA (Solo si hay un servidor seleccionado)
        # ==========================================================================
        if servidores_filtrados:
            html_lineas = []
            html_lineas.append("""
            <style>
                .tabla-banco {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                }
                .tabla-banco th {
                    background-color: #003366 !important;
                    color: #FFFFFF !important;
                    font-weight: bold !important;
                    text-align: center !important;
                    padding: 12px 10px;
                    border: 1px solid #dee2e6 !important;
                    font-size: 12px;
                    text-transform: uppercase;
                }
                .tabla-banco td { 
                    color: #000000 !important; 
                    border: 1px solid #dee2e6 !important; 
                    padding: 10px;
                    text-align: left;
                    font-size: 12px;
                }
                .tabla-banco tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
                .sub-disco {
                    font-size: 10px;
                    color: #555555;
                    display: block;
                    line-height: 1.2;
                }
            </style>
            """)
            html_lineas.append('<table class="tabla-banco">')
            html_lineas.append("""
                <thead>
                    <tr>
                        <th>DIRECCIÓN IP</th>
                        <th>NOBRE</th>
                        <th>SISTEMA OPERATIVO</th>
                        <th>ID CPU</th>
                        <th>ID RAM</th>
                        <th>ALMACENAMIENTO (DISCOS)</th>
                        <th>ID RED</th>
                        <th>ID LATENCIA</th>
                        <th>ESTADO</th>
                        <th>FECHA REGISTRO</th>
                    </tr>
                </thead>
            """)
            html_lineas.append('<tbody>')
            
            lista_ips = []
            mapeo_servidores = {}
            
            for s in servidores_filtrados:
                lista_ips.append(s['ip'])
                mapeo_servidores[s['ip']] = s
                
                if s['estado_monitoreo'] == 1:
                    estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>'
                else:
                    estado_html = '<span style="color: #C62828; font-weight: bold;">INACTIVO</span>'
                
                fecha_formateada = s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"
                
                cpu = s['id_sensor_cpu'] if s['id_sensor_cpu'] != 0 else "No asignado"
                ram = s['id_sensor_ram'] if s['id_sensor_ram'] != 0 else "No asignado"
                red = s['id_sensor_red'] if s['id_sensor_red'] != 0 else "No asignado"
                latencia = s['id_sensor_latencia'] if s['id_sensor_latencia'] != 0 else "No asignado"
                
                discos_html = []
                letras_unidades = {1: "C:", 2: "F:", 3: "E:", 4: "D:", 5: "G:"}
                for i in range(1, 6):
                    id_d = s[f'id_sensor_disco_{i}']
                    if id_d != 0:
                        discos_html.append(f"<span class='sub-disco'><b>{letras_unidades[i]}</b> ID {id_d}</span>")
                
                txt_discos = "".join(discos_html) if discos_html else "<span style='color:#777;'>Sin discos</span>"
                so_str = str(s['sistema_operativo'])
                
                html_lineas.append('<tr>')
                html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                html_lineas.append(f'<td>{so_str}</td>')
                html_lineas.append(f'<td>{cpu}</td>')
                html_lineas.append(f'<td>{ram}</td>')
                html_lineas.append(f'<td>{txt_discos}</td>')
                html_lineas.append(f'<td>{red}</td>')
                html_lineas.append(f'<td>{latencia}</td>')
                html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                html_lineas.append(f'<td>{fecha_formateada}</td>')
                html_lineas.append('</tr>')
                
            html_lineas.append('</tbody></table>')
            
            html_final = "".join(html_lineas)
            altura_vista = max(180, len(servidores_filtrados) * 55 + 70)
            st.components.v1.html(html_final, height=altura_vista, scrolling=True)
            st.markdown("---")

        # =====================================================================
        # FILTRO DE SEGURIDAD: CONTROL DE ACCESO PARA ESCRITURA
        # =====================================================================
        if not es_seguridad:
            st.info("ℹ️ **Modo Consulta Activo:** Su perfil de Operador permite verificar la infraestructura pero no dispone de privilegios para modificar el catálogo.")
            cursor.close()
            conn.close()
            return

        # =====================================================================
        # INTERFAZ DE OPERACIONES CONDICIONAL
        # =====================================================================
        if not hay_filtro:
            # Caso 1: Sin selección -> Solo se permite "Registrar Servidor"
            if st.button("➕ Registrar Servidor", use_container_width=True):
                st.session_state.accion_infra = "registrar"

        else:
            # Caso 2: Servidor seleccionado -> Se permite "Editar" y "Desactivar" sobre este nodo
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("📝 Editar Servidor Filtrado", use_container_width=True):
                st.session_state.accion_infra = "editar"
            if col_b2.button("❌ Cambiar Estado / Desactivar", use_container_width=True):
                st.session_state.accion_infra = "desactivar"

        # --- FORMULARIO DE REGISTRO (Solo si no hay filtro) ---
        if st.session_state.accion_infra == "registrar" and not hay_filtro:
            st.markdown("### 📥 Nuevo Servidor")
            with st.form("form_registro_srv"):
                reg_ip = st.text_input("Dirección IP (Requerido)")
                reg_alias = st.text_input("Nombre (Requerido)")
                reg_so = st.selectbox("Sistema Operativo", ["Windows", "Linux"])
                
                if st.form_submit_button("Guardar Servidor"):
                    if not reg_ip.strip() or not reg_alias.strip():
                        st.error("❌ Error: La Dirección IP y el nombre son campos obligatorios para el alta.")
                    else:
                        try:
                            ins_query = """
                                INSERT INTO servidores (ip, nombre_alias, sistema_operativo, 
                                                        id_sensor_cpu, id_sensor_ram, 
                                                        id_sensor_disco_1, id_sensor_disco_2, id_sensor_disco_3, id_sensor_disco_4, id_sensor_disco_5,
                                                        id_sensor_red, id_sensor_latencia)
                                VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                            """
                            cursor.execute(ins_query, (reg_ip.strip(), reg_alias.strip(), reg_so))
                            conn.commit()
                            st.success("Servidor añadido al catálogo institucional.")
                            st.session_state.accion_infra = None
                            st.rerun()
                        except Exception as ex:
                            if "Duplicate entry" in str(ex):
                                st.error("❌ Conflicto de Red: Esta dirección IP ya está asignada a otro servidor.")
                            else:
                                st.error(f"Error de persistencia: {ex}")

        # --- FORMULARIO DE EDICIÓN MULTIDISCO (Solo si hay selección activa) ---
        elif st.session_state.accion_infra == "editar" and hay_filtro:
            st.markdown("### 📝 Modificación de Parámetros Técnicos")
            
            ip_edit = st.selectbox("Seleccione la IP del Servidor a Modificar", lista_ips)
            
            if ip_edit:
                srv_actual = mapeo_servidores[ip_edit]
                fecha_act = srv_actual['fecha_alta'].strftime("%Y-%m-%d %H:%M") if srv_actual['fecha_alta'] else "N/A"
                
                with st.form("form_edicion_srv"):
                    col_lock1, col_lock2 = st.columns(2)
                    col_lock1.text_input("Fecha de Alta Institucional (No modificable)", value=fecha_act, disabled=True)
                    col_lock2.text_input("Sistema Operativo Base (No modificable)", value=srv_actual['sistema_operativo'], disabled=True)
                    
                    edit_alias = st.text_input("Alias / Nombre Comercial", value=srv_actual['nombre_alias'])
                    
                    st.markdown("#### 🛠️ Configuración de Sensores Básicos")
                    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                    edit_cpu = col_e1.number_input("ID Sensor CPU", value=int(srv_actual['id_sensor_cpu']), step=1)
                    edit_ram = col_e2.number_input("ID Sensor RAM", value=int(srv_actual['id_sensor_ram']), step=1)
                    edit_red = col_e3.number_input("ID Sensor Red", value=int(srv_actual['id_sensor_red']), step=1)
                    edit_lat = col_e4.number_input("ID Sensor Latencia", value=int(srv_actual['id_sensor_latencia']), step=1)
                    
                    st.markdown("#### 💾 Matriz de Almacenamiento (PRTG Multidisco)")
                    col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
                    edit_d1 = col_d1.number_input("Disco 1 (C:)", value=int(srv_actual['id_sensor_disco_1']), step=1)
                    edit_d2 = col_d2.number_input("Disco 2 (F:)", value=int(srv_actual['id_sensor_disco_2']), step=1)
                    edit_d3 = col_d3.number_input("Disco 3 (E:)", value=int(srv_actual['id_sensor_disco_3']), step=1)
                    edit_d4 = col_d4.number_input("Disco 4 (D:)", value=int(srv_actual['id_sensor_disco_4']), step=1)
                    edit_d5 = col_d5.number_input("Disco 5 (G:)", value=int(srv_actual['id_sensor_disco_5']), step=1)
                    
                    if st.form_submit_button("Aplicar Cambios"):
                        try:
                            upd_query = """
                                UPDATE servidores 
                                SET nombre_alias=%s, id_sensor_cpu=%s, id_sensor_ram=%s, 
                                    id_sensor_disco_1=%s, id_sensor_disco_2=%s, id_sensor_disco_3=%s, id_sensor_disco_4=%s, id_sensor_disco_5=%s,
                                    id_sensor_red=%s, id_sensor_latencia=%s
                                WHERE ip=%s
                            """
                            cursor.execute(upd_query, (
                                edit_alias.strip(), int(edit_cpu), int(edit_ram), 
                                int(edit_d1), int(edit_d2), int(edit_d3), int(edit_d4), int(edit_d5),
                                int(edit_red), int(edit_lat), ip_edit
                            ))
                            conn.commit()
                            st.success("Estructura multidisco modificada con éxito.")
                            st.session_state.accion_infra = None
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al actualizar: {ex}")

        # --- FORMULARIO DE DESACTIVACIÓN (Solo si hay selección activa) ---
        elif st.session_state.accion_infra == "desactivar" and hay_filtro:
            st.markdown("### ❌ Suspensión Lógica de Monitoreo")
            with st.form("form_baja_srv"):
                ip_des = st.selectbox("Seleccione Servidor a cambiar de estado", lista_ips)
                srv_baja = mapeo_servidores[ip_des]
                estado_actual_str = "ACTIVO" if srv_baja['estado_monitoreo'] == 1 else "INACTIVO"
                st.info(f"Estado de monitoreo actual en la granja: **{estado_actual_str}**")
                
                nuevo_est_bit = st.selectbox("Seleccione Nuevo Estado Lógico", ["Desactivar Monitoreo", "Activar Monitoreo"])
                
                if st.form_submit_button("Confirmar Estado"):
                    bit_val = 0 if "Desactivar" in nuevo_est_bit else 1
                    try:
                        cursor.execute("UPDATE servidores SET estado_monitoreo=%s WHERE ip=%s", (bit_val, ip_des))
                        conn.commit()
                        st.success(f"Nodo {ip_des} actualizado con éxito.")
                        st.session_state.accion_infra = None
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error: {ex}")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de servidores: {e}")

if __name__ == "__main__":
    mostrar_tabla_servidores()