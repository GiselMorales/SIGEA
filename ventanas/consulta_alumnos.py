from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QColor

from conexiondb.db import obtener_conexion
from reportes.generador_pdf_consulta import generar_pdf_consulta
from reportes.generador_pdf import generar_pdf_oficial
from ventanas.base_consulta import VentanaConsulta
from ventanas.ventana import Config

# Los PDF se guardan en <proyecto>/reportes_generados
CARPETA_SALIDA = Path(__file__).resolve().parent.parent / "reportes_generados"

COLOR_ESTATUS = {
    "Activo": "#28882C",
    "Aspirante": Config.AZUL_ENTRAR,
    "Baja": "#C0392B",
    "Egresado": "#0037FF",
}


class VentanaConsultaAlumnos(VentanaConsulta):
    COLUMNAS_PDF = ["No.", "No. control", "Nombre completo", "Carrera", "CURP", "Turno", "Sem.", "Estatus"]
    ANCHOS_PDF = [35, 75, 250, 50, 130, 70, 40, 70]
    OPCIONES_FILTRO = ["Todos", "No. control", "Nombre", "CURP"]

    def __init__(self, menu=None):
        super().__init__("SIGEA - Consultas de alumnos", "CONSULTAS", menu)
        self._alumnos = []
        self._filtro_texto = "Todos los alumnos"

    # ------------------------------------------------------------------
    #  Consulta
    # ------------------------------------------------------------------
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
                        c.nombre,
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

            alumnos = []
            for (control, nombres, paterno, materno, clave, carrera, curp,
                 sexo, estatus, turno, semestre) in filas:
                alumnos.append({
                    "control": control,
                    "nombre": " ".join(p for p in (nombres, paterno, materno) if p),
                    "clave_carrera": clave,
                    "carrera": carrera,
                    "curp": (curp or "").strip(),
                    "sexo": sexo,
                    "estatus": (estatus or "").capitalize(),
                    "turno": (turno or "").capitalize(),
                    "semestre": semestre,
                })

            self._alumnos = alumnos
            self._total_resultados = len(alumnos)
            self._filtro_texto = (
                f"{campo}: {valor}" if valor and campo != "Todos"
                else (f"«{valor}»" if valor else "Todos los alumnos")
            )
            self._mostrar(alumnos)

        except Exception as error:
            print(f"Error al consultar alumnos: {error}")
            QMessageBox.warning(self, "Error", "No fue posible consultar los alumnos.")

        finally:
            conexion.close()

    def _mostrar(self, alumnos):
        total = len(alumnos)
        self._numeros["total"].setText(str(total))
        self._numeros["mujeres"].setText(str(sum(a["sexo"] == "Mujer" for a in alumnos)))
        self._numeros["hombres"].setText(str(sum(a["sexo"] == "Hombre" for a in alumnos)))
        self._numeros["carreras"].setText(str(len({a["clave_carrera"] for a in alumnos})))

        if not alumnos:
            self.mostrar_vacio("No se encontraron alumnos con esa búsqueda.")
            self.etiqueta_info.setText("")
            return

        self.limpiar_resultados()
        for alumno in alumnos[:self.MAX_TARJETAS]:
            self.agregar_resultado(self._tarjeta_alumno(alumno))
        self.cerrar_resultados()

        if total > self.MAX_TARJETAS:
            self.etiqueta_info.setText(
                f"{total} registro(s). Se muestran los primeros {self.MAX_TARJETAS}; "
                "el PDF incluye todos."
            )
        else:
            self.etiqueta_info.setText(f"{total} registro(s) encontrado(s)")

    def _tarjeta_alumno(self, a):
        tarjeta = QFrame()
        tarjeta.setObjectName("resultado")
        tarjeta.setAttribute(Qt.WA_StyledBackground, True)
        tarjeta.setFixedHeight(80)
        tarjeta.setStyleSheet(
            "#resultado { background-color: #FFFFFF; border-radius: 12px; }"
        )

        lay = QHBoxLayout(tarjeta)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        nombre = QLabel(a["nombre"])
        nombre.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 13px; font-weight: bold; "
            "background: transparent;"
        )
        linea1 = QLabel(f"No. control: {a['control']}   •   CURP: {a['curp'] or '-'}")
        linea2 = QLabel(
            f"{a['carrera']}   •   Semestre {a['semestre'] or '-'}   •   "
            f"Turno {a['turno'] or '-'}"
        )
        for etiqueta in (linea1, linea2):
            etiqueta.setStyleSheet(
                f"color: {Config.TEXTO_SUBTITULO}; font-size: 11px; background: transparent;"
            )
        textos.addWidget(nombre)
        textos.addWidget(linea1)
        textos.addWidget(linea2)
        lay.addLayout(textos, 1)

        color = QColor(COLOR_ESTATUS.get(a["estatus"], Config.TEXTO_SUBTITULO))
        chip = QLabel(a["estatus"] or "-")
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet(
            f"color: {color.name()}; font-size: 11px; font-weight: bold; "
            f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 38); "
            "border-radius: 10px; padding: 4px 14px;"
        )
        lay.addWidget(chip, 0, Qt.AlignVCenter)
        return tarjeta

    # ------------------------------------------------------------------
    #  PDF: ficha sin tabla si hay 1 alumno; listado con tabla si hay varios
    # ------------------------------------------------------------------
    def generar_pdf(self):
        alumnos = self._alumnos
        if not alumnos:
            self.mostrar_advertencia("SIGEA", "Primero haz una consulta que tenga resultados.")
            return

        marca = f"{datetime.now():%Y%m%d_%H%M%S}"
        try:
            if len(alumnos) == 1:
                a = alumnos[0]
                ruta = CARPETA_SALIDA / f"alumno_{a['control']}_{marca}.pdf"
                generar_pdf_oficial(
                    {
                        "campos": [
                            ("Nombre", a["nombre"]),
                            ("Número de control", a["control"]),
                            ("CURP", a["curp"]),
                            ("Carrera", a["carrera"]),
                            ("Semestre", a["semestre"]),
                            ("Turno", a["turno"]),
                            ("Estatus", a["estatus"]),
                        ],
                    },
                    ruta,
                )
            else:
                filas_pdf = [
                    [
                        str(i).zfill(2), a["control"], a["nombre"], a["clave_carrera"],
                        a["curp"], a["turno"], a["semestre"], a["estatus"],
                    ]
                    for i, a in enumerate(alumnos, start=1)
                ]
                mujeres = sum(a["sexo"] == "Mujer" for a in alumnos)
                hombres = sum(a["sexo"] == "Hombre" for a in alumnos)
                ruta = CARPETA_SALIDA / f"consulta_alumnos_{marca}.pdf"
                generar_pdf_consulta(
                    "CONSULTA DE ALUMNOS",
                    self.COLUMNAS_PDF,
                    filas_pdf,
                    ruta,
                    anchos=self.ANCHOS_PDF,
                    filtro=self._filtro_texto,
                    resumen=f"Total: {len(alumnos)}   Mujeres: {mujeres}   Hombres: {hombres}",
                )

            self.etiqueta_info.setText(f"PDF generado: {ruta.name}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))

        except Exception as error:
            print(f"Error al generar el PDF: {error}")
            QMessageBox.warning(self, "Error", "No fue posible generar el PDF.")