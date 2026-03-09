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
    # Soporte para procesos congelados (PyInstaller)
    multiprocessing.freeze_support() 
    
    # 1. EL FILTRO: Si detecta el parámetro --agente, ejecuta el script y muere
    # Esto evita que el proceso del agente intente abrir Streamlit otra vez
    if len(sys.argv) > 1 and sys.argv[1] == "--agente":
        import agente_captura 
        # Aquí puedes llamar a la función principal de tu agente si tiene una
        # por ejemplo: agente_captura.main()
        sys.exit(0)

    # 2. LANZAMIENTO SEGURO:
    # Llamamos al propio ejecutable (sys.executable) pero le pasamos el parámetro --agente
    subprocess.Popen(
        [sys.executable, "--agente"], 
        creationflags=0x08000000, # CREATE_NO_WINDOW: Oculta la consola del agente
        shell=False
    )

    # 3. LANZAR INTERFAZ (Streamlit)
    # Solo llegamos aquí si NO somos el proceso del agente
    time.sleep(1) # Pequeña pausa para dejar que el agente respire
    
    sys.argv = [
        "streamlit", 
        "run", 
        get_resource_path("app.py"),
        "--server.port=8501", 
        "--server.headless=true",
        "--global.developmentMode=false"
    ]
    
    # Abrir navegador
    webbrowser.open("http://localhost:8501")
    
    # Iniciar motor de Streamlit
    sys.exit(stcli.main())