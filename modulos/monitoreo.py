import streamlit as st
from datetime import datetime
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla(user_actual):
    # --- 1. CAMBIO NATIVO: Eliminamos st_autorefresh ---
    # En su lugar, usamos un botón de actualización manual para el servidor
    col_t, col_refresh = st.columns([4, 1])
    with col_t:
        st.markdown(
            "<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: CSU</h2>",
            unsafe_allow_html=True,
        )
    with col_refresh:
        if st.button("🔄 ACTUALIZAR", use_container_width=True):
            st.rerun()

    # 2. Captura de datos instantáneos (Nativo, no usa Pandas)
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%H:%M:%S")

    # Panel de indicadores superiores (Métricas nativas de Streamlit)
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(
            f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">CAPTURA EN VIVO</div>
                <h3 style="margin:0; color:#003366;">Infraestructura de Red - Banco Caroní</h3>
                <p style="margin:0; color:#666; font-size:13px;">Última lectura: {fecha_actual} | Origen: {fuente_msg}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with col_status:
        c1, c2 = st.columns(2)
        # st.metric es nativo y muy eficiente
        c1.metric("CPU", f"{cpu_val}%")
        c2.metric("RAM", f"{ram_val}%")

    st.divider()

    # 3. Visualización de Tendencia (100% Nativa - Sin Pandas ni Plotly)
    try:
        conn = conectar_bd()
        if conn:
            # EXTRACCIÓN NATIVA: Usamos el cursor de MySQL directamente
            cursor = conn.cursor(dictionary=True)
            query = "SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo ORDER BY id DESC LIMIT 20"
            cursor.execute(query)
            datos_raw = cursor.fetchall() # Lista de diccionarios
            cursor.close()
            conn.close()

            if datos_raw:
                st.markdown("### 📊 Tendencia de Carga Reciente")
                
                # --- GRÁFICO NATIVO DE STREAMLIT ---
                # Preparamos los datos usando 'Comprensión de Listas' de Python puro
                # Esto es ultra rápido y no requiere Numpy ni Pandas
                chart_data = {
                    "Carga CPU %": [d['uso_cpu'] for d in reversed(datos_raw)],
                    "Uso RAM %": [d['uso_ram'] for d in reversed(datos_raw)]
                }
                
                # st.line_chart es una función interna de Streamlit que dibuja gráficos limpios
                st.line_chart(chart_data, height=300)
                
                # Tabla de datos para auditoría visual opcional
                with st.expander("Ver tabla de datos detallada"):
                    st.table(datos_raw)

            else:
                st.info("💡 No se encontraron registros. Verifique el agente.")

    except Exception as e:
        st.error(f"⚠️ Error de telemetría: {e}")

    # 4. Panel de sugerencias (Nativo)
    with st.expander("Ver recomendaciones de optimización", expanded=True):
        if cpu_val > 80:
            st.warning("Se detecta una carga alta de CPU. Revise procesos de PRTG.")
        elif ram_val > 85:
            st.warning("Uso de RAM elevado. Considere revisar la caché del servidor.")
        else:
            st.success("El rendimiento se mantiene dentro de los parámetros estables.")