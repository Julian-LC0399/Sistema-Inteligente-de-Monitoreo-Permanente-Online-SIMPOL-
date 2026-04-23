import streamlit as st
from utils import load_css
import auth
import menu

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# 2. LÓGICA DE PERSISTENCIA REFORZADA
def restaurar_sesion():
    params = st.query_params
    # Solo restaura si hay parámetros activos y NO venimos de un cierre de sesión manual
    if params.get("session") == "active" and st.session_state.get("autenticado") is not False:
        st.session_state["autenticado"] = True
        if "user_actual" not in st.session_state:
            st.session_state["user_actual"] = params.get("u", "Sistema")
            st.session_state["user_id"] = int(params.get("uid", 1))
            st.session_state["nombre_analista"] = params.get("n", "Analista")
            st.session_state["rol"] = params.get("r", "operador")
            if "seccion_actual" not in st.session_state:
                st.session_state["seccion_actual"] = params.get("page", "🏠 Inicio")
    else:
        if "autenticado" not in st.session_state:
            st.session_state["autenticado"] = False

restaurar_sesion()

# 3. ORQUESTADOR DE MÓDULOS
def orquestar_paginas(seleccion):
    nombre_analista = st.session_state.get("nombre_analista", "Analista")
    user_id = st.session_state.get("user_id", 1)
    user_actual = st.session_state.get("user_actual", "Sistema")

    if seleccion == "🏠 Inicio":
        from modulos import inicio
        inicio.mostrar_pantalla()
    elif seleccion == "📊 Monitoreo en vivo":
        from modulos import monitoreo
        monitoreo.mostrar_pantalla(nombre_analista)
    elif seleccion == "📈 Capacity planning":
        from modulos import capacity
        capacity.mostrar_pantalla(nombre_analista, user_id)
    elif seleccion == "🔔 Alertas":
        from modulos import alertas
        alertas.mostrar_pantalla(user_id)
    elif seleccion == "📄 Reportes":
        from modulos import reportes
        reportes.mostrar_pantalla(user_actual, user_id)
    elif seleccion == "👥 Gestión de usuarios":
        from modulos import gestion
        gestion.mostrar_pantalla(nombre_analista, user_id)
    elif seleccion == "🕵️ Auditoría":
        from modulos import auditoria
        auditoria.mostrar_pantalla()

# 4. MAIN
def main():
    if not st.session_state.get("autenticado"):
        # Limpieza de seguridad: si no hay sesión, la URL debe estar limpia
        if st.query_params:
            st.query_params.clear()
        auth.mostrar_login()
    else:
        seleccion = menu.generar_menu()
        orquestar_paginas(seleccion)

if __name__ == "__main__":
    main()