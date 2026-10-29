from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from Logica import validaciones as v
from Logica import inscripciones as li
from Logica import horarios as lh
from ventanas.alta_horario import VentanaAltaHorario
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ESTILO_BOTON_SUBIR, ESTILO_COMBO_TIPO, destinos_barra


class VentanaAltaInscripcion(VentanaAlta):
    DESTINOS_BARRA = destinos_barra()

    def __init__(self, menu=None):
        self._ultima_ruta_pdf = None
        super().__init__(
            "SIGEA - Alta de inscripción", "ALTA DE INSCRIPCIÓN", "REGISTRAR INSCRIPCIÓN", menu
        )

    def construir_secciones(self):
        self._alumno = None
        self._contexto = None            # (periodo, semestre) de los grupos cargados

        self.agregar_seccion(
            "NÚMERO DE FICHA O DE CONTROL",
            [self.fila(self.campo("ficha", "Número de ficha / control"), None, pesos=(1, 2))],
            self._validar_alumno,
        )

        self.agregar_seccion(
            "DATOS DE LA INSCRIPCIÓN",
            [
                self.fila(
                    self.campo("periodo", "Periodo (ej. AGO-DIC 2026)", v.periodos_disponibles()),
                    self.selector("tipo_inscripcion", "Tipo de trámite", v.TIPOS_INSCRIPCION),
                    pesos=(1, 1),
                ),
                self.fila(
                    self.campo("carrera", "Carrera", v.CARRERAS),
                    self.campo("semestre", "Semestre", v.SEMESTRES),
                    pesos=(4, 1),
                ),
            ],
            self._validar_datos,
        )

        self.agregar_seccion(
            "GRUPO Y HORARIO",
            [self._selector_horario()],
            self._validar_horario,
        )

        self.agregar_seccion(
            "COMPROBANTES EN PDF",
            [self.zona_pdf("documentos")],
            lambda d: v.validar_documentos(
                d, minimo=1, etiqueta="Comprobantes (pago, horario...)"
            ),
        )

    def _validar_alumno(self, datos):
        # Acepta cualquier número (solo dígitos) y lo busca como control o como ficha.
        errores, limpio = v.validar_numero(
            datos, "ficha", "Número de ficha / control", min_len=1, max_len=20
        )
        if errores:
            return errores, limpio

        alumno, problema = li.buscar_alumno(limpio["ficha"])
        if problema:
            return {"ficha": problema}, {}
        if alumno is None:
            return {"ficha": "No existe un alumno con ese número de ficha o de control."}, {}

        self._alumno = alumno
        limpio["numero_control"] = alumno["numero_control"]
        limpio["alumno_nombre"] = alumno["nombre"]
        return {}, limpio

    def _validar_datos(self, datos):
        errores, limpio = v.validar_inscripcion(datos)
        if not errores:
            self._cargar_grupos(limpio["periodo"], int(limpio["semestre"]))
        return errores, limpio

    def _selector_horario(self):
        self.combo_horario = QComboBox()
        self.combo_horario.setFixedHeight(40)
        self.combo_horario.setCursor(Qt.PointingHandCursor)
        self.combo_horario.setStyleSheet(ESTILO_COMBO_TIPO)
        self.combo_horario.addItem("Selecciona el grupo y horario", None)
        self.combo_horario.currentIndexChanged.connect(lambda _i: self._cambio("horario"))
        self._registrar_lector("horario", self.combo_horario.currentData, self.combo_horario)

        actualizar = QPushButton("Actualizar lista")
        actualizar.setFixedSize(150, 40)
        actualizar.setCursor(Qt.PointingHandCursor)
        actualizar.setStyleSheet(ESTILO_BOTON_SUBIR)
        actualizar.clicked.connect(self._actualizar_grupos)

        nuevo = QPushButton("+ Añadir horario")
        nuevo.setFixedSize(150, 40)
        nuevo.setCursor(Qt.PointingHandCursor)
        nuevo.setStyleSheet(ESTILO_BOTON_SUBIR)
        nuevo.clicked.connect(self._añadir_horario)

        ver_pdf = QPushButton("Ver horario PDF")
        ver_pdf.setFixedSize(150, 40)
        ver_pdf.setCursor(Qt.PointingHandCursor)
        ver_pdf.setStyleSheet(ESTILO_BOTON_SUBIR)
        ver_pdf.clicked.connect(self._ver_horario_pdf)

        self._btn_pdf_alumno = QPushButton("Abrir PDF del último alumno inscrito")
        self._btn_pdf_alumno.setFixedSize(250, 40)
        self._btn_pdf_alumno.setCursor(Qt.PointingHandCursor)
        self._btn_pdf_alumno.setStyleSheet(ESTILO_BOTON_SUBIR)
        self._btn_pdf_alumno.setEnabled(False)
        self._btn_pdf_alumno.clicked.connect(self._abrir_pdf_alumno)

        self._aviso_grupos = self.crear_label_subtitulo("", 10, "#5B6B79")
        self._aviso_grupos.setWordWrap(True)

        caja = self._contenedor("selectorHorario")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self.crear_label_campo(
            "GRUPO (MATUTINO / VESPERTINO)", color="rgba(128, 128, 128, 178)"
        ))
        fila = QHBoxLayout()
        fila.setSpacing(12)
        fila.addWidget(self.combo_horario, 1)
        fila.addWidget(actualizar, 0)
        fila.addWidget(nuevo, 0)
        lay.addLayout(fila)
        lay.addWidget(ver_pdf, 0, Qt.AlignLeft)
        lay.addWidget(self._btn_pdf_alumno, 0, Qt.AlignLeft)
        lay.addWidget(self._aviso_grupos)
        return caja

    def _cargar_grupos(self, periodo, semestre):
        self._contexto = (periodo, semestre)
        grupos = lh.grupos_disponibles(periodo, semestre)

        turno_alumno = ((self._alumno or {}).get("turno") or "").lower()
        if turno_alumno:                             # solo el grupo del turno del alumno
            grupos = [g for g in grupos if not g["turno"] or g["turno"] == turno_alumno]

        self.combo_horario.blockSignals(True)
        self.combo_horario.clear()
        self.combo_horario.addItem("Selecciona el grupo y horario", None)
        for g in grupos:
            turno = (g["turno"] or "").capitalize() or "Sin turno"
            self.combo_horario.addItem(
                f"Grupo {g['clave']} · {turno} — {g['materias']} materias",
                {"clave": g["clave"], "turno": g["turno"]},
            )
        self.combo_horario.blockSignals(False)

        if grupos:
            self._aviso_grupos.setText(
                f"Alumno de turno {turno_alumno}." if turno_alumno else ""
            )
        else:
            self._aviso_grupos.setText(
                "No hay grupos para ese semestre y periodo"
                + (f" en el turno {turno_alumno}" if turno_alumno else "")
                + ". Presiona «+ Añadir horario» para darlos de alta."
            )

    def _añadir_horario(self):
        """Abre el alta de horarios; al cerrarla, la lista de grupos se actualiza sola."""
        ventana = VentanaAltaHorario(self)
        ventana.al_cerrar = self._actualizar_grupos
        self._ventana_horario = ventana
        ventana.show()

    def _actualizar_grupos(self):
        if self._contexto:
            self._cargar_grupos(*self._contexto)

    def _ver_horario_pdf(self):
        seleccion = self.combo_horario.currentData()
        if not seleccion or not self._contexto:
            QMessageBox.information(self, "SIGEA", "Selecciona primero un grupo.")
            return

        periodo, semestre = self._contexto
        datos = lh.obtener_horario(
            periodo, semestre, seleccion["turno"], seleccion["clave"]
        )
        if not datos:
            QMessageBox.warning(self, "SIGEA", "No se pudo consultar el horario del grupo.")
            return

        sugerido = f"Horario_{seleccion['clave']}_{periodo.replace(' ', '_')}.pdf"
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar o ver horario del grupo", sugerido, "Documentos PDF (*.pdf)"
        )
        if not ruta:
            return
        try:
            from reportes.generador_pdf import generar_pdf_horario

            generar_pdf_horario(datos, ruta)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(ruta).resolve())))
        except Exception as error:
            QMessageBox.critical(self, "SIGEA", f"No se pudo generar el PDF:\n{error}")

    def _abrir_pdf_alumno(self):
        if self._ultima_ruta_pdf and Path(self._ultima_ruta_pdf).is_file():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(Path(self._ultima_ruta_pdf).resolve()))
            )
        else:
            QMessageBox.information(
                self, "SIGEA", "Todavía no hay un PDF de horario generado en esta sesión."
            )

    def _validar_horario(self, datos):
        seleccion = datos.get("horario")
        if not seleccion:
            return {"horario": "Selecciona el grupo y horario del semestre."}, {}
        turno = str(seleccion.get("turno") or "").strip().lower()
        clave = str(seleccion.get("clave") or "").strip().upper()
        if turno not in ("matutino", "vespertino"):
            return {"horario": "Selecciona un turno válido."}, {}

        return {}, {
            "horario_clave": clave,
            "horario_turno": turno,
            "horario_texto": self.combo_horario.currentText(),
        }
    # ------------------------------------------------------------------
    def resumen_confirmacion(self, datos):
        lineas = [
            ("Alumno", datos.get("alumno_nombre")),
            ("Número de control", datos.get("numero_control")),
            ("Trámite", datos.get("tipo_inscripcion")),
            ("Periodo", datos.get("periodo")),
            ("Semestre", datos.get("semestre")),
            ("Grupo y horario", datos.get("horario_texto")),
            ("PDF adjuntos", str(len(datos.get("documentos") or []))),
        ]
        return lineas, "El alumno quedará inscrito en todas las materias del grupo elegido."

    def guardar(self, datos):
        print("DEBUG guardar():", datos)

        ok, mensaje = li.registrar_tramite(datos)
        if ok:
            prefijo = "PDF del horario: "
            self._ultima_ruta_pdf = next(
                (linea[len(prefijo):].strip()
                 for linea in mensaje.splitlines() if linea.startswith(prefijo)),
                None,
            )
            self._btn_pdf_alumno.setEnabled(bool(self._ultima_ruta_pdf))
        return ok, mensaje

    def limpiar(self):
        super().limpiar()
        self._alumno = None
        self._contexto = None
        self.combo_horario.blockSignals(True)
        self.combo_horario.clear()
        self.combo_horario.addItem("Selecciona el grupo y horario", None)
        self.combo_horario.blockSignals(False)
        self._aviso_grupos.setText("")
