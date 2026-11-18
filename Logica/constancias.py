import psycopg

from conexiondb.db import obtener_conexion


def obtener_datos_constancia(numero_control):
    """Obtiene el expediente y las materias con inscripción vigente del alumno."""
    numero_control = str(numero_control or "").strip()
    if not numero_control:
        return None, "Escribe el número de control del alumno."

    conexion = obtener_conexion()
    if conexion is None:
        return None, "No fue posible conectar con la base de datos."

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.numero_control, a.nombres, a.apellido_paterno,
                       a.apellido_materno, a.estado_alumno, a.semestre_actual,
                       a.turno, c.clave, c.nombre
                FROM public.alumnos AS a
                LEFT JOIN public.carreras AS c ON c.carrera_id = a.carrera_id
                WHERE a.numero_control = %s
                """,
                (numero_control,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None, "No existe un alumno con ese número de control."

            alumno = {
                "numero_control": fila[0],
                "nombre": " ".join(
                    parte for parte in (fila[1], fila[2], fila[3]) if parte
                ),
                "estado": fila[4] or "",
                "semestre_actual": fila[5],
                "turno": fila[6] or "",
                "clave_carrera": fila[7] or "",
                "carrera": fila[8] or "",
            }

            cursor.execute(
                """
                SELECT p.nombre, m.semestre, g.clave_grupo,
                       m.clave, m.nombre,
                       c.evaluacion1, c.evaluacion2, c.evaluacion3,
                       c.promediofinal
                FROM public.alumno_grupo AS ag
                JOIN public.grupos AS g ON g.grupo_id = ag.grupo_id
                JOIN public.materias AS m ON m.materia_id = g.materia_id
                JOIN public.periodos_escolares AS p
                  ON p.periodo_id = g.periodo_id
                LEFT JOIN public.calificaciones AS c
                  ON c.alumno_grupo_id = ag.alumno_grupo_id
                WHERE ag.numero_control = %s
                  AND ag.estado = 'inscrito'
                ORDER BY p.fecha_inicio DESC, m.semestre, m.clave, g.clave_grupo
                """,
                (numero_control,),
            )
            materias = [
                {
                    "periodo": registro[0],
                    "semestre": registro[1],
                    "grupo": registro[2],
                    "clave": registro[3],
                    "materia": registro[4],
                    "evaluacion1": registro[5],
                    "evaluacion2": registro[6],
                    "evaluacion3": registro[7],
                    "promediofinal": registro[8],
                }
                for registro in cursor.fetchall()
            ]
        alumno["materias"] = materias
        return alumno, None
    except psycopg.Error as error:
        print(f"Error al consultar datos para constancia: {error}")
        return None, "No se pudieron consultar los datos del alumno."
    finally:
        conexion.close()
