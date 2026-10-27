import hmac

import psycopg
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
        return False, MENSAJE_LIMITE

    usuario = (usuario or "").strip()
    rol_esperado = ROLES.get(tipo_usuario)

    if not usuario or not contrasena:
        return False, "Ingresa tu usuario y contraseña."

    if rol_esperado is None:
        return False, "Selecciona un tipo de usuario válido."

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT contrasena, rol, activo
                FROM public.usuarios
                WHERE nombre_usuario = %s
                """,
                (usuario,),
            )
            registro = cursor.fetchone()

        if registro is None:
            return _fallo("Usuario o contraseña incorrectos.")

        contrasena_guardada, rol_guardado, activo = registro

        if not activo:
            return False, "La cuenta está desactivada."

        # comparación en tiempo constante
        if not hmac.compare_digest(
            contrasena.encode("utf-8"),
            (contrasena_guardada or "").encode("utf-8"),
        ):
            return _fallo("Usuario o contraseña incorrectos.")

        if (rol_guardado or "").lower() != rol_esperado:
            return _fallo("El tipo de usuario seleccionado no corresponde a esta cuenta.")

        _intentos_fallidos = 0
        return True, f"Bienvenido(a), {usuario}."

    except psycopg.Error as error:
        print(f"Error en autenticar: {error}")
        return False, "Ocurrió un error al consultar la base de datos."
    finally:
        conexion.close()