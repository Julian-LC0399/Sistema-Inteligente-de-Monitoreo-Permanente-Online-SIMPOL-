import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria
from streamlit_autorefresh import st_autorefresh

def mostrar_pantalla():
    # Refresco automático cada 10 segundos para monitoreo en tiempo real
    st_autorefresh(interval=10000, key="alertas_sync_pro")
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    # --- LECTURA ACTUAL ---
    try:
        cpu_act, ram_act, fuente = obtener_telemetria()
        if cpu_act is not None:
            st.markdown(f'''
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 8px; border-left: 5px solid #003366; margin-bottom: 20px;">
                    <span style="color: #555;">Lectura actual desde <b>{fuente}</b>:</span><br>
                    <span style="font-size: 18px;">💻 CPU: <b>{cpu_act}%</b> | 💾 RAM: <b>{ram_act}%</b></span>
                </div>
            ''', unsafe_allow_html=True)
    except: 
        pass

    # --- CONFIGURACIÓN DE UMBRALES ---
    st.markdown("### ⚙️ Ajuste de Umbrales Críticos")
    col1, col2 = st.columns(2)
    u_cpu = col1.number_input("Umbral Crítico CPU (%)", 1, 100, st.session_state.u_cpu_perc)
    u_ram = col2.number_input("Umbral Crítico RAM (%)", 1, 100, st.session_state.u_ram_perc)
    
    # Actualizar estado de sesión
    st.session_state.u_cpu_perc, st.session_state.u_ram_perc = u_cpu, u_ram

    st.markdown("---")
    st.subheader("📋 Monitor de Eventos Recientes")
    
    try:
        conn = conectar_bd()
        if conn:
            # Consulta a la tabla correcta: monitoreo_nodos
            query = """
                SELECT fecha_registro as 'Fecha', 
                       nodo_nombre as 'Nodo', 
                       uso_cpu as 'CPU %', 
                       uso_ram as 'RAM %' 
                FROM monitoreo_nodos 
                ORDER BY fecha_registro DESC 
                LIMIT 20
            """
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                # --- LÓGICA DE ALERTA CON EMOJIS (Sustituye a StatusColumn) ---
                df['ESTADO'] = df.apply(
                    lambda r: "🔴 CRÍTICO" if r['CPU %'] >= u_cpu or r['RAM %'] >= u_ram else "🟢 NORMAL", 
                    axis=1
                )

                # --- RENDERIZADO DE TABLA CORREGIDO ---
                st.dataframe(
                    df,
                    column_config={
                        "Fecha": st.column_config.DatetimeColumn("Fecha/Hora", format="D MMM, h:mm a"),
                        "CPU %": st.column_config.ProgressColumn("Uso CPU", min_value=0, max_value=100, format="%d%%"),
                        "RAM %": st.column_config.ProgressColumn("Uso RAM", min_value=0, max_value=100, format="%d%%"),
                        "ESTADO": st.column_config.TextColumn("Estatus del Sistema") # Cambiado de StatusColumn a TextColumn
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Resumen rápido debajo de la tabla
                alertas_activas = len(df[df['ESTADO'] == "🔴 CRÍTICO"])
                if alertas_activas > 0:
                    st.error(f"⚠️ Se detectaron {alertas_activas} eventos críticos en las últimas 20 lecturas.")
                else:
                    st.success("✅ Todos los nodos operan bajo los umbrales normales.")
            else:
                st.info("No hay registros recientes para mostrar.")
        else:
            st.error("Error de conexión: Revisa database.py")

    except Exception as e:
        st.error(f"Error al cargar el monitor de alertas: {e}")

if __name__ == "__main__":
    mostrar_pantalla()