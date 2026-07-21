import json
import urllib.request
import urllib.error
import os
import time
import sys
from datetime import datetime, timedelta
import socket
import re
import shutil
import ssl

# =============================================================================
# CONFIGURACION
# =============================================================================
TELEGRAM_TOKEN = "8511465977:AAHAbgPqJ1pSndxZ2JeCcrbXBk0vMSxYx24"
TELEGRAM_CHAT_ID = "7766964399"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# =============================================================================
# RUTA DEL ARCHIVO DE MENSAJES
# =============================================================================
def obtener_ruta_mensajes():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "mensajes_telegram_pendientes.json")
    else:
        return r"\\DESKTOP-BFL80DV\Users\programadorje\Documents\archivos\Julian semestres\UNEG\trabajo de grado\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"

MENSAJES_FILE = obtener_ruta_mensajes()

# =============================================================================
# CONFIGURACION DE FILTRO
# =============================================================================
MINUTOS_A_MANTENER = 1
SEGUNDOS_A_MANTENER = MINUTOS_A_MANTENER * 60

# =============================================================================
# LOGS
# =============================================================================
def get_log_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(get_log_dir(), "enviador_telegram.log")

def obtener_hora_actual():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{obtener_hora_actual()} - {msg}\n")
    except:
        pass
    print(msg)

# =============================================================================
# FUNCIONES DE DEPURACIÓN
# =============================================================================

def verificar_conexion_telegram():
    """Verifica que se pueda conectar a la API de Telegram"""
    try:
        log("[DEBUG] Verificando conexión a Telegram...")
        
        # Crear un contexto SSL que ignore errores (para el .exe)
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode('utf-8')
            log(f"[DEBUG] Conexión a Telegram exitosa")
            return True
            
    except urllib.error.URLError as e:
        log(f"[ERROR] No se puede conectar a Telegram: {e.reason}")
        log("[ERROR] Verifica que el .exe tenga acceso a internet")
        log("[ERROR] En el .exe, puede ser un problema de proxy o firewall")
        return False
    except Exception as e:
        log(f"[ERROR] Error verificando conexión a Telegram: {e}")
        return False

def sanitizar_mensaje(mensaje):
    if not mensaje:
        return mensaje
    mensaje = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', mensaje)
    if len(mensaje) > 4000:
        mensaje = mensaje[:4000] + "...\n[Mensaje truncado por longitud]"
    return mensaje

# =============================================================================
# FUNCION PARA ENVIAR A TELEGRAM CON DEPURACIÓN
# =============================================================================
def enviar_a_telegram(mensaje):
    """
    Envía mensaje a Telegram con logs detallados para depurar en el .exe
    """
    try:
        mensaje_limpio = sanitizar_mensaje(mensaje)
        
        if not mensaje_limpio or len(mensaje_limpio.strip()) < 2:
            log("[ERROR] Mensaje vacío o demasiado corto")
            return False
        
        # Preparar payload
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje_limpio
        }).encode('utf-8')
        
        # Configurar request
        req = urllib.request.Request(
            TELEGRAM_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(payload)
            }
        )
        
        # Enviar
        with urllib.request.urlopen(req, timeout=30) as response:
            log(f"[OK] Enviado: {response.status}")
            return True
            
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode('utf-8')
            log(f"[ERROR] HTTP {e.code}: {e.reason}")
            log(f"[ERROR] Detalle: {error_body}")
        except:
            log(f"[ERROR] HTTP {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        log(f"[ERROR] URL Error: {e.reason}")
        log("[ERROR] Esto puede ser un problema de red, proxy o SSL en el .exe")
        return False
    except socket.timeout:
        log(f"[ERROR] Timeout")
        return False
    except Exception as e:
        log(f"[ERROR] Error: {e}")
        import traceback
        log(traceback.format_exc())
        return False

# =============================================================================
# VERIFICAR CONEXION A INTERNET
# =============================================================================
def verificar_conexion():
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except:
        return False

# =============================================================================
# FUNCION PRINCIPAL
# =============================================================================
def procesar_mensajes():
    log("=" * 60)
    log("ENVIADOR SIMPOL - BANCO CARONI")
    log(f"Archivo: {MENSAJES_FILE}")
    log(f"Log: {LOG_FILE}")
    log(f"Hora actual: {obtener_hora_actual()}")
    log(f"Manteniendo mensajes del último {MINUTOS_A_MANTENER} minuto")
    
    if getattr(sys, 'frozen', False):
        log("Modo: EJECUTABLE (.exe)")
        log(f"Directorio EXE: {os.path.dirname(sys.executable)}")
        log(f"Python EXE: {sys.executable}")
    else:
        log("Modo: DESARROLLO")
    
    # Verificar conexión a internet
    if not verificar_conexion():
        log("[ERROR] Sin internet")
        return
    log("[OK] Conexion a internet verificada")
    
    # =============================================================
    # VERIFICAR CONEXIÓN A TELEGRAM (IMPORTANTE PARA EL .EXE)
    # =============================================================
    if not verificar_conexion_telegram():
        log("[ERROR] No se puede conectar a la API de Telegram")
        log("[ERROR] En el .exe, prueba con: pip install certifi")
        log("[ERROR] O verifica que el firewall no bloquee el .exe")
        return
    
    log("[OK] Conexión a Telegram verificada")
    
    # Verificar ruta de red
    if MENSAJES_FILE.startswith('\\\\'):
        if not os.path.exists(os.path.dirname(MENSAJES_FILE)):
            log(f"[WARN] Ruta de red no accesible: {MENSAJES_FILE}")
            log("[INFO] Usando archivo local...")
    
    log("=" * 60)
    
    # Crear archivo si no existe
    if not os.path.exists(MENSAJES_FILE):
        try:
            os.makedirs(os.path.dirname(MENSAJES_FILE), exist_ok=True)
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            log("[INFO] Archivo creado (estaba vacío)")
            return
        except Exception as e:
            log(f"[ERROR] Creando archivo: {e}")
            return
    
    # Leer mensajes
    try:
        with open(MENSAJES_FILE, "r", encoding="utf-8") as f:
            mensajes = json.load(f)
    except json.JSONDecodeError:
        log("[ERROR] Archivo corrupto, creando nuevo")
        with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return
    except Exception as e:
        log(f"[ERROR] Leyendo archivo: {e}")
        return
    
    if not mensajes:
        log("[INFO] No hay mensajes pendientes")
        return
    
    total_original = len(mensajes)
    log(f"[INFO] Total mensajes: {total_original}")
    
    # FILTRAR MENSAJES RECIENTES
    ahora = datetime.now()
    mensajes_recientes = []
    mensajes_antiguos = []
    
    for item in mensajes:
        fecha_str = item.get('fecha', '')
        if not fecha_str:
            mensajes_recientes.append(item)
            continue
        
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
            if (ahora - fecha).total_seconds() <= SEGUNDOS_A_MANTENER:
                mensajes_recientes.append(item)
            else:
                mensajes_antiguos.append(item)
        except:
            mensajes_recientes.append(item)
    
    # Eliminar mensajes antiguos
    if mensajes_antiguos:
        log(f"[INFO] {len(mensajes_antiguos)} mensajes antiguos (> {MINUTOS_A_MANTENER} minuto) ELIMINADOS")
        
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump(mensajes_recientes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"[ERROR] Eliminando antiguos: {e}")
            return
    
    if not mensajes_recientes:
        log("[INFO] No hay mensajes del último minuto para enviar")
        return
    
    log(f"[INFO] Procesando {len(mensajes_recientes)} mensajes del último minuto")
    
    # ENVIAR MENSAJES
    enviados = []
    fallidos = []
    
    for idx, item in enumerate(mensajes_recientes):
        fecha_original = item.get("fecha", "Fecha desconocida")
        mensaje = item.get("mensaje", "")
        
        if not mensaje:
            continue
        
        hora_envio = obtener_hora_actual()
        mensaje_completo = f"[{hora_envio}] Alerta: {fecha_original}\n{mensaje}"
        mensaje_completo = sanitizar_mensaje(mensaje_completo)
        
        log(f"  [{idx+1}/{len(mensajes_recientes)}] Enviando {fecha_original}...")
        
        if enviar_a_telegram(mensaje_completo):
            enviados.append(item)
        else:
            fallidos.append(item)
            time.sleep(5)
        
        if idx < len(mensajes_recientes) - 1:
            time.sleep(1)
    
    # ACTUALIZAR ARCHIVO CON FALLIDOS
    try:
        with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
            json.dump(fallidos, f, ensure_ascii=False, indent=2)
        log(f"[INFO] Archivo actualizado: {len(fallidos)} mensajes en cola")
    except Exception as e:
        log(f"[ERROR] Guardando: {e}")
    
    log("=" * 60)
    log("RESUMEN:")
    log(f"  Originales: {total_original}")
    log(f"  Antiguos (> {MINUTOS_A_MANTENER} min): {len(mensajes_antiguos)} (ELIMINADOS)")
    log(f"  Enviados: {len(enviados)}")
    log(f"  Fallidos: {len(fallidos)}")
    log(f"  Quedan en cola: {len(fallidos)}")
    log("=" * 60)

# =============================================================================
# EJECUTAR
# =============================================================================
if __name__ == "__main__":
    modo_auto = '--auto' in sys.argv
    
    if modo_auto:
        try:
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
        except:
            pass
    
    try:
        socket.setdefaulttimeout(30)
        procesar_mensajes()
    except KeyboardInterrupt:
        log("\n[STOP] Interrumpido")
    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{obtener_hora_actual()} - [CRITICO] {e}\n")
                import traceback
                traceback.print_exc(file=f)
        except:
            pass
    
    if not modo_auto and not sys.stdin.isatty():
        input("\nPresiona Enter para salir...")