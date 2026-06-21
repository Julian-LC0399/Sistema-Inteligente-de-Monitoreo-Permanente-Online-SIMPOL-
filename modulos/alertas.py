import streamlit as st
import traceback
import logging
import time
from datetime import datetime
from database import conectar_bd, obtener_lista_servidores

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# PERSISTENCIA Y CONSULTA DE TELEMETRÍA Y UMBRALES
# =====================================================================

def obtener_ultimo_monitoreo(ip):
    conn = conectar_bd()
    registro = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM monitoreo 
                WHERE ip_servidor = %s 
                ORDER BY fecha_registro DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            registro = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo último monitoreo para {ip}: {e}")
    return registro

def obtener_umbrales_actuales(ip):
    umbrales = {
        "cpu_buen_estado": 69.0, "cpu_advertencia": 70.0, "cpu_critico": 85.0,
        "ram_buen_estado": 20.0, "ram_advertencia": 15.0, "ram_critico": 10.0,
        "red_limite_mbps": 90.0, "ping_limite_ms": 80.0,
        "disco_buen_estado": 30.0, "disco_advertencia": 20.0, "disco_critico": 15.0
    }
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM umbrales WHERE ip_servidor = %s LIMIT 1", (ip,))
            row = cursor.fetchone()
            if row:
                umbrales = {
                    "cpu_buen_estado": float(row.get("cpu_buen_estado") or 69.0),
                    "cpu_advertencia": float(row.get("cpu_advertencia") or 70.0),
                    "cpu_critico": float(row.get("cpu_critico") or 85.0),
                    "ram_buen_estado": float(row.get("ram_buen_estado") or 20.0),
                    "ram_advertencia": float(row.get("ram_advertencia") or 15.0),
                    "ram_critico": float(row.get("ram_critico") or 10.0),
                    "red_limite_mbps": float(row.get("red_limite_mbps") or 90.0),
                    "ping_limite_ms": float(row.get("ping_limite_ms") or 80.0),
                    "disco_buen_estado": float(row.get("disco_buen_estado") or 30.0),
                    "disco_advertencia": float(row.get("disco_advertencia") or 20.0),
                    "disco_critico": float(row.get("disco_critico") or 15.0)
                }
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error obteniendo umbrales para {ip}: {e}")
    return umbrales

def guardar_nuevos_umbrales(ip, u, usuario_id, justificacion):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_umb FROM umbrales WHERE ip_servidor = %s LIMIT 1", (ip,))
        row = cursor.fetchone()
        
        if row:
            query = """
                UPDATE umbrales SET 
                    cpu_buen_estado=%s, cpu_advertencia=%s, cpu_critico=%s,
                    ram_buen_estado=%s, ram_advertencia=%s, ram_critico=%s,
                    red_limite_mbps=%s, ping_limite_ms=%s,
                    disco_buen_estado=%s, disco_advertencia=%s, disco_critico=%s,
                    fecha_modificacion=NOW()
                WHERE ip_servidor=%s
            """
            cursor.execute(query, (
                u["cpu_buen_estado"], u["cpu_advertencia"], u["cpu_critico"],
                u["ram_buen_estado"], u["ram_advertencia"], u["ram_critico"],
                u["red_limite_mbps"], u["ping_limite_ms"],
                u["disco_buen_estado"], u["disco_advertencia"], u["disco_critico"],
                ip
            ))
        else:
            query = """
                INSERT INTO umbrales (
                    ip_servidor, cpu_buen_estado, cpu_advertencia, cpu_critico,
                    ram_buen_estado, ram_advertencia, ram_critico,
                    red_limite_mbps, ping_limite_ms,
                    disco_buen_estado, disco_advertencia, disco_critico, fecha_modificacion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (
                ip, u["cpu_buen_estado"], u["cpu_advertencia"], u["cpu_critico"],
                u["ram_buen_estado"], u["ram_advertencia"], u["ram_critico"],
                u["red_limite_mbps"], u["ping_limite_ms"],
                u["disco_buen_estado"], u["disco_advertencia"], u["disco_critico"]
            ))
            
        query_hist = """
            INSERT INTO umbrales_historial (
                ip_servidor, id_usuario, fecha_cambio, justificacion,
                cpu_critico_ant, cpu_critico_nue, ram_critico_ant, ram_critico_nue
            ) VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
        """
        cursor.execute(query_hist, (ip, usuario_id, justificacion, 0.0, u["cpu_critico"], 0.0, u["ram_critico"]))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error guardando umbrales: {e}\n{traceback.format_exc()}")
        if conn: conn.rollback()
        return False

# =====================================================================
# FRAGMENTO DE MONITOREO EN VIVO ADAPTATIVO
# =====================================================================
@st.fragment()
def renderizar_paneles_vivo_alertas(ip_conf_sel):
    ultimo_registro = obtener_ultimo_monitoreo(ip_conf_sel)
    
    if not ultimo_registro:
        st.warning("⚠️ No se registran datos de telemetría para esta IP en la tabla `monitoreo`.")
        return

    # Determinar si el agente está enviando datos activamente
    fecha_reg = ultimo_registro["fecha_registro"]
    diferencia_tiempo = datetime.now() - fecha_reg
    agente_activo = diferencia_tiempo.total_seconds() <= 45

    # Cabecera con indicador de estado dinámico
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.markdown(f"##### 📊 Estado Actual del Nodo (Paquete: {fecha_reg.strftime('%H:%M:%S')})")
    with col_t2:
        if agente_activo:
            st.markdown('<p style="font-size: 11px; color: #47a323; margin-top: 5px; text-align: right;">🟢 <b>Live Feed Activo</b> — Refrescando cada 15s</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size: 11px; color: #888888; margin-top: 5px; text-align: right;">⚠️ <b>Agente Desconectado</b> — Datos fijos</p>', unsafe_allow_html=True)

    # Renderizado de Tarjetas de Métricas
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.metric(label="⚙️ USO CPU GLOBAL", value=f"{ultimo_registro.get('val_cpu', 0.0):.1f} %")
    with col_m2:
        st.metric(label="🧠 RAM DISPONIBLE", value=f"{ultimo_registro.get('val_ram_disponible_pct', 0.0):.1f} %")
    with col_m3:
        st.metric(label="💽 DISCO C LIBRE", value=f"{ultimo_registro.get('val_disco_1_pct_libre', 0.0):.1f} %")
    with col_m4:
        st.metric(label="🌐 TRÁFICO RED", value=f"{ultimo_registro.get('val_red_total', 0.0):.1f} Mbps")
    with col_m5:
        st.metric(label="⏳ LATENCIA PING", value=f"{ultimo_registro.get('val_latencia_ping', 0.0):.1f} ms")

    # Si el agente está activo, gatillar bucle de refresco cada 15 segundos
    if agente_activo:
        time.sleep(15)
        st.rerun(scope="fragment")

# =====================================================================
# VISTA PRINCIPAL DEL MÓDULO
# =====================================================================

def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "GESTION_ALERTAS" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su rol no cuenta con el privilegio [GESTION_ALERTAS].")
            return

    st.markdown(
        f'<div style="background-color:#f8f9fa; padding:10px 15px; border-left:4px solid #cc0000; border-radius:4px; margin-bottom:15px;">'
        f'<h3 style="color:#cc0000; margin:0px; font-size:20px;">🚨 Gestión de Alertas y Políticas de Umbrales</h3>'
        f'<p style="color:#555; font-size:12.5px; margin:2px 0px 0px 0px;">'
        f'Administración Operativa de Límites de Control | <b>Firmado por:</b> {nombre_analista} ({usuario_login})</p>'
        f'</div>', 
        unsafe_allow_html=True
    )

    servidores = obtener_lista_servidores()
    if not servidores:
        st.info("💡 No existen servidores registrados en el sistema para configurar umbrales.")
        return

    # Selector de servidores
    dict_srv_mapeo = {s["nombre_alias"]: s["ip"] for s in servidores if s.get("nombre_alias")}
    lista_nombres_srv = list(dict_srv_mapeo.keys())

    col_selector, col_vacia = st.columns([2, 2])
    with col_selector:
        srv_seleccionado = st.selectbox("🖥️ Seleccione el Servidor Bajo Análisis:", options=lista_nombres_srv)

    ip_conf_sel = dict_srv_mapeo[srv_seleccionado]

    # Invocación del Fragmento Inteligente de Telemetría
    renderizar_paneles_vivo_alertas(ip_conf_sel)

    st.markdown("---")
    st.markdown("##### 🛠️ Modificación de Umbrales Operativos")

    umbrales_vivos = obtener_umbrales_actuales(ip_conf_sel)
    dict_nuevos_valores = {}

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown('<p style="color:#003366; font-weight:bold; margin-bottom:2px;">⚙️ Procesador (CPU)</p>', unsafe_allow_html=True)
        dict_nuevos_valores["cpu_buen_estado"] = st.number_input("Buen Estado (<= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["cpu_buen_estado"], step=1.0, key="u_cpu_ok")
        dict_nuevos_valores["cpu_advertencia"] = st.number_input("Advertencia (> %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["cpu_advertencia"], step=1.0, key="u_cpu_warn")
        dict_nuevos_valores["cpu_critico"] = st.number_input("Crítico (>= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["cpu_critico"], step=1.0, key="u_cpu_crit")

    with col_c2:
        st.markdown('<p style="color:#712cb0; font-weight:bold; margin-bottom:2px;">🧠 Memoria Volátil (RAM)</p>', unsafe_allow_html=True)
        dict_nuevos_valores["ram_buen_estado"] = st.number_input("Buen Estado Libre (>= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["ram_buen_estado"], step=1.0, key="u_ram_ok")
        dict_nuevos_valores["ram_advertencia"] = st.number_input("Advertencia Libre (< %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["ram_advertencia"], step=1.0, key="u_ram_warn")
        dict_nuevos_valores["ram_critico"] = st.number_input("Crítico Libre (<= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["ram_critico"], step=1.0, key="u_ram_crit")

    with col_c3:
        st.markdown('<p style="color:#e65c00; font-weight:bold; margin-bottom:2px;">💽 Sistema de Archivos (Disco C)</p>', unsafe_allow_html=True)
        dict_nuevos_valores["disco_buen_estado"] = st.number_input("Disco OK Libre (>= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["disco_buen_estado"], step=1.0, key="u_dis_ok")
        dict_nuevos_valores["disco_advertencia"] = st.number_input("Disco Warn Libre (< %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["disco_advertencia"], step=1.0, key="u_dis_warn")
        dict_nuevos_valores["disco_critico"] = st.number_input("Disco Crítico Libre (<= %)", min_value=0.0, max_value=100.0, value=umbrales_vivos["disco_critico"], step=1.0, key="u_dis_crit")

    st.markdown('<p style="color:#008080; font-weight:bold; margin-top:10px; margin-bottom:2px;">🌐 Límites de Conectividad General</p>', unsafe_allow_html=True)
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        dict_nuevos_valores["red_limite_mbps"] = st.number_input("Capacidad de Tráfico de Red Máxima (Mbps)", min_value=1.0, max_value=10000.0, value=umbrales_vivos["red_limite_mbps"], step=10.0, key="u_red_max")
    with col_n2:
        dict_nuevos_valores["ping_limite_ms"] = st.number_input("Latencia de Respuesta Tolerable ICMP (ms)", min_value=1.0, max_value=2000.0, value=umbrales_vivos["ping_limite_ms"], step=5.0, key="u_png_max")

    st.markdown("---")
    st.markdown("##### 📝 Firma de Auditoría de Sistemas")
    
    with st.expander("🔐 Formulario de Declaración de Cambios", expanded=True):
        txt_justificacion = st.text_area("Justificación Operativa / Ticket de Soporte:", placeholder="Ej: Ampliación de umbrales por holgura de procesamiento requerida para sobrecarga transaccional...", key="p2_justificacion")
        
        col_submit = st.columns([1, 2, 1])
        with col_submit[1]:
            btn_salvar = st.button("💾 ACTUALIZAR POLÍTICAS DE UMBRALES", key="p2_btn_salvar", use_container_width=True)
        
        if btn_salvar:
            if not txt_justificacion.strip():
                st.warning("⚠️ Operación rechazada: Debe ingresar una justificación válida para la auditoría de sistemas.")
            else:
                for k, v in umbrales_vivos.items():
                    if k not in dict_nuevos_valores: 
                        dict_nuevos_valores[k] = v
                        
                if guardar_nuevos_umbrales(ip_conf_sel, dict_nuevos_valores, usuario_id, txt_justificacion):
                    st.success("🎉 Umbrales actualizados con éxito. Historial relacional firmado.")
                    st.rerun()

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)