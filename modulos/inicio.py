import streamlit as st
from database import conectar_bd
from datetime import datetime
import os
import sys  # ← AGREGAR ESTA LÍNEA

def get_resource_path(relative_path):
    """Localiza recursos dentro del paquete .exe o en desarrollo"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def obtener_estado_agente_local():
    """
    Consulta el último latido del agente en la base de datos
    y evalúa su estado en tiempo real.
    """
    conexion = conectar_bd()
    estado = {"activo": False, "tipo": "DESCONECTADO", "modo": "DESCONOCIDO"}
    
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor(dictionary=True)
            
            # Obtener el registro más reciente
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
                
                if isinstance(fecha_reg, str):
                    try:
                        fecha_reg = datetime.strptime(fecha_reg, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                
                ahora = datetime.now()
                diferencia_segundos = abs((ahora - fecha_reg).total_seconds())
                
                # Margen de 30 segundos (el agente guarda cada 15s)
                if diferencia_segundos <= 30:
                    estado["activo"] = True
                    
                    # DETERMINAR MODO POR IP
                    # LOCAL: 127.0.0.1 (localhost)
                    # PRTG: Cualquier otra IP (192.168.x.x, 10.x.x.x, etc.)
                    if ip_reg in ["127.0.0.1", "localhost", "::1"]:
                        estado["modo"] = "LOCAL"
                        estado["tipo"] = "MODO LOCAL"
                    else:
                        estado["modo"] = "PRTG"
                        estado["tipo"] = "CONECTADO A PRTG"
                    
                    estado["ultima_ip"] = ip_reg
                    estado["ultima_fecha"] = fecha_reg.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    estado["activo"] = False
                    estado["tipo"] = "INACTIVO (Sin latido reciente)"
                    estado["ultima_fecha"] = fecha_reg.strftime("%Y-%m-%d %H:%M:%S")
                    estado["ultima_ip"] = ip_reg
            else:
                estado["activo"] = False
                estado["tipo"] = "INACTIVO (Sin registros)"
                estado["ultima_fecha"] = "N/A"
                estado["ultima_ip"] = "N/A"
                
        except Exception as e:
            estado["activo"] = False
            estado["tipo"] = f"ERROR: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            conexion.close()
            
    return estado

def mostrar_pantalla():
    contenedor_principal = st.empty()
    
    with contenedor_principal.container():
        cargo = st.session_state.get("cargo", "Analista")
        rol = st.session_state.get("rol", "operador").upper()

        st.markdown("""
            <style>
                [data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] h3 {
                    color: #000000 !important;
                }
                .bienvenida-titulo {
                    color: #003366 !important;
                    font-weight: bold !important;
                    margin-bottom: 0px;
                    text-align: center;
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
                    padding: 10px 14px;
                    border-radius: 6px;
                    color: #137333;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    margin-top: 10px;
                }
                .badge-inactivo {
                    background-color: #fce8e6;
                    border: 1px solid #ea4335;
                    padding: 10px 14px;
                    border-radius: 6px;
                    color: #c5221f;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    margin-top: 10px;
                }
                .badge-local {
                    background-color: #e8f0fe;
                    border: 1px solid #1a73e8;
                    padding: 10px 14px;
                    border-radius: 6px;
                    color: #1557b0;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
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
                    margin-right: 10px;
                    animation: pulse 1.5s infinite;
                }
                .punto-rojo {
                    height: 9px;
                    width: 9px;
                    background-color: #ea4335;
                    border-radius: 50%;
                    display: inline-block;
                    margin-right: 10px;
                }
                .punto-azul {
                    height: 9px;
                    width: 9px;
                    background-color: #1a73e8;
                    border-radius: 50%;
                    display: inline-block;
                    margin-right: 10px;
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0% { transform: scale(0.95); opacity: 0.5; }
                    50% { transform: scale(1.1); opacity: 1; }
                    100% { transform: scale(0.95); opacity: 0.5; }
                }
                .detalle-agente {
                    font-size: 11px;
                    color: #5f6368;
                    margin-top: 4px;
                    font-weight: normal;
                }
                .logo-container {
                    display: flex;
                    justify-content: center;
                    margin-bottom: 15px;
                }
                .logo-container img {
                    max-width: 250px;
                    width: 100%;
                    height: auto;
                }
            </style>
        """, unsafe_allow_html=True)

        # =============================================================
        # AGREGAR IMAGEN DEL LOGO - USANDO get_resource_path()
        # =============================================================
        logo_encontrado = None
        
        # Buscar en múltiples rutas usando get_resource_path
        logo_paths = [
            get_resource_path("SIMPOL.jpg"),
            get_resource_path("logo-banco.jpg"),
            get_resource_path("logo.jpg"),
            get_resource_path("inicio.jpg"),
            os.path.join(os.path.dirname(__file__), "SIMPOL.jpg"),
            os.path.join(os.path.dirname(__file__), "logo-banco.jpg"),
            "SIMPOL.jpg",
            "logo-banco.jpg"
        ]
        
        for path in logo_paths:
            if os.path.exists(path):
                logo_encontrado = path
                break
        
        if logo_encontrado:
            # Usar columnas para desplazar la imagen a la derecha
            col_logo1, col_logo2, col_logo3 = st.columns([1.5, 2, 0.5])
            with col_logo2:
                st.image(logo_encontrado, width=250)
        else:
            # Si no se encuentra la imagen, mostrar un texto alternativo
            st.markdown("""
            <div style="text-align: center; padding: 10px;">
                <h2 style="color: #003366;">SIMPOL</h2>
                <p style="color: #666;">Sistema Inteligente de Monitoreo Permanente Online</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"<h1 class='bienvenida-titulo'>Bienvenido al sistema simpol, estimado {cargo}</h1>", unsafe_allow_html=True)
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
            
            info_agente = obtener_estado_agente_local()
            
            if info_agente["activo"]:
                if info_agente["modo"] == "PRTG":
                    html_agente = f"""
                    <div class="badge-activo">
                        <span class="punto-verde"></span>
                        <span>AGENTE ACTIVO<br>
                        <small style="font-weight:normal; font-size:11px;">MODO: PRTG - Conectado al servidor</small>
                        <br><small class="detalle-agente">Último latido: {info_agente.get('ultima_fecha', 'N/A')}</small>
                        </span>
                    </div>
                    """
                elif info_agente["modo"] == "LOCAL":
                    html_agente = f"""
                    <div class="badge-local">
                        <span class="punto-azul"></span>
                        <span>AGENTE ACTIVO<br>
                        <small style="font-weight:normal; font-size:11px;">MODO: LOCAL - Sin conexión a PRTG</small>
                        <br><small class="detalle-agente">Último latido: {info_agente.get('ultima_fecha', 'N/A')}</small>
                        </span>
                    </div>
                    """
                else:
                    html_agente = f"""
                    <div class="badge-local">
                        <span class="punto-azul"></span>
                        <span>AGENTE ACTIVO<br>
                        <small style="font-weight:normal; font-size:11px;">MODO: {info_agente.get('modo', 'DESCONOCIDO')}</small>
                        <br><small class="detalle-agente">Último latido: {info_agente.get('ultima_fecha', 'N/A')}</small>
                        </span>
                    </div>
                    """
            else:
                ultima_fecha = info_agente.get('ultima_fecha', 'Sin registros')
                html_agente = f"""
                <div class="badge-inactivo">
                    <span class="punto-rojo"></span>
                    <span>AGENTE INACTIVO<br>
                    <small style="font-weight:normal; font-size:11px;">El agente no está enviando datos</small>
                    <br><small class="detalle-agente">Último registro: {ultima_fecha}</small>
                    </span>
                </div>
                """
            st.markdown(html_agente, unsafe_allow_html=True)