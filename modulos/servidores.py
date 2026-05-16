import streamlit as st
# Cambiamos 'obtener_conexion' por 'conectar_bd'
from database import conectar_bd 

def mostrar_tabla_servidores():
    st.title("🖥️ Gestión de Servidores")
    st.markdown("---")
    
    try:
        # Usamos el nombre de función exacto que está en tu database.py
        conn = conectar_bd() 
        
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL. Verifica el servicio.")
            return
            
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT ip, nombre_alias, departamento, estado_monitoreo, fecha_alta FROM servidores"
        cursor.execute(query)
        
        servidores = cursor.fetchall()
        
        if servidores:
            datos_formateados = []
            for s in servidores:
                datos_formateados.append({
                    "Dirección IP": s['ip'],
                    "Alias del Servidor": s['nombre_alias'],
                    "Departamento": s['departamento'],
                    "Estado": "🟢 Activo" if s['estado_monitoreo'] == 1 else "🔴 Inactivo",
                    "Fecha Registro": s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"
                })
            
            st.dataframe(datos_formateados, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Servidores", len(servidores))
            
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
        st.error(f"Error al procesar los datos de los servidores: {e}")

if __name__ == "__main__":
    mostrar_tabla_servidores()