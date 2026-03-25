import streamlit as st
import pandas as pd
from database import conectar_bd

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>🕵️ Control de Accesos y Seguridad</h2>", unsafe_allow_html=True)
    st.info("Este registro es inmutable y muestra todos los ingresos exitosos al sistema SIMPOL.")

    try:
        conn = conectar_bd()
        # Traemos los últimos 50 accesos
        query = """
            SELECT 
                fecha_acceso as 'Fecha/Hora', 
                usuario as 'ID Usuario', 
                nombre_completo as 'Analista', 
                rol as 'Nivel de Acceso',
                ip_cliente as 'Origen IP'
            FROM log_accesos 
            ORDER BY fecha_acceso DESC 
            LIMIT 50
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            # Resumen rápido en métricas
            c1, c2 = st.columns(2)
            total_hoy = len(df) # Simplificado para el ejemplo
            c1.metric("Ingresos (Últimos 50)", total_hoy)
            c2.metric("Último acceso", str(df.iloc[0]['Fecha/Hora'])[:16])

            # Tabla de logs
            st.dataframe(
                df,
                column_config={
                    "Fecha/Hora": st.column_config.DatetimeColumn(format="DD/MM/YY - hh:mm A"),
                    "Nivel de Acceso": st.column_config.TextColumn("Rol")
                },
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("🗑️ Limpiar Vista (Solo Visual)", use_container_width=True):
                st.rerun()
        else:
            st.warning("No hay registros de acceso todavía.")

    except Exception as e:
        st.error(f"Error al cargar logs de auditoría: {e}")