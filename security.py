import bcrypt
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN DE POLÍTICAS DE SEGURIDAD
# ==========================================
MAX_INTENTOS = 5
TIEMPO_BLOQUEO_MINUTOS = 15
HISTORIAL_CLAVES_PERMITIDO = 3

# ==========================================
# FUNCIONES CRIPTOGRÁFICAS
# ==========================================
def hashear_clave(clave_plana: str) -> str:
    bytes_clave = clave_plana.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(bytes_clave, salt).decode('utf-8')

def verificar_clave(clave_plana: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(clave_plana.encode('utf-8'), hash_guardado.encode('utf-8'))
    except ValueError:
        return False

def validar_politica_clave(nueva_clave: str) -> tuple[bool, str]:
    if len(nueva_clave) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isupper() for c in nueva_clave):
        return False, "Debe contener al menos una letra mayúscula."
    if not any(c.isdigit() for c in nueva_clave):
        return False, "Debe contener al menos un número."
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in nueva_clave):
        return False, "Debe contener al menos un carácter especial (!, @, #, $, etc.)."
    return True, "Válida"

# ==========================================
# FUNCIONES AUXILIARES INTERNAS (AUDITORÍA)
# ==========================================
def _registrar_log(cursor, usuario_id, usuario, cargo, rol, ip_cliente, resultado):
    cursor.execute("""
        INSERT INTO log_accesos (usuario_id, usuario, cargo, rol, ip_cliente, resultado) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (usuario_id, usuario, cargo, rol, ip_cliente, resultado))

def _registrar_auditoria(cursor, usuario_id, usuario_afectado, accion, valor_anterior=None, valor_nuevo=None, comentario=None):
    cursor.execute("""
        INSERT INTO historico_usuarios (usuario_id, usuario_afectado, accion_realizada, valor_anterior, valor_nuevo, commentario) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (usuario_id, usuario_afectado, accion, valor_anterior, valor_nuevo, comentario))

# ==========================================
# LÓGICA DE AUTENTICACIÓN Y CAMBIO DE CLAVE
# ==========================================
def procesar_login(cursor, usuario: str, clave_plana: str, ip_cliente: str = '127.0.0.1') -> dict:
    cursor.execute("""
        SELECT id, clave, debe_cambiar_clave, intentos_fallidos, bloqueado_hasta, rol, estado, usuario, cargo 
        FROM usuarios WHERE usuario = %s
    """, (usuario,))
    user = cursor.fetchone()

    if not user:
        _registrar_log(cursor, None, usuario, None, None, ip_cliente, 'FALLIDO')
        return {"exito": False, "mensaje": "Credenciales incorrectas."}

    # 1. Verificar contraseña PRIMERO (para auto-sanar bloqueos si acierta)
    clave_correcta = verificar_clave(clave_plana, user['clave'])

    if clave_correcta:
        # --- AUTO-SANACIÓN ---
        # Si la clave es correcta, limpiamos bloqueos, intentos fallidos y forzamos debe_cambiar_clave=0
        cursor.execute("""
            UPDATE usuarios 
            SET intentos_fallidos = 0, bloqueado_hasta = NULL, debe_cambiar_clave = 0 
            WHERE id = %s
        """, (user['id'],))
        
        _registrar_log(cursor, user['id'], usuario, user['cargo'], user['rol'], ip_cliente, 'EXITOSO')
        return {
            "exito": True,
            "usuario_id": user['id'],
            "rol": user['rol'],
            "cargo": user['cargo'],
            "debe_cambiar_clave": False # Ya lo limpiamos arriba
        }

    # 2. Si la clave es incorrecta, evaluar bloqueos
    if user['bloqueado_hasta'] and user['bloqueado_hasta'] > datetime.now():
        tiempo_restante = int((user['bloqueado_hasta'] - datetime.now()).total_seconds() // 60) + 1
        _registrar_log(cursor, user['id'], usuario, user['cargo'], user['rol'], ip_cliente, 'BLOQUEADO')
        return {"exito": False, "mensaje": f"Cuenta bloqueada. Intente en {tiempo_restante} minutos."}

    if user['estado'] == 0:
        _registrar_log(cursor, user['id'], usuario, user['cargo'], user['rol'], ip_cliente, 'SUSPENDIDO')
        return {"exito": False, "mensaje": "Cuenta suspendida. Contacte al administrador."}

    # 3. Clave incorrecta: incrementar intentos
    nuevos_intentos = user['intentos_fallidos'] + 1
    if nuevos_intentos >= MAX_INTENTOS:
        bloqueo = datetime.now() + timedelta(minutes=TIEMPO_BLOQUEO_MINUTOS)
        cursor.execute("UPDATE usuarios SET intentos_fallidos = %s, bloqueado_hasta = %s WHERE id = %s", 
                       (nuevos_intentos, bloqueo, user['id']))
        _registrar_log(cursor, user['id'], usuario, user['cargo'], user['rol'], ip_cliente, 'BLOQUEADO')
        return {"exito": False, "mensaje": f"Demasiados intentos. Bloqueado por {TIEMPO_BLOQUEO_MINUTOS} min."}
    else:
        cursor.execute("UPDATE usuarios SET intentos_fallidos = %s WHERE id = %s", (nuevos_intentos, user['id']))
        _registrar_log(cursor, user['id'], usuario, user['cargo'], user['rol'], ip_cliente, 'FALLIDO')
        return {"exito": False, "mensaje": f"Credenciales incorrectas. Intentos restantes: {MAX_INTENTOS - nuevos_intentos}"}

def cambiar_clave(cursor, usuario_id: int, clave_actual: str, clave_nueva: str, es_admin: bool = False, admin_id: int = None) -> dict:
    cursor.execute("SELECT clave, usuario FROM usuarios WHERE id = %s", (usuario_id,))
    user = cursor.fetchone()
    if not user:
        return {"exito": False, "mensaje": "Usuario no encontrado."}

    if not es_admin:
        if not verificar_clave(clave_actual, user['clave']):
            return {"exito": False, "mensaje": "La contraseña actual es incorrecta."}

    es_valida, msg = validar_politica_clave(clave_nueva)
    if not es_valida:
        return {"exito": False, "mensaje": msg}

    cursor.execute("""
        SELECT clave_hash FROM historico_claves 
        WHERE usuario_id = %s ORDER BY fecha_cambio DESC LIMIT %s
    """, (usuario_id, HISTORIAL_CLAVES_PERMITIDO))
    
    for row in cursor.fetchall():
        if verificar_clave(clave_nueva, row['clave_hash']):
            return {"exito": False, "mensaje": f"No puedes reutilizar tus últimas {HISTORIAL_CLAVES_PERMITIDO} contraseñas."}

    cursor.execute("INSERT INTO historico_claves (usuario_id, clave_hash, cambiado_por) VALUES (%s, %s, %s)", 
                   (usuario_id, user['clave'], admin_id or usuario_id))

    nuevo_hash = hashear_clave(clave_nueva)
    
    # Forzamos la actualización correcta
    cursor.execute("""
        UPDATE usuarios 
        SET clave = %s, debe_cambiar_clave = 0, fecha_ultimo_cambio_clave = NOW(), intentos_fallidos = 0, bloqueado_hasta = NULL 
        WHERE id = %s
    """, (nuevo_hash, usuario_id))

    _registrar_auditoria(
        cursor, 
        usuario_id=admin_id or usuario_id, 
        usuario_afectado=user['usuario'], 
        accion='CAMBIO_CLAVE', 
        comentario='Contraseña actualizada correctamente.'
    )

    return {"exito": True, "mensaje": "Contraseña actualizada correctamente."}