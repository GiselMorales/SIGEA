import secrets
import string
import unicodedata
from datetime import datetime

import psycopg
from conexiondb.db import obtener_conexion

def generar_usuario(nombres, apellido_paterno, cursor):
    nombre = f"{nombres.split()[0]}.{apellido_paterno}".lower()

    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(
        caracter for caracter in nombre
        if not unicodedata.combining(caracter)
    )
    nombre = "".join(
        caracter if caracter.isalnum() or caracter == "." else ""
        for caracter in nombre
    )

    usuario = nombre
    consecutivo = 1

    while True:
        cursor.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE nombre_usuario = %s
            """,
            (usuario,),
        )

        if cursor.fetchone() is None:
            return usuario

        usuario = f"{nombre}{consecutivo}"
        consecutivo += 1


def generar_contrasena(longitud=12):
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(
        secrets.choice(caracteres)
        for _ in range(longitud)
    )


def registrar_secretaria(datos):
    conexion = obtener_conexion()

    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                usuario = generar_usuario(
                    datos["nombre"],
                    datos["apellido_paterno"],
                    cursor,
                )
                contrasena = generar_contrasena()

                cursor.execute(
                    """
                    INSERT INTO usuarios (
                        nombre_usuario,
                        contrasena,
                        rol,
                        activo
                    )
                    VALUES (%s, %s, %s, TRUE)
                    RETURNING usuario_id
                    """,
                    (usuario, contrasena, "administrativo"),
                )

                usuario_id = cursor.fetchone()[0]

                # Registrar los datos personales y académicos.
                cursor.execute(
                    """
                    INSERT INTO administrativos (
                        rfc,
                        usuario_id,
                        nombres,
                        apellido_paterno,
                        apellido_materno,
                        sexo,
                        puesto,
                        activo,
                        curp, 
                        fecha_nacimiento,
                        grado_academico
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s
                    )
                    """,
                    (
                        datos["rfc"],
                        usuario_id,
                        datos["nombre"],
                        datos["apellido_paterno"],
                        datos.get("apellido_materno"),
                        datos["sexo"],
                        datos["puesto"],
                        datos.get("curp"),
                        datos.get("fecha_nacimiento_iso"),
                        datos["grado_academico"],
                    ),
                )

        mensaje = (
            "SECRETARIA REGISTRADO CORRECTAMENTE\n\n"
            f"Nombre: {datos['nombre']} "
            f"{datos['apellido_paterno']} "
            f"{datos.get('apellido_materno') or ''}\n"
            f"RFC: {datos['rfc']}\n"
            f"Usuario: {usuario}\n"
            f"Contraseña inicial: {contrasena}\n\n"
            "Guarda estas credenciales y entrégalas al secretaria."
        )

        return True, mensaje

    except psycopg.errors.UniqueViolation as error:
        restriccion = error.diag.constraint_name

        if restriccion == "administrativo_pkey":
            return False, "Ya existe una secretaria registrada con ese RFC."

        if restriccion == "usuarios_nombre_usuario_key":
            return False, "El nombre de usuario ya existe. Intenta registrarlo nuevamente."

        return False, "Ya existe un registro con alguno de los datos únicos."

    except psycopg.Error as error:
        print(f"Error al registrar secretaria: {error}")
        return False, "Ocurrió un error al registrar a la secretaria."

    finally:
        conexion.close()