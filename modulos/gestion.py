import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

def mostrar_pantalla(user_actual, user_id):
    # 1. SEGURIDAD DE ROL
    rol_sanitizado = str(st.session_state.get("rol")).strip().upper() if st.session_state.get("rol") else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado

    if not es_seguridad:
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad o Administrador.")
        return

    # 2. CSS ENCAPSULADO PARA BOTONES Y TABLAS
    st.markdown("""
        <style>
            .modulo-banco .analista-sesion-tag {
                color: #546E7A !important;
                font-size: 14px !important;
                margin-top: -10px;
                margin-bottom: 20px;
                display: block;
                line-height: 1.2;
            }
            
            /* Afectar ÚNICAMENTE a los botones que estén dentro de .modulo-banco */
            .modulo-banco div.stButton > button {
                background-color: #003366 !important;
                color: #FFFFFF !important;
                border: 1px solid #003366 !important;
                border-radius: 0px !important;
                font-weight: bold !important;
                text-transform: uppercase !important;
                height: 42px !important;
                transition: 0.3s ease;
            }
            
            .modulo-banco div.stButton > button p {
                color: #FFFFFF !important;
                font-weight: bold !important;
            }
            
            /* Efecto Hover Acotado */
            .modulo-banco div.stButton > button:hover {
                background-color: #001f3f !important;
                border: 1px solid #FFCC00 !important;
                color: #FFCC00 !important;
            }
            .modulo-banco div.stButton > button:hover p {
                color: #FFCC00 !important;
            }

            /* Forzar también los botones de los formularios dentro de este módulo */
            .modulo-banco div[data-testid="stForm"] div.stButton > button {
                background-color: #003366 !important;
                color: #FFFFFF !important;
            }
            .modulo-banco div[data-testid="stForm"] div.stButton > button p {
                color: #FFFFFF !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # ENCABEZADO CON TU SINTAXIS EXACTA REPLICADA
    # ==========================================================================
    st.markdown('<h2 style="color:#003366;">👥 Gestión de Personal</h2>', unsafe_allow_html=True)

    # Contenedor HTML Maestro para encapsular el resto de los estilos del módulo
    st.markdown('<div class="modulo-banco">', unsafe_allow_html=True)
    st.markdown(f'<p class="analista-sesion-tag">Analista en sesión: <b>{user_actual}</b></p>', unsafe_allow_html=True)

    # Inicializar estados de sesión para el filtro de analistas y acciones
    if "filtro_analista" not in st.session_state:
        st.session_state.filtro_analista = "-- Seleccione un Analista --"
    if "accion_personal" not in st.session_state:
        st.session_state.accion_personal = None

    try:
        conn = conectar_bd()
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL. Verifica el servicio de base de datos.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
            
        cursor = conn.cursor(dictionary=True)
        
        # 1. CARGA DINÁMICA DE USUARIOS PARA EL SELECTBOX (Formato: Cargo [usuario] v3.3)
        cursor.execute("SELECT id, usuario, cargo FROM usuarios ORDER BY cargo ASC")
        lista_raw = cursor.fetchall()
        
        # Mapeamos un diccionario para identificar fácilmente la selección y construir las opciones
        mapeo_opciones = {f"{u['cargo']} [{u['usuario']}]": u['id'] for u in lista_raw}
        opciones_selectbox = ["-- Seleccione un Analista --"] + list(mapeo_opciones.keys())

        # Determinar índice para permanencia del estado
        idx_actual = 0
        if st.session_state.filtro_analista in opciones_selectbox:
            idx_actual = opciones_selectbox.index(st.session_state.filtro_analista)

        # ==========================================================================
        # SECCIÓN DE FILTRADO (Control por clic con alineación exacta a 36px)
        # ==========================================================================
        col_f1, col_f2 = st.columns([3, 1])
        
        seleccion = col_f1.selectbox(
            "Filtrar Analistas por Cargo Institucional:",
            options=opciones_selectbox,
            index=idx_actual
        )
        
        # Espaciado de alineación milimétrica homologada
        col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
        
        if col_f2.button("🧹 Limpiar Filtro", use_container_width=True):
            st.session_state.filtro_analista = "-- Seleccione un Analista --"
            st.session_state.accion_personal = None
            st.rerun()

        if seleccion != st.session_state.filtro_analista:
            st.session_state.filtro_analista = seleccion
            st.session_state.accion_personal = None
            st.rerun()

        # Validación del estado del filtro
        hay_filtro = st.session_state.filtro_analista != "-- Seleccione un Analista --"
        datos_filtrados = []

        if not hay_filtro:
            st.info("💡 Por favor, seleccione un analista de la lista desplegable superior para evaluar sus credenciales y estatus corporativo.")
        else:
            # Obtener el ID correspondiente al registro seleccionado
            id_seleccionado = mapeo_opciones[st.session_state.filtro_analista]
            cursor.execute("SELECT id, usuario, cargo, rol, estado FROM usuarios WHERE id = %s", (id_seleccionado,))
            datos_filtrados = cursor.fetchall()

        # ==========================================================================
        # RENDERIZADO DE TABLA (Solo si hay un analista seleccionado)
        # ==========================================================================
        if datos_filtrados:
            html_lineas = []
            html_lineas.append("""
            <style>
                .tabla-banco-usr {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                }
                .tabla-banco-usr th {
                    background-color: #003366 !important;
                    color: #FFFFFF !important;
                    font-weight: bold !important;
                    text-align: center !important;
                    padding: 12px 10px;
                    border: 1px solid #dee2e6 !important;
                    font-size: 13px;
                    text-transform: uppercase;
                }
                .tabla-banco-usr td { 
                    color: #000000 !important; 
                    border: 1px solid #dee2e6 !important; 
                    padding: 10px;
                    text-align: left;
                    font-size: 13px;
                }
                .tabla-banco-usr tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
            </style>
            """)
            html_lineas.append('<table class="tabla-banco-usr">')
            html_lineas.append("""
                <thead>
                    <tr>
                        <th style="width: 10%;">ID</th>
                        <th style="width: 25%;">USUARIO</th>
                        <th style="width: 35%;">CARGO INSTITUCIONAL</th>
                        <th style="width: 15%;">ROL</th>
                        <th style="width: 15%;">ESTATUS</th>
                    </tr>
                </thead>
            """)
            html_lineas.append('<tbody>')
            
            lista_ids = []
            mapeo_usuarios = {}
            
            for u in datos_filtrados:
                lista_ids.append(u['id'])
                mapeo_usuarios[u['id']] = u
                
                if u['estado'] == 1:
                    estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>'
                else:
                    estado_html = '<span style="color: #C62828; font-weight: bold;">SUSPENDIDO</span>'
                
                html_lineas.append('<tr>')
                html_lineas.append(f'<td style="text-align: center;"><b>{u["id"]}</b></td>')
                html_lineas.append(f'<td><code>{u["usuario"]}</code></td>')
                html_lineas.append(f'<td><b>{u["cargo"]}</b></td>')
                html_lineas.append(f'<td style="text-align: center;">{str(u["rol"]).upper()}</td>')
                html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                html_lineas.append('</tr>')
                
            html_lineas.append('</tbody></table>')
            
            html_final = "".join(html_lineas)
            altura_vista = max(180, len(datos_filtrados) * 42 + 65)
            st.components.v1.html(html_final, height=altura_vista, scrolling=True)
            st.markdown("---")

        # ==========================================================================
        # INTERFAZ DE OPERACIONES CONDICIONAL
        # ==========================================================================
        if not hay_filtro:
            # Caso 1: Sin selección -> Solo se permite "Registrar Usuario"
            if st.button("➕ Registrar Usuario", use_container_width=True):
                st.session_state.accion_personal = "registrar"
        else:
            # Caso 2: Analista seleccionado -> Habilitar "Modificar" y "Alterar Estatus"
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("📝 Modificar Cargo Filtrado", use_container_width=True):
                st.session_state.accion_personal = "editar"
            if col_b2.button("⚙️ Alterar Estatus Lógico", use_container_width=True):
                st.session_state.accion_personal = "estatus"

        # --- FORMULARIO DE REGISTRO (Solo si no hay filtro) ---
        if st.session_state.accion_personal == "registrar" and not hay_filtro:
            st.markdown("### 📥 Nuevo Integrante")
            with st.form("form_alta_usr"):
                c1, c2 = st.columns(2)
                f_user = c1.text_input("Usuario:")
                f_pass = c2.text_input("Contraseña:", type="password")
                f_cargo = c1.text_input("Cargo:")
                f_rol = c2.selectbox("Rol institucional:", ["operador", "seguridad", "admin"])
                
                if st.form_submit_button("Guardar Credenciales"):
                    if not f_user.strip() or not f_pass.strip() or not f_cargo.strip():
                        st.error("Error: Todos los campos del formulario son de carácter obligatorio.")
                    else:
                        try:
                            cursor.execute("INSERT INTO usuarios (usuario, clave, cargo, rol) VALUES (%s, %s, %s, %s)", (f_user.strip(), f_pass, f_cargo.strip(), f_rol))
                            conn.commit()
                            registrar_auditoria_usuario(f_user.strip(), "REGISTRO", "N/A", f"ROL:{f_rol}", user_id, "Alta institucional en SIMPOL")
                            st.success("Analista registrado exitosamente en el sistema.")
                            st.session_state.accion_personal = None
                            st.rerun()
                        except Exception as ex:
                            if "Duplicate entry" in str(ex):
                                st.error("❌ Conflicto de Registro: El usuario ya se encuentra asignado.")
                            else:
                                st.error(f"Error de persistencia: {ex}")

        # --- FORMULARIO DE MODIFICACIÓN (Solo sobre nodo filtrado) ---
        elif st.session_state.accion_personal == "editar" and hay_filtro:
            st.markdown("### 📝 Modificación de Credenciales Nominales")
            id_edit = lista_ids[0] # Auto-asigna el ID del único analista en el visor estricto
            usr_sel = mapeo_usuarios[id_edit]
            
            with st.form("form_edicion_usr"):
                st.text_input("Identificador de Acceso (No modificable)", value=usr_sel['usuario'], disabled=True)
                nuevo_cargo = st.text_input("Cargo:", value=usr_sel['cargo'])
                justificacion = st.text_input("Justificación de Auditoría:")
                
                if st.form_submit_button("Aplicar Modificación"):
                    if not nuevo_cargo.strip() or not justificacion.strip():
                        st.error("Debe ingresar el nuevo cargo y la correspondiente justificación de seguridad.")
                    else:
                        try:
                            cursor.execute("UPDATE usuarios SET cargo=%s WHERE id=%s", (nuevo_cargo.strip(), id_edit))
                            conn.commit()
                            registrar_auditoria_usuario(usr_sel['usuario'], "MOD_CARGO", usr_sel['cargo'], nuevo_cargo.strip(), user_id, justificacion.strip())
                            st.success("Cargo institucional actualizado correctamente.")
                            st.session_state.accion_personal = None
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al actualizar: {ex}")

        # --- FORMULARIO DE CAMBIO DE ESTADO (Solo sobre nodo filtrado) ---
        elif st.session_state.accion_personal == "estatus" and hay_filtro:
            st.markdown("### ⚙️ Alteración de Estatus Operativo")
            id_est = lista_ids[0]
            usr_sel = mapeo_usuarios[id_est]
            estado_actual_str = "ACTIVO" if usr_sel['estado'] == 1 else "SUSPENDIDO"
            st.info(f"Estatus actual del usuario en la base: **{estado_actual_str}**")
            
            with st.form("form_estatus_usr"):
                nuevo_est_str = st.selectbox("Seleccione Nuevo Estatus Lógico", ["Activar Acceso", "Suspender Acceso"])
                justificacion_est = st.text_input("Justificación de Auditoría obligatoria:")
                
                if st.form_submit_button("Confirmar Estatus Lógico"):
                    if str(usr_sel['usuario']) == str(user_actual):
                        st.error("Operación inválida: No puede revocar o alterar las propiedades de su propio usuario activo.")
                    elif not justificacion_est.strip():
                        st.error("Error: Toda alteración de estatus de seguridad requiere una justificación válida.")
                    else:
                        bit_val = 1 if "Activar" in nuevo_est_str else 0
                        v_v, v_n = ("ACTIVO", "SUSPENDIDO") if usr_sel['estado'] == 1 else ("SUSPENDIDO", "ACTIVO")
                        try:
                            cursor.execute("UPDATE usuarios SET estado=%s WHERE id=%s", (bit_val, id_est))
                            conn.commit()
                            registrar_auditoria_usuario(usr_sel['usuario'], "MOD_ESTADO", v_v, v_n, user_id, justificacion_est.strip())
                            st.success(f"Estatus del analista {usr_sel['usuario']} actualizado con éxito.")
                            st.session_state.accion_personal = None
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")

        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de personal: {e}")

    # Cierre del contenedor maestro seguro
    st.markdown('</div>', unsafe_allow_html=True)


# --- FUNCIONES DE BACKEND AUTOMATIZADAS (Mantenidas por compatibilidad de arquitectura) ---
def crear_nuevo_usuario(u, c, cargo_val, r, ejecutor_id):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (usuario, clave, cargo, rol) VALUES (%s, %s, %s, %s)", (u, c, cargo_val, r))
        conn.commit()
        registrar_auditoria_usuario(u, "REGISTRO", "N/A", f"ROL:{r}", ejecutor_id, "Alta institucional")
        conn.close(); st.success("Registrado."); st.session_state.mostrar_registro = False; st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_nombre(log, v, n, ejecutor_id, mot):
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET cargo=%s WHERE usuario=%s", (n, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_CARGO", v, n, ejecutor_id, mot)
        conn.close(); st.success("Cargo actualizado."); st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def ejecutar_update_estado(log, est_v, ejecutor_id, ejecutor_log, mot):
    if str(log) == str(ejecutor_log): st.error("No puede auto-suspenderse."); return
    n_est = 0 if est_v == 1 else 1
    v_v, v_n = ("ACTIVO", "SUSPENDIDO") if est_v == 1 else ("SUSPENDIDO", "ACTIVO")
    try:
        conn = conectar_bd(); cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (n_est, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_ESTADO", v_v, v_n, ejecutor_id, mot)
        conn.close(); st.success(f"Estatus modificado a: {v_n}."); st.rerun()
    except Exception as e: st.error(f"Error: {e}")