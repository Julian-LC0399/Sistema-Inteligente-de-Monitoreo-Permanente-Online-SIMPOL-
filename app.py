import streamlit as st
import os
import sys
import threading
import logging
from datetime import datetime

# === 1. CONFIGURACIÓN DE LOGS ===
logging.basicConfig(
    filename="simpol_debug.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# === 2. PARCHE DE COMPATIBILIDAD PARA EL EJECUTABLE ===
try:
    from streamlit.proto.Common_pb2 import ToolbarMode
    if 'HIDDEN' not in ToolbarMode.keys():
        ToolbarMode.values()['HIDDEN'] = 0
except Exception:
    pass

# === 3. FUNCIONES DE UTILIDAD Y RUTAS ===
def get_resource_path(relative_path):
    """Localiza recursos dentro del paquete .exe o en desarrollo"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# === 4. MOTOR DEL AGENTE (INTEGRADO COMO HILO) ===
def ejecutar_agente_motor():
    """Ejecuta la lógica de monitoreo sin bloquear la interfaz"""
    try:
        logging.info("Intentando importar e iniciar el motor del agente...")
        from agente import iniciar_agente
        iniciar_agente()
    except Exception as e:
        logging.error(f"Error crítico en el hilo del agente: {e}")

def lanzar_hilo_monitoreo():
    """Lanza el hilo del agente una sola vez por sesión de ejecución"""
    if "agente_hilo_activo" not in st.session_state:
        try:
            t = threading.Thread(target=ejecutar_agente_motor, daemon=True)
            t.start()
            st.session_state["agente_hilo_activo"] = True
            logging.info("Hilo del agente lanzado con éxito.")
        except Exception as e:
            logging.error(f"No se pudo crear el hilo: {e}")

# === VERIFICACIÓN DE ALERTAS EXPLICATIVAS EN ESPAÑOL (AISLADA Y REACTIVA) ===
# SOLUCIÓN DE ARQUITECTURA: Se añade run_every=4 para que consulte la BD y refresque 
# el banner de forma asíncrona e independiente del módulo que se esté viendo.
@st.fragment(run_every=4)
def verificar_alertas_globales():
    """
    Escanea la telemetría evaluando cada ID de sensor. Muestra las razones detalladas
    de las alertas cuando un volumen cae por debajo de sus límites. Refresco automático.
    """
    from database import conectar_bd
    
    if "ultima_alerta_persistente" not in st.session_state:
        st.session_state["ultima_alerta_persistente"] = None
    if "color_alerta_persistente" not in st.session_state:
        st.session_state["color_alerta_persistente"] = "#28a745"
    if "bg_alerta_persistente" not in st.session_state:
        st.session_state["bg_alerta_persistente"] = "#d4edda"

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # SOLUCIÓN CRÍTICA: Rompe el aislamiento REPEATABLE READ en la conexión del hilo visual.
            # Sin esto, MySQL devolvería siempre los mismos datos guardados en caché.
            conn.commit()
            
            query = """
                SELECT 
                    m.ip_servidor, s.nombre_alias, m.val_cpu, m.val_ram, 
                    m.val_disco_1, m.val_disco_2, m.val_disco_3, m.val_disco_4, m.val_disco_5,
                    m.val_latencia, m.fecha_registro,
                    s.id_sensor_cpu, s.id_sensor_ram, s.id_sensor_latencia,
                    s.id_sensor_disco_1, s.id_sensor_disco_2, s.id_sensor_disco_3, s.id_sensor_disco_4, s.id_sensor_disco_5,
                    s.letra_disco_1, s.letra_disco_2, s.letra_disco_3, s.letra_disco_4, s.letra_disco_5,
                    h.cpu_advertencia, h.cpu_critico, h.ram_advertencia, h.ram_critico,
                    h.disco_1_advertencia as d1_adv, h.disco_1_critico as d1_crit,
                    h.disco_2_advertencia as d2_adv, h.disco_2_critico as d2_crit,
                    h.disco_3_advertencia as d3_adv, h.disco_3_critico as d3_crit,
                    h.disco_4_advertencia as d4_adv, h.disco_4_critico as d4_crit,
                    h.disco_5_advertencia as d5_adv, h.disco_5_critico as d5_crit
                FROM monitoreo m
                INNER JOIN (
                    SELECT ip_servidor, MAX(fecha_registro) as max_fecha
                    FROM monitoreo
                    WHERE fecha_registro >= NOW() - INTERVAL 5 MINUTE
                    GROUP BY ip_servidor
                ) m_reciente ON m.ip_servidor = m_reciente.ip_servidor AND m.fecha_registro = m_reciente.max_fecha
                INNER JOIN servidores s ON m.ip_servidor = s.ip
                LEFT JOIN (
                    SELECT h1.* FROM historico_umbrales h1
                    INNER JOIN (
                        SELECT ip_servidor, MAX(id_historico) as max_id 
                        FROM historico_umbrales GROUP BY ip_servidor
                    ) h2 ON h1.id_historico = h2.max_id
                ) h ON s.ip = h.ip_servidor
                ORDER BY s.nombre_alias ASC
            """
            cursor.execute(query)
            registros_recientes = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if registros_recientes:
                html_sensores = []
                tiene_critico = False
                tiene_advertencia = False
                
                for alr in registros_recientes:
                    ip_nodo = alr['ip_servidor']
                    alias = alr['nombre_alias']

                    c_cpu_adv = float(alr['cpu_advertencia']) if alr['cpu_advertencia'] is not None else 70.0
                    c_cpu_crit = float(alr['cpu_critico']) if alr['cpu_critico'] is not None else 85.0
                    
                    if ip_nodo == "10.10.1.133":
                        c_ram_adv = float(alr['ram_advertencia']) if alr['ram_advertencia'] is not None else 1.5
                        c_ram_crit = float(alr['ram_critico']) if alr['ram_critico'] is not None else 0.5
                    else:
                        c_ram_adv = float(alr['ram_advertencia']) if alr['ram_advertencia'] is not None else 8.0
                        c_ram_crit = float(alr['ram_critico']) if alr['ram_critico'] is not None else 4.0

                    # 1. EVALUACIÓN DE CPU
                    if alr['id_sensor_cpu'] and int(alr['id_sensor_cpu']) > 0:
                        id_s = alr['id_sensor_cpu']
                        v = float(alr['val_cpu'])
                        if v >= c_cpu_crit:
                            html_sensores.append(f"<span style='color:#dc3545; font-weight:bold;'>🔴 ID:{id_s} CPU ({alias}): {v}%</span>")
                            tiene_critico = True
                        elif v >= c_cpu_adv:
                            html_sensores.append(f"<span style='color:#b58105; font-weight:bold;'>🟡 ID:{id_s} CPU ({alias}): {v}%</span>")
                            tiene_advertencia = True
                        else:
                            html_sensores.append(f"<span style='color:#28a745;'>🟢 ID:{id_s} CPU ({alias}): {v}%</span>")

                    # 2. EVALUACIÓN DE RAM
                    if alr['id_sensor_ram'] and int(alr['id_sensor_ram']) > 0:
                        id_s = alr['id_sensor_ram']
                        v = float(alr['val_ram'])
                        if v <= c_ram_crit:
                            html_sensores.append(f"<span style='color:#dc3545; font-weight:bold;'>🔴 ID:{id_s} RAM ({alias}): {v}GB</span>")
                            tiene_critico = True
                        elif v <= c_ram_adv:
                            html_sensores.append(f"<span style='color:#b58105; font-weight:bold;'>🟡 ID:{id_s} RAM ({alias}): {v}GB</span>")
                            tiene_advertencia = True
                        else:
                            html_sensores.append(f"<span style='color:#28a745;'>🟢 ID:{id_s} RAM ({alias}): {v}GB</span>")

                    # 3. EVALUACIÓN DE DISCOS (Mapeado directo)
                    for idx in range(1, 6):
                        if alr[f'id_sensor_disco_{idx}'] and int(alr[f'id_sensor_disco_{idx}']) > 0:
                            id_s = alr[f'id_sensor_disco_{idx}']
                            v = float(alr[f'val_disco_{idx}'])
                            letra = alr.get(f'letra_disco_{idx}') or f"D{idx}"
                            
                            u_adv = float(alr[f'd{idx}_adv']) if alr[f'd{idx}_adv'] is not None else 40.0
                            u_crit = float(alr[f'd{idx}_crit']) if alr[f'd{idx}_crit'] is not None else 15.0
                            
                            # Ajuste dinámico si es volumen C de sistema
                            if str(letra).upper() == "C":
                                u_adv = 25.0
                                u_crit = 10.0

                            if v <= u_crit:
                                html_sensores.append(f"<span style='color:#dc3545; font-weight:bold;'>🔴 ID:{id_s} Disco {letra} ({alias}): {v}GB</span>")
                                tiene_critico = True
                            elif v <= u_adv:
                                html_sensores.append(f"<span style='color:#b58105; font-weight:bold;'>🟡 ID:{id_s} Disco {letra} ({alias}): {v}GB</span>")
                                tiene_advertencia = True
                            else:
                                html_sensores.append(f"<span style='color:#28a745;'>🟢 ID:{id_s} Disco {letra} ({alias}): {v}GB</span>")

            if html_sensores:
                st.session_state["ultima_alerta_persistente"] = " &nbsp;|&nbsp; ".join(html_sensores)
                if tiene_critico:
                    st.session_state["color_alerta_persistente"] = "#cc0000"
                    st.session_state["bg_alerta_persistente"] = "#ffcccc"
                elif tiene_advertencia:
                    st.session_state["color_alerta_persistente"] = "#856404"
                    st.session_state["bg_alerta_persistente"] = "#fff3cd"
                else:
                    st.session_state["color_alerta_persistente"] = "#28a745"
                    st.session_state["bg_alerta_persistente"] = "#d4edda"
            else:
                st.session_state["ultima_alerta_persistente"] = "⚪ Sin telemetría reciente de sensores en los últimos 5 minutos."
                st.session_state["color_alerta_persistente"] = "#6c757d"
                st.session_state["bg_alerta_persistente"] = "#e2e3e5"

        except Exception as e:
            logging.error(f"Error formateando la alerta explicativa de discos: {e}")

    # --- INYECCIÓN GRÁFICA EN PANTALLA ---
    if "ultima_alerta_persistente" in st.session_state and st.session_state["ultima_alerta_persistente"] is not None:
        color_borde = st.session_state["color_alerta_persistente"]
        color_fondo = st.session_state["bg_alerta_persistente"]
        
        if color_borde == "#cc0000":
            titulo_banner = "🚨 ESTADO DE SENSORES EN TIEMPO REAL (NIVEL DE RIESGO: ALTO)"
        elif color_borde == "#856404":
            titulo_banner = "⚠️ ESTADO DE SENSORES EN TIEMPO REAL (NIVEL DE RIESGO: PREVENTIVO)"
        else:
            titulo_banner = "🟢 ESTADO DE SENSORES EN TIEMPO REAL (INFRAESTRUCTURA SALUDABLE)"

        st.markdown(f"""
            <div style="background-color: {color_fondo}; padding: 12px; border-radius: 4px; 
                        border-left: 6px solid {color_borde}; margin-bottom: 20px; border-top: 1px solid #ddd; border-right: 1px solid #ddd; border-bottom: 1px solid #ddd;">
                <div style="color: {color_borde}; font-weight: bold; font-size: 13px; text-align: left; margin-bottom: 6px; text-transform: uppercase;">
                    {titulo_banner}
                </div>
                <div style="color: #222222; font-size: 12px; font-family: monospace; line-height: 1.8; background: rgba(255,255,255,0.6); padding: 8px; border-radius: 2px;">
                    {st.session_state["ultima_alerta_persistente"]}
                </div>
            </div>
        """, unsafe_allow_html=True)

# === 5. CONFIGURACIÓN DE PÁGINA Y ESTILOS ===
st.set_page_config(
    page_title="SIMPOL - Banco Caroní",
    layout="wide",
    initial_sidebar_state="expanded"
)

css_path = get_resource_path("style.css")
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass

# === 6. FLUJO PRINCIPAL PROTEGIDO ===
import auth
from menu import generar_menu

def main():
    params = st.query_params
    
    # 1. Recuperar Autenticación desde la URL tras F5
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = True if params.get("s") == "1" else False
    
    if params.get("rol") and "rol" not in st.session_state:
        st.session_state["rol"] = params.get("rol")
    if params.get("uid") and "user_id" not in st.session_state:
        st.session_state["user_id"] = int(params.get("uid"))
    if params.get("c") and "cargo" not in st.session_state:
        st.session_state["cargo"] = params.get("c")
    if params.get("u") and "user_actual" not in st.session_state:
        st.session_state["user_actual"] = params.get("u")

    if not st.session_state.get("autenticado", False):
        auth.mostrar_login()
    else:
        lanzar_hilo_monitoreo()
        
        # 2. Recuperar la sección exacta
        if "seccion_actual" not in st.session_state:
            st.session_state["seccion_actual"] = params.get("p", "🏠 Inicio")
        
        # 3. Blindaje de Variables en URL (Para aguantar el F5 en caliente)
        st.query_params["s"] = "1"
        st.query_params["p"] = st.session_state["seccion_actual"]
        st.query_params["rol"] = st.session_state.get("rol", "operador")
        st.query_params["uid"] = str(st.session_state.get("user_id", 1))
        st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
        st.query_params["c"] = st.session_state.get("cargo", "Analista")
        
        generar_menu()
        
        # RENDERIZADO REACTIVO INDEPENDIENTE DEL BANNER DE ALERTAS
        verificar_alertas_globales()
        
        seleccion = st.session_state.get("seccion_actual", "🏠 Inicio")
        placeholder_principal = st.empty()

        with placeholder_principal.container():
            try:
                if seleccion == "🏠 Inicio":
                    from modulos import inicio
                    inicio.mostrar_pantalla()
                elif seleccion == "🖥️ Servidores":
                    from modulos import servidores
                    servidores.mostrar_tabla_servidores(rol_usuario=st.session_state.get("rol"))
                elif seleccion == "📊 Monitoreo en vivo":
                    from modulos import monitoreo
                    monitoreo.mostrar_pantalla()
                elif seleccion == "📈 Capacity planning":
                    from modulos import capacity
                    id_usuario = st.session_state.get("user_id", 1)
                    login_usuario = st.session_state.get("user_actual", "Sistema")
                    cargo_analista = st.session_state.get("cargo", "Analista")
                    
                    capacity.mostrar_pantalla(
                        usuario_id=id_usuario, 
                        usuario_login=login_usuario, 
                        nombre_analista=cargo_analista
                    )
                elif seleccion == "🔔 Alertas":
                    from modulos import alertas
                    alertas.mostrar_pantalla(usuario_id=st.session_state.get("user_id", 1), rol_usuario=st.session_state.get("rol", "operador"))
                elif seleccion == "📄 Reportes":
                    from modulos import reportes
                    reportes.mostrar_pantalla(st.session_state.get("cargo", "Analista"), st.session_state.get("user_id", 1))
                elif seleccion == "👥 Gestión de usuarios":
                    from modulos import gestion
                    gestion.mostrar_pantalla(st.session_state.get("user_actual", "Sistema"), st.session_state.get("user_id", 1))
                elif seleccion == "🕵️ Auditoría":
                    from modulos import auditoria
                    auditoria.mostrar_pantalla()
            except Exception as e:
                logging.error(f"Error crítico cargando sección {seleccion}: {e}")
                st.error(f"⚠️ Error en la sección {seleccion}. Verifique logs.")

if __name__ == "__main__":
    main()