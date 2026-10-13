
import psycopg


def obtener_conexion():
    try:
        conexion = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="sigea",
            user="postgres",
            password="Yuliana2005"
        )

        return conexion

    except psycopg.Error as error:
        print(f"Error al conectar con PostgreSQL: {error}")
        return None
