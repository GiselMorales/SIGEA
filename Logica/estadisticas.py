import json

import psycopg

from conexiondb.db import obtener_conexion


def listar_periodos():
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT periodo_id, nombre
                FROM public.periodos_escolares
                ORDER BY fecha_inicio DESC, nombre DESC
                """
            )
            periodos = [
                {"periodo_id": fila[0], "nombre": fila[1]}
                for fila in cursor.fetchall()
            ]
        return periodos, None
    except psycopg.Error as error:
        print(f"Error al consultar periodos escolares: {error}")
        return None, "No se pudieron consultar los periodos escolares."
    finally:
        conexion.close()


def listar_grupos(periodo_id):
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT clave_grupo
                FROM public.grupos
                WHERE periodo_id = %s
                ORDER BY clave_grupo
                """,
                (periodo_id,),
            )
            grupos = [fila[0] for fila in cursor.fetchall()]
        return grupos, None
    except psycopg.Error as error:
        print(f"Error al consultar grupos escolares: {error}")
        return None, "No se pudieron consultar los grupos del periodo."
    finally:
        conexion.close()


def consultar_estadisticas(periodo_id, grupo=None):
    """Devuelve grupos, totales y distribuciones únicas del filtro."""
    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                WITH grupos_filtrados AS (
                    SELECT g.grupo_id, g.clave_grupo, m.clave AS clave_materia,
                           m.nombre AS nombre_materia, m.semestre,
                           LOWER(g.turno) AS turno
                    FROM public.grupos AS g
                    JOIN public.periodos_escolares AS p
                      ON p.periodo_id = g.periodo_id
                    JOIN public.materias AS m ON m.materia_id = g.materia_id
                    WHERE p.periodo_id = %s
                      AND (%s::text IS NULL OR g.clave_grupo = %s)
                ),
                miembros AS (
                    SELECT gf.*, ag.numero_control, a.sexo
                    FROM grupos_filtrados AS gf
                    LEFT JOIN public.alumno_grupo AS ag
                      ON ag.grupo_id = gf.grupo_id
                     AND ag.estado = 'inscrito'
                    LEFT JOIN public.alumnos AS a
                      ON a.numero_control = ag.numero_control
                     AND a.estado_alumno <> 'baja'
                ),
                por_grupo AS (
                    SELECT MIN(grupo_id) AS grupo_id, clave_grupo,
                           STRING_AGG(
                               DISTINCT clave_materia || ' · ' || nombre_materia,
                               '; ' ORDER BY clave_materia || ' · ' || nombre_materia
                           ) AS materias,
                           semestre, turno,
                           COUNT(DISTINCT numero_control) AS alumnos,
                           COUNT(DISTINCT numero_control)
                               FILTER (WHERE sexo = 'Hombre') AS hombres,
                           COUNT(DISTINCT numero_control)
                               FILTER (WHERE sexo = 'Mujer') AS mujeres
                    FROM miembros
                    GROUP BY clave_grupo, semestre, turno
                ),
                por_semestre AS (
                    SELECT semestre, COUNT(DISTINCT numero_control) AS alumnos
                    FROM miembros
                    WHERE numero_control IS NOT NULL
                    GROUP BY semestre
                ),
                por_turno AS (
                    SELECT turno, COUNT(DISTINCT numero_control) AS alumnos
                    FROM miembros
                    WHERE numero_control IS NOT NULL
                    GROUP BY turno
                ),
                distribucion_semestre AS (
                    SELECT COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'semestre', semestre,
                                'alumnos', alumnos
                            )
                            ORDER BY semestre
                        ),
                        '[]'::jsonb
                    )::text AS datos
                    FROM por_semestre
                ),
                distribucion_turno AS (
                    SELECT COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'turno', turno,
                                'alumnos', alumnos
                            )
                            ORDER BY turno
                        ),
                        '[]'::jsonb
                    )::text AS datos
                    FROM por_turno
                ),
                totales AS (
                    SELECT COUNT(DISTINCT numero_control) AS total_alumnos,
                           COUNT(DISTINCT numero_control)
                               FILTER (WHERE sexo = 'Hombre') AS hombres,
                           COUNT(DISTINCT numero_control)
                               FILTER (WHERE sexo = 'Mujer') AS mujeres
                    FROM miembros
                )
                SELECT pg.grupo_id, pg.clave_grupo, pg.materias,
                       pg.semestre, pg.turno,
                       pg.alumnos, pg.hombres, pg.mujeres,
                       t.total_alumnos, t.hombres, t.mujeres,
                       ds.datos, dt.datos
                FROM por_grupo AS pg
                CROSS JOIN totales AS t
                CROSS JOIN distribucion_semestre AS ds
                CROSS JOIN distribucion_turno AS dt
                ORDER BY pg.clave_grupo, pg.grupo_id
                """,
                (periodo_id, grupo, grupo),
            )
            filas = cursor.fetchall()

        grupos = [
            {
                "grupo_id": fila[0],
                "clave_grupo": fila[1],
                "materias": fila[2],
                "semestre": fila[3],
                "turno": fila[4],
                "alumnos": fila[5],
                "hombres": fila[6],
                "mujeres": fila[7],
            }
            for fila in filas
        ]
        por_semestre = json.loads(filas[0][11]) if filas else []
        por_turno = json.loads(filas[0][12]) if filas else []
        return {
            "grupos": grupos,
            "total_grupos": len(grupos),
            "total_alumnos": filas[0][8] if filas else 0,
            "hombres": filas[0][9] if filas else 0,
            "mujeres": filas[0][10] if filas else 0,
            "por_semestre": por_semestre,
            "por_turno": por_turno,
        }, None
    except psycopg.Error as error:
        print(f"Error al consultar estadísticas escolares: {error}")
        return None, "No fue posible consultar las estadísticas de la base de datos."
    finally:
        conexion.close()
