import re
from Logica import validaciones as v
from Logica import inscripciones as li
from Logica import horarios as lh
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ESTILO_BOTON_SUBIR, ESTILO_COMBO_TIPO
from ventanas.dialogo_horario import DialogoHorario


class VentanaAltaInscripcion(VentanaAlta):
    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Alta de inscripción", "ALTA DE INSCRIPCIÓN", "REGISTRAR INSCRIPCIÓN", menu
        )

    def construir_secciones(self):
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
                    self.campo("grupo", "Grupo"),
                    pesos=(4, 1, 1),
                ),
            ],
            self._validar_datos,
        )

        self.agregar_seccion(
            "HORARIO",
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

    # ------------------------------------------------------------------
    #  Horario: se elige uno del semestre o se añade uno nuevo ahí mismo
    # ------------------------------------------------------------------
    def _selector_horario(self):
        self._semestre_horario = None
        self.combo_horario = QComboBox()
        self.combo_horario.setFixedHeight(40)
        self.combo_horario.setCursor(Qt.PointingHandCursor)
        self.combo_horario.setStyleSheet(ESTILO_COMBO_TIPO)
        self.combo_horario.currentIndexChanged.connect(
            lambda _i: self._cambio("horario")
        )
        self._cargar_horarios(None)
        self._registrar_lector("horario", self.combo_horario.currentData, self.combo_horario)

        boton = QPushButton("+ Añadir horario")
        boton.setFixedSize(170, 40)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setStyleSheet(ESTILO_BOTON_SUBIR)
        boton.clicked.connect(self._añadir_horario)

        caja = self._contenedor("selectorHorario")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.crear_label_campo(
            "HORARIO DEL SEMESTRE (MATUTINO / VESPERTINO)",
            color="rgba(128, 128, 128, 178)",
        ))
        fila = QHBoxLayout()
        fila.setSpacing(12)
        fila.addWidget(self.combo_horario, 1)
        fila.addWidget(boton, 0)
        lay.addLayout(fila)
        return caja

    def _cargar_horarios(self, semestre, seleccionar_id=None):
        self._semestre_horario = semestre
        self.combo_horario.blockSignals(True)
        self.combo_horario.clear()
        self.combo_horario.addItem("Selecciona un horario", None)
        if semestre:
            for h in lh.listar_horarios(semestre):
                self.combo_horario.addItem(
                    f"Sem. {h['semestre']} · {h['turno'].capitalize()} — {h['descripcion']}",
                    h["id"],
                )
            indice = self.combo_horario.findData(seleccionar_id)
            if indice >= 0:
                self.combo_horario.setCurrentIndex(indice)
        self.combo_horario.blockSignals(False)

    def _añadir_horario(self):
        if not self._semestre_horario:
            self.mostrar_advertencia("SIGEA", "Primero valida los datos de la inscripción.")
            return
        dialogo = DialogoHorario(self._semestre_horario, self)
        if dialogo.exec() and dialogo.horario_id:
            self._cargar_horarios(self._semestre_horario, dialogo.horario_id)
            self._cambio("horario")

    @staticmethod
    def _numero_semestre(valor):
        coincidencia = re.match(r"\s*(\d+)", str(valor or ""))
        return int(coincidencia.group(1)) if coincidencia else None

    def _validar_datos(self, datos):
        errores, limpio = v.validar_inscripcion(datos)
        if not errores:
            semestre = self._numero_semestre(limpio.get("semestre", datos.get("semestre")))
            if semestre != self._semestre_horario:
                self._cargar_horarios(semestre)
        return errores, limpio

    def _validar_horario(self, datos):
        horario_id = datos.get("horario")
        if not horario_id:
            return {"horario": "Selecciona un horario o añade uno nuevo."}, {}
        return {}, {
            "horario_id": horario_id,
            "horario_texto": self.combo_horario.currentText(),
        }

    def limpiar(self):
        super().limpiar()
        self._cargar_horarios(None)

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

        limpio["numero_control"] = alumno["numero_control"]
        limpio["alumno_nombre"] = alumno["nombre"]
        return {}, limpio

    def resumen_confirmacion(self, datos):
        lineas = [
            ("Alumno", datos.get("alumno_nombre")),
            ("Número de control", datos.get("numero_control")),
            ("Trámite", datos.get("tipo_inscripcion")),
            ("Periodo", datos.get("periodo")),
            ("Semestre", datos.get("semestre")),
            ("Horario", datos.get("horario_texto")),
            ("PDF adjuntos", str(len(datos.get("documentos") or []))),
        ]
        return lineas, ""

    def guardar(self, datos):
        return li.registrar_tramite(datos)