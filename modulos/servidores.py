import streamlit as st
from database import obtener_conexion

def mostrar_tabla_servidores():
    st.title("🖥️ Gestión de Servidores")
    st.markdown("---")
    
    try:
        # Establecer conexión con la base de datos MySQL
        conn = obtener_conexion()
        cursor = conn.cursor(dictionary=True) # Retorna cada fila como un diccionario
        
        query = "SELECT ip, nombre_alias, departamento, estado_monitoreo, fecha_alta FROM servidores"
        cursor.execute(query)
        
        # Recuperar todas las filas (Lista de diccionarios)
        servidores = cursor.fetchall()
        
        if servidores:
            # Creamos los encabezados de la tabla manualmente
            # Usamos st.table o st.dataframe pasando la lista de diccionarios directamente
            
            # Limpiamos y formateamos los datos para la vista
            datos_formateados = []
            for s in servidores:
                datos_formateados.append({
                    "Dirección IP": s['ip'],
                    "Alias del Servidor": s['nombre_alias'],
                    "Departamento": s['departamento'],
                    "Estado": "🟢 Activo" if s['estado_monitoreo'] == 1 else "🔴 Inactivo",
                    "Fecha Registro": s['fecha_alta'].strftime("%Y-%m-%d %H:%M")
                })
            
            # Mostrar la tabla nativa de Streamlit (acepta listas de dicts)
            st.dataframe(datos_formateados, use_container_width=True, hide_index=True)
            
            # Métricas rápidas usando lógica nativa
            col1, col2 = st.columns(2)
            col1.metric("Total Servidores", len(servidores))
            
            # Obtener departamentos únicos sin set/numpy
            depto_unicos = []
            for s in servidores:
                if s['departamento'] not in depto_unicos:
                    depto_unicos.append(s['departamento'])
            
            col2.metric("Departamentos", len(depto_unicos))
            
        else:
            st.warning("No hay servidores registrados en la base de datos.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

if __name__ == "__main__":
    mostrar_tabla_servidores()