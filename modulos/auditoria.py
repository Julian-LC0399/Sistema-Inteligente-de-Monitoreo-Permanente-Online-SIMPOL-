import streamlit as st
from database import conectar_bd

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366; font-family: sans-serif;'>🕵️ Control de Accesos</h2>", unsafe_allow_html=True)
    
    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            
            # 1. Búsqueda simple
            busqueda = st.text_input("🔍 Buscar usuario:", placeholder="Ej: seguridad_csu")
            
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

            # 4. Banner institucional
            st.markdown(f"""
                <div style="background-color:#003366; padding:15px; border-radius:10px; color:white; text-align:center; margin-bottom:20px;">
                    <p style="margin:0; font-size:12px; opacity:0.8;">REGISTROS EN BASE DE DATOS</p>
                    <h1 style="margin:0; color:white; font-size:28px;">{total}</h1>
                </div>
            """, unsafe_allow_html=True)

            # 5. Renderizado de Tarjetas
            if logs:
                for l in logs:
                    u, f, ip, res = l[0], l[1].strftime('%d/%m/%Y %H:%M'), l[2], l[3]
                    color_borde = "#28a745" if res == "EXITOSO" else "#d32f2f"
                    
                    st.markdown(f"""
                        <div style="border-left: 5px solid {color_borde}; background-color: white; padding: 12px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #eee; border-left-width: 5px;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color:#003366; font-weight:bold; font-size: 16px;">{u}</span>
                                <span style="color:#28a745; font-weight:bold; font-size: 12px;">{res}</span>
                            </div>
                            <div style="color:#666; font-size: 13px; margin-top: 5px;">
                                📅 {f} &nbsp;&nbsp; | &nbsp;&nbsp; 💻 IP: {ip}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No se encontraron resultados para la búsqueda.")

    except Exception as e:
        st.error(f"Error en Auditoría: {str(e)}")