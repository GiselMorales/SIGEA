from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
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

        resumen = QHBoxLayout()
        resumen.setSpacing(12)
        self._contadores = {}
        for clave, titulo, color in (
            ("total", "ACCESOS REGISTRADOS", "#1E508E"),
            ("activos", "SESIONES ACTIVAS", "#E68A00"),
            ("secretaria", "SECRETARÍA", "#7B4CB5"),
            ("docente", "DOCENTES", "#16876B"),
        ):
            tarjeta = QFrame()
            tarjeta.setObjectName(f"resumen_{clave}")
            tarjeta.setStyleSheet(
                f"QFrame#resumen_{clave} {{ background: white; "
                "border-radius: 12px; border-left: 5px solid "
                f"{color}; }}"
            )
            contenido = QVBoxLayout(tarjeta)
            contenido.setContentsMargins(14, 10, 14, 10)
            numero = QLabel("0")
            numero.setStyleSheet(
                f"color: {color}; font-size: 24px; font-weight: bold; "
                "background: transparent;"
            )
            etiqueta = QLabel(titulo)
            etiqueta.setStyleSheet(
                "color: #5B6B79; font-size: 9px; font-weight: bold; "
                "background: transparent;"
            )
            contenido.addWidget(numero)
            contenido.addWidget(etiqueta)
            self._contadores[clave] = numero
            resumen.addWidget(tarjeta, 1)
        raiz.addLayout(resumen)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self._lista = QWidget()
        self._lista.setStyleSheet("background: transparent;")
        self._lista_layout = QVBoxLayout(self._lista)
        self._lista_layout.setContentsMargins(2, 2, 10, 8)
        self._lista_layout.setSpacing(10)
        self._scroll.setWidget(self._lista)
        raiz.addWidget(self._scroll, 1)

    def actualizar(self):
        if not es_administrador(self.usuario):
            self.boton_actualizar.setEnabled(False)
            self._mostrar_vacio("La bitácora solo está disponible para admin.")
            self.mostrar_advertencia(
                "Acceso restringido",
                "La bitácora de accesos solo está disponible para admin.",
            )
            return

        registros, problema = listar_entradas_secretarias(self.usuario)
        if problema:
            self._mostrar_vacio(problema)
            self.mostrar_advertencia("Bitácora de accesos", problema)
            return

        while self._lista_layout.count():
            item = self._lista_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        total = len(registros)
        activos = sum(not registro["fecha_salida"] for registro in registros)
        administrativos = sum(
            registro["tipo_usuario"] == "administrativo"
            for registro in registros
        )
        docentes = sum(
            registro["tipo_usuario"] == "docente"
            for registro in registros
        )
        for clave, valor in (
            ("total", total),
            ("activos", activos),
            ("secretaria", administrativos),
            ("docente", docentes),
        ):
            self._contadores[clave].setText(str(valor))

        if not registros:
            self._mostrar_vacio("Todavía no hay accesos registrados.")
            return

        for registro in registros:
            self._lista_layout.addWidget(self._tarjeta_acceso(registro))
        self._lista_layout.addStretch(1)

    def _tarjeta_acceso(self, registro):
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjetaAcceso")
        tarjeta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tarjeta.setStyleSheet(
            "#tarjetaAcceso { background: white; border-radius: 12px; "
            "border: 1px solid #DCE7F5; }"
        )
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(16, 12, 16, 12)
        fila.setSpacing(14)

        icono = QLabel(
            "S" if registro["tipo_usuario"] == "administrativo" else "D"
        )
        icono.setAlignment(Qt.AlignCenter)
        icono.setFixedSize(42, 42)
        color = (
            "#7B4CB5"
            if registro["tipo_usuario"] == "administrativo"
            else "#16876B"
        )
        icono.setStyleSheet(
            f"background: {color}; color: white; border-radius: 21px; "
            "font-size: 17px; font-weight: bold;"
        )
        fila.addWidget(icono)

        identidad = QVBoxLayout()
        identidad.setSpacing(3)
        usuario = QLabel(registro["usuario"])
        usuario.setStyleSheet(
            "color: #1E2A3A; font-size: 14px; font-weight: bold; "
            "background: transparent;"
        )
        tipo = (
            "Secretaría"
            if registro["tipo_usuario"] == "administrativo"
            else "Docente"
        )
        etiqueta_tipo = QLabel(tipo)
        etiqueta_tipo.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: bold; "
            "background: transparent;"
        )
        identidad.addWidget(usuario)
        identidad.addWidget(etiqueta_tipo)
        fila.addLayout(identidad, 1)

        fechas = QVBoxLayout()
        fechas.setSpacing(4)
        entrada = registro["fecha_entrada"].strftime("%d/%m/%Y %H:%M:%S")
        salida = registro["fecha_salida"]
        salida_texto = (
            salida.strftime("%d/%m/%Y %H:%M:%S")
            if salida
            else "Sesión activa"
        )
        for titulo, texto, color_fecha in (
            ("ENTRADA", entrada, "#5B6B79"),
            (
                "SALIDA",
                salida_texto,
                "#E68A00" if salida is None else "#5B6B79",
            ),
        ):
            detalle = QLabel(f"{titulo}  {texto}")
            detalle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            detalle.setStyleSheet(
                f"color: {color_fecha}; font-size: 10px; "
                "background: transparent;"
            )
            fechas.addWidget(detalle)
        fila.addLayout(fechas)
        return tarjeta

    def _mostrar_vacio(self, texto):
        while self._lista_layout.count():
            item = self._lista_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        mensaje = QLabel(texto)
        mensaje.setWordWrap(True)
        mensaje.setAlignment(Qt.AlignCenter)
        mensaje.setStyleSheet(
            "color: white; font-size: 13px; padding: 28px; "
            "background: rgba(255,255,255,24); border-radius: 12px;"
        )
        self._lista_layout.addWidget(mensaje)
        self._contadores["total"].setText("0")
        self._contadores["activos"].setText("0")
        self._contadores["secretaria"].setText("0")
        self._contadores["docente"].setText("0")

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)
