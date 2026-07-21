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

# =============================================================================
# CONFIGURACION
# =============================================================================
TELEGRAM_TOKEN = "8511465977:AAHAbgPqJ1pSndxZ2JeCcrbXBk0vMSxYx24"
TELEGRAM_CHAT_ID = "7766964399"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# =============================================================================
# RUTA DEL ARCHIVO DE MENSAJES
# =============================================================================
MENSAJES_FILE = r"\\DESKTOP-BFL80DV\Users\programadorje\Documents\archivos\Julian semestres\UNEG\trabajo de grado\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"

# =============================================================================
# CONFIGURACION DE FILTRO - SOLO ÚLTIMO MINUTO
# =============================================================================
# SOLO enviar mensajes del último minuto
# Esto evita spam y solo envía alertas realmente actuales
MINUTOS_A_MANTENER = 1
SEGUNDOS_A_MANTENER = MINUTOS_A_MANTENER * 60  # 60 segundos

# =============================================================================
# FUNCIONES
# =============================================================================
def obtener_hora_actual():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def sanitizar_mensaje(mensaje):
    if not mensaje:
        return mensaje
    mensaje = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', mensaje)
    if len(mensaje) > 4000:
        mensaje = mensaje[:4000] + "...\n[Mensaje truncado por longitud]"
    return mensaje

def get_log_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(get_log_dir(), "enviador_telegram.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{obtener_hora_actual()} - {msg}\n")
    except:
        pass
    print(msg)

def verificar_conexion():
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except:
        return False

def verificar_ruta_red(ruta):
    try:
        directorio = os.path.dirname(ruta)
        if os.path.exists(directorio):
            return True
        if ruta.startswith('\\\\'):
            import subprocess
            try:
                servidor = ruta.split('\\')[2]
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', '1000', servidor],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            except:
                return False
        return False
    except:
        return False

def crear_backup_automatico(mensajes):
    """Crea backup automático si hay muchos mensajes"""
    if len(mensajes) > 100:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.dirname(MENSAJES_FILE)
            backup_file = os.path.join(backup_dir, f"mensajes_backup_{timestamp}.json")
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(mensajes, f, ensure_ascii=False, indent=2)
            
            log(f"[BACKUP] Creado automáticamente: {backup_file} ({len(mensajes)} mensajes)")
            return backup_file
        except Exception as e:
            log(f"[BACKUP] Error: {e}")
            return None
    return None

def enviar_a_telegram(mensaje):
    try:
        mensaje_limpio = sanitizar_mensaje(mensaje)
        if not mensaje_limpio or len(mensaje_limpio.strip()) < 2:
            return False
        
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje_limpio
        }).encode('utf-8')
        
        req = urllib.request.Request(
            TELEGRAM_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(payload)
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            log(f"[OK] Enviado: {response.status}")
            return True
            
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode('utf-8')
            log(f"[ERROR] HTTP {e.code}: {e.reason}")
            if 'description' in error_body:
                log(f"[ERROR] {error_body}")
        except:
            log(f"[ERROR] HTTP {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        log(f"[ERROR] URL: {e.reason}")
        return False
    except socket.timeout:
        log(f"[ERROR] Timeout")
        return False
    except Exception as e:
        log(f"[ERROR] {e}")
        return False

# =============================================================================
# FUNCION PRINCIPAL - SOLO ÚLTIMO MINUTO
# =============================================================================
def procesar_mensajes():
    log("=" * 60)
    log("ENVIADOR SIMPOL - BANCO CARONI")
    log(f"Archivo: {MENSAJES_FILE}")
    log(f"Hora actual: {obtener_hora_actual()}")
    log(f"Manteniendo mensajes del último {MINUTOS_A_MANTENER} minuto")
    
    if getattr(sys, 'frozen', False):
        log("Modo: EJECUTABLE (.exe)")
    else:
        log("Modo: DESARROLLO")
    
    # Verificar conexiones
    if not verificar_conexion():
        log("[ERROR] Sin internet")
        return
    log("[OK] Conexion verificada")
    
    if MENSAJES_FILE.startswith('\\\\'):
        if not verificar_ruta_red(MENSAJES_FILE):
            log(f"[ERROR] Ruta red no accesible")
            return
        log("[OK] Ruta red accesible")
    
    log("=" * 60)
    
    # Si no existe el archivo, crearlo vacío
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
    
    # =============================================================
    # PASO 1: FILTRAR SOLO MENSAJES DEL ÚLTIMO MINUTO
    # =============================================================
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
            diferencia_segundos = (ahora - fecha).total_seconds()
            
            # SOLO mensajes del último minuto (60 segundos)
            if diferencia_segundos <= SEGUNDOS_A_MANTENER:
                mensajes_recientes.append(item)
            else:
                mensajes_antiguos.append(item)
        except:
            mensajes_recientes.append(item)
    
    # =============================================================
    # PASO 2: SI HAY MENSAJES ANTIGUOS, CREAR BACKUP Y LIMPIAR
    # =============================================================
    if mensajes_antiguos:
        log(f"[INFO] {len(mensajes_antiguos)} mensajes antiguos (> {MINUTOS_A_MANTENER} minuto)")
        
        # Crear backup automático
        if len(mensajes_antiguos) > 50:
            crear_backup_automatico(mensajes_antiguos)
        
        # Eliminar mensajes antiguos del archivo
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump(mensajes_recientes, f, ensure_ascii=False, indent=2)
            log(f"[INFO] {len(mensajes_antiguos)} mensajes antiguos ELIMINADOS")
        except Exception as e:
            log(f"[ERROR] Eliminando antiguos: {e}")
            return
    
    if not mensajes_recientes:
        log(f"[INFO] No hay mensajes del último minuto para enviar")
        # Si solo había mensajes antiguos, ya se eliminaron
        return
    
    log(f"[INFO] Procesando {len(mensajes_recientes)} mensajes del último minuto")
    
    # =============================================================
    # PASO 3: ENVIAR SOLO MENSAJES DEL ÚLTIMO MINUTO
    # =============================================================
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
            time.sleep(2)
    
    # =============================================================
    # PASO 4: ACTUALIZAR ARCHIVO CON FALLIDOS
    # =============================================================
    mensajes_finales = fallidos  # Solo los fallidos
    
    try:
        with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
            json.dump(mensajes_finales, f, ensure_ascii=False, indent=2)
        log(f"[INFO] Archivo actualizado: {len(mensajes_finales)} mensajes en cola")
    except Exception as e:
        log(f"[ERROR] Guardando: {e}")
    
    # =============================================================
    # PASO 5: RESUMEN FINAL
    # =============================================================
    log("=" * 60)
    log("RESUMEN:")
    log(f"  Originales: {total_original}")
    log(f"  Antiguos (> {MINUTOS_A_MANTENER} minuto): {len(mensajes_antiguos)} (ELIMINADOS)")
    log(f"  Enviados (último minuto): {len(enviados)}")
    log(f"  Fallidos: {len(fallidos)} (reintentarán)")
    log(f"  Quedan en cola: {len(mensajes_finales)}")
    
    if len(mensajes_antiguos) > 0:
        log(f"  💡 {len(mensajes_antiguos)} mensajes antiguos eliminados para evitar spam")
    
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