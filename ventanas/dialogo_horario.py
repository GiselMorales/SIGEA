from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from Logica import horarios as lh
from ventanas.componentes import ESTILO_BOTON_SUBIR, ESTILO_BOTON_QUITAR

ESTILO = """
QDialog { background-color: #F4F7FB; }
QLabel { color: #1B2A3A; font-size: 12px; background: transparent; }
QLineEdit, QComboBox {
    background: white; color: #1B2A3A; border: 1px solid #B8C4D2;
    border-radius: 8px; padding: 6px 10px; min-height: 24px;
}
QComboBox QAbstractItemView { background: white; color: #1B2A3A; }
"""


class DialogoHorario(QDialog):
    """Alta de un horario (semestre + turno). Si 'semestre' viene, queda fijo."""

    def __init__(self, semestre=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir horario")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(ESTILO)
        self.horario_id = None
        self._ruta_pdf = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(10)

        lay.addWidget(QLabel("<b>Semestre</b>"))
        self.semestre = QComboBox()
        for n in range(1, 13):
            self.semestre.addItem(f"Semestre {n}", n)
        if semestre:
            self.semestre.setCurrentIndex(int(semestre) - 1)
            self.semestre.setEnabled(False)
        lay.addWidget(self.semestre)

        lay.addWidget(QLabel("<b>Turno</b>"))
        self.turno = QComboBox()
        self.turno.addItem("Matutino", "matutino")
        self.turno.addItem("Vespertino", "vespertino")
        lay.addWidget(self.turno)

        lay.addWidget(QLabel("<b>Nombre o descripción</b>"))
        self.descripcion = QLineEdit()
        self.descripcion.setPlaceholderText("Ej. Horario 1er semestre matutino")
        self.descripcion.setMaxLength(120)
        lay.addWidget(self.descripcion)

        lay.addWidget(QLabel("<b>PDF del horario (opcional)</b>"))
        fila_pdf = QHBoxLayout()
        self.etiqueta_pdf = QLabel("Ningún archivo seleccionado.")
        boton_pdf = QPushButton("Seleccionar PDF")
        boton_pdf.setFixedSize(150, 36)
        boton_pdf.setCursor(Qt.PointingHandCursor)
        boton_pdf.setStyleSheet(ESTILO_BOTON_SUBIR)
        boton_pdf.clicked.connect(self._elegir_pdf)
        fila_pdf.addWidget(self.etiqueta_pdf, 1)
        fila_pdf.addWidget(boton_pdf)
        lay.addLayout(fila_pdf)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #C0392B; font-weight: bold;")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        botones = QHBoxLayout()
        botones.addStretch()
        cancelar = QPushButton("Cancelar")
        cancelar.setFixedSize(110, 38)
        cancelar.setStyleSheet(ESTILO_BOTON_QUITAR)
        cancelar.clicked.connect(self.reject)
        guardar = QPushButton("Guardar horario")
        guardar.setFixedSize(150, 38)
        guardar.setStyleSheet(ESTILO_BOTON_SUBIR)
        guardar.setDefault(True)
        guardar.clicked.connect(self._guardar)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        lay.addLayout(botones)

    def _elegir_pdf(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Selecciona el PDF del horario", "", "Documentos PDF (*.pdf)"
        )
        if ruta:
            self._ruta_pdf = ruta
            self.etiqueta_pdf.setText(Path(ruta).name)

    def _guardar(self):
        ok, mensaje, horario_id = lh.crear_horario(
            self.semestre.currentData(),
            self.turno.currentData(),
            self.descripcion.text(),
            self._ruta_pdf,
        )
        if not ok:
            self.error.setText(mensaje)
            return
        if "no se pudo copiar" in mensaje:
            QMessageBox.warning(self, "SIGEA", mensaje)
        self.horario_id = horario_id
        self.accept()