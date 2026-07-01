import streamlit as st
import os
import sys
import logging
from datetime import datetime
import webbrowser
import base64

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

def get_favicon_base64():
    """Genera un favicon en base64 desde un archivo o crea uno por defecto"""
    try:
        favicon_path = get_resource_path("favicon.ico")
        if os.path.exists(favicon_path):
            with open(favicon_path, "rb") as f:
                icon_data = f.read()
                return base64.b64encode(icon_data).decode()
    except Exception as e:
        logging.error(f"Error cargando favicon: {e}")
    
    # Si no existe el archivo, creamos un icono simple en base64
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" rx="15" fill="#003366"/>
        <text x="50" y="68" font-size="50" text-anchor="middle" fill="white">🏦</text>
        <text x="50" y="90" font-size="12" text-anchor="middle" fill="#FFD700">SIMPOL</text>
    </svg>'''
    return base64.b64encode(svg_icon.encode()).decode()

# === 4. CONFIGURACIÓN DE PÁGINA Y ESTILOS CRÍTICOS ===
st.set_page_config(
    page_title="SIMPOL - Banco Caroní",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# AGREGAR FAVICON PERSONALIZADO EN EL HEADER
favicon_b64 = get_favicon_base64()
st.markdown(f'''
    <link rel="icon" type="image/x-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
    <link rel="shortcut icon" type="image/x-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
    <link rel="apple-touch-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
''', unsafe_allow_html=True)

# SE GARANTIZA LA INYECCIÓN TEMPRANA: Forzar la carga de style.css antes de la lógica de ruteo
css_path = get_resource_path("style.css")
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        logging.error(f"Error cargando style.css: {e}")

# BLINDAJE VISUAL INSTITUCIONAL Y ELIMINACIÓN DE MARCAS DE STREAMLIT
st.markdown("""
    <style>
        /* 1. Mantener barra lateral fija y abierta */
        section[data-testid="stSidebar"] {
            display: flex !important;
            visibility: visible !important;
            min-width: 320px !important;
            max-width: 320px !important;
            transform: none !important;
            transition: none !important;
        }
        
        /* Ocultar botones de colapso de la barra lateral */
        section[data-testid="stSidebar"] button {
            display: none !important;
        }
        [data-testid="stSidebar"] [id^="collapsed-control"],
        section[data-testid="stSidebar"] button[title="Collapse sidebar"],
        section[data-testid="stSidebar"] svg {
            display: none !important;
        }
        [data-testid="sidebar-collapsed-control"],
        [data-testid="sidebar-collapsed-control"] button {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* 2. OCULTAR MENÚ DE 3 PUNTOS, BOTÓN DE DEPLOY Y ENCABEZADO SUPERIOR */
        [data-testid="stHeader"], 
        header, 
        .stActionButton, 
        #MainMenu, 
        footer {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 3. OCULTAR EL TEXTO "Press Enter to apply" EN TODOS LOS CAMPOS DE TEXTO */
        [data-testid="stTextInputInstructions"],
        [data-testid="stNumberInputInstructions"],
        [data-testid="stTextAreaInstructions"],
        .stTextInput small,
        .stTextInput div[data-testid="InputInstructions"] {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
            padding: 0px !important;
        }
        
        /* 4. OCULTAR TOOLBARS SECUNDARIOS */
        [data-testid="stToolbar"] {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* Ajustar el contenedor de la app */
        .stAppViewMain {
            margin-left: 0px !important;
            padding-top: 20px !important;
        }
        
        /* Mejorar la barra de título del navegador */
        title {
            color: #003366 !important;
        }
    </style>
""", unsafe_allow_html=True)

# PARCHE ANTI-ENTER FUNCIONAL
st.markdown("""
    <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.keyCode === 13) {
                const target = e.target;
                if (target.tagName === 'INPUT' && target.type !== 'submit' && target.type !== 'button') {
                    e.preventDefault();
                    return false;
                }
            }
        }, true);
        
        // FORZAR QUE LOS ENLACES ABRAN EN EL NAVEGADOR
        document.addEventListener('click', function(e) {
            const target = e.target.closest('a');
            if (target && target.href) {
                if (target.target !== '_blank') {
                    target.target = '_blank';
                }
            }
        });
    </script>
""", unsafe_allow_html=True)

# === 5. FLUJO PRINCIPAL PROTEGIDO ===
import auth
from menu import generar_menu

def gestionar_limpieza_filtros(seccion_destino):
    """
    Controla los estados de los filtros de monitoreo, usuarios, servidores,
    reportes, capacity planning, alertas y umbrales.
    """
    # BLINDAJE ULTRA-CRÍTICO: Si en la URL viene el parámetro "srv" o ya estamos en monitoreo, 
    # abortamos cualquier purga destructiva para no romper la redirección activa.
    if "srv" in st.query_params or seccion_destino == "🖥️ Monitoreo en vivo" or st.query_params.get("p") == "🖥️ Monitoreo en vivo":
        return

    if seccion_destino != "🖥️ Monitoreo en vivo":
        if "filtro_monitoreo_nombre" in st.session_state:
            st.session_state["filtro_monitoreo_nombre"] = "-- Seleccione un Servidor--"
        if "filtro_monitoreo_sensor" in st.session_state:
            st.session_state["filtro_monitoreo_sensor"] = "-- Seleccione un Sensor --"
        if "servidor_seleccionado" in st.session_state:
            st.session_state["servidor_seleccionado"] = "-- Seleccione un Servidor --"

    if seccion_destino != "👥 Gestión de usuarios":
        if "filtro_analista" in st.session_state:
            st.session_state["filtro_analista"] = "-- Seleccione un Analista --"
        if "accion_personal" in st.session_state:
            st.session_state["accion_personal"] = None

    if seccion_destino != "🖥️ Servidores":
        if "filtro_servidor_nombre" in st.session_state:
            st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
        if "accion_infra" in st.session_state:
            st.session_state["accion_infra"] = None
        if "filtro_adicional_nombre" in st.session_state:
            st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
        if "accion_adicional" in st.session_state:
            st.session_state["accion_adicional"] = None

    if seccion_destino != "📄 Reportes":
        st.session_state["rep_listo"] = False
        st.session_state["rep_csv"] = None
        st.session_state["rep_pdf"] = None
        st.session_state["rep_name_csv"] = ""
        st.session_state["rep_name_pdf"] = ""
        st.session_state["servidor_seleccionado_reporte"] = "-- Seleccione un Servidor --"
        if "key_semilla_selectbox" in st.session_state:
            st.session_state["key_semilla_selectbox"] += 1

    if seccion_destino != "📈 Capacity planning":
        if "servidor_seleccionado_capacity" in st.session_state:
            st.session_state["servidor_seleccionado_capacity"] = "-- Seleccione un Servidor --"
        if "metrica_seleccionada_capacity" in st.session_state:
            st.session_state["metrica_seleccionada_capacity"] = "CPU"
        if "dias_prediccion_capacity" in st.session_state:
            st.session_state["dias_prediccion_capacity"] = 30

    if seccion_destino != "🔔 Alertas":
        if "sb_alerta_srv" in st.session_state:
            st.session_state["sb_alerta_srv"] = "-- Seleccione un Servidor para empezar --"
        if "filtro_alerta_criticidad" in st.session_state:
            st.session_state["filtro_alerta_criticidad"] = "-- Todas --"
        if "filtro_alerta_estado" in st.session_state:
            st.session_state["filtro_alerta_estado"] = "No Resueltas"

    # 🔥 NUEVO: Limpieza de filtros de Umbrales al salir
    if seccion_destino != "⚙️ Umbrales":
        if "filtro_umbral_servidor" in st.session_state:
            st.session_state["filtro_umbral_servidor"] = "-- Seleccione un Servidor --"
        if "filtro_umbral_componente" in st.session_state:
            st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"
        if "justificacion_umbrales" in st.session_state:
            # No eliminamos, solo reseteamos
            pass

def main():
    params = st.query_params
    
    # =============================================================
    # CAPTURAR PARÁMETRO SRV DE LA URL
    # =============================================================
    srv_desde_url = params.get("srv")
    if srv_desde_url:
        st.session_state["_srv_redirect"] = srv_desde_url
        st.session_state["_srv_captured"] = True
        logging.info(f"🔴 SRV capturado desde URL: {srv_desde_url}")
        
        st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
        st.session_state["nav_radio"] = "🖥️ Monitoreo en vivo"
        st.session_state["filtro_monitoreo_nombre"] = srv_desde_url
        st.session_state["servidor_seleccionado"] = srv_desde_url
        
        try:
            del st.query_params["srv"]
        except:
            pass
    
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

    if st.session_state.get("autenticado") and not params.get("s"):
        st.query_params["s"] = "1"
        st.query_params["rol"] = st.session_state.get("rol", "operador")
        st.query_params["uid"] = str(st.session_state.get("user_id", 1))
        st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
        st.query_params["c"] = st.session_state.get("cargo", "Analista")
        st.query_params["p"] = st.session_state.get("seccion_actual", "🏠 Inicio")
        st.rerun()

    if not st.session_state.get("autenticado", False):
        if any(k in params for k in ["s", "rol", "uid", "u", "c", "p"]):
            st.query_params.clear()
        auth.mostrar_login()
    else:
        placeholder_principal = st.empty()
        
        # --- LÓGICA DE RUTAS Y SINCRONIZACIÓN ---
        url_pestaña = params.get("p")
        
        if "navegacion_principal" in st.session_state:
            destino = st.session_state["navegacion_principal"]
            st.session_state["seccion_actual"] = destino
            st.session_state["nav_radio"] = destino  
            del st.session_state["navegacion_principal"] 
        elif "seccion_actual" not in st.session_state:
            st.session_state["seccion_actual"] = url_pestaña if url_pestaña else "🏠 Inicio"
        elif url_pestaña and url_pestaña != st.session_state["seccion_actual"]:
            if st.session_state.get("nav_radio") != st.session_state["seccion_actual"]:
                st.session_state["seccion_actual"] = url_pestaña
                st.session_state["nav_radio"] = url_pestaña

        if st.session_state.get("nav_radio") and st.session_state["nav_radio"] != st.session_state["seccion_actual"]:
            st.session_state["seccion_actual"] = st.session_state["nav_radio"]
        
        # =============================================================
        # VERIFICAR REDIRECCIÓN PENDIENTE
        # =============================================================
        if "_srv_redirect" in st.session_state and st.session_state["_srv_redirect"]:
            if st.session_state["seccion_actual"] == "🖥️ Monitoreo en vivo":
                if not st.session_state.get("_srv_processed", False):
                    st.session_state["filtro_monitoreo_nombre"] = st.session_state["_srv_redirect"]
                    st.session_state["servidor_seleccionado"] = st.session_state["_srv_redirect"]
                    st.session_state["_srv_processed"] = True
                    logging.info(f"🟢 SRV aplicado a monitoreo: {st.session_state['_srv_redirect']}")
        
        gestionar_limpieza_filtros(st.session_state["seccion_actual"])
        
        generar_menu()
        
        # =============================================================
        # SINCRONIZAR URL CON SESSION_STATE
        # =============================================================
        if params.get("p") != st.session_state["seccion_actual"]:
            placeholder_principal.empty()  
            st.query_params["p"] = st.session_state["seccion_actual"]
            st.rerun()  
        
        st.query_params["s"] = "1"
        st.query_params["rol"] = st.session_state.get("rol", "operador")
        st.query_params["uid"] = str(st.session_state.get("user_id", 1))
        st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
        st.query_params["c"] = st.session_state.get("cargo", "Analista")
        
        seleccion = st.session_state["seccion_actual"]

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
                    monitoreo.mostrar_pantalla(
                        nombre_analista=st.session_state.get("cargo", "Analista"),
                        usuario_id=st.session_state.get("user_id", 1),
                        usuario_login=st.session_state.get("user_actual", "Sistema")
                    )
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
                # 🔥 NUEVO: Sección de Umbrales
                elif seleccion == "⚙️ Umbrales":
                    from modulos import umbrales
                    umbrales.mostrar_pantalla(
                        nombre_analista=st.session_state.get("cargo", "Analista"),
                        usuario_id=st.session_state.get("user_id", 1),
                        usuario_login=st.session_state.get("user_actual", "Sistema")
                    )
                elif seleccion == "📄 Reportes":
                    from modulos import reportes
                    reportes.mostrar_pantalla(
                        nombre_analista=st.session_state.get("cargo", "Analista"),
                        usuario_id=st.session_state.get("user_id", 1),
                        usuario_login=st.session_state.get("user_actual", "Sistema")
                    )
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