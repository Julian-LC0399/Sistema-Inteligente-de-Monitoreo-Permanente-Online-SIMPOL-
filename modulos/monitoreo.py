import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos
import time

def mostrar_pantalla(nombre_analista="Analista"):
    st.title("🛰️ Monitoreo de Infraestructura - Banco Caroní")
    
    # 1. OBTENER CATÁLOGO DE SERVIDORES
    servidores = obtener_lista_servidores()
    
    if not servidores:
        st.warning("⚠️ No se encontraron servidores en el catálogo. Verifique la tabla 'servidores_it'.")
        return

    # 2. SELECTOR DE SERVIDOR
    opciones_servidores = {f"{s['nombre_alias']} ({s['ip']})": s['ip'] for s in servidores}
    seleccion = st.selectbox("Seleccione el servidor a inspeccionar:", list(opciones_servidores.keys()))
    ip_seleccionada = opciones_servidores[seleccion]

    # 3. OBTENER DATOS ESPECÍFICOS (Actualizado para traer las 5 métricas)
    datos = obtener_datos_historicos(ip_seleccionada)

    if not datos:
        st.info(f"Esperando datos en tiempo real para {seleccion}...")
        # Valores por defecto
        reciente = {
            'val_cpu': 0, 'val_ram': 0, 'val_disco': 0, 
            'val_red': 0, 'val_latencia': 0, 'estado_sistema': "SIN DATOS"
        }
    else:
        # El primer registro es el más reciente (val_cpu, val_ram, val_disco, val_red, val_latencia)
        reciente = datos[0]

    # 4. DASHBOARD DE ESTADO - FILA 1: CPU, RAM Y DISCO (Uso de Recursos)
    st.subheader("Estado de Recursos Críticos")
    col1, col2, col3 = st.columns(3)

    with col1:
        cpu = reciente['val_cpu']
        color_cpu = "#2ecc71" if cpu < 70 else "#f39c12" if cpu < 85 else "#e74c3c"
        st.metric("Carga CPU", f"{cpu}%", delta_color="inverse")
        st.markdown(f'<div style="height:10px; background-color:#ecf0f1; border-radius:5px;"><div style="width:{cpu}%; height:10px; background-color:{color_cpu}; border-radius:5px;"></div></div>', unsafe_allow_html=True)

    with col2:
        ram = reciente['val_ram']
        color_ram = "#3498db" if ram < 80 else "#e74c3c"
        st.metric("Memoria RAM", f"{ram}%")
        st.markdown(f'<div style="height:10px; background-color:#ecf0f1; border-radius:5px;"><div style="width:{ram}%; height:10px; background-color:{color_ram}; border-radius:5px;"></div></div>', unsafe_allow_html=True)

    with col3:
        disco = reciente['val_disco']
        color_disco = "#9b59b6" if disco < 85 else "#e74c3c"
        st.metric("Uso de Disco", f"{disco}%")
        st.markdown(f'<div style="height:10px; background-color:#ecf0f1; border-radius:5px;"><div style="width:{disco}%; height:10px; background-color:{color_disco}; border-radius:5px;"></div></div>', unsafe_allow_html=True)

    # 5. DASHBOARD - FILA 2: RED Y CONECTIVIDAD
    st.markdown("---")
    st.subheader("Rendimiento de Red y Conectividad")
    col_a, col_b = st.columns(2)

    with col_a:
        red = reciente['val_red']
        st.metric("Tráfico de Red", f"{red} Mbps", "Entrada/Salida")
        
    with col_b:
        lat = reciente['val_latencia']
        color_lat = "normal" if lat < 100 else "off"
        st.metric("Latencia (Ping)", f"{lat} ms", delta=f"{lat-5} ms", delta_color=color_lat)

    # 6. SEMÁFORO DE ESTADO CRÍTICO
    st.markdown("---")
    estado_actual = reciente['estado_sistema']
    st.write(f"### Estado General del Servidor: **{estado_actual}**")
    
    if estado_actual == "CRÍTICO":
        st.error(f"⚠️ ALERTA: El servidor {seleccion} presenta saturación en uno o más sensores.")
    elif estado_actual == "PRECAUCIÓN":
        st.warning(f"🔔 AVISO: Se recomienda revisar la carga en {seleccion}.")
    else:
        st.success(f"✅ El servidor {seleccion} opera con normalidad.")

    # 7. HISTÓRICO EXPANDIBLE (Actualizado con las 5 columnas)
    with st.expander("Ver bitácora detallada de telemetría"):
        if datos:
            # Encabezado de tabla para mayor orden
            st.markdown("""
            | Fecha y Hora | CPU | RAM | DISCO | RED | LAT | ESTADO |
            | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
            """)
            for d in datos[:12]: 
                st.write(f"| {d['fecha_registro']} | {d['val_cpu']}% | {d['val_ram']}% | {d['val_disco']}% | {d['val_red']}Mb | {d['val_latencia']}ms | {d['estado_sistema']} |")
        else:
            st.write("No hay registros históricos disponibles.")

if __name__ == "__main__":
    mostrar_pantalla()