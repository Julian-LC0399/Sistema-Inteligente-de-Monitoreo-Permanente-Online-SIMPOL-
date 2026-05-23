import streamlit as st
from database import obtener_lista_servidores, conectar_bd
from datetime import datetime

def obtener_umbrales_actuales(ip):
    """
    Busca el último registro de configuración de umbrales para esa IP.
    Si es el UAP Compensación (10.10.1.133), adapta los valores iniciales 
    para alinearse con el perfil ajustado de 4GB RAM de PRTG.
    """
    if ip == "10.10.1.133":
        umbrales = {
            "cpu_advertencia": 70, "cpu_critico": 85,
            "ram_advertencia": 1.5, "ram_critico": 0.5
        }
    else:
        # Contingencia estándar para servidores web u otros nodos grandes
        umbrales = {
            "cpu_advertencia": 70, "cpu_critico": 85,
            "ram_advertencia": 8.0, "ram_critico": 4.0  
        }
    
    for i in range(1, 6):
        umbrales[f"disco_{i}_advertencia"] = 3.0 if ip == "10.10.1.133" else 40.0
        umbrales[f"disco_{i}_critico"] = 1.0 if ip == "10.10.1.133" else 15.0

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM historico_umbrales 
                WHERE ip_servidor = %s 
                ORDER BY id_historico DESC LIMIT 1
            """
            cursor.execute(query, (ip,))
            res = cursor.fetchone()
            if res and "disco_1_advertencia" in res:
                umbrales = res
            cursor.close()
            conn.close()
        except Exception:
            pass 
    return umbrales

def guardar_nuevo_umbral(usuario_id, ip, cpu_adv, cpu_crit, ram_adv, ram_crit, discos_umbrales, motivo):
    """Inserta la auditoría de cambio de semáforos en la base de datos."""
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_umbrales 
                (ip_servidor, usuario_id, cpu_advertencia, cpu_critico, 
                 ram_advertencia, ram_critico, 
                 disco_1_advertencia, disco_1_critico, 
                 disco_2_advertencia, disco_2_critico, 
                 disco_3_advertencia, disco_3_critico, 
                 disco_4_advertencia, disco_4_critico, 
                 disco_5_advertencia, disco_5_critico, 
                 justificacion, fecha_change)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                ip, usuario_id, float(cpu_adv), float(cpu_crit), float(ram_adv), float(ram_crit),
                float(discos_umbrales['d1_adv']), float(discos_umbrales['d1_crit']),
                float(discos_umbrales['d2_adv']), float(discos_umbrales['d2_crit']),
                float(discos_umbrales['d3_adv']), float(discos_umbrales['d3_crit']),
                float(discos_umbrales['d4_adv']), float(discos_umbrales['d4_crit']),
                float(discos_umbrales['d5_adv']), float(discos_umbrales['d5_crit']),
                motivo, datetime.now()
            )
            cursor.execute(query, valores)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception:
            pass
    return False

# ==========================================================
# VISTA PRINCIPAL DEL MÓDULO (REFRESCO DINÁMICO POR IP)
# ==========================================================
def mostrar_pantalla(usuario_id=1, rol_usuario="operador"):
    """Dibuja la interfaz garantizando que cada servidor mantenga su estado aislado."""
    st.title("🔔 Gestión de Alertas y Semáforos Operativos")
    st.subheader("Versión 3.1 - Configuración basada en Capacidades Líquidas (GB)")
    
    st.info(f"👤 Analista Autónomo: ID {usuario_id} | Rol Asignado: {rol_usuario.upper()}")

    servidores = obtener_lista_servidores()
    if not servidores:
        st.warning("No hay servidores registrados en la infraestructura para parametrizar.")
        return

    # Selector de Servidores
    dict_servidores = {f"{s['nombre_alias']} ({s['ip']})": s['ip'] for s in servidores}
    seleccion = st.selectbox("Seleccione el Servidor Institucional:", list(dict_servidores.keys()))
    ip_sel = dict_servidores[seleccion]

    # Cargar umbrales específicos de la IP seleccionada
    u_actuales = obtener_umbrales_actuales(ip_sel)

    st.markdown("### ") 

    # --- CONTENEDOR 1: CPU (Campos indexados con la IP en el key) ---
    with st.container(border=True):
        st.markdown("#### 📊 Carga de Procesamiento (CPU)")
        st.caption("Métrica porcentual de estrés: El valor Crítico debe ser MAYOR al de Advertencia.")
        cc1, cc2 = st.columns(2)
        with cc1:
            cpu_adv = st.number_input("Advertencia CPU (%)", min_value=1.0, max_value=100.0, value=float(u_actuales['cpu_advertencia']), step=1.0, key=f"cpu_a_{ip_sel}")
        with cc2:
            cpu_crit = st.number_input("Crítico CPU (%)", min_value=1.0, max_value=100.0, value=float(u_actuales['cpu_critico']), step=1.0, key=f"cpu_c_{ip_sel}")

    st.markdown("### ") 

    # --- CONTENEDOR 2: RAM (Campos indexados con la IP en el key) ---
    with st.container(border=True):
        st.markdown("#### 🧠 Disponibilidad Volátil (RAM)")
        
        val_ram_adv = float(u_actuales['ram_advertencia'])
        val_ram_crit = float(u_actuales['ram_critico'])
        # Si viene en Bytes, normalizar a GB
        if val_ram_adv > 1024:
            val_ram_adv = round(val_ram_adv / (1024**3), 2)
            val_ram_crit = round(val_ram_crit / (1024**3), 2)

        st.caption(f"Métrica líquida (GB Libres) para el nodo activo.")
        cr1, cr2 = st.columns(2)
        with cr1:
            ram_adv = st.number_input("Advertencia RAM (GB Libres)", min_value=0.1, max_value=512.0, value=float(val_ram_adv), step=0.1, format="%.2f", key=f"ram_a_{ip_sel}")
        with cr2:
            ram_crit = st.number_input("Crítico RAM (GB Libres)", min_value=0.1, max_value=512.0, value=float(val_ram_crit), step=0.1, format="%.2f", key=f"ram_c_{ip_sel}")

    st.markdown("### ") 

    # --- CONTENEDOR 3: ALMACENAMIENTO (Campos indexados con la IP en el key) ---
    with st.container(border=True):
        st.markdown("#### 💾 Almacenamiento Estático (Límites Mínimos en GB Libres)")
        st.markdown("### ") 

        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1:
            st.markdown("<div style='background-color: #f0f2f6; padding: 6px; border-radius: 4px; font-weight: bold; text-align: center; font-size:12px;'>Disco 1 (C:)</div>", unsafe_allow_html=True)
            d1_adv = st.number_input("Adv. C: (GB)", min_value=0.1, value=float(u_actuales.get('disco_1_advertencia', 3.0)), step=0.1, format="%.2f", key=f"d1_a_{ip_sel}")
            d1_crit = st.number_input("Crit. C: (GB)", min_value=0.1, value=float(u_actuales.get('disco_1_critico', 1.0)), step=0.1, format="%.2f", key=f"d1_c_{ip_sel}")
            
        with c2:
            st.markdown("<div style='background-color: #f0f2f6; padding: 6px; border-radius: 4px; font-weight: bold; text-align: center; font-size:12px;'>Disco 2 (D:)</div>", unsafe_allow_html=True)
            d2_adv = st.number_input("Adv. D: (GB)", min_value=0.1, value=float(u_actuales.get('disco_2_advertencia', 3.0)), step=0.1, format="%.2f", key=f"d2_a_{ip_sel}")
            d2_crit = st.number_input("Crit. D: (GB)", min_value=0.1, value=float(u_actuales.get('disco_2_critico', 1.0)), step=0.1, format="%.2f", key=f"d2_c_{ip_sel}")
            
        with c3:
            st.markdown("<div style='background-color: #f0f2f6; padding: 6px; border-radius: 4px; font-weight: bold; text-align: center; font-size:12px;'>Disco 3</div>", unsafe_allow_html=True)
            d3_adv = st.number_input("Adv. D3 (GB)", min_value=0.1, value=float(u_actuales.get('disco_3_advertencia', 3.0)), step=0.1, format="%.2f", key=f"d3_a_{ip_sel}")
            d3_crit = st.number_input("Crit. D3 (GB)", min_value=0.1, value=float(u_actuales.get('disco_3_critico', 1.0)), step=0.1, format="%.2f", key=f"d3_c_{ip_sel}")
            
        with c4:
            st.markdown("<div style='background-color: #f0f2f6; padding: 6px; border-radius: 4px; font-weight: bold; text-align: center; font-size:12px;'>Disco 4</div>", unsafe_allow_html=True)
            d4_adv = st.number_input("Adv. D4 (GB)", min_value=0.1, value=float(u_actuales.get('disco_4_advertencia', 3.0)), step=0.1, format="%.2f", key=f"d4_a_{ip_sel}")
            d4_crit = st.number_input("Crit. D4 (GB)", min_value=0.1, value=float(u_actuales.get('disco_4_critico', 1.0)), step=0.1, format="%.2f", key=f"d4_c_{ip_sel}")
            
        with c5:
            st.markdown("<div style='background-color: #f0f2f6; padding: 6px; border-radius: 4px; font-weight: bold; text-align: center; font-size:12px;'>Disco 5</div>", unsafe_allow_html=True)
            d5_adv = st.number_input("Adv. D5 (GB)", min_value=0.1, value=float(u_actuales.get('disco_5_advertencia', 3.0)), step=0.1, format="%.2f", key=f"d5_a_{ip_sel}")
            d5_crit = st.number_input("Crit. D5 (GB)", min_value=0.1, value=float(u_actuales.get('disco_5_critico', 1.0)), step=0.1, format="%.2f", key=f"d5_c_{ip_sel}")

    st.markdown("### ") 
    st.markdown("---")
    st.markdown("### ") 

    # --- SECCIÓN DE GUARDADO ASOCIADA A LA INSTANCIA ---
    es_operador = rol_usuario.lower() == "operador"

    if es_operador:
        st.warning("⚠️ Tu rol de Operador te permite visualizar los umbrales institucionales, pero no modificarlos. Solicita privilegios al Administrador del CSU si es requerido.")
    else:
        # Usamos una variable de estado que dependa de la IP para que se cierre automáticamente al cambiar de nodo
        key_panel = f"mostrar_panel_{ip_sel}"
        if key_panel not in st.session_state:
            st.session_state[key_panel] = False

        if st.button("🔧 Modificar Parámetros Institucionales", use_container_width=True):
            st.session_state[key_panel] = not st.session_state[key_panel]

        if st.session_state[key_panel]:
            st.markdown("### ") 
            with st.container(border=True):
                st.markdown("#### 📝 Confirmación y Registro de Auditoría")
                motivo = st.text_area(
                    "Justificación del Cambio (Requisito Obligatorio CSU):", 
                    placeholder="Ej: Ajuste de umbrales basado en el plan de capacidad del servidor seleccionado.",
                    key=f"justificacion_{ip_sel}"
                )
                
                st.markdown("### ") 
                confirmar_submit = st.button("🚀 Confirmar y Aplicar Umbrales en Caliente", type="primary")

                if confirmar_submit:
                    if not motivo.strip():
                        st.error("Error: Debe ingresar una justificación válida para la bitácora de auditoría.")
                    elif cpu_adv >= cpu_crit:
                        st.error("❌ Error de consistencia en CPU: El umbral Crítico (%) debe ser estrictamente MAYOR al de Advertencia.")
                    elif ram_adv <= ram_crit:
                        st.error("❌ Error de consistencia en RAM: El umbral de Advertencia (GB) debe ser MAYOR al Crítico.")
                    elif (d1_adv <= d1_crit or d2_adv <= d2_crit or d3_adv <= d3_crit or d4_adv <= d4_crit or d5_adv <= d5_crit):
                        st.error("❌ Error de consistencia en Discos: La Advertencia (GB) debe ser numéricamente superior al estado Crítico.")
                    else:
                        discos_umbrales = {
                            'd1_adv': d1_adv, 'd1_crit': d1_crit,
                            'd2_adv': d2_adv, 'd2_crit': d2_crit,
                            'd3_adv': d3_adv, 'd3_crit': d3_crit,
                            'd4_adv': d4_adv, 'd4_crit': d4_crit,
                            'd5_adv': d5_adv, 'd5_crit': d5_crit
                        }
                        
                        exito = guardar_nuevo_umbral(usuario_id, ip_sel, cpu_adv, cpu_crit, ram_adv, ram_crit, discos_umbrales, motivo)
                        if exito:
                            st.success(f"¡Umbrales actualizados con éxito para el nodo {seleccion}! Cambios aplicados en caliente.")
                            st.session_state[key_panel] = False
                            st.rerun()
                        else:
                            st.error("Error crítico: Falló la comunicación con el servidor MySQL al guardar la bitácora.")