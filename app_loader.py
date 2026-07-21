import streamlit.web.cli as stcli
import os
import sys
import threading
import time
import webbrowser
import atexit
import multiprocessing
import subprocess
import logging
from datetime import datetime
import signal
import tempfile

# =============================================================================
# CONFIGURACION GLOBAL
# =============================================================================
AGENTE_PROCESS = None
ENVIADOR_PROCESS = None
STREAMLIT_PROCESS = None
SISTEMA_ACTIVO = True
AGENTE_SCRIPT = "agente.py"
ENVIADOR_SCRIPT = "enviar_mensajes.py"
LOCK_FILE = None

# =============================================================================
# CONFIGURACION DE LOGS
# =============================================================================
LOG_DIR = None

def setup_logging():
    global LOG_DIR
    if getattr(sys, 'frozen', False):
        LOG_DIR = os.path.dirname(sys.executable)
    else:
        LOG_DIR = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(LOG_DIR, "simpol_loader.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = None

# =============================================================================
# MANEJO DE INSTANCIA UNICA (LOCK FILE)
# =============================================================================

def obtener_lock_file():
    """Obtiene la ruta del archivo de bloqueo"""
    if getattr(sys, 'frozen', False):
        lock_dir = os.path.dirname(sys.executable)
    else:
        lock_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(lock_dir, "simpol.lock")

def verificar_instancia_unica():
    """Verifica que solo haya una instancia del sistema ejecutandose"""
    global LOCK_FILE
    
    lock_path = obtener_lock_file()
    
    try:
        if os.path.exists(lock_path):
            try:
                with open(lock_path, 'r') as f:
                    pid = int(f.read().strip())
                
                try:
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}'],
                        capture_output=True,
                        text=True
                    )
                    if str(pid) in result.stdout:
                        logger.error(f"El sistema ya esta ejecutandose (PID: {pid})")
                        logger.error("Solo se permite una instancia")
                        return False
                    else:
                        os.remove(lock_path)
                except:
                    try:
                        os.remove(lock_path)
                    except:
                        pass
            except:
                try:
                    os.remove(lock_path)
                except:
                    pass
        
        with open(lock_path, 'w') as f:
            f.write(str(os.getpid()))
        
        LOCK_FILE = lock_path
        atexit.register(eliminar_lock_file)
        return True
        
    except Exception as e:
        logger.error(f"Error verificando instancia unica: {e}")
        return True

def eliminar_lock_file():
    """Elimina el archivo de bloqueo"""
    global LOCK_FILE
    if LOCK_FILE and os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass

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

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# MANEJADOR DE SEÑALES PARA CIERRE GRACIAL
# =============================================================================

def signal_handler(signum, frame):
    global SISTEMA_ACTIVO
    logger.info(f"[SISTEMA] Señal {signum} recibida, cerrando...")
    SISTEMA_ACTIVO = False
    detener_todo()
    eliminar_lock_file()
    sys.exit(0)

# =============================================================================
# FUNCION PARA EJECUTAR STREAMLIT COMO PROCESO SEPARADO
# =============================================================================

def ejecutar_streamlit():
    global logger
    
    if logger is None:
        logger = setup_logging()
    
    try:
        script_path = resolve_path("app.py")
        logger.info(f"[STREAMLIT] Iniciando con app.py en: {script_path}")
        
        if not os.path.exists(script_path):
            logger.error(f"[STREAMLIT] No se encontro app.py en: {script_path}")
            return False
        
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
            "--server.enableXsrfProtection=false",
            "--server.maxUploadSize=200",
            "--server.enableWebsocketCompression=false"
        ]
        
        logger.info("[STREAMLIT] Ejecutando servidor...")
        stcli.main()
        
    except KeyboardInterrupt:
        logger.info("[STREAMLIT] Interrupcion manual")
    except Exception as e:
        logger.error(f"[STREAMLIT] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())

# =============================================================================
# FUNCION PARA EJECUTAR EL ENVIADOR DE MENSAJES (VERSIÓN CORREGIDA)
# =============================================================================

def ejecutar_enviador_mensajes():
    """
    Ejecuta enviar_mensajes.py en un bucle continuo.
    En el .exe, importa y ejecuta la función directamente.
    """
    global SISTEMA_ACTIVO, logger
    
    if logger is None:
        logger = setup_logging()
    
    logger.info("[MENSAJES] Proceso iniciado correctamente")
    
    # Agregar el directorio del script al path
    script_dir = get_script_dir()
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    logger.info(f"[MENSAJES] Script dir: {script_dir}")
    
    contador = 0
    
    while SISTEMA_ACTIVO:
        try:
            contador += 1
            logger.info(f"[MENSAJES] Ejecucion #{contador}")
            
            # =============================================================
            # IMPORTAR Y EJECUTAR DIRECTAMENTE (FUNCIONA EN .EXE)
            # =============================================================
            try:
                import enviar_mensajes as enviador
                enviador.procesar_mensajes()
                logger.info(f"[MENSAJES] Ejecucion #{contador} completada")
                
            except ImportError as e:
                logger.error(f"[MENSAJES] Error importando enviar_mensajes: {e}")
                logger.info("[MENSAJES] Intentando como subproceso...")
                
                # Fallback: ejecutar como subproceso
                enviador_path = os.path.join(script_dir, ENVIADOR_SCRIPT)
                if not os.path.exists(enviador_path):
                    enviador_path = os.path.join(get_exe_dir(), ENVIADOR_SCRIPT)
                
                if os.path.exists(enviador_path):
                    logger.info(f"[MENSAJES] Script encontrado en: {enviador_path}")
                    cmd = [sys.executable, enviador_path, "--auto"]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=get_exe_dir()
                    )
                    
                    if result.stdout:
                        logger.info(f"[MENSAJES] STDOUT: {result.stdout.strip()}")
                    if result.stderr:
                        logger.warning(f"[MENSAJES] STDERR: {result.stderr.strip()}")
                else:
                    logger.error(f"[MENSAJES] No se encontro {ENVIADOR_SCRIPT}")
                    
            except Exception as e:
                logger.error(f"[MENSAJES] Error en ejecucion: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(10)
                
        except Exception as e:
            logger.error(f"[MENSAJES] Error en bucle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(10)
        
        # Esperar antes de la proxima ejecucion
        if SISTEMA_ACTIVO:
            logger.info("[MENSAJES] Esperando 30 segundos...")
            for _ in range(30):
                if not SISTEMA_ACTIVO:
                    break
                time.sleep(1)
    
    logger.info("[MENSAJES] Proceso finalizado")

# =============================================================================
# FUNCION PARA EJECUTAR EL AGENTE
# =============================================================================

def ejecutar_agente():
    global SISTEMA_ACTIVO, logger
    
    if logger is None:
        logger = setup_logging()
    
    try:
        script_dir = get_script_dir()
        
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        original_dir = os.getcwd()
        os.chdir(script_dir)
        
        try:
            import agente
            logger.info("[AGENTE] Motor iniciado correctamente")
            
            while SISTEMA_ACTIVO:
                try:
                    if hasattr(agente, 'ejecutar_motor_agente'):
                        agente.ejecutar_motor_agente()
                        time.sleep(5)
                    else:
                        logger.error("[AGENTE] La funcion 'ejecutar_motor_agente' no existe")
                        break
                except Exception as e:
                    logger.error(f"[AGENTE] Error en ejecucion: {e}")
                    time.sleep(5)
                    
        finally:
            os.chdir(original_dir)
            
    except ImportError as e:
        logger.error(f"[AGENTE] No se pudo importar agente: {e}")
    except Exception as e:
        logger.error(f"[AGENTE] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())

# =============================================================================
# MANEJO DE PROCESOS
# =============================================================================

def iniciar_agente():
    global AGENTE_PROCESS, logger
    
    if logger is None:
        logger = setup_logging()
    
    try:
        script_dir = get_script_dir()
        agente_path = os.path.join(script_dir, AGENTE_SCRIPT)
        
        if not os.path.exists(agente_path):
            agente_path = os.path.join(get_exe_dir(), AGENTE_SCRIPT)
        
        if not os.path.exists(agente_path):
            logger.error(f"[AGENTE] No se encontro {AGENTE_SCRIPT}")
            return False
        
        logger.info(f"[AGENTE] Encontrado en: {agente_path}")
        
        AGENTE_PROCESS = multiprocessing.Process(
            target=ejecutar_agente,
            name="AgenteSIMPOL"
        )
        AGENTE_PROCESS.start()
        
        time.sleep(2)
        
        if AGENTE_PROCESS.is_alive():
            logger.info(f"[AGENTE] ACTIVO - PID: {AGENTE_PROCESS.pid}")
            return True
        else:
            logger.error("[AGENTE] No se pudo iniciar")
            return False
        
    except Exception as e:
        logger.error(f"[AGENTE] Error: {e}")
        return False

def iniciar_enviador():
    global ENVIADOR_PROCESS, logger
    
    if logger is None:
        logger = setup_logging()
    
    try:
        ENVIADOR_PROCESS = multiprocessing.Process(
            target=ejecutar_enviador_mensajes,
            name="EnviadorTelegram"
        )
        ENVIADOR_PROCESS.start()
        
        logger.info("[MENSAJES] Proceso iniciado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"[MENSAJES] Error al iniciar: {e}")
        return False

def iniciar_streamlit():
    global STREAMLIT_PROCESS, logger
    
    if logger is None:
        logger = setup_logging()
    
    try:
        script_path = resolve_path("app.py")
        if not os.path.exists(script_path):
            logger.error(f"[STREAMLIT] No se encontro app.py en: {script_path}")
            return False
        
        logger.info(f"[STREAMLIT] app.py encontrado en: {script_path}")
        
        STREAMLIT_PROCESS = multiprocessing.Process(
            target=ejecutar_streamlit,
            name="StreamlitServer"
        )
        STREAMLIT_PROCESS.start()
        
        time.sleep(3)
        
        if STREAMLIT_PROCESS.is_alive():
            logger.info(f"[STREAMLIT] Servidor iniciado - PID: {STREAMLIT_PROCESS.pid}")
            return True
        else:
            logger.error("[STREAMLIT] No se pudo iniciar")
            return False
        
    except Exception as e:
        logger.error(f"[STREAMLIT] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def detener_todo():
    global AGENTE_PROCESS, ENVIADOR_PROCESS, STREAMLIT_PROCESS, SISTEMA_ACTIVO
    
    SISTEMA_ACTIVO = False
    logger.info("[SISTEMA] Deteniendo todos los procesos...")
    
    if AGENTE_PROCESS and AGENTE_PROCESS.is_alive():
        try:
            logger.info("[AGENTE] Deteniendo proceso...")
            AGENTE_PROCESS.terminate()
            AGENTE_PROCESS.join(timeout=5)
            if AGENTE_PROCESS.is_alive():
                AGENTE_PROCESS.kill()
            logger.info("[AGENTE] Detenido")
        except Exception as e:
            logger.error(f"[AGENTE] Error al detener: {e}")
    
    if ENVIADOR_PROCESS and ENVIADOR_PROCESS.is_alive():
        try:
            logger.info("[MENSAJES] Deteniendo proceso...")
            ENVIADOR_PROCESS.terminate()
            ENVIADOR_PROCESS.join(timeout=5)
            if ENVIADOR_PROCESS.is_alive():
                ENVIADOR_PROCESS.kill()
            logger.info("[MENSAJES] Detenido")
        except Exception as e:
            logger.error(f"[MENSAJES] Error al detener: {e}")
    
    if STREAMLIT_PROCESS and STREAMLIT_PROCESS.is_alive():
        try:
            logger.info("[STREAMLIT] Deteniendo proceso...")
            STREAMLIT_PROCESS.terminate()
            STREAMLIT_PROCESS.join(timeout=5)
            if STREAMLIT_PROCESS.is_alive():
                STREAMLIT_PROCESS.kill()
            logger.info("[STREAMLIT] Detenido")
        except Exception as e:
            logger.error(f"[STREAMLIT] Error al detener: {e}")
    
    logger.info("[SISTEMA] Todos los procesos detenidos")

# =============================================================================
# FUNCION PRINCIPAL
# =============================================================================

def abrir_navegador():
    time.sleep(5)
    url = "http://127.0.0.1:8501"
    try:
        webbrowser.open(url)
        logger.info(f"[WEB] Navegador abierto en {url}")
    except Exception as e:
        logger.warning(f"[WEB] No se pudo abrir navegador: {e}")

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
    print("  [MENSAJES] INICIANDO...")
    print("  [STREAMLIT] INICIANDO...")
    print("  ------------------------------------------------------")
    print()
    print("  Para ver logs, revisa: simpol_loader.log")
    print("  Presiona Ctrl+C para detener el sistema")
    print("  ------------------------------------------------------")
    print()

def main():
    global SISTEMA_ACTIVO, logger
    
    logger = setup_logging()
    
    if not verificar_instancia_unica():
        input("\nPresiona Enter para salir...")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("INICIANDO SIMPOL LOADER")
    logger.info(f"Ejecutable: {sys.executable}")
    logger.info(f"Directorio: {os.getcwd()}")
    if getattr(sys, 'frozen', False):
        logger.info(f"Modo: CONGELADO (EXE)")
        logger.info(f"_MEIPASS: {sys._MEIPASS}")
    else:
        logger.info(f"Modo: DESARROLLO")
    logger.info("=" * 70)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if getattr(sys, 'frozen', False):
        sys.path.insert(0, sys._MEIPASS)
        os.chdir(os.path.dirname(sys.executable))
        logger.info(f"Directorio de trabajo cambiado a: {os.getcwd()}")

    mostrar_consola()

    logger.info("[SISTEMA] Iniciando procesos...")
    
    if not iniciar_agente():
        logger.warning("[SISTEMA] El agente no se inicio correctamente")
    
    if not iniciar_enviador():
        logger.warning("[SISTEMA] El enviador no se inicio correctamente")
    
    if not iniciar_streamlit():
        logger.error("[SISTEMA] Streamlit no se inicio correctamente")
        print("\n[ERROR] No se pudo iniciar Streamlit")
        detener_todo()
        input("\nPresione ENTER para salir...")
        sys.exit(1)

    threading.Timer(3, abrir_navegador).start()

    logger.info("[SISTEMA] Sistema completamente iniciado")
    print("\n[SISTEMA] Sistema iniciado correctamente")
    print("[SISTEMA] Presiona Ctrl+C para detener\n")
    
    try:
        while SISTEMA_ACTIVO:
            if STREAMLIT_PROCESS and not STREAMLIT_PROCESS.is_alive():
                logger.error("[SISTEMA] Streamlit se detuvo inesperadamente")
                print("\n[ERROR] Streamlit se detuvo. Revisa los logs.")
                SISTEMA_ACTIVO = False
                break
            
            if AGENTE_PROCESS and not AGENTE_PROCESS.is_alive():
                logger.warning("[SISTEMA] El agente se detuvo, reintentando...")
                iniciar_agente()
            
            if ENVIADOR_PROCESS and not ENVIADOR_PROCESS.is_alive():
                logger.warning("[SISTEMA] El enviador se detuvo, reintentando...")
                iniciar_enviador()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("[SISTEMA] Interrupcion recibida")
    finally:
        detener_todo()
        eliminar_lock_file()
        logger.info("[SISTEMA] Sistema finalizado")
        print("\n[SISTEMA] Sistema finalizado correctamente")
        time.sleep(2)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()