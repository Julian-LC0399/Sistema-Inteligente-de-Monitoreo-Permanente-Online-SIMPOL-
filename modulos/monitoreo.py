import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos
import time

# Definimos la zona de telemetría como un fragmento aislado del resto de SIMPOL
@st.fragment(run_every=3)
def renderizar_telemetria_dinamica(ip_seleccionada, seleccion, info_servidor):
    """
    Bloque aislado que se refresca automáticamente cada 3 segundos.
    Muestra los datos en tiempo real de RAM y 5 discos leídos directamente en GB desde la BD V3.2.
    SOLUCIÓN ARQUITECTÓNICA: Lee las etiquetas de los volúmenes dinámicamente de la base de datos.
    """
    # OBTENER DATOS ESPECÍFICOS (Histórico reciente de 5 discos)
    datos = obtener_datos_historicos(ip_seleccionada)

    if not datos:
        st.info(f"⏳ Esperando transmisiones de telemetría del agente para el nodo {ip_seleccionada}...")
        if st.button("Forzar reconexión con el agente", key="btn_reconect_agente"):
            st.rerun()
        return

    reciente = datos[0]
    
    # Extraemos valores actuales de la telemetría viva base
    pct_cpu_uso = reciente['val_cpu']
    ram_libre_gb = reciente['val_ram']  # Ya viene expresado directamente en GB desde la BD

    # === 1. DISPOSICIÓN DE MÉTRICAS BASE EN PANTALLA (Fila 1) ===
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        label="🌡️ Carga de CPU", 
        value=f"{pct_cpu_uso}%"
    )
    
    col2.metric(
        label="🧠 RAM Disponible", 
        value=f"{ram_libre_gb} GB",
        help="Cantidad neta de memoria RAM física libre en el sistema operativo."
    )
    
    col3.metric(label="🌐 Rendimiento Red", value=f"{reciente['val_red']} Mb/s")
    col4.metric(label="⏳ Latencia de Enlace", value=f"{reciente['val_latencia']} ms")

    st.markdown("---")
    st.write("### 💽 Estado de Almacenamiento Dinámico (Multi-Volumen)")

    # === 2. PROCESAMIENTO MÚLTIPLE DE HASTA 5 DISCOS DINÁMICOS ===
    # Identificamos cuáles discos realmente tienen un sensor mapeado (> 0) en el catálogo del servidor
    discos_activos = []
    for i in range(1, 6):
        if info_servidor.get(f'id_sensor_disco_{i}', 0) > 0:
            discos_activos.append(i)

    if not discos_activos:
        st.caption("ℹ️ No hay volúmenes de disco indexados para este servidor en el catálogo.")
    else:
        # Creamos columnas dinámicas según la cantidad de discos activos encontrados
        columnas_discos = st.columns(len(discos_activos))
        
        for idx, num_disco in enumerate(discos_activos):
            disco_libre_gb = reciente[f'val_disco_{num_disco}']  # Ya viene expresado en GB desde la BD
            
            # SOLUCIÓN ARQUITECTÓNICA: Extracción dinámica de etiquetas directo de la BD V3.2
            letra_volumen = info_servidor.get(f'letra_disco_{num_disco}', f"Disk_{num_disco}")
            
            # Si por alguna razón la cadena viene vacía de la BD, asignamos un fallback descriptivo
            if not letra_volumen or letra_volumen.strip() == "":
                letra_volumen = f"Vol_{num_disco}"
            
            # Cálculo de tendencia histórica del volumen específico utilizando deltas en Gigabytes reales
            delta_disco = None
            if len(datos) > 1:
                val_anterior_gb = datos[1][f'val_disco_{num_disco}']
                diferencia_gb = round(disco_libre_gb - val_anterior_gb, 2)
                
                # Formateo visual del Delta según el signo
                if diferencia_gb > 0:
                    delta_disco = f"+{diferencia_gb} GB"
                elif diferencia_gb < 0:
                    delta_disco = f"{diferencia_gb} GB"
                else:
                    delta_disco = "0.0 GB"

            # Renderizado en su respectiva columna adaptativa
            columnas_discos[idx].metric(
                label=f"Volumen {letra_volumen}",
                value=f"{disco_libre_gb} GB",
                delta=delta_disco,
                delta_color="inverse",  # Alerta visual si disminuye el espacio libre
                help=f"Espacio libre neto reportado por el sensor asignado al volumen {letra_volumen}"
            )
            
            # Impresión del resumen de auditoría individual compacto por debajo de la métrica
            columnas_discos[idx].markdown(f"""
                <div style="background-color: #f8f9fa; padding: 6px; border-radius: 4px; text-align: center; font-size: 11px; color: #555; margin-top:5px; border: 1px solid #e9ecef;">
                    <b>{letra_volumen} real:</b> {disco_libre_gb} GB Libres
                </div>
            """, unsafe_allow_html=True)

    # === 3. SEMÁFORO DE ESTADO CRÍTICO ===
    st.markdown("---")
    estado_actual = reciente['estado_sistema']
    st.write(f"### Estado General del Servidor: **{estado_actual}**")
    
    if estado_actual == "CRÍTICO":
        st.error(f"⚠️ ALERTA: El servidor {seleccion} presenta saturación o falta de disponibilidad crítica en uno o más sensores.")
    elif estado_actual == "PRECAUCIÓN":
        st.warning(f"🔔 AVISO: Se recomienda revisar la carga o la reducción de espacio libre en {seleccion}.")
    else:
        st.success(f"✅ El servidor {seleccion} opera con normalidad y rangos óptimos de disponibilidad.")

    st.caption("🔄 Actualización automática de telemetría activa (Aislado vía Fragment cada 3s)")


def mostrar_pantalla(nombre_analista="Analista"):
    st.markdown('<h2 style="color:#003366;">🛰️ Monitoreo de Infraestructura - Banco Caroní</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. OBTENER CATÁLOGO DE SERVIDORES
    servidores = obtener_lista_servidores()
    
    if not servidores:
        st.warning("⚠️ No se encontraron servidores en el catálogo. Verifique la tabla 'servidores'.")
        return

    # 2. SELECTOR DE SERVIDOR
    opciones_servidores = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
    
    seleccion = st.selectbox(
        "Seleccione el servidor a inspeccionar:", 
        list(opciones_servidores.keys()), 
        key="monitoreo_server_select_final"
    )
    serv_info = opciones_servidores[seleccion]
    ip_seleccionada = serv_info['ip']

    # Invocamos el fragmento dinámico pasando la info completa del catálogo
    renderizar_telemetria_dinamica(ip_seleccionada, seleccion, serv_info)

if __name__ == "__main__":
    mostrar_pantalla()