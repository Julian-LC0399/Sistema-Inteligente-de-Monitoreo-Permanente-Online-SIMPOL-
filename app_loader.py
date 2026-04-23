import sys
from types import ModuleType

# === PARCHE DE COMPATIBILIDAD STREAMLIT ===
try:
    import streamlit.runtime.scriptrunner.magic_funcs
except ImportError:
    mod = ModuleType("streamlit.runtime.scriptrunner.magic_funcs")
    sys.modules["streamlit.runtime.scriptrunner.magic_funcs"] = mod
    mod.magic_funcs = lambda x: x
# ==========================================

import streamlit.web.cli as stcli
import os, subprocess, time, webbrowser
import multiprocessing

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # Necesario para que PyInstaller no ejecute el main infinitamente al crear procesos hijos
    multiprocessing.freeze_support()

    # Si el argumento es --agente, arranca la lógica de recolección de PRTG
    if len(sys.argv) > 1 and sys.argv[1] == "--agente":
        try:
            import agente
            agente.iniciar_agente()
        except Exception as e:
            # Registrar error en un archivo local si el agente falla en el servidor
            with open("error_agente.log", "a") as f:
                f.write(f"[{time.ctime()}] Error: {str(e)}\n")
        sys.exit(0)

    # Lanzar el agente PRTG en segundo plano (invisible, sin consola)
    # Se usa sys.executable para que apunte al propio archivo .exe generado
    subprocess.Popen([sys.executable, "--agente"], 
                     creationflags=0x08000000, 
                     close_fds=True)

    # Configuración de Streamlit para la interfaz
    sys.argv = [
        "streamlit",
        "run",
        get_resource_path("app.py"),
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
    ]

    # Espera para que el servidor Streamlit levante antes de abrir el navegador
    time.sleep(5)
    webbrowser.open("http://localhost:8501")
    
    sys.exit(stcli.main())