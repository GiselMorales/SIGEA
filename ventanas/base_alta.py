from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSizePolicy,
    QGraphicsOpacityEffect, QFileDialog, QCompleter, QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from ventanas.ventana import VentanaBase, Config, CampoFlotante

AZUL = "#1E508E"
GRIS = "#5B6B79"
_ANCHO_MAX_QT = 16777215

class _Seccion:
    def __init__(self, indice, tarjeta, claves, validador, error, estado):
        self.indice = indice
        self.tarjeta = tarjeta
        self.claves = claves
        self.validador = validador
        self.error = error
        self.estado = estado
        self.validada = False
        self.datos = {}
        self.actualizando = False      # evita que reescribir un campo cuente como cambio del usuario

class VentanaAlta(VentanaBase):
    ANCHO_TARJETA = 790
    #contiene la estructura de la ventana para dar de alta un registro (alumno, docente, inscripción, etc.)
    def __init__(self, titulo_ventana, titulo, texto_registrar, menu=None, ancho=1080, alto=660):
        super().__init__(titulo_ventana, ancho, alto)
        self.menu = menu
        self._secciones = []
        self._seccion_de = {}          # clave de campo - indice de sección
        self._lectores = {}            # clave - (función que lee el valor, widget para enfocar)
        self._claves_actuales = []
        self._pdfs = {}                # clave - lista de rutas PDF elegidas
        self._etiquetas_pdf = {}
        self._filas_pdf = {}
        self._layouts_pdf = {}

        self._armar_marco(titulo)
        self.construir_secciones()
        self._terminar(texto_registrar)
        self.centrar_ventana()

    def construir_secciones(self):
        raise NotImplementedError
    
    def guardar(self, datos):
        return True, (
            "Los datos son válidos.\n"
            "(Falta conectar la base de datos para guardarlos.)"
        )

    #marco de la ventana, con barra lateral y scroll para el contenido
    def _armar_marco(self, titulo):
        raiz = QVBoxLayout(self) 
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(16)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self.crear_label_titulo(titulo, 30))
        cabecera.addStretch()
        cabecera.addWidget(self.crear_boton_salida("Salir", self.volver, ancho=120, alto=40))
        raiz.addLayout(cabecera)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(18)

        self._barra = self.crear_barra_vertical([
            ("Menú principal", self.volver),
            ("Alta", None),
            ("Baja", None),
            ("Modificar", None),
            ("Consultar", None),
        ])
        self._barra.seleccionado.connect(self._navegar)
        cuerpo.addWidget(self._barra, 0, Qt.AlignTop)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,90); border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,150); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        contenido = QWidget()
        self._col = QVBoxLayout(contenido)
        self._col.setContentsMargins(0, 0, 12, 0)
        self._col.setSpacing(16)
        self._scroll.setWidget(contenido)
        cuerpo.addWidget(self._scroll, 1)

        raiz.addLayout(cuerpo, 1)
        self._barra.seleccionar(1)       # "Alta" activa

    def _navegar(self, indice, texto):
        if indice in (2, 3, 4):
            self.mostrar_mensaje(texto, "Esta opción aún está en construcción.")
            self._barra.seleccionar(1)

    def _terminar(self, texto_registrar):
        self.boton_registrar = self.crear_boton_entrar(texto_registrar, self._registrar, ancho=320, alto=54)
        self.boton_registrar.setEnabled(False)
        self._col.addWidget(self.boton_registrar, 0, Qt.AlignHCenter)
        self._col.addStretch()
        for seccion in self._secciones[1:]:
            self._bloquear(seccion, True)

    def volver(self):
        self.close()

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)


    def _contenedor(self, nombre="fila"):
        c = QWidget()
        c.setObjectName(nombre)
        c.setStyleSheet(f"#{nombre} {{ background: transparent; }}")
        return c

    def _registrar_lector(self, clave, lector, widget):
        self._lectores[clave] = (lector, widget)
        self._claves_actuales.append(clave)

    def campo(self, clave, etiqueta, sugerencias=None, password=False):
        """Campo flotante. 'sugerencias' agrega una lista desplegable al escribir."""
        c = CampoFlotante(etiqueta, password)
        c.setMinimumWidth(0)                              # que se repartan el ancho de la fila
        c.setMaximumWidth(_ANCHO_MAX_QT)
        c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if sugerencias:
            lista = QCompleter(list(sugerencias), c.entrada)
            lista.setCaseSensitivity(Qt.CaseInsensitive)
            lista.setFilterMode(Qt.MatchContains)
            c.entrada.setCompleter(lista)
        c.entrada.textChanged.connect(lambda _t, k=clave: self._cambio(k))
        self._registrar_lector(clave, c.valor, c.entrada)
        return c

    def selector(self, clave, etiqueta, opciones):
        radio = self.crear_glass_radio_group(list(opciones))
        radio.seleccion_cambiada.connect(lambda _i, _t, k=clave: self._cambio(k))
        self._registrar_lector(clave, radio.obtener_seleccion, radio)

        caja = self._contenedor("selector")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.crear_label_campo(etiqueta.upper(), color="rgba(128, 128, 128, 178)"))
        lay.addWidget(radio)
        return caja

    
    def zona_pdf(self, clave, texto_boton="Subir PDF"):
        self._pdfs[clave] = []
        self._filas_pdf[clave] = []

        lista = self.crear_label_subtitulo(
            "Ningún archivo seleccionado.",
            10,
            Config.TEXTO_OSCURO,
        )
        lista.setWordWrap(True)
        self._etiquetas_pdf[clave] = lista

        boton = self.crear_boton_secundario(
            texto_boton,
            lambda: self._elegir_pdfs(clave),
            ancho=150,
            alto=42,
        )

        self._registrar_lector(
            clave,
            lambda: list(self._pdfs[clave]),
            None,
        )

        caja = self._contenedor("zonaPdf")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(boton, 0, Qt.AlignLeft)
        lay.addWidget(lista)

        contenedor_filas = QWidget()
        contenedor_filas.setStyleSheet("background: transparent;")
        layout_filas = QVBoxLayout(contenedor_filas)
        layout_filas.setContentsMargins(0, 0, 0, 0)
        layout_filas.setSpacing(6)

        self._layouts_pdf[clave] = layout_filas
        lay.addWidget(contenedor_filas)

        return caja


    def _crear_fila_pdf(self, clave, ruta):
        """Crea una fila con el nombre, tipo y botón para quitar un PDF."""
        fila = self._contenedor("filaPdf")
        layout = QHBoxLayout(fila)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        archivo = Path(ruta)
        nombre = self.crear_label_subtitulo(
            archivo.name, 10, Config.TEXTO_OSCURO
        )
        nombre.setWordWrap(True)

        tipo = QComboBox()
        tipo.addItem("Selecciona el tipo", "")
        tipo.addItem("Acta de nacimiento", "acta_nacimiento")
        tipo.addItem("CURP", "curp")
        tipo.addItem("Certificado de bachillerato", "certificado_bachillerato")
        tipo.addItem("Comprobante de domicilio", "comprobante_domicilio")
        tipo.addItem("Otro", "otro")
        tipo.setMinimumWidth(210)

        quitar = QPushButton("Quitar")
        quitar.setFixedWidth(70)

        layout.addWidget(nombre, 1)
        layout.addWidget(tipo, 0)
        layout.addWidget(quitar, 0)

        fila.tipo_documento = tipo
        fila.ruta_pdf = str(archivo)
        quitar.clicked.connect(
            lambda: self._quitar_pdf(clave, fila)
        )

        return fila


    def _quitar_pdf(self, clave, fila):
        if fila in self._filas_pdf.get(clave, []):
            self._filas_pdf[clave].remove(fila)

        self._actualizar_pdfs(clave)
        fila.deleteLater()


    def _actualizar_pdfs(self, clave):
        """Actualiza los datos que recibe la validación de la sección."""
        documentos = []

        for fila in self._filas_pdf.get(clave, []):
            documentos.append({
                "ruta": fila.ruta_pdf,
                "tipo": fila.tipo_documento.currentData(),
            })

        self._pdfs[clave] = documentos

        if documentos:
            texto = "\n".join(
                f"• {Path(doc['ruta']).name}"
                for doc in documentos
            )
        else:
            texto = "Ningún archivo seleccionado."

        self._etiquetas_pdf[clave].setText(texto)
        self._cambio(clave)

    def fila(self, *widgets, pesos=None):
        """Acomoda widgets en una fila. Un None deja un espacio vacío."""
        caja = self._contenedor("fila")
        lay = QHBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        for i, w in enumerate(widgets):
            peso = pesos[i] if pesos else 1
            if w is None:
                lay.addStretch(peso)
            else:
                lay.addWidget(w, peso, Qt.AlignBottom)
        return caja

    # ------------------------------------------------------------------
    #  SECCIONES
    # ------------------------------------------------------------------
    def agregar_seccion(self, titulo, filas, validador, texto_boton="Validar"):
        """validador: función(datos) -> (errores, limpio)  (ver logica/validaciones.py)."""
        indice = len(self._secciones)
        tarjeta = self.crear_formulario(titulo, "", texto_boton=None, ancho=self.ANCHO_TARJETA)
        for f in filas:
            tarjeta.agregar_widget(f)

        error = self.crear_label_error(9)
        error.setWordWrap(True)
        error.setAlignment(Qt.AlignLeft)
        error.hide()
        tarjeta.agregar_widget(error)

        estado = self.crear_label_campo("", color=AZUL)
        boton = self.crear_boton_secundario(texto_boton, lambda: self._validar(indice), ancho=130, alto=42)
        pie = self._contenedor("pieSeccion")
        lay = QHBoxLayout(pie)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(estado, 1)
        lay.addWidget(boton, 0, Qt.AlignRight)
        tarjeta.agregar_widget(pie)

        claves = list(self._claves_actuales)
        self._claves_actuales = []
        seccion = _Seccion(indice, tarjeta, claves, validador, error, estado)
        for k in claves:
            self._seccion_de[k] = indice
        self._secciones.append(seccion)
        self._col.addWidget(tarjeta, 0, Qt.AlignHCenter)
        return seccion

    def _bloquear(self, seccion, bloquear):
        seccion.tarjeta.setEnabled(not bloquear)
        if bloquear:
            efecto = QGraphicsOpacityEffect(seccion.tarjeta)
            efecto.setOpacity(0.5)
            seccion.tarjeta.setGraphicsEffect(efecto)
        else:
            seccion.tarjeta.setGraphicsEffect(None)

    def _poner_estado(self, seccion, texto, color=AZUL):
        seccion.estado.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: bold; background: transparent;"
        )
        seccion.estado.setText(texto)

    def _leer(self, clave):
        return self._lectores[clave][0]()

    def _validar(self, indice):
        seccion = self._secciones[indice]
        datos = {k: self._leer(k) for k in seccion.claves}

        errores, limpio = seccion.validador(datos)

        if errores:
            seccion.validada = False
            seccion.error.setText("\n".join(f"• {m}" for m in errores.values()))
            seccion.error.show()
            self._poner_estado(seccion, "")
            for clave in errores:                        # enfoca el primer campo con error
                widget = self._lectores.get(clave, (None, None))[1]
                if isinstance(widget, QLineEdit):
                    widget.setFocus()
                    break
            return

        seccion.actualizando = True
        for clave, valor in limpio.items():
            widget = self._lectores.get(clave, (None, None))[1]
            if isinstance(widget, QLineEdit):
                texto = "" if valor is None else str(valor)
                if widget.text() != texto:
                    widget.setText(texto)

        seccion.actualizando = False

        seccion.datos = limpio
        seccion.validada = True
        seccion.error.hide()
        self._poner_estado(seccion, "✔ Sección validada")

        if indice + 1 < len(self._secciones):
            siguiente = self._secciones[indice + 1]
            self._bloquear(siguiente, False)
            destino = siguiente.tarjeta
        else:
            self.boton_registrar.setEnabled(True)
            destino = self.boton_registrar
        QTimer.singleShot(80, lambda: self._scroll.ensureWidgetVisible(destino, 0, 40))

    def _cambio(self, clave):
        """El usuario cambió un dato: lo ya validado de ahí hacia abajo deja de valer."""
        indice = self._seccion_de.get(clave)
        if indice is None:
            return
        seccion = self._secciones[indice]
        if seccion.actualizando:
            return
        if seccion.validada or any(s.validada for s in self._secciones[indice + 1:]):
            for s in self._secciones[indice:]:
                s.validada = False
            for s in self._secciones[indice + 1:]:
                self._bloquear(s, True)
            self._poner_estado(seccion, "Cambiaste datos: vuelve a validar esta sección.", GRIS)
            self.boton_registrar.setEnabled(False)

    # ------------------------------------------------------------------
    #  PDF
    # ------------------------------------------------------------------
    
    def _elegir_pdfs(self, clave):
        archivos, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecciona archivos PDF", "", "Documentos PDF (*.pdf)", )

        if not archivos:
            return
        rutas_actuales = {
            str(Path(f.ruta_pdf).resolve())
            for f in self._filas_pdf[clave]
        }

        for ruta in archivos:
            ruta_normalizada = str(Path(ruta).resolve())

            if ruta_normalizada in rutas_actuales:
                continue

            fila = self._crear_fila_pdf(clave, ruta)
            self._filas_pdf[clave].append(fila)
            self._layouts_pdf[clave].addWidget(fila)
            fila.tipo_documento.currentIndexChanged.connect(
                lambda _i, k=clave: self._actualizar_pdfs(k)
            )

            rutas_actuales.add(ruta_normalizada)

        self._actualizar_pdfs(clave)
    #  CONFIRMACIÓN ANTES DE REGISTRAR
    def resumen_confirmacion(self, datos):
        """
        A redefinir en cada alta. Devuelve (lineas, aviso):
          lineas -> [("Etiqueta", "valor"), ...] con los datos principales a mostrar
          aviso  -> texto de lo que se va a crear automáticamente (puede ir vacío)
        """
        return [], ""

    def confirmar_registro(self, datos):
        """Pregunta '¿Seguro que deseas registrar?'. Devuelve True si el usuario confirma."""
        lineas, aviso = self.resumen_confirmacion(datos)
        detalle = "\n".join(f"•  {etiqueta}: {valor}" for etiqueta, valor in lineas if valor)
        if aviso:
            detalle += "\n\n" + aviso

        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Question)
        caja.setWindowTitle("Confirmar registro")
        caja.setText("¿Seguro que deseas registrar estos datos?")
        caja.setInformativeText(detalle)
        si = caja.addButton("Sí, registrar", QMessageBox.AcceptRole)
        no = caja.addButton("Revisar datos", QMessageBox.RejectRole)
        caja.setDefaultButton(no)
        caja.exec()
        return caja.clickedButton() is si

    #  REGISTRAR / LIMPIAR
    def _registrar(self):
        if not all(s.validada for s in self._secciones):
            self.mostrar_advertencia("SIGEA", "Valida todas las secciones antes de registrar.")
            return
        datos = {}
        for s in self._secciones:
            datos.update(s.datos)
        if not self.confirmar_registro(datos):
            return
        ok, mensaje = self.guardar(datos)
        if ok:
            self.mostrar_mensaje("SIGEA", mensaje)
            self.limpiar()
        else:
            self.mostrar_advertencia("SIGEA", mensaje)

    def limpiar(self):
        for clave, (_, widget) in self._lectores.items():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif widget is not None and hasattr(widget, "seleccionar"):
                widget.seleccionar(0)
        for clave in self._pdfs:
            for fila in self._filas_pdf.get(clave, []):
                fila.deleteLater()
                self._filas_pdf[clave] = []
                self._pdfs[clave] = []
                self._etiquetas_pdf[clave].setText("Ningún archivo seleccionado.")
        for s in self._secciones:
            s.validada = False
            s.datos = {}
            s.error.hide()
            self._poner_estado(s, "")
            self._bloquear(s, s.indice != 0)
        self.boton_registrar.setEnabled(False)
        self._scroll.verticalScrollBar().setValue(0)