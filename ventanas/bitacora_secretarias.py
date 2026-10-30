from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from Logica.bitacora import es_administrador, listar_entradas_secretarias
from ventanas.ventana import VentanaBase


class VentanaBitacoraSecretarias(VentanaBase):
    def __init__(self, menu=None, usuario=""):
        super().__init__("SIGEA - Bitácora de accesos", 900, 620)
        self.menu = menu
        self.usuario = usuario
        self._armar_interfaz()
        self.actualizar()
        self.centrar_ventana()

    def _armar_interfaz(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(16)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self.crear_label_titulo("BITÁCORA DE ACCESOS", 28))
        cabecera.addStretch()
        cabecera.addWidget(
            self.crear_boton_salida("Menú", self.close, ancho=120, alto=40)
        )
        raiz.addLayout(cabecera)

        fila_acciones = QHBoxLayout()
        fila_acciones.addWidget(
            self.crear_label_subtitulo(
                "Accesos registrados de secretaría y docentes", 11, "#FFFFFF"
            ),
            1,
        )
        self.boton_actualizar = self.crear_boton_secundario(
            "Actualizar", self.actualizar, ancho=145, alto=42
        )
        fila_acciones.addWidget(self.boton_actualizar)
        raiz.addLayout(fila_acciones)

        tarjeta = QFrame()
        tarjeta.setObjectName("tablaBitacora")
        tarjeta.setStyleSheet(
            "#tablaBitacora { background: white; border-radius: 12px; }"
        )
        layout_tabla = QVBoxLayout(tarjeta)
        layout_tabla.setContentsMargins(10, 10, 10, 10)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(
            ["Usuario", "Tipo de usuario", "Fecha de entrada", "Fecha de salida"]
        )
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setStyleSheet(
            "QTableWidget { background: white; alternate-background-color: #EDF3FD; "
            "color: #1E2A3A; border: none; selection-background-color: #D9F7FF; }"
            "QHeaderView::section { background: #1E508E; color: white; "
            "font-weight: bold; padding: 9px; border: none; }"
        )
        layout_tabla.addWidget(self.tabla)
        raiz.addWidget(tarjeta, 1)

    def actualizar(self):
        if not es_administrador(self.usuario):
            self.boton_actualizar.setEnabled(False)
            self.tabla.setRowCount(0)
            self.mostrar_advertencia(
                "Acceso restringido",
                "La bitácora de accesos solo está disponible para admin.",
            )
            return

        registros, problema = listar_entradas_secretarias(self.usuario)
        if problema:
            self.tabla.setRowCount(0)
            self.mostrar_advertencia("Bitácora de accesos", problema)
            return

        self.tabla.setRowCount(len(registros))
        for fila, registro in enumerate(registros):
            fecha_entrada = registro["fecha_entrada"]
            fecha_entrada_texto = fecha_entrada.strftime("%d/%m/%Y %H:%M:%S")
            fecha_salida = registro["fecha_salida"]
            fecha_salida_texto = (
                fecha_salida.strftime("%d/%m/%Y %H:%M:%S")
                if fecha_salida
                else "Sesión activa"
            )
            tipo = (
                "Secretaría"
                if registro["tipo_usuario"] == "administrativo"
                else "Docente"
            )
            for columna, texto in enumerate(
                (
                    registro["usuario"],
                    tipo,
                    fecha_entrada_texto,
                    fecha_salida_texto,
                )
            ):
                elemento = QTableWidgetItem(texto)
                elemento.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.tabla.setItem(fila, columna, elemento)
        self.tabla.resizeRowsToContents()

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)
