
import re
import shutil
from pathlib import Path

import psycopg
from psycopg import errors

from conexiondb.db import obtener_conexion
from Logica.validaciones import turno_por_puntaje

CARPETA_DOCUMENTOS = Path(__file__).resolve().parent.parent / "documentos"


def _nombre_seguro(nombre):
    return re.sub(r"[^\w.\-]+", "_", nombre)


# ----------------------------------------------------------------------
#  Búsqueda del alumno (por número de control o por número de ficha)
# ----------------------------------------------------------------------
def buscar_alumno(clave):
    """Devuelve (alumno | None, mensaje_de_error | None)."""
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT numero_control, nombres, apellido_paterno,
                       apellido_materno, estado_alumno
                FROM public.alumnos
                WHERE numero_control = %s OR numero_ficha = %s
                ORDER BY (numero_control = %s) DESC
                LIMIT 1
                """,
                (clave, clave, clave),
            )
            fila = cursor.fetchone()

        if fila is None:
            return None, None

        nombre = " ".join(p for p in (fila[1], fila[2], fila[3]) if p)
        if (fila[4] or "").lower() == "baja":
            return None, "Ese alumno está dado de baja."
        return {"numero_control": fila[0], "nombre": nombre, "estado": fila[4]}, None

    except psycopg.Error as error:
        print(f"Error al buscar alumno: {error}")
        return None, "No se pudo consultar la base de datos."
    finally:
        conexion.close()


# ----------------------------------------------------------------------
#  Documentos PDF
# ----------------------------------------------------------------------
def _registrar_documentos(cursor, numero_control, documentos):
    """Guarda los metadatos en documentos_pdf (dentro de la transacción).
    Devuelve [(origen, destino)] para copiar los archivos después del commit."""
    pendientes = []
    for doc in documentos or []:
        origen = Path(doc["ruta"])
        nombre = f"{numero_control}_{doc['tipo']}_{_nombre_seguro(origen.name)}"
        cursor.execute(
            """
            INSERT INTO public.documentos_pdf
                (numero_control, tipo_documento, nombre_archivo, ruta_archivo)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (numero_control, tipo_documento)
            DO UPDATE SET nombre_archivo = EXCLUDED.nombre_archivo,
                          ruta_archivo   = EXCLUDED.ruta_archivo,
                          fecha_carga    = CURRENT_TIMESTAMP
            """,
            (numero_control, doc["tipo"], nombre, f"documentos/{nombre}"),
        )
        pendientes.append((origen, CARPETA_DOCUMENTOS / nombre))
    return pendientes


def _copiar_archivos(pendientes):
    guardados, fallidos = [], []
    if pendientes:
        CARPETA_DOCUMENTOS.mkdir(parents=True, exist_ok=True)
    for origen, destino in pendientes:
        try:
            shutil.copy2(origen, destino)
            guardados.append(destino.name)
        except OSError as error:
            print(f"No se pudo copiar {origen}: {error}")
            fallidos.append(origen.name)
    return guardados, fallidos


# ----------------------------------------------------------------------
#  Registro del trámite
# ----------------------------------------------------------------------
def registrar_tramite(datos):
    """Inscripción (nuevo ingreso) o reinscripción, según datos['tipo_inscripcion']."""
    tipo = datos["tipo_inscripcion"]
    numero_control = datos["numero_control"]
    semestre = int(datos["semestre"])

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT estado_alumno, semestre_actual, turno,
                           puntaje_examen_admision
                    FROM public.alumnos
                    WHERE numero_control = %s
                    FOR UPDATE
                    """,
                    (numero_control,),
                )
                alumno = cursor.fetchone()
                if alumno is None:
                    raise ValueError("El alumno ya no existe en la base de datos.")
                estado, semestre_actual, turno, puntaje = alumno

                if estado == "baja":
                    raise ValueError("El alumno está dado de baja.")
                if estado == "egresado":
                    raise ValueError("El alumno ya está egresado.")

                cursor.execute(
                    "SELECT periodo_id FROM public.periodos_escolares WHERE nombre = %s",
                    (datos["periodo"],),
                )
                fila_periodo = cursor.fetchone()
                if fila_periodo is None:
                    raise ValueError(
                        f"El periodo {datos['periodo']} no está dado de alta "
                        "en periodos_escolares."
                    )
                periodo_id = fila_periodo[0]

                if tipo == "Inscripción":
                    if estado != "aspirante":
                        raise ValueError(
                            "Ese alumno ya fue inscrito. Para continuar usa el "
                            "trámite de Reinscripción."
                        )
                    turno_asignado = turno
                    if not turno_asignado and puntaje is not None:
                        turno_asignado = turno_por_puntaje(puntaje).lower()
                    if not turno_asignado:
                        raise ValueError("El alumno no tiene turno asignado.")

                    cursor.execute(
                        """
                        INSERT INTO public.inscripciones
                            (numero_control, periodo_ingreso_id,
                             semestre_asignado, turno_asignado)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (numero_control, periodo_id, semestre, turno_asignado),
                    )
                    cursor.execute(
                        """
                        UPDATE public.alumnos
                        SET estado_alumno = 'activo',
                            semestre_actual = %s,
                            turno = %s
                        WHERE numero_control = %s
                        """,
                        (semestre, turno_asignado, numero_control),
                    )
                    detalle = f"Turno: {turno_asignado.capitalize()}\n"
                else:
                    if estado == "aspirante":
                        raise ValueError(
                            "Ese alumno aún no está inscrito. Primero realiza "
                            "su Inscripción."
                        )
                    if semestre_actual and semestre < semestre_actual:
                        raise ValueError(
                            f"El alumno cursa el semestre {semestre_actual}; "
                            "no puede reinscribirse a uno menor."
                        )
                    cursor.execute(
                        """
                        INSERT INTO public.reinscripciones
                            (numero_control, periodo_id, semestre)
                        VALUES (%s, %s, %s)
                        """,
                        (numero_control, periodo_id, semestre),
                    )
                    cursor.execute(
                        """
                        UPDATE public.alumnos
                        SET semestre_actual = %s
                        WHERE numero_control = %s
                        """,
                        (semestre, numero_control),
                    )
                    detalle = ""

                pendientes = _registrar_documentos(
                    cursor, numero_control, datos.get("documentos")
                )

        # La transacción ya se confirmó: ahora se copian los PDF.
        guardados, fallidos = _copiar_archivos(pendientes)

        mensaje = (
            f"{tipo} registrada correctamente.\n\n"
            f"Número de control: {numero_control}\n"
            f"Periodo: {datos['periodo']}\n"
            f"Semestre: {semestre}\n"
            f"{detalle}"
            f"Documentos guardados: {len(guardados)}"
        )
        if fallidos:
            mensaje += (
                "\n\nNo se pudieron copiar estos archivos, súbelos de nuevo:\n"
                + "\n".join(f"• {n}" for n in fallidos)
            )
        return True, mensaje

    except errors.UniqueViolation:
        if tipo == "Inscripción":
            return False, "Ese alumno ya tiene una inscripción registrada."
        return False, "Ese alumno ya está reinscrito en ese periodo."

    except ValueError as error:
        return False, str(error)

    except psycopg.Error as error:
        print(f"Error al registrar {tipo}: {error}")
        return False, "No se pudo guardar el trámite en la base de datos."

    finally:
        conexion.close()