import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos

# =====================================================================
# SECCIÓN 1: COMPONENTE DINÁMICO REFRESCO EN TIEMPO REAL (FRAGMENT)
# =====================================================================

@st.fragment(run_every=3)
def renderizar_telemetria_v33(servidores):
    """
    Bloque aislado que se refresca automáticamente cada 3 segundos.
    Mueve el selector al contexto del fragmento para evitar congelamiento de argumentos.
    Procesamiento puro mediante estructuras de datos nativas (Listas y Diccionarios).
    """
    st.markdown("---")
    
    # 1. CONSTRUCCIÓN DEL SELECTOR DENTRO DEL FRAGMENTO
    # Sanitización estricta de cadenas (TRIM implícito en la IP)
    dict_servidores = {f"🖥️ {s['nombre_alias']} ({str(s['ip']).strip()})": s for s in servidores}
    
    seleccion = st.selectbox(
        "Seleccione el Servidor del Banco para Monitorear:",
        options=list(dict_servidores.keys()),
        key="simpol_live_server_selector"
    )
    
    # Extracción de la metadata de infraestructura
    info_servidor = dict_servidores[seleccion]
    ip_objetivo = str(info_servidor['ip']).strip()
    
    st.info(f"🛰️ **Línea de datos activa:** Conectado a {info_servidor['nombre_alias']} ({ip_objetivo}) | S.O: {info_servidor['sistema_operativo']}")

    # 2. CONSUMO DE TELEMETRÍA Y CONTROL DE BUFFER VACÍO
    datos = obtener_datos_historicos(ip_objetivo)
    
    if not datos:
        st.error(f"⏳ Esperando transmisiones de telemetría del agente para el nodo {ip_objetivo}...")
        st.caption("Nota CSU: Si el nodo está registrado en la base de datos, verifique que el agente remoto esté transmitiendo hacia el MySQL central.")
        if st.button("Forzar Limpieza de Buffer (Caché)", key="btn_clear_cache_mon"):
            st.cache_data.clear()
            st.rerun()
        return

    # Extraemos la muestra más reciente del backend (Índice 0)
    reciente = datos[0]
    
    # =====================================================================
    # 3. FILA 1: RENDIMIENTO NÚCLEO (MÉTRICAS BASE ADAPTATIVAS N/A)
    # =====================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    # Validación dinámica de existencia de sensores activos en el catálogo del Banco
    cpu_activa = int(info_servidor.get('id_sensor_cpu') or 0) > 0
    ram_activa = int(info_servidor.get('id_sensor_ram') or 0) > 0
    red_activa = int(info_servidor.get('id_sensor_red') or 0) > 0
    lat_activa = int(info_servidor.get('id_sensor_latencia') or 0) > 0

    col1.metric(
        label="🔥 Carga de CPU", 
        value=f"{reciente['val_cpu']}%" if cpu_activa else "N/A",
        help="Monitoreo de procesador central." if cpu_activa else "Métrica no configurada para este servidor en el Catálogo."
    )
    
    col2.metric(
        label="🧠 RAM Disponible", 
        value=f"{reciente['val_ram']} GB" if ram_activa else "N/A",
        help="Memoria RAM física neta disponible." if ram_activa else "Métrica no configurada para este servidor en el Catálogo."
    )
    
    col3.metric(
        label="🌐 Tráfico de Red", 
        value=f"{reciente['val_red']} Mb/s" if red_activa else "N/A",
        help="Ancho de banda ocupado en la interfaz." if red_activa else "Métrica no configurada para este servidor en el Catálogo."
    )
    
    col4.metric(
        label="⏳ Latencia Enlace", 
        value=f"{reciente['val_latencia']} ms" if lat_activa else "N/A",
        help="Tiempo de respuesta ICMP / API." if lat_activa else "Métrica no configurada para este servidor en el Catálogo."
    )

    st.markdown("---")
    st.write("### 💽 Estado de Almacenamiento Adaptativo (Matriz de 5 Volúmenes)")

    # 4. ITERACIÓN FILTRADA DE DISCOS SEGÚN SENSORES ACTIVOS (> 0)
    discos_activos = []
    for i in range(1, 6):
        try:
            id_sensor = int(info_servidor.get(f'id_sensor_disco_{i}') or 0)
            if id_sensor > 0:
                discos_activos.append(i)
        except (ValueError, TypeError):
            continue

    if not discos_activos:
        st.warning("ℹ️ Este servidor no posee volúmenes de almacenamiento indexados en la base de datos.")
    else:
        # Generación dinámica de columnas según cantidad de discos activos
        columnas_discos = st.columns(len(discos_activos))
        
        for idx, num_disco in enumerate(discos_activos):
            val_actual_gb = reciente[f'val_disco_{num_disco}']
            letra_volumen = info_servidor.get(f'letra_disco_{num_disco}')
            
            # Formateo estético de etiquetas vacías en Python básico
            if not letra_volumen or str(letra_volumen).strip() == "":
                letra_volumen = f"Vol_{num_disco}:\\"

            # Cálculo de tendencia histórica utilizando deltas reales (Muestra actual vs anterior)
            delta_texto = "0.0 GB"
            if len(datos) > 1:
                val_anterior_gb = datos[1][f'val_disco_{num_disco}']
                diferencia_gb = round(val_actual_gb - val_anterior_gb, 2)
                if diferencia_gb > 0:
                    delta_texto = f"+{diferencia_gb} GB"
                elif diferencia_gb < 0:
                    delta_texto = f"{diferencia_gb} GB"

            # Renderizado de la celda de almacenamiento
            columnas_discos[idx].metric(
                label=f"Letra {letra_volumen}",
                value=f"{val_actual_gb} GB",
                delta=delta_texto,
                delta_color="normal", 
                help=f"Sensor ID: {info_servidor[f'id_sensor_disco_{num_disco}']} - Espacio Libre reportado."
            )
            
            # Contenedor estético HTML descriptivo
            columnas_discos[idx].markdown(f"""
                <div style="background-color: #f8f9fa; padding: 5px; border-radius: 4px; text-align: center; font-size: 11px; color: #212529; font-weight: bold; margin-top: 3px; border: 1px solid #e9ecef;">
                    📍 {letra_volumen}
                </div>
            """, unsafe_allow_html=True)

    # 5. SEMÁFORO OPERATIVO INTEGRAL
    st.markdown("---")
    estado_sistema = str(reciente.get('estado_sistema', 'ÓPTIMO')).upper().strip()
    
    if "CRÍTICO" in estado_sistema or "CRITICO" in estado_sistema:
        st.error(f"🔴 **Estado General: CRÍTICO**\n\n⚠️ ALERTA DE INFRAESTRUCTURA: El servidor {info_servidor['nombre_alias']} ha sobrepasado los umbrales críticos establecidos por el CSU.")
    elif estado_sistema in ["PRECAUCIÓN", "PRECAUCION", "ADVERTENCIA", "AMARILLO"]:
        st.warning(f"🟡 **Estado General: PRECAUCIÓN**\n\n🔔 AVISO OPERATIVO: Rangos preventivos detectados en el nodo {info_servidor['nombre_alias']}. Monitoree el almacenamiento.")
    else:
        st.success(f"🟢 **Estado General: ÓPTIMO**\n\n✅ Operación Normal: El nodo {info_servidor['nombre_alias']} opera de forma estable bajo los rangos ideales.")

    st.caption(f"🔄 Sincronización SIMPOL activa • Registros en memoria: {len(datos)} métricas.")


# =====================================================================
# SECCIÓN 2: CONTROLADOR Y VISTA PRINCIPAL
# =====================================================================

def mostrar_pantalla():
    """Lanza la interfaz principal verificando la matriz de permisos de la sesión."""
    
    # Verificación de Seguridad Atómica (Matriz Muchos a Muchos)
    if "usuario" in st.session_state:
        permisos_activos = st.session_state.get("permisos", [])
        if "VER_SISTEMA" not in permisos_activos:
            st.error("🚫 Acceso Denegado: Su cuenta no posee el código de permiso [VER_SISTEMA] en la matriz del Banco.")
            return

    # Encabezado Corporativo Actualizado con Icono Sincronizado
    st.markdown('<h2 style="color:#003366;">🖥️ Monitoreo de servidores - Banco Caroní</h2>', unsafe_allow_html=True)
    
    # Extracción del catálogo de servidores activos (estado_monitoreo = 1)
    servidores = obtener_lista_servidores()
    
    if not servidores:
        st.warning("⚠️ No se encontraron servidores activos o mapeados en el catálogo central de la base de datos.")
        return

    # Ejecución del fragmento dinámico aislado
    renderizar_telemetria_v33(servidores)


if __name__ == "__main__":
    st.set_page_config(page_title="SIMPOL - Monitoreo", layout="wide")
    mostrar_pantalla()