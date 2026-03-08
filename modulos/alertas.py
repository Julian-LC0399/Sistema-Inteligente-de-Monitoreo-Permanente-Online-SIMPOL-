import streamlit as st
import pandas as pd
from utils import obtener_telemetria # Usamos tu función existente

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>🚨 Panel de Alertas y Notificaciones</h2>", unsafe_allow_html=True)
    
    # 1. Obtener datos actuales sin tocar la BD directamente aquí
    cpu_act, ram_act, fuente = obtener_telemetria()
    
    # 2. Configuración de Umbrales (esto es lo que el analista regula)
    st.markdown('<p style="color:#666;">Configure los límites críticos para el Nodo CSU</p>', unsafe_allow_html=True)
    
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        u_cpu = st.number_input("Umbral Crítico CPU (%)", 1, 100, 85)
    with col_conf2:
        u_ram = st.number_input("Umbral Crítico RAM (%)", 1, 100, 90)

    # 3. Lógica de Alerta Inmediata
    st.divider()
    if cpu_act > u_cpu:
        st.error(f"### ⚠️ ALERTA DE RENDIMIENTO\n**El CPU está al {cpu_act}%**. Supera el límite de {u_cpu}% establecido.")
        st.button("📩 Notificar a Infraestructura")
    elif ram_act > u_ram:
        st.warning(f"### ⚠️ AVISO DE MEMORIA\n**La RAM está al {ram_act}%**. Supera el límite de {u_ram}%.")
    else:
        st.success(f"✅ **Sistemas Normales**: CPU {cpu_act}% | RAM {ram_act}% | Fuente: {fuente}")

    # 4. Tabla de historial (Simulada para la entrega)
    st.subheader("Historial de Alertas (Últimas 24h)")
    eventos = {
        "Hora": ["08:30:12", "14:22:05"],
        "Componente": ["CPU", "CONEXIÓN"],
        "Mensaje": ["Exceso de carga en procesos Batch", "Pérdida de enlace con sensor PRTG"],
        "Nivel": ["CRÍTICO", "ADVERTENCIA"]
    }
    st.table(pd.DataFrame(eventos))