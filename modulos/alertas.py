import streamlit as st
from database import obtener_lista_servidores, conectar_bd
from datetime import datetime

def obtener_umbrales_actuales(ip):
    # Valores por defecto de contingencia si no se encuentra un registro previo
    umbrales = {"cpu_critico": 80, "ram_critico": 85, "disco_critico": 90}
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Buscamos el último registro de configuración de umbrales para esa IP específica
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
            pass # Retorna los valores por defecto si ocurre algún error
    return umbrales

def guardar_nuevo_umbral(usuario_id, ip, cpu, ram, disco, motivo):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            # Inserción formal de auditoría en la nueva tabla historico_umbrales
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
    
    # Sanitización estricta del rol del usuario para la validación de permisos
    rol_sanitizado = str(rol_usuario).strip().upper() if rol_usuario else ""
    es_seguridad = "SEGURIDAD" in rol_sanitizado or "ADMIN" in rol_sanitizado
    
    with canvas_alertas.container():
        # Encabezado institucional homologado en azul corporativo
        st.markdown('<h2 style="color:#003366;">🔔 Centro de Control de Alertas y Umbrales</h2>', unsafe_allow_html=True)
        st.markdown("---")
        
        # 1. CATÁLOGO DE INFRAESTRUCTURA (FILTRO DE SERVIDOR ACTIVO)
        servidores = obtener_lista_servidores()
        if not servidores:
            st.warning("⚠️ No hay servidores registrados en la granja de SIMPOL.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        seleccion = st.selectbox("Seleccione Servidor para Inspección y Parámetros:", list(opciones.keys()), key="alertas_main_filter")
        serv_info = opciones[seleccion]
        ip_actual = serv_info['ip']
        alias_actual = serv_info['nombre_alias']

        # BANNER DE IDENTIFICACIÓN: Visualización clara del nodo seleccionado
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 6px; border-left: 5px solid #003366; margin-bottom: 25px;">
                <span style="color: #003366; font-weight: bold;">🖥️ Nodo en Análisis Actual:</span> 
                <span style="color: #333;">{alias_actual} — IP Pública / Interna: <b>{ip_actual}</b></span>
            </div>
        """, unsafe_allow_html=True)

        # 2. CONSOLA DE GESTIÓN DE UMBRALES (CONTROLES NUMÉRICOS GRANDES)
        st.markdown('<h4 style="color:#003366;">🎛️ Configuración de Límites y Tolerancia</h4>', unsafe_allow_html=True)
        
        umbrales_base = obtener_umbrales_actuales(ip_actual)
        
        # Formulario encapsulado para evitar recargas fantasma durante la edición
        with st.form("form_gestion_umbrales"):
            st.markdown("<small>Defina los puntos de quiebre numéricos donde los sensores dispararán los estados críticos en SIMPOL.</small>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_u1, col_u2, col_u3 = st.columns(3)
            
            # Cajas numéricas de alta visibilidad para reemplazo de los sliders pequeños
            nuevo_cpu = col_u1.number_input("Límite Crítico CPU (%)", min_value=1, max_value=100, value=int(umbrales_base['cpu_critico']), step=1, key="num_cpu_u")
            nuevo_ram = col_u2.number_input("Límite Crítico RAM (%)", min_value=1, max_value=100, value=int(umbrales_base['ram_critico']), step=1, key="num_ram_u")
            nuevo_disco = col_u3.number_input("Límite Crítico DISCO (%)", min_value=1, max_value=100, value=int(umbrales_base['disco_critico']), step=1, key="num_disco_u")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Campo obligatorio de justificación técnica para logs de auditoría
            justificacion = st.text_area("✍️ Justificación del Cambio (Exigido por Seguridad / Auditoría Interna):", 
                                         placeholder="Ej. Incremento transitorio por cierre fiscal de mes / Ampliación física de hardware...")
            
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

if __name__ == "__main__":
    mostrar_pantalla(usuario_id=1, rol_usuario="ADMIN")