import re

import psycopg

from conexiondb.db import obtener_conexion
from Logica import validaciones as v

PREFIJOS_SEMESTRE = {
    2: ("2632",),
    3: ("2532", "2632"),
}
CORREO_INSTITUCIONAL = "l{numero_control}@acapulco.tecnm.mx"


def validar_numero_control(numero_control, semestre):
    numero_control = (numero_control or "").strip()
    if not re.fullmatch(r"\d{9}", numero_control):
        return False, "El número de control debe contener 9 dígitos."
    if semestre not in PREFIJOS_SEMESTRE:
        return False, "Selecciona segundo o tercer semestre."
    if not numero_control.startswith(PREFIJOS_SEMESTRE[semestre]):
        if semestre == 2:
            return False, "Para segundo semestre el número debe comenzar con 2632."
        return False, (
            "Para tercer semestre el número debe comenzar con 2532 o 2632."
        )
    return True, None


def correo_institucional(numero_control):
    return CORREO_INSTITUCIONAL.format(numero_control=numero_control.strip())


def _validar_nombre(valor, etiqueta, obligatorio=True):
    nombre = v.espacios(valor)
    if not nombre:
        if obligatorio:
            return None, f"{etiqueta} es obligatorio."
        return "", None
    if len(nombre) < 3:
        return None, f"{etiqueta} debe contener al menos 3 caracteres."
    if len(nombre) > 80 or not v.RE_NOMBRE.fullmatch(nombre):
        return None, (
            f"{etiqueta} debe contener solo letras, espacios, apóstrofes "
            "o guiones y tener máximo 80 caracteres."
        )
    if re.search(r"(.)\1{2}", nombre, re.IGNORECASE):
        return None, f"{etiqueta} no puede repetir una letra 3 veces seguidas."
    return nombre, None


def _semestre_existente(cursor, numero_control):
    cursor.execute(
        """
        SELECT semestre_actual
        FROM public.reinscripcion_controles
        WHERE numero_control = %s
        UNION ALL
        SELECT 2
        FROM public.reinscripcion_segundo
        WHERE numero_control = %s
        UNION ALL
        SELECT 3
        FROM public.reinscripcion_tercero
        WHERE numero_control = %s
        LIMIT 1
        """,
        (numero_control, numero_control, numero_control),
    )
    fila = cursor.fetchone()
    return fila[0] if fila else None


def consultar_reinscripcion(numero_control):
    numero_control = (numero_control or "").strip()
    if not numero_control:
        return None, "Ingresa un número de control."

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            semestre = _semestre_existente(cursor, numero_control)
        return semestre, None
    except psycopg.Error as error:
        print(f"Error al consultar reinscripción existente: {error}")
        return None, "No se pudo validar el número de control."
    finally:
        conexion.close()


def consultar_reinscripciones(filtro=""):
    filtro = (filtro or "").strip()
    patron = f"%{filtro}%"
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                WITH reinscritos AS (
                    SELECT numero_control, apellido_paterno, apellido_materno,
                           nombres, semestre, turno, correo_institucional,
                           fecha_registro
                    FROM public.reinscripcion_segundo
                    UNION ALL
                    SELECT numero_control, apellido_paterno, apellido_materno,
                           nombres, semestre, turno, correo_institucional,
                           fecha_registro
                    FROM public.reinscripcion_tercero
                )
                SELECT numero_control,
                       CONCAT_WS(
                           ' ',
                           apellido_paterno,
                           NULLIF(apellido_materno, ''),
                           nombres
                       ) AS nombre_completo,
                       semestre, turno, correo_institucional, fecha_registro
                FROM reinscritos
                WHERE %s = ''
                   OR numero_control ILIKE %s
                   OR CONCAT_WS(
                       ' ',
                       apellido_paterno,
                       NULLIF(apellido_materno, ''),
                       nombres
                   ) ILIKE %s
                ORDER BY fecha_registro DESC, apellido_paterno, nombres
                """,
                (filtro, patron, patron),
            )
            filas = cursor.fetchall()
        return [
            {
                "numero_control": fila[0],
                "nombre": fila[1],
                "semestre": fila[2],
                "turno": fila[3],
                "correo": fila[4],
                "fecha_registro": fila[5],
            }
            for fila in filas
        ], None
    except psycopg.Error as error:
        print(f"Error al consultar reinscripciones: {error}")
        return None, "No se pudieron consultar los alumnos reinscritos."
    finally:
        conexion.close()


def listar_horarios_semestre():
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT horario_semestre_id, semestre, turno, descripcion
                FROM public.horarios_semestre
                WHERE semestre IN (2, 3)
                ORDER BY semestre, turno
                """
            )
            filas = cursor.fetchall()
        return [
            {
                "horario_semestre_id": fila[0],
                "semestre": fila[1],
                "turno": fila[2],
                "descripcion": fila[3],
            }
            for fila in filas
        ], None
    except psycopg.Error as error:
        print(f"Error al consultar horarios de reinscripción: {error}")
        return None, "No se pudieron consultar los horarios disponibles."
    finally:
        conexion.close()


def consultar_horario(semestre, turno):
    if semestre not in (2, 3) or turno not in ("matutino", "vespertino"):
        return None, "Selecciona un semestre y turno válidos."
    clave_grupo = {2: None, 3: "3M" if turno == "matutino" else "3V"}[semestre]
    filtro_clave_disponible = (
        "" if clave_grupo is None else "AND gx.clave_grupo = %s"
    )
    filtro_clave = (
        "" if clave_grupo is None else "AND g.clave_grupo = %s"
    )
    parametros_periodo = [semestre, turno]
    parametros_consulta = [semestre, turno]
    if clave_grupo is not None:
        parametros_periodo.append(clave_grupo)
        parametros_consulta.append(clave_grupo)

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT horario_semestre_id
                FROM public.horarios_semestre
                WHERE semestre = %s AND turno = %s
                """,
                (semestre, turno),
            )
            horario_semestre = cursor.fetchone()

            cursor.execute(
                f"""
                WITH periodo_disponible AS (
                    SELECT MAX(gx.periodo_id) AS periodo_id
                    FROM public.grupos AS gx
                    JOIN public.materias AS mx
                      ON mx.materia_id = gx.materia_id
                    WHERE gx.activo
                      AND mx.semestre = %s
                      AND gx.turno = %s
                      {filtro_clave_disponible}
                )
                SELECT g.grupo_id, g.clave_grupo, m.clave, m.nombre,
                       m.semestre, d.apellido_paterno,
                       COALESCE(d.apellido_materno, ''), d.nombres,
                       h.dia_semana,
                       h.hora_inicio, h.hora_fin,
                       COALESCE(h.aula, g.aula, '')
                FROM public.grupos AS g
                JOIN public.materias AS m ON m.materia_id = g.materia_id
                JOIN periodo_disponible AS p ON p.periodo_id = g.periodo_id
                LEFT JOIN public.docentes AS d ON d.rfc = g.docente_rfc
                LEFT JOIN public.horarios AS h ON h.grupo_id = g.grupo_id
                WHERE g.activo
                  AND m.semestre = %s
                  AND g.turno = %s
                  {filtro_clave}
                ORDER BY m.clave,
                    CASE h.dia_semana
                        WHEN 'lunes' THEN 1
                        WHEN 'martes' THEN 2
                        WHEN 'miércoles' THEN 3
                        WHEN 'jueves' THEN 4
                        WHEN 'viernes' THEN 5
                        WHEN 'sábado' THEN 6
                        ELSE 7
                    END,
                    h.hora_inicio
                """,
                tuple(parametros_periodo + parametros_consulta),
            )
            filas = cursor.fetchall()

        materias = {}
        for fila in filas:
            grupo_id = fila[0]
            materia = materias.setdefault(
                grupo_id,
                {
                    "grupo_id": grupo_id,
                    "grupo": fila[1],
                    "clave": fila[2],
                    "materia": fila[3],
                    "semestre": fila[4],
                    "docente": " ".join(
                        parte for parte in fila[5:8] if parte
                    ),
                    "bloques": [],
                },
            )
            if fila[8] is not None:
                materia["bloques"].append(
                    (fila[8], fila[9], fila[10], fila[11] or "")
                )

        return {
            "horario_semestre_id": (
                horario_semestre[0] if horario_semestre else None
            ),
            "materias": list(materias.values()),
        }, None
    except psycopg.Error as error:
        print(f"Error al consultar horario de reinscripción: {error}")
        return None, "No se pudo consultar el horario del semestre."
    finally:
        conexion.close()


def registrar_reinscripcion(
    numero_control,
    apellido_paterno,
    apellido_materno,
    nombres,
    semestre,
    turno,
):
    numero_control = (numero_control or "").strip()
    valido, problema = validar_numero_control(numero_control, semestre)
    if not valido:
        return False, problema
    if turno not in ("matutino", "vespertino"):
        return False, "Selecciona un turno válido."
    apellido_paterno, problema = _validar_nombre(
        apellido_paterno, "El apellido paterno"
    )
    if problema:
        return False, problema
    apellido_materno, problema = _validar_nombre(
        apellido_materno, "El apellido materno", obligatorio=False
    )
    if problema:
        return False, problema
    nombres, problema = _validar_nombre(nombres, "El nombre")
    if problema:
        return False, problema

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."
    try:
        with conexion:
            with conexion.cursor() as cursor:
                existente = _semestre_existente(cursor, numero_control)
                if existente:
                    return False, (
                        f"El número de control ya está registrado en "
                        f"{existente}° semestre."
                    )

                cursor.execute(
                    """
                    SELECT horario_semestre_id
                    FROM public.horarios_semestre
                    WHERE semestre = %s AND turno = %s
                    """,
                    (semestre, turno),
                )
                if cursor.fetchone() is None:
                    return False, (
                        "No existe un horario registrado para este semestre "
                        "y turno en horarios_semestre."
                    )

                cursor.execute(
                    """
                    SELECT public.registrar_reinscripcion(
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        numero_control,
                        apellido_paterno,
                        apellido_materno or None,
                        nombres,
                        semestre,
                        turno,
                    ),
                )
                mensaje = cursor.fetchone()[0]
        return True, mensaje
    except psycopg.Error as error:
        print(f"Error al registrar reinscripción: {error}")
        detalle = getattr(error.diag, "message_primary", None) or str(error)
        return False, detalle.splitlines()[0]
    finally:
        conexion.close()
