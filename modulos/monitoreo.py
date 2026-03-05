import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from database import conectar_bd
from utils import obtener_telemetria

def mostrar_pantalla(user_actual):
    st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos y telemetría
    cpu_val, ram_val, fuente_msg = obtener_telemetria()
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Header de información (Barra de progreso eliminada)
    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #d3d3d3; padding:20px; border-left:5px solid #003366;">
                <div style="background-color:#003366; color:white; padding:2px 8px; font-size:10px; font-weight:bold; display:inline-block; margin-bottom:10px;">DISPOSITIVO ACTIVO</div>
                <h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Nodo CSU</h3>
                <p style="margin:0; color:#666; font-size:13px;"><b>Origen:</b> {fuente_msg} | <b>ID Sensor:</b> 2094<br><b>Última Lectura:</b> {fecha_actual}</p>
            </div>
        """, unsafe_allow_html=True)

    st.write("---")
    
    # Métricas principales (CPU, RAM, Estado)
    m1, m2, m3 = st.columns(3)
    m1.metric("USO DE CPU", f"{cpu_val}%", delta=fuente_msg)
    m2.metric("MEMORIA RAM", f"{ram_val}%")
    m3.metric("ESTADO LÓGICO", "OPERATIVO")

    # 2. Lógica de Almacenamiento y Graficación
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Insertamos el pulso actual en la base de datos
        cursor.execute("""
            INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) 
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), user_actual, cpu_val, ram_val, "ESTABLE"))
        conn.commit()
        
        # Consultamos el historial para la gráfica
        df_m = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
        conn.close()

        if not df_m.empty:
            df_m = df_m.sort_values("fecha_registro") # Ordenar para que la línea fluya de izquierda a derecha
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_m["fecha_registro"], 
                y=df_m["uso_cpu"], 
                mode='lines+markers',
                name='Carga CPU %',
                line=dict(color='#003366', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 51, 102, 0.1)'
            ))

            fig.update_layout(
                title="Historial Dinámico de Carga (%)",
                xaxis_title="Registro de Tiempo",
                yaxis_title="Uso de Recursos",
                yaxis=dict(range=[0, 100]), # Escala fija para evitar saltos
                plot_bgcolor="white",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=40, b=10),
                height=350
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Sincronizando con la base de datos...")

    except Exception as e:
        st.error(f"Error de conexión con telemetría: {e}")
    
    # 3. Ciclo de refresco (Ajustado a 5 segundos para balancear carga)
    time.sleep(5)
    st.rerun()