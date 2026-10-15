import psycopg
from conexiondb.db import obtener_conexion

def autenticar(usuario, contrasena, tipo_usuario):
    roles = {
        "Secretaría": "administrativo",
        "Administrativo": "administrativo",
        "Docente": "docente",
    }
    rol_esperado = roles.get(tipo_usuario)

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
                FROM usuarios
                WHERE nombre_usuario = %s
                """,
                (usuario,),
            )
            registro = cursor.fetchone()

        if registro is None:
            return False, "Usuario o contraseña incorrectos."

        contrasena_guardada, rol_guardado, activo = registro

        if not activo:
            return False, "La cuenta está desactivada."

        if contrasena != contrasena_guardada:
            return False, "Usuario o contraseña incorrectos."

        if rol_guardado != rol_esperado:
            return False, "El tipo de usuario seleccionado no corresponde a esta cuenta."

        return True, f"Bienvenido(a), {usuario}."

    except psycopg.Error:
        return False, "Ocurrió un error al consultar la base de datos."
    finally:
        conexion.close()