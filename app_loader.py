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
    # Evita que el ejecutable se abra a sí mismo infinitamente en Windows
    multiprocessing.freeze_support()

    # Lógica para detectar si este proceso es el Agente o la Interfaz
    if len(sys.argv) > 1 and sys.argv[1] == "--agente":
        import agente

        agente.iniciar_agente()
        sys.exit(0)

    # Lanzar el proceso del agente en segundo plano (invisible)
    # 0x08000000 es para que no se abra una ventana de consola extra
    subprocess.Popen([sys.executable, "--agente"], creationflags=0x08000000)

    # Configurar argumentos para Streamlit
    sys.argv = [
        "streamlit",
        "run",
        get_resource_path("app.py"),
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
    ]

    # Tiempo de cortesía para que el servidor local de Streamlit levante
    time.sleep(4)

    # Abrir el navegador automáticamente
    webbrowser.open("http://localhost:8501")

    # Iniciar la interfaz de Streamlit
    sys.exit(stcli.main())
