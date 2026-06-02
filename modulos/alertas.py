import streamlit as st
import traceback
from datetime import datetime, timedelta
from database import obtener_lista_servidores, conectar_bd

# =====================================================================
# CONSULTAS DE BASE DE DATOS PARA LA PESTAÑA DE ALERTAS
# =====================================================================
def obtener_ultimo_monitoreo(ip):
    """
    Recupera el último registro de telemetría enviado por agente.py 
    para el servidor seleccionado desde la tabla 'monitoreo'.
    """
    conn = conectar_bd()
    registro = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM monitoreo 
                WHERE ip_servidor = %s 
                ORDER BY id_monitoreo DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            registro = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception:
            pass
    return registro

def obtener_umbrales_actuales(ip):
    """Busca el último registro de configuración de umbrales para esa IP en porcentaje."""
    umbrales = {
        "cpu_advertencia": 70, "cpu_critico": 85,
        "ram_advertencia": 80, "ram_critico": 90
    }
    for i in range(1, 7):
        umbrales[f"disco_{i}_advertencia"] = 80.0 
        umbrales[f"disco_{i}_critico"] = 95.0
    for i in range(1, 6):
        umbrales[f"servicio_{i}_advertencia"] = 50.0 
        umbrales[f"servicio_{i}_critico"] = 100.0

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
            if res and "disco_1_advertencia" in res:
                umbrales = res
            cursor.close()
            conn.close()
        except Exception:
            pass 
    return umbrales

def guardar_nuevo_umbral(usuario_id, ip, cpu_adv, cpu_crit, ram_adv, ram_crit, discos_umbrales, servicios_umbrales, motivo):
    """Inserta la auditoría de cambio de semáforos en la base de datos."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_umbrales 
                (ip_servidor, usuario_id, cpu_advertencia, cpu_critico, 
                 ram_advertencia, ram_critico, 
                 disco_1_advertencia, disco_1_critico, 
                 disco_2_advertencia, disco_2_critico, 
                 disco_3_advertencia, disco_3_critico, 
                 disco_4_advertencia, disco_4_critico, 
                 disco_5_advertencia, disco_5_critico,
                 disco_6_advertencia, disco_6_critico,
                 servicio_1_advertencia, servicio_1_critico,
                 servicio_2_advertencia, servicio_2_critico,
                 servicio_3_advertencia, servicio_3_critico,
                 servicio_4_advertencia, servicio_4_critico,
                 servicio_5_advertencia, servicio_5_critico,
                 justificacion, fecha_change)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                ip, usuario_id, float(cpu_adv), float(cpu_crit), float(ram_adv), float(ram_crit),
                float(discos_umbrales['d1_adv']), float(discos_umbrales['d1_crit']),
                float(discos_umbrales['d2_adv']), float(discos_umbrales['d2_crit']),
                float(discos_umbrales['d3_adv']), float(discos_umbrales['d3_crit']),
                float(discos_umbrales['d4_adv']), float(discos_umbrales['d4_crit']),
                float(discos_umbrales['d5_adv']), float(discos_umbrales['d5_crit']),
                float(discos_umbrales['d6_adv']), float(discos_umbrales['d6_crit']),
                int(servicios_umbrales['s1_adv']), int(servicios_umbrales['s1_crit']),
                int(servicios_umbrales['s2_adv']), int(servicios_umbrales['s2_crit']),
                int(servicios_umbrales['s3_adv']), int(servicios_umbrales['s3_crit']),
                int(servicios_umbrales['s4_adv']), int(servicios_umbrales['s4_crit']),
                int(servicios_umbrales['s5_adv']), int(servicios_umbrales['s5_crit']),
                motivo, datetime.now()
            )
            cursor.execute(query, valores)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception:
            pass
    return False

# =====================================================================
# AUXILIAR GRÁFICO PARA SEMÁFOROS (VERDE, AMARILLO, ROJO)
# =====================================================================
def renderizar_semaforo(valor, adv, crit, es_servicio=False):
    """Calcula el estado y devuelve un componente visual HTML con el color respectivo."""
    # Lógica de colores invertida si es necesario, o estándar de porcentaje de uso:
    if valor >= crit:
        color = "#e53e3e"  # Rojo
        texto = "CRÍTICO"
    elif valor >= adv:
        color = "#f6e05e"  # Amarillo
        texto = "ADVERTENCIA"
    else:
        color = "#48bb78"  # Verde
        texto = "NORMAL"
        
    return f"""
    <div style="background-color: {color}; padding: 8px; border-radius: 6px; text-align: center; color: { '#000' if color=='#f6e05e' else '#fff' }; font-weight: bold; font-size: 14px;">
        {texto} ({valor}%)
    </div>
    """

# =====================================================================
# VISTA PRINCIPAL CON DOS PESTAÑAS (UMBRALES Y ALERTAS)
# =====================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Usuario", rol_usuario="operador"):
    st.markdown('<h2 style="color:#003366;">🔔 Panel de Control de Semáforos y Alertas</h2>', unsafe_allow_html=True)
    st.markdown(f"f👤 **Responsable:** {nombre_analista} (`{usuario_login}`) | Rol: {rol_usuario.upper()}")
    st.markdown("<br>", unsafe_allow_html=True)

    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("⚠️ No hay servidores activos registrados en la plataforma.")
        return

    # Definición de las dos pestañas institucionales
    tab_alertas_vivo, tab_config_umbrales = st.tabs(["🚨 Monitoreo de Alertas (Sensores)", "⚙️ Configuración Avanzada de Umbrales"])

    # =====================================================================
    # PESTAÑA 1: MONITOR DE ALERTAS POR SERVIDOR (ESTADOS VERDE/AMARILLO/ROJO)
    # =====================================================================
    with tab_alertas_vivo:
        st.markdown("### ")
        opciones_alr = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        sel_alr = st.selectbox("Seleccione Servidor para Inspección de Alertas:", list(opciones_alr.keys()), key="sb_alertas_vivo")
        serv_alr_info = opciones_alr[sel_alr]
        ip_alr_sel = serv_alr_info['ip']

        # Extraer telemetría y configuraciones
        data_monitoreo = obtener_ultimo_monitoreo(ip_alr_sel)
        umbrales_alr = obtener_umbrales_actuales(ip_alr_sel)

        # VERIFICACIÓN DE AGENTE CORRIENDO (Latido / Heartbeat de 60 segundos)
        agente_corriendo = False
        fecha_registro_agente = None
        
        if data_monitoreo and 'fecha_registro' in data_monitoreo:
            fecha_registro_agente = data_monitoreo['fecha_registro']
            # Si el último registro fue hace menos de 1 minuto, el agente está vivo
            if datetime.now() - fecha_registro_agente < timedelta(minutes=1):
                agente_corriendo = True

        # Mostrar estado de la sonda agente.py
        if agente_corriendo:
            st.success(f"🟢 **Agente Activo:** `agente.py` se está ejecutando correctamente en tiempo real. Última actualización: {fecha_registro_agente.strftime('%H:%M:%S')}")
        else:
            st.error(f"🔴 **Agente Inactivo / Desconectado:** `agente.py` no está corriendo. Mostrando el último estado histórico registrado en la tabla de monitoreo ({fecha_registro_agente.strftime('%d/%m/%Y %H:%M:%S') if fecha_registro_agente else 'Sin registros'}).")

        st.markdown("---")
        st.markdown("#### 🚥 Estado Actual de los Sensores Indexados")

        if not data_monitoreo:
            st.info("📭 No existen registros previos de telemetría para este servidor en la tabla 'monitoreo'.")
        else:
            # Iterar de manera limpia sobre cada sensor para aplicar la lógica del semáforo
            
            # --- EVALUACIÓN CPU y RAM ---
            c_cpu, c_ram = st.columns(2)
            with c_cpu:
                st.markdown("**Procesador (CPU)**")
                val_cpu = float(data_monitoreo.get('cpu_uso', 0.0))
                html_semaforo = renderizar_semaforo(val_cpu, float(umbrales_alr['cpu_advertencia']), float(umbrales_alr['cpu_critico']))
                st.markdown(html_semaforo, unsafe_allow_html=True)

            with c_ram:
                st.markdown("**Memoria Volátil (RAM)**")
                val_ram = float(data_monitoreo.get('ram_uso', 0.0))
                html_semaforo = renderizar_semaforo(val_ram, float(umbrales_alr['ram_advertencia']), float(umbrales_alr['ram_critico']))
                st.markdown(html_semaforo, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- EVALUACIÓN DE MATRIZ DE DISCOS (Si están registrados) ---
            st.markdown("##### 💾 Unidades de Almacenamiento Estático")
            columnas_discos = st.columns(3)
            
            for i in range(1, 7):
                # Verificar si el sensor del disco está registrado
                if serv_alr_info.get(f'id_sensor_disco_{i}', 0) > 0:
                    idx_col = (i - 1) % 3
                    with columnas_discos[idx_col]:
                        st.markdown(f"**Disco {i}**")
                        # Se asume que el agente reporta columnas 'disco_1_uso', etc. en porcentaje
                        val_disco = float(data_monitoreo.get(f'disco_{i}_uso', 0.0))
                        adv_d = float(umbrales_alr.get(f'disco_{i}_advertencia', 80.0))
                        crit_d = float(umbrales_alr.get(f'disco_{i}_critico', 95.0))
                        
                        html_d = renderizar_semaforo(val_disco, adv_d, crit_d)
                        st.markdown(html_d, unsafe_allow_html=True)
                        st.markdown("### ")

            # --- EVALUACIÓN DE SENSORES DE SERVICIO (Si están registrados) ---
            st.markdown("##### ⚙️ Servicios Basales de Infraestructura")
            columnas_servicios = st.columns(5)
            
            for i in range(1, 6):
                # Verificar si el servicio está registrado
                if serv_alr_info.get(f'id_sensor_servicio_{i}', 0) > 0:
                    with columnas_servicios[i-1]:
                        st.markdown(f"**Servicio {i}**")
                        # Se mapea el estado del servicio a porcentaje de falla/caída (0% OK, 100% Caído)
                        # Si en monitoreo viene como 1 (Activo) -> 0% de error. Si viene como 0 (Inactivo) -> 100% de error.
                        estado_raw = int(data_monitoreo.get(f'servicio_{i}_estado', 1))
                        val_servicio_porcentaje = 0.0 if estado_raw == 1 else 100.0
                        
                        html_s = renderizar_semaforo(val_servicio_porcentaje, 50.0, 100.0, es_servicio=True)
                        st.markdown(html_s, unsafe_allow_html=True)

    # =====================================================================
    # PESTAÑA 2: CONFIGURACIÓN DE UMBRALES (CÓDIGO ANTERIOR EN PORCENTAJE)
    # =====================================================================
    with tab_config_umbrales:
        st.markdown("### ")
        opciones_cfg = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        seleccion_cfg = st.selectbox("Seleccione Servidor para Configurar Parámetros:", list(opciones_cfg.keys()), key="sb_config_umbrales")
        serv_info = opciones_cfg[seleccion_cfg]
        ip_sel = serv_info['ip']

        metrica_label = st.selectbox(
            "Seleccione Métrica / Sensor Registrado para Modificar:", 
            [
                "CPU", "RAM", 
                "DISCO 1 (C:\\)", "DISCO 2 (F:\\)", "DISCO 3 (E:\\)", "DISCO 4 (D:\\)", "DISCO 5 (G:\\)", "DISCO 6 (H:\\)",
                "SERVICIO 1", "SERVICIO 2", "SERVICIO 3", "SERVICIO 4", "SERVICIO 5"
            ], 
            key="alr_metrica_sel"
        )

        # Validación estricta de existencia en la infraestructura
        if "DISCO" in metrica_label:
            num_disco = int(metrica_label.split(" ")[1])
            if serv_info.get(f'id_sensor_disco_{num_disco}', 0) == 0:
                st.error(f"❌ El volumen seleccionado ({metrica_label}) no se encuentra indexado en este servidor.")
                return
                
        if "SERVICIO" in metrica_label:
            num_servicio = int(metrica_label.split(" ")[1])
            if serv_info.get(f'id_sensor_servicio_{num_servicio}', 0) == 0:
                st.error(f"❌ El servicio seleccionado ({metrica_label}) no se encuentra indexado en este servidor.")
                return

        u_actuales = obtener_umbrales_actuales(ip_sel)

        if metrica_label == "CPU":
            adv_threshold = float(u_actuales['cpu_advertencia'])
            crit_threshold = float(u_actuales['cpu_critico'])
        elif metrica_label == "RAM":
            adv_threshold = float(u_actuales['ram_advertencia'])
            crit_threshold = float(u_actuales['ram_critico'])
        elif "DISCO" in metrica_label:
            num_d = metrica_label.split(" ")[1]
            adv_threshold = float(u_actuales.get(f'disco_{num_d}_advertencia', 80.0))
            crit_threshold = float(u_actuales.get(f'disco_{num_d}_critico', 95.0))
        else:
            num_s = metrica_label.split(" ")[1]
            adv_threshold = float(u_actuales.get(f'servicio_{num_s}_advertencia', 50.0))
            crit_threshold = float(u_actuales.get(f'servicio_{num_s}_critico', 100.0))

        with st.container(border=True):
            st.markdown(f"#### ⚙️ Modificar Parámetros de Alerta en Caliente (% Uso)")
            
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                nuevo_adv = st.number_input(f"Umbral Advertencia {metrica_label} (%)", min_value=1.0, max_value=100.0, value=adv_threshold, step=1.0, key="alr_in_adv")
            with col_u2:
                nuevo_crit = st.number_input(f"Umbral Crítico {metrica_label} (%)", min_value=1.0, max_value=100.0, value=crit_threshold, step=1.0, key="alr_in_crit")
            
            motivo = st.text_area("Justificación obligatoria del cambio (Auditoría CSU):", placeholder="Ej: Redimensionamiento del perfil de alertas por contingencia operativa.", key="txt_motivo_cfg")

            es_operador = rol_usuario.lower() == "operador"
            if es_operador:
                st.info("ℹ️ Su cuenta posee Rol: OPERADOR. Puede auditar la gráfica, pero no reescribir la base de datos.")

            if st.button("🚀 APLICAR NUEVOS UMBRALES EN CALIENTE", use_container_width=True, disabled=es_operador, key="btn_save_umbrales"):
                if not motivo.strip():
                    st.error("❌ Error: Debe registrar la justificación en la bitácora para aplicar los cambios.")
                    return
                if nuevo_adv >= nuevo_crit:
                    st.error("❌ Error de consistencia: El porcentaje Crítico debe ser estrictamente MAYOR al de Advertencia.")
                    return

                try:
                    d_umbrales = {f'd{i}_adv': nuevo_adv if f"DISCO {i}" in metrica_label else float(u_actuales.get(f'disco_{i}_advertencia', 80.0)) for i in range(1, 7)}
                    d_umbrales.update({f'd{i}_crit': nuevo_crit if f"DISCO {i}" in metrica_label else float(u_actuales.get(f'disco_{i}_critico', 95.0)) for i in range(1, 7)})
                    
                    s_umbrales = {f's{i}_adv': int(nuevo_adv) if f"SERVICIO {i}" in metrica_label else int(u_actuales.get(f'servicio_{i}_advertencia', 50)) for i in range(1, 6)}
                    s_umbrales.update({f's{i}_crit': int(nuevo_crit) if f"SERVICIO {i}" in metrica_label else int(u_actuales.get(f'servicio_{i}_critico', 100)) for i in range(1, 6)})

                    cpu_p_adv = nuevo_adv if metrica_label == "CPU" else u_actuales['cpu_advertencia']
                    cpu_p_crit = nuevo_crit if metrica_label == "CPU" else u_actuales['cpu_critico']
                    ram_p_adv = nuevo_adv if metrica_label == "RAM" else u_actuales['ram_advertencia']
                    ram_p_crit = nuevo_crit if metrica_label == "RAM" else u_actuales['ram_critico']

                    exito = guardar_nuevo_umbral(usuario_id, ip_sel, cpu_p_adv, cpu_p_crit, ram_p_adv, ram_p_crit, d_umbrales, s_umbrales, motivo)
                    
                    if exito:
                        st.success("🎉 ¡Umbrales actualizados con éxito en la base de datos!")
                        st.rerun()
                    else:
                        st.error("❌ Error crítico: No se pudo guardar el registro.")
                except Exception:
                    st.error("⚠️ Error procesando la actualización de alertas.")

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Nombre Completo")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "Usuario")
    rol_actual = st.session_state.get("rol", "operador")
    
    mostrar_pantalla(cargo_usuario, id_usuario, login_usuario, rol_actual)