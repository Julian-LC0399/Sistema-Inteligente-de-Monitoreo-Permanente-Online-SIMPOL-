import streamlit as st
from database import obtener_lista_servidores, conectar_bd

def mostrar_pantalla(usuario_id=None):
    """
    Módulo de visualización de incidentes.
    Filtra y muestra alertas basadas en los 5 sensores críticos.
    """
    st.title("🔔 Centro de Alertas y Notificaciones")
    
    # 1. Selector de Servidor para Filtrar Alertas
    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("⚠️ No hay servidores registrados en el catálogo.")
        return

    opciones = {f"{s['nombre_alias']} ({s['ip']})": s['ip'] for s in servidores}
    seleccion = st.selectbox("Filtrar alertas por servidor:", list(opciones.keys()))
    ip_sel = opciones[seleccion]

    # 2. Obtención de datos (Actualizado para el nuevo SQL)
    alertas = obtener_alertas_por_ip(ip_sel)
    
    # Resumen de métricas rápidas
    criticas = [a for a in alertas if a['estado_sistema'] == 'CRÍTICO']
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Alertas Críticas (Recientes)", len(criticas), delta_color="inverse")
    with col2:
        st.metric("Total Incidentes Detectados", len(alertas))

    st.divider()

    # 3. Listado de Alertas con Formato Multi-Sensor
    st.subheader(f"Historial de eventos: {seleccion}")
    
    if not alertas:
        st.success(f"✅ El servidor {seleccion} no presenta incidencias en los últimos registros.")
    else:
        for alerta in alertas:
            fecha = alerta['fecha_registro']
            estado = alerta['estado_sistema']
            
            # Construimos un mensaje detallado con los 5 sensores
            detalle = (f"CPU: {alerta['val_cpu']}% | RAM: {alerta['val_ram']}% | "
                       f"DISCO: {alerta['val_disco']}% | RED: {alerta['val_red']}Mb | "
                       f"LAT: {alerta['val_latencia']}ms")
            
            if estado == "CRÍTICO":
                st.error(f"🔴 **CRÍTICO** | {fecha} \n\n {detalle}")
            elif estado == "PRECAUCIÓN":
                st.warning(f"🟠 **PRECAUCIÓN** | {fecha} \n\n {detalle}")
            else:
                st.info(f"🔵 **ESTABLE** | {fecha} | Registro de rutina.")

def obtener_alertas_por_ip(ip):
    """
    Consulta la tabla monitoreo buscando estados de advertencia o falla.
    Actualizado para las nuevas columnas val_xxx.
    """
    conn = conectar_bd()
    alertas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Cambiamos las columnas a la nueva estructura SQL
            # Filtramos cualquier estado que no sea 'ÓPTIMO' (o 'ESTABLE' según tu SQL)
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