from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from Logica import horarios as lh
from Logica import validaciones as v
from ventanas.ventana import Config, VentanaBase

DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes")
PASTELES = (
    "#DCEBFA",
    "#E3F4E1",
    "#FCEFD2",
    "#F6DDE8",
    "#E6E0F5",
    "#D9F0F0",
    "#FBE3D6",
    "#EDEDED",
)


class VentanaConsultaHorarios(VentanaBase):
    def __init__(self, menu=None):
        super().__init__("SIGEA - Consulta de horarios", 1080, 700)
        self.menu = menu
        self._navegando = False
        self._armar_interfaz()
        self._cargar_periodos()
        self.centrar_ventana()

    def _armar_interfaz(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(16)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self.crear_label_titulo("CONSULTA DE HORARIOS", 30))
        cabecera.addStretch()
        cabecera.addWidget(
            self.crear_boton_salida("Menú", self.close, ancho=120, alto=40)
        )
        raiz.addLayout(cabecera)

        filtros = QFrame()
        filtros.setObjectName("filtrosHorario")
        filtros.setStyleSheet(
            "#filtrosHorario { background-color: white; border-radius: 14px; }"
        )
        fila_filtros = QHBoxLayout(filtros)
        fila_filtros.setContentsMargins(18, 14, 18, 14)
        fila_filtros.setSpacing(12)
        self.periodo = self._agregar_selector(fila_filtros, "PERIODO")
        self.semestre = self._agregar_selector(fila_filtros, "SEMESTRE")
        self.turno = self._agregar_selector(fila_filtros, "TURNO")
        self.grupo = self._agregar_selector(fila_filtros, "GRUPO")
        self.consultar_boton = self.crear_boton(
            "Consultar", self.consultar, ancho=150, alto=44
        )
        fila_filtros.addWidget(self.consultar_boton, 0, Qt.AlignBottom)
        raiz.addWidget(filtros)

        self.periodo.currentIndexChanged.connect(self._actualizar_grupos)
        self.semestre.currentIndexChanged.connect(self._actualizar_grupos)
        self.turno.currentIndexChanged.connect(self._actualizar_grupos)

        self.resumen = QLabel("Selecciona periodo, semestre, turno y grupo.")
        self.resumen.setWordWrap(True)
        self.resumen.setStyleSheet(
            "color: white; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 2px;"
        )
        raiz.addWidget(self.resumen)

        self.tabla = QTableWidget(0, len(DAYS) + 1)
        self.tabla.setHorizontalHeaderLabels(
            ["Materia"] + [dia.capitalize() for dia in DAYS]
        )
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setWordWrap(True)
        self.tabla.setShowGrid(False)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        for columna in range(2, len(DAYS) + 1):
            self.tabla.horizontalHeader().setSectionResizeMode(
                columna, QHeaderView.Stretch
            )
        self.tabla.setStyleSheet(
            "QTableWidget { background: white; color: #1E2A3A; border: none; "
            "border-radius: 12px; selection-background-color: #B9DDF7; "
            "gridline-color: #9FB3CF; }"
            "QHeaderView::section { background: #1E508E; color: white; "
            "font-weight: bold; padding: 10px 8px; border: 1px solid #DCE7F5; }"
        )
        self.tabla.setAlternatingRowColors(False)
        raiz.addWidget(self.tabla, 1)

    def _agregar_selector(self, fila, titulo):
        caja = QVBoxLayout()
        caja.setSpacing(5)
        etiqueta = QLabel(titulo)
        etiqueta.setStyleSheet(
            f"color: {Config.TEXTO_SUBTITULO}; font-size: 10px; "
            "font-weight: bold; background: transparent;"
        )
        selector = QComboBox()
        selector.setMinimumWidth(145)
        selector.setFixedHeight(40)
        selector.setCursor(Qt.PointingHandCursor)
        selector.setStyleSheet(
            "QComboBox { background: #F2F4F7; color: #1E2A3A; "
            "border: 1px solid #C9D8EE; border-radius: 8px; padding: 5px 9px; }"
            "QComboBox QAbstractItemView { background: white; color: #1E2A3A; }"
        )
        caja.addWidget(etiqueta)
        caja.addWidget(selector)
        fila.addLayout(caja, 1)
        return selector

    def _cargar_periodos(self):
        periodos = lh.listar_periodos()
        self.periodo.addItems(periodos)
        self.semestre.addItems(v.SEMESTRES)
        self.turno.addItem("Matutino", "matutino")
        self.turno.addItem("Vespertino", "vespertino")
        if not periodos:
            self.resumen.setText(
                "No hay periodos escolares disponibles. Verifica la conexión "
                "y los periodos registrados."
            )
        self._actualizar_grupos()

    def _actualizar_grupos(self, *_):
        periodo = self.periodo.currentText()
        semestre = self.semestre.currentText()
        turno = self.turno.currentData()
        grupos = (
            lh.grupos_disponibles(periodo, semestre)
            if periodo and semestre
            else []
        )
        grupos = [
            grupo for grupo in grupos
            if not grupo["turno"] or grupo["turno"].lower() == turno
        ]

        self.grupo.blockSignals(True)
        self.grupo.clear()
        self.grupo.addItem("Selecciona un grupo", None)
        for grupo in grupos:
            self.grupo.addItem(
                f"{grupo['clave']} · {grupo['materias']} materias",
                grupo["clave"],
            )
        self.grupo.blockSignals(False)

        self.tabla.setRowCount(0)
        if periodo and semestre and not grupos:
            self.resumen.setText(
                f"No hay grupos disponibles para el semestre {semestre}, "
                f"turno {self.turno.currentText()} y periodo {periodo}."
            )
        elif grupos:
            self.resumen.setText("Selecciona un grupo para consultar su horario.")

    def consultar(self):
        periodo = self.periodo.currentText()
        semestre = self.semestre.currentText()
        turno = self.turno.currentData()
        clave = self.grupo.currentData()
        if not all((periodo, semestre, turno, clave)):
            self.mostrar_advertencia(
                "Consulta de horarios",
                "Selecciona un periodo, semestre, turno y grupo.",
            )
            return

        horario = lh.obtener_horario(periodo, semestre, turno, clave)
        if horario is None:
            self.tabla.setRowCount(0)
            self.resumen.setText(
                f"No se encontró un horario para el grupo {clave} "
                f"en el periodo {periodo}."
            )
            return

        materias = horario["materias"]
        self.tabla.setRowCount(len(materias))
        total_clases = 0
        for numero_fila, materia in enumerate(materias):
            color = QColor(PASTELES[numero_fila % len(PASTELES)])
            nombre = QTableWidgetItem(
                f"{materia['clave']} · {materia['nombre']}\n"
                f"Docente: {materia['docente'] or 'Sin docente'}"
            )
            nombre.setBackground(color)
            nombre.setToolTip(materia["nombre"])
            self.tabla.setItem(numero_fila, 0, nombre)

            bloques_por_dia = {dia: [] for dia in DAYS}
            for dia, inicio, fin in materia["bloques"]:
                if dia not in bloques_por_dia:
                    continue
                bloques_por_dia[dia].append(
                    f"{lh.formato_hora(inicio)} - {lh.formato_hora(fin)}"
                )
                total_clases += 1

            for columna, dia in enumerate(DAYS, start=1):
                bloques = bloques_por_dia[dia]
                texto = "\n".join(bloques)
                if bloques and materia["aula"]:
                    texto += f"\nAula {materia['aula']}"
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignCenter)
                if bloques:
                    celda.setBackground(color)
                    celda.setForeground(QColor("#1E2A3A"))
                self.tabla.setItem(numero_fila, columna, celda)

        self.tabla.resizeRowsToContents()
        for numero_fila in range(self.tabla.rowCount()):
            self.tabla.setRowHeight(
                numero_fila, max(68, self.tabla.rowHeight(numero_fila))
            )

        self.resumen.setText(
            f"Grupo {horario['clave']} · {horario['turno'].capitalize()} · "
            f"Semestre {horario['semestre']} · {horario['periodo']} · "
            f"{total_clases} clase(s) programada(s)"
            if total_clases
            else f"El grupo {horario['clave']} no tiene clases programadas."
        )

    def closeEvent(self, evento):
        if self.menu is not None and not self._navegando:
            self.menu.show()
        super().closeEvent(evento)
