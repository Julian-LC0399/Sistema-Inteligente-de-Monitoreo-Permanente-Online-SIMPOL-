import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

def mostrar_pantalla(nombre_analista, usuario_id):
    st.title("📈 Capacity Planning - Banco Caroní")
    
    # Barra de identificación (Consistencia con Monitoreo)
    st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 5px solid #e67e22; margin-bottom: 20px;">
            <span style="color: #e67e22; font-weight: bold;">👤 Analista Responsable:</span> {nombre_analista}
        </div>
    """, unsafe_allow_html=True)

    # 1. Selector Dinámico de Servidor
    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("⚠️ No hay servidores activos para realizar proyecciones.")
        return

    opciones = {f"{s['nombre_alias']} ({s['ip']})": s['ip'] for s in servidores}
    seleccion = st.selectbox("Seleccione Servidor para Análisis de Capacidad:", list(opciones.keys()))
    ip_sel = opciones[seleccion]

    # 2. Configuración del Análisis (Expandido a 5 métricas)
    col1, col2 = st.columns(2)
    with col1:
        # Añadimos DISCO, RED y PING a la proyección
        metrica_label = st.selectbox("Métrica a Proyectar:", ["CPU", "RAM", "DISCO", "RED", "PING"])
        # Mapeo interno a las columnas de la DB
        mapa_metrica = {
            "CPU": "val_cpu", "RAM": "val_ram", "DISCO": "val_disco", 
            "RED": "val_red", "PING": "val_latencia"
        }
        columna_db = mapa_metrica[metrica_label]
        
    with col2:
        dias_proy = st.slider("Días a proyectar:", 7, 90, 30)
    
    # 3. Obtener Datos Reales
    datos = obtener_datos_historicos(ip_sel)
    
    if len(datos) < 5:
        st.error(f"❌ Datos insuficientes para {seleccion}. Se requieren al menos 5 registros históricos.")
        return

    # Extraer valores usando las nuevas columnas val_xxx
    valores = [d[columna_db] for d in datos]
    valor_actual = sum(valores[:5]) / 5  # Promedio reciente para evitar picos falsos
    
    # Lógica de Proyección (Simulando crecimiento según la métrica)
    # El Disco suele crecer más lento pero constante, el CPU es más volátil
    factor_crecimiento = 1.08 if metrica_label == "DISCO" else 1.05
    valor_proyectado = valor_actual * factor_crecimiento
    
    # Limitar a 100 si es porcentaje, dejar libre si es Mbps o ms
    if metrica_label in ["CPU", "RAM", "DISCO"]:
        valor_proyectado = min(100.0, valor_proyectado)
    
    # 4. Visualización Gráfica
    st.subheader(f"Tendencia Proyectada: {metrica_label}")
    
    h_base = 150
    # Normalización simple para el gráfico SVG
    y_actual = h_base - (min(valor_actual, 100) * 1.2)
    y_proy = h_base - (min(valor_proyectado, 100) * 1.2)
    
    puntos = f"0,{h_base} 0,{y_actual} 150,{y_actual} 300,{y_proy} 300,{h_base}"
    
    st.markdown(f"""
    <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
        <svg width="100%" height="180" viewBox="0 0 300 180">
            <line x1="0" y1="{h_base}" x2="300" y2="{h_base}" stroke="#ccc" stroke-width="2" />
            <polyline points="{puntos}" fill="rgba(230, 126, 34, 0.2)" stroke="#e67e22" stroke-width="3" />
            <circle cx="0" cy="{y_actual}" r="4" fill="#2c3e50" />
            <circle cx="300" cy="{y_proy}" r="4" fill="#e67e22" />
            <text x="5" y="{y_actual - 10}" font-size="12" fill="#2c3e50">Hoy: {valor_actual:.1f}</text>
            <text x="200" y="{y_proy - 10}" font-size="12" fill="#e67e22" font-weight="bold">Prox: {valor_proyectado:.1f}</text>
            <text x="0" y="170" font-size="10" fill="#999">Estado Actual</text>
            <text x="240" y="170" font-size="10" fill="#999">+{dias_proy} días</text>
        </svg>
    </div>
    """, unsafe_allow_html=True)

    # 5. Veredicto Técnico
    st.divider()
    # Umbrales diferenciados
    umbral = 85 if metrica_label == "DISCO" else 80
    veredicto = "SUFICIENTE" if valor_proyectado < umbral else "CRÍTICO"
    
    if veredicto == "CRÍTICO":
        st.error(f"🚩 ALERTA DE CAPACIDAD: Se proyecta agotamiento de {metrica_label} en el periodo de {dias_proy} días.")
        st.info("💡 Sugerencia: Planificar ampliación de recursos o depuración de logs.")
    else:
        st.success(f"✅ Análisis de Capacidad: El recurso {metrica_label} se mantendrá estable.")

    # 6. Guardado en Base de Datos
    if st.button(f"💾 Registrar Análisis en Auditoría"):
        exito = registrar_proyeccion(
            usuario_id=usuario_id,
            ip_servidor=ip_sel,
            metrica=metrica_label,
            actual=valor_actual,
            proyectado=valor_proyectado,
            veredicto=veredicto
        )
        if exito:
            st.balloons()
            st.success("Informe de Capacity Planning guardado exitosamente.")
        else:
            st.error("Error al guardar el informe técnico.")