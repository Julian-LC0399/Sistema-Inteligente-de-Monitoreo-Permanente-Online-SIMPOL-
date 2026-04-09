import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

def mostrar_pantalla():
    # --- ESTILOS INSTITUCIONALES BANCO CARONÍ ---
    st.markdown("""
        <style>
        .main { background-color: #F5F7F9; }
        h2, h3 {
            color: #003366 !important;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-weight: bold;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #003366;
            border-radius: 8px;
        }
        .stButton>button {
            background-color: #003366;
            color: white;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    
    # 1. Obtención de datos desde la tabla 'monitoreo'
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.warning("⚠️ Se requieren registros históricos en la tabla 'monitoreo' para procesar la tendencia.")
        return

    # 2. Configuración del Análisis
    with st.container(border=True):
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col2.selectbox("Recurso a analizar:", ["uso_cpu", "uso_ram"], 
                                format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    # 3. Lógica Matemática (Frecuencia 5s: 17,280 registros/día)
    try:
        valores = [float(d.get(metrica, 0)) for d in datos_raw]
        n = len(valores)
        # Tendencia lineal: (último - primero) / espacios
        tendencia_unidad = (valores[-1] - valores[0]) / (n - 1) if n > 1 else 0
        
        puntos_dia = 17280 
        incremento = tendencia_unidad * dias_proyectar * puntos_dia
        valor_futuro = max(0, min(100, valores[-1] + incremento))

        # Visualización de la tendencia actual
        st.subheader(f"Análisis de Tendencia: {metrica.replace('_', ' ').upper()}")
        st.line_chart(valores, height=250)

        # Resultados y Veredicto
        fecha_meta_dt = datetime.now() + timedelta(days=dias_proyectar)
        fecha_meta_str = fecha_meta_dt.strftime('%d/%m/%Y')
        
        # Umbrales desde el estado de sesión (configurados en alertas.py)
        umbral_critico = st.session_state.get("CPU_CRITICO" if "cpu" in metrica else "RAM_CRITICO", 90)
        
        with st.container(border=True):
            if valor_futuro >= umbral_critico:
                veredicto = "ALERTA"
                st.error(f"🚨 **{veredicto}:** Proyección de **{valor_futuro:.1f}%** para el {fecha_meta_str}.")
            elif valor_futuro >= 75:
                veredicto = "PRECAUCIÓN"
                st.warning(f"⚠️ **{veredicto}:** Proyección de **{valor_futuro:.1f}%** para el {fecha_meta_str}.")
            else:
                veredicto = "ESTABLE"
                st.success(f"✅ **{veredicto}:** Proyección de **{valor_futuro:.1f}%** para el {fecha_meta_str}.")

            # --- NUEVA FUNCIONALIDAD: GUARDAR EN TABLA 'PROYECCIONES' ---
            if st.button("💾 Registrar Proyección en Auditoría"):
                exito = registrar_proyeccion(
                    recurso=metrica.upper(),
                    actual=valores[-1],
                    proyectado=valor_futuro,
                    fecha_fin=fecha_meta_dt.date(),
                    dias=dias_proyectar,
                    veredicto=veredicto,
                    ejecutor=st.session_state.get('usuario', 'Analista-CSU')
                )
                if exito:
                    st.toast("Proyección guardada correctamente en la base de datos.", icon="✅")
                else:
                    st.error("Error al persistir la proyección.")

    except Exception as e:
        st.error(f"Error en el cálculo: {e}")

    # 4. Auditoría de Datos (Tabla con Fechas corregidas)
    st.markdown("---")
    st.subheader("📋 Historial de Registros Analizados")
    
    try:
        datos_tabla = []
        for d in datos_raw[-15:]:
            # Identificación de la fecha según el esquema de tu base de datos
            fecha_exacta = d.get('fecha_registro') or d.get('fecha') or d.get('FECHA') or "N/D"
            
            fila = {
                "MARCA DE TIEMPO": str(fecha_exacta),
                "CPU %": f"{float(d.get('uso_cpu', 0)):.2f}%",
                "RAM %": f"{float(d.get('uso_ram', 0)):.2f}%",
                "ESTADO": str(d.get('estado', 'ACTIVO')).upper()
            }
            datos_tabla.append(fila)
        
        st.dataframe(datos_tabla, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Error al mostrar auditoría: {e}")