import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos
import time

def mostrar_pantalla(nombre_analista="Analista"):
    # Limpieza total forzada al entrar al módulo
    st.empty()
    
    # Encabezado fuera del bloque dinámico para que actúe como ancla visual fija
    st.markdown('<h2 style="color:#003366;">🛰️ Monitoreo de Infraestructura - Banco Caroní</h2>', unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. OBTENER CATÁLOGO DE SERVIDORES
    servidores = obtener_lista_servidores()
    
    if not servidores:
        st.warning("⚠️ No se encontraron servidores en el catálogo. Verifique la tabla 'servidores'.")
        return

    # 2. SELECTOR DE SERVIDOR
    opciones_servidores = {f"{s['nombre_alias']} ({s['ip']})": s['ip'] for s in servidores}
    
    # Key única y específica para evitar colisiones en la sesión global
    seleccion = st.selectbox(
        "Seleccione el servidor a inspeccionar:", 
        list(opciones_servidores.keys()), 
        key="monitoreo_server_select_final"
    )
    ip_seleccionada = opciones_servidores[seleccion]

    # Contenedor dinámico aislado exclusivamente para las métricas variables
    zona_dinamica = st.empty()
    
    with zona_dinamica.container():
        # 3. OBTENER DATOS ESPECÍFICOS
        datos = obtener_datos_historicos(ip_seleccionada)

        if not datos:
            st.info(f"⏳ Esperando transmisiones de telemetría del agente para el nodo {ip_seleccionada}...")
            # En vez de un st.rerun() agresivo inmediato, dejamos un botón de auxilio técnico
            if st.button("Forzar reconexión con el agente", key="btn_reconect_agente"):
                st.rerun()
            return

        reciente = datos[0]

        # 4. DISPOSICIÓN DE MÉTRICAS EN PANTALLA
        col1, col2, col3 = st.columns(3)
        col1.metric(label="🌡️ Carga de CPU", value=f"{reciente['val_cpu']}%")
        col2.metric(label="🧠 Uso de Memoria RAM", value=f"{reciente['val_ram']}%")
        col3.metric(label="💾 Espacio de Disco", value=f"{reciente['val_disco']}%")

        col4, col5 = st.columns(2)
        col4.metric(label="🌐 Rendimiento Red", value=f"{reciente['val_red']} Mb/s")
        col5.metric(label="⏳ Latencia de Enlace", value=f"{reciente['val_latencia']} ms")

        # 5. SEMÁFORO DE ESTADO CRÍTICO
        st.markdown("---")
        estado_actual = reciente['estado_sistema']
        st.write(f"### Estado General del Servidor: **{estado_actual}**")
        
        if estado_actual == "CRÍTICO":
            st.error(f"⚠️ ALERTA: El servidor {seleccion} presenta saturación en uno o más sensores.")
        elif estado_actual == "PRECAUCIÓN":
            st.warning(f"🔔 AVISO: Se recomienda revisar la carga en {seleccion}.")
        else:
            st.success(f"✅ El servidor {seleccion} opera con normalidad.")

        # 6. MOTOR DE ACTUALIZACIÓN CONTROLADA (Previene persistencia de otros módulos)
        st.caption("🔄 Actualización en tiempo real activa (Sincronizado con el Agente WMI)")
        
        # Pausa controlada. Si el usuario cambió de módulo en estos 3 segundos,
        # la sesión registrará el cambio de menú en app.py y no arrastrará componentes.
        time.sleep(3)
        st.rerun()

if __name__ == "__main__":
    mostrar_pantalla()