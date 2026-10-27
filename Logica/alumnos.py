import re
import secrets
import shutil
from pathlib import Path

import psycopg
from psycopg import errors

from conexiondb.db import obtener_conexion
from Logica.validaciones import turno_por_puntaje, SEMESTRE_INICIAL

CARRERA_CLAVE = "ISC"

# Carpeta "documentos" en la raíz del proyecto (junto a main.py)
CARPETA_DOCUMENTOS = Path(__file__).resolve().parent.parent / "documentos"

MENSAJES_UNICOS = {
    "alumnos_numero_ficha_key": "Ese número de ficha ya está registrado.",
    "alumnos_nss_key": "Ese NSS ya está registrado.",
    "alumnos_curp_key": "Esa CURP ya está registrada.",
    "alumnos_correo_personal_key": "Ese correo personal ya está registrado.",
    "alumnos_correo_institucional_key": "Ese correo institucional ya está registrado.",
}
LOCK_NSS = 728934620417


def _nombre_seguro(nombre):
    return re.sub(r"[^\w.\-]+", "_", nombre)


def _guardar_pdfs(numero_control, documentos):
    """Copia los PDF a documentos/<numero_control>_<tipo>_<archivo>.pdf.
    Devuelve (guardados, fallidos)."""
    guardados, fallidos = [], []
    if not documentos:
        return guardados, fallidos

    CARPETA_DOCUMENTOS.mkdir(parents=True, exist_ok=True)
    for doc in documentos:
        origen = Path(doc["ruta"])
        destino = CARPETA_DOCUMENTOS / (
            f"{numero_control}_{doc['tipo']}_{_nombre_seguro(origen.name)}"
        )
        try:
            shutil.copy2(origen, destino)
            guardados.append(destino.name)
        except OSError as error:
            print(f"No se pudo copiar {origen}: {error}")
            fallidos.append(origen.name)
    return guardados, fallidos


def _resolver_nss(cursor, nss):
    cursor.execute("SELECT pg_advisory_xact_lock(%s::bigint)", (LOCK_NSS,))

    nss = str(nss or "").strip()
    if nss:
        if not re.fullmatch(r"[0-9]{11}", nss):
            raise ValueError("El NSS debe contener exactamente 11 dígitos.")
        cursor.execute(
            "SELECT 1 FROM public.alumnos WHERE nss = %s LIMIT 1",
            (nss,),
        )
        if cursor.fetchone():
            raise ValueError("Ese NSS ya está registrado.")
        return nss, False

    for _ in range(1000):
        candidato = f"999{secrets.randbelow(100_000_000):08d}"
        cursor.execute(
            "SELECT 1 FROM public.alumnos WHERE nss = %s LIMIT 1",
            (candidato,),
        )
        if cursor.fetchone() is None:
            return candidato, True

    raise ValueError(
        "No se pudo asignar un NSS disponible. Intenta nuevamente."
    )


def registrar_alumno(datos):
    conexion = obtener_conexion()

    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                turno = turno_por_puntaje(datos["puntaje_examen_admision"])
                nss, nss_generado = _resolver_nss(cursor, datos.get("nss"))

                cursor.execute(
                    "SELECT carrera_id FROM public.carreras WHERE clave = %s",
                    (CARRERA_CLAVE,),
                )
                carrera = cursor.fetchone()
                if carrera is None:
                    raise ValueError("No existe la carrera ISC en la base de datos.")
                carrera_id = carrera[0]

                cursor.execute(
                    """
                    INSERT INTO public.alumnos (
                        numero_ficha, nss, nombres, apellido_paterno, apellido_materno,
                        curp, fecha_nacimiento, sexo, tipo_sanguineo,
                        calle, manzana, lote, colonia, codigo_postal,
                        municipio, estado, pais, telefono,
                        correo_personal, correo_institucional, carrera_id,
                        escuela_procedencia, promedio_previo,
                        puntaje_examen_admision,
                        contacto_emergencia_nombre,
                        contacto_emergencia_parentesco,
                        contacto_emergencia_telefono,
                        turno, semestre_actual
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s
                    )
                    RETURNING numero_control
                    """,
                    (
                        datos["ficha"],
                        nss,
                        datos["nombre"],
                        datos["apellido_paterno"],
                        datos.get("apellido_materno") or None,
                        datos["curp"],
                        datos["fecha_nacimiento_iso"],
                        datos["sexo"],
                        datos.get("tipo_sangre") or None,
                        datos["calle"],
                        datos.get("manzana") or None,
                        datos.get("lote") or None,
                        datos["colonia"],
                        datos["cp"],
                        datos["municipio"],
                        datos["estado"],
                        datos.get("pais") or "México",
                        datos["telefono"],
                        datos.get("correo") or None,
                        None,  # el correo institucional se calcula con el número de control
                        carrera_id,
                        datos.get("escuela_procedencia") or None,
                        datos.get("promedio"),
                        datos.get("puntaje_examen_admision"),
                        datos["contacto_emergencia_nombre"],
                        datos["contacto_emergencia_parentesco"],
                        datos["contacto_emergencia_telefono"],
                        turno.lower(),  # la base guarda "matutino" / "vespertino"
                        SEMESTRE_INICIAL,
                    ),
                )

                numero_control = cursor.fetchone()[0]
                correo_institucional = f"l{numero_control}@acapulco.tecnm.mx"

                cursor.execute(
                    """
                    UPDATE public.alumnos
                    SET correo_institucional = %s
                    WHERE numero_control = %s
                    """,
                    (correo_institucional, numero_control),
                )

        # Ya se confirmó la transacción: ahora sí se copian los PDF.
        guardados, fallidos = _guardar_pdfs(numero_control, datos.get("documentos"))

        mensaje = (
            "Alumno registrado correctamente.\n\n"
            f"Número de control: {numero_control}\n"
            f"NSS: {nss}"
            + (" (generado)" if nss_generado else "")
            + "\n"
            f"Correo institucional: {correo_institucional}\n"
            f"Turno asignado: {turno}\n"
            f"Semestre actual: {SEMESTRE_INICIAL}\n"
            f"Documentos guardados: {len(guardados)}"
        )
        if fallidos:
            mensaje += (
                "\n\nNo se pudieron copiar estos archivos, súbelos de nuevo más tarde:\n"
                + "\n".join(f"• {n}" for n in fallidos)
            )
        return True, mensaje

    except errors.UniqueViolation as error:
        restriccion = getattr(error.diag, "constraint_name", "") or ""
        return False, MENSAJES_UNICOS.get(
            restriccion, "Ya existe un dato que debe ser único."
        )

    except ValueError as error:
        return False, str(error)

    except psycopg.Error as error:
        print(f"Error al registrar alumno: {error}")
        return False, (
            "No se pudo registrar al alumno en la base de datos. "
            "Revisa la conexión y las restricciones de las tablas."
        )

    finally:
        conexion.close()


def buscar_alumno(clave):
    """Busca por número de control o número de ficha.
    Devuelve (alumno | None, mensaje_de_error | None).
    No utiliza alumno_id.
    """
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
                LIMIT 1
                """,
                (str(clave).strip(), str(clave).strip()),
            )
            fila = cursor.fetchone()

        if fila is None:
            return None, None

        alumno = {
            "numero_control": fila[0],
            "ficha": fila[1],
            "nombres": fila[2],
            "apellido_paterno": fila[3],
            "apellido_materno": fila[4],
            "estado": fila[5],
            "turno": fila[6],
            "semestre_actual": fila[7],
        }

        if (alumno["estado"] or "").strip().lower() == "baja":
            return None, "Ese alumno está dado de baja."

        return alumno, None

    except psycopg.Error as error:
        print(f"Error al buscar alumno para inscripción: {error}")
        return None, "No se pudo consultar la base de datos."

    finally:
        conexion.close()

def realizar_baja_logica(numero_control):
    """Baja lógica: el registro se conserva, solo cambia su estatus."""
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.alumnos
                    SET estado_alumno = 'baja'
                    WHERE numero_control = %s
                    """,
                    (numero_control,),
                )
                if cursor.rowcount == 0:
                    return False, "No existe un alumno con ese número de control."
        return True, "El registro se ha dado de baja correctamente."
    except psycopg.Error as error:
        print(f"Error en baja lógica: {error}")
        return False, "No se pudo procesar la baja en el sistema. Intente más tarde."
    finally:
        conexion.close()
