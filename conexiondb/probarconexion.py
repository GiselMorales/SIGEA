from db import obtener_conexion

conexion = obtener_conexion()

if conexion:
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT
                    current_database(),
                    current_user,
                    inet_server_addr();
            """)

            base, usuario, servidor = cursor.fetchone()

            print("Conexión exitosa")
            print("Base de datos:", base)
            print("Usuario:", usuario)
            print("Servidor:", servidor)

    finally:
        conexion.close()