import streamlit as st
from database import conectar_bd
from datetime import datetime, timedelta

def mostrar_pantalla():
    # Estilos CSS Unificados para el módulo de auditoría
    st.markdown("""
        <style>
            /* Estilo para el texto del analista */
            .info-analista-auditoria {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-auditoria span {
                color: #003366;
                font-weight: 700;
            }
            /* Alinear botones verticalmente con los filtros */
            div[data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
            }
            div[data-testid="column"] button {
                margin-bottom: 0px;
                height: 38px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: #003366; font-family: sans-serif;'>🕵️ Control de Accesos y Auditoría</h2>", unsafe_allow_html=True)
    
    # ==========================================================================
    # MOSTRAR ANALISTA EN SESIÓN
    # ==========================================================================
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-auditoria">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # ==========================================================================
    # PESTAÑAS DE AUDITORÍA
    # ==========================================================================
    tab_accesos, tab_sesiones = st.tabs(["📊 Accesos al Sistema (Logins)", "🛡️ Actividad y Sesiones (Runtime)"])

    # Estilos de tabla compartidos y consistentes entre ambas pestañas
    estilo_tabla_unificado = """
    <style>
        .tabla-banco { width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }
        .tabla-banco th { background-color: #003366 !important; color: #FFFFFF !important; font-weight: bold !important; text-align: center !important; padding: 12px 10px; border: 1px solid #dee2e6 !important; font-size: 13px; text-transform: uppercase; }
        .tabla-banco td { color: #000000 !important; border: 1px solid #dee2e6 !important; padding: 10px; text-align: left; font-size: 13px; }
        .tabla-banco tr:nth-child(even) { background-color: #f8f9fa; }
        .badge-evento { background-color: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 12px; font-weight: bold; font-size: 11px; display: inline-block; }
        .usuario-nombre { font-weight: 600; color: #003366; }
    </style>
    """

    # ==========================================================================
    # PESTAÑA 1: ACCESOS AL SISTEMA (LOG_ACCESOS) - Sin columna Resultado
    # ==========================================================================
    with tab_accesos:
        if "_limpiar_auditoria" in st.query_params and st.query_params["_limpiar_auditoria"] == "1":
            st.session_state["filtro_usuario_auditoria"] = "-- Seleccione un Usuario --"
            st.session_state["fecha_desde_auditoria"] = (datetime.now() - timedelta(days=7)).date()
            st.session_state["fecha_hasta_auditoria"] = datetime.now().date()
            st.session_state["mostrar_resultados_acc"] = False
            del st.query_params["_limpiar_auditoria"]
            st.rerun()

        if "filtro_usuario_auditoria" not in st.session_state:
            st.session_state["filtro_usuario_auditoria"] = "-- Seleccione un Usuario --"
        if "fecha_desde_auditoria" not in st.session_state:
            st.session_state["fecha_desde_auditoria"] = (datetime.now() - timedelta(days=7)).date()
        if "fecha_hasta_auditoria" not in st.session_state:
            st.session_state["fecha_hasta_auditoria"] = datetime.now().date()
        if "mostrar_resultados_acc" not in st.session_state:
            st.session_state["mostrar_resultados_acc"] = False

        try:
            conn = conectar_bd()
            if not conn:
                st.error("❌ No se pudo establecer conexión con la base de datos.")
                return

            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT DISTINCT usuario FROM log_accesos ORDER BY usuario ASC")
            usuarios_db = cursor.fetchall()
            lista_usuarios = ["-- Seleccione un Usuario --", "-- Todos los Usuarios --"] + [u["usuario"] for u in usuarios_db]

            col_f1, col_f2, col_f3 = st.columns([3, 1, 1])

            with col_f1:
                st.selectbox(
                    "👤 Filtrar por Usuario (Accesos)",
                    options=lista_usuarios,
                    key="filtro_usuario_auditoria",
                    label_visibility="collapsed"
                )

            with col_f2:
                if st.button("🔍 Filtrar", use_container_width=True, key="btn_filtrar_auditoria"):
                    st.session_state["mostrar_resultados_acc"] = True
                    st.rerun()

            with col_f3:
                if st.button("🧹 Limpiar", use_container_width=True, key="btn_limpiar_auditoria"):
                    st.query_params["_limpiar_auditoria"] = "1"
                    st.rerun()

            st.markdown("---")

            usuario_seleccionado = st.session_state["filtro_usuario_auditoria"]
            hay_usuario = usuario_seleccionado != "-- Seleccione un Usuario --"
            mostrar_todos = usuario_seleccionado == "-- Todos los Usuarios --"

            if hay_usuario or mostrar_todos:
                col_f3, col_f4 = st.columns([2, 2])
                with col_f3:
                    st.date_input("📅 Desde", key="fecha_desde_auditoria")
                with col_f4:
                    st.date_input("📅 Hasta", key="fecha_hasta_auditoria")
                st.markdown("---")

            if not st.session_state["mostrar_resultados_acc"]:
                if hay_usuario or mostrar_todos:
                    st.info("🔍 Seleccione el rango de fechas y presione **Filtrar** para visualizar el historial de accesos.")
                else:
                    st.info("👤 Por favor, seleccione un usuario para habilitar los filtros de fecha y búsqueda.")
                cursor.close()
                conn.close()
            else:
                fecha_desde = st.session_state["fecha_desde_auditoria"]
                fecha_hasta = st.session_state["fecha_hasta_auditoria"]

                params = []
                condiciones = []

                if not mostrar_todos:
                    condiciones.append("usuario = %s")
                    params.append(usuario_seleccionado)

                condiciones.append("DATE(fecha_acceso) >= %s")
                params.append(fecha_desde.strftime("%Y-%m-%d"))
                condiciones.append("DATE(fecha_acceso) <= %s")
                params.append(fecha_hasta.strftime("%Y-%m-%d"))

                query = "SELECT usuario, cargo, rol, fecha_acceso FROM log_accesos"
                if condiciones:
                    query += " WHERE " + " AND ".join(condiciones)
                query += " ORDER BY fecha_acceso DESC LIMIT 100"

                cursor.execute(query, params)
                logs = cursor.fetchall()

                cursor.execute("SELECT COUNT(*) as total FROM log_accesos" + (" WHERE " + " AND ".join(condiciones) if condiciones else ""), params)
                total_registros = cursor.fetchone()["total"]

                cursor.close()
                conn.close()

                titulo_usuario = "Todos los Usuarios" if mostrar_todos else usuario_seleccionado
                st.markdown(
                    f"""
                    <div style="background-color: #f1f5f9; padding: 12px 18px; border-radius: 6px; margin-bottom: 18px; border: 1px solid #e2e8f0;">
                        <span style="color: #475569; font-size: 13px; font-weight: 600;">📊 REGISTROS ENCONTRADOS:</span>
                        <span style="color: #003366; font-size: 18px; font-weight: 700; margin-left: 8px;">{total_registros}</span>
                        <span style="color: #64748b; font-size: 12px; margin-left: 15px;">👤 {titulo_usuario}</span>
                        <span style="color: #64748b; font-size: 12px; margin-left: 15px;">📅 {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if not logs:
                    st.info("📭 No se encontraron registros de accesos para este criterio.")
                else:
                    html_lineas = [estilo_tabla_unificado, """
                    <table class="tabla-banco">
                        <thead>
                            <tr>
                                <th style="width: 30%;">USUARIO</th>
                                <th style="width: 30%;">CARGO</th>
                                <th style="width: 15%;">ROL</th>
                                <th style="width: 25%;">FECHA / HORA</th>
                            </tr>
                        </thead>
                        <tbody>
                    """]

                    for log in logs:
                        u_name = log.get("usuario", "-")
                        c_name = log.get("cargo", "-") or "-"
                        r_name = log.get("rol", "-") or "-"
                        f_time = log["fecha_acceso"].strftime("%d/%m/%Y %H:%M:%S") if log.get("fecha_acceso") else "-"

                        html_lineas.append(f"""
                            <tr>
                                <td><span class="usuario-nombre">{u_name}</span></td>
                                <td>{c_name}</td>
                                <td style="text-align: center;">{r_name.upper()}</td>
                                <td style="text-align: center; font-size: 12px;">{f_time}</td>
                            </tr>
                        """)

                    html_lineas.append("</tbody></table>")
                    st.components.v1.html("".join(html_lineas), height=max(180, len(logs) * 42 + 65), scrolling=True)

        except Exception as e:
            st.error(f"❌ Error al cargar accesos: {e}")

    # ==========================================================================
    # PESTAÑA 2: ACTIVIDAD Y SESIONES (AUDITORIA_SESIONES)
    # ==========================================================================
    with tab_sesiones:
        st.markdown("<p style='color: #475569; font-size: 14px;'>Monitoreo en tiempo real del ciclo de vida de las sesiones (Tokens, Navegación y Eventos de Seguridad).</p>", unsafe_allow_html=True)

        if "_limpiar_sesiones" in st.query_params and st.query_params["_limpiar_sesiones"] == "1":
            st.session_state["filtro_usuario_sesiones"] = "-- Seleccione un Usuario --"
            st.session_state["fecha_desde_sesiones"] = (datetime.now() - timedelta(days=7)).date()
            st.session_state["fecha_hasta_sesiones"] = datetime.now().date()
            st.session_state["mostrar_resultados_ses"] = False
            del st.query_params["_limpiar_sesiones"]
            st.rerun()

        if "filtro_usuario_sesiones" not in st.session_state:
            st.session_state["filtro_usuario_sesiones"] = "-- Seleccione un Usuario --"
        if "fecha_desde_sesiones" not in st.session_state:
            st.session_state["fecha_desde_sesiones"] = (datetime.now() - timedelta(days=7)).date()
        if "fecha_hasta_sesiones" not in st.session_state:
            st.session_state["fecha_hasta_sesiones"] = datetime.now().date()
        if "mostrar_resultados_ses" not in st.session_state:
            st.session_state["mostrar_resultados_ses"] = False

        try:
            conn = conectar_bd()
            if not conn:
                st.error("❌ No se pudo establecer conexión con la base de datos.")
                return

            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT DISTINCT u.usuario FROM auditoria_sesiones a INNER JOIN usuarios u ON a.usuario_id = u.id ORDER BY u.usuario ASC")
            usuarios_sesiones_db = cursor.fetchall()
            lista_usuarios_sesiones = ["-- Seleccione un Usuario --", "-- Todos los Usuarios --"] + [u["usuario"] for u in usuarios_sesiones_db]

            col_s1, col_s2, col_s3 = st.columns([3, 1, 1])

            with col_s1:
                st.selectbox(
                    "👤 Filtrar por Usuario (Sesiones)",
                    options=lista_usuarios_sesiones,
                    key="filtro_usuario_sesiones",
                    label_visibility="collapsed"
                )

            with col_s2:
                if st.button("🔍 Filtrar", use_container_width=True, key="btn_filtrar_sesiones"):
                    st.session_state["mostrar_resultados_ses"] = True
                    st.rerun()

            with col_s3:
                if st.button("🧹 Limpiar", use_container_width=True, key="btn_limpiar_sesiones"):
                    st.query_params["_limpiar_sesiones"] = "1"
                    st.rerun()

            st.markdown("---")

            usr_seleccionado_ses = st.session_state["filtro_usuario_sesiones"]
            hay_usr_ses = usr_seleccionado_ses != "-- Seleccione un Usuario --"
            mostrar_todos_ses = usr_seleccionado_ses == "-- Todos los Usuarios --"

            if hay_usr_ses or mostrar_todos_ses:
                col_s4, col_s5 = st.columns([2, 2])
                with col_s4:
                    st.date_input("📅 Desde", key="fecha_desde_sesiones")
                with col_s5:
                    st.date_input("📅 Hasta", key="fecha_hasta_sesiones")
                st.markdown("---")

            if not st.session_state["mostrar_resultados_ses"]:
                if hay_usr_ses or mostrar_todos_ses:
                    st.info("🔍 Seleccione el rango de fechas y presione **Filtrar** para visualizar la actividad de sesiones.")
                else:
                    st.info("👤 Por favor, seleccione un usuario para habilitar los filtros de fecha y búsqueda.")
                cursor.close()
                conn.close()
            else:
                f_desde_ses = st.session_state["fecha_desde_sesiones"]
                f_hasta_ses = st.session_state["fecha_hasta_sesiones"]

                params_ses = []
                condiciones_ses = []

                if not mostrar_todos_ses:
                    condiciones_ses.append("u.usuario = %s")
                    params_ses.append(usr_seleccionado_ses)

                condiciones_ses.append("DATE(a.fecha_evento) >= %s")
                params_ses.append(f_desde_ses.strftime("%Y-%m-%d"))
                condiciones_ses.append("DATE(a.fecha_evento) <= %s")
                params_ses.append(f_hasta_ses.strftime("%Y-%m-%d"))

                query_sesiones = """
                    SELECT 
                        COALESCE(u.usuario, 'Sistema / Externo') as usuario,
                        a.evento,
                        a.seccion,
                        a.detalle,
                        a.fecha_evento
                    FROM auditoria_sesiones a
                    LEFT JOIN usuarios u ON a.usuario_id = u.id
                """
                if condiciones_ses:
                    query_sesiones += " WHERE " + " AND ".join(condiciones_ses)
                query_sesiones += " ORDER BY a.fecha_evento DESC LIMIT 100"

                cursor.execute(query_sesiones, params_ses)
                eventos_sesion = cursor.fetchall()

                query_count_ses = "SELECT COUNT(*) as total FROM auditoria_sesiones a LEFT JOIN usuarios u ON a.usuario_id = u.id"
                if condiciones_ses:
                    query_count_ses += " WHERE " + " AND ".join(condiciones_ses)
                cursor.execute(query_count_ses, params_ses)
                total_reg_ses = cursor.fetchone()["total"]

                cursor.close()
                conn.close()

                titulo_usr_ses = "Todos los Usuarios" if mostrar_todos_ses else usr_seleccionado_ses
                st.markdown(
                    f"""
                    <div style="background-color: #f1f5f9; padding: 12px 18px; border-radius: 6px; margin-bottom: 18px; border: 1px solid #e2e8f0;">
                        <span style="color: #475569; font-size: 13px; font-weight: 600;">📊 EVENTOS ENCONTRADOS:</span>
                        <span style="color: #003366; font-size: 18px; font-weight: 700; margin-left: 8px;">{total_reg_ses}</span>
                        <span style="color: #64748b; font-size: 12px; margin-left: 15px;">👤 {titulo_usr_ses}</span>
                        <span style="color: #64748b; font-size: 12px; margin-left: 15px;">📅 {f_desde_ses.strftime('%d/%m/%Y')} - {f_hasta_ses.strftime('%d/%m/%Y')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if not eventos_sesion:
                    st.info("📭 No hay registros de auditoría de sesiones para este criterio.")
                else:
                    html_sesiones = [estilo_tabla_unificado, """
                    <table class="tabla-banco">
                        <thead>
                            <tr>
                                <th style="width: 20%;">USUARIO</th>
                                <th style="width: 20%;">EVENTO</th>
                                <th style="width: 20%;">MÓDULO / SECCIÓN</th>
                                <th style="width: 20%;">FECHA / HORA</th>
                                <th style="width: 20%;">DETALLE</th>
                            </tr>
                        </thead>
                        <tbody>
                    """]

                    for ev in eventos_sesion:
                        usr = ev.get("usuario", "-")
                        evt = ev.get("evento", "-")
                        sec = ev.get("seccion", "-") or "-"
                        f_evt = ev["fecha_evento"].strftime("%d/%m/%Y %H:%M:%S") if ev.get("fecha_evento") else "-"
                        det = ev.get("detalle", "-") or "-"

                        html_sesiones.append(f"""
                            <tr>
                                <td><span class="usuario-nombre">{usr}</span></td>
                                <td style="text-align: center;"><span class="badge-evento">{evt}</span></td>
                                <td>{sec}</td>
                                <td style="text-align: center; font-size: 12px;">{f_evt}</td>
                                <td style="font-size: 12px; color: #334155;">{det}</td>
                            </tr>
                        """)

                    html_sesiones.append("</tbody></table>")
                    st.components.v1.html("".join(html_sesiones), height=max(180, len(eventos_sesion) * 42 + 65), scrolling=True)

        except Exception as e:
            st.error(f"❌ Error al consultar la auditoría de sesiones: {e}")

if __name__ == "__main__":
    mostrar_pantalla()