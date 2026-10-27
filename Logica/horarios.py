
from datetime import time

import psycopg
from psycopg import errors

from conexiondb.db import obtener_conexion

CARRERA_CLAVE = "ISC"
TURNOS = ("matutino", "vespertino")
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes")
HORA_MIN = time(7, 0)
HORA_MAX = time(20, 0)


def clave_grupo(semestre, turno):
    """1 + matutino -> '1M'; 1 + vespertino -> '1V'."""
    return f"{int(semestre)}{'M' if str(turno).lower() == 'matutino' else 'V'}"


def listar_grupos_horario(periodo, semestre, turno):
    """Grupos con horario para un periodo, semestre y turno."""
    filas = _consultar(
        """
        SELECT g.clave_grupo, COUNT(DISTINCT g.grupo_id)
        FROM public.grupos AS g
        JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
        JOIN public.materias AS m ON m.materia_id = g.materia_id
        WHERE p.nombre = %s AND m.semestre = %s
          AND LOWER(g.turno) = %s AND g.activo
          AND EXISTS (
              SELECT 1 FROM public.horarios AS h
              WHERE h.grupo_id = g.grupo_id
          )
        GROUP BY g.clave_grupo
        ORDER BY g.clave_grupo
        """,
        (periodo, int(semestre), str(turno).lower()), [],
    )
    return [{"clave": fila[0], "materias": fila[1]} for fila in filas]


def listar_claves_grupo(periodo, semestre, turno):
    """Claves usadas, incluso si el grupo está inactivo o aún no tiene horario."""
    filas = _consultar(
        """
        SELECT DISTINCT g.clave_grupo
        FROM public.grupos AS g
        JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
        JOIN public.materias AS m ON m.materia_id = g.materia_id
        WHERE p.nombre = %s AND m.semestre = %s
          AND LOWER(g.turno) = %s
        """,
        (periodo, int(semestre), str(turno).lower()), [],
    )
    return [fila[0] for fila in filas]


def siguiente_clave_grupo(semestre, turno, grupos):
    """Calcula la siguiente clave libre: 1M, 1M-2, 1M-3..."""
    base = clave_grupo(semestre, turno)
    numeros = []
    for grupo in grupos:
        clave = grupo["clave"] if isinstance(grupo, dict) else str(grupo)
        if clave == base:
            numeros.append(1)
        elif clave.startswith(base + "-"):
            sufijo = clave[len(base) + 1:]
            if sufijo.isdigit() and int(sufijo) > 1:
                numeros.append(int(sufijo))
    if not numeros:
        return base
    return f"{base}-{max(numeros) + 1}"


def formato_hora(valor):
    return valor.strftime("%H:%M") if valor is not None else ""


def _consultar(sql, parametros=(), por_defecto=None):
    """Ejecuta un SELECT y devuelve todas las filas (o `por_defecto` si algo falla)."""
    conexion = obtener_conexion()
    if conexion is None:
        return por_defecto
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()
    except psycopg.Error as error:
        print(f"Error de consulta: {error}")
        return por_defecto
    finally:
        conexion.close()


# ----------------------------------------------------------------------
#  Catálogos para la ventana
# ----------------------------------------------------------------------
def listar_periodos():
    filas = _consultar(
        "SELECT nombre FROM public.periodos_escolares ORDER BY fecha_inicio DESC", (), []
    )
    return [f[0] for f in filas]


def listar_materias(semestre):
    filas = _consultar(
        """
        SELECT m.materia_id, m.clave, m.nombre, m.creditos
        FROM public.materias AS m
        JOIN public.carreras AS c ON c.carrera_id = m.carrera_id
        WHERE c.clave = %s AND m.semestre = %s
        ORDER BY m.clave
        """,
        (CARRERA_CLAVE, int(semestre)), [],
    )
    return [{"id": f[0], "clave": f[1], "nombre": f[2], "creditos": f[3]} for f in filas]


def listar_docentes():
    filas = _consultar(
        """
        SELECT rfc, apellido_paterno, COALESCE(apellido_materno, ''), nombres
        FROM public.docentes
        WHERE activo
        ORDER BY apellido_paterno, apellido_materno, nombres
        """,
        (), [],
    )
    return [
        {"rfc": f[0], "nombre": " ".join(p for p in (f[1], f[2], f[3]) if p)}
        for f in filas
    ]


def materias_en_grupo(periodo, clave):
    """ids de las materias que ya tiene ese grupo en ese periodo."""
    filas = _consultar(
        """
        SELECT g.materia_id
        FROM public.grupos AS g
        JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
        WHERE p.nombre = %s AND g.clave_grupo = %s
        """,
        (periodo, clave), [],
    )
    return {f[0] for f in filas}


# ----------------------------------------------------------------------
#  Validación de bloques (día + hora de inicio + hora de fin)
# ----------------------------------------------------------------------
def validar_bloques(bloques):
    """bloques: [(dia, inicio:time, fin:time)]. Devuelve un mensaje de error o None."""
    if not bloques:
        return "Agrega al menos un día y hora para la materia."
    por_dia = {}
    for dia, inicio, fin in bloques:
        if dia not in DIAS:
            return f"Día no válido: {dia}."
        if fin <= inicio:
            return f"{dia.capitalize()}: la hora de fin debe ser mayor que la de inicio."
        if inicio < HORA_MIN or fin > HORA_MAX:
            return (
                f"{dia.capitalize()}: el horario debe estar entre "
                f"{formato_hora(HORA_MIN)} y {formato_hora(HORA_MAX)}."
            )
        for otro_inicio, otro_fin in por_dia.get(dia, []):
            if inicio < otro_fin and fin > otro_inicio:
                return f"{dia.capitalize()}: dos bloques de la misma materia se empalman."
        por_dia.setdefault(dia, []).append((inicio, fin))
    return None


# ----------------------------------------------------------------------
#  Alta de un horario (grupo con sus materias)
# ----------------------------------------------------------------------
def crear_horario_grupo(datos):
    """datos: periodo, semestre, turno y materias=[{materia_id, docente_rfc, aula,
    cupo, bloques:[(dia, inicio, fin)]}], clave_grupo opcional. Devuelve (ok, mensaje)."""
    periodo = datos["periodo"]
    semestre = int(datos["semestre"])
    turno = datos["turno"].lower()
    materias = datos.get("materias") or []
    clave_base = clave_grupo(semestre, turno)
    clave = str(datos.get("clave_grupo") or clave_base).strip().upper()

    if turno not in TURNOS:
        return False, "Turno no válido."
    if clave != clave_base and not (
        clave.startswith(clave_base + "-")
        and clave[len(clave_base) + 1:].isdigit()
        and int(clave[len(clave_base) + 1:]) > 1
    ):
        return False, "La clave del grupo no corresponde al semestre y turno."
    if not materias:
        return False, "Agrega al menos una materia al horario."

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT periodo_id FROM public.periodos_escolares WHERE nombre = %s",
                    (periodo,),
                )
                fila = cursor.fetchone()
                if fila is None:
                    raise ValueError(
                        f"El periodo {periodo} no está dado de alta en periodos_escolares."
                    )
                periodo_id = fila[0]

                if datos.get("crear_grupo_nuevo"):
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)",
                        (f"sigea-grupo:{periodo}:{clave}",),
                    )
                    cursor.execute(
                        """
                        SELECT 1 FROM public.grupos
                        WHERE periodo_id = %s AND clave_grupo = %s
                        LIMIT 1
                        """,
                        (periodo_id, clave),
                    )
                    if cursor.fetchone():
                        raise ValueError(
                            "Otro usuario creó ese grupo mientras capturabas. "
                            "Actualiza el alta y vuelve a intentarlo."
                        )

                for m in materias:
                    problema = validar_bloques(m["bloques"])
                    if problema:
                        raise ValueError(f"{m['nombre']}: {problema}")

                    cursor.execute(
                        "SELECT semestre, nombre FROM public.materias WHERE materia_id = %s",
                        (m["materia_id"],),
                    )
                    fila = cursor.fetchone()
                    if fila is None:
                        raise ValueError("Una de las materias ya no existe.")
                    if fila[0] != semestre:
                        raise ValueError(f"{fila[1]} no es del semestre {semestre}.")

                    cursor.execute(
                        """
                        SELECT 1 FROM public.grupos
                        WHERE clave_grupo = %s AND materia_id = %s AND periodo_id = %s
                        """,
                        (clave, m["materia_id"], periodo_id),
                    )
                    if cursor.fetchone():
                        raise ValueError(
                            f"{m['nombre']} ya está en el grupo {clave} de ese periodo."
                        )

                    # Empalmes con lo que ya existe (incluye las materias que se
                    # acaban de insertar en esta misma operación).
                    for dia, inicio, fin in m["bloques"]:
                        cursor.execute(
                            """
                            SELECT mt.nombre
                            FROM public.horarios AS h
                            JOIN public.grupos AS g ON g.grupo_id = h.grupo_id
                            JOIN public.materias AS mt ON mt.materia_id = g.materia_id
                            WHERE g.periodo_id = %s AND g.clave_grupo = %s
                              AND h.dia_semana = %s
                              AND h.hora_inicio < %s AND h.hora_fin > %s
                            LIMIT 1
                            """,
                            (periodo_id, clave, dia, fin, inicio),
                        )
                        choque = cursor.fetchone()
                        if choque:
                            raise ValueError(
                                f"{m['nombre']} se empalma con {choque[0]} el "
                                f"{dia} ({formato_hora(inicio)}-{formato_hora(fin)})."
                            )
                        cursor.execute(
                            """
                            SELECT g.clave_grupo, mt.nombre
                            FROM public.horarios AS h
                            JOIN public.grupos AS g ON g.grupo_id = h.grupo_id
                            JOIN public.materias AS mt ON mt.materia_id = g.materia_id
                            WHERE g.periodo_id = %s AND g.docente_rfc = %s
                              AND h.dia_semana = %s
                              AND h.hora_inicio < %s AND h.hora_fin > %s
                            LIMIT 1
                            """,
                            (periodo_id, m["docente_rfc"], dia, fin, inicio),
                        )
                        choque = cursor.fetchone()
                        if choque:
                            raise ValueError(
                                f"El docente de {m['nombre']} ya da {choque[1]} "
                                f"(grupo {choque[0]}) el {dia} en ese horario."
                            )

                    aula = (m.get("aula") or "").strip() or None
                    cursor.execute(
                        """
                        INSERT INTO public.grupos
                            (clave_grupo, materia_id, periodo_id, docente_rfc,
                             cupo, aula, turno)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING grupo_id
                        """,
                        (clave, m["materia_id"], periodo_id, m["docente_rfc"],
                         int(m.get("cupo") or 30), aula, turno),
                    )
                    grupo_id = cursor.fetchone()[0]
                    for dia, inicio, fin in m["bloques"]:
                        cursor.execute(
                            """
                            INSERT INTO public.horarios
                                (grupo_id, dia_semana, hora_inicio, hora_fin, aula)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (grupo_id, dia, inicio, fin, aula),
                        )

        return True, (
            f"Horario guardado.\n\n"
            f"Periodo: {periodo}\n"
            f"Grupo: {clave} ({turno.capitalize()}, semestre {semestre})\n"
            f"Materias agregadas: {len(materias)}"
        )

    except errors.UniqueViolation:
        return False, "Esa materia ya está registrada en ese grupo y periodo."
    except ValueError as error:
        return False, str(error)
    except psycopg.Error as error:
        print(f"Error al crear horario: {error}")
        return False, (
            "No se pudo guardar el horario. ¿Ya ejecutaste sql/horarios_grupos.sql "
            "en la base de datos?"
        )
    finally:
        conexion.close()


# ----------------------------------------------------------------------
#  Consultas para inscripción y reportes
# ----------------------------------------------------------------------
def grupos_disponibles(periodo, semestre):
    """Grupos que existen para ese periodo y semestre: [{clave, turno, materias}]."""
    filas = _consultar(
        """
        SELECT g.clave_grupo, g.turno, COUNT(*)
        FROM public.grupos AS g
        JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
        JOIN public.materias AS m ON m.materia_id = g.materia_id
        WHERE p.nombre = %s AND m.semestre = %s AND g.activo
        GROUP BY g.clave_grupo, g.turno
        ORDER BY g.clave_grupo
        """,
        (periodo, int(semestre)), [],
    )
    return [{"clave": f[0], "turno": f[1], "materias": f[2]} for f in filas]



def obtener_horario(periodo, semestre, turno, clave=None):
    """Devuelve el horario completo del grupo o None si no existe."""
    clave = clave or clave_grupo(semestre, turno)
    turno = turno.lower()

    if turno not in TURNOS:
        return None

    conexion = obtener_conexion()
    if conexion is None:
        return None

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    g.grupo_id,
                    m.clave,
                    m.nombre,
                    m.creditos,
                    d.apellido_paterno,
                    COALESCE(d.apellido_materno, ''),
                    d.nombres,
                    g.aula,
                    g.cupo
                FROM public.grupos AS g
                JOIN public.periodos_escolares AS p
                    ON p.periodo_id = g.periodo_id
                JOIN public.materias AS m
                    ON m.materia_id = g.materia_id
                JOIN public.docentes AS d
                    ON d.rfc = g.docente_rfc
                WHERE p.nombre = %s
                  AND g.clave_grupo = %s
                  AND g.turno = %s
                  AND g.activo = TRUE
                ORDER BY m.clave
                """,
                (periodo, clave, turno),
            )

            filas = cursor.fetchall()
            if not filas:
                return None

            orden_dias = {
                dia: posicion
                for posicion, dia in enumerate(DIAS)
            }

            materias = []

            for (
                grupo_id, cve, nombre, creditos,
                ap, am, nom, aula, cupo
            ) in filas:
                cursor.execute(
                    """
                    SELECT dia_semana, hora_inicio, hora_fin
                    FROM public.horarios
                    WHERE grupo_id = %s
                    ORDER BY
                        CASE dia_semana
                            WHEN 'lunes' THEN 1
                            WHEN 'martes' THEN 2
                            WHEN 'miércoles' THEN 3
                            WHEN 'jueves' THEN 4
                            WHEN 'viernes' THEN 5
                            WHEN 'sábado' THEN 6
                            ELSE 7
                        END,
                        hora_inicio
                    """,
                    (grupo_id,),
                )

                bloques = list(cursor.fetchall())

                materias.append({
                    "clave": cve,
                    "nombre": nombre,
                    "creditos": creditos,
                    "docente": " ".join(
                        parte for parte in (ap, am, nom) if parte
                    ),
                    "aula": aula or "",
                    "cupo": cupo,
                    "bloques": bloques,
                })

        return {
            "periodo": periodo,
            "semestre": int(semestre),
            "turno": turno,
            "clave": clave,
            "materias": materias,
        }

    except psycopg.Error as error:
        print(f"Error al obtener horario: {error}")
        return None

    finally:
        conexion.close()


def lista_grupo(periodo, semestre, turno, clave_materia=None, clave_grupo_seleccionada=None):
    """Alumnos inscritos en el grupo (o solo en una materia).
    Devuelve (datos | None, mensaje | None)."""
    clave = clave_grupo_seleccionada or clave_grupo(semestre, turno)
    parametros = [periodo, clave]
    filtro = ""
    if clave_materia:
        filtro = "AND m.clave = %s"
        parametros.append(clave_materia)

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT DISTINCT a.numero_control, a.apellido_paterno,
                       COALESCE(a.apellido_materno, ''), a.nombres,
                       a.sexo, a.estado_alumno
                FROM public.alumno_grupo AS ag
                JOIN public.grupos AS g ON g.grupo_id = ag.grupo_id
                JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
                JOIN public.materias AS m ON m.materia_id = g.materia_id
                JOIN public.alumnos AS a ON a.numero_control = ag.numero_control
                WHERE p.nombre = %s AND g.clave_grupo = %s
                  AND ag.estado = 'inscrito' {filtro}
                ORDER BY a.apellido_paterno, 3, a.nombres
                """,
                parametros,
            )
            filas = cursor.fetchall()

            materia = None
            if clave_materia:
                cursor.execute(
                    """
                    SELECT m.clave, m.nombre,
                           d.apellido_paterno, COALESCE(d.apellido_materno, ''), d.nombres
                    FROM public.grupos AS g
                    JOIN public.periodos_escolares AS p ON p.periodo_id = g.periodo_id
                    JOIN public.materias AS m ON m.materia_id = g.materia_id
                    JOIN public.docentes AS d ON d.rfc = g.docente_rfc
                    WHERE p.nombre = %s AND g.clave_grupo = %s AND m.clave = %s
                    """,
                    (periodo, clave, clave_materia),
                )
                fila = cursor.fetchone()
                if fila is None:
                    return None, f"La materia {clave_materia} no está en el grupo {clave}."
                materia = {
                    "clave": fila[0], "nombre": fila[1],
                    "docente": " ".join(p for p in fila[2:] if p),
                }
        alumnos = [
            {
                "control": f[0],
                "nombre": " ".join(p for p in (f[1], f[2], f[3]) if p),
                "sexo": f[4], "estatus": (f[5] or "").capitalize(),
            }
            for f in filas
        ]
        return {
            "periodo": periodo, "semestre": int(semestre), "turno": turno.lower(),
            "clave": clave, "materia": materia, "alumnos": alumnos,
        }, None
    except psycopg.Error as error:
        print(f"Error al obtener la lista del grupo: {error}")
        return None, "No se pudo consultar la base de datos."
    finally:
        conexion.close()
