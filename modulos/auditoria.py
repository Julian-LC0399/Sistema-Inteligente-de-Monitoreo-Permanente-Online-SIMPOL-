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

                # 4. Banner institucional (Optimizado para no romper el layout)
                st.markdown(f"""
                    <div style="background-color:#003366; padding:15px; border-radius:10px; color:white; text-align:center; margin-bottom:20px;">
                        <p style="margin:0; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Registros en Base de Datos</p>
                        <h1 style="margin:0; color:white; font-size:32px; font-weight:bold;">{total}</h1>
                    </div>
                """, unsafe_allow_html=True)

                # 5. Renderizado de Tarjetas (ENCAPSULADAS)
                if logs:
                    # Usamos un solo bloque de Markdown para reducir la carga de hilos en el .exe
                    # En lugar de 30 st.markdown, generamos un solo string HTML
                    html_acumulado = ""
                    for l in logs:
                        u, f, ip, res = l[0], l[1].strftime('%d/%m/%Y %H:%M'), l[2], l[3]
                        color_borde = "#28a745" if res == "EXITOSO" else "#d32f2f"
                        
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
                    st.warning("No se encontraron resultados para la búsqueda.")

        except Exception as e:
            st.error(f"Error en Auditoría: {str(e)}")