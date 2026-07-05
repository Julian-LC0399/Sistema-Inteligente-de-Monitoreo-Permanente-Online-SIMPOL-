import json
import urllib.request
import urllib.error
import os
import time
import sys
from datetime import datetime

# =============================================================================
# CONFIGURACION DE TELEGRAM
# =============================================================================
TELEGRAM_TOKEN = "8511465977:AAHAbgPqJ1pSndxZ2JeCcrbXBk0vMSxYx24"
TELEGRAM_CHAT_ID = "7766964399"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# =============================================================================
# RUTA DEL ARCHIVO DE MENSAJES (CARPETA COMPARTIDA)
# =============================================================================
# ¡¡¡ CAMBIA ESTA RUTA POR LA CARPETA COMPARTIDA DEL SERVIDOR !!!
# Ejemplo: r"\\NOMBRE_SERVIDOR\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"
# Ejemplo: r"\\192.168.1.100\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"
# Ejemplo: r"Z:\mensajes_telegram_pendientes.json"  (si mapeaste unidad)
MENSAJES_FILE = r"\\NOMBRE_SERVIDOR\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"

# =============================================================================
# LOGS
# =============================================================================
LOG_FILE = os.path.join(os.path.dirname(__file__), "enviador_telegram.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except:
        pass
    print(msg)

# =============================================================================
# FUNCION PARA ENVIAR A TELEGRAM
# =============================================================================
def enviar_a_telegram(mensaje):
    try:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown"
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
            log(f"✅ Enviado: {response.status}")
            return True
            
    except urllib.error.HTTPError as e:
        log(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        log(f"❌ URL Error: {e.reason}")
        return False
    except Exception as e:
        log(f"❌ Error: {e}")
        return False

# =============================================================================
# FUNCION PRINCIPAL
# =============================================================================
def procesar_mensajes():
    log("=" * 60)
    log("INICIANDO ENVIADOR DE MENSAJES A TELEGRAM")
    log(f"Archivo: {MENSAJES_FILE}")
    log("=" * 60)
    
    # Verificar si existe el archivo
    if not os.path.exists(MENSAJES_FILE):
        log("📂 No hay mensajes pendientes (archivo no existe)")
        return
    
    # Leer mensajes
    try:
        with open(MENSAJES_FILE, "r", encoding="utf-8") as f:
            mensajes = json.load(f)
    except json.JSONDecodeError as e:
        log(f"❌ Error leyendo JSON: {e}")
        return
    except Exception as e:
        log(f"❌ Error leyendo archivo: {e}")
        return
    
    if not mensajes:
        log("📂 No hay mensajes pendientes (archivo vacio)")
        return
    
    log(f"📨 Procesando {len(mensajes)} mensajes pendientes...")
    
    enviados = []
    fallidos = []
    
    for idx, item in enumerate(mensajes):
        fecha = item.get("fecha", "Fecha desconocida")
        mensaje = item.get("mensaje", "")
        
        if not mensaje:
            log(f"  [{idx+1}/{len(mensajes)}] ⚠️ Mensaje vacio, saltando...")
            continue
        
        log(f"  [{idx+1}/{len(mensajes)}] Enviando mensaje de {fecha}...")
        
        if enviar_a_telegram(mensaje):
            enviados.append(item)
        else:
            fallidos.append(item)
        
        # Esperar entre mensajes para evitar rate limit
        if idx < len(mensajes) - 1:
            time.sleep(1)
    
    # Guardar solo los mensajes no enviados
    if fallidos:
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump(fallidos, f, ensure_ascii=False, indent=2)
            log(f"⚠️ {len(fallidos)} mensajes fallidos, guardados para reintentar")
        except Exception as e:
            log(f"❌ Error guardando mensajes fallidos: {e}")
    else:
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            log(f"✅ Archivo vaciado (todos los mensajes enviados)")
        except Exception as e:
            log(f"❌ Error vaciando archivo: {e}")
    
    log("=" * 60)
    log(f"RESUMEN: {len(enviados)} enviados, {len(fallidos)} fallidos")
    log("=" * 60)

# =============================================================================
# EJECUTAR
# =============================================================================
if __name__ == "__main__":
    try:
        procesar_mensajes()
    except KeyboardInterrupt:
        log("\n⏹️ Proceso interrumpido por el usuario")
    except Exception as e:
        log(f"❌ Error critico: {e}")
        import traceback
        traceback.print_exc()
    
    # Si se ejecuta con doble clic, esperar a que el usuario presione Enter
    if not sys.stdin.isatty():
        input("\nPresiona Enter para salir...")