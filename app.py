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
        
        # =====================================================================
        # MEJORADO: DETECCIÓN Y PRIORIZACIÓN DE RE-DIRECCIÓN EXTERNA (URL -> STATE)
        # =====================================================================
        url_pestaña = params.get("p")
        
        # Primero, sincronizamos si se forzó un cambio directo desde servidores.py usando 'navegacion_principal'
        if "navegacion_principal" in st.session_state:
            st.session_state["seccion_actual"] = st.session_state["navegacion_principal"]
            # Limpiamos para evitar loops
            del st.session_state["navegacion_principal"] 
        
        # Inicialización base estándar
        elif "seccion_actual" not in st.session_state:
            st.session_state["seccion_actual"] = url_pestaña if url_pestaña else "🏠 Inicio"

        # Interceptamos cambios por parámetros url ordinarios
        elif url_pestaña and url_pestaña != st.session_state["seccion_actual"]:
            if st.session_state.get("nav_radio") != st.session_state["seccion_actual"]:
                st.session_state["seccion_actual"] = url_pestaña
        
        # =====================================================================
        # PERSISTENCIA DE PARÁMETROS EN URL (POST-EVALUACIÓN DE ESTADO)
        # =====================================================================
        st.query_params["s"] = "1"
        st.query_params["p"] = st.session_state["seccion_actual"]
        st.query_params["rol"] = st.session_state.get("rol", "operador")
        st.query_params["uid"] = str(st.session_state.get("user_id", 1))
        st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
        st.query_params["c"] = st.session_state.get("cargo", "Analista")
        
        # Construcción aislada del menú lateral
        generar_menu()
        
        # RENDERIZADO DEL MÓDULO CORRESPONDIENTE
        seleccion = st.session_state["seccion_actual"]
        placeholder_principal = st.empty()

        with placeholder_principal.container():
            try:
                if seleccion == "🏠 Inicio":
                    from modulos import inicio
                    inicio.mostrar_pantalla()
                elif seleccion == "🖥️ Servidores":
                    from modulos import servidores
                    servidores.mostrar_tabla_servidores(rol_usuario=st.session_state.get("rol"))
                elif seleccion == "🖥️ Monitoreo en vivo":
                    from modulos import monitoreo
                    monitoreo.mostrar_pantalla()
                elif seleccion == "📈 Capacity planning":
                    from modulos import capacity
                    capacity.mostrar_pantalla(
                        usuario_id=st.session_state.get("user_id", 1), 
                        usuario_login=st.session_state.get("user_actual", "Sistema"), 
                        nombre_analista=st.session_state.get("cargo", "Analista")
                    )
                elif seleccion == "🔔 Alertas":
                    from modulos import alertas
                    alertas.mostrar_pantalla(
                        nombre_analista=st.session_state.get("cargo", "Analista"),
                        usuario_id=st.session_state.get("user_id", 1),
                        usuario_login=st.session_state.get("user_actual", "Sistema")
                    )
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