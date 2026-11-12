"""Consultas y operaciones académicas limitadas al docente autenticado."""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN

import psycopg

from conexiondb.db import obtener_conexion

SEMANA_UNIDAD = {1: 5, 2: 9, 3: 13}
SEMANA_CIERRE = 17


def _nombre_completo(nombres, paterno, materno):
    return " ".join(
        str(parte).strip()
        for parte in (nombres, paterno, materno)
        if parte and str(parte).strip()
    )


def _semana_periodo(fecha_inicio, hoy=None):
    hoy = hoy or date.today()
    if hoy < fecha_inicio:
        return 0
    return (hoy - fecha_inicio).days // 7 + 1


def _perfil_autenticado(cursor, usuario_id):
    cursor.execute(
        """
        SELECT d.rfc, u.nombre_usuario, d.nombres,
               d.apellido_paterno, d.apellido_materno,
               d.sexo, d.grado_academico, d.curp, d.fecha_nacimiento
        FROM public.usuarios AS u
        JOIN public.docentes AS d ON d.usuario_id = u.usuario_id
        WHERE u.usuario_id = %s
          AND u.rol = 'docente'
          AND u.activo
          AND d.activo
        """,
        (usuario_id,),
    )
    fila = cursor.fetchone()
    if fila is None:
        return None
    return {
        "rfc": fila[0],
        "usuario": fila[1],
        "nombres": fila[2],
        "apellido_paterno": fila[3],
        "apellido_materno": fila[4],
        "nombre": _nombre_completo(fila[2], fila[3], fila[4]),
        "sexo": fila[5],
        "grado_academico": fila[6],
        "curp": fila[7],
        "fecha_nacimiento": fila[8],
    }


def obtener_perfil_docente(usuario_id):
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            perfil = _perfil_autenticado(cursor, usuario_id)
        if perfil is None:
            return None, "La cuenta no corresponde a un docente activo."
        return perfil, None
    except psycopg.Error as error:
        print(f"Error al consultar el perfil docente: {error}")
        return None, "No se pudo consultar la información del docente."
    finally:
        conexion.close()


def listar_grupos_docente(usuario_id):
    conexion = obtener_conexion()
    if conexion is None:
        return [], "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            if _perfil_autenticado(cursor, usuario_id) is None:
                return [], "La cuenta no corresponde a un docente activo."
            cursor.execute(
                """
                SELECT g.grupo_id, g.clave_grupo, m.materia_id,
                       m.clave, m.nombre, m.semestre, g.turno,
                       p.nombre, p.fecha_inicio, g.aula
                FROM public.grupos AS g
                JOIN public.docentes AS d ON d.rfc = g.docente_rfc
                JOIN public.usuarios AS u ON u.usuario_id = d.usuario_id
                JOIN public.materias AS m ON m.materia_id = g.materia_id
                JOIN public.periodos_escolares AS p
                    ON p.periodo_id = g.periodo_id
                WHERE d.usuario_id = %s
                  AND u.rol = 'docente'
                  AND u.activo
                  AND d.activo
                  AND g.activo
                ORDER BY p.fecha_inicio DESC, m.semestre, g.clave_grupo, m.clave
                """,
                (usuario_id,),
            )
            filas = cursor.fetchall()
        return [
            {
                "grupo_id": fila[0],
                "clave": fila[1],
                "materia_id": fila[2],
                "materia_clave": fila[3],
                "materia": fila[4],
                "semestre": fila[5],
                "turno": fila[6],
                "periodo": fila[7],
                "fecha_inicio": fila[8],
                "aula": fila[9] or "",
            }
            for fila in filas
        ], None
    except psycopg.Error as error:
        print(f"Error al listar grupos del docente: {error}")
        return [], "No se pudieron consultar los grupos asignados."
    finally:
        conexion.close()


def _contexto_grupo(cursor, usuario_id, grupo_id, bloquear=None):
    clausula_bloqueo = {
        "SHARE": " FOR SHARE OF g, d, u",
        "UPDATE": " FOR UPDATE OF g, d, u",
    }.get(bloquear, "")
    cursor.execute(
        """
        SELECT g.grupo_id, g.clave_grupo, g.materia_id,
               m.clave, m.nombre, m.semestre, g.turno, g.aula,
               p.nombre, p.fecha_inicio
        FROM public.grupos AS g
        JOIN public.docentes AS d ON d.rfc = g.docente_rfc
        JOIN public.usuarios AS u ON u.usuario_id = d.usuario_id
        JOIN public.materias AS m ON m.materia_id = g.materia_id
        JOIN public.periodos_escolares AS p
            ON p.periodo_id = g.periodo_id
        WHERE g.grupo_id = %s
          AND d.usuario_id = %s
          AND u.rol = 'docente'
          AND u.activo
          AND d.activo
          AND g.activo
        """ + clausula_bloqueo,
        (grupo_id, usuario_id),
    )
    fila = cursor.fetchone()
    if fila is None:
        return None
    return {
        "grupo_id": fila[0],
        "clave": fila[1],
        "materia_id": fila[2],
        "materia_clave": fila[3],
        "materia": fila[4],
        "semestre": fila[5],
        "turno": fila[6],
        "aula": fila[7] or "",
        "periodo": fila[8],
        "fecha_inicio": fila[9],
    }


def _filas_alumnos(cursor, grupo_id):
    cursor.execute(
        """
        SELECT ag.alumno_grupo_id, a.numero_control,
               a.nombres, a.apellido_paterno, a.apellido_materno,
               c.evaluacion1, c.evaluacion2, c.evaluacion3,
               c.promediofinal
        FROM public.alumno_grupo AS ag
        JOIN public.alumnos AS a
            ON a.numero_control = ag.numero_control
        LEFT JOIN public.calificaciones AS c
            ON c.alumno_grupo_id = ag.alumno_grupo_id
        WHERE ag.grupo_id = %s
          AND ag.estado = 'inscrito'
          AND a.estado_alumno <> 'baja'
        ORDER BY a.apellido_paterno, a.apellido_materno, a.nombres
        """,
        (grupo_id,),
    )
    alumnos = []
    for fila in cursor.fetchall():
        alumnos.append({
            "alumno_grupo_id": fila[0],
            "control": fila[1],
            "nombre": _nombre_completo(fila[2], fila[3], fila[4]),
            "evaluaciones": (fila[5], fila[6], fila[7]),
            "final_guardado": fila[8],
        })
    return alumnos


def _guardar_valor_calificacion(cursor, alumno_grupo_id, columna, valor):
    cursor.execute(
        f"""
        UPDATE public.calificaciones
        SET {columna} = %s
        WHERE alumno_grupo_id = %s
        """,
        (valor, alumno_grupo_id),
    )
    if cursor.rowcount == 0:
        cursor.execute(
            f"""
            INSERT INTO public.calificaciones (alumno_grupo_id, {columna})
            VALUES (%s, %s)
            """,
            (alumno_grupo_id, valor),
        )


def _promedio_final(evaluaciones):
    if any(valor is None for valor in evaluaciones):
        return None
    calificaciones = tuple(Decimal(valor) for valor in evaluaciones)
    if any(valor == 0 for valor in calificaciones):
        return Decimal("0.00")
    promedio = sum(calificaciones, Decimal(0)) / 3
    return promedio.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def _estado_evaluaciones(grupo, alumnos, hoy=None):
    semana = _semana_periodo(grupo["fecha_inicio"], hoy)
    completo = {
        unidad: bool(alumnos) and all(
            alumno["evaluaciones"][unidad - 1] is not None
            for alumno in alumnos
        )
        for unidad in (1, 2, 3)
    }
    disponibles = {}
    for unidad in SEMANA_UNIDAD:
        anteriores_completas = all(
            completo[previa] for previa in range(1, unidad)
        )
        disponibles[unidad] = (
            semana < SEMANA_CIERRE
            and anteriores_completas
        )
    promedio_guardado = bool(alumnos) and all(
        alumno["final_guardado"] is not None for alumno in alumnos
    )
    return {
        "semana": semana,
        "cerrado": semana >= SEMANA_CIERRE or promedio_guardado,
        "completas": completo,
        "disponibles": disponibles,
        "final_generado": semana >= SEMANA_CIERRE or promedio_guardado,
        "promedio_guardado": promedio_guardado,
    }


def obtener_lista_docente(usuario_id, grupo_id):
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."
    try:
        with conexion:
            with conexion.cursor() as cursor:
                grupo = _contexto_grupo(
                    cursor, usuario_id, grupo_id, bloquear="SHARE"
                )
                if grupo is None:
                    return None, "No tienes acceso a ese grupo."
                alumnos = _filas_alumnos(cursor, grupo_id)
                estado = _estado_evaluaciones(grupo, alumnos)
                for alumno in alumnos:
                    promedio = _promedio_final(alumno["evaluaciones"])
                    if (
                        estado["cerrado"]
                        and promedio is not None
                        and alumno["final_guardado"] is None
                    ):
                        _guardar_valor_calificacion(
                            cursor,
                            alumno["alumno_grupo_id"],
                            "promediofinal",
                            promedio,
                        )
                        alumno["final_guardado"] = promedio
                    alumno["final"] = (
                        alumno["final_guardado"]
                        if alumno["final_guardado"] is not None
                        else promedio
                    )
                estado["promedio_guardado"] = bool(alumnos) and all(
                    alumno["final_guardado"] is not None
                    for alumno in alumnos
                )
                estado["cerrado"] = (
                    estado["semana"] >= SEMANA_CIERRE
                    or estado["promedio_guardado"]
                )
                estado["final_generado"] = estado["cerrado"]
        return {"grupo": grupo, "alumnos": alumnos, "estado": estado}, None
    except psycopg.Error as error:
        print(f"Error al consultar alumnos del grupo docente: {error}")
        return None, "No se pudo consultar la lista del grupo."
    finally:
        conexion.close()


def obtener_horario_docente(usuario_id):
    conexion = obtener_conexion()
    if conexion is None:
        return [], "No fue posible conectar con la base de datos."
    try:
        with conexion.cursor() as cursor:
            if _perfil_autenticado(cursor, usuario_id) is None:
                return [], "La cuenta no corresponde a un docente activo."
            cursor.execute(
                """
                SELECT g.grupo_id, g.clave_grupo, m.clave, m.nombre,
                       m.semestre, g.turno, p.nombre, g.aula,
                       h.dia_semana, h.hora_inicio, h.hora_fin,
                       COALESCE(h.aula, g.aula, '')
                FROM public.grupos AS g
                LEFT JOIN public.horarios AS h ON h.grupo_id = g.grupo_id
                JOIN public.docentes AS d ON d.rfc = g.docente_rfc
                JOIN public.usuarios AS u ON u.usuario_id = d.usuario_id
                JOIN public.materias AS m ON m.materia_id = g.materia_id
                JOIN public.periodos_escolares AS p
                    ON p.periodo_id = g.periodo_id
                WHERE d.usuario_id = %s
                  AND u.rol = 'docente'
                  AND u.activo
                  AND d.activo
                  AND g.activo
                ORDER BY p.fecha_inicio DESC, m.semestre, g.clave_grupo,
                    m.clave,
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
                (usuario_id,),
            )
            filas = cursor.fetchall()

        grupos = {}
        for fila in filas:
            grupo_id = fila[0]
            grupo = grupos.setdefault(
                grupo_id,
                {
                    "grupo_id": grupo_id,
                    "clave": fila[1],
                    "materia_clave": fila[2],
                    "materia": fila[3],
                    "semestre": fila[4],
                    "turno": fila[5],
                    "periodo": fila[6],
                    "aula": fila[7] or "",
                    "bloques": [],
                },
            )
            if fila[8] is not None:
                grupo["bloques"].append(
                    (fila[8], fila[9], fila[10], fila[11] or "")
                )
        return list(grupos.values()), None
    except psycopg.Error as error:
        print(f"Error al consultar horario del docente: {error}")
        return [], "No se pudo consultar el horario."
    finally:
        conexion.close()


def obtener_estado_calificaciones(usuario_id, grupo_id):
    datos, problema = obtener_lista_docente(usuario_id, grupo_id)
    if problema:
        return None, problema
    return datos, None


def _normalizar_calificacion(valor):
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        return None, "Captura la calificación de cada alumno."
    try:
        calificacion = Decimal(texto)
    except InvalidOperation:
        return None, "La calificación debe ser numérica."
    if not calificacion.is_finite() or not Decimal(0) <= calificacion <= Decimal(100):
        return None, "La calificación debe estar entre 0 y 100."
    if calificacion.as_tuple().exponent < -2:
        return None, "La calificación admite hasta dos decimales."
    if calificacion < Decimal(70):
        return Decimal("0.00"), None
    return calificacion, None


def guardar_evaluacion(usuario_id, grupo_id, unidad, calificaciones):
    if unidad not in SEMANA_UNIDAD:
        return False, "La evaluación seleccionada no es válida."
    if not isinstance(calificaciones, dict) or not calificaciones:
        return False, "No hay calificaciones para guardar."

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."
    try:
        with conexion:
            with conexion.cursor() as cursor:
                grupo = _contexto_grupo(
                    cursor, usuario_id, grupo_id, bloquear="UPDATE"
                )
                if grupo is None:
                    return False, "No tienes acceso a ese grupo."

                semana = _semana_periodo(grupo["fecha_inicio"])
                if semana >= SEMANA_CIERRE:
                    return False, "El periodo de captura está cerrado."

                alumnos = _filas_alumnos(cursor, grupo_id)
                if not alumnos:
                    return False, "El grupo no tiene alumnos inscritos."
                if any(
                    alumno["final_guardado"] is not None for alumno in alumnos
                ):
                    return False, (
                        "El promedio final ya se guardó; las calificaciones "
                        "quedaron bloqueadas."
                    )
                for previa in range(1, unidad):
                    if any(
                        alumno["evaluaciones"][previa - 1] is None
                        for alumno in alumnos
                    ):
                        return False, (
                            f"Completa la evaluación {previa} de todo el grupo "
                            "antes de continuar."
                        )
                controles = {alumno["control"] for alumno in alumnos}
                if set(calificaciones) != controles:
                    return False, (
                        "La lista de alumnos cambió. Actualiza la pantalla "
                        "antes de guardar."
                    )

                normalizadas = []
                for alumno in alumnos:
                    valor, problema = _normalizar_calificacion(
                        calificaciones[alumno["control"]]
                    )
                    if problema:
                        return False, f"{alumno['nombre']}: {problema}"
                    normalizadas.append((alumno, valor))

                columna = f"evaluacion{unidad}"
                for alumno, valor in normalizadas:
                    cursor.execute(
                        f"""
                        UPDATE public.calificaciones
                        SET {columna} = %s, promediofinal = NULL
                        WHERE alumno_grupo_id = %s
                        """,
                        (valor, alumno["alumno_grupo_id"]),
                    )
                    if cursor.rowcount == 0:
                        cursor.execute(
                            f"""
                            INSERT INTO public.calificaciones
                                (alumno_grupo_id, {columna})
                            VALUES (%s, %s)
                            """,
                            (alumno["alumno_grupo_id"], valor),
                        )
        return True, f"Evaluación {unidad} guardada para todo el grupo."
    except psycopg.Error as error:
        print(f"Error al guardar calificaciones del docente: {error}")
        return False, "No se pudieron guardar las calificaciones."
    finally:
        conexion.close()


def guardar_promedio_final(usuario_id, grupo_id):
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."
    try:
        with conexion:
            with conexion.cursor() as cursor:
                grupo = _contexto_grupo(
                    cursor, usuario_id, grupo_id, bloquear="UPDATE"
                )
                if grupo is None:
                    return False, "No tienes acceso a ese grupo."

                alumnos = _filas_alumnos(cursor, grupo_id)
                if not alumnos:
                    return False, "El grupo no tiene alumnos inscritos."
                if any(alumno["final_guardado"] is not None for alumno in alumnos):
                    return False, (
                        "El promedio final ya fue guardado; las calificaciones "
                        "no se pueden modificar."
                    )
                if any(
                    valor is None
                    for alumno in alumnos
                    for valor in alumno["evaluaciones"]
                ):
                    return False, (
                        "Completa las tres evaluaciones de todo el grupo "
                        "antes de guardar el promedio final."
                    )

                for alumno in alumnos:
                    promedio = _promedio_final(alumno["evaluaciones"])
                    _guardar_valor_calificacion(
                        cursor,
                        alumno["alumno_grupo_id"],
                        "promediofinal",
                        promedio,
                    )
        return True, "Promedio final guardado. Las calificaciones quedaron bloqueadas."
    except psycopg.Error as error:
        print(f"Error al guardar el promedio final del docente: {error}")
        return False, "No se pudo guardar el promedio final."
    finally:
        conexion.close()
