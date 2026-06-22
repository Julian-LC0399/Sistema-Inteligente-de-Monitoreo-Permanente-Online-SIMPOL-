import streamlit as st
from database import conectar_bd
from datetime import datetime

def obtener_estado_agente_local():
    """
    Consulta el último latido del agente en la base de datos
    y evalúa su estado con un margen ultra-estricto para detectar el apagado rápido.
    """
    conexion = conectar_bd()
    # Estado por defecto si falla la conexión o no hay registros (Agente Apagado)
    estado = {"activo": False, "tipo": "DESCONECTADO"}
    
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor(dictionary=True)
            # Traemos el último registro absoluto para evaluar el latido en tiempo real
            query = """
                SELECT ip_servidor, fecha_registro
                FROM monitoreo 
                ORDER BY fecha_registro DESC LIMIT 1
            """
            cursor.execute(query)
            registro = cursor.fetchone()
            
            if registro:
                fecha_reg = registro["fecha_registro"]
                ip_reg = str(registro["ip_servidor"])
                
                # Conversión preventiva por si el driver retorna la fecha como string
                if isinstance(fecha_reg, str):
                    try:
                        fecha_reg = datetime.strptime(fecha_reg, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                
                ahora = datetime.now()
                diferencia_segundos = abs((ahora - fecha_reg).total_seconds())
                
                # DETECCIÓN EN TIEMPO REAL: 
                # Bajamos la tolerancia a un margen estricto (ej. 15-20 segundos).
                # Si el agente se detiene, dejará de escribir y superará este tiempo de inmediato.
                if diferencia_segundos <= 20:
                    estado["activo"] = True
                    
                    # Identificación del modo basada en tu rango de red local (terminal)
                    if ip_reg in ["127.0.0.1", "localhost", "::1"] or ip_reg.startswith("10."):
                        estado["tipo"] = "MODO LOCAL"
                    else:
                        estado["tipo"] = "CONECTADO A PRTG"
                else:
                    # Si la diferencia es mayor, el dato es viejo -> El agente fue desactivado
                    estado["activo"] = False
        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()
            conexion.close()
            
    return estado

def mostrar_pantalla():
    # 1. CREAMOS UN CONTENEDOR VACÍO
    contenedor_principal = st.empty()
    
    with contenedor_principal.container():
        cargo = st.session_state.get("cargo", "Analista")
        rol = st.session_state.get("rol", "operador").upper()

        # --- BLOQUE DE ESTILOS (Inyectados localmente) ---
        st.markdown("""
            <style>
                [data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] h3 {
                    color: #000000 !important;
                }
                .bienvenida-titulo {
                    color: #003366 !important;
                    font-weight: bold !important;
                    margin-bottom: 0px;
                }
                .estatus-box {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #d1d3d8;
                    margin-bottom: 10px;
                }
                .badge-activo {
                    background-color: #e6f4ea;
                    border: 1px solid #34a853;
                    padding: 8px 12px;
                    border-radius: 6px;
                    color: #137333;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 12.5px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    margin-top: 10px;
                }
                .badge-inactivo {
                    background-color: #fce8e6;
                    border: 1px solid #ea4335;
                    padding: 8px 12px;
                    border-radius: 6px;
                    color: #c5221f;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 12.5px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    margin-top: 10px;
                }
                .punto-verde {
                    height: 9px;
                    width: 9px;
                    background-color: #34a853;
                    border-radius: 50%;
                    display: inline-block;
                    margin-right: 8px;
                    animation: pulse 1.5s infinite;
                }
                .punto-rojo {
                    height: 9px;
                    width: 9px;
                    background-color: #ea4335;
                    border-radius: 50%;
                    display: inline-block;
                    margin-right: 8px;
                }
                @keyframes pulse {
                    0% { transform: scale(0.95); opacity: 0.5; }
                    50% { transform: scale(1.1); opacity: 1; }
                    100% { transform: scale(0.95); opacity: 0.5; }
                }
            </style>
        """, unsafe_allow_html=True)

        # 2. CONTENIDO ENCAPSULADO
        st.markdown(f"<h1 class='bienvenida-titulo'>Bienvenido al sistema, {cargo}</h1>", unsafe_allow_html=True)
        st.divider()

        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            <div class="estatus-box">
                <h3>📊 Estatus de Sesión</h3>
                <p>Usted ha ingresado al <b>SIMPOL</b> (Sistema Inteligente de Monitoreo Permanente Online).</p>
                <ul>
                    <li><b>Cargo Institucional:</b> {cargo}</li>
                    <li><b>Rango de Sistema:</b> {rol}</li>
                    <li><b>Ubicación:</b> Central Banco Caroní</li>
                    <li><b>Acceso:</b> Autorizado</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.success(f"✅ Conexión Segura Establecida\n\nIP: Localhost\nDB: Sincronizada")
            
            # --- INDICADOR DINÁMICO ---
            info_agente = obtener_estado_agente_local()
            if info_agente["activo"]:
                html_agente = f"""
                <div class="badge-activo">
                    <span class="punto-verde"></span>
                    <span>AGENTE ACTIVADO<br><small style="font-weight:normal; font-size:10.5px;">{info_agente["tipo"]}</small></span>
                </div>
                """
            else:
                html_agente = """
                <div class="badge-inactivo">
                    <span class="punto-rojo"></span>
                    <span>AGENTE INACTIVO (OFFLINE)<br><small style="font-weight:normal; font-size:10.5px;">Esperando telemetría...</small></span>
                </div>
                """
            st.markdown(html_agente, unsafe_allow_html=True)