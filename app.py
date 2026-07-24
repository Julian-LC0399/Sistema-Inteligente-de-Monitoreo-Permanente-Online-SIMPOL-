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

favicon_b64 = get_favicon_base64()
st.markdown(f'''
    <link rel="icon" type="image/x-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
    <link rel="shortcut icon" type="image/x-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
    <link rel="apple-touch-icon" href="data:image/x-icon;base64,{favicon_b64}"/>
''', unsafe_allow_html=True)

css_path = get_resource_path("style.css")
if os.path.exists(css_path):
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        logging.error(f"Error cargando style.css: {e}")

st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: flex !important;
            visibility: visible !important;
            min-width: 320px !important;
            max-width: 320px !important;
            transform: none !important;
            transition: none !important;
        }
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
        [data-testid="stHeader"], 
        header, 
        .stActionButton, 
        #MainMenu, 
        footer {
            visibility: hidden !important;
            display: none !important;
        }
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
        [data-testid="stToolbar"] {
            visibility: hidden !important;
            display: none !important;
        }
        .stAppViewMain {
            margin-left: 0px !important;
            padding-top: 20px !important;
        }
        title {
            color: #003366 !important;
        }
    </style>
""", unsafe_allow_html=True)

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

def limpiar_estado_capacity():
    keys_to_clear = [
        'p1_servidor', 'p1_metrica', 'p1_dias', 'p1_ajuste',
        'p1_filtros_aplicados', 'p1_reporte_generado',
        'p2_servidor_seleccionado', 'p2_metrica_filtro',
        'p2_formato_filtro', 'p2_mostrar_tabla',
        'modulo_capacity_activo'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def gestionar_limpieza_filtros(seccion_destino):
    # Si es monitoreo y hay un SRV pendiente O filtro aplicado, NO LIMPIAR
    if seccion_destino == "🖥️ Monitoreo en vivo":
        if st.session_state.get("_srv_redirect") or st.session_state.get("filtro_aplicado_tab1", False):
            return
    
    if "srv" in st.query_params or seccion_destino == "🖥️ Monitoreo en vivo" or st.query_params.get("p") == "🖥️ Monitoreo en vivo":
        return

    tab_actual = None
    if seccion_destino == "🖥️ Servidores":
        tab_actual = st.query_params.get("tab_servidores")
    elif seccion_destino == "👥 Gestión de usuarios":
        tab_actual = st.query_params.get("tab_gestion")
    elif seccion_destino == "📈 Capacity planning":
        tab_actual = st.query_params.get("tab_capacity")

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
        limpiar_estado_capacity()
        if "servidor_seleccionado_capacity" in st.session_state:
            st.session_state["servidor_seleccionado_capacity"] = "-- Seleccione un Servidor --"
        if "metrica_seleccionada_capacity" in st.session_state:
            st.session_state["metrica_seleccionada_capacity"] = "CPU"
        if "dias_prediccion_capacity" in st.session_state:
            st.session_state["dias_prediccion_capacity"] = 30
        if "temp_servidor_capacity" in st.session_state:
            del st.session_state["temp_servidor_capacity"]
        if "temp_metrica_capacity" in st.session_state:
            del st.session_state["temp_metrica_capacity"]
        if "temp_dias_capacity" in st.session_state:
            del st.session_state["temp_dias_capacity"]
        if "temp_ajuste_capacity" in st.session_state:
            del st.session_state["temp_ajuste_capacity"]
        if "filtros_aplicados_capacity" in st.session_state:
            del st.session_state["filtros_aplicados_capacity"]
        if "reporte_generado" in st.session_state:
            st.session_state["reporte_generado"] = False

    if seccion_destino != "🔔 Alertas":
        if "sb_alerta_srv" in st.session_state:
            st.session_state["sb_alerta_srv"] = "-- Seleccione un Servidor para empezar --"
        if "filtro_alerta_criticidad" in st.session_state:
            st.session_state["filtro_alerta_criticidad"] = "-- Todas --"
        if "filtro_alerta_estado" in st.session_state:
            st.session_state["filtro_alerta_estado"] = "No Resueltas"

    if seccion_destino != "⚙️ Umbrales":
        if "filtro_umbral_servidor" in st.session_state:
            st.session_state["filtro_umbral_servidor"] = "-- Seleccione un Servidor --"
        if "filtro_umbral_componente" in st.session_state:
            st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"

    if tab_actual:
        if seccion_destino == "🖥️ Servidores":
            st.query_params["tab_servidores"] = tab_actual
        elif seccion_destino == "👥 Gestión de usuarios":
            st.query_params["tab_gestion"] = tab_actual
        elif seccion_destino == "📈 Capacity planning":
            st.query_params["tab_capacity"] = tab_actual

def main():
    params = st.query_params
    
    # =============================================================
    # SRV DESDE URL - CAPTURAR Y GUARDAR EN SESSION_STATE
    # =============================================================
    srv_desde_url = params.get("srv")
    if srv_desde_url:
        st.session_state["_srv_redirect"] = srv_desde_url
        st.session_state["_srv_captured"] = True
        logging.info(f"SRV capturado desde URL: {srv_desde_url}")
        
        st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
        st.session_state["filtro_monitoreo_nombre"] = srv_desde_url
        st.session_state["servidor_seleccionado"] = srv_desde_url
        
        try:
            del st.query_params["srv"]
        except:
            pass
    
    # =============================================================
    # PROCESAR REDIRECCIÓN DESDE SERVIDORES.PY (CORREGIDO)
    # =============================================================
    if "_redirigir_a_monitoreo" in st.session_state:
        servidor = st.session_state["_redirigir_a_monitoreo"]
        if servidor:
            logging.info(f"App.py procesando redirección a: {servidor}")
            
            # === FORZAR TODOS LOS ESTADOS DE MONITOREO ===
            st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
            st.session_state["sb_srv_tab1"] = servidor
            st.session_state["sb_srv_tab1_temp"] = servidor
            st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
            st.session_state["sb_metrica_tab1_temp"] = "📊 Todas las Métricas"
            st.session_state["filtro_aplicado_tab1"] = True
            st.session_state["filtro_aplicado_tab2"] = False
            st.session_state["_srv_mensaje_mostrado"] = True
            st.session_state["tab_servidores_activa"] = 0
            st.session_state["_srv_redirect"] = servidor
            
            # Limpiar la redirección
            del st.session_state["_redirigir_a_monitoreo"]
            st.query_params["tab_servidores"] = "1"
            st.rerun()
    
    # =============================================================
    # AUTENTICACIÓN
    # =============================================================
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
        return

    # =============================================================
    # USUARIO AUTENTICADO - NAVEGACIÓN
    # =============================================================
    
    # 1. PRIMERO: Obtener la sección de la URL (prioridad máxima)
    url_seccion = params.get("p")
    if url_seccion:
        st.session_state["seccion_actual"] = url_seccion
    
    # 2. SEGUNDO: Si hay redirección SRV, forzar monitoreo
    if st.session_state.get("_srv_redirect"):
        st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
        # NO LIMPIAR _srv_redirect aquí - monitoreo.py lo necesita
    
    # 3. TERCERO: Si no hay sección, usar Inicio
    if "seccion_actual" not in st.session_state:
        st.session_state["seccion_actual"] = "🏠 Inicio"
    
    # =============================================================
    # GENERAR MENÚ (el widget se sincroniza con seccion_actual)
    # =============================================================
    generar_menu()
    
    # =============================================================
    # LEER LA SECCIÓN DEL WIDGET Y ACTUALIZAR
    # =============================================================
    if "widget_navegacion" in st.session_state:
        widget_seleccion = st.session_state["widget_navegacion"]
        if widget_seleccion != st.session_state["seccion_actual"]:
            st.session_state["seccion_actual"] = widget_seleccion
    
    # =============================================================
    # LIMPIEZA DE FILTROS
    # =============================================================
    gestionar_limpieza_filtros(st.session_state["seccion_actual"])
    
    # =============================================================
    # SINCRONIZAR URL
    # =============================================================
    if params.get("p") != st.session_state["seccion_actual"]:
        st.query_params["p"] = st.session_state["seccion_actual"]
    
    st.query_params["s"] = "1"
    st.query_params["rol"] = st.session_state.get("rol", "operador")
    st.query_params["uid"] = str(st.session_state.get("user_id", 1))
    st.query_params["u"] = st.session_state.get("user_actual", "Sistema")
    st.query_params["c"] = st.session_state.get("cargo", "Analista")
    
    # =============================================================
    # RENDERIZAR MÓDULO
    # =============================================================
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
            st.error(f"Error en la sección {seleccion}. Verifique logs.")

if __name__ == "__main__":
    main()