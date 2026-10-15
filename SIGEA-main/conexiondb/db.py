
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion():
    try:
        conexion = psycopg.connect(
            host=os.getenv("host"),
            port=os.getenv("port", "5432"),
            dbname=os.getenv("name", "postgres"),
            user=os.getenv("user"),
            password=os.getenv("password"),
            sslmode="require",
            connect_timeout=10
        )

        return conexion

    except psycopg.Error as error:
        print(f"Error al conectar con Supabase: {error}")
        return None
