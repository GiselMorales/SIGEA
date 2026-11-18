from datetime import datetime
from io import BytesIO
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, QSize, QEventLoop, QTimer
from PySide6.QtGui import QColor, QPageLayout, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from Logica.estadisticas import (
    consultar_estadisticas,
    listar_grupos,
    listar_periodos,
)
from reportes.generador_pdf import generar_pdf_estadisticas
from ventanas.componentes import (
    DESTINOS_REPORTES,
    ORDEN_BARRA_REPORTES,
    destinos_barra,
    navegar_a,
    opciones_barra,
)
from ventanas.ventana import Config, VentanaBase
from ventanas.estadisticas_graficas import (
    crear_figura_alumnos,
    crear_figura_genero,
    crear_figura_semestre,
    crear_figura_turno,
)

CARPETA_SALIDA = (
    Path(__file__).resolve().parent.parent / "reportes_generados"
)
ORDEN_BARRA_ESTADISTICAS = ("Estadísticas",) + ORDEN_BARRA_REPORTES
DESTINOS_BARRA_ESTADISTICAS = destinos_barra(
    ORDEN_BARRA_ESTADISTICAS,
    DESTINOS_REPORTES,
)


class _IconoIndicador(QWidget):
    def __init__(self, tipo, color, parent=None):
        super().__init__(parent)
        self.tipo = tipo
        self.color = QColor(color)
        self.setFixedSize(44, 44)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setClipRegion(evento.region())
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(self.color)
        pintor.drawEllipse(self.rect())
        pintor.setBrush(QColor("white"))

        if self.tipo == "grupos":
            for x, y in ((12, 12), (24, 12), (12, 24), (24, 24)):
                pintor.drawRoundedRect(x, y, 8, 8, 2, 2)
        elif self.tipo == "personas":
            pintor.drawEllipse(17, 7, 10, 10)
            pintor.drawEllipse(7, 12, 8, 8)
            pintor.drawEllipse(29, 12, 8, 8)
            pintor.drawRoundedRect(14, 20, 16, 15, 7, 7)
            pintor.drawRoundedRect(4, 23, 12, 12, 5, 5)
            pintor.drawRoundedRect(28, 23, 12, 12, 5, 5)
        else:
            pintor.drawEllipse(17, 8, 10, 10)
            pintor.drawRoundedRect(13, 21, 18, 15, 8, 8)


class VentanaEstadisticas(VentanaBase):
    def __init__(self, menu=None):
        super().__init__("SIGEA - Estadísticas escolares", 1200, 900)
        self.setObjectName("ventanaEstadisticas")
        self.setStyleSheet(
            "QWidget { font-family: 'Sans Serif'; }"
            "QWidget#ventanaEstadisticas { "
            f"background-color: {Config.FONDO_VENTANA}; "
            f"color: {Config.TEXTO_TITULO}; }}"
        )
        self.menu = menu
        self._navegando = False
        self._datos = None
        self._periodos = {}
        self._filtros_consulta = None
        self._crear_interfaz()
        self._cargar_periodos()
        self.periodo.currentIndexChanged.connect(self._periodo_cambiado)
        self.grupo.currentIndexChanged.connect(self._filtros_cambiaron)
        self.centrar_ventana()

    def _crear_interfaz(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 14, 16, 14)
        raiz.setSpacing(8)

        encabezado = QHBoxLayout()
        titulos = QVBoxLayout()
        titulo = QLabel("Estadísticas escolares")
        titulo.setStyleSheet(
            f"color: {Config.TEXTO_TITULO}; font-size: 24px; font-weight: 700; "
            "background: transparent;"
        )
        descripcion = QLabel(
            "Consulta de la distribución de alumnos inscritos por grupo y género."
        )
        descripcion.setStyleSheet(
            "color: rgba(255,255,255,210); font-size: 11px; "
            "background: transparent;"
        )
        titulos.addWidget(titulo)
        titulos.addWidget(descripcion)
        encabezado.addLayout(titulos)
        encabezado.addStretch()
        raiz.addLayout(encabezado)

        self.area_contenido = QScrollArea()
        self.area_contenido.setWidgetResizable(True)
        self.area_contenido.setFrameShape(QFrame.NoFrame)
        self.area_contenido.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area_contenido.setStyleSheet(
            "QScrollArea { background: transparent; border: 0; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        contenido = QWidget()
        contenido.setStyleSheet("background: transparent;")
        paneles = QVBoxLayout(contenido)
        paneles.setContentsMargins(0, 6, 0, 4)
        paneles.setSpacing(10)

        filtros = self._crear_panel()
        filtros_layout = QHBoxLayout(filtros)
        filtros_layout.setContentsMargins(10, 10, 10, 10)
        filtros_layout.setSpacing(10)
        self.periodo = QComboBox()
        self.grupo = QComboBox()
        for combo in (self.periodo, self.grupo):
            combo.setMinimumHeight(36)
            combo.setMinimumContentsLength(18)
            combo.setSizeAdjustPolicy(
                QComboBox.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            combo.setStyleSheet(
                "QComboBox { background: white; color: #24364B; "
                "border: 1px solid #D4E1EF; border-radius: 7px; "
                "padding: 5px 9px; font-size: 11px; }"
                "QComboBox::drop-down { border: 0; width: 22px; }"
            )
        self.periodo.addItem("Selecciona un periodo escolar", None)
        self.grupo.addItem("Selecciona primero un periodo", None)
        self.grupo.setEnabled(False)
        filtros_layout.addWidget(
            self._crear_campo_filtro("Periodo escolar", self.periodo), 3
        )
        filtros_layout.addWidget(
            self._crear_campo_filtro("Grupo", self.grupo), 2
        )
        self.boton_generar = self._crear_boton_tablero(
            "Actualizar", self.generar_estadisticas, 125, primario=True
        )
        self.boton_pdf = self._crear_boton_tablero(
            "Generar PDF", self.exportar_pdf, 130, 38
        )
        self.boton_imprimir = self._crear_boton_tablero(
            "Imprimir", self.imprimir, 105, 38
        )
        self.boton_pdf.setEnabled(False)
        self.boton_imprimir.setEnabled(False)
        filtros_layout.addWidget(self.boton_generar, 0, Qt.AlignBottom)
        filtros_layout.addWidget(self.boton_pdf, 0, Qt.AlignBottom)
        filtros_layout.addWidget(self.boton_imprimir, 0, Qt.AlignBottom)
        paneles.addWidget(filtros)

        indicadores = QHBoxLayout()
        indicadores.setSpacing(10)
        self._indicadores = {}
        for clave, texto, icono, color, fondo in (
            ("alumnos", "Total de alumnos", "personas", "#2563A6", "#EAF3FF"),
            ("hombres", "Hombres", "persona", "#4288E4", "#EDF5FF"),
            ("mujeres", "Mujeres", "persona", "#D65383", "#FFF0F5"),
            ("grupos", "Total de grupos", "grupos", "#38A878", "#ECF8F2"),
        ):
            tarjeta = QFrame()
            tarjeta.setMinimumHeight(78)
            tarjeta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tarjeta.setStyleSheet(
                f"QFrame {{ background-color: {fondo}; border: 1px solid "
                f"{color}30; border-radius: 10px; }}"
            )
            tarjeta_layout = QHBoxLayout(tarjeta)
            tarjeta_layout.setContentsMargins(8, 8, 8, 8)
            tarjeta_layout.setSpacing(6)
            insignia = _IconoIndicador(icono, color)
            texto_layout = QVBoxLayout()
            texto_layout.setSpacing(1)
            etiqueta = QLabel(texto)
            etiqueta.setStyleSheet(
                "color: #35516F; font-size: 10px; font-weight: 600; "
                "background: transparent;"
            )
            numero = QLabel("0")
            numero.setStyleSheet(
                f"color: {color}; font-size: 23px; font-weight: 700; "
                "background: transparent;"
            )
            detalle = QLabel("")
            detalle.setStyleSheet(
                "color: #64748B; font-size: 9px; background: transparent;"
            )
            texto_layout.addWidget(etiqueta)
            texto_layout.addWidget(numero)
            texto_layout.addWidget(detalle)
            tarjeta_layout.addWidget(insignia)
            tarjeta_layout.addLayout(texto_layout, 1)
            self._indicadores[clave] = {
                "valor": numero,
                "detalle": detalle,
            }
            indicadores.addWidget(tarjeta)
        paneles.addLayout(indicadores)

        self.mensaje_estado = QLabel(
            "Selecciona los filtros y pulsa Actualizar para consultar los datos."
        )
        self.mensaje_estado.setWordWrap(True)
        self.mensaje_estado.setStyleSheet(
            "color: rgba(255,255,255,220); font-size: 10px; "
            "background: transparent; "
            "padding: 0 3px;"
        )
        paneles.addWidget(self.mensaje_estado)

        self.figura_alumnos = crear_figura_alumnos({"grupos": []})
        self.canvas_alumnos = FigureCanvasQTAgg(self.figura_alumnos)
        self.figura_genero = crear_figura_genero({"grupos": []})
        self.canvas_genero = FigureCanvasQTAgg(self.figura_genero)
        self.figura_semestre = crear_figura_semestre({"por_semestre": []})
        self.canvas_semestre = FigureCanvasQTAgg(self.figura_semestre)
        self.figura_turno = crear_figura_turno({"por_turno": []})
        self.canvas_turno = FigureCanvasQTAgg(self.figura_turno)
        self._configurar_canvas(
            self.canvas_alumnos,
            self.canvas_genero,
            self.canvas_semestre,
            self.canvas_turno,
        )
        graficas = QGridLayout()
        graficas.setHorizontalSpacing(10)
        graficas.setVerticalSpacing(10)
        graficas.addWidget(
            self._crear_panel_grafica("Alumnos por grupo", self.canvas_alumnos),
            0, 0,
        )
        graficas.addWidget(
            self._crear_panel_grafica("Distribución por sexo", self.canvas_genero),
            0, 1,
        )
        graficas.addWidget(
            self._crear_panel_grafica("Matrícula por semestre", self.canvas_semestre),
            1, 0,
        )
        graficas.addWidget(
            self._crear_panel_grafica("Distribución por turno", self.canvas_turno),
            1, 1,
        )
        graficas.setColumnStretch(0, 1)
        graficas.setColumnStretch(1, 1)
        paneles.addLayout(graficas)

        tabla_panel = self._crear_panel()
        tabla_layout = QVBoxLayout(tabla_panel)
        tabla_layout.setContentsMargins(12, 10, 12, 12)
        tabla_layout.setSpacing(7)
        titulo_tabla = QLabel("Detalle por grupo")
        titulo_tabla.setStyleSheet(
            "color: #174A7E; font-size: 12px; font-weight: 700; "
            "background: transparent;"
        )
        tabla_layout.addWidget(titulo_tabla)
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(
            ["Grupo", "Materias", "Alumnos", "Hombres", "Mujeres"]
        )
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setWordWrap(True)
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.tabla.horizontalHeader().setStretchLastSection(False)
        for columna, ancho in ((0, 100), (2, 80), (3, 80), (4, 80)):
            self.tabla.setColumnWidth(columna, ancho)
        self.tabla.setMinimumHeight(150)
        self.tabla.setStyleSheet(
            "QTableWidget { background: white; color: #1E2A3A; "
            "border: 1px solid #E1E9F2; border-radius: 8px; "
            "gridline-color: #D7E0EA; alternate-background-color: #F5F8FC; }"
            "QHeaderView::section { background: #EEF4FB; color: #35516F; "
            "padding: 6px; border: 0; font-weight: 600; }"
        )
        tabla_layout.addWidget(self.tabla)
        paneles.addWidget(tabla_panel)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        self._barra = self.crear_barra_vertical(
            opciones_barra(
                self.volver,
                orden=ORDEN_BARRA_ESTADISTICAS,
            )
        )
        self._barra.seleccionado.connect(self._navegar)
        cuerpo.addWidget(self._barra, 0, Qt.AlignTop)
        self.area_contenido.setWidget(contenido)
        cuerpo.addWidget(self.area_contenido, 1)
        raiz.addLayout(cuerpo, 1)
        self._barra.seleccionar(1)

    def _crear_panel(self):
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background: white; border: 1px solid #DCE7F2; "
            "border-radius: 10px; }"
        )
        return panel

    def _crear_boton_tablero(self, texto, funcion, ancho, alto=38, primario=False):
        boton = QPushButton(texto)
        boton.setFixedSize(ancho, alto)
        boton.setCursor(Qt.PointingHandCursor)
        if primario:
            boton.setStyleSheet(
                "QPushButton { background: #2D80D3; color: white; "
                "border: 1px solid #2D80D3; border-radius: 7px; "
                "font-size: 10px; font-weight: 600; padding: 5px 9px; }"
                "QPushButton:hover { background: #246EB8; }"
                "QPushButton:disabled { background: #B5C9DD; "
                "border-color: #B5C9DD; }"
            )
        else:
            boton.setStyleSheet(
                "QPushButton { background: white; color: #31516F; "
                "border: 1px solid #C9D8E9; border-radius: 7px; "
                "font-size: 10px; font-weight: 600; padding: 5px 8px; }"
                "QPushButton:hover { background: #F0F6FC; }"
                "QPushButton:disabled { color: #A7B4C2; "
                "border-color: #DFE7F0; }"
            )
        boton.clicked.connect(funcion)
        return boton

    def _crear_campo_filtro(self, texto, control):
        campo = QWidget()
        campo.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(campo)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        etiqueta = QLabel(texto + ":")
        etiqueta.setStyleSheet(
            "color: #35516F; font-size: 9px; font-weight: 600; "
            "background: transparent;"
        )
        layout.addWidget(etiqueta)
        layout.addWidget(control)
        return campo

    def _crear_panel_grafica(self, titulo, canvas):
        panel = self._crear_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(3)
        encabezado = QLabel(titulo)
        encabezado.setStyleSheet(
            "color: #174A7E; font-size: 11px; font-weight: 700; "
            "background: transparent; padding-left: 2px;"
        )
        layout.addWidget(encabezado)
        layout.addWidget(canvas, 1)
        return panel

    def _configurar_canvas(self, *canvases):
        for canvas in canvases:
            canvas.setMinimumWidth(0)
            canvas.setMinimumHeight(190)
            canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    def _cargar_periodos(self):
        periodos, problema = listar_periodos()
        if problema:
            self.mensaje_estado.setText(problema)
            QMessageBox.warning(self, "Error de conexión", problema)
            return
        for periodo in periodos:
            self.periodo.addItem(periodo["nombre"], periodo["periodo_id"])
            self._periodos[periodo["periodo_id"]] = periodo["nombre"]
        if not periodos:
            self.mensaje_estado.setText(
                "No hay periodos escolares registrados para consultar."
            )

    def _cargar_grupos(self):
        periodo_id = self.periodo.currentData()
        self.grupo.blockSignals(True)
        self.grupo.clear()
        if periodo_id is None:
            self.grupo.addItem("Selecciona primero un periodo", None)
            self.grupo.setEnabled(False)
            self.grupo.blockSignals(False)
            return

        grupos, problema = listar_grupos(periodo_id)
        if problema:
            self.grupo.addItem("No se pudieron cargar los grupos", None)
            self.grupo.setEnabled(False)
        else:
            self.grupo.addItem("Todos los grupos", None)
            for grupo in grupos:
                self.grupo.addItem(grupo, grupo)
            self.grupo.setEnabled(True)
        self.grupo.blockSignals(False)
        if problema:
            QMessageBox.warning(self, "Error de consulta", problema)

    def _periodo_cambiado(self, *_):
        self._cargar_grupos()
        if self._datos is not None:
            self._limpiar_datos(
                "El periodo cambió. Genera nuevamente las estadísticas."
            )

    def generar_estadisticas(self):
        periodo_id = self.periodo.currentData()
        if periodo_id is None:
            QMessageBox.information(
                self, "Filtro requerido", "Selecciona un periodo escolar."
            )
            self.periodo.setFocus()
            return

        datos, problema = consultar_estadisticas(
            periodo_id,
            self.grupo.currentData(),
        )
        if problema:
            self._limpiar_datos(problema)
            QMessageBox.warning(self, "Error de consulta", problema)
            return

        self._datos = datos
        self._filtros_consulta = self._filtros_seleccionados()
        self._mostrar_datos(datos)
        self._actualizar_acciones()
        if not datos["grupos"]:
            QMessageBox.information(
                self, "Sin grupos",
                "No hay grupos para el periodo seleccionado.",
            )
        elif not datos["total_alumnos"]:
            QMessageBox.information(
                self, "Sin alumnos inscritos",
                "No hay alumnos inscritos en los grupos seleccionados.",
            )

    def _filtros_cambiaron(self, *_):
        if self._datos is not None:
            self._limpiar_datos(
                "Los filtros cambiaron. Genera nuevamente las estadísticas."
            )

    def _navegar(self, indice, texto):
        if indice in (0, 1):
            return
        destino = DESTINOS_BARRA_ESTADISTICAS.get(indice)
        if destino:
            navegar_a(self, destino)
        else:
            self.mostrar_mensaje(
                texto,
                "Esta opción aún está en construcción.",
            )
            self._barra.seleccionar(1)

    def volver(self):
        self.close()

    def _limpiar_datos(self, mensaje):
        self._datos = None
        self._filtros_consulta = None
        for indicador in self._indicadores.values():
            indicador["valor"].setText("0")
            indicador["detalle"].clear()
        self.tabla.setRowCount(0)
        self._actualizar_graficas(
            {
                "grupos": [],
                "por_semestre": [],
                "por_turno": [],
                "total_alumnos": 0,
                "hombres": 0,
                "mujeres": 0,
            }
        )
        self.mensaje_estado.setText(mensaje)
        self._actualizar_acciones()

    def _mostrar_datos(self, datos):
        total = datos["total_alumnos"]
        for clave, valor in (
            ("alumnos", total),
            ("grupos", datos["total_grupos"]),
            ("hombres", datos["hombres"]),
            ("mujeres", datos["mujeres"]),
        ):
            self._indicadores[clave]["valor"].setText(str(valor))
            self._indicadores[clave]["detalle"].clear()
        for clave in ("hombres", "mujeres"):
            cantidad = datos[clave]
            porcentaje = cantidad / total * 100 if total else 0
            self._indicadores[clave]["detalle"].setText(
                f"{porcentaje:.2f}% del total"
            )
        self.mensaje_estado.setText(
            f"Periodo: {self._periodos.get(self.periodo.currentData(), '')}  •  "
            f"Grupo: {self.grupo.currentText()}"
        )

        self._actualizar_graficas(datos)

        self.tabla.setRowCount(len(datos["grupos"]))
        for fila, grupo in enumerate(datos["grupos"]):
            valores = (
                grupo["clave_grupo"],
                grupo["materias"],
                grupo["alumnos"],
                grupo["hombres"],
                grupo["mujeres"],
            )
            for columna, valor in enumerate(valores):
                elemento = QTableWidgetItem(str(valor))
                if columna >= 2:
                    elemento.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(fila, columna, elemento)
        self.tabla.resizeRowsToContents()

    def _actualizar_graficas(self, datos):
        figuras = (
            ("figura_alumnos", self.canvas_alumnos, crear_figura_alumnos(datos)),
            ("figura_genero", self.canvas_genero, crear_figura_genero(datos)),
            ("figura_semestre", self.canvas_semestre, crear_figura_semestre(datos)),
            ("figura_turno", self.canvas_turno, crear_figura_turno(datos)),
        )
        for atributo, canvas, figura in figuras:
            setattr(self, atributo, figura)
            canvas.figure = figura
            canvas.draw()

    def _actualizar_acciones(self):
        habilitado = bool(
            self._datos
            and self._datos["grupos"]
            and self._datos["total_alumnos"] > 0
        )
        self.boton_pdf.setEnabled(habilitado)
        self.boton_imprimir.setEnabled(habilitado)

    def _filtros_pdf(self):
        if self._filtros_consulta is not None:
            return self._filtros_consulta
        return self._filtros_seleccionados()

    def _filtros_seleccionados(self):
        return {
            "periodo": self._periodos.get(self.periodo.currentData(), ""),
            "grupo": self.grupo.currentText(),
        }

    def _bytes_graficas(self):
        imagenes = []
        for figura in (
            self.figura_alumnos,
            self.figura_genero,
            self.figura_semestre,
            self.figura_turno,
        ):
            salida = BytesIO()
            figura.savefig(salida, format="png", dpi=180, bbox_inches="tight")
            imagenes.append(salida.getvalue())
        return imagenes

    def _generar_pdf(self, ruta):
        if not self._actualizar_acciones_disponibles():
            return False
        (
            grafica_alumnos,
            grafica_genero,
            grafica_semestre,
            grafica_turno,
        ) = self._bytes_graficas()
        generar_pdf_estadisticas(
            self._datos,
            self._filtros_pdf(),
            grafica_alumnos,
            grafica_genero,
            grafica_semestre,
            grafica_turno,
            str(ruta),
        )
        return True

    def _actualizar_acciones_disponibles(self):
        if not self._datos or not self._datos["grupos"]:
            QMessageBox.information(
                self, "Sin datos", "Primero genera estadísticas con grupos."
            )
            return False
        if not self._datos["total_alumnos"]:
            QMessageBox.information(
                self, "Sin datos", "No hay alumnos inscritos para reportar."
            )
            return False
        return True

    def exportar_pdf(self):
        if not self._actualizar_acciones_disponibles():
            return
        try:
            CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"No se pudo crear la carpeta de reportes: {error}")
            QMessageBox.warning(
                self, "Error", "No se pudo preparar la carpeta para el reporte."
            )
            return
        sugerido = CARPETA_SALIDA / (
            f"reporte_estadistico_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        )
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte estadístico", str(sugerido), "Documento PDF (*.pdf)"
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        try:
            self._generar_pdf(ruta)
            QMessageBox.information(
                self, "Reporte generado", f"El PDF se guardó correctamente en:\n{ruta}"
            )
        except Exception as error:
            print(f"Error al generar reporte estadístico: {error}")
            QMessageBox.warning(
                self, "Error", "No fue posible generar el reporte estadístico."
            )

    def imprimir(self):
        if not self._actualizar_acciones_disponibles():
            return
        try:
            CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"No se pudo crear la carpeta de reportes: {error}")
            QMessageBox.warning(
                self, "Error", "No se pudo preparar el archivo para impresión."
            )
            return
        ruta = CARPETA_SALIDA / (
            f"reporte_estadistico_impresion_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        )
        try:
            self._generar_pdf(ruta)
            self._imprimir_pdf(ruta)
        except Exception as error:
            print(f"Error al preparar impresión de estadísticas: {error}")
            QMessageBox.warning(
                self, "Error", "No fue posible preparar el reporte para impresión."
            )

    def _imprimir_pdf(self, ruta):
        impresora = QPrinter(QPrinter.HighResolution)
        impresora.setPageOrientation(QPageLayout.Orientation.Portrait)
        dialogo = QPrintDialog(impresora, self)
        if dialogo.exec() != QPrintDialog.Accepted:
            return

        documento = QPdfDocument(self)
        error_carga = documento.load(str(ruta))
        if error_carga != QPdfDocument.Error.None_:
            documento.close()
            QMessageBox.warning(
                self, "Error de impresión",
                f"No se pudo leer el PDF generado ({error_carga}).",
            )
            return
        try:
            if documento.status() == QPdfDocument.Status.Loading:
                espera = QEventLoop(self)
                temporizador = QTimer(self)
                temporizador.setSingleShot(True)

                def carga_finalizada(estado):
                    if estado != QPdfDocument.Status.Loading:
                        espera.quit()

                documento.statusChanged.connect(carga_finalizada)
                temporizador.timeout.connect(espera.quit)
                temporizador.start(10000)
                if documento.status() == QPdfDocument.Status.Loading:
                    espera.exec()
                temporizador.stop()
                documento.statusChanged.disconnect(carga_finalizada)

            if (
                documento.status() != QPdfDocument.Status.Ready
                or documento.pageCount() == 0
            ):
                QMessageBox.warning(
                    self, "Error de impresión",
                    "No se pudo cargar el PDF para impresión.",
                )
                return

            self._enviar_pdf_a_impresora(documento, impresora)
        finally:
            documento.close()
        QMessageBox.information(
            self, "Impresión", "El reporte se envió a la impresora seleccionada."
        )

    def _enviar_pdf_a_impresora(self, documento, impresora):
        area = impresora.pageRect(QPrinter.Unit.DevicePixel)
        tamano = QSize(max(1, int(area.width())), max(1, int(area.height())))
        pintor = QPainter()
        if not pintor.begin(impresora):
            raise RuntimeError("No se pudo iniciar la impresora seleccionada.")
        try:
            for pagina in range(documento.pageCount()):
                if pagina and not impresora.newPage():
                    raise RuntimeError("No se pudo avanzar a la siguiente página.")
                imagen = documento.render(pagina, tamano)
                if imagen.isNull():
                    raise RuntimeError(
                        f"No se pudo renderizar la página {pagina + 1}."
                    )
                pintor.drawImage(area, imagen)
        finally:
            pintor.end()

    def closeEvent(self, evento):
        if self.menu is not None and not self._navegando:
            self.menu.show()
        super().closeEvent(evento)
