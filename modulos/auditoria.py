import streamlit as st
from database import conectar_bd
from datetime import datetime, timedelta

def mostrar_pantalla():
    # === INICIALIZAR ESTADOS ===
    if "filtro_usuario_auditoria" not in st.session_state:
        st.session_state["filtro_usuario_auditoria"] = "-- Seleccione un Usuario --"
    if "fecha_desde_auditoria" not in st.session_state:
        st.session_state["fecha_desde_auditoria"] = (datetime.now() - timedelta(days=7)).date()
    if "fecha_hasta_auditoria" not in st.session_state:
        st.session_state["fecha_hasta_auditoria"] = datetime.now().date()
    if "mostrar_resultados" not in st.session_state:
        st.session_state["mostrar_resultados"] = False

    st.markdown("<h2 style='color: #003366; font-family: sans-serif;'>🕵️ Control de Accesos y Auditoría</h2>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        conn = conectar_bd()
        if not conn:
            st.error("❌ No se pudo establecer conexión con la base de datos.")
            return

        cursor = conn.cursor(dictionary=True)

        # =============================================================
        # 1. OBTENER LISTA DE USUARIOS ÚNICOS PARA EL FILTRO
        # =============================================================
        cursor.execute("SELECT DISTINCT usuario FROM log_accesos ORDER BY usuario ASC")
        usuarios_db = cursor.fetchall()
        lista_usuarios = ["-- Seleccione un Usuario --"] + [u["usuario"] for u in usuarios_db]

        # =============================================================
        # 2. FILTRO DE USUARIO + BOTÓN LIMPIAR
        # =============================================================
        col_f1, col_f2 = st.columns([3, 1])

        with col_f1:
            usuario_seleccionado = st.selectbox(
                "👤 Filtrar por Usuario",
                options=lista_usuarios,
                key="filtro_usuario_auditoria"
            )

        with col_f2:
            st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
            if st.button("🧹 Limpiar Filtros", use_container_width=True, key="btn_limpiar_auditoria"):
                st.session_state["filtro_usuario_auditoria"] = "-- Seleccione un Usuario --"
                st.session_state["fecha_desde_auditoria"] = (datetime.now() - timedelta(days=7)).date()
                st.session_state["fecha_hasta_auditoria"] = datetime.now().date()
                st.session_state["mostrar_resultados"] = False
                st.rerun()

        st.markdown("---")

        # =============================================================
        # 3. FILTRO DE FECHAS (SOLO APARECE SI HAY USUARIO SELECCIONADO)
        # =============================================================
        usuario_seleccionado = st.session_state["filtro_usuario_auditoria"]
        hay_usuario_seleccionado = usuario_seleccionado != "-- Seleccione un Usuario --"

        if hay_usuario_seleccionado:
            col_f3, col_f4, col_f5 = st.columns([2, 2, 1])

            with col_f3:
                st.date_input(
                    "📅 Desde",
                    key="fecha_desde_auditoria"
                )

            with col_f4:
                st.date_input(
                    "📅 Hasta",
                    key="fecha_hasta_auditoria"
                )

            with col_f5:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                if st.button("🔍 Buscar", use_container_width=True, key="btn_buscar_auditoria"):
                    st.session_state["mostrar_resultados"] = True
                    st.rerun()

            st.markdown("---")

        # =============================================================
        # 4. MOSTRAR RESULTADOS SOLO SI SE HA BUSCADO
        # =============================================================
        if not st.session_state["mostrar_resultados"]:
            if hay_usuario_seleccionado:
                st.info("🔍 Seleccione el rango de fechas y presione **Buscar** para visualizar el historial.")
            else:
                st.info("👤 Por favor, seleccione un usuario para habilitar los filtros de fecha y búsqueda.")
            cursor.close()
            conn.close()
            return

        # =============================================================
        # 5. CONSTRUIR CONSULTA CON FILTROS
        # =============================================================
        fecha_desde = st.session_state["fecha_desde_auditoria"]
        fecha_hasta = st.session_state["fecha_hasta_auditoria"]

        query = """
            SELECT 
                usuario, 
                cargo, 
                rol, 
                fecha_acceso, 
                resultado, 
                ip_cliente
            FROM log_accesos 
            WHERE usuario = %s
        """
        params = [usuario_seleccionado]

        # Filtro por rango de fechas
        query += " AND DATE(fecha_acceso) >= %s AND DATE(fecha_acceso) <= %s"
        params.append(fecha_desde.strftime("%Y-%m-%d"))
        params.append(fecha_hasta.strftime("%Y-%m-%d"))

        query += " ORDER BY fecha_acceso DESC LIMIT 100"

        cursor.execute(query, params)
        logs = cursor.fetchall()

        # =============================================================
        # 6. CONTAR TOTAL DE REGISTROS CON FILTROS APLICADOS
        # =============================================================
        query_count = """
            SELECT COUNT(*) as total 
            FROM log_accesos 
            WHERE usuario = %s
            AND DATE(fecha_acceso) >= %s AND DATE(fecha_acceso) <= %s
        """
        params_count = [
            usuario_seleccionado,
            fecha_desde.strftime("%Y-%m-%d"),
            fecha_hasta.strftime("%Y-%m-%d")
        ]

        cursor.execute(query_count, params_count)
        total_registros = cursor.fetchone()["total"]

        cursor.close()
        conn.close()

        # =============================================================
        # 7. BANNER ESTADÍSTICO
        # =============================================================
        st.markdown(
            f"""
            <div style="background-color: #f1f5f9; padding: 12px 18px; border-radius: 6px; margin-bottom: 18px; border: 1px solid #e2e8f0;">
                <span style="color: #475569; font-size: 13px; font-weight: 600;">📊 REGISTROS ENCONTRADOS:</span>
                <span style="color: #003366; font-size: 18px; font-weight: 700; margin-left: 8px;">{total_registros}</span>
                <span style="color: #64748b; font-size: 12px; margin-left: 15px;">👤 {usuario_seleccionado}</span>
                <span style="color: #64748b; font-size: 12px; margin-left: 15px;">📅 {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =============================================================
        # 8. TABLA CON ESTILO DE GESTIÓN
        # =============================================================
        if not logs:
            st.info("📭 No se encontraron registros de auditoría para este usuario en el rango de fechas seleccionado.")
            return

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
                text-transform: uppercase; 
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
            .badge-ok {
                background-color: #d4edda;
                color: #155724;
                padding: 2px 10px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
                display: inline-block;
            }
            .badge-fail {
                background-color: #f8d7da;
                color: #721c24;
                padding: 2px 10px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
                display: inline-block;
            }
            .badge-warn {
                background-color: #fff3cd;
                color: #856404;
                padding: 2px 10px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
                display: inline-block;
            }
            .usuario-nombre {
                font-weight: 600;
                color: #003366;
            }
            .ip-cliente {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: #475569;
            }
        </style>
        """)
        
        html_lineas.append("""
        <table class="tabla-banco">
            <thead>
                <tr>
                    <th style="width: 15%;">USUARIO</th>
                    <th style="width: 18%;">CARGO</th>
                    <th style="width: 12%;">ROL</th>
                    <th style="width: 20%;">FECHA / HORA</th>
                    <th style="width: 15%;">RESULTADO</th>
                    <th style="width: 15%;">IP CLIENTE</th>
                </tr>
            </thead>
            <tbody>
        """)

        for log in logs:
            usuario = log.get("usuario", "-")
            cargo = log.get("cargo", "-") or "-"
            rol = log.get("rol", "-") or "-"
            fecha = log["fecha_acceso"].strftime("%d/%m/%Y %H:%M:%S") if log.get("fecha_acceso") else "-"
            resultado = log.get("resultado", "-")
            ip = log.get("ip_cliente", "-") or "-"

            # Badge según resultado
            if resultado == "EXITOSO":
                badge = f'<span class="badge-ok">✅ {resultado}</span>'
            elif resultado == "FALLIDO":
                badge = f'<span class="badge-fail">❌ {resultado}</span>'
            elif resultado == "SUSPENDIDO":
                badge = f'<span class="badge-warn">⚠️ {resultado}</span>'
            else:
                badge = f'<span>{resultado}</span>'

            html_lineas.append(f"""
                <tr>
                    <td><span class="usuario-nombre">{usuario}</span></td>
                    <td>{cargo}</td>
                    <td style="text-align: center;">{rol.upper()}</td>
                    <td style="text-align: center; font-size: 12px;">{fecha}</td>
                    <td style="text-align: center;">{badge}</td>
                    <td><span class="ip-cliente">{ip}</span></td>
                </tr>
            """)

        html_lineas.append("""
            </tbody>
        </table>
        """)

        st.components.v1.html("".join(html_lineas), height=max(180, len(logs) * 42 + 65), scrolling=True)
        st.caption(f"📌 Mostrando {len(logs)} registro(s) de {total_registros} total(es)")

    except Exception as e:
        st.error(f"❌ Error al cargar el módulo de auditoría: {e}")

if __name__ == "__main__":
    mostrar_pantalla()