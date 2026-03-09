import streamlit.web.cli as stcli
import os, sys, subprocess, time, webbrowser

def get_resource_path(relative_path):
    """ Gestiona rutas internas cuando el archivo está empaquetado """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def iniciar_agente():
    """ Lanza el agente de monitoreo de forma invisible """
    agente_path = get_resource_path("agente_captura.py")
    # CREATE_NO_WINDOW evita que salga la pantalla negra de consola
    subprocess.Popen([sys.executable, agente_path], creationflags=subprocess.CREATE_NO_WINDOW)

if __name__ == "__main__":
    # 1. Arrancamos el agente de captura primero
    iniciar_agente()
    
    # 2. Esperamos un segundo y configuramos Streamlit
    time.sleep(1)
    
    # 3. Lanzamos el Dashboard
    sys.argv = [
        "streamlit",
        "run",
        get_resource_path("login.py"), # Tu punto de entrada
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
    ]
    
    # 4. Abrimos el navegador automáticamente
    webbrowser.open("http://localhost:8501")
    
    sys.exit(stcli.main())