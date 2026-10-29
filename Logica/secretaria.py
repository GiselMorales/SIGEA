import secrets
import string
import unicodedata

import psycopg
from psycopg import errors
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
            "Guarda estas credenciales y entrégalas a la secretaria."
        )

        return True, mensaje

    except psycopg.errors.UniqueViolation as error:
        restriccion = error.diag.constraint_name

        if restriccion == "administrativos_pkey":
            return False, "Ya existe una secretaria registrada con ese RFC."

        if restriccion == "administrativos_curp_key":
            return False, "Ya existe una secretaria registrada con esa CURP."

        if restriccion == "usuarios_nombre_usuario_key":
            return False, "El nombre de usuario ya existe. Intenta registrarlo nuevamente."

        return False, "Ya existe un registro con alguno de los datos únicos."

    except psycopg.Error as error:
        print(f"Error al registrar secretaria: {error}")
        return False, "Ocurrió un error al registrar a la secretaria."

    finally:
        conexion.close()


def obtener_secretaria(rfc):
    """Busca una secretaria por RFC. Devuelve (registro | None, error | None)."""
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.rfc, a.usuario_id, a.nombres, a.apellido_paterno,
                       a.apellido_materno, a.sexo, a.puesto, a.activo,
                       a.curp, a.fecha_nacimiento, a.grado_academico,
                       u.nombre_usuario, u.activo
                FROM public.administrativos AS a
                JOIN public.usuarios AS u ON u.usuario_id = a.usuario_id
                WHERE UPPER(a.rfc) = %s
                """,
                (str(rfc).strip().upper(),),
            )
            fila = cursor.fetchone()

        if fila is None:
            return None, None
        registro = {
            "rfc": fila[0],
            "usuario_id": fila[1],
            "nombre": fila[2] or "",
            "apellido_paterno": fila[3] or "",
            "apellido_materno": fila[4] or "",
            "sexo": fila[5] or "",
            "puesto": fila[6] or "",
            "activo": bool(fila[7]),
            "curp": fila[8] or "",
            "fecha_nacimiento": fila[9].strftime("%d/%m/%Y") if fila[9] else "",
            "grado_academico": fila[10] or "",
            "usuario": fila[11] or "",
            "usuario_activo": bool(fila[12]),
        }
        registro["nombre_completo"] = " ".join(
            parte for parte in (
                registro["nombre"],
                registro["apellido_paterno"],
                registro["apellido_materno"],
            ) if parte
        )
        return registro, None
    except psycopg.Error as error:
        print(f"Error al buscar secretaria: {error}")
        return None, "No se pudo consultar la base de datos."
    finally:
        conexion.close()


def actualizar_secretaria(datos):
    """Actualiza los datos editables de una secretaria identificada por su RFC."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.administrativos
                    SET nombres = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s,
                        sexo = %s,
                        puesto = %s,
                        curp = %s,
                        fecha_nacimiento = %s,
                        grado_academico = %s
                    WHERE rfc = %s
                    RETURNING rfc
                    """,
                    (
                        datos["nombre"],
                        datos["apellido_paterno"],
                        datos.get("apellido_materno") or None,
                        datos["sexo"],
                        datos["puesto"],
                        datos.get("curp") or None,
                        datos.get("fecha_nacimiento_iso"),
                        datos.get("grado_academico") or None,
                        datos["rfc"],
                    ),
                )
                if cursor.fetchone() is None:
                    raise ValueError("No se encontró la secretaria que deseas modificar.")

        return True, f"Datos de {datos['rfc']} actualizados correctamente."
    except errors.UniqueViolation as error:
        restriccion = getattr(error.diag, "constraint_name", "") or ""
        if restriccion == "administrativos_curp_key":
            return False, "Esa CURP ya pertenece a otra persona."
        return False, "Ya existe un registro con alguno de los datos únicos."
    except ValueError as error:
        return False, str(error)
    except psycopg.Error as error:
        print(f"Error al actualizar secretaria: {error}")
        return False, "No se pudieron guardar los cambios en la base de datos."
    finally:
        conexion.close()


def dar_de_baja_secretaria(rfc):
    """Elimina la secretaria y su usuario dentro de una transacción."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT usuario_id
                    FROM public.administrativos
                    WHERE rfc = %s
                    FOR UPDATE
                    """,
                    (str(rfc).strip().upper(),),
                )
                fila = cursor.fetchone()
                if fila is None:
                    raise ValueError("No existe una secretaria con ese RFC.")

                cursor.execute(
                    "DELETE FROM public.administrativos WHERE rfc = %s",
                    (str(rfc).strip().upper(),),
                )
                cursor.execute(
                    "DELETE FROM public.usuarios WHERE usuario_id = %s",
                    (fila[0],),
                )

        return True, f"Se eliminó la secretaria con RFC {rfc} y su cuenta de acceso."
    except ValueError as error:
        return False, str(error)
    except errors.ForeignKeyViolation as error:
        print(f"No se pudo eliminar la secretaria por una relación existente: {error}")
        return False, (
            "No se pudo eliminar el registro porque su cuenta tiene relaciones "
            "en otros datos. No se realizaron cambios."
        )
    except psycopg.Error as error:
        print(f"Error al eliminar secretaria: {error}")
        return False, "No se pudo eliminar la secretaria de la base de datos."
    finally:
        conexion.close()


def listar_secretarias(criterio="Todos", valor=""):
    """Consulta secretarias por RFC, nombre, CURP, puesto o usuario."""
    columnas = {
        "RFC": ["a.rfc"],
        "Nombre": [
            "a.nombres || ' ' || a.apellido_paterno || ' ' "
            "|| COALESCE(a.apellido_materno, '')"
        ],
        "CURP": ["a.curp"],
        "Puesto": ["a.puesto"],
        "Usuario": ["u.nombre_usuario"],
    }
    buscar_en = columnas.get(criterio, [
        "a.rfc",
        "a.nombres || ' ' || a.apellido_paterno || ' ' "
        "|| COALESCE(a.apellido_materno, '')",
        "a.curp",
        "a.puesto",
        "u.nombre_usuario",
    ])
    parametros = [f"%{valor.strip()}%"] * len(buscar_en) if valor.strip() else []
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
                SELECT a.rfc, a.nombres, a.apellido_paterno,
                       a.apellido_materno, a.sexo, a.puesto, a.activo,
                       a.curp, a.fecha_nacimiento, a.grado_academico,
                       u.nombre_usuario, u.activo
                FROM public.administrativos AS a
                JOIN public.usuarios AS u ON u.usuario_id = a.usuario_id
                {where}
                ORDER BY a.apellido_paterno, a.apellido_materno, a.nombres
                """,
                parametros,
            )
            filas = cursor.fetchall()

        registros = []
        for fila in filas:
            registro = {
                "rfc": fila[0],
                "nombre": fila[1] or "",
                "apellido_paterno": fila[2] or "",
                "apellido_materno": fila[3] or "",
                "sexo": fila[4] or "",
                "puesto": fila[5] or "",
                "activo": bool(fila[6]),
                "curp": fila[7] or "",
                "fecha_nacimiento": fila[8].strftime("%d/%m/%Y") if fila[8] else "",
                "grado_academico": fila[9] or "",
                "usuario": fila[10] or "",
                "usuario_activo": bool(fila[11]),
            }
            registro["nombre_completo"] = " ".join(
                parte for parte in (
                    registro["nombre"],
                    registro["apellido_paterno"],
                    registro["apellido_materno"],
                ) if parte
            )
            registros.append(registro)
        return registros, None
    except psycopg.Error as error:
        print(f"Error al consultar secretarias: {error}")
        return None, "No se pudieron consultar las secretarias."
    finally:
        conexion.close()