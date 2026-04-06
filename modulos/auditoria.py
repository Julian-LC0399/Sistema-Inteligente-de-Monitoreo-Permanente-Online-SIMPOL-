import streamlit as st
from database import conectar_bd

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>🕵️ Control de Accesos y Seguridad</h2>", unsafe_allow_html=True)
    
    st.info("Este registro es inmutable y muestra los ingresos al sistema SIMPOL.")

    try:
        conn = conectar_bd()
        if conn:
            # 1. Obtener estadísticas rápidas (Nativo)
            cursor = conn.cursor(dictionary=True)
            
            # Conteo total
            cursor.execute("SELECT COUNT(*) as total FROM historico_accesos")
            total_ingresos = cursor.fetchone()['total']
            
            # Último acceso
            cursor.execute("SELECT fecha_acceso FROM historico_accesos ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()
            fecha_u = ultimo['fecha_acceso'].strftime('%Y-%m-%d %H:%M') if ultimo else "N/A"

            # 2. Renderizar métricas superiores
            c1, c2 = st.columns(2)
            with c1.container(border=True):
                st.metric("INGRESOS (TOTAL)", total_ingresos)
            with c2.container(border=True):
                st.metric("ÚLTIMO ACCESO", fecha_u)

            st.divider()

            # 3. Tabla de registros (100% Nativa - Sin Pandas)
            st.markdown("### 📋 Historial Detallado")
            
            # Traemos los últimos 50 registros
            cursor.execute("""
                SELECT usuario, fecha_acceso, ip_origen, terminal_nombre 
                FROM historico_accesos 
                ORDER BY fecha_acceso DESC LIMIT 50
            """)
            logs = cursor.fetchall()
            cursor.close()
            conn.close()

            if logs:
                # Formateamos para que se vea limpio en st.table
                tabla_limpia = []
                for l in logs:
                    tabla_limpia.append({
                        "USUARIO": l['usuario'],
                        "FECHA Y HORA": l['fecha_acceso'].strftime('%d/%m/%Y %H:%M:%S'),
                        "IP ORIGEN": l['ip_origen'],
                        "ESTACIÓN": l['terminal_nombre']
                    })
                
                # Usamos st.table porque no requiere librerías externas
                st.table(tabla_limpia)
            else:
                st.warning("No hay registros de auditoría disponibles.")

    except Exception as e:
        # Si algo falla aquí, es por la base de datos, no por Numpy
        st.error(f"Error técnico en auditoría: {e}")