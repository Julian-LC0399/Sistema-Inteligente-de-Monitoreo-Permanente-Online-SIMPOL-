import streamlit as st
from database import obtener_lista_servidores, conectar_bd
from datetime import datetime

def obtener_alertas_por_ip(ip):
    conn = conectar_bd()
    alertas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT fecha_registro, val_cpu, val_ram, val_disco, val_red, val_latencia, estado_sistema 
                FROM monitoreo 
                WHERE ip_servidor = %s AND estado_sistema != 'ÓPTIMO'
                ORDER BY fecha_registro DESC LIMIT 30
            """
            cursor.execute(query, (ip,))
            alertas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error al cargar el historial de alertas: {e}")
    return alertas

def obtener_umbrales_actuales(ip):
    # Valores por defecto del banco si no existen en la BD
    umbrales = {"cpu_critico": 80, "ram_critico": 85, "disco_critico": 90}
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Buscamos el último registro de configuración para esa IP
            query = """
                SELECT cpu_critico, ram_critico, disco_critico 
                FROM historico_umbrales 
                WHERE ip_servidor = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            res = cursor.fetchone()
            if res:
                umbrales = res
            cursor.close()
            conn.close()
        except Exception:
            pass # Si la tabla no existe o está vacía, asume los defaults de contingencia
    return umbrales

def guardar_nuevo_umbral(usuario_id, ip, cpu, ram, disco, motivo):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_umbrales 
                (ip_servidor, usuario_id, cpu_critico, ram_critico, disco_critico, justificacion, fecha_cambio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (ip, usuario_id, cpu, ram, disco, motivo, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error de persistencia en auditoría: {e}")
    return False

def mostrar_pantalla(usuario_id=1, rol_usuario="OPERADOR"):
    # === ANCLA DE LIMPIEZA TOTAL ATÓMICA ===
    canvas_alertas = st.empty()
    
    # Normalización del rol de seguridad
    rol_sanitizado = str(rol_usuario).strip().upper() if rol_usuario else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado
    
    with canvas_alertas.container():
        # Encabezado institucional blindado
        st.markdown('<h2 style="color:#003366;">🔔 Centro de Control de Alertas y Umbrales</h2>', unsafe_allow_html=True)
        st.markdown("---")
        
        # 1. CATALOGO DE INFRAESTRUCTURA
        servidores = obtener_lista_servidores()
        if not servidores:
            st.warning("⚠️ No hay servidores registrados en la granja de SIMPOL.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        seleccion = st.selectbox("Seleccione Servidor para Inspección y Parámetros:", list(opciones.keys()), key="alertas_main_filter")
        serv_info = opciones[seleccion]
        ip_actual = serv_info['ip']
        alias_actual = serv_info['nombre_alias']

        # BANNER DE IDENTIFICACIÓN: Filtro activo explícito
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 6px; border-left: 5px solid #003366; margin-bottom: 25px;">
                <span style="color: #003366; font-weight: bold;">🖥️ Nodo en Análisis Actual:</span> 
                <span style="color: #333;">{alias_actual} — IP Pública / Interna: <b>{ip_actual}</b></span>
            </div>
        """, unsafe_allow_html=True)

        # 2. CONSOLA DE GESTIÓN DE UMBRALES (PANEL DE CONTROL)
        st.markdown('<h4 style="color:#003366;">🎛️ Configuración de Límites y Tolerancia</h4>', unsafe_allow_html=True)
        
        umbrales_base = obtener_umbrales_actuales(ip_actual)
        
        # Formulario controlado para evitar que refresque la pantalla antes de la justificación
        with st.form("form_gestion_umbrales"):
            st.markdown("<small>Defina los puntos de quiebre donde los sensores dispararán los estados críticos en SIMPOL.</small>", unsafe_allow_html=True)
            col_u1, col_u2, col_u3 = st.columns(3)
            
            nuevo_cpu = col_u1.slider("Límite Crítico CPU (%)", 50, 100, int(umbrales_base['cpu_critico']), key="sl_cpu_u")
            nuevo_ram = col_u2.slider("Límite Crítico RAM (%)", 50, 100, int(umbrales_base['ram_critico']), key="sl_ram_u")
            nuevo_disco = col_u3.slider("Límite Crítico DISCO (%)", 50, 100, int(umbrales_base['disco_critico']), key="sl_disco_u")
            
            # Campo obligatorio de Auditoría
            justificacion = st.text_area("✍️ Justificación del Cambio (Exigido por Seguridad / Auditoría Interna):", 
                                         placeholder="Ej. Incremento transatorio por cierre fiscal de mes / Ampliación física de hardware...")
            
            btn_aplicar = st.form_submit_button("💾 Modificar y Registrar Umbrales", use_container_width=True)
            
            if btn_aplicar:
                if not es_seguridad:
                    st.error("❌ Privilegios Insuficientes: Su rol no cuenta con permisos de escritura sobre las políticas de hardware.")
                elif not justificacion.strip():
                    st.error("🛑 Operación Rechazada: Debe ingresar la justificación técnica para el log de cambios.")
                elif len(justificacion.strip()) < 10:
                    st.error("⚠️ Justificación muy corta. Explique detalladamente el motivo para el registro de auditoría.")
                else:
                    exito = guardar_nuevo_umbral(usuario_id, ip_actual, nuevo_cpu, nuevo_ram, nuevo_disco, justificacion.strip())
                    if exito:
                        st.success(f"✅ Umbrales actualizados para {alias_actual}. Registro guardado en el histórico.")
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        # 3. HISTORIAL DE INCIDENTES DETECTADOS
        st.markdown(f'<h4 style="color:#003366;">📋 Bitácora de Eventos Recientes: {alias_actual}</h4>', unsafe_allow_html=True)
        
        alertas = obtener_alertas_por_ip(ip_actual)
        criticas = [a for a in alertas if a['estado_sistema'] == 'CRÍTICO']
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Eventos de Saturación (Críticos)", len(criticas))
        col_m2.metric("Total Alertas en Historial", len(alertas))
        
        if st.button("🔄 Refrescar Bitácora", key="btn_manual_refresh_alertas", use_container_width=True):
            st.rerun()

        if not alertas:
            st.success(f"🟢 **ÓPTIMO:** El servidor {alias_actual} no registra transgresiones a las métricas vigentes.")
        else:
            # Renderizado limpio sin arrastrar basura visual de otros módulos
            for i, alerta in enumerate(alertas):
                fecha = alerta['fecha_registro'].strftime('%H:%M:%S | %d-%m-%Y')
                estado = alerta['estado_sistema']
                detalle = f"**CPU:** {alerta['val_cpu']}%  |  **RAM:** {alerta['val_ram']}%  |  **DISCO:** {alerta['val_disco']}%  |  **LAT:** {alerta['val_latencia']}ms"
                
                if estado == "CRÍTICO":
                    st.error(f"🔴 **CRÍTICO** | {fecha}\n\n{detalle}", icon="🔥")
                else:
                    st.warning(f"⚠️ **PRECAUCIÓN** | {fecha}\n\n{detalle}", icon="📢")

if __name__ == "__main__":
    # Prueba local por defecto
    mostrar_pantalla(usuario_id=1, rol_usuario="ADMIN")