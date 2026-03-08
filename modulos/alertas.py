import streamlit as st
import pandas as pd
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    # 1. Telemetría actual
    cpu_act, ram_act, fuente = obtener_telemetria()
    
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        u_cpu = st.number_input("Umbral Crítico CPU (%)", 1, 100, 85)
    with col_conf2:
        u_ram = st.number_input("Umbral Crítico RAM (%)", 1, 100, 90)

    st.divider()

    # 2. SECCIÓN DE DIAGNÓSTICO (Solo para ver por qué no carga)
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Primero: ¿Hay algo en la tabla?
        cursor.execute("SELECT COUNT(*) FROM monitoreo_30_nodos")
        total_registros = cursor.fetchone()[0]
        
        # Segundo: ¿Cómo se llaman los nodos guardados?
        cursor.execute("SELECT DISTINCT nodo_nombre FROM monitoreo_30_nodos")
        nodos_existentes = [fila[0] for fila in cursor.fetchall()]
        
        conn.close()

        # Mostramos diagnóstico en un cuadro pequeño
        with st.expander("🔍 Diagnóstico de Base de Datos"):
            st.write(f"Total registros en tabla: **{total_registros}**")
            st.write(f"Nodos encontrados en DB: {nodos_existentes}")
            st.write(f"Buscando por: **'Nodo CSU'**")

    except Exception as e:
        st.error(f"No se pudo conectar a la DB: {e}")

    # 3. CARGA DE TABLA REFORMULADA
    st.subheader("📋 Historial de Nodos")
    
    try:
        conn = conectar_bd()
        # Quitamos el WHERE temporalmente para ver si trae ALGO
        query = """
            SELECT fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado 
            FROM monitoreo_30_nodos 
            ORDER BY fecha_registro DESC 
            LIMIT 20
        """
        df_historial = pd.read_sql(query, conn)
        conn.close()

        if not df_historial.empty:
            # Si el dataframe tiene datos, lo mostramos
            st.dataframe(df_historial, use_container_width=True)
        else:
            st.warning("La consulta SQL se ejecutó pero la tabla está vacía. Verifica que tu Agente de Captura esté insertando datos.")
            
    except Exception as e:
        st.error(f"Error al procesar la tabla: {e}")