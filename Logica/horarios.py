import re
import shutil
from pathlib import Path
import psycopg
from psycopg import errors
from conexiondb.db import obtener_conexion

CARPETA_HORARIOS = Path(__file__).resolve().parent.parent / "documentos" / "horarios"
TURNOS = ("matutino", "vespertino")

def listar_horarios(semestre=None):
    conexion = obtener_conexion()
    if conexion is None:
        return []
    try:
        with conexion.cursor() as cursor:
            if semestre is None:
                cursor.execute(
                    "SELECT horario_semestre_id, semestre, turno, descripcion "
                    "FROM public.horarios_semestre ORDER BY semestre, turno"
                )
            else:
                cursor.execute(
                    "SELECT horario_semestre_id, semestre, turno, descripcion "
                    "FROM public.horarios_semestre WHERE semestre = %s "
                    "ORDER BY turno",
                    (int(semestre),),
                )
            return [
                {"id": f[0], "semestre": f[1], "turno": f[2], "descripcion": f[3]}
                for f in cursor.fetchall()
            ]
    except psycopg.Error as error:
        print(f"Error al listar horarios: {error}")
        return []
    finally:
        conexion.close()


def crear_horario(semestre, turno, descripcion, ruta_pdf=None):
    """Devuelve (ok, mensaje, horario_id | None)."""
    turno = (turno or "").lower()
    descripcion = (descripcion or "").strip()
    if turno not in TURNOS:
        return False, "Turno no válido.", None
    if not descripcion:
        return False, "Escribe el nombre o descripción del horario.", None
    if len(descripcion) > 120:
        return False, "La descripción no puede pasar de 120 caracteres.", None

    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos.", None

    destino = None
    try:
        ruta_guardada = None
        if ruta_pdf:
            origen = Path(ruta_pdf)
            seguro = re.sub(r"[^\w.\-]+", "_", origen.name)
            nombre = f"sem{int(semestre)}_{turno}_{seguro}"
            destino = CARPETA_HORARIOS / nombre
            ruta_guardada = f"documentos/horarios/{nombre}"

        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.horarios_semestre
                        (semestre, turno, descripcion, ruta_archivo)
                    VALUES (%s, %s, %s, %s)
                    RETURNING horario_semestre_id
                    """,
                    (int(semestre), turno, descripcion, ruta_guardada),
                )
                horario_id = cursor.fetchone()[0]

        if destino is not None:
            try:
                CARPETA_HORARIOS.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origen, destino)
            except OSError as error:
                print(f"No se pudo copiar el PDF del horario: {error}")
                return True, "Horario guardado, pero no se pudo copiar el PDF.", horario_id
        return True, "Horario guardado.", horario_id

    except errors.UniqueViolation:
        return False, (
            f"Ya existe un horario {turno} para el semestre {int(semestre)}."
        ), None
    except psycopg.Error as error:
        print(f"Error al crear horario: {error}")
        return False, "No se pudo guardar el horario en la base de datos.", None
    finally:
        conexion.close()