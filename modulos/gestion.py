import streamlit as st
from database import conectar_bd, registrar_auditoria_usuario

# ==========================================================================
# FUNCIONES DE CALLBACK
# ==========================================================================
def cb_limpiar_p1():
    # Resetear completamente el estado del filtro
    st.session_state.filtro_analista = "-- Seleccione un Analista --"
    st.session_state.filtro_aplicado_p1 = False
    st.session_state.accion_personal = None
    # Forzar que el selectbox también se resetee
    st.session_state.wb_filtro_analista = "-- Seleccione un Analista --"

def cb_limpiar_p2():
    # Resetear completamente el estado del filtro de auditoría
    st.session_state.filtro_auditoria_usr = "-- Seleccione un Usuario --"
    st.session_state.filtro_aplicado_p2 = False

def mostrar_pantalla(user_actual, user_id):
    # ==========================================================================
    # INICIALIZACIÓN DE ESTADO
    # ==========================================================================
    if "modulo_actual" not in st.session_state:
        st.session_state.modulo_actual = "gestion_personal"
    
    if "filtro_analista" not in st.session_state:
        st.session_state.filtro_analista = "-- Seleccione un Analista --"
    if "accion_personal" not in st.session_state:
        st.session_state.accion_personal = None
    if "filtro_aplicado_p1" not in st.session_state:
        st.session_state.filtro_aplicado_p1 = False
    if "wb_filtro_analista" not in st.session_state:
        st.session_state.wb_filtro_analista = "-- Seleccione un Analista --"

    if "filtro_auditoria_usr" not in st.session_state:
        st.session_state.filtro_auditoria_usr = "-- Seleccione un Usuario --"
    if "filtro_aplicado_p2" not in st.session_state:
        st.session_state.filtro_aplicado_p2 = False

    # ==========================================================================
    # VALIDACIÓN DE PERMISOS
    # ==========================================================================
    rol_sanitizado = str(st.session_state.get("rol")).strip().upper() if st.session_state.get("rol") else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado or "OFICIAL" in rol_sanitizado

    if not es_seguridad:
        st.error("🚫 Acceso denegado. Se requieren permisos de Oficial de Seguridad o Administrador.")
        return

    # ==========================================================================
    # PROCESAR LIMPIEZA DE FILTROS VIA QUERY_PARAMS (MANTENIDO)
    # ==========================================================================
    if "_limpiar_p1" in st.query_params and st.query_params["_limpiar_p1"] == "1":
        cb_limpiar_p1()
        del st.query_params["_limpiar_p1"]
        st.rerun()

    if "_limpiar_p2" in st.query_params and st.query_params["_limpiar_p2"] == "1":
        cb_limpiar_p2()
        del st.query_params["_limpiar_p2"]
        st.rerun()

    # ==========================================================================
    # CSS Y ENCABEZADO
    # ==========================================================================
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
            .info-analista-gestion {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-gestion span {
                color: #003366;
                font-weight: 700;
            }
            div[data-testid="stInputInstructions"] {
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
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366;">👥 Gestión de Personal</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-gestion">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="modulo-banco">', unsafe_allow_html=True)

    # ==========================================================================
    # TABS
    # ==========================================================================
    tab1, tab2 = st.tabs(["👤 Gestión de Personal", "📋 Tabla Histórico Usuarios"])

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
                opciones_selectbox = ["-- Seleccione un Analista --", "-- Todos los Analistas --"] + list(mapeo_opciones.keys())

                # =============================================================
                # FILTROS - CORREGIDO CON LIMPIEZA TOTAL
                # =============================================================
                col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
                with col_f1:
                    # El selectbox se sincroniza con filtro_analista
                    current_value = st.session_state.get("filtro_analista", "-- Seleccione un Analista --")
                    
                    # Si el valor actual no está en las opciones, usar el primero
                    if current_value not in opciones_selectbox:
                        current_value = "-- Seleccione un Analista --"
                    
                    selected = st.selectbox(
                        "Filtrar Analistas por Cargo Institucional:",
                        options=opciones_selectbox,
                        index=opciones_selectbox.index(current_value) if current_value in opciones_selectbox else 0,
                        key="wb_filtro_analista",
                        label_visibility="collapsed"
                    )
                    
                    # Actualizar filtro_analista con el valor seleccionado
                    st.session_state.filtro_analista = selected
                
                with col_f2:
                    if st.button("🔍 Filtrar", key="btn_filtrar_p1", use_container_width=True):
                        st.session_state.filtro_aplicado_p1 = True
                        st.session_state.accion_personal = None
                        st.rerun()
                
                with col_f3:
                    if st.button("🧹 Limpiar", key="btn_p1_limpiar", use_container_width=True):
                        # Usar query_params para forzar la limpieza
                        st.query_params["_limpiar_p1"] = "1"
                        st.rerun()

                # =============================================================
                # PROCESAMIENTO DE DATOS
                # =============================================================
                filtro_actual = st.session_state.get("filtro_analista", "-- Seleccione un Analista --")
                filtro_aplicado = st.session_state.get("filtro_aplicado_p1", False)
                mostrar_todos = (filtro_actual == "-- Todos los Analistas --")
                hay_filtro_especifico = (filtro_actual != "-- Seleccione un Analista --" and filtro_actual != "-- Todos los Analistas --")

                datos_filtrados = []

                # Solo mostrar datos si el filtro está aplicado Y hay una selección válida
                if not filtro_aplicado:
                    st.info("👤 Seleccione un analista o 'Todos los Analistas' y presione 'Filtrar' para evaluar sus credenciales y estatus corporativo.")
                elif filtro_actual == "-- Seleccione un Analista --":
                    st.warning("⚠️ Por favor, seleccione una opción válida y presione 'Filtrar'.")
                elif mostrar_todos:
                    cursor.execute("SELECT id, usuario, cargo, rol, estado FROM usuarios ORDER BY cargo ASC")
                    datos_filtrados = cursor.fetchall()
                    if datos_filtrados:
                        st.success(f"✅ Mostrando {len(datos_filtrados)} analistas")
                elif hay_filtro_especifico and filtro_actual in mapeo_opciones:
                    id_seleccionado = mapeo_opciones[filtro_actual]
                    cursor.execute("SELECT id, usuario, cargo, rol, estado FROM usuarios WHERE id = %s", (id_seleccionado,))
                    datos_filtrados = cursor.fetchall()
                    if datos_filtrados:
                        st.success("✅ Mostrando analista seleccionado")

                # =============================================================
                # MOSTRAR TABLA - SOLO SI HAY DATOS FILTRADOS
                # =============================================================
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
                    html_lineas.append('<table class="tabla-banco-usr"><thead><tr><th style="width: 30%;">USUARIO</th><th style="width: 40%;">CARGO INSTITUCIONAL</th><th style="width: 15%;">ROL</th><th style="width: 15%;">ESTATUS</th></tr></thead><tbody>')
                    
                    lista_ids = []
                    mapeo_usuarios = {}
                    
                    for u in datos_filtrados:
                        lista_ids.append(u['id'])
                        mapeo_usuarios[u['id']] = u
                        estado_html = '<span style="color: #2E7D32; font-weight: bold;">ACTIVO</span>' if u['estado'] == 1 else '<span style="color: #C62828; font-weight: bold;">SUSPENDIDO</span>'
                        
                        html_lineas.append('<tr>')
                        html_lineas.append(f'<td><code>{u["usuario"]}</code></td>')
                        html_lineas.append(f'<td><b>{u["cargo"]}</b></td>')
                        html_lineas.append(f'<td style="text-align: center;">{str(u["rol"]).upper()}</td>')
                        html_lineas.append(f'<td style="text-align: center;">{estado_html}</td>')
                        html_lineas.append('</tr>')
                        
                    html_lineas.append('</tbody></table>')
                    st.components.v1.html("".join(html_lineas), height=max(180, len(datos_filtrados) * 42 + 65), scrolling=True)
                    st.markdown("---")

                # =============================================================
                # BOTONES DE ACCIÓN
                # =============================================================
                # Botón Registrar siempre visible
                if st.button("➕ Registrar Usuario", key="btn_registrar_siempre", use_container_width=True):
                    st.session_state.accion_personal = "registrar"
                    st.rerun()

                # Botones de modificación solo si hay filtro específico Y datos mostrados
                if filtro_aplicado and hay_filtro_especifico and datos_filtrados:
                    col_b1, col_b2 = st.columns(2)
                    if col_b1.button("📝 Modificar Cargo", key="btn_modificar", use_container_width=True):
                        st.session_state.accion_personal = "editar"
                        st.rerun()
                    if col_b2.button("⚙️ Alterar Estatus", key="btn_estatus", use_container_width=True):
                        st.session_state.accion_personal = "estatus"
                        st.rerun()

                # =============================================================
                # FORMULARIOS
                # =============================================================
                # REGISTRO
                if st.session_state.get("accion_personal") == "registrar":
                    st.markdown("### 📥 Nuevo Integrante")
                    with st.form("form_alta_usr"):
                        c1, c2 = st.columns(2)
                        f_user = c1.text_input("Usuario:")
                        f_pass = c2.text_input("Contraseña:", type="password")
                        f_cargo = c1.text_input("Cargo:")
                        f_rol = c2.selectbox("Rol institucional:", ["operador", "seguridad", "admin"])
                        
                        col_btn1, col_btn2 = st.columns(2)
                        guardar_click = col_btn1.form_submit_button("💾 Guardar Credenciales", use_container_width=True)
                        cancelar_click = col_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if guardar_click:
                            if not f_user.strip() or not f_pass.strip() or not f_cargo.strip():
                                st.error("❌ Todos los campos son obligatorios.")
                            else:
                                crear_nuevo_usuario(f_user.strip(), f_pass, f_cargo.strip(), f_rol, user_id)

                # MODIFICACIÓN
                if st.session_state.get("accion_personal") == "editar" and hay_filtro_especifico and datos_filtrados:
                    st.markdown("### 📝 Modificación de Credenciales")
                    usr_sel = datos_filtrados[0]
                    
                    with st.form("form_edicion_usr"):
                        st.text_input("Usuario (no modificable)", value=usr_sel['usuario'], disabled=True)
                        nuevo_cargo = st.text_input("Nuevo Cargo:", value=usr_sel['cargo'])
                        justificacion = st.text_input("Justificación:")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        aplicar_click = col_btn1.form_submit_button("💾 Aplicar Cambios", use_container_width=True)
                        cancelar_click = col_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if aplicar_click:
                            if not nuevo_cargo.strip() or not justificacion.strip():
                                st.error("❌ Todos los campos son obligatorios.")
                            else:
                                ejecutar_update_nombre(usr_sel['usuario'], usr_sel['cargo'], nuevo_cargo.strip(), user_id, justificacion.strip())

                # ESTATUS
                if st.session_state.get("accion_personal") == "estatus" and hay_filtro_especifico and datos_filtrados:
                    st.markdown("### ⚙️ Alteración de Estatus")
                    usr_sel = datos_filtrados[0]
                    estado_actual = "ACTIVO" if usr_sel['estado'] == 1 else "SUSPENDIDO"
                    st.info(f"ℹ️ Estatus actual: **{estado_actual}**")
                    
                    with st.form("form_estatus_usr"):
                        nuevo_estado = st.selectbox("Nuevo Estatus:", ["Activar", "Suspender"])
                        justificacion = st.text_input("Justificación:")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        confirmar_click = col_btn1.form_submit_button("💾 Confirmar Cambio", use_container_width=True)
                        cancelar_click = col_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if cancelar_click:
                            st.session_state.accion_personal = None
                            st.rerun()
                            
                        if confirmar_click:
                            if usr_sel['usuario'] == user_actual:
                                st.error("🚫 No puede modificar su propio usuario.")
                            elif not justificacion.strip():
                                st.error("❌ La justificación es obligatoria.")
                            else:
                                ejecutar_update_estado(usr_sel['usuario'], usr_sel['estado'], user_id, user_actual, justificacion.strip())

        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ==========================================================================
    # PESTAÑA 2: HISTÓRICO - CORREGIDO
    # ==========================================================================
    with tab2:
        conn_p2 = None
        cursor_p2 = None

        try:
            conn_p2 = conectar_bd()
            if conn_p2 is None:
                st.error("❌ No se pudo establecer conexión.")
            else:
                cursor_p2 = conn_p2.cursor(dictionary=True)
                cursor_p2.execute("SELECT id, usuario FROM usuarios ORDER BY usuario ASC")
                raw_usuarios_p2 = cursor_p2.fetchall()
                
                opciones_auditoria = ["-- Seleccione un Usuario --", "-- Todos los Usuarios --"] + [row['usuario'] for row in raw_usuarios_p2]

                col_aud1, col_aud2, col_aud3 = st.columns([3, 1, 1])
                with col_aud1:
                    current_value_p2 = st.session_state.get("filtro_auditoria_usr", "-- Seleccione un Usuario --")
                    if current_value_p2 not in opciones_auditoria:
                        current_value_p2 = "-- Seleccione un Usuario --"
                    
                    st.selectbox(
                        "Filtrar por Usuario:",
                        options=opciones_auditoria,
                        index=opciones_auditoria.index(current_value_p2) if current_value_p2 in opciones_auditoria else 0,
                        key="filtro_auditoria_usr",
                        label_visibility="collapsed"
                    )
                
                with col_aud2:
                    if st.button("🔍 Filtrar", key="btn_filtrar_p2", use_container_width=True):
                        st.session_state.filtro_aplicado_p2 = True
                        st.rerun()
                
                with col_aud3:
                    if st.button("🧹 Limpiar", key="btn_p2_limpiar", use_container_width=True):
                        st.query_params["_limpiar_p2"] = "1"
                        st.rerun()

                filtro_aud = st.session_state.get("filtro_auditoria_usr", "-- Seleccione un Usuario --")
                filtro_aplicado_p2 = st.session_state.get("filtro_aplicado_p2", False)

                if not filtro_aplicado_p2:
                    st.info("👤 Seleccione un usuario o 'Todos los Usuarios' y presione 'Filtrar' para evaluar sus operaciones históricas de auditoría.")
                elif filtro_aud == "-- Seleccione un Usuario --":
                    st.warning("⚠️ Por favor, seleccione una opción válida.")
                else:
                    if filtro_aud == "-- Todos los Usuarios --":
                        cursor_p2.execute(
                            "SELECT id_auditoria, fecha_evento, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, commentario "
                            "FROM historico_usuarios ORDER BY fecha_evento DESC LIMIT 200"
                        )
                    else:
                        cursor_p2.execute(
                            "SELECT id_auditoria, fecha_evento, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, commentario "
                            "FROM historico_usuarios WHERE usuario_afectado = %s ORDER BY fecha_evento DESC",
                            (filtro_aud,)
                        )
                    
                    datos_aud = cursor_p2.fetchall()
                    
                    if datos_aud:
                        html = []
                        html.append("""
                        <style>
                            .tabla-banco-usr { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
                            .tabla-banco-usr th { background-color: #003366 !important; color: #FFFFFF !important; font-weight: bold !important; text-align: center !important; padding: 12px 10px; border: 1px solid #dee2e6 !important; font-size: 13px; text-transform: uppercase; }
                            .tabla-banco-usr td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 10px; text-align: left; font-size: 13px; }
                            .tabla-banco-usr tr:nth-child(even) { background-color: #f8f9fa; }
                        </style>
                        """)
                        html.append('<table class="tabla-banco-usr"><thead><tr><th>FECHA</th><th>USUARIO</th><th>ACCIÓN</th><th>ANTERIOR</th><th>NUEVO</th><th>JUSTIFICACIÓN</th></tr></thead><tbody>')
                        
                        for row in datos_aud:
                            val_ant = str(row['valor_anterior']) if row['valor_anterior'] else "N/A"
                            val_nue = str(row['valor_nuevo']) if row['valor_nuevo'] else "N/A"
                            comm = str(row['commentario']) if row['commentario'] else "Sin observaciones"
                            
                            accion = str(row['accion_realizada']).strip().upper()
                            if accion == "REGISTRO":
                                texto = "registro de usuario"
                            elif accion == "MOD_CARGO":
                                texto = "modificación de cargo"
                            elif accion == "MOD_ESTADO":
                                texto = "suspensión de usuario" if "SUSPENDIDO" in str(row['valor_nuevo']).upper() else "activación de usuario"
                            else:
                                texto = accion.lower()
                            
                            html.append('<tr>')
                            html.append(f'<td style="font-size:12px;">{row["fecha_evento"]}</td>')
                            html.append(f'<td><code>{row["usuario_afectado"]}</code></td>')
                            html.append(f'<td style="font-weight:bold;color:#003366;">{texto}</td>')
                            html.append(f'<td>{val_ant}</td>')
                            html.append(f'<td><b>{val_nue}</b></td>')
                            html.append(f'<td style="font-size:12px;font-style:italic;">{comm}</td>')
                            html.append('</tr>')
                        
                        html.append('</tbody></table>')
                        st.components.v1.html("".join(html), height=max(200, len(datos_aud) * 45 + 65), scrolling=True)
                    else:
                        st.warning(f"📭 No se encontraron transacciones en el histórico de auditoría.")

        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            if cursor_p2: cursor_p2.close()
            if conn_p2: conn_p2.close()

    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================================================
# FUNCIONES DE BACKEND (sin cambios)
# ==========================================================================
def crear_nuevo_usuario(u, c, cargo_val, r, ejecutor_id):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (usuario, clave, cargo, rol) VALUES (%s, %s, %s, %s)", (u, c, cargo_val, r))
        conn.commit()
        registrar_auditoria_usuario(u, "REGISTRO", "N/A", f"ROL:{r}", ejecutor_id, "Alta institucional en SIMPOL")
        conn.close()
        st.success("✅ Analista registrado exitosamente.")
        st.session_state.filtro_analista = f"{cargo_val} [{u}]"
        st.session_state.filtro_aplicado_p1 = True
        st.session_state.accion_personal = None
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error: {e}")

def ejecutar_update_nombre(log, v, n, ejecutor_id, mot):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET cargo=%s WHERE usuario=%s", (n, log))
        conn.commit()
        registrar_auditoria_usuario(log, "MOD_CARGO", v, n, ejecutor_id, mot)
        conn.close()
        st.success("✅ Cargo actualizado correctamente.")
        st.session_state.filtro_analista = f"{n} [{log}]"
        st.session_state.filtro_aplicado_p1 = True
        st.session_state.accion_personal = None
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error: {e}")

def ejecutar_update_estado(log, est_v, ejecutor_id, ejecutor_log, mot):
    if str(log) == str(ejecutor_log):
        st.error("🚫 No puede modificar su propio usuario.")
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
        st.success(f"✅ Estatus de {log} actualizado.")
        if cargo_actual:
            st.session_state.filtro_analista = f"{cargo_actual['cargo']} [{log}]"
        st.session_state.filtro_aplicado_p1 = True
        st.session_state.accion_personal = None
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error: {e}")