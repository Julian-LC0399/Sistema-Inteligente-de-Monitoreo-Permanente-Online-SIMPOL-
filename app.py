import streamlit as st
from utils import load_css
import auth
import menu

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

# 2. LÓGICA DE PERSISTENCIA (EL SECRETO DEL F5)
if "autenticado" not in st.session_state:
    params = st.query_params
    # Si la URL dice que la sesión está activa, restauramos el estado
    if params.get("session") == "active":
        st.session_state["autenticado"] = True
        # RECUPERAMOS LA PÁGINA: Si la URL dice 'page=🔔 Alertas', cargamos eso
        st.session_state["seccion_actual"] = params.get("page", "🏠 Inicio")
    else:
        st.session_state["autenticado"] = False

# 3. ORQUESTADOR DE MÓDULOS
def orquestar_paginas(seleccion):
    # ACTUALIZAMOS LA URL: Cada vez que hagas clic, la URL del navegador cambia
    # Esto permite que al dar F5, el navegador sepa dónde estabas
    st.query_params["page"] = seleccion
    st.query_params["session"] = "active"
    
    user_actual = st.session_state.get("user_actual", "Sistema")
    nombre_analista = st.session_state.get("nombre_analista", "Analista")

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

# 4. MAIN
def main():
    if not st.session_state.get("autenticado"):
        auth.mostrar_login()
    else:
        # El menú usa la 'key' para sincronizarse con el session_state
        seleccion = menu.generar_menu()
        orquestar_paginas(seleccion)

if __name__ == "__main__":
    main()