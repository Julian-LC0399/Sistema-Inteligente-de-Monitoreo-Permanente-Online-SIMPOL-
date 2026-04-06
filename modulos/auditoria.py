import streamlit as st
from database import conectar_bd

def mostrar_pantalla():
    st.markdown("<h2 style='color: #003366;'>🕵️ Control de Accesos y Seguridad</h2>", unsafe_allow_html=True)
    
    # CSS Reforzado: Bordes, Colores y Columnas
    st.markdown("""
        <style>
            [data-testid="stTable"] {
                background-color: white;
                border-radius: 5px;
            }
            [data-testid="stTable"] td {
                color: #000000 !important;
                border: 1px solid #dee2e6 !important;
            }
            [data-testid="stTable"] th {
                background-color: #003366 !important;
                color: white !important;
                border: 1px solid #002244 !important;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    try:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM log_accesos")
            total_ingresos = cursor.fetchone()[0]
            
            cursor.execute("SELECT fecha_acceso FROM log_accesos ORDER BY id_log DESC LIMIT 1")
            ultimo = cursor.fetchone()
            fecha_u = ultimo[0].strftime('%d/%m/%Y %H:%M') if ultimo else "N/A"

            c1, c2 = st.columns(2)
            c1.metric("INGRESOS (TOTAL)", total_ingresos)
            c2.metric("ÚLTIMO ACCESO", fecha_u)

            st.divider()

            st.markdown("### 📋 Historial Detallado")
            cursor.execute("SELECT usuario, fecha_acceso, ip_cliente, resultado FROM log_accesos ORDER BY fecha_acceso DESC LIMIT 50")
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
                        "RESULTADO": l[3]
                    })
                st.table(tabla_limpia)
            else:
                st.warning("No hay registros en 'log_accesos'.")

    except Exception as e:
        st.error(f"⚠️ Error de base de datos: {e}")