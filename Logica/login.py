import hmac

import psycopg
from Logica.bitacora import registrar_entrada_secretaria
from conexiondb.db import obtener_conexion

ROLES = {
    "Secretaría": "administrativo",
    "Administrativo": "administrativo",
    "Docente": "docente",
}

MAX_INTENTOS = 3
MENSAJE_LIMITE = "Superaste el límite de intentos. Regresa más tarde."

_intentos_fallidos = 0


def limite_superado():
    return _intentos_fallidos >= MAX_INTENTOS


def _fallo(mensaje):
    """Cuenta un intento fallido y arma el mensaje para el usuario."""
    global _intentos_fallidos
    _intentos_fallidos += 1

    if limite_superado():
        return False, MENSAJE_LIMITE

    restantes = MAX_INTENTOS - _intentos_fallidos
    return False, f"{mensaje}\n\nIntentos restantes: {restantes}"


def autenticar(usuario, contrasena, tipo_usuario):
    global _intentos_fallidos

    if limite_superado():
        return False, MENSAJE_LIMITE, None

    usuario = (usuario or "").strip()
    rol_esperado = ROLES.get(tipo_usuario)

    if not usuario or not contrasena:
        return False, "Ingresa tu usuario y contraseña.", None

    if rol_esperado is None:
        return False, "Selecciona un tipo de usuario válido.", None

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos.", None

    acceso_id = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT usuario_id, contrasena, rol, activo
                FROM public.usuarios
                WHERE nombre_usuario = %s
                """,
                (usuario,),
            )
            registro = cursor.fetchone()

        if registro is None:
            correcto, mensaje = _fallo("Usuario o contraseña incorrectos.")
            return correcto, mensaje, None

        usuario_id, contrasena_guardada, rol_guardado, activo = registro

        if not activo:
            return False, "La cuenta está desactivada.", None

        # comparación en tiempo constante
        if not hmac.compare_digest(
            contrasena.encode("utf-8"),
            (contrasena_guardada or "").encode("utf-8"),
        ):
            correcto, mensaje = _fallo("Usuario o contraseña incorrectos.")
            return correcto, mensaje, None

        if (rol_guardado or "").lower() != rol_esperado:
            correcto, mensaje = _fallo(
                "El tipo de usuario seleccionado no corresponde a esta cuenta."
            )
            return correcto, mensaje, None

        if usuario.casefold() != "admin":
            try:
                with conexion.cursor() as cursor:
                    acceso_id = registrar_entrada_secretaria(
                        cursor, usuario_id, usuario, rol_esperado
                    )
                conexion.commit()
            except psycopg.Error as error:
                print(f"No se pudo registrar el acceso del usuario: {error}")
                return False, (
                    "No se pudo registrar tu acceso. Verifica que la bitácora "
                    "de accesos esté instalada en Supabase."
                ), None

        _intentos_fallidos = 0
        return True, f"Bienvenido(a), {usuario}.", acceso_id

    except psycopg.Error as error:
        print(f"Error en autenticar: {error}")
        return False, "Ocurrió un error al consultar la base de datos.", None
    finally:
        conexion.close()