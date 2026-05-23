import streamlit as st
from database import obtener_lista_servidores, obtener_datos_historicos, registrar_proyeccion
from datetime import datetime, timedelta

def mostrar_pantalla(nombre_analista, usuario_id):
    # === ANCLA DE LIMPIEZA ATÓMICA ===
    capas_planning = st.empty()
    
    with capas_planning.container():
        # ==========================================================================
        # ENCABEZADO CON LA SINTAXIS HOMOLOGADA EN AZUL CORPORATIVO
        # ==========================================================================
        st.markdown('<h2 style="color:#003366;">📈 Capacity Planning - Banco Caroní</h2>', unsafe_allow_html=True)
        
        # Identificación del analista limpia y sin bloques de color invasivos
        st.markdown(f"👤 **Analista Responsable:** {nombre_analista}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 1. Selector Dinámico de Servidor
        servidores = obtener_lista_servidores()
        if not servidores:
            st.warning("⚠️ No hay servidores activos para realizar proyecciones.")
            return

        opciones = {f"{s['nombre_alias']} ({s['ip']})": s for s in servidores}
        seleccion = st.selectbox("Seleccione Servidor para Análisis de Capacidad:", list(opciones.keys()), key="cap_serv_sel")
        serv_info = opciones[seleccion]
        ip_sel = serv_info['ip']

        # 2. Configuración del Análisis (Adaptado a Multi-Volumen de Almacenamiento)
        col1, col2 = st.columns(2)
        with col1:
            metrica_label = st.selectbox(
                "Métrica a Proyectar:", 
                ["CPU", "RAM", "DISCO 1 (C:\\)", "DISCO 2 (F:\\)", "DISCO 3 (E:\\)", "DISCO 4 (D:\\)", "DISCO 5 (G:\\)", "RED", "PING"], 
                key="cap_metrica_sel"
            )
            
            # Mapeo exacto hacia las columnas indexadas de la Base de Datos
            mapa_metrica = {
                "CPU": "val_cpu", "RAM": "val_ram", 
                "DISCO 1 (C:\\)": "val_disco_1", "DISCO 2 (F:\\)": "val_disco_2", 
                "DISCO 3 (E:\\)": "val_disco_3", "DISCO 4 (D:\\)": "val_disco_4", 
                "DISCO 5 (G:\\)": "val_disco_5",
                "RED": "val_red", "PING": "val_latencia"
            }
            columna_db = mapa_metrica[metrica_label]
            
        with col2:
            dias_proy = st.slider("Días a proyectar:", 7, 90, 30, key="cap_slider_dias")
        
        # --- VALIDACIÓN DE SENSOR ACTIVO EN CATÁLOGO ---
        # Si seleccionan un disco, verificamos en el catálogo si el id_sensor_disco_X es mayor a 0
        if "DISCO" in metrica_label:
            num_disco = int(metrica_label.split(" ")[1])
            if serv_info.get(f'id_sensor_disco_{num_disco}', 0) == 0:
                st.error(f"❌ El volumen seleccionado ({metrica_label}) no se encuentra indexado ni activo en este servidor.")
                return

        # 3. Obtener Datos Reales
        datos = obtener_datos_historicos(ip_sel)
        
        if len(datos) < 5:
            st.error(f"❌ Datos insuficientes para {seleccion}. Se requieren al menos 5 registros históricos en la tabla de telemetría.")
            return

        # 4. ALGORITMO MATEMÁTICO DE CAPACITY PLANNING (Verificación de Lógica Vital)
        valores = [d[columna_db] for d in datos]
        valor_actual = sum(valores[:5]) / 5  # Promedio móvil de las últimas 5 muestras basales
        
        # El factor varía según la naturaleza de la métrica (Discos y RAM son críticos por agotamiento)
        if "DISCO" in metrica_label:
            # LÓGICA INVERSA: El valor en la BD es % LIBRE. El crecimiento reduce la disponibilidad.
            factor_reduccion = 0.92  # Simula una pérdida del 8% de espacio libre en el periodo
            valor_proyectado = valor_actual * factor_reduccion
            valor_proyectado = max(0.0, valor_proyectado) # El espacio libre no puede ser menor a cero
        elif metrica_label == "RAM":
            # LÓGICA INVERSA: La RAM en la BD es % LIBRE. 
            factor_reduccion = 0.95  # Simula una pérdida del 5% de RAM disponible
            valor_proyectado = max(0.0, valor_actual * factor_reduccion)
        else:
            # LÓGICA DIRECTA: CPU, RED y PING incrementan su valor (uso/saturación)
            factor_crecimiento = 1.05
            valor_proyectado = valor_actual * factor_crecimiento
            if metrica_label == "CPU":
                valor_proyectado = min(100.0, valor_proyectado)

        # 5. Visualización Gráfica (Protegida vía SVG Nativo)
        st.markdown(f'<h4 style="color:#003366; margin-top:20px;">Tendencia Proyectada: {metrica_label}</h4>', unsafe_allow_html=True)
        
        h_base = 150
        # Mapeo visual del SVG adaptado al tipo de lógica
        y_actual = h_base - (min(valor_actual, 100) * 1.2)
        y_proy = h_base - (min(valor_proyectado, 100) * 1.2)
        puntos = f"0,{h_base} 0,{y_actual} 150,{y_actual} 300,{y_proy} 300,{h_base}"
        
        # Construcción de leyendas dinámicas de unidad
        simbolo_unidad = "% Disp." if ("DISCO" in metrica_label or metrica_label == "RAM") else ("%" if metrica_label == "CPU" else ("Mb/s" if metrica_label == "RED" else "ms"))

        st.markdown(f"""
        <div id="contenedor-grafico" style="background: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <svg id="grafico-svg" width="100%" height="180" viewBox="0 0 300 180">
                <line x1="0" y1="{h_base}" x2="300" y2="{h_base}" stroke="#ccc" stroke-width="2" />
                <polyline points="{puntos}" fill="rgba(0, 51, 102, 0.15)" stroke="#003366" stroke-width="3" />
                <circle cx="0" cy="{y_actual}" r="4" fill="#2c3e50" />
                <circle cx="300" cy="{y_proy}" r="4" fill="#003366" />
                <text x="5" y="{y_actual - 10}" font-size="12" fill="#2c3e50">Hoy: {valor_actual:.1f} {simbolo_unidad}</text>
                <text x="180" y="{y_proy - 10}" font-size="12" fill="#003366" font-weight="bold">Prox: {valor_proyectado:.1f} {simbolo_unidad}</text>
                <text x="0" y="170" font-size="10" fill="#999">Estado Actual</text>
                <text x="240" y="170" font-size="10" fill="#999">+{dias_proy} días</text>
            </svg>
        </div>
        """, unsafe_allow_html=True)

        # 6. Veredicto Técnico bajo Cumplimiento Institucional
        st.divider()
        
        # Aplicación estricta de las reglas del semáforo bancario de tres estados
        if "DISCO" in metrica_label:
            # Alerta si el espacio libre proyectado cae por debajo del 10% crítico
            veredicto = "CRÍTICO" if valor_proyectado <= 10.0 else "SUFICIENTE"
        elif metrica_label == "RAM":
            # Alerta si la RAM libre proyectada cae por debajo del 10% crítico
            veredicto = "CRÍTICO" if valor_proyectado <= 10.0 else "SUFICIENTE"
        elif metrica_label == "CPU":
            veredicto = "CRÍTICO" if valor_proyectado >= 85.0 else "SUFICIENTE"
        else:
            veredicto = "SUFICIENTE"
        
        if veredicto == "CRÍTICO":
            st.error(f"🚩 ALERTA DE CAPACITY PLANNING: Se proyecta el colapso o agotamiento de {metrica_label} en la ventana de {dias_proy} días.")
            st.info("💡 Acción Recomendada por Auditoría: Tramitar ticket de infraestructura para expansión física de recursos o depuración inmediata.")
        else:
            st.success(f"✅ Previsión de Capacidad: El recurso {metrica_label} posee suficiente tolerancia operativa para los próximos {dias_proy} días.")

        # 7. Persistencia Segura del Informe Técnico
        if st.button(f"💾 Registrar Análisis en Auditoría", key="btn_auditoria"):
            exito = registrar_proyeccion(
                usuario_id=usuario_id,
                ip_servidor=ip_sel,
                metrica=metrica_label, # Guarda la etiqueta explícita (ej: "DISCO 1 (C:\)")
                actual=float(valor_actual),
                proyectado=float(valor_proyectado),
                veredicto=veredicto
            )
            if exito:
                st.balloons()
                st.success("Informe técnico de Capacity Planning enviado y firmado en auditoría.")
            else:
                st.error("Error de persistencia: No se pudo registrar el análisis en el histórico.")

if __name__ == "__main__":
    mostrar_pantalla("Analista de Guardia", 1)