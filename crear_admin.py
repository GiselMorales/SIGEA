
import os
import hashlib
import secrets
import getpass
import psycopg


def crear_hash(contrasena):
    salt = secrets.token_bytes(16)
    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        salt,
        600_000
    )

    return (
        "pbkdf2_sha256$600000$"
        + salt.hex()
        + "$"
        + resultado.hex()
    )


def main():
    print("=== SIGEA | Administrador inicial ===")

    usuario_bd = input("Usuario de PostgreSQL: ").strip()
    contrasena_bd = getpass.getpass(
        "Contraseña de PostgreSQL: "
    )

    nombre_usuario = input(
        "Nombre de usuario para SIGEA: "
    ).strip()

    contrasena = getpass.getpass(
        "Contraseña nueva para SIGEA: "
    )
    confirmar = getpass.getpass(
        "Confirma la contraseña: "
    )

    if not nombre_usuario:
        print("Error: el usuario no puede estar vacío.")
        return

    if len(contrasena) < 12:
        print("Error: usa al menos 12 caracteres.")
        return

    if contrasena != confirmar:
        print("Error: las contraseñas no coinciden.")
        return

    try:
        with psycopg.connect(
            host="localhost",
            port=5432,
            dbname="sigea",
            user=usuario_bd,
            password=contrasena_bd
        ) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT 1
                    FROM usuarios
                    WHERE rol = 'administrativo'
                    LIMIT 1;
                """)

                if cursor.fetchone():
                    print(
                        "Ya existe un usuario administrativo. "
                        "No se creó otro."
                    )
                    return

                cursor.execute("""
                    INSERT INTO usuarios (
                        nombre_usuario,
                        contrasena_hash,
                        rol,
                        activo
                    )
                    VALUES (%s, %s, %s, TRUE);
                """, (
                    nombre_usuario,
                    crear_hash(contrasena),
                    "administrativo"
                ))

            print("Administrador creado correctamente.")

    except psycopg.Error as error:
        print("No se pudo crear el administrador.")
        print("Detalle:", error)


if __name__ == "__main__":
    main()
