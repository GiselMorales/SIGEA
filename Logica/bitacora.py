import psycopg

from conexiondb.db import obtener_conexion

USUARIO_ADMIN = "admin"


def es_administrador(usuario):
    return str(usuario or "").strip().casefold() == USUARIO_ADMIN


def registrar_entrada_secretaria(cursor, usuario_id, nombre_usuario, tipo_usuario):
    tipo_usuario = str(tipo_usuario or "").strip().casefold()
    if tipo_usuario not in ("administrativo", "docente"):
        raise ValueError("Tipo de usuario inválido. Debe ser 'administrativo' o 'docente'.")
    cursor.execute(
        """
        INSERT INTO public.bitacora_accesos_secretaria
            (usuario_id, nombre_usuario, tipo_usuario)
        VALUES (%s, %s, %s)
        RETURNING acceso_id
        """,
        (usuario_id, nombre_usuario, tipo_usuario),
    )
    fila = cursor.fetchone()
    if fila is None:
        raise psycopg.DatabaseError(
            "La bitácora no devolvió el identificador de acceso creado."
        )
    return fila[0]


def registrar_salida(acceso_id):
    if acceso_id is None:
        return True, None

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar para registrar la salida."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.bitacora_accesos_secretaria
                    SET fecha_salida = CURRENT_TIMESTAMP
                    WHERE acceso_id = %s AND fecha_salida IS NULL
                    """,
                    (acceso_id,),
                )
        return True, None
    except psycopg.Error as error:
        print(f"No se pudo registrar la salida en la bitácora: {error}")
        return False, "No se pudo guardar la fecha de salida en la bitácora."
    finally:
        conexion.close()


def listar_entradas_secretarias(usuario_solicitante):
    if not es_administrador(usuario_solicitante):
        return None, "La bitácora de accesos solo está disponible para admin."

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT nombre_usuario, tipo_usuario, fecha_entrada, fecha_salida
                FROM public.bitacora_accesos_secretaria
                ORDER BY fecha_entrada DESC, acceso_id DESC
                """
            )
            filas = cursor.fetchall()

        return [
            {
                "usuario": fila[0],
                "tipo_usuario": fila[1],
                "fecha_entrada": fila[2],
                "fecha_salida": fila[3],
            }
            for fila in filas
        ], None

    except psycopg.Error as error:
        print(f"Error al consultar la bitácora de accesos: {error}")
        return None, (
            "No se pudo consultar la bitácora. Verifica que la tabla "
            "bitacora_accesos_secretaria esté creada en Supabase."
        )
    finally:
        conexion.close()