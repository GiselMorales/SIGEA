from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QScrollArea, QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt

from ventanas.ventana import VentanaBase, Config, CampoFlotante
from ventanas.componentes import opciones_barra, destinos_barra, navegar_a


class VentanaConsulta(VentanaBase):
    """Base de las ventanas de consulta.
    Cada módulo define OPCIONES_FILTRO y los métodos consultar() y generar_pdf()."""

    OPCIONES_FILTRO = ["Todos"]
    ANCHO_CONTENIDO = 806
    TEXTO_BOTON = "Consultar"
    MAX_TARJETAS = 200            # máximo de resultados dibujados en pantalla

    def __init__(self, titulo_ventana, titulo, menu=None, ancho=1080, alto=660):
        super().__init__(titulo_ventana, ancho, alto)
        self.menu = menu
        self._navegando = False
        self._total_resultados = 0
        self._armar(titulo)
        self.centrar_ventana()

    # --- a redefinir en cada módulo -----------------------------------
    def consultar(self):
        raise NotImplementedError

    def generar_pdf(self):
        raise NotImplementedError

    # ------------------------------------------------------------------
    def _armar(self, titulo):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(16)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self.crear_label_titulo(titulo, 30))
        cabecera.addStretch()
        cabecera.addWidget(self.crear_boton_salida("Menú", self.volver, ancho=120, alto=40))
        raiz.addLayout(cabecera)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(18)
        self._barra = self.crear_barra_vertical(
            opciones_barra(self.volver, orden=("Consultar", "Alta", "Baja", "Modificar"))
        )
        self._barra.seleccionado.connect(self._navegar)
        cuerpo.addWidget(self._barra, 0, Qt.AlignTop)

        derecha = QVBoxLayout()
        derecha.setSpacing(14)
        derecha.addLayout(self._fila_totales())
        derecha.addLayout(self._fila_resultados())
        derecha.addWidget(self._zona_resultados(), 1)
        derecha.addWidget(self._barra_consulta())
        cuerpo.addLayout(derecha, 1)

        raiz.addLayout(cuerpo, 1)
        self._barra.seleccionar(1)
        self.mostrar_vacio("Elige cómo consultar, escribe el valor y presiona «Consultar».")

    def _navegar(self, indice, texto):
        if indice == 1:                       # «Consultar»: ya estamos aquí
            return
        destino = destinos_barra(("Consultar", "Alta", "Baja", "Modificar")).get(indice)
        if destino:
            navegar_a(self, destino)
        else:
            self.mostrar_mensaje(texto, "Esta opción aún está en construcción.")
            self._barra.seleccionar(1)

    def _fila_totales(self):
        fila = QHBoxLayout()
        fila.setSpacing(14)
        self._numeros = {}
        for clave, texto, color in (
            ("total", "Total", Config.AZUL_ENTRAR),
            ("mujeres", "Mujeres", "#C2185B"),
            ("hombres", "Hombres", Config.AZUL_BOTON),
            ("carreras", "Carreras", "#2E7D32"),
        ):
            tarjeta = self.crear_tarjeta(190, 84, 18)
            lay = QVBoxLayout(tarjeta)
            lay.setContentsMargins(18, 10, 18, 10)
            lay.setSpacing(0)
            numero = self.crear_label_titulo("0", 30, color)
            lay.addWidget(numero)
            lay.addWidget(self.crear_label_campo(texto.upper(), color="rgba(128, 128, 128, 200)"))
            self._numeros[clave] = numero
            fila.addWidget(tarjeta)
        fila.addStretch()
        return fila

    # --- resultados en pantalla ---------------------------------------
    def _fila_resultados(self):
        """Texto con el número de resultados + botón para generar el PDF."""
        fila = QHBoxLayout()
        self.etiqueta_info = self.crear_label_campo("", color="rgba(255, 255, 255, 200)")
        self.etiqueta_info.setWordWrap(True)
        fila.addWidget(self.etiqueta_info, 1)
        self.boton_pdf = self.crear_boton_secundario(
            "Generar PDF", self._pedir_pdf, ancho=170, alto=46
        )
        fila.addWidget(self.boton_pdf, 0, Qt.AlignRight)
        return fila

    def _zona_resultados(self):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,90); border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,150); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        contenido = QFrame()
        contenido.setStyleSheet("background: transparent;")
        self._lista = QVBoxLayout(contenido)
        self._lista.setContentsMargins(0, 0, 8, 0)
        self._lista.setSpacing(10)
        self._scroll.setWidget(contenido)
        return self._scroll

    def limpiar_resultados(self):
        while self._lista.count():
            item = self._lista.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def mostrar_vacio(self, texto):
        self.limpiar_resultados()
        etiqueta = QLabel(texto)
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setWordWrap(True)
        etiqueta.setStyleSheet(
            "color: rgba(255, 255, 255, 200); font-size: 13px; background: transparent;"
        )
        self._lista.addStretch()
        self._lista.addWidget(etiqueta)
        self._lista.addStretch()

    def agregar_resultado(self, widget):
        self._lista.addWidget(widget)

    def cerrar_resultados(self):
        self._lista.addStretch()
        self._scroll.verticalScrollBar().setValue(0)

    # --- PDF ------------------------------------------------------------
    def _pedir_pdf(self):
        n = self._total_resultados
        if n == 0:
            self.mostrar_advertencia("SIGEA", "Primero haz una consulta que tenga resultados.")
            return

        if n == 1:
            detalle = "Se creará una ficha individual, sin tabla."
        else:
            detalle = f"Se creará un listado en tabla con {n} registros."

        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Question)
        caja.setWindowTitle("Generar PDF")
        caja.setText("¿Deseas generar el PDF de esta consulta?")
        caja.setInformativeText(detalle)
        si = caja.addButton("Sí, generar", QMessageBox.AcceptRole)
        caja.addButton("Cancelar", QMessageBox.RejectRole)
        caja.exec()
        if caja.clickedButton() is si:
            self.generar_pdf()

    # --- barra de búsqueda ---------------------------------------------
    def _barra_consulta(self):
        tarjeta = self.crear_tarjeta(self.ANCHO_CONTENIDO, 84, 18)
        lay = QHBoxLayout(tarjeta)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(12)

        lay.addWidget(self.crear_label_campo("CONSULTAR POR", color="rgba(128, 128, 128, 200)"))
        self.selector_campo = self.crear_glass_radio_group(list(self.OPCIONES_FILTRO))
        lay.addWidget(self.selector_campo)

        self.campo_valor = CampoFlotante("Valor a buscar")
        self.campo_valor.setMinimumWidth(0)
        self.campo_valor.setMaximumWidth(16777215)
        self.campo_valor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.campo_valor.entrada.returnPressed.connect(self.consultar)
        lay.addWidget(self.campo_valor, 1)

        lay.addWidget(self.crear_boton(self.TEXTO_BOTON, self.consultar, ancho=170, alto=44))
        return tarjeta

    def volver(self):
        self.close()

    def closeEvent(self, evento):
        if self.menu is not None and not self._navegando:
            self.menu.show()
        super().closeEvent(evento)
