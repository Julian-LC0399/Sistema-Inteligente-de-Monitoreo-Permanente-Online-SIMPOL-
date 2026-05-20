import streamlit as st
import os
import sys
import threading
import logging
from datetime import datetime

# === 1. CONFIGURACIÓN DE LOGS (Para diagnóstico en el Banco) ===
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

# === FUNCIÓN INTEGRADA: VERIFICACIÓN GLOBAL DE ALERTAS SIMPOL ===
def verificar_alertas_globales():
    """
    Escanea la telemetría en tiempo real buscando servidores saturados.
    Consolida las alertas en una ventana de 5 minutos para evitar saturación de pantalla.
    """
    from database import conectar_bd
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Ventana móvil de 5 minutos agrupando por IP para consolidar en un solo mensaje
            query = """
                SELECT COUNT(DISTINCT ip_servidor) AS total_criticos
                FROM monitoreo 
                WHERE estado_sistema = 'CRÍTICO' 
                  AND fecha_registro >= NOW() - INTERVAL 5 MINUTE
            """
            cursor.execute(query)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if res and res['total_criticos'] > 0:
                total = res['total_criticos']
                plural = "SERVIDORES PRESENTAN" if total > 1 else "SERVIDOR PRESENTA"
                
                # Inyección visual elegante en la cabecera (Estilo Warning Corporativo)
                st.markdown(f"""
                    <div style="background-color: #ffcccc; padding: 14px; border-radius: 4px; 
                                border-left: 6px solid #cc0000; margin-bottom: 20px; text-align: center;">
                        <span style="color: #cc0000; font-weight: bold; font-size: 15px;">
                            🚨 ALERTA CRÍTICA DE INFRAESTRUCTURA: ¡Atención! {total} {plural} saturación severa en los últimos 5 minutos.
                        </span>
                        <br>
                        <small style="color: #555;">Por favor, verifique el módulo de 'Monitoreo en vivo' para identificar los nodos afectados.</small>
                    </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            logging.error(f"Error en escaneo global de alertas: {e}")

# === 5. CONFIGURACIÓN DE PÁGINA Y ESTILOS ===
st.set_page_config(
    page_title="SIMPOL - Banco Caroní",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CARGA DEL CSS GLOBAL Y PARCHE DE INYECCIÓN INSTITUCIONAL ---
css_path = get_resource_path("style.css")
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_contenido = f.read()
            
        css_institucional = """
        /* ==========================================================================
           REFUERZO DE IDENTIDAD CORPORATIVA - BANCO CARONÍ (ESTILOS GLOBALES)
           ========================================================================== */
        
        div.stButton > button {
            background-color: #003366 !important;
            color: #FFFFFF !important;
            border: 1px solid #003366 !important;
            border-radius: 0px !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
            height: 42px !important;
            transition: all 0.3s ease-in-out !important;
        }
        
        div.stButton > button p {
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        
        div.stButton > button:hover {
            background-color: #001f3f !important;
            border: 1px solid #FFCC00 !important;
            color: #FFCC00 !important;
        }
        
        div.stButton > button:hover p {
            color: #FFCC00 !important;
        }

        div[data-testid="stForm"] div.stButton > button {
            background-color: #003366 !important;
            color: #FFFFFF !important;
            border: 1px solid #003366 !important;
            border-radius: 0px !important;
        }
        
        div[data-testid="stForm"] div.stButton > button p {
            color: #FFFFFF !important;
        }
        
        div[data-testid="stForm"] div.stButton > button:hover {
            background-color: #001f3f !important;
            border: 1px solid #FFCC00 !important;
        }
        
        div[data-testid="stForm"] div.stButton > button:hover p {
            color: #FFCC00 !important;
        }
        """
        st.markdown(f"<style>{css_contenido}\n{css_institucional}</style>", unsafe_allow_html=True)
        
    except Exception as e:
        logging.warning(f"No se pudo cargar el CSS: {e}")

# === 6. FLUJO PRINCIPAL ===
import auth
from menu import generar_menu

def main():
    # --- REPARACIÓN DE F5: RECUPERACIÓN DE DATOS DESDE URL ---
    params = st.query_params
    
    if "autenticado" not in st.session_state:
        if params.get("s") == "1":
            st.session_state["autenticado"] = True
            st.session_state["seccion_actual"] = params.get("p", "🏠 Inicio")
            st.session_state["rol"] = params.get("r")
            st.session_state["user_id"] = params.get("uid")
            st.session_state["nombre_analista"] = params.get("n")
        else:
            st.session_state["autenticado"] = False

    # Pantalla de Login
    if not st.session_state["autenticado"]:
        auth.mostrar_login()
    else:
        lanzar_hilo_monitoreo()

        if "seccion_actual" not in st.session_state:
            st.session_state["seccion_actual"] = params.get("p", "🏠 Inicio")
        
        # Invocamos la barra lateral de navegación
        generar_menu()
        
        # === INYECCIÓN ESTRATÉGICA DE ALERTAS EN TIEMPO REAL VIVO ===
        # Se ejecuta de cabecera superior en toda la app antes de cargar el módulo activo
        verificar_alertas_globales()
        
        # Recuperamos la sección activa modificada por el control st.radio interno del menú
        seleccion = st.session_state.get("seccion_actual", "🏠 Inicio")
        
        # ACTUALIZACIÓN DE PERSISTENCIA EN URL
        st.query_params.update({
            "s": "1", 
            "p": seleccion, 
            "r": st.session_state.get("rol", ""),
            "uid": st.session_state.get("user_id", ""),
            "n": st.session_state.get("nombre_analista", "")
        })
        
        placeholder_principal = st.empty()

        with placeholder_principal.container():
            try:
                if seleccion == "🏠 Inicio":
                    from modulos import inicio
                    inicio.mostrar_pantalla()
                
                elif seleccion == "🖥️ Servidores":
                    from modulos import servidores
                    rol_actual = st.session_state.get("rol")
                    servidores.mostrar_tabla_servidores(rol_usuario=rol_actual)
                
                elif seleccion == "📊 Monitoreo en vivo":
                    from modulos import monitoreo
                    monitoreo.mostrar_pantalla()
                    
                elif seleccion == "📈 Capacity planning":
                    from modulos import capacity
                    capacity.mostrar_pantalla(
                        st.session_state.get("nombre_analista"), 
                        st.session_state.get("user_id")
                    )
                    
                elif seleccion == "🔔 Alertas":
                    from modulos import alertas
                    # SE ADAPTA LLAMADO: Se pasan parámetros de control para unificar la pantalla limpia
                    rol_actual = st.session_state.get("rol", "OPERADOR")
                    uid_actual = st.session_state.get("user_id", 1)
                    alertas.mostrar_pantalla(usuario_id=uid_actual, rol_usuario=rol_actual)
                    
                elif seleccion == "📄 Reportes":
                    from modulos import reportes
                    reportes.mostrar_pantalla(
                        st.session_state.get("nombre_analista"), 
                        st.session_state.get("user_id")
                    )
                    
                elif seleccion == "👥 Gestión de usuarios":
                    from modulos import gestion
                    gestion.mostrar_pantalla(
                        st.session_state.get("nombre_analista"), 
                        st.session_state.get("user_id")
                    )
                    
                elif seleccion == "🕵️ Auditoría":
                    from modulos import auditoria
                    auditoria.mostrar_pantalla()

            except Exception as e:
                logging.error(f"Error cargando sección {seleccion}: {e}")
                st.error(f"⚠️ Error en {seleccion}. Revisa simpol_debug.log")

if __name__ == "__main__":
    main()