import streamlit as st
import os
import sys
import threading
import logging

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
            
        # Añadimos al final del estilo global las reglas forzadas para los botones del Banco
        # Esto asegura que ningún componente nativo rompa la identidad visual.
        css_institucional = """
        /* ==========================================================================
           REFUERZO DE IDENTIDAD CORPORATIVA - BANCO CARONÍ (ESTILOS GLOBALES)
           ========================================================================== */
        
        /* Botones de acción general (Nativos y en columnas) */
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
        
        /* Asegurar visibilidad del texto en los botones */
        div.stButton > button p {
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        
        /* Comportamiento Hover general (Mouse encima) */
        div.stButton > button:hover {
            background-color: #001f3f !important;
            border: 1px solid #FFCC00 !important;
            color: #FFCC00 !important;
        }
        
        div.stButton > button:hover p {
            color: #FFCC00 !important;
        }

        /* Botones específicos dentro de contenedores st.form */
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
        # Si el F5 borró la sesión pero la URL dice que estábamos autenticados
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

        # Aseguramos la persistencia interna en session_state antes de invocar el menú
        if "seccion_actual" not in st.session_state:
            st.session_state["seccion_actual"] = params.get("p", "🏠 Inicio")
        
        # Invocamos la función sin argumentos tal como está definida en menu.py
        generar_menu()
        
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
                    alertas.mostrar_pantalla()
                    
                elif seleccion == "📄 Reportes":
                    from modulos import reportes
                    reportes.mostrar_pantalla(
                        st.session_state.get("nombre_analista"), 
                        st.session_state.get("user_id")
                    )
                    
                elif seleccion == "👥 Gestión de usuarios":
                    from modulos import gestion
                    # CORRECCIÓN DE PARÁMETRO: Se cambia "user_actual" por "nombre_analista" para coincidir con la persistencia
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