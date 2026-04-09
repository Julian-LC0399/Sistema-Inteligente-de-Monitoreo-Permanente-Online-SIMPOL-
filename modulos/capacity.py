import streamlit as st
from database import obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

def mostrar_pantalla():
    # --- 1. ESTILOS INSTITUCIONALES (NATIVOS Y SIN PANDAS) ---
    st.markdown("""
        <style>
            h2, h3 { color: #003366 !important; font-weight: bold; }
            
            /* Estilo de la Tabla (Réplica de alertas.py) */
            [data-testid="stTable"] td { 
                color: black !important; 
                border: 1px solid #eee !important; 
                font-weight: 500; 
                text-align: center;
            }
            [data-testid="stTable"] th { 
                background-color: #003366 !important; 
                color: white !important; 
                text-align: center;
            }
            
            /* OCULTAR LA COLUMNA DE ÍNDICE (0, 1, 2...) */
            [data-testid="stTable"] td:nth-child(1), 
            [data-testid="stTable"] th:nth-child(1) { 
                display: none !important; 
            }
            
            /* Botón del Banco */
            .stButton>button { 
                background-color: #003366; 
                color: white; 
                border-radius: 5px; 
                font-weight: bold; 
                width: 100%;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2>📈 Planificación de Capacidad (Capacity Planning)</h2>", unsafe_allow_html=True)
    
    # 2. OBTENCIÓN DE DATOS (Lista de diccionarios nativa)
    datos_raw = obtener_datos_historicos()

    if not datos_raw or len(datos_raw) < 5:
        st.warning("⚠️ Se requieren registros históricos para procesar la tendencia.")
        return

    # CONFIGURACIÓN DEL ANÁLISIS
    with st.container(border=True):
        col1, col2 = st.columns(2)
        dias_proyectar = col1.slider("Días a proyectar:", 1, 30, 7)
        metrica = col2.selectbox("Recurso a analizar:", ["uso_cpu", "uso_ram"], 
                                format_func=lambda x: "PROCESADOR (CPU)" if "cpu" in x else "MEMORIA (RAM)")

    # 3. LÓGICA DE PROYECCIÓN (CÁLCULOS NATIVOS)
    try:
        # Extraemos valores usando listas nativas
        valores = [float(d.get(metrica, 0)) for d in datos_raw]
        n = len(valores)
        
        # Tendencia Lineal Simple
        tendencia_unitaria = (valores[-1] - valores[0]) / (n - 1) if n > 1 else 0
        
        # 5 segundos = 17,280 registros/día
        puntos_por_dia = 17280 
        incremento_total = tendencia_unitaria * dias_proyectar * puntos_por_dia
        valor_futuro = max(0, min(100, valores[-1] + incremento_total))

        # Gráfico nativo de Streamlit
        st.subheader(f"Tendencia de Consumo: {metrica.replace('_', ' ').upper()}")
        st.line_chart(valores, height=250)

        # Resultados
        fecha_meta_dt = datetime.now() + timedelta(days=dias_proyectar)
        fecha_meta_str = fecha_meta_dt.strftime('%d/%m/%Y')
        umbral_critico = st.session_state.get("CPU_CRITICO" if "cpu" in metrica else "RAM_CRITICO", 90)
        
        with st.container(border=True):
            if valor_futuro >= umbral_critico:
                veredicto = "ALERTA"
                st.error(f"🚨 **{veredicto}:** Proyección de **{valor_futuro:.1f}%** para el {fecha_meta_str}.")
            else:
                veredicto = "ESTABLE"
                st.success(f"✅ **{veredicto}:** Proyección de **{valor_futuro:.1f}%** para el {fecha_meta_str}.")

            if st.button("💾 Guardar Proyección en Auditoría"):
                exito = registrar_proyeccion(
                    metrica.upper(), valores[-1], valor_futuro, 
                    fecha_meta_dt.date(), dias_proyectar, veredicto, 
                    st.session_state.get('usuario', 'Analista-CSU')
                )
                if exito: st.toast("Análisis guardado exitosamente.")

    except Exception as e:
        st.error(f"Error en el cálculo: {e}")

    # --- 4. TABLA DE AUDITORÍA (NATIVA SIN ÍNDICE) ---
    st.divider()
    st.markdown("### 📋 Auditoría de Registros Analizados")
    
    try:
        tabla_final = []
        # Tomamos los últimos 10 registros
        for d in datos_raw[-10:]:
            f_cruda = d.get('fecha_registro')
            # Formateo manual para evitar milisegundos
            f_limpia = f_cruda.strftime('%Y-%m-%d %H:%M:%S') if isinstance(f_cruda, datetime) else str(f_cruda).split('.')[0]
            
            fila = {
                "FECHA Y HORA": f_limpia,
                "USO CPU": f"{d.get('uso_cpu', 0)}%",
                "USO RAM": f"{d.get('uso_ram', 0)}%",
                "ESTADO": "ACTIVO" 
            }
            tabla_final.append(fila)
        
        # st.table() con el CSS de arriba oculta automáticamente la columna 0, 1, 2...
        st.table(tabla_final)
        
    except Exception as e:
        st.error(f"Error al renderizar tabla institucional: {e}")