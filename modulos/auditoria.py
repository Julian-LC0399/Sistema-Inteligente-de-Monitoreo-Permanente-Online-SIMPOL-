import streamlit as st
from database import conectar_bd

def mostrar_pantalla():
    # === ANCLA DE LIMPIEZA ATÓMICA ===
    canvas_auditoria = st.empty()
    
    with canvas_auditoria.container():
        st.markdown("<h2 style='color: #003366; font-family: sans-serif;'>🕵️ Control de Accesos</h2>", unsafe_allow_html=True)
        
        try:
            conn = conectar_bd()
            if conn:
                # Se fuerza cursor con diccionario para estabilidad arquitectónica del EXE
                cursor = conn.cursor(dictionary=True)
                
                # 1. Búsqueda con Key Única para el .exe
                busqueda = st.text_input("🔍 Buscar usuario por login:", placeholder="Ej: seguridad_csu", key="input_busqueda_auditoria")
                
                # 2. Conteo total de la tabla de logs institucional
                cursor.execute("SELECT COUNT(*) as total FROM log_accesos")
                total = cursor.fetchone()["total"]
                
                # 3. Consulta con filtro incorporando la nueva columna 'cargo' de la V3.3
                query = "SELECT usuario, cargo, fecha_acceso, resultado FROM log_accesos"
                params = []
                if busqueda:
                    query += " WHERE usuario LIKE %s"
                    params.append(f"%{busqueda}%")
                
                query += " ORDER BY id_log DESC LIMIT 30"
                cursor.execute(query, params)
                logs = cursor.fetchall()
                
                cursor.close()
                conn.close()

                # 4. Banner Estadístico Institucional
                st.markdown(
                    f"""
                    <div style="background-color: #f1f5f9; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #cbd5e1; font-family: sans-serif;">
                        <span style="color: #475569; font-size: 13px; font-weight: bold;">TOTAL DE EVENTOS REGISTRADOS:</span>
                        <span style="color: #003366; font-size: 16px; font-weight: bold; margin-left: 5px;">{total}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

                # 5. Renderizado de línea de tiempo HTML5 (Cero Pandas para estabilidad del EXE)
                if logs:
                    html_acumulado = ""
                    for l in logs:
                        u = l["usuario"]
                        cargo_val = l["cargo"] if l["cargo"] else "Sin Cargo Asignado"
                        f = l["fecha_acceso"].strftime('%d/%m/%Y %H:%M')
                        res = l["resultado"]
                        
                        # Establecemos colores institucionales según criticidad de auditoría
                        if res == "EXITOSO":
                            color_borde = "#28a745"
                        elif res == "SUSPENDIDO":
                            color_borde = "#ff9800"
                        else:
                            color_borde = "#d32f2f"
                        
                        html_acumulado += f"""
                        <div style="border-left: 5px solid {color_borde}; background-color: white; padding: 12px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #eee; border-left-width: 5px; font-family: sans-serif;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color:#003366; font-weight:bold; font-size: 15px;">{u}</span>
                                <span style="color:{color_borde}; font-weight:bold; font-size: 11px; background:{color_borde}15; padding: 2px 8px; border-radius:10px;">{res}</span>
                            </div>
                            <div style="color:#666; font-size: 12px; margin-top: 6px; display: flex; flex-wrap: wrap; gap: 15px;">
                                <span>💼 <b>Cargo:</b> {cargo_val}</span>
                                <span>📅 <b>Fecha:</b> {f}</span>
                            </div>
                        </div>
                        """
                    st.markdown(html_acumulado, unsafe_allow_html=True)
                else:
                    st.info("No se registran eventos de autenticación bajo el criterio suministrado.")
            else:
                st.error("No se pudo establecer conexión con el repositorio de logs.")
        except Exception as e:
            st.error(f"Fallo crítico en el hilo de auditoría: {e}")