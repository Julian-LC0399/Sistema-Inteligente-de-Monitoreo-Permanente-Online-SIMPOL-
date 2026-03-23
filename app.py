import streamlit as st
from utils import load_css

# 1. CONFIGURACIÓN INICIAL (Obligatorio en el arranque)
st.set_page_config(
    page_title="SIMPOL | Banco Caroní", 
    layout="wide", 
    page_icon="🏦"
)

# 2. CARGAR ESTILOS GLOBALES
load_css("style.css")

# 3. ESTADO DE SESIÓN (Control de flujo)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# 4. LÓGICA DE ARRANQUE (Sin código de interfaz aquí)
def main():
    if not st.session_state["autenticado"]:
        # Solo importa y ejecuta el login si no hay sesión
        import auth
        auth.mostrar_login()
    else:
        # Una vez autenticado, el control pasa al menú
        # El menú es el que ahora decide qué pantalla mostrar
        import menu
        menu.generar_interfaz_principal()

if __name__ == "__main__":
    main()