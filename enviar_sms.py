import json
import os
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from datetime import datetime

# =============================================================================
# CONFIGURACION DE CORREO GMAIL
# =============================================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "julianlopezcastillo12@gmail.com"
SMTP_PASSWORD = ""  # <-- PON AQUI TU CONTRASEÑA DE APLICACION (16 digitos)

# =============================================================================
# CONFIGURACION DE SMS - DIGITEL VENEZUELA
# =============================================================================
DESTINO_SMS = "584126918133@digitel.com.ve"

# =============================================================================
# RUTA DEL ARCHIVO DE MENSAJES (donde esta el JSON)
# =============================================================================
# Opcion 1: Si copias el archivo manualmente a la misma carpeta
MENSAJES_FILE = "mensajes_telegram_pendientes.json"

# Opcion 2: Si usas USB (cambia E: por la letra de tu USB)
# MENSAJES_FILE = r"E:\mensajes_telegram_pendientes.json"

# Opcion 3: Si usas carpeta compartida en red
# MENSAJES_FILE = r"\\CMSRV053\SIMPOL_Mensajes\mensajes_telegram_pendientes.json"

# =============================================================================
# LOGS
# =============================================================================
LOG_FILE = os.path.join(os.path.dirname(__file__), "enviador_sms.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except:
        pass
    print(msg)

def extraer_informacion_sms(mensaje):
    """Extrae solo la informacion mas importante para el SMS"""
    lineas = mensaje.strip().split('\n')
    texto_sms = ""
    
    for linea in lineas:
        linea = linea.strip()
        if any(key in linea for key in [
            "Servidor:", "IP:", "Componente:", "Estado:", 
            "ALERTA", "SISTEMA", "RESUELTA", "CRITICA", "PRECAUCION"
        ]):
            linea = linea.replace('=', '').replace('_', '').strip()
            if linea:
                texto_sms += linea + " | "
    
    if not texto_sms:
        texto_sms = mensaje[:140]
    
    if len(texto_sms) > 160:
        texto_sms = texto_sms[:157] + "..."
    
    return texto_sms

def enviar_sms(mensaje):
    try:
        texto_sms = extraer_informacion_sms(mensaje)
        
        msg = MIMEText(texto_sms, 'plain', 'utf-8')
        msg['Subject'] = 'SIMPOL'
        msg['From'] = SMTP_USER
        msg['To'] = DESTINO_SMS
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        log(f"✅ SMS Enviado: {texto_sms[:50]}...")
        return True
        
    except Exception as e:
        log(f"❌ Error enviando SMS: {e}")
        return False

def procesar_mensajes():
    log("=" * 60)
    log("INICIANDO ENVIADOR DE SMS (GMAIL -> DIGITEL)")
    log(f"Archivo: {MENSAJES_FILE}")
    log(f"Destino: {DESTINO_SMS}")
    log("=" * 60)
    
    if not os.path.exists(MENSAJES_FILE):
        log("📂 No hay mensajes pendientes (archivo no existe)")
        log("   Coloca el archivo mensajes_telegram_pendientes.json en la misma carpeta")
        return
    
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
        
        log(f"  [{idx+1}/{len(mensajes)}] Enviando SMS de {fecha}...")
        
        if enviar_sms(mensaje):
            enviados.append(item)
        else:
            fallidos.append(item)
        
        if idx < len(mensajes) - 1:
            time.sleep(2)
    
    if fallidos:
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump(fallidos, f, ensure_ascii=False, indent=2)
            log(f"⚠️ {len(fallidos)} SMS fallidos, guardados para reintentar")
        except Exception as e:
            log(f"❌ Error guardando mensajes fallidos: {e}")
    else:
        try:
            with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            log(f"✅ Archivo vaciado (todos los SMS enviados)")
        except Exception as e:
            log(f"❌ Error vaciando archivo: {e}")
    
    log("=" * 60)
    log(f"RESUMEN: {len(enviados)} enviados, {len(fallidos)} fallidos")
    log("=" * 60)

if __name__ == "__main__":
    try:
        procesar_mensajes()
    except KeyboardInterrupt:
        log("\n⏹️ Proceso interrumpido por el usuario")
    except Exception as e:
        log(f"❌ Error critico: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPresiona Enter para salir...")