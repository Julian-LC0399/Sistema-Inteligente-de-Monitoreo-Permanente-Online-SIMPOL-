import streamlit.web.cli as stcli
import os, sys, subprocess, time, webbrowser
import multiprocessing

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # CRÍTICO: Soporte para multiprocessing en Windows empaquetado
    multiprocessing.freeze_support() 
    
    # Si el proceso se llama con la bandera --agente, solo ejecuta la captura
    if len(sys.argv) > 1 and sys.argv[1] == "--agente":
        try:
            import agente_captura
            # Si tu agente_captura tiene una función main(), llámala aquí
        except Exception as e:
            print(f"Error en agente: {e}")
        sys.exit(0)

    # Lanzar el Agente de Captura como un proceso hijo independiente y oculto
    # Se llama al propio EXE pero pasando la bandera --agente
    subprocess.Popen(
        [sys.executable, "--agente"], 
        creationflags=0x08000000, # CREATE_NO_WINDOW
        shell=False
    )
    
    time.sleep(1.5)
    
    # Configurar los argumentos para iniciar Streamlit internamente
    sys.argv = [
        "streamlit", 
        "run", 
        get_resource_path("app.py"),
        "--server.port=8501", 
        "--server.headless=true", 
        "--global.developmentMode=false"
    ]
    
    # Abrir el navegador por defecto del usuario
    webbrowser.open("http://localhost:8501")
    
    # Iniciar el motor de Streamlit
    sys.exit(stcli.main())