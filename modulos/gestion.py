import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

# ==========================================================================
# FUNCIONES DE CALLBACK PARA PREVENIR REDIRECCIONES EN LOS SELECTBOX
# ==========================================================================
def cb_cambio_analista():
    st.session_state.filtro_analista = st.session_state.wb_filtro_analista
    st.session_state.accion_personal = None

def cb_limpiar_p1():
    st.session_state.filtro_analista = "-- Seleccione un Analista --"
    if "wb_filtro_analista" in st.session_state:
        del st.session_state["wb_filtro_analista"]
    st.session_state.accion_personal = None

def cb_cambio_auditoria():
    st.session_state.filtro_auditoria_usr = st.session_state.wb_filtro_auditoria
    
def cb_limpiar_p2():
    st.session_state.filtro_auditoria_usr = "-- Seleccione un Usuario --"
    if "wb_filtro_auditoria" in st.session_state:
        del st.session_state["wb_filtro_auditoria"]


def mostrar_pantalla(user_actual, user_id):
    # ==========================================================================
    # CONTROL DE ENTRADA Y ESTADOS INDEPENDIENTES
    # ==========================================================================
    if "modulo_actual" not in st.session_state:
        st.session_state.modulo_actual = "gestion_personal"
    
    if "filtro_analista" not in st.session_state:
        st.session_state.filtro_analista = "-- Seleccione un Analista --"
    if "accion_personal" not in st.session_state:
        st.session_state.accion_personal = None

    if "filtro_auditoria_usr" not in st.session_state:
        st.session_state.filtro_auditoria_usr = "-- Seleccione un Usuario --"

    if st.session_state.modulo_actual != "gestion_personal":
        st.session_state.filtro_analista = "-- Seleccione un Analista --"
        st.session_state.accion_personal = None
        st.session_state.filtro_auditoria_usr = "-- Seleccione un Usuario --"
        st.session_state.modulo_actual = "gestion_personal"

    rol_sanitizado = str(st.session_state.get("rol")).strip().upper() if st.session_state.get("rol") else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado

    if not es_seguridad:
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad o Administrador.")
        return

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
            
            div[data-testid="stInputInstructions"] {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
            }
            .stInput div[data-testid="stInputInstructions"] {
                display: none !important;
                visibility: hidden !important;
            }
            .modulo-banco div[data-testid="stInputInstructions"] {
                display: none !important;
                visibility: hidden !important;
            }
            .modulo-banco small {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
            }
            
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
            .modulo-banco div.stButton > button:hover {
                background-color: #001f3f !important;
                border: 1px solid #FFCC00 !important;
                color: #FFCC00 !important;
            }
            .modulo-banco div.stButton > button:hover p {
                color: #FFCC00 !important;
            }
            .modulo-banco div[data-testid="stForm"] div.stButton > button {
                background-color: #003366 !important;
                color: #FFFFFF !important;
            }
            .modulo-banco div[data-testid="stForm"] div.stButton > button p {
                color: #FFFFFF !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366;">👥 Gestión de Personal</h2>', unsafe_allow_html=True)
    st.markdown('<div class="modulo-banco">', unsafe_allow_html=True)
    st.markdown(f'<p class="analista-sesion-tag">Analista en sesión: <b>{user_actual}</b></p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["👤 Gestión de Personal", "📋 Tabla Histórico Usuarios"], key="tabs_gestion")

    # ==========================================================================
    # PESTAÑA 1: GESTIÓN DE PERSONAL
    # ==========================================================================
    with tab1:
        conn = None
        cursor = None

        try:
            conn = conectar_bd()
            if conn is None:
                st.error("❌ No se pudo establecer conexión con el servidor MySQL.")
            else:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, usuario, cargo FROM usuarios ORDER BY cargo ASC")
                lista_raw = cursor.fetchall()
                
                mapeo_opciones = {f"{u['cargo']} [{u['usuario']}]": u['id'] for u in lista_raw}
                opciones_selectbox = ["-- Seleccione un Analista --"] + list(mapeo_opciones.keys())

                idx_actual = 0
                if st.session_state.filtro_analista in opciones_selectbox:
                    idx_actual = opciones_selectbox.index(st.session_state.filtro_analista)

                col_f1, col_f2 = st.columns([3, 1])
                col_f1.selectbox(
                    "Filtrar Analistas por Cargo Institucional:",
                    options=opciones_selectbox,
                    index=idx_actual,
                    key="wb_filtro_analista",
                    on_change=cb_cambio_analista
                )
                
                col_f2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
                col_f2.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_p1_limpiar", on_click=cb_limpiar_p1)

                hay_filtro = st.session_state.filtro_analista != "-- Seleccione un Analista --"
                datos_filtrados = []

                if not hay_filtro:
                    st.info("💡 Por favor, seleccione un analista de la lista desplegable superior para evaluar sus credenciales y estatus corporativo.")
                else:
                    id_seleccionado = mapeo_opciones[st.session_state.filtro_analista]
                    cursor.execute("SELECT id, usuario, cargo, rol, estado FROM usuarios WHERE id = %s", (id_seleccionado,))
                    datos_filtrados = cursor.fetchall()

                if datos_filtrados:
                    html_lineas = []
                    html_lineas.append("""
                    <style>
                        .tabla-banco-usr { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
                        .tabla-banco-usr th { background-color: #003366 !important; color: #FFFFFF !important; font-weight: bold !important; text-align: center !important; padding: 12px 10px; border: 1px solid #dee2e6 !important; font-size: 13px; text-transform: uppercase; }
                        .tabla-banco-usr td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 10px; text-align: left; font-size: 13px; }
                        .tabla-banco-usr tr:nth-child(even) { background-color: #f8f9fa; }
                    </style>
                    """)
                    # SE REMOVIÓ EL ENCABEZADO "ID" DE LA TABLA
                    html_lineas.append('<table class="tabla-banco-usr"><thead><tr><th style="width: 30%;">USUARIO</th><th style="width: 40%;">CARGO INSTITUCIONAL</th><th style="width: 15%;">ROL</th><th style="width: 15%;">ESTATUS</th></tr></thead><tbody>')
                    
                    lista_ids = []
                    mapeo_usuarios = {}
                    
                    for u in datos_filtrados:
                        lista_ids.append(u['id'])
                        mapeo_usuarios[u['id']] = u
                        estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>' if u['estado'] == 1 else '<span style="color: #C62828; font-weight: bold;">SUSPENDIDO</span>'
                        
                        html_lineas.append('<tr>')
                        # SE DETECTÓ Y REMOVIÓ LA CELDA QUE RENDERIZABA EL VALOR DEL ID
                        html_lineas.append(f'<td><code>{u["usuario"]}</code></td>')
                        html_lineas.append(f'<td><b>{u["cargo"]}</b></td>')
                        html_lineas.append(f'<td style="text-align: center;">{str(u["rol"]).upper()}</td>')
                        html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                        html_lineas.append('</tr>')
                        
                    html_lineas.append('</tbody></table>')
                    st.components.v1.html("".join(html_lineas), height=max(180, len(datos_filtrados) * 42 + 65), scrolling=True)
                    st.markdown("---")

                if not hay_filtro:
                    if st.button("➕ Registrar Usuario", use_container_width=True, key="btn_p1_registrar_vista"):
                        st.session_state.accion_personal = "registrar"
                else:
                    col_b1, col_b2 = st.columns(2)
                    if col_b1.button("📝 Modificar Cargo Filtrado", use_container_width=True, key="btn_p1_modificar"):
                        st.session_state.accion_personal = "editar"
                    if col_b2.button("⚙️ Alterar Estatus Lógico", use_container_width=True, key="btn_p1_estatus"):
                        st.session_state.accion_personal = "estatus"

                # --- FORMULARIO DE REGISTRO ---
                if st.session_state.accion_personal == "registrar" and not hay_filtro:
                    st.markdown("### 📥 Nuevo Integrante")
                    with st.form("form_alta_usr"):
                        c1, c2 = st.columns(2)
                        f_user = c1.text_input("Usuario:")
                        f_pass = c2.text_input("Contraseña:", type="password")
                        f_cargo = c1.text_input("Cargo:")
                        f_rol = c2.selectbox("Rol institucional:", ["operador", "seguridad", "admin"])
                        
                        c_btn1, c_btn2 = st.columns(2)
                        guardar_click = c_btn1.form_submit_button("Guardar Credenciales", use_container_width=True)
                        cancelar_click = c_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if guardar_click:
                            if not f_user.strip() or not f_pass.strip() or not f_cargo.strip():
                                st.error("Error: Todos los campos del formulario son obligatorios.")
                            else:
                                crear_nuevo_usuario(f_user.strip(), f_pass, f_cargo.strip(), f_rol, user_id)

                # --- FORMULARIO DE MODIFICACIÓN ---
                elif st.session_state.accion_personal == "editar" and hay_filtro:
                    st.markdown("### 📝 Modificación de Credenciales Nominales")
                    id_edit = lista_ids[0]
                    usr_sel = mapeo_usuarios[id_edit]
                    
                    with st.form("form_edicion_usr"):
                        st.text_input("Identificador de Acceso (No modificable)", value=usr_sel['usuario'], disabled=True)
                        nuevo_cargo = st.text_input("Cargo:", value=usr_sel['cargo'])
                        justificacion = st.text_input("Justificación de Auditoría:")
                        
                        c_btn1, c_btn2 = st.columns(2)
                        aplicar_click = c_btn1.form_submit_button("Aplicar Modificación", use_container_width=True)
                        cancelar_click = c_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if aplicar_click:
                            if not nuevo_cargo.strip() or not justificacion.strip():
                                st.error("Debe ingresar el nuevo cargo y la correspondiente justificación.")
                            else:
                                ejecutar_update_nombre(usr_sel['usuario'], usr_sel['cargo'], nuevo_cargo.strip(), user_id, justificacion.strip())

                # --- FORMULARIO DE CAMBIO DE ESTADO ---
                elif st.session_state.accion_personal == "estatus" and hay_filtro:
                    st.markdown("### ⚙️ Alteración de Estatus Operativo")
                    id_est = lista_ids[0]
                    usr_sel = mapeo_usuarios[id_est]
                    estado_actual_str = "ACTIVO" if usr_sel['estado'] == 1 else "SUSPENDIDO"
                    st.info(f"Estatus actual del usuario en la base: **{estado_actual_str}**")
                    
                    with st.form("form_estatus_usr"):
                        nuevo_est_str = st.selectbox("Seleccione Nuevo Estatus Lógico", ["Activar Acceso", "Suspender Acceso"])
                        justificacion_est = st.text_input("Justificación de Auditoría obligatoria:")
                        
                        c_btn1, c_btn2 = st.columns(2)
                        confirmar_click = c_btn1.form_submit_button("Confirmar Estatus Lógico", use_container_width=True)
                        cancelar_click = c_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if confirmar_click:
                            if str(usr_sel['usuario']) == str(user_actual):
                                st.error("Operación inválida: No puede alterar las propiedades de su propio usuario activo.")
                            elif not justificacion_est.strip():
                                st.error("Error: Requiere una justificación válida.")
                            else:
                                ejecutar_update_estado(usr_sel['usuario'], usr_sel['estado'], user_id, user_actual, justificacion_est.strip())

        except Exception as e:
            st.error(f"Fallo técnico en módulo de personal: {e}")
        finally:
            if cursor is not None: cursor.close()
            if conn is not None: conn.close()

    # ==========================================================================
    # PESTAÑA 2: TABLA HISTÓRICO USUARIOS
    # ==========================================================================
    with tab2:
        conn_p2 = None
        cursor_p2 = None

        try:
            conn_p2 = conectar_bd()
            if conn_p2 is None:
                st.error("❌ No se pudo establecer conexión con el servidor MySQL.")
            else:
                cursor_p2 = conn_p2.cursor(dictionary=True)
                cursor_p2.execute("SELECT id, usuario FROM usuarios ORDER BY usuario ASC")
                raw_usuarios_p2 = cursor_p2.fetchall()
                
                opciones_auditoria = ["-- Seleccione un Usuario --"] + [row['usuario'] for row in raw_usuarios_p2]

                idx_auditoria = 0
                if st.session_state.filtro_auditoria_usr in opciones_auditoria:
                    idx_auditoria = opciones_auditoria.index(st.session_state.filtro_auditoria_usr)

                col_aud1, col_aud2 = st.columns([3, 1])
                col_aud1.selectbox(
                    "Filtrar Registros de Auditoría por Nombre de Usuario:",
                    options=opciones_auditoria,
                    index=idx_auditoria,
                    key="wb_filtro_auditoria",
                    on_change=cb_cambio_auditoria
                )
                
                col_aud2.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
                col_aud2.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_p2_limpiar", on_click=cb_limpiar_p2)

                if st.session_state.filtro_auditoria_usr == "-- Seleccione un Usuario --":
                    st.info("💡 Por favor, seleccione un usuario para evaluar sus operaciones históricas de auditoría.")
                else:
                    cursor_p2.execute(
                        "SELECT id_auditoria, fecha_evento, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, commentario "
                        "FROM historico_usuarios WHERE usuario_afectado = %s ORDER BY fecha_evento DESC",
                        (st.session_state.filtro_auditoria_usr,)
                    )
                    datos_auditoria_filtrados = cursor_p2.fetchall()

                    if datos_auditoria_filtrados:
                        html_lineas_aud = []
                        html_lineas_aud.append("""
                        <style>
                            .tabla-banco-usr { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
                            .tabla-banco-usr th { background-color: #003366 !important; color: #FFFFFF !important; font-weight: bold !important; text-align: center !important; padding: 12px 10px; border: 1px solid #dee2e6 !important; font-size: 13px; text-transform: uppercase; }
                            .tabla-banco-usr td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 10px; text-align: left; font-size: 13px; }
                            .tabla-banco-usr tr:nth-child(even) { background-color: #f8f9fa; }
                        </style>
                        """)
                        # SE REMOVIÓ EL ENCABEZADO "ID" DE LA TABLA DE AUDITORÍA
                        html_lineas_aud.append('<table class="tabla-banco-usr"><thead><tr><th style="width: 22%;">FECHA EVENTO</th><th style="width: 18%;">AFECTADO</th><th style="width: 22%;">ACCCIÓN</th><th style="width: 11%;">ANTERIOR</th><th style="width: 11%;">NUEVO</th><th style="width: 16%;">JUSTIFICACIÓN</th></tr></thead><tbody>')
                        
                        for row in datos_auditoria_filtrados:
                            val_ant = str(row['valor_anterior']) if row['valor_anterior'] is not None else "N/A"
                            val_nue = str(row['valor_nuevo']) if row['valor_nuevo'] is not None else "N/A"
                            comm = str(row['commentario']) if row['commentario'] is not None else "Sin observaciones"
                            
                            accion_raw = str(row['accion_realizada']).strip().upper()
                            
                            if accion_raw == "REGISTRO":
                                listado_texto = "registro de usuario"
                            elif accion_raw == "MOD_CARGO":
                                listado_texto = "modificacion de cargo"
                            elif accion_raw == "MOD_ESTADO":
                                if str(row['valor_nuevo']).strip().upper() == "SUSPENDIDO":
                                    listado_texto = "suspencion de usuario"
                                else:
                                    listado_texto = "activacion de usuaruo"
                            else:
                                listado_texto = accion_raw.lower()
                            
                            html_lineas_aud.append('<tr>')
                            # SE REMOVIÓ EL TD CORRESPONDIENTE AL ID_AUDITORIA
                            html_lineas_aud.append(f'<td style="font-size:12px; text-align: center;">{str(row["fecha_evento"])}</td>')
                            html_lineas_aud.append(f'<td><code>{row["usuario_afectado"]}</code></td>')
                            html_lineas_aud.append(f'<td style="text-align: center; font-weight: bold; color: #003366;">{listado_texto}</td>')
                            html_lineas_aud.append(f'<td>={val_ant}</td>')
                            html_lineas_aud.append(f'<td><b>{val_nue}</b></td>')
                            html_lineas_aud.append(f'<td style="font-style: italic; font-size:12px;">{comm}</td>')
                            html_lineas_aud.append('</tr>')
                            
                        html_lineas_aud.append('</tbody></table>')
                        st.components.v1.html("".join(html_lineas_aud), height=max(180, len(datos_auditoria_filtrados) * 45 + 65), scrolling=True)
                    else:
                        st.warning(f"No se encontraron transacciones en el histórico para el usuario '{st.session_state.filtro_auditoria_usr}'.")

        except Exception as e:
            st.error(f"Fallo técnico al procesar el histórico de auditoría: {e}")
        finally:
            if cursor_p2 is not None: cursor_p2.close()
            if conn_p2 is not None: conn_p2.close()

    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================================================
# FUNCIONES DE BACKEND
# ==========================================================================
def crear_nuevo_usuario(u, c, cargo_val, r, ejecutor_id):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (usuario, clave, cargo, rol) VALUES (%s, %s, %s, %s)", (u, c, cargo_val, r))
        conn.commit()
        registrar_auditoria_usuario(u, "REGISTRO", "N/A", f"ROL:{r}", ejecutor_id, "Alta institucional en SIMPOL")
        conn.close()
        st.success("Analista registrado exitosamente en el sistema.")
        
        st.session_state.filtro_analista = f"{cargo_val} [{u}]"
        st.session_state.accion_personal = None
        if "wb_filtro_analista" in st.session_state:
            del st.session_state["wb_filtro_analista"]
        st.rerun()
    except Exception as e: 
        st.error(f"Error de persistencia: {e}")

def ejecutar_update_nombre(log, v, n, ejecutor_id, mot):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET cargo=%s WHERE usuario=%s", (n, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_CARGO", v, n, ejecutor_id, mot)
        conn.close()
        st.success("Cargo institucional actualizado correctamente.")
        
        st.session_state.filtro_analista = f"{n} [{log}]"
        st.session_state.accion_personal = None
        if "wb_filtro_analista" in st.session_state:
            del st.session_state["wb_filtro_analista"]
        st.rerun()
    except Exception as e: 
        st.error(f"Error al actualizar: {e}")

def ejecutar_update_estado(log, est_v, ejecutor_id, ejecutor_log, mot):
    if str(log) == str(ejecutor_log): 
        st.error("Operación inválida: No puede alterar las propiedades de su propio usuario activo.")
        return
    n_est = 0 if est_v == 1 else 1
    v_v, v_n = ("ACTIVO", "SUSPENDIDO") if est_v == 1 else ("SUSPENDIDO", "ACTIVO")
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado=%s WHERE usuario=%s", (n_est, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_ESTADO", v_v, v_n, ejecutor_id, mot)
        
        cursor.execute("SELECT cargo FROM usuarios WHERE usuario=%s", (log,))
        cargo_actual = cursor.fetchone()
        conn.close()
        st.success(f"Estatus del analista {log} actualizado con éxito.")
        
        if cargo_actual:
            st.session_state.filtro_analista = f"{cargo_actual['cargo']} [{log}]"
        else:
            st.session_state.filtro_analista = "-- Seleccione un Analista --"
            
        st.session_state.accion_personal = None
        if "wb_filtro_analista" in st.session_state:
            del st.session_state["wb_filtro_analista"]
        st.rerun()
    except Exception as e: 
        st.error(f"Error al conmutar estatus: {e}")