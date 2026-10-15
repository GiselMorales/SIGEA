from pathlib import Path
import psycopg
from psycopg import errors
from conexiondb.db import obtener_conexion

CARRERA_CLAVE = "ISC"
def registrar_alumno(datos):
    conexion = obtener_conexion()

    if conexion is None:
        return False, "No fue posible conectar con la base de datos."
    try:
        with conexion:
            with conexion.cursor() as cursor:
                # id de carrera
                cursor.execute(
                    """
                    SELECT carrera_id
                    FROM public.carreras
                    WHERE clave = %s
                    """,
                    (CARRERA_CLAVE,),
                )
                carrera = cursor.fetchone()

                if carrera is None:
                    raise ValueError(
                        "No existe la carrera ISC en la base de datos."
                    )

                carrera_id = carrera[0]
                # Insertar el alumno en la tabla "alumnos"
                cursor.execute(
                    """
                    INSERT INTO public.alumnos (
                        numero_ficha,
                        nombres,
                        apellido_paterno,
                        apellido_materno,
                        curp,
                        fecha_nacimiento,
                        sexo,
                        tipo_sanguineo,
                        calle,
                        manzana,
                        lote,
                        colonia,
                        codigo_postal,
                        municipio,
                        estado,
                        pais,
                        telefono,
                        correo_personal,
                        correo_institucional,
                        carrera_id,
                        escuela_procedencia,
                        promedio_previo,
                        puntaje_examen_admision,
                        contacto_emergencia_nombre,
                        contacto_emergencia_parentesco,
                        contacto_emergencia_telefono
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING numero_control
                    """,
                    (
                        datos["ficha"],
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
                        None,  # Se actualiza después de generar el num
                        carrera_id,
                        datos.get("escuela_procedencia") or None,
                        datos.get("promedio"),
                        datos.get("puntaje_examen_admision"),
                        datos["contacto_emergencia_nombre"],
                        datos["contacto_emergencia_parentesco"],
                        datos["contacto_emergencia_telefono"],
                    ),
                )

                numero_control = cursor.fetchone()[0]
                correo_institucional = (
                    f"l{numero_control}@acapulco.tecnm.mx"
                )

                cursor.execute(
                    """
                    UPDATE public.alumnos
                    SET correo_institucional = %s
                    WHERE numero_control = %s
                    """,
                    (correo_institucional, numero_control),
                )

                # los archivos PDF se guardan en la carpeta "documentos" con el nombre "<numero_control>_<nombre_archivo>"

        return True, (
            "Alumno registrado correctamente.\n\n"
            f"Número de control: {numero_control}\n"
            f"Correo institucional: {correo_institucional}"
        )

    except errors.UniqueViolation as error:
        restriccion = getattr(error.diag, "constraint_name", "")

        
        if restriccion == "alumnos_numero_ficha_key":
            mensaje = "Ese número de ficha ya está registrado."
        elif restriccion == "alumnos_curp_key":
            mensaje = "Esa CURP ya está registrada."
        elif restriccion == "alumnos_correo_personal_key":
            mensaje = "Ese correo personal ya está registrado."
        elif restriccion == "alumnos_correo_institucional_key":
            mensaje = "Ese correo institucional ya está registrado."
        else:
            mensaje = "Ya existe un dato que debe ser único."

        return False, mensaje

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
# ========================================================
# NUEVA FUNCIÓN DE BAJA LÓGICA (AÑADIR AQUÍ)
# ========================================================
def realizar_baja_logica(numero_control):
    """
    Realiza una baja lógica cambiando el estado o un campo lógico,
    ocultándolo al usuario pero conservándolo para el administrador.
    """
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No fue posible conectar con la base de datos."

    try:
        with conexion:
            with conexion.cursor() as cursor:
                # Actualiza el estado a 'baja' o activo a FALSE según tu tabla
                cursor.execute(
                    """
                    UPDATE public.alumnos
                    SET estado = 'baja'
                    WHERE numero_control = %s
                    """,
                    (numero_control,),
                )
        return True, "El registro se ha dado de baja correctamente de su vista."
    except psycopg.Error as error:
        print(f"Error en baja lógica: {error}")
        return False, "No se pudo procesar la baja en el sistema. Intente más tarde."
    finally:
        conexion.close()