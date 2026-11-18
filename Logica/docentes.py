import secrets
import string
import unicodedata

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


def registrar_docente(datos):
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

                # Crear la cuenta del docente.
                cursor.execute(
                    """
                    INSERT INTO usuarios (
                        nombre_usuario,
                        contrasena,
                        rol
                    )
                    VALUES (%s, %s, %s)
                    RETURNING usuario_id
                    """,
                    (usuario, contrasena, "docente"),
                )

                usuario_id = cursor.fetchone()[0]

                # Registrar los datos personales y académicos.
                cursor.execute(
                    """
                    INSERT INTO docentes (
                        rfc,
                        usuario_id,
                        nombres,
                        apellido_paterno,
                        apellido_materno
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        datos["rfc"],
                        usuario_id,
                        datos["nombre"],
                        datos["apellido_paterno"],
                        datos.get("apellido_materno") or None,
                    ),
                )

        mensaje = (
            "DOCENTE REGISTRADO CORRECTAMENTE\n\n"
            f"Nombre: {datos['nombre']} "
            f"{datos['apellido_paterno']} "
            f"{datos.get('apellido_materno') or ''}\n"
            f"RFC: {datos['rfc']}\n"
            f"Usuario: {usuario}\n"
            f"Contraseña inicial: {contrasena}\n\n"
            "Guarda estas credenciales y entrégalas al docente."
        )

        return True, mensaje

    except psycopg.errors.UniqueViolation as error:
        restriccion = error.diag.constraint_name

        if restriccion == "docentes_pkey":
            return False, "Ya existe un docente registrado con ese RFC."

        if restriccion == "usuarios_nombre_usuario_key":
            return False, "El nombre de usuario ya existe. Intenta registrarlo nuevamente."

        return False, "Ya existe un registro con alguno de los datos únicos."

    except psycopg.Error as error:
        print(f"Error al registrar docente: {error}")
        return False, "Ocurrió un error al registrar al docente."

    finally:
        conexion.close()


def obtener_docente(rfc):
    """Busca un docente por RFC y devuelve sus datos junto con su usuario."""
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT d.rfc, d.usuario_id, d.nombres, d.apellido_paterno,
                       d.apellido_materno, u.nombre_usuario
                FROM public.docentes AS d
                JOIN public.usuarios AS u ON u.usuario_id = d.usuario_id
                WHERE UPPER(d.rfc) = %s
                """,
                (str(rfc).strip().upper(),),
            )
            fila = cursor.fetchone()

        if fila is None:
            return None, None

        docente = {
            "rfc": fila[0],
            "usuario_id": fila[1],
            "nombre": fila[2] or "",
            "apellido_paterno": fila[3] or "",
            "apellido_materno": fila[4] or "",
            "usuario": fila[5] or "",
        }
        docente["nombre_completo"] = " ".join(
            parte for parte in (
                docente["nombre"],
                docente["apellido_paterno"],
                docente["apellido_materno"],
            ) if parte
        )
        return docente, None
    except psycopg.Error as error:
        print(f"Error al buscar docente: {error}")
        return None, "No se pudo consultar la base de datos."
    finally:
        conexion.close()


def actualizar_docente(datos):
    """Actualiza el nombre del docente; el RFC y la cuenta no se modifican."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.docentes
                    SET nombres = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s
                    WHERE rfc = %s
                    RETURNING rfc
                    """,
                    (
                        datos["nombre"],
                        datos["apellido_paterno"],
                        datos.get("apellido_materno") or None,
                        str(datos["rfc"]).strip().upper(),
                    ),
                )
                if cursor.fetchone() is None:
                    raise ValueError("No se encontró el docente que deseas modificar.")
        return True, f"Datos de {datos['rfc']} actualizados correctamente."
    except psycopg.errors.UniqueViolation:
        return False, "Ya existe un registro con alguno de los datos únicos."
    except ValueError as error:
        return False, str(error)
    except psycopg.Error as error:
        print(f"Error al actualizar docente: {error}")
        return False, "No se pudieron guardar los cambios en la base de datos."
    finally:
        conexion.close()


def dar_de_baja_docente(rfc, usuario_actual=""):
    """Bloquea la baja hasta que la base tenga un mecanismo de estado seguro."""
    return False, (
        "La baja de docentes está deshabilitada: la base de datos ya no cuenta "
        "con una columna de estado para bloquear el acceso."
    )


def listar_docentes(criterio="Todos", valor=""):
    """Lista docentes por RFC, nombre o usuario."""
    columnas = {
        "RFC": ["d.rfc"],
        "Nombre": [
            "d.nombres || ' ' || d.apellido_paterno || ' ' "
            "|| COALESCE(d.apellido_materno, '')"
        ],
        "Usuario": ["u.nombre_usuario"],
    }
    buscar_en = columnas.get(criterio, [
        "d.rfc",
        "d.nombres || ' ' || d.apellido_paterno || ' ' "
        "|| COALESCE(d.apellido_materno, '')",
        "u.nombre_usuario",
    ])
    valor = str(valor or "").strip()
    parametros = [f"%{valor}%"] * len(buscar_en) if valor else []
    where = (
        "WHERE " + " OR ".join(f"{columna} ILIKE %s" for columna in buscar_en)
        if parametros else ""
    )

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT d.rfc, d.nombres, d.apellido_paterno,
                       d.apellido_materno, u.nombre_usuario
                FROM public.docentes AS d
                JOIN public.usuarios AS u ON u.usuario_id = d.usuario_id
                {where}
                ORDER BY d.apellido_paterno, d.apellido_materno, d.nombres
                """,
                parametros,
            )
            filas = cursor.fetchall()

        docentes = []
        for fila in filas:
            docente = {
                "rfc": fila[0],
                "nombre": fila[1] or "",
                "apellido_paterno": fila[2] or "",
                "apellido_materno": fila[3] or "",
                "usuario": fila[4] or "",
            }
            docente["nombre_completo"] = " ".join(
                parte for parte in (
                    docente["nombre"],
                    docente["apellido_paterno"],
                    docente["apellido_materno"],
                ) if parte
            )
            docentes.append(docente)
        return docentes, None
    except psycopg.Error as error:
        print(f"Error al consultar docentes: {error}")
        return None, "No se pudieron consultar los docentes."
    finally:
        conexion.close()
