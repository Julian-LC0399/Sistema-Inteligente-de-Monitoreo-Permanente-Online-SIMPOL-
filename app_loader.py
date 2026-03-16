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
    multiprocessing.freeze_support() # EVITA BUCLE INFINITO EN EL EXE
    
    if len(sys.argv) > 1 and sys.argv[1] == "--agente":
        import agente_captura
        sys.exit(0)

    # Lanzar agente en segundo plano de forma oculta
    subprocess.Popen([sys.executable, "--agente"], creationflags=0x08000000)
    
    time.sleep(1.5)
    
    sys.argv = [
        "streamlit", "run", get_resource_path("app.py"),
        "--server.port=8501", "--server.headless=true", "--global.developmentMode=false"
    ]
    
    webbrowser.open("http://localhost:8501")
    sys.exit(stcli.main())