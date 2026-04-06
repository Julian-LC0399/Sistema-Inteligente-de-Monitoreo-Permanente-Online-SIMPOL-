import streamlit as st
from database import conectar_bd

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>🕵️ Control de Accesos y Seguridad</h2>", unsafe_allow_html=True)
    
    st.info("Este registro es inmutable y muestra los ingresos al sistema SIMPOL.")

    try:
        conn = conectar_bd()
        if conn:
            # Usamos un cursor normal para evitar conflictos de configuración
            cursor = conn.cursor()
            
            # 1. Obtener estadísticas rápidas (Ajustado a nombres de SQL real)
            # Conteo total
            cursor.execute("SELECT COUNT(*) FROM log_accesos")
            res_total = cursor.fetchone()
            total_ingresos = res_total[0] if res_total else 0
            
            # Último acceso
            cursor.execute("SELECT fecha_acceso FROM log_accesos ORDER BY id_log DESC LIMIT 1")
            ultimo = cursor.fetchone()
            fecha_u = ultimo[0].strftime('%d/%m/%Y %H:%M') if ultimo else "N/A"

            # 2. Renderizar métricas superiores
            c1, c2 = st.columns(2)
            with c1.container(border=True):
                st.metric("INGRESOS (TOTAL)", total_ingresos)
            with c2.container(border=True):
                st.metric("ÚLTIMO ACCESO", fecha_u)

            st.divider()

            # 3. Tabla de registros (Ajustada a columnas del SQL: usuario, fecha_acceso, ip_cliente, resultado)
            st.markdown("### 📋 Historial Detallado")
            
            cursor.execute("""
                SELECT usuario, fecha_acceso, ip_cliente, resultado 
                FROM log_accesos 
                ORDER BY fecha_acceso DESC LIMIT 50
            """)
            logs = cursor.fetchall()
            cursor.close()
            conn.close()

            if logs:
                tabla_limpia = []
                for l in logs:
                    tabla_limpia.append({
                        "USUARIO": l[0],
                        "FECHA Y HORA": l[1].strftime('%d/%m/%Y %H:%M:%S'),
                        "IP CLIENTE": l[2],
                        "ESTADO": l[3]
                    })
                
                # Visualización nativa
                st.table(tabla_limpia)
            else:
                st.warning("No hay registros de auditoría disponibles en la tabla 'log_accesos'.")

    except Exception as e:
        st.error(f"⚠️ Error de base de datos: {e}")