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
    # En el EXE, el agente debe lanzarse como un proceso de Python 
    # pero usando los argumentos del motor interno de PyInstaller
    agente_path = get_resource_path("agente_captura.py")
    
    # IMPORTANTE: Usamos un comando simplificado para evitar bucles en el EXE
    subprocess.Popen(
        [sys.executable, agente_path], 
        creationflags=subprocess.CREATE_NO_WINDOW,
        shell=False
    )

if __name__ == "__main__":
    # 1. Agregamos la ruta base al sistema para que encuentre 'modulos'
    base_dir = get_resource_path(".")
    sys.path.append(base_dir)

    # 2. Arrancamos el agente de captura
    try:
        iniciar_agente()
    except:
        pass # Evita que el programa principal muera si el agente falla
    
    # 3. Esperamos a que el motor caliente
    time.sleep(2)
    
    # 4. Configuramos Streamlit para que apunte a APP.PY
    sys.argv = [
        "streamlit",
        "run",
        get_resource_path("app.py"), # <--- CORREGIDO: Tu Login vive aquí
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
    ]
    
    # 5. Abrimos el navegador
    webbrowser.open("http://localhost:8501")
    
    # 6. Ejecutamos Streamlit
    sys.exit(stcli.main())