import streamlit as st
from utils import load_css
import auth
import menu

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")
load_css("style.css")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# 2. CARGA DINÁMICA DE PÁGINAS
def orquestar_paginas(seleccion):
    # Importamos solo el archivo necesario según la selección
    if seleccion == "🏠 Inicio":
        from modulos import inicio
        inicio.mostrar_pantalla()
    elif seleccion == "📊 Monitoreo en vivo":
        from modulos import monitoreo
        monitoreo.mostrar_pantalla(st.session_state.get("nombre_analista"))
    elif seleccion == "📈 Capacity planning":
        from modulos import capacity
        capacity.mostrar_pantalla()
    elif seleccion == "🔔 Alertas":
        from modulos import alertas
        alertas.mostrar_pantalla()
    elif seleccion == "📄 Reportes":
        from modulos import reportes
        reportes.mostrar_pantalla()
    elif seleccion == "👥 Gestión de personal":
        from modulos import gestion
        gestion.mostrar_pantalla(st.session_state.get("user_actual"))

# 3. MAIN
def main():
    if not st.session_state["autenticado"]:
        auth.mostrar_login()
    else:
        # Capturamos la opción elegida del menú
        opcion = menu.generar_menu()
        # Mostramos la página correspondiente
        orquestar_paginas(opcion)

if __name__ == "__main__":
    main()