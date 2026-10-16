from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from conexiondb.db import obtener_conexion
from reportes.generador_pdf_consulta import generar_pdf_consulta
from ventanas.base_consulta import VentanaConsulta

# Los PDF se guardan en <proyecto>/reportes_generados
CARPETA_SALIDA = Path(__file__).resolve().parent.parent / "reportes_generados"


class VentanaConsultaAlumnos(VentanaConsulta):
    COLUMNAS = ["No.", "No. control", "Nombre completo", "Carrera", "CURP", "Turno", "Sem.", "Estatus"]
    ANCHOS_PDF = [35, 75, 250, 50, 130, 70, 40, 70]
    OPCIONES_FILTRO = ["Todos", "No. control", "Nombre", "CURP"]

    def __init__(self, menu=None):
        super().__init__("SIGEA - Consultas de alumnos", "CONSULTAS", menu)
        self.etiqueta_info.setText("Elige un filtro y presiona «Generar PDF».")

    def consultar(self):
        conexion = obtener_conexion()

        if conexion is None:
            QMessageBox.warning(
                self, "Error de conexión",
                "No fue posible conectar con la base de datos.",
            )
            return

        campo = self.selector_campo.obtener_seleccion()
        valor = self.campo_valor.valor().strip()
        nombre_sql = ("(a.nombres || ' ' || a.apellido_paterno || ' ' "
                      "|| COALESCE(a.apellido_materno, ''))")
        columnas = {
            "No. control": ["a.numero_control::text"],
            "Nombre": [nombre_sql],
            "CURP": ["a.curp"],
        }.get(campo, ["a.numero_control::text", nombre_sql, "a.curp"])

        where, parametros = "", []
        if valor:
            where = "WHERE " + " OR ".join(f"{c} ILIKE %s" for c in columnas)
            parametros = [f"%{valor}%"] * len(columnas)

        try:
            with conexion.cursor() as cursor:
                cursor.execute(f"""
                    SELECT
                        a.numero_control,
                        a.nombres,
                        a.apellido_paterno,
                        a.apellido_materno,
                        c.clave,
                        a.curp,
                        a.sexo,
                        a.estado_alumno,
                        a.turno,
                        a.semestre_actual
                    FROM public.alumnos AS a
                    INNER JOIN public.carreras AS c
                        ON a.carrera_id = c.carrera_id
                    {where}
                    ORDER BY a.apellido_paterno, a.apellido_materno, a.nombres
                """, parametros)
                filas = cursor.fetchall()

            mujeres = sum(f[6] == "Mujer" for f in filas)
            hombres = sum(f[6] == "Hombre" for f in filas)
            carreras = len({f[4] for f in filas})

            self._numeros["total"].setText(str(len(filas)))
            self._numeros["mujeres"].setText(str(mujeres))
            self._numeros["hombres"].setText(str(hombres))
            self._numeros["carreras"].setText(str(carreras))

            if not filas:
                self.etiqueta_info.setText("No se encontraron registros con esa búsqueda.")
                return

            filas_pdf = []
            for i, (control, nombres, paterno, materno, carrera, curp,
                    _sexo, estatus, turno, semestre) in enumerate(filas, start=1):
                filas_pdf.append([
                    str(i).zfill(2),
                    control,
                    " ".join(p for p in (nombres, paterno, materno) if p),
                    carrera,
                    (curp or "").strip(),
                    (turno or "").capitalize(),
                    semestre,
                    (estatus or "").capitalize(),
                ])

            filtro = f"{campo}: {valor}" if valor and campo != "Todos" else (
                f"«{valor}»" if valor else "Todos los alumnos"
            )
            ruta = CARPETA_SALIDA / f"consulta_alumnos_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            generar_pdf_consulta(
                "CONSULTA DE ALUMNOS",
                self.COLUMNAS,
                filas_pdf,
                ruta,
                anchos=self.ANCHOS_PDF,
                filtro=filtro,
                resumen=f"Total: {len(filas)}   Mujeres: {mujeres}   Hombres: {hombres}",
            )

            self.etiqueta_info.setText(f"{len(filas)} registro(s). PDF generado: {ruta.name}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))

        except Exception as error:
            print(f"Error al consultar alumnos: {error}")
            QMessageBox.warning(self, "Error", "No fue posible generar el PDF de la consulta.")

        finally:
            conexion.close()