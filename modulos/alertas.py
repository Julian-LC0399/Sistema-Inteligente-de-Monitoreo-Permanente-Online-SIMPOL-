import streamlit as st
import traceback
from datetime import datetime, timedelta
from database import obtener_lista_servidores, conectar_bd
from utils import obtener_telemetria_total

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
        except Exception:
            pass
    return registro

def obtener_umbrales_actuales(ip):
    umbrales = {
        "ram_advertencia": 3.5, "ram_critico": 1.5
    }
    for i in range(1, 7):
        umbrales[f"disco_{i}_advertencia"] = 35.0 if ip == "10.10.1.133" else 40.0
        umbrales[f"disco_{i}_critico"] = 15.0

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM historico_umbrales 
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
            pass 
    return umbrales

def renderizar_semaforo(valor, adv, crit, tipo="uso", pct_libre=None):
    if tipo == "inverso":
        if valor <= crit:
            color = "#e53e3e"  # Rojo
            texto = "CRÍTICO"
        elif valor <= adv:
            color = "#f6e05e"  # Amarillo
            texto = "ADVERTENCIA"
        else:
            color = "#48bb78"  # Verde
            texto = "NORMAL"
        
        if pct_libre is not None:
            unidad = f"GB ({pct_libre}% libre)"
        else:
            unidad = "GB"
    else:
        if valor >= crit:
            color = "#e53e3e"
            texto = "CRÍTICO"
        elif valor >= adv:
            color = "#f6e05e"
            texto = "ADVERTENCIA"
        else:
            color = "#48bb78"
            texto = "NORMAL"
        unidad = "%"
        
    color_t = '#000' if color == '#f6e05e' else '#fff'
    return f"""
    <div style="background-color: {color}; padding: 8px; border-radius: 6px; text-align: center; color: {color_t}; font-weight: bold; font-size: 14px;">
        {texto} ({valor} {unidad})
    </div>
    """

# =====================================================================
# VISTA PRINCIPAL DEL MÓDULO (ESTRUCTURADA EN PESTAÑAS)
# =====================================================================
def mostrar_pantalla(nombre_analista, usuario_id, usuario_login):
    # Inicialización del estado intermedio para el widget de Alertas
    if "servidor_seleccionado_alertas" not in st.session_state:
        st.session_state["servidor_seleccionado_alertas"] = "-- Seleccione un Servidor --"

    # Inicialización de la semilla para forzar limpieza visual del selectbox
    if "key_semilla_alertas" not in st.session_state:
        st.session_state["key_semilla_alertas"] = 0

    st.markdown('<h2 style="color:#003366;">🔔 Panel de Control de Semáforos y Alertas</h2>', unsafe_allow_html=True)
    st.markdown(f"👤 **Cargo Responsable:** {nombre_analista} (`usuario: {usuario_login}`)", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("⚠️ No hay servidores activos registrados en la plataforma.")
        return

    tab_alertas_vivo, tab_config_umbrales = st.tabs(["🚨 Monitoreo de Alertas (Sensores)", "⚙️ Configuración Avanzada de Umbrales"])

    # =====================================================================
    # PESTAÑA 1: INSPECCIÓN VIVA DE SENSORES Y SEMÁFOROS
    # =====================================================================
    with tab_alertas_vivo:
        st.markdown("### ")
        
        # Construcción ordenada agregando la opción basal vacía
        lista_opciones = ["-- Seleccione un Servidor --"] + [f"{s['nombre_alias']} ({s['ip']})" for s in servidores]
        
        try:
            default_index = lista_opciones.index(st.session_state["servidor_seleccionado_alertas"])
        except ValueError:
            default_index = 0

        # Fila de Filtro Principal de Servidores con Clave Dinámica
        col_filtro, col_limpieza = st.columns([4, 1])
        
        with col_filtro:
            sel_alr = st.selectbox(
                "Seleccione Servidor para Inspección de Alertas:", 
                lista_opciones, 
                index=default_index,
                key=f"sb_alertas_vivo_dyn_{st.session_state['key_semilla_alertas']}"
            )
        
        with col_limpieza:
            st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
            btn_limpiar = st.button("🧹 Limpiar Filtro", use_container_width=True, key="btn_limpiar_alertas_modulo")

        # LÓGICA DEL BOTÓN LIMPIAR (Reinicia la selección y altera la semilla)
        if btn_limpiar:
            st.session_state["servidor_seleccionado_alertas"] = "-- Seleccione un Servidor --"
            st.session_state["key_semilla_alertas"] += 1
            st.rerun()

        # Sincronizamos la selección actual en el estado interno
        st.session_state["servidor_seleccionado_alertas"] = sel_alr

        # REQUISITO EXIGIDO: Si no se ha elegido nada, congelar renderizado y no mostrar datos fantasma
        if sel_alr == "-- Seleccione un Servidor --":
            st.info("💡 Por favor, seleccione un servidor de la infraestructura para desplegar el estado de alertas de sus sensores indexados.")
            return

        # Localizar metadatos del nodo seleccionado
        serv_alr_info = next(s for s in servidores if f"{s['nombre_alias']} ({s['ip']})" == sel_alr)
        ip_alr_sel = serv_alr_info['ip']

        # Consultar la telemetría viva conectada con utils.py
        data_monitoreo = obtener_ultimo_monitoreo(ip_alr_sel)
        telemetria_viva = obtener_telemetria_total(serv_alr_info)
        umbrales_alr = obtener_umbrales_actuales(ip_alr_sel)

        st.markdown("---")
        st.markdown("#### 🚥 Estado Actual de los Sensores Indexados")

        val_cpu = float(telemetria_viva.get('cpu', 0.0))
        val_ram = float(telemetria_viva.get('ram', 0.0))

        # DISEÑO VISUAL DINÁMICO
        if val_cpu > 0.0 and val_ram > 0.0:
            c_cpu, c_ram = st.columns(2)
            with c_cpu:
                st.markdown("**Procesador (CPU)**")
                st.markdown(renderizar_semaforo(val_cpu, 70.0, 85.0, tipo="uso"), unsafe_allow_html=True)
            with c_ram:
                st.markdown("**Memoria Volátil Libre (RAM)**")
                pct_ram_libre = telemetria_viva.get('pct_ram', None)
                adv_r = float(umbrales_alr['ram_advertencia'])
                crit_r = float(umbrales_alr['ram_critico'])
                if val_ram >= 4.0: adv_r = 3.5
                st.markdown(renderizar_semaforo(val_ram, adv_r, crit_r, tipo="inverso", pct_libre=pct_ram_libre), unsafe_allow_html=True)
        
        elif val_ram > 0.0:
            st.markdown("**Memoria Volátil Libre (RAM)**")
            pct_ram_libre = telemetria_viva.get('pct_ram', None)
            adv_r = float(umbrales_alr['ram_advertencia'])
            crit_r = float(umbrales_alr['ram_critico'])
            if val_ram >= 4.0: adv_r = 3.5
            st.markdown(renderizar_semaforo(val_ram, adv_r, crit_r, tipo="inverso", pct_libre=pct_ram_libre), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 💾 Unidades de Almacenamiento Estático (Libre)")
        
        columnas_discos = st.columns(3)
        col_idx_actual = 0
        
        for i in range(1, 7):
            if serv_alr_info.get(f'id_sensor_disco_{i}', 0) > 0:
                val_disco = float(telemetria_viva.get(f'disco_{i}', 0.0))
                
                # ELIMINAR ALERTAS EN 0
                if val_disco == 0.0:
                    continue
                
                pct_disco_libre = telemetria_viva.get(f'pct_disco_{i}', None)
                adv_d = float(umbrales_alr.get(f'disco_{i}_advertencia', 40.0))
                crit_d = float(umbrales_alr.get(f'disco_{i}_critico', 15.0))
                
                if ip_alr_sel == "10.10.1.133":
                    if i == 1: adv_d = 35.0
                    if i == 2: adv_d = 65.0
                
                idx_col = col_idx_actual % 3
                with columnas_discos[idx_col]:
                    st.markdown(f"**Disco {i}**")
                    st.markdown(renderizar_semaforo(val_disco, adv_d, crit_d, tipo="inverso", pct_libre=pct_disco_libre), unsafe_allow_html=True)
                    st.markdown("### ")
                col_idx_actual += 1

    # =====================================================================
    # PESTAÑA 2: CONFIGURACIÓN AVANZADA DE UMBRALES
    # =====================================================================
    with tab_config_umbrales:
        st.markdown("### ")
        st.info("⚙️ Módulo de modificación de políticas de criticidad para operaciones centrales de Banco Caroní.")

# REPLICA EXACTA: Inyección idéntica de variables de sesión desde st.session_state
if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Nombre Completo")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "Usuario")
    
    mostrar_pantalla(cargo_usuario, id_usuario, login_usuario)