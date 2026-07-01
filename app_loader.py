import streamlit.web.cli as stcli
import os
import sys
import threading
import time
import webbrowser
import atexit
import multiprocessing

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
AGENTE_PROCESS = None
AGENTE_SCRIPT = "agente.py"

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(bundle_dir, path))

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# FUNCIÓN PARA EJECUTAR EL AGENTE (se ejecuta en proceso separado)
# =============================================================================

def ejecutar_agente():
    """Función que se ejecuta en el proceso hijo"""
    try:
        # Importar y ejecutar agente directamente
        import agente
        agente.ejecutar_motor_agente()
    except Exception as e:
        # Si falla, escribir en un archivo de error
        try:
            log_dir = get_exe_dir()
            error_file = os.path.join(log_dir, "agente_error.log")
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(f"Error en agente: {e}\n")
                import traceback
                traceback.print_exc(file=f)
        except:
            pass

# =============================================================================
# MANEJO DEL AGENTE
# =============================================================================

def iniciar_agente():
    global AGENTE_PROCESS
    
    try:
        # Verificar que agente.py existe
        agente_path = resolve_path(AGENTE_SCRIPT)
        
        if not os.path.exists(agente_path):
            agente_path = os.path.join(os.getcwd(), AGENTE_SCRIPT)
        
        if not os.path.exists(agente_path):
            print("[AGENTE] No se encontro agente.py")
            return False
        
        print(f"[AGENTE] Encontrado en: {agente_path}")
        
        # Usar multiprocessing para iniciar el agente
        AGENTE_PROCESS = multiprocessing.Process(
            target=ejecutar_agente,
            name="AgenteSIMPOL",
            daemon=True
        )
        AGENTE_PROCESS.start()
        
        atexit.register(detener_agente)
        time.sleep(2)
        
        if AGENTE_PROCESS.is_alive():
            print(f"[AGENTE] ACTIVO - PID: {AGENTE_PROCESS.pid}")
            return True
        else:
            print("[AGENTE] No se pudo iniciar")
            return False
        
    except Exception as e:
        print(f"[AGENTE] Error: {e}")
        return False

def detener_agente():
    global AGENTE_PROCESS
    
    if AGENTE_PROCESS and AGENTE_PROCESS.is_alive():
        try:
            AGENTE_PROCESS.terminate()
            AGENTE_PROCESS.join(timeout=3)
            if AGENTE_PROCESS.is_alive():
                AGENTE_PROCESS.kill()
        except:
            pass

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def abrir_navegador():
    time.sleep(2)
    url = "http://127.0.0.1:8501"
    try:
        webbrowser.open(url)
    except:
        pass

def mostrar_consola():
    os.system('cls' if sys.platform == 'win32' else 'clear')
    
    print("=" * 70)
    print("  SIMPOL - Sistema Inteligente de Monitoreo Permanente Online")
    print("=" * 70)
    print()
    print("  [WEB] ACCESO:")
    print("  ------------------------------------------------------")
    print("  http://127.0.0.1:8501")
    print("  ------------------------------------------------------")
    print()
    print("  [AGENTE] INICIANDO...")
    print("  ------------------------------------------------------")
    print()

def main():
    # === CONFIGURACION INICIAL ===
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, sys._MEIPASS)
        os.chdir(os.path.dirname(sys.executable))

    # === MOSTRAR CONSOLA ===
    mostrar_consola()

    # === INICIAR AGENTE ===
    iniciar_agente()

    # === ABRIR NAVEGADOR ===
    hilo_navegador = threading.Thread(target=abrir_navegador, daemon=True)
    hilo_navegador.start()

    # === LOCALIZAR app.py ===
    script_path = resolve_path("app.py")

    if not os.path.exists(script_path):
        print(f"\n[ERROR] No se encontro app.py en: {script_path}")
        input("\nPresione ENTER para salir...")
        sys.exit(1)

    # === CONFIGURAR ARGUMENTOS DE STREAMLIT ===
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.headless=true",
        "--client.toolbarMode=viewer",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ]

    print("Iniciando servidor SIMPOL...\n")

    # === LANZAR STREAMLIT ===
    try:
        stcli.main()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupcion manual.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        detener_agente()
        print("\n[OK] Sistema SIMPOL finalizado.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()