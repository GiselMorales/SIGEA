from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt

from ventanas.ventana import VentanaBase, Config, CampoFlotante
from ventanas.componentes import opciones_barra


class VentanaConsulta(VentanaBase):
    """Base de las ventanas de consulta. El resultado se entrega en PDF.
    Cada módulo define OPCIONES_FILTRO y el método consultar()."""

    OPCIONES_FILTRO = ["Todos"]
    ANCHO_CONTENIDO = 806
    TEXTO_BOTON = "Generar PDF"

    def __init__(self, titulo_ventana, titulo, menu=None, ancho=1080, alto=660):
        super().__init__(titulo_ventana, ancho, alto)
        self.menu = menu
        self._armar(titulo)
        self.centrar_ventana()

    def consultar(self):
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
        derecha.addWidget(self._panel_central(), 1)
        self.etiqueta_info = self.crear_label_campo("", color="rgba(255, 255, 255, 200)")
        derecha.addWidget(self.etiqueta_info)
        derecha.addWidget(self._barra_consulta())
        cuerpo.addLayout(derecha, 1)

        raiz.addLayout(cuerpo, 1)
        self._barra.seleccionar(1)

    def _navegar(self, indice, texto):
        if indice in (2, 3, 4):
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

    def _panel_central(self):
        """Zona principal: ahora solo explica que el resultado sale en PDF."""
        panel = QFrame()
        panel.setObjectName("panelPdf")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel.setStyleSheet(
            "#panelPdf { background-color: #FFFFFF; border-radius: 14px; }"
        )
        lay = QVBoxLayout(panel)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(8)

        titulo = QLabel("Consulta en PDF")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {Config.AZUL_ENTRAR}; font-size: 22px; font-weight: bold; background: transparent;"
        )
        texto = QLabel(
            "Elige cómo consultar, escribe el valor a buscar\n"
            f"y presiona «{self.TEXTO_BOTON}». El documento se abrirá automáticamente."
        )
        texto.setAlignment(Qt.AlignCenter)
        texto.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 13px; background: transparent;"
        )
        lay.addWidget(titulo)
        lay.addWidget(texto)
        return panel

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

        lay.addWidget(self.crear_boton(self.TEXTO_BOTON, self.consultar, ancho=180, alto=44))
        return tarjeta

    def volver(self):
        self.close()

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)