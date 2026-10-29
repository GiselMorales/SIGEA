
import psycopg
from psycopg import errors

from conexiondb.db import obtener_conexion
from Logica.validaciones import CARRERAS

CARRERA_CLAVE = "ISC"

MENSAJES_UNICOS = {
    "alumnos_curp_key": "Esa CURP ya está registrada en otro alumno.",
    "alumnos_correo_personal_key": "Ese correo personal ya está registrado en otro alumno.",
    "alumnos_numero_ficha_key": "Ese número de ficha ya está registrado.",
}


def obtener_alumno(clave):
    """Busca por número de control o de ficha (cualquier número).
    Devuelve (alumno | None, mensaje_de_error | None). El alumno trae los datos
    con los mismos nombres que usan los campos de las ventanas de alta."""
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT numero_control, numero_ficha, nombres, apellido_paterno,
                       apellido_materno, fecha_nacimiento, curp, sexo,
                       tipo_sanguineo, calle, manzana, lote, colonia,
                       codigo_postal, municipio, estado, pais, telefono,
                       correo_personal, escuela_procedencia, promedio_previo,
                       contacto_emergencia_nombre, contacto_emergencia_parentesco,
                       contacto_emergencia_telefono, estado_alumno, semestre_actual
                FROM public.alumnos
                WHERE numero_control = %s OR numero_ficha = %s
                ORDER BY (numero_control = %s) DESC
                LIMIT 1
                """,
                (clave, clave, clave),
            )
            f = cursor.fetchone()

        if f is None:
            return None, None

        alumno = {
            "numero_control": f[0],
            "ficha": f[1],
            "nombre": f[2] or "",
            "apellido_paterno": f[3] or "",
            "apellido_materno": f[4] or "",
            "fecha_nacimiento": f[5].strftime("%d/%m/%Y") if f[5] else "",
            "curp": (f[6] or "").strip(),
            "sexo": f[7] or "",
            "tipo_sangre": f[8] or "",
            "calle": f[9] or "",
            "manzana": f[10] or "",
            "lote": f[11] or "",
            "colonia": f[12] or "",
            "cp": (f[13] or "").strip(),
            "municipio": f[14] or "",
            "estado": f[15] or "",
            "pais": f[16] or "",
            "telefono": f[17] or "",
            "correo": f[18] or "",
            "carrera": CARRERAS[0],
            "escuela_procedencia": f[19] or "",
            "promedio": "" if f[20] is None else f"{float(f[20]):.2f}",
            "contacto_emergencia_nombre": f[21] or "",
            "contacto_emergencia_parentesco": f[22] or "",
            "contacto_emergencia_telefono": f[23] or "",
            "estado_alumno": (f[24] or "").lower(),
            "semestre_actual": f[25],
        }
        nombre = " ".join(
            p for p in (alumno["nombre"], alumno["apellido_paterno"], alumno["apellido_materno"]) if p
        )
        alumno["nombre_completo"] = nombre
        if alumno["estado_alumno"] == "baja":
            return None, "Ese alumno ya está dado de baja."
        return alumno, None

    except psycopg.Error as error:
        print(f"Error al buscar alumno: {error}")
        return None, "No se pudo consultar la base de datos."
    finally:
        conexion.close()


def actualizar_alumno(datos):
    """UPDATE de los datos editables. `datos` trae lo validado por las secciones."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT carrera_id FROM public.carreras WHERE clave = %s",
                    (CARRERA_CLAVE,),
                )
                carrera = cursor.fetchone()
                if carrera is None:
                    raise ValueError("No existe la carrera ISC en la base de datos.")

                cursor.execute(
                    """
                    UPDATE public.alumnos SET
                        nombres = %s, apellido_paterno = %s, apellido_materno = %s,
                        curp = %s, fecha_nacimiento = %s, sexo = %s,
                        tipo_sanguineo = %s,
                        calle = %s, manzana = %s, lote = %s, colonia = %s,
                        codigo_postal = %s, municipio = %s, estado = %s, pais = %s,
                        telefono = %s, correo_personal = %s,
                        carrera_id = %s, escuela_procedencia = %s,
                        promedio_previo = %s,
                        contacto_emergencia_nombre = %s,
                        contacto_emergencia_parentesco = %s,
                        contacto_emergencia_telefono = %s
                    WHERE numero_control = %s AND estado_alumno <> 'baja'
                    """,
                    (
                        datos["nombre"], datos["apellido_paterno"],
                        datos.get("apellido_materno") or None,
                        datos["curp"], datos["fecha_nacimiento_iso"], datos["sexo"],
                        datos.get("tipo_sangre") or None,
                        datos["calle"], datos.get("manzana") or None,
                        datos.get("lote") or None, datos["colonia"],
                        datos["cp"], datos["municipio"], datos["estado"],
                        datos.get("pais") or "México",
                        datos["telefono"], datos.get("correo") or None,
                        carrera[0], datos.get("escuela_procedencia") or None,
                        datos.get("promedio"),
                        datos["contacto_emergencia_nombre"],
                        datos["contacto_emergencia_parentesco"],
                        datos["contacto_emergencia_telefono"],
                        datos["numero_control"],
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError("No se encontró al alumno (o ya está dado de baja).")

        return True, (
            "Datos actualizados correctamente.\n\n"
            f"Número de control: {datos['numero_control']}"
        )

    except errors.UniqueViolation as error:
        restriccion = getattr(error.diag, "constraint_name", "") or ""
        return False, MENSAJES_UNICOS.get(restriccion, "Ya existe un dato que debe ser único.")
    except ValueError as error:
        return False, str(error)
    except psycopg.Error as error:
        print(f"Error al actualizar alumno: {error}")
        return False, "No se pudieron guardar los cambios en la base de datos."
    finally:
        conexion.close()


def dar_de_baja(numero_control):
    """Baja lógica: el alumno y su historial se conservan; cambia su estatus y se
    cancelan sus materias en curso (alumno_grupo.estado = 'baja')."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT estado_alumno FROM public.alumnos
                    WHERE numero_control = %s FOR UPDATE
                    """,
                    (numero_control,),
                )
                fila = cursor.fetchone()
                if fila is None:
                    raise ValueError("No existe un alumno con ese número de control.")
                if fila[0] == "baja":
                    raise ValueError("Ese alumno ya estaba dado de baja.")
                if fila[0] == "egresado":
                    raise ValueError("Ese alumno ya egresó; no se puede dar de baja.")

                cursor.execute(
                    "UPDATE public.alumnos SET estado_alumno = 'baja' "
                    "WHERE numero_control = %s",
                    (numero_control,),
                )
                cursor.execute(
                    "UPDATE public.alumno_grupo SET estado = 'baja' "
                    "WHERE numero_control = %s AND estado = 'inscrito'",
                    (numero_control,),
                )
                materias = cursor.rowcount
        return True, (
            "La baja se registró correctamente.\n\n"
            f"Número de control: {numero_control}\n"
            f"Materias canceladas: {materias}"
        )
    except ValueError as error:
        return False, str(error)
    except psycopg.Error as error:
        print(f"Error en baja de alumno: {error}")
        return False, "No se pudo procesar la baja en el sistema. Intenta más tarde."
    finally:
        conexion.close()
