import streamlit as st
from database import conectar_bd

def mostrar_tabla_servidores():
    # 1. ESTILOS CSS REFORZADOS
    st.markdown("""
        <style>
            .titulo-gestion { 
                color: #003366 !important; 
                font-size: 24px !important; 
                font-weight: bold !important; 
                margin-bottom: 15px;
                display: block;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<span class='titulo-gestion'>🖥️ GESTIÓN Y VISTA DE SERVIDORES</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    try:
        # Conexión exacta a tu base de datos MySQL
        conn = conectar_bd()
        if conn is None:
            st.error("❌ No se pudo establecer conexión con el servidor MySQL. Verifica el servicio de base de datos.")
            return
            
        cursor = conn.cursor(dictionary=True)
        # Consulta de todo el catálogo técnico
        query = """
            SELECT ip, nombre_alias, departamento, estado_monitoreo, fecha_alta, 
                   id_sensor_cpu, id_sensor_ram, id_sensor_disco, id_sensor_red, id_sensor_latencia 
            FROM servidores
        """
        cursor.execute(query)
        servidores = cursor.fetchall()
        
        if servidores:
            # 2. CONSTRUCCIÓN DE LA TABLA EN HTML PURO
            html_lineas = []
            html_lineas.append("""
            <style>
                .tabla-banco {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                }
                .tabla-banco th {
                    background-color: #003366 !important;
                    color: #FFFFFF !important;
                    font-weight: bold !important;
                    text-align: center !important;
                    padding: 12px 10px;
                    border: 1px solid #dee2e6 !important;
                    font-size: 13px;
                }
                .tabla-banco td { 
                    color: #000000 !important; 
                    border: 1px solid #dee2e6 !important; 
                    padding: 10px;
                    text-align: left;
                    font-size: 13px;
                }
                .tabla-banco tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
            </style>
            """)
            html_lineas.append('<table class="tabla-banco">')
            html_lineas.append("""
                <thead>
                    <tr>
                        <th>DIRECCIÓN IP</th>
                        <th>ALIAS DEL SERVIDOR</th>
                        <th>DEPARTAMENTO</th>
                        <th>ID CPU</th>
                        <th>ID RAM</th>
                        <th>ID DISCO</th>
                        <th>ID RED</th>
                        <th>ID LATENCIA</th>
                        <th>ESTADO</th>
                        <th>FECHA REGISTRO</th>
                    </tr>
                </thead>
            """)
            html_lineas.append('<tbody>')
            
            for s in servidores:
                estado = "🟢 ACTIVO" if s['estado_monitoreo'] == 1 else "🔴 INACTIVO"
                fecha_formateada = s['fecha_alta'].strftime("%Y-%m-%d %H:%M") if s['fecha_alta'] else "N/A"
                
                # Evaluación lógica nativa para el formateo de IDs no asignados (0)
                cpu = s['id_sensor_cpu'] if s['id_sensor_cpu'] != 0 else "No asignado"
                ram = s['id_sensor_ram'] if s['id_sensor_ram'] != 0 else "No asignado"
                disco = s['id_sensor_disco'] if s['id_sensor_disco'] != 0 else "No asignado"
                red = s['id_sensor_red'] if s['id_sensor_red'] != 0 else "No asignado"
                latencia = s['id_sensor_latencia'] if s['id_sensor_latencia'] != 0 else "No asignado"
                
                html_lineas.append('<tr>')
                html_lineas.append(f'<td><b>{s["ip"]}</b></td>')
                html_lineas.append(f'<td>{s["nombre_alias"]}</td>')
                html_lineas.append(f'<td>{s["departamento"]}</td>')
                html_lineas.append(f'<td>{cpu}</td>')
                html_lineas.append(f'<td>{ram}</td>')
                html_lineas.append(f'<td>{disco}</td>')
                html_lineas.append(f'<td>{red}</td>')
                html_lineas.append(f'<td>{latencia}</td>')
                html_lineas.append(f'<td>{estado}</td>')
                html_lineas.append(f'<td>{fecha_formateada}</td>')
                html_lineas.append('</tr>')
                
            html_lineas.append('</tbody></table>')
            
            html_final = "".join(html_lineas)
            
            # Altura calculada para evitar barras de desplazamiento innecesarias en el iframe
            altura_vista = max(250, len(servidores) * 45 + 70)
            st.components.v1.html(html_final, height=altura_vista, scrolling=True)
            
        else:
            st.warning("No se encontraron servidores registrados en la base de datos.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Fallo técnico al procesar el módulo de servidores: {e}")

if __name__ == "__main__":
    mostrar_tabla_servidores()