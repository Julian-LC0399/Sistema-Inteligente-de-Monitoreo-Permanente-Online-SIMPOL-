import streamlit as st
from database import obtener_lista_servidores, conectar_bd

# Mantenemos el caché pero con un scope más controlado
@st.cache_data(ttl=5)
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

# ELIMINAMOS 'run_every' del fragmento para el .EXE
# El refresco automático es el que causa la superposición fantasma
@st.fragment()
def renderizar_lista_alertas(ip_sel, nombre_alias):
    # Contenedor local para asegurar limpieza en cada llamada del fragmento
    espacio_alertas = st.container()
    
    with espacio_alertas:
        alertas = obtener_alertas_por_ip(ip_sel)
        
        criticas = [a for a in alertas if a['estado_sistema'] == 'CRÍTICO']
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Alertas Críticas (Recientes)", len(criticas), delta_color="inverse")
        with col2:
            st.metric("Total Incidentes Detectados", len(alertas))

        st.divider()
        st.subheader(f"Historial de eventos: {nombre_alias}")
        
        if not alertas:
            st.success(f"✅ El servidor {nombre_alias} no presenta incidencias.")
        else:
            # Agregamos una key única al loop para que el .exe identifique cada alerta
            for i, alerta in enumerate(alertas):
                fecha = alerta['fecha_registro'].strftime('%H:%M:%S | %d-%m')
                estado = alerta['estado_sistema']
                detalle = (f"**CPU:** {alerta['val_cpu']}% | **RAM:** {alerta['val_ram']}% | "
                           f"**LAT:** {alerta['val_latencia']}ms")
                
                if estado == "CRÍTICO":
                    st.error(f"🔴 **CRÍTICO** | {fecha} \n\n {detalle}", icon="🔥")
                elif estado == "PRECAUCIÓN":
                    st.warning(f"🟠 **PRECAUCIÓN** | {fecha} \n\n {detalle}", icon="⚠️")

def mostrar_pantalla(usuario_id=None):
    # === ANCLA DE LIMPIEZA TOTAL (Crucial para el .exe) ===
    # Si esta página se cierra, este 'empty' se destruye y con él todo el rastro
    canvas_alertas = st.empty()
    
    with canvas_alertas.container():
        st.title("🔔 Centro de Alertas y Notificaciones")
        
        servidores = obtener_lista_servidores()
        if not servidores:
            st.warning("⚠️ No hay servidores registrados en el catálogo.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        # Key única para el widget de selección
        seleccion = st.selectbox("Filtrar alertas por servidor:", list(opciones.keys()), key="alertas_filter_select")
        
        serv_info = opciones[seleccion]
        
        # Botón de refresco manual (Más seguro que el automático en .exe para evitar fantasmas)
        if st.button("🔄 Actualizar Alertas Ahora", key="btn_refresco_alertas"):
            st.cache_data.clear()
            st.rerun()
            
        renderizar_lista_alertas(serv_info['ip'], serv_info['nombre_alias'])