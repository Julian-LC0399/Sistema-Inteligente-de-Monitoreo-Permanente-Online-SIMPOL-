import streamlit as st
from database import conectar_bd

def mostrar_tabla_servidores():
    # 1. ESTILOS CSS REFORZADOS
    st.markdown("""
        <style>
            .titulo-gestion { 
                color: #003366 !important; 
                font-size: 24px !important; 
                font-weight: bold !important; 
                margin-bottom: 15px;
                display: block;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<span class='titulo-gestion'>🖥️ GESTIÓN Y VISTA DE SERVIDORES</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    try:
        # Conexión exacta a la base de datos MySQL
        conn = conectar_bd()
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL. Verifica el servicio de base de datos.")
            return
            
        cursor = conn.cursor(dictionary=True)
        
        # Consulta de los parámetros de infraestructura (Sin departamento)
        query = """
            SELECT ip, nombre_alias, estado_monitoreo, fecha_alta, 
                   id_sensor_cpu, id_sensor_ram, id_sensor_disco, id_sensor_red, id_sensor_latencia 
            FROM servidores
        """
        cursor.execute(query)
        servidores = cursor.fetchall()
        
        if servidores:
            # 2. CONSTRUCCIÓN DE LA TABLA EN HTML PURO (Cero Pandas / Cero Numpy)
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
                    font-size: 13px;
                }
                .tabla-banco td { 
                    color: #000000 !important; 
                    border: 1px solid #dee2e6 !important; 
                    padding: 10px;
                    text-align: left;
                    font-size: 13px;
                }
                .tabla-banco tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
            </style>
            """)
            html_lineas.append('<table class="tabla-banco">')
            html_lineas.append("""
                <thead>
                    <tr>
                        <th>DIRECCIÓN IP</th>
                        <th>ALIAS DEL SERVIDOR</th>
                        <th>ID CPU</th>
                        <th>ID RAM</th>
                        <th>ID DISCO</th>
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
            
            for s in servidores:
                lista_ips.append(s['ip'])
                mapeo_servidores[s['ip']] = s
                
                estado = "🟢 ACTIVO" if s['estado_monitoreo'] == 1 else "🔴 INACTIVO"
                fecha_formateada = s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"
                
                cpu = s['id_sensor_cpu'] if s['id_sensor_cpu'] != 0 else "No asignado"
                ram = s['id_sensor_ram'] if s['id_sensor_ram'] != 0 else "No asignado"
                disco = s['id_sensor_disco'] if s['id_sensor_disco'] != 0 else "No asignado"
                red = s['id_sensor_red'] if s['id_sensor_red'] != 0 else "No asignado"
                latencia = s['id_sensor_latencia'] if s['id_sensor_latencia'] != 0 else "No asignado"
                
                html_lineas.append('<tr>')
                html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                html_lineas.append(f'<td>{cpu}</td>')
                html_lineas.append(f'<td>{ram}</td>')
                html_lineas.append(f'<td>{disco}</td>')
                html_lineas.append(f'<td>{red}</td>')
                html_lineas.append(f'<td>{latencia}</td>')
                html_lineas.append(f'<td>{estado}</td>')
                html_lineas.append(f'<td>{fecha_formateada}</td>')
                html_lineas.append('</tr>')
                
            html_lineas.append('</tbody></table>')
            
            html_final = "".join(html_lineas)
            altura_vista = max(200, len(servidores) * 45 + 70)
            st.components.v1.html(html_final, height=altura_vista, scrolling=True)
            
            st.markdown("---")
            
            # 3. INTERFAZ DE OPERACIONES (BOTONES)
            col_b1, col_b2, col_b3 = st.columns(3)
            
            # Inicializar estados de formularios en session_state si no existen
            if "accion_infra" not in st.session_state:
                st.session_state.accion_infra = None

            if col_b1.button("➕ Registrar Servidor", use_container_width=True):
                st.session_state.accion_infra = "registrar"
            if col_b2.button("📝 Editar Servidor", use_container_width=True):
                st.session_state.accion_infra = "editar"
            if col_b3.button("❌ Desactivar Servidor", use_container_width=True):
                st.session_state.accion_infra = "desactivar"

            # --- FORMULARIO DE REGISTRO ---
            if st.session_state.accion_infra == "registrar":
                st.markdown("### 📥 Alta de Nuevo Servidor")
                with st.form("form_registro_srv"):
                    reg_ip = st.text_input("Dirección IP (Única)")
                    reg_alias = st.text_input("Alias / Nombre Comercial")
                    col_r1, col_r2, col_r3 = st.columns(3)
                    reg_cpu = col_r1.number_input("ID Sensor CPU", value=0, step=1)
                    reg_ram = col_r2.number_input("ID Sensor RAM", value=0, step=1)
                    reg_disco = col_r3.number_input("ID Sensor Disco", value=0, step=1)
                    col_r4, col_r5 = st.columns(2)
                    reg_red = col_r4.number_input("ID Sensor Red", value=0, step=1)
                    reg_lat = col_r5.number_input("ID Sensor Latencia", value=0, step=1)
                    
                    btn_guardar_reg = st.form_submit_button("Guardar Servidor")
                    if btn_guardar_reg:
                        if not reg_ip or not reg_alias:
                            st.error("Campos obligatorios vacíos.")
                        else:
                            try:
                                ins_query = """
                                    INSERT INTO servidores (ip, nombre_alias, id_sensor_cpu, id_sensor_ram, id_sensor_disco, id_sensor_red, id_sensor_latencia)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """
                                cursor.execute(ins_query, (reg_ip, reg_alias, reg_cpu, reg_ram, reg_disco, reg_red, reg_lat))
                                conn.commit()
                                st.success("Servidor añadido al catálogo.")
                                st.session_state.accion_infra = None
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error de duplicado o persistencia: {ex}")

            # --- FORMULARIO DE EDICIÓN ---
            elif st.session_state.accion_infra == "editar":
                st.markdown("### 📝 Modificación de Parámetros Técnicos")
                ip_edit = st.selectbox("Seleccione la IP del Servidor a Modificar", lista_ips)
                
                if ip_edit:
                    srv_actual = mapeo_servidores[ip_edit]
                    fecha_act = srv_actual['fecha_alta'].strftime("%Y-%m-%d %H:%M") if srv_actual['fecha_alta'] else "N/A"
                    
                    with st.form("form_edicion_srv"):
                        # Campo de fecha NO editable (Bloqueado por parámetro disabled)
                        st.text_input("Fecha de Alta Institucional (No modificable)", value=fecha_act, disabled=True)
                        
                        edit_alias = st.text_input("Alias / Nombre Comercial", value=srv_actual['nombre_alias'])
                        col_e1, col_e2, col_e3 = st.columns(3)
                        edit_cpu = col_e1.number_input("ID Sensor CPU", value=int(srv_actual['id_sensor_cpu']), step=1)
                        edit_ram = col_e2.number_input("ID Sensor RAM", value=int(srv_actual['id_sensor_ram']), step=1)
                        edit_disco = col_e3.number_input("ID Sensor Disco", value=int(srv_actual['id_sensor_disco']), step=1)
                        col_e4, col_e5 = st.columns(2)
                        edit_red = col_e4.number_input("ID Sensor Red", value=int(srv_actual['id_sensor_red']), step=1)
                        edit_lat = col_e5.number_input("ID Sensor Latencia", value=int(srv_actual['id_sensor_latencia']), step=1)
                        
                        btn_guardar_edit = st.form_submit_button("Aplicar Cambios")
                        if btn_guardar_edit:
                            try:
                                upd_query = """
                                    UPDATE servidores 
                                    SET nombre_alias=%s, id_sensor_cpu=%s, id_sensor_ram=%s, id_sensor_disco=%s, id_sensor_red=%s, id_sensor_latencia=%s
                                    WHERE ip=%s
                                """
                                cursor.execute(upd_query, (edit_alias, edit_cpu, edit_ram, edit_disco, edit_red, edit_lat, ip_edit))
                                conn.commit()
                                st.success("Estructura de sensores modificada con éxito.")
                                st.session_state.accion_infra = None
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error al actualizar: {ex}")

            # --- FORMULARIO DE DESACTIVACIÓN ---
            elif st.session_state.accion_infra == "desactivar":
                st.markdown("### ❌ Suspensión Lógica de Monitoreo")
                with st.form("form_baja_srv"):
                    ip_des = st.selectbox("Seleccione Servidor a cambiar de estado", lista_ips)
                    srv_baja = mapeo_servidores[ip_des]
                    estado_actual_str = "🟢 ACTIVO" if srv_baja['estado_monitoreo'] == 1 else "🔴 INACTIVO"
                    st.info(f"Estado de monitoreo actual en la granja: **{estado_actual_str}**")
                    
                    nuevo_est_bit = st.selectbox("Seleccione Nuevo Estado Lógico", ["🔴 Desactivar Monitoreo", "🟢 Activar Monitoreo"])
                    
                    btn_baja = st.form_submit_button("Confirmar Estado")
                    if btn_baja:
                        bit_val = 0 if "Desactivar" in nuevo_est_bit else 1
                        try:
                            cursor.execute("UPDATE servidores SET estado_monitoreo=%s WHERE ip=%s", (bit_val, ip_des))
                            conn.commit()
                            st.success(f"Nodo {ip_des} actualizado con éxito.")
                            st.session_state.accion_infra = None
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")
            
        else:
            st.warning("No se encontraron servidores registrados en la base de datos.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de servidores: {e}")

if __name__ == "__main__":
    mostrar_tabla_servidores()