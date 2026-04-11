import streamlit as st
from utils import load_css
import auth
import menu

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# 2. LÓGICA DE PERSISTENCIA REFORZADA (CORRECCIÓN CRÍTICA)
def restaurar_sesion():
    params = st.query_params
    # Si hay una sesión activa en la URL, restauramos el session_state
    if params.get("session") == "active":
        st.session_state["autenticado"] = True
        # Recuperamos los datos del usuario desde la URL si no están en el estado
        if "user_actual" not in st.session_state:
            st.session_state["user_actual"] = params.get("u", "Sistema")
            st.session_state["nombre_analista"] = params.get("n", "Analista")
            st.session_state["rol"] = params.get("r", "operador")
            st.session_state["seccion_actual"] = params.get("page", "🏠 Inicio")
    else:
        if "autenticado" not in st.session_state:
            st.session_state["autenticado"] = False

restaurar_sesion()

# 3. ORQUESTADOR DE MÓDULOS
def orquestar_paginas(seleccion):
    user_actual = st.session_state.get("user_actual", "Sistema")
    nombre_analista = st.session_state.get("nombre_analista", "Analista")
    rol_actual = st.session_state.get("rol", "operador")

    # Actualizamos URL para mantener persistencia al recargar
    if st.session_state.get("autenticado"):
        st.query_params["page"] = seleccion
        st.query_params["session"] = "active"
        st.query_params["u"] = user_actual
        st.query_params["n"] = nombre_analista
        st.query_params["r"] = rol_actual
    
    if seleccion == "🏠 Inicio":
        from modulos import inicio
        inicio.mostrar_pantalla()
    elif seleccion == "📊 Monitoreo en vivo":
        from modulos import monitoreo
        monitoreo.mostrar_pantalla(nombre_analista)
    elif seleccion == "📈 Capacity planning":
        from modulos import capacity
        capacity.mostrar_pantalla()
    elif seleccion == "🔔 Alertas":
        from modulos import alertas
        alertas.mostrar_pantalla(user_actual)
    elif seleccion == "📄 Reportes":
        from modulos import reportes
        reportes.mostrar_pantalla()
    elif seleccion == "👥 Gestión de usuarios":
        from modulos import gestion
        gestion.mostrar_pantalla(user_actual)
    elif seleccion == "🕵️ Auditoría":
        from modulos import auditoria
        auditoria.mostrar_pantalla()

# 4. FUNCIÓN DE CIERRE DE SESIÓN
def logout():
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# 5. MAIN
def main():
    if not st.session_state.get("autenticado"):
        # Asegurarse de que no haya basura en la URL si no está logueado
        if st.query_params.get("session") == "active":
            st.query_params.clear()
        auth.mostrar_login()
    else:
        # Generar menú y capturar selección
        seleccion = menu.generar_menu()
        
        # Lógica de cierre de sesión desde el menú
        if seleccion == "Cerrar Sesión":
            logout()
        else:
            orquestar_paginas(seleccion)

if __name__ == "__main__":
    main()