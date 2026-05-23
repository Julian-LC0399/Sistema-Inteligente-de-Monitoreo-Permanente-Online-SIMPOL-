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
                cursor = conn.cursor()
                
                # 1. Búsqueda con Key Única para el .exe
                busqueda = st.text_input("🔍 Buscar usuario:", placeholder="Ej: seguridad_csu", key="input_busqueda_auditoria")
                
                # 2. Conteo total
                cursor.execute("SELECT COUNT(*) FROM log_accesos")
                total = cursor.fetchone()[0]
                
                # 3. Consulta con filtro
                query = "SELECT usuario, fecha_acceso, ip_cliente, resultado FROM log_accesos"
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
                        u, f, ip, res = l[0], l[1].strftime('%d/%m/%Y %H:%M'), l[2], l[3]
                        
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
                            <div style="color:#666; font-size: 12px; margin-top: 6px; display: flex; gap: 15px;">
                                <span>📅 {f}</span>
                                <span>💻 IP: {ip}</span>
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