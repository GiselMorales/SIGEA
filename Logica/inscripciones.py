
"""Registro de inscripciones, reinscripciones y documentos de alumnos."""

import re
import shutil
from pathlib import Path

import psycopg
from psycopg import errors

from conexiondb.db import obtener_conexion


RAIZ = Path(__file__).resolve().parent.parent
CARPETA_DOCUMENTOS = RAIZ / "documentos"
CARPETA_REPORTES = RAIZ / "reportes_generados" / "horarios_alumnos"


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------

def _nombre_seguro(nombre):
    return re.sub(r"[^\w.\-]+", "_", str(nombre))


def _normalizar(valor):
    return str(valor or "").strip().lower()


def _nombre_completo(nombres, paterno, materno):
    return " ".join(
        str(parte).strip()
        for parte in (nombres, paterno, materno)
        if parte and str(parte).strip()
    )


# ----------------------------------------------------------------------
# Búsqueda del alumno por número de control o número de ficha
# ----------------------------------------------------------------------

def buscar_alumno(clave):
    """
    Devuelve (alumno, None) si encuentra al alumno.
    Devuelve (None, mensaje) si existe un problema.
    Devuelve (None, None) si no encuentra coincidencias.
    """

    clave = str(clave or "").strip()

    if not clave:
        return None, "Escribe el número de control o número de ficha."

    conexion = obtener_conexion()

    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    numero_control,
                    numero_ficha,
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    estado_alumno,
                    turno,
                    semestre_actual
                FROM public.alumnos
                WHERE numero_control::text = %s
                   OR numero_ficha::text = %s
                ORDER BY
                    CASE WHEN numero_control::text = %s
                         THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (clave, clave, clave),
            )

            fila = cursor.fetchone()

        if fila is None:
            return None, None

        alumno = {
            "numero_control": fila[0],
            "ficha": fila[1],
            "nombre": _nombre_completo(fila[2], fila[3], fila[4]),
            "estado": fila[5],
            "turno": fila[6],
            "semestre_actual": fila[7],
        }

        if _normalizar(alumno["estado"]) == "baja":
            return None, "Ese alumno está dado de baja."

        if _normalizar(alumno["estado"]) == "egresado":
            return None, "Ese alumno ya está egresado."

        return alumno, None

    except psycopg.Error as error:
        print(f"Error al buscar alumno: {error}")
        return None, "No se pudo consultar la base de datos."

    finally:
        conexion.close()


# ----------------------------------------------------------------------
# Registro de documentos PDF proporcionados por el usuario
# ----------------------------------------------------------------------

def _registrar_documentos(cursor, numero_control, documentos):
    """
    Guarda los metadatos en documentos_pdf y prepara las copias.
    Los documentos se guardan dentro de la transacción de inscripción.
    """

    pendientes = []

    for documento in documentos or []:
        origen = Path(documento["ruta"])
        tipo = str(documento["tipo"]).strip()

        if not origen.is_file():
            raise ValueError(
                f"No se encontró el archivo seleccionado: {origen.name}"
            )

        nombre = (
            f"{numero_control}_{_nombre_seguro(tipo)}_"
            f"{_nombre_seguro(origen.name)}"
        )

        ruta_relativa = (Path("documentos") / nombre).as_posix()

        cursor.execute(
            """
            INSERT INTO public.documentos_pdf
                (numero_control, tipo_documento, nombre_archivo, ruta_archivo)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (numero_control, tipo_documento)
            DO UPDATE SET
                nombre_archivo = EXCLUDED.nombre_archivo,
                ruta_archivo = EXCLUDED.ruta_archivo,
                fecha_carga = CURRENT_TIMESTAMP
            """,
            (numero_control, tipo, nombre, ruta_relativa),
        )

        pendientes.append((origen, CARPETA_DOCUMENTOS / nombre))

    return pendientes


def _copiar_archivos(pendientes):
    guardados = []
    fallidos = []

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
# Consultar grupos disponibles para el alumno
# ----------------------------------------------------------------------

def _consultar_grupos(cursor, periodo_id, clave, turno, semestre):
    """
    Obtiene los grupos activos del periodo, turno y semestre seleccionados.
    Cada grupo corresponde a una materia.
    """

    cursor.execute(
        """
        SELECT
            g.grupo_id,
            g.cupo,
            m.nombre
        FROM public.grupos AS g
        JOIN public.materias AS m
            ON m.materia_id = g.materia_id
        WHERE g.periodo_id = %s
          AND g.clave_grupo = %s
          AND LOWER(g.turno) = %s
          AND m.semestre = %s
          AND g.activo = TRUE
          AND EXISTS (
              SELECT 1
              FROM public.horarios AS h
              WHERE h.grupo_id = g.grupo_id
          )
        ORDER BY m.clave
        """,
        (periodo_id, clave, turno, semestre),
    )

    return cursor.fetchall()


# ----------------------------------------------------------------------
# Datos necesarios para generar el PDF del horario
# ----------------------------------------------------------------------

def _datos_pdf_horario(
    cursor, alumno, periodo, semestre, turno, clave, grupo_ids
):
    cursor.execute(
        """
        SELECT
            m.clave,
            m.nombre,
            m.creditos,
            d.apellido_paterno,
            COALESCE(d.apellido_materno, ''),
            d.nombres,
            g.aula,
            g.cupo,
            h.dia_semana,
            h.hora_inicio,
            h.hora_fin
        FROM public.grupos AS g
        JOIN public.materias AS m
            ON m.materia_id = g.materia_id
        JOIN public.docentes AS d
            ON d.rfc = g.docente_rfc
        JOIN public.horarios AS h
            ON h.grupo_id = g.grupo_id
        WHERE g.grupo_id = ANY(%s)
        ORDER BY
            m.clave,
            CASE LOWER(h.dia_semana)
                WHEN 'lunes' THEN 1
                WHEN 'martes' THEN 2
                WHEN 'miércoles' THEN 3
                WHEN 'miercoles' THEN 3
                WHEN 'jueves' THEN 4
                WHEN 'viernes' THEN 5
                WHEN 'sábado' THEN 6
                WHEN 'sabado' THEN 6
                ELSE 7
            END,
            h.hora_inicio
        """,
        (grupo_ids,),
    )

    materias = {}

    for fila in cursor.fetchall():
        clave_materia = fila[0]

        materia = materias.setdefault(
            clave_materia,
            {
                "clave": fila[0],
                "nombre": fila[1],
                "creditos": fila[2],
                "docente": _nombre_completo(fila[5], fila[3], fila[4]),
                "aula": fila[6] or "",
                "cupo": fila[7],
                "bloques": [],
            },
        )

        materia["bloques"].append((fila[8], fila[9], fila[10]))

    return {
        "periodo": periodo,
        "semestre": semestre,
        "turno": turno,
        "clave": clave,
        "numero_control": alumno["numero_control"],
        "alumno_nombre": alumno["nombre"],
        "materias": list(materias.values()),
    }


# ----------------------------------------------------------------------
# Registro de inscripción o reinscripción
# ----------------------------------------------------------------------

def registrar_tramite(datos):
    """
    Registra una inscripción o reinscripción, asigna las materias del grupo,
    guarda documentos y genera el PDF del horario.
    """

    tipo = str(datos.get("tipo_inscripcion") or "").strip()

    if tipo not in ("Inscripción", "Reinscripción"):
        return False, "Selecciona Inscripción o Reinscripción."

    numero_control = str(datos.get("numero_control") or "").strip()
    periodo = str(datos.get("periodo") or "").strip()
    clave = str(datos.get("horario_clave") or "").strip().upper()
    turno = _normalizar(datos.get("horario_turno"))
    print("DEBUG datos recibidos:", datos)
    print("DEBUG horario_turno:", repr(datos.get("horario_turno")))

    if not numero_control:
        return False, "No se recibió el número de control del alumno."

    if not periodo:
        return False, "Selecciona el periodo escolar."

    if not clave:
        return False, "Selecciona el grupo del alumno."

    if turno not in ("matutino", "vespertino","Matutino", "Vespertino"):
        return False, "Selecciona un turno válido."

    try:
        semestre = int(datos["semestre"])
    except (KeyError, TypeError, ValueError):
        return False, "Selecciona un semestre válido."

    if not 1 <= semestre <= 12:
        return False, "El semestre debe estar entre 1 y 12."

    conexion = obtener_conexion()

    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    pendientes = []
    grupo_ids = []
    info_pdf = None
    alumno_pdf = None
    detalle_turno = turno.capitalize()

    try:
        with conexion:
            with conexion.cursor() as cursor:

                # Bloquear el registro durante el trámite.
                cursor.execute(
                    """
                    SELECT
                        numero_control,
                        estado_alumno,
                        semestre_actual,
                        turno,
                        nombres,
                        apellido_paterno,
                        apellido_materno,
                        puntaje_examen_admision
                    FROM public.alumnos
                    WHERE numero_control = %s
                    FOR UPDATE
                    """,
                    (numero_control,),
                )

                fila = cursor.fetchone()

                if fila is None:
                    raise ValueError(
                        "El alumno ya no existe en la base de datos."
                    )

                (
                    control_db,
                    estado,
                    semestre_actual,
                    turno_alumno,
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    puntaje,
                ) = fila

                alumno_pdf = {
                    "numero_control": control_db,
                    "nombre": _nombre_completo(
                        nombres, apellido_paterno, apellido_materno
                    ),
                }

                estado = _normalizar(estado)
                turno_alumno = _normalizar(turno_alumno)

                if estado == "baja":
                    raise ValueError("El alumno está dado de baja.")

                if estado == "egresado":
                    raise ValueError("El alumno ya está egresado.")

                if turno_alumno and turno_alumno != turno:
                    raise ValueError(
                        f"El alumno tiene turno {turno_alumno.capitalize()}. "
                        "Selecciona un grupo de ese turno."
                    )

                # Determinar el periodo escolar.
                cursor.execute(
                    """
                    SELECT periodo_id
                    FROM public.periodos_escolares
                    WHERE UPPER(nombre) = UPPER(%s)
                    LIMIT 1
                    """,
                    (periodo,),
                )

                fila_periodo = cursor.fetchone()

                if fila_periodo is None:
                    raise ValueError(
                        f"El periodo '{periodo}' no está dado de alta."
                    )

                periodo_id = fila_periodo[0]

                # Validaciones según el tipo de trámite.
                if tipo == "Inscripción":
                    if estado != "aspirante":
                        raise ValueError(
                            "Ese alumno ya fue inscrito. "
                            "Para continuar utiliza Reinscripción."
                        )

                    if semestre != 1:
                        raise ValueError(
                            "La inscripción de nuevo ingreso corresponde "
                            "al primer semestre."
                        )

                    cursor.execute(
                        """
                        INSERT INTO public.inscripciones
                            (
                                numero_control,
                                periodo_ingreso_id,
                                semestre_asignado,
                                turno_asignado
                            )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (numero_control, periodo_id, semestre, turno),
                    )

                else:
                    if estado == "aspirante":
                        raise ValueError(
                            "Primero realiza la inscripción del alumno."
                        )

                    if semestre <= 1:
                        raise ValueError(
                            "La reinscripción corresponde al segundo "
                            "semestre en adelante."
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

                    # Cerrar las materias inscritas en periodos anteriores.
                    cursor.execute(
                        """
                        UPDATE public.alumno_grupo AS ag
                        SET estado = 'finalizado'
                        FROM public.grupos AS g
                        WHERE ag.grupo_id = g.grupo_id
                          AND ag.numero_control = %s
                          AND ag.estado = 'inscrito'
                          AND g.periodo_id <> %s
                        """,
                        (numero_control, periodo_id),
                    )

                # Recuperar las materias del grupo elegido.
                grupos = _consultar_grupos(
                    cursor, periodo_id, clave, turno, semestre
                )

                if not grupos:
                    raise ValueError(
                        "No se encontraron materias activas con horario "
                        "para el grupo, periodo, semestre y turno elegidos."
                    )

                for grupo_id, cupo, nombre_materia in grupos:

                    # Comprobar si el alumno ya pertenece al grupo.
                    cursor.execute(
                        """
                        SELECT estado
                        FROM public.alumno_grupo
                        WHERE numero_control = %s
                          AND grupo_id = %s
                        LIMIT 1
                        """,
                        (numero_control, grupo_id),
                    )

                    existente = cursor.fetchone()

                    if existente:
                        if existente[0] != "inscrito":
                            cursor.execute(
                                """
                                UPDATE public.alumno_grupo
                                SET estado = 'inscrito'
                                WHERE numero_control = %s
                                  AND grupo_id = %s
                                """,
                                (numero_control, grupo_id),
                            )

                        grupo_ids.append(grupo_id)
                        continue

                    # Comprobar el cupo disponible.
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM public.alumno_grupo
                        WHERE grupo_id = %s
                          AND estado = 'inscrito'
                        """,
                        (grupo_id,),
                    )

                    inscritos = cursor.fetchone()[0]

                    if inscritos >= cupo:
                        raise ValueError(
                            f"No hay cupo disponible en {nombre_materia} "
                            f"del grupo {clave}."
                        )

                    cursor.execute(
                        """
                        INSERT INTO public.alumno_grupo
                            (numero_control, grupo_id, estado)
                        VALUES (%s, %s, 'inscrito')
                        """,
                        (numero_control, grupo_id),
                    )

                    grupo_ids.append(grupo_id)

                # Actualizar el estado académico del alumno.
                cursor.execute(
                    """
                    UPDATE public.alumnos
                    SET estado_alumno = 'activo',
                        semestre_actual = %s,
                        turno = %s
                    WHERE numero_control = %s
                    """,
                    (semestre, turno, numero_control),
                )

                # Guardar los metadatos de los documentos proporcionados.
                pendientes = _registrar_documentos(
                    cursor,
                    numero_control,
                    datos.get("documentos"),
                )

                # Preparar los datos para generar el horario.
                info_pdf = _datos_pdf_horario(
                    cursor,
                    alumno_pdf,
                    periodo,
                    semestre,
                    turno,
                    clave,
                    grupo_ids,
                )

        # La transacción terminó correctamente; copiar archivos.
        guardados, fallidos = _copiar_archivos(pendientes)

        ruta_pdf = None
        aviso_pdf = ""

        try:
            CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)

            periodo_archivo = _nombre_seguro(periodo)
            nombre_pdf = (
                f"{numero_control}_{periodo_archivo}_"
                f"{_nombre_seguro(clave)}_horario.pdf"
            )

            destino_pdf = CARPETA_REPORTES / nombre_pdf

            from reportes.generador_pdf import generar_pdf_horario

            generar_pdf_horario(info_pdf, destino_pdf)

            ruta_pdf = str(destino_pdf)

        except Exception as error:
            print(f"No se pudo generar el PDF del horario: {error}")
            aviso_pdf = (
                "\nLa operación se guardó, pero no se pudo generar "
                "el PDF del horario."
            )

        mensaje = (
            f"{tipo} registrada correctamente.\n\n"
            f"Número de control: {numero_control}\n"
            f"Periodo: {periodo}\n"
            f"Semestre: {semestre}\n"
            f"Turno: {detalle_turno}\n"
            f"Grupo: {clave}\n"
            f"Materias asignadas: {len(grupo_ids)}\n"
            f"Documentos guardados: {len(guardados)}"
        )

        if ruta_pdf:
            mensaje += f"\nPDF del horario: {ruta_pdf}"

        if fallidos:
            mensaje += (
                "\nNo se pudieron copiar estos documentos: "
                + ", ".join(fallidos)
            )

        mensaje += aviso_pdf

        return True, mensaje

    except errors.UniqueViolation:
        if tipo == "Inscripción":
            return False, (
                "El alumno ya tiene una inscripción registrada "
                "o existe un registro duplicado."
            )

        return False, (
            "El alumno ya tiene una reinscripción registrada "
            "para ese periodo."
        )

    except ValueError as error:
        return False, str(error)

    except psycopg.Error as error:
        print(f"Error al registrar {tipo}: {error}")
        return False, (
            "No se pudo guardar el trámite en la base de datos. "
            "Revisa la terminal para consultar el error SQL."
        )

    finally:
        conexion.close()
