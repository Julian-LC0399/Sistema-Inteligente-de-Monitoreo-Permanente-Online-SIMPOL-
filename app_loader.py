import streamlit.web.cli as stcli
import os
import sys

def resolve_path(path):
    """
    Busca el archivo dentro de la carpeta temporal del .exe (_MEIPASS)
    o en la carpeta actual de trabajo.
    """
    if getattr(sys, 'frozen', False):
        # Cuando corre como .exe, bundle_dir es la carpeta temporal
        bundle_dir = sys._MEIPASS
    else:
        # Cuando corre como script .py
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.normpath(os.path.join(bundle_dir, path))

def main():
    # --- AJUSTE DE RUTAS PARA MÓDULOS INTERNOS ---
    # Si es un EXE, forzamos a Python a mirar dentro de la carpeta temporal
    # para que encuentre 'utils', 'modulos', 'auth', etc.
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, sys._MEIPASS)
        # También nos aseguramos de que el directorio de trabajo sea donde está el EXE
        # para que el agente pueda escribir su log 'debug_agente.txt'
        os.chdir(os.path.dirname(sys.executable))

    # 1. Localizamos app.py de forma absoluta
    script_path = resolve_path("app.py")

    # 2. Verificación de existencia con mensaje de depuración
    if not os.path.exists(script_path):
        print(f"--- ERROR CRÍTICO ---")
        print(f"No se encontró el archivo principal: {script_path}")
        print(f"Directorio actual: {os.getcwd()}")
        if getattr(sys, 'frozen', False):
            print(f"Contenido de _MEIPASS: {os.listdir(sys._MEIPASS)}")
        input("\nPresione ENTER para salir...")
        sys.exit(1)

    # 3. Configuramos los argumentos de ejecución de Streamlit
    # Agregamos configuraciones para mejorar la estabilidad en el Banco
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.headless=true",
        "--client.toolbarMode=viewer",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
        "--server.address=127.0.0.1" # Fuerza a usar localhost para evitar bloqueos de red
    ]

    # 4. Lanzamos Streamlit
    try:
        stcli.main()
    except Exception as e:
        print(f"Error al lanzar Streamlit: {e}")
        input("Presione ENTER para salir...")

if __name__ == "__main__":
    # Soporte para multiprocessing (necesario para el agente en Windows)
    import multiprocessing
    multiprocessing.freeze_support()
    main()