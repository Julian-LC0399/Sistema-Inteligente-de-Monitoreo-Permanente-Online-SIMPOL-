import streamlit as st
from database import conectar_bd

# Intento silencioso de importar pandas
try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

def mostrar_pantalla():
    st.markdown("<h2 style='color:#003366;'>🕵️ Control de Accesos y Seguridad</h2>", unsafe_allow_html=True)
    st.info("Este registro es inmutable y muestra los ingresos al sistema SIMPOL.")

    try:
        conn = conectar_bd()
        if not conn:
            st.error("No se pudo conectar a la base de datos.")
            return

        # USAMOS CURSOR NATIVO: Esto es lo que salva el archivo
        cursor = conn.cursor(dictionary=True)
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
        cursor.execute(query)
        datos = cursor.fetchall() 
        cursor.close()
        conn.close()

        if datos:
            # Métricas rápidas (Funcionan perfecto con listas)
            c1, c2 = st.columns(2)
            c1.metric("Ingresos (Últimos 50)", len(datos))
            c2.metric("Último acceso", str(datos[0]['Fecha/Hora'])[:16])

            # --- DECISIÓN DE VISUALIZACIÓN ---
            if PANDAS_OK:
                # Si estamos en tu PC con todo instalado
                df = pd.DataFrame(datos)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                # Si estamos en el Servidor del Banco con error de DLL
                st.warning("⚠️ Ejecutando en modo de alta compatibilidad (Servidor)")
                # st.table crea una tabla estática muy limpia y elegante
                st.table(datos)
            
            if st.button("🗑️ Limpiar Vista", use_container_width=True):
                st.rerun()
        else:
            st.warning("No hay registros de acceso todavía.")

    except Exception as e:
        st.error(f"Error técnico en auditoría: {e}")