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
    # Obtenemos el ID del usuario actual para las auditorías
    user_actual = st.session_state.get("user_actual", "Sistema")
    nombre_analista = st.session_state.get("nombre_analista", "Analista")

    # Importamos solo el archivo necesario según la selección del menú
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
        # CORRECCIÓN: Se añade user_actual para el registro de umbrales
        alertas.mostrar_pantalla(user_actual)
        
    elif seleccion == "📄 Reportes":
        from modulos import reportes
        reportes.mostrar_pantalla()
        
    elif seleccion == "👥 Gestión de usuarios":
        from modulos import gestion
        # CORRECCIÓN: Se asegura el paso de user_actual para auditoría de usuarios
        gestion.mostrar_pantalla(user_actual)
        
    elif seleccion == "🕵️ Auditoría":
        from modulos import auditoria
        # OPCIONAL: Si auditoria.py también requiere user_actual en el futuro
        auditoria.mostrar_pantalla()


# 3. MAIN
def main():
    if not st.session_state["autenticado"]:
        auth.mostrar_login()
    else:
        # Generar el menú lateral y obtener la opción seleccionada
        seleccion = menu.generar_menu()
        
        # Cargar el módulo correspondiente
        orquestar_paginas(seleccion)


if __name__ == "__main__":
    main()