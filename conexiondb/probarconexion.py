from db import obtener_conexion
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
conexion = obtener_conexion()

if conexion:
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)

            print("Tablas de SIGEA:")
            for fila in cursor.fetchall():
                print("-", fila[0])

    finally:
        conexion.close()
