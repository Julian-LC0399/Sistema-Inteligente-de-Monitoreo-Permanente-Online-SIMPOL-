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

# =============================================================
# FUNCIONES DE LIMPIEZA DE ESTADO
# =============================================================
def limpiar_estado_capacity():
    """Limpia todas las variables de estado del módulo capacity"""
    keys_to_clear = [
        'p1_servidor', 'p1_metrica', 'p1_dias', 'p1_ajuste',
        'p1_filtros_aplicados', 'p1_reporte_generado',
        'p2_servidor_seleccionado', 'p2_metrica_filtro',
        'p2_formato_filtro', 'p2_mostrar_tabla'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def limpiar_estado_reportes():
    """Limpia todas las variables de estado del módulo reportes"""
    keys_to_clear = [
        'rep_listo',
        'rep_csv',
        'rep_pdf',
        'rep_name_csv',
        'rep_name_pdf',
        'key_semilla_selectbox',
        'filtros_aplicados',
        'temp_servidor',
        'temp_sensor',
        'temp_fecha_i',
        'temp_fecha_f',
        'temp_formato',
        'servidor_seleccionado_reporte',
        'filtro_sensor_general',
        'filtro_fecha_i',
        'filtro_fecha_f',
        'filtro_formato_salida'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def limpiar_parametros_monitoreo():
    """Limpia TODOS los parámetros y estados de monitoreo"""
    # Limpiar parámetros de URL
    params_to_remove = ['srv', 'srv_mon', 'srv_select', 'metrica_select', 'tab_servidores']
    for param in params_to_remove:
        if param in st.query_params:
            del st.query_params[param]
    
    # Limpiar estados de monitoreo
    keys_to_clear = [
        '_monitoreo_activo',
        '_srv_redirect_pending',
        'filtro_monitoreo_nombre',
        'filtro_monitoreo_sensor',
        'servidor_seleccionado',
        'sb_srv_tab1',
        'sb_metrica_tab1',
        'filtro_aplicado_tab1',
        'filtro_aplicado_tab2',
        '_srv_mensaje_mostrado'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Resetear estados de monitoreo a valores por defecto
    st.session_state["_monitoreo_activo"] = False
    st.session_state["filtro_aplicado_tab1"] = False
    st.session_state["filtro_aplicado_tab2"] = False

def gestionar_limpieza_filtros(seccion_destino):
    """Gestiona la limpieza de filtros al cambiar de módulo"""
    # Si es monitoreo, NO LIMPIAR NADA
    if seccion_destino == "🖥️ Monitoreo en vivo":
        return
    
    # Si hay un SRV en query params o redirección pendiente, NO LIMPIAR
    if "srv" in st.query_params or st.session_state.get("_srv_redirect_pending"):
        return

    tab_actual = None
    if seccion_destino == "🖥️ Servidores":
        tab_actual = st.query_params.get("tab_servidores")
    elif seccion_destino == "👥 Gestión de usuarios":
        tab_actual = st.query_params.get("tab_gestion")
    elif seccion_destino == "📈 Capacity planning":
        tab_actual = st.query_params.get("tab_capacity")

    # =============================================================
    # LIMPIEZA DE FILTROS POR MÓDULO
    # =============================================================
    
    # LIMPIAR MONITOREO (si no estamos en monitoreo)
    if seccion_destino != "🖥️ Monitoreo en vivo":
        if "filtro_monitoreo_nombre" in st.session_state:
            st.session_state["filtro_monitoreo_nombre"] = "-- Seleccione un Servidor--"
        if "filtro_monitoreo_sensor" in st.session_state:
            st.session_state["filtro_monitoreo_sensor"] = "-- Seleccione un Sensor --"
        if "servidor_seleccionado" in st.session_state:
            st.session_state["servidor_seleccionado"] = "-- Seleccione un Servidor --"
        if "sb_srv_tab1" in st.session_state:
            st.session_state["sb_srv_tab1"] = "-- Seleccione un Servidor --"
        if "sb_metrica_tab1" in st.session_state:
            st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
        if "filtro_aplicado_tab1" in st.session_state:
            st.session_state["filtro_aplicado_tab1"] = False
        if "filtro_aplicado_tab2" in st.session_state:
            st.session_state["filtro_aplicado_tab2"] = False

    # LIMPIAR GESTIÓN DE USUARIOS
    if seccion_destino != "👥 Gestión de usuarios":
        if "filtro_analista" in st.session_state:
            st.session_state["filtro_analista"] = "-- Seleccione un Analista --"
        if "accion_personal" in st.session_state:
            st.session_state["accion_personal"] = None

    # LIMPIAR SERVIDORES
    if seccion_destino != "🖥️ Servidores":
        if "filtro_servidor_nombre" in st.session_state:
            st.session_state["filtro_servidor_nombre"] = "-- Seleccione un Servidor --"
        if "accion_infra" in st.session_state:
            st.session_state["accion_infra"] = None
        if "filtro_adicional_nombre" in st.session_state:
            st.session_state["filtro_adicional_nombre"] = "-- Seleccione un Servidor Base --"
        if "accion_adicional" in st.session_state:
            st.session_state["accion_adicional"] = None

    # LIMPIAR REPORTES
    if seccion_destino != "📄 Reportes":
        limpiar_estado_reportes()

    # LIMPIAR CAPACITY PLANNING
    if seccion_destino != "📈 Capacity planning":
        limpiar_estado_capacity()
        if "servidor_seleccionado_capacity" in st.session_state:
            st.session_state["servidor_seleccionado_capacity"] = "-- Seleccione un Servidor --"
        if "metrica_seleccionada_capacity" in st.session_state:
            st.session_state["metrica_seleccionada_capacity"] = "CPU"
        if "dias_prediccion_capacity" in st.session_state:
            st.session_state["dias_prediccion_capacity"] = 30
        if "reporte_generado" in st.session_state:
            st.session_state["reporte_generado"] = False

    # LIMPIAR ALERTAS
    if seccion_destino != "🔔 Alertas":
        if "sb_alerta_srv" in st.session_state:
            st.session_state["sb_alerta_srv"] = "-- Seleccione un Servidor para empezar --"
        if "filtro_alerta_criticidad" in st.session_state:
            st.session_state["filtro_alerta_criticidad"] = "-- Todas --"
        if "filtro_alerta_estado" in st.session_state:
            st.session_state["filtro_alerta_estado"] = "No Resueltas"

    # LIMPIAR UMBRALES
    if seccion_destino != "⚙️ Umbrales":
        if "filtro_umbral_servidor" in st.session_state:
            st.session_state["filtro_umbral_servidor"] = "-- Seleccione un Servidor --"
        if "filtro_umbral_componente" in st.session_state:
            st.session_state["filtro_umbral_componente"] = "-- Seleccione un Componente --"

    # Restaurar pestañas activas
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
    # 🔥 PROCESAR REDIRECCIÓN DESDE SERVIDORES ("Ver en vivo")
    # =============================================================
    srv_desde_url = params.get("srv")
    if srv_desde_url:
        logging.info(f"🔍 Procesando redirección desde servidores: {srv_desde_url}")
        st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
        st.session_state["_monitoreo_activo"] = True
        st.session_state["filtro_monitoreo_nombre"] = srv_desde_url
        st.session_state["servidor_seleccionado"] = srv_desde_url
        st.session_state["sb_srv_tab1"] = srv_desde_url
        st.session_state["sb_metrica_tab1"] = "📊 Todas las Métricas"
        st.session_state["filtro_aplicado_tab1"] = True
        # Eliminar srv de la URL
        del st.query_params["srv"]
        # Eliminar cualquier rastro de srv_mon
        if "srv_mon" in st.query_params:
            del st.query_params["srv_mon"]
        st.rerun()
        return
    
    # =============================================================
    # 🔥 Si hay srv_mon en URL, limpiarlo (ya estamos en monitoreo)
    # =============================================================
    if "srv_mon" in st.query_params:
        # Ya estamos en monitoreo, eliminar srv_mon para evitar bucles
        del st.query_params["srv_mon"]
        st.rerun()
        return
    
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
    
    # 1. PRIMERO: Obtener la sección de la URL
    url_seccion = params.get("p")
    if url_seccion:
        st.session_state["seccion_actual"] = url_seccion
    
    # 2. SEGUNDO: Si hay flag de monitoreo activo, mantener monitoreo
    if st.session_state.get("_monitoreo_activo", False):
        st.session_state["seccion_actual"] = "🖥️ Monitoreo en vivo"
    
    # 3. TERCERO: Si no hay sección, usar Inicio
    if "seccion_actual" not in st.session_state:
        st.session_state["seccion_actual"] = "🏠 Inicio"
    
    # =============================================================
    # GENERAR MENÚ
    # =============================================================
    generar_menu()
    
    # =============================================================
    # ESTABLECER MÓDULO ACTUAL ANTES DE LIMPIAR
    # =============================================================
    modulo_map = {
        "🏠 Inicio": "inicio",
        "🖥️ Servidores": "servidores",
        "🖥️ Monitoreo en vivo": "monitoreo",
        "📈 Capacity planning": "capacity",
        "🔔 Alertas": "alertas",
        "⚙️ Umbrales": "umbrales",
        "📄 Reportes": "reportes",
        "👥 Gestión de usuarios": "gestion",
        "🕵️ Auditoría": "auditoria"
    }
    st.session_state["modulo_actual"] = modulo_map.get(st.session_state["seccion_actual"], "otros")
    
    # =============================================================
    # LIMPIEZA DE FILTROS - PRESERVAR MONITOREO
    # =============================================================
    if st.session_state["seccion_actual"] != "🖥️ Monitoreo en vivo":
        gestionar_limpieza_filtros(st.session_state["seccion_actual"])
        limpiar_parametros_monitoreo()
    
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
            st.exception(e)

if __name__ == "__main__":
    main()