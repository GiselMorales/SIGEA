from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from reportlab.platypus.doctemplate import LayoutError

from Logica.reinscripcion_semestres import (
    consultar_horario,
    consultar_reinscripcion,
    consultar_reinscripciones,
    correo_institucional,
    listar_horarios_semestre,
    registrar_reinscripcion,
    validar_numero_control,
)
from reportes.generador_pdf import generar_pdf_horario_reinscripcion
from ventanas.ventana import Config, VentanaBase

CARPETA_REPORTES = (
    Path(__file__).resolve().parent.parent
    / "reportes_generados"
    / "reinscripciones"
)
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


class VentanaModuloReinscripcion(VentanaBase):
    def __init__(self, menu=None):
        super().__init__("SIGEA - Gestión de reinscripciones", 1120, 800)
        self.menu = menu
        self._horario_semestre_id = None
        self._control_validado = None
        self._horario_actual = None
        self._armar_interfaz()
        self._cargar_opciones_horario()
        self.centrar_ventana()

    def _armar_interfaz(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(12)

        cabecera = QHBoxLayout()
        cabecera.addWidget(
            self.crear_label_titulo("GESTIÓN DE REINSCRIPCIONES", 27)
        )
        cabecera.addStretch()
        cabecera.addWidget(
            self.crear_boton_salida("Menú", self.close, ancho=120, alto=40)
        )
        raiz.addLayout(cabecera)

        formulario = self._crear_panel()
        grid = QGridLayout(formulario)
        grid.setContentsMargins(18, 14, 18, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(9)

        self.campo_control = self.crear_campo_texto(
            "Número de control (8 dígitos)"
        )
        self.campo_control.setMaxLength(8)
        self.campo_control.textChanged.connect(self._cambio_control)
        self.boton_validar = self.crear_boton(
            "Validar",
            self._validar_control_usuario,
            ancho=290,
            alto=42,
        )
        control_fila = QHBoxLayout()
        control_fila.setContentsMargins(0, 0, 0, 0)
        control_fila.setSpacing(10)
        control_fila.addWidget(self.campo_control, 1)
        control_fila.addWidget(self.boton_validar)
        grid.addWidget(
            self._crear_campo("Número de control", control_fila), 0, 0, 1, 2
        )

        self.campo_paterno = self.crear_campo_texto("Apellido paterno")
        self.campo_materno = self.crear_campo_texto(
            "Apellido materno (opcional)"
        )
        self.campo_nombres = self.crear_campo_texto("Nombre(s)")
        grid.addWidget(
            self._crear_campo("Apellido paterno", self.campo_paterno), 1, 0
        )
        grid.addWidget(
            self._crear_campo("Apellido materno", self.campo_materno), 1, 1
        )
        grid.addWidget(
            self._crear_campo("Nombre(s)", self.campo_nombres), 1, 2
        )

        self.selector_horario = QComboBox()
        self._estilizar_combo(self.selector_horario)
        self.selector_horario.addItem("Cargando horarios...")
        self.selector_horario.setItemData(0, None)
        self.selector_horario.currentIndexChanged.connect(
            self._cambio_horario
        )
        grid.addWidget(
            self._crear_campo("Horario de reinscripción", self.selector_horario),
            2,
            0,
        )

        self.campo_correo = self.crear_campo_texto(
            "Correo institucional generado automáticamente"
        )
        self.campo_correo.setReadOnly(True)
        grid.addWidget(
            self._crear_campo("Correo institucional", self.campo_correo),
            2,
            1,
        )

        acciones = QHBoxLayout()
        acciones.addStretch()
        self.boton_consultar = self.crear_boton_secundario(
            "Consultar reinscripciones",
            self._abrir_consulta_reinscripciones,
            ancho=245,
            alto=44,
        )
        self.boton_limpiar = self.crear_boton_secundario(
            "Limpiar formulario", self._limpiar_formulario, ancho=190, alto=44
        )
        self.boton_registrar = self.crear_boton_entrar(
            "Registrar reinscripción",
            self._registrar,
            ancho=260,
            alto=48,
        )
        acciones.addWidget(self.boton_consultar)
        acciones.addWidget(self.boton_limpiar)
        acciones.addWidget(self.boton_registrar)
        grid.addLayout(acciones, 3, 0, 1, 3)
        raiz.addWidget(formulario)

        encabezado_horario = QHBoxLayout()
        encabezado_horario.addWidget(
            self.crear_label_titulo("HORARIO SELECCIONADO", 17)
        )
        encabezado_horario.addStretch()
        self.boton_pdf = self.crear_boton_secundario(
            "Generar", self._generar_pdf, ancho=160, alto=42
        )
        encabezado_horario.addWidget(self.boton_pdf)
        raiz.addLayout(encabezado_horario)
        self.etiqueta_estado_horario = QLabel()
        self.etiqueta_estado_horario.setWordWrap(True)
        self.etiqueta_estado_horario.setStyleSheet(
            f"color: {Config.TEXTO_CLARO}; background: transparent;"
        )
        raiz.addWidget(self.etiqueta_estado_horario)
        self.tabla_horario = self._crear_tabla(
            ["Hora"] + [dia.capitalize() for dia in DAYS]
        )
        self.tabla_horario.setShowGrid(False)
        self.tabla_horario.verticalHeader().setVisible(False)
        self.tabla_horario.setAlternatingRowColors(False)
        self.tabla_horario.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        for columna in range(1, len(DAYS) + 1):
            self.tabla_horario.horizontalHeader().setSectionResizeMode(
                columna, QHeaderView.Stretch
            )
        self.tabla_horario.setStyleSheet("""
            QTableWidget {
                background: white;
                color: #1E2A3A;
                border: none;
                border-radius: 12px;
                selection-background-color: #B9DDF7;
                gridline-color: #9FB3CF;
            }
            QHeaderView::section {
                background: #1E508E;
                color: white;
                font-weight: bold;
                padding: 10px 8px;
                border: 1px solid #DCE7F5;
            }
        """)
        self.tabla_horario.setMinimumHeight(190)
        raiz.addWidget(self.tabla_horario, 1)

    def _crear_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: {Config.FONDO_FORM};
                border: 1px solid {Config.FONDO_FORM_BORDE};
                border-radius: 12px;
            }}
        """)
        return panel

    def _crear_campo(self, titulo, widget):
        caja = QVBoxLayout()
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(4)
        etiqueta = self.crear_label_campo(titulo, Config.TEXTO_OSCURO)
        caja.addWidget(etiqueta)
        if isinstance(widget, QHBoxLayout):
            caja.addLayout(widget)
        else:
            caja.addWidget(widget)
        contenedor = QFrame()
        contenedor.setStyleSheet("QFrame { background: transparent; border: none; }")
        contenedor.setLayout(caja)
        return contenedor

    @staticmethod
    def _estilizar_combo(combo):
        combo.setMinimumHeight(40)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet(f"""
            QComboBox {{
                background: {Config.GRIS_CAMPO};
                color: {Config.TEXTO_OSCURO};
                border: 1px solid {Config.FONDO_FORM_BORDE};
                border-radius: 9px;
                padding: 5px 10px;
            }}
            QComboBox QAbstractItemView {{
                background: white;
                color: {Config.TEXTO_OSCURO};
            }}
        """)

    @staticmethod
    def _crear_tabla(encabezados):
        tabla = QTableWidget(0, len(encabezados))
        tabla.setHorizontalHeaderLabels(encabezados)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setWordWrap(True)
        tabla.setStyleSheet("""
            QTableWidget {
                background: white;
                color: #1E2A3A;
                alternate-background-color: #EDF3FD;
                gridline-color: #D5DFEC;
                border: 1px solid #C9D8EE;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #0B2A55;
                color: white;
                padding: 7px;
                border: none;
                font-weight: bold;
            }
        """)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tabla.horizontalHeader().setStretchLastSection(True)
        return tabla

    def _cambio_control(self, texto):
        self._control_validado = None
        self._limpiar_horario(
            "Valida el número de control para consultar el horario correspondiente."
        )
        self.campo_correo.setText(correo_institucional(texto) if texto else "")

    def _cambio_horario(self, *_):
        self._control_validado = None
        self._limpiar_horario(
            "Selecciona un horario y valida el número de control para consultarlo."
        )

    def _semestre_turno(self):
        seleccion = self.selector_horario.currentData()
        if seleccion is None:
            return None, None
        return seleccion["semestre"], seleccion["turno"]

    def _cargar_opciones_horario(self):
        horarios, problema = listar_horarios_semestre()
        self.selector_horario.blockSignals(True)
        self.selector_horario.clear()
        if problema:
            QMessageBox.warning(self, "Horarios", problema)
        if horarios:
            for horario in horarios:
                semestre = horario["semestre"]
                turno = horario["turno"].capitalize()
                descripcion = horario["descripcion"]
                self.selector_horario.addItem(
                    descripcion or f"{semestre}° semestre · {turno}",
                    horario,
                )
        else:
            self.selector_horario.addItem("No hay horarios disponibles", None)
        self.selector_horario.blockSignals(False)
        self._cambio_horario()

    def _validar_control(self, mostrar_exito):
        numero_control = self.campo_control.text().strip()
        semestre, _ = self._semestre_turno()
        if semestre is None:
            QMessageBox.warning(
                self, "Horario", "Selecciona un horario antes de validar."
            )
            return False
        valido, problema = validar_numero_control(numero_control, semestre)
        if not valido:
            QMessageBox.warning(self, "Número de control", problema)
            self.campo_control.setFocus()
            return False

        existente, problema = consultar_reinscripcion(numero_control)
        if problema:
            QMessageBox.warning(self, "Validación", problema)
            return False
        if existente:
            QMessageBox.warning(
                self,
                "Número de control duplicado",
                f"El alumno ya aparece registrado en {existente}° semestre.",
            )
            return False

        self._control_validado = numero_control
        self._cargar_horario()
        if mostrar_exito:
            QMessageBox.information(
                self,
                "Número de control",
                "El número de control es válido y no está registrado.",
            )
        return True

    def _validar_control_usuario(self):
        self._validar_control(mostrar_exito=True)

    def _cargar_horario(self):
        semestre, turno = self._semestre_turno()
        if semestre is None:
            self._limpiar_horario("Selecciona un horario disponible.")
            self.boton_registrar.setEnabled(False)
            return
        if self._control_validado != self.campo_control.text().strip():
            self._limpiar_horario(
                "Valida el número de control para consultar el horario seleccionado."
            )
            self.boton_registrar.setEnabled(False)
            return

        datos, problema = consultar_horario(semestre, turno)
        self._limpiar_horario("")
        self.boton_registrar.setEnabled(False)
        if problema:
            self.etiqueta_estado_horario.setText(problema)
            return

        self._horario_actual = datos
        self._horario_semestre_id = datos["horario_semestre_id"]
        bloques_por_materia = []
        franjas = set()
        for materia in datos["materias"]:
            bloques_validos = []
            for dia, inicio, fin, aula in materia["bloques"]:
                dia = str(dia).strip().casefold()
                if dia == "miercoles":
                    dia = "miércoles"
                if dia not in DAYS:
                    continue
                bloques_validos.append((dia, inicio, fin, aula))
                franjas.add((inicio, fin))
            bloques_por_materia.append((materia, bloques_validos))

        franjas_ordenadas = sorted(franjas)
        self.tabla_horario.setRowCount(len(franjas_ordenadas))
        total_bloques = 0
        for row, (inicio_franja, fin_franja) in enumerate(franjas_ordenadas):
            hora = QTableWidgetItem(
                f"{inicio_franja.strftime('%H:%M')} - "
                f"{fin_franja.strftime('%H:%M')}"
            )
            hora.setTextAlignment(Qt.AlignCenter)
            self.tabla_horario.setItem(row, 0, hora)

            for columna, dia in enumerate(DAYS, start=1):
                clases = []
                for indice, (materia, bloques) in enumerate(bloques_por_materia):
                    for dia_bloque, inicio, fin, aula in bloques:
                        if (
                            dia_bloque == dia
                            and inicio == inicio_franja
                            and fin == fin_franja
                        ):
                            clases.append(
                                (
                                    materia,
                                    aula,
                                    PASTELES[indice % len(PASTELES)],
                                )
                            )
                texto = "\n\n".join(
                    f"{materia['materia']}\n"
                    f"Grupo {materia['grupo']}\n"
                    f"Aula {aula or 'Sin aula'}"
                    for materia, aula, _ in clases
                )
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignCenter)
                if clases:
                    celda.setBackground(QColor(clases[0][2]))
                    celda.setForeground(QColor("#1E2A3A"))
                    celda.setToolTip(texto)
                    total_bloques += len(clases)
                self.tabla_horario.setItem(row, columna, celda)

        self.tabla_horario.resizeRowsToContents()
        for row in range(self.tabla_horario.rowCount()):
            self.tabla_horario.setRowHeight(
                row, max(58, self.tabla_horario.rowHeight(row))
            )
        grupos = len(datos["materias"])
        if not grupos:
            mensaje = (
                f"No hay materias ni horarios disponibles para {semestre}° "
                f"semestre {turno}."
            )
        elif not total_bloques:
            mensaje = (
                f"{grupos} materia(s) encontrada(s), pero no tienen clases "
                "programadas de lunes a viernes."
            )
        elif not self._horario_semestre_id:
            mensaje = (
                f"{grupos} materia(s) encontrada(s), pero no "
                f"hay un registro de horario_semestre para {semestre}° "
                f"{turno}. No se puede registrar sin esa configuración."
            )
        else:
            mensaje = (
                f"{grupos} materia(s) · {total_bloques} clase(s) "
                f"programada(s) de lunes a viernes · {turno.capitalize()}."
            )
            self.boton_registrar.setEnabled(True)
        self.etiqueta_estado_horario.setText(mensaje)

    def _limpiar_horario(self, mensaje):
        self.tabla_horario.setRowCount(0)
        self._horario_semestre_id = None
        self._horario_actual = None
        if hasattr(self, "boton_registrar"):
            self.boton_registrar.setEnabled(False)
        if hasattr(self, "etiqueta_estado_horario"):
            self.etiqueta_estado_horario.setText(mensaje)

    def _registrar(self):
        if not self._validar_control(mostrar_exito=False):
            return

        if not self._horario_semestre_id:
            QMessageBox.warning(
                self,
                "Horario no configurado",
                "No existe un horario registrado para este semestre y turno "
                "en horarios_semestre.",
            )
            return

        correcto, mensaje = registrar_reinscripcion(
            self.campo_control.text().strip(),
            self.campo_paterno.text().strip(),
            self.campo_materno.text().strip(),
            self.campo_nombres.text().strip(),
            *self._semestre_turno(),
        )
        if not correcto:
            QMessageBox.warning(self, "Reinscripción", mensaje)
            return

        QMessageBox.information(
            self,
            "Reinscripción",
            f"{mensaje}\n\nAhora selecciona dónde guardar el horario en PDF.",
        )
        if self._guardar_pdf():
            self._limpiar_formulario()

    def _limpiar_formulario(self):
        self.campo_control.clear()
        self.campo_paterno.clear()
        self.campo_materno.clear()
        self.campo_nombres.clear()
        self.campo_control.setFocus()

    def _abrir_consulta_reinscripciones(self):
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Consulta de reinscripciones")
        dialogo.resize(1000, 560)
        dialogo.setStyleSheet(
            f"background: {Config.FONDO_VENTANA}; color: {Config.TEXTO_OSCURO};"
        )
        layout = QVBoxLayout(dialogo)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(
            self.crear_label_titulo("ALUMNOS REINSCRITOS", 20)
        )

        controles = QHBoxLayout()
        campo_busqueda = self.crear_campo_texto(
            "Buscar por número de control o nombre"
        )
        boton_buscar = self.crear_boton(
            "Buscar",
            lambda: self._cargar_consulta_reinscripciones(
                lista, estado, campo_busqueda.text()
            ),
            ancho=120,
            alto=40,
        )
        controles.addWidget(campo_busqueda, 1)
        controles.addWidget(boton_buscar)
        layout.addLayout(controles)
        campo_busqueda.returnPressed.connect(boton_buscar.click)

        estado = QLabel()
        estado.setWordWrap(True)
        estado.setStyleSheet(
            f"color: {Config.TEXTO_CLARO}; background: transparent;"
        )
        layout.addWidget(estado)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        contenido = QFrame()
        contenido.setStyleSheet("QFrame { background: transparent; }")
        lista = QVBoxLayout(contenido)
        lista.setContentsMargins(2, 2, 8, 2)
        lista.setSpacing(10)
        scroll.setWidget(contenido)
        layout.addWidget(scroll, 1)

        self._cargar_consulta_reinscripciones(lista, estado)
        dialogo.exec()

    def _cargar_consulta_reinscripciones(
        self, lista, estado, filtro=""
    ):
        filas, problema = consultar_reinscripciones(filtro)
        while lista.count():
            item = lista.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if problema:
            estado.setText(problema)
            QMessageBox.warning(
                estado.window(), "Consulta de reinscripciones", problema
            )
            return

        if not filas:
            vacio = QLabel(
                "No se encontraron reinscripciones con ese criterio."
            )
            vacio.setAlignment(Qt.AlignCenter)
            vacio.setWordWrap(True)
            vacio.setStyleSheet(
                f"color: {Config.TEXTO_CLARO}; background: transparent; "
                "font-size: 13px;"
            )
            lista.addStretch()
            lista.addWidget(vacio)
            lista.addStretch()
        else:
            for reinscrito in filas:
                lista.addWidget(self._tarjeta_reinscripcion(reinscrito))
            lista.addStretch()

        estado.setText(
            f"{len(filas)} reinscripción(es) encontrada(s)."
            if filas
            else ""
        )

    @staticmethod
    def _tarjeta_reinscripcion(reinscrito):
        tarjeta = QFrame()
        tarjeta.setObjectName("resultadoReinscripcion")
        tarjeta.setAttribute(Qt.WA_StyledBackground, True)
        tarjeta.setMinimumHeight(84)
        tarjeta.setStyleSheet(
            "#resultadoReinscripcion { "
            "background-color: #FFFFFF; border-radius: 12px; }"
        )
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(3)

        nombre = QLabel(reinscrito["nombre"])
        nombre.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 13px; "
            "font-weight: bold; background: transparent;"
        )
        fecha = reinscrito["fecha_registro"]
        fecha_texto = (
            fecha.strftime("%d/%m/%Y %H:%M") if fecha else "Sin fecha"
        )
        detalle = QLabel(
            f"No. de control: {reinscrito['numero_control']}  •  "
            f"Semestre {reinscrito['semestre']}°  •  "
            f"Turno {reinscrito['turno'].capitalize()}"
        )
        contacto = QLabel(
            f"{reinscrito['correo']}  •  Registro: {fecha_texto}"
        )
        for etiqueta in (detalle, contacto):
            etiqueta.setWordWrap(True)
            etiqueta.setStyleSheet(
                f"color: {Config.TEXTO_SUBTITULO}; font-size: 11px; "
                "background: transparent;"
            )
        layout.addWidget(nombre)
        layout.addWidget(detalle)
        layout.addWidget(contacto)
        return tarjeta

    def _generar_pdf(self):
        self._guardar_pdf()

    def _guardar_pdf(self):
        if not self._control_validado:
            QMessageBox.information(
                self, "Generar", "Valida primero el número de control."
            )
            return False
        if self._horario_actual is None:
            QMessageBox.warning(
                self,
                "Generar",
                "Valida el número de control y carga su horario antes de generar el PDF.",
            )
            return False
        materias = self._horario_actual.get("materias", [])
        if not any(
            bloque[0] in DAYS
            for materia in materias
            for bloque in materia["bloques"]
        ):
            QMessageBox.information(
                self,
                "Generar",
                "No hay bloques horarios de lunes a viernes para generar el PDF.",
            )
            return False

        numero_control = self.campo_control.text().strip()
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar horario de reinscripción",
            str(CARPETA_REPORTES / f"horario_{numero_control}.pdf"),
            "Documentos PDF (*.pdf)",
        )
        if not ruta:
            QMessageBox.information(
                self,
                "Reinscripción",
                "La reinscripción quedó registrada. Puedes guardar el PDF "
                "después con el botón «Generar».",
            )
            return False

        try:
            self._generar_archivo_pdf(ruta)
        except (OSError, ValueError, LayoutError) as error:
            QMessageBox.critical(
                self,
                "Generar",
                f"No fue posible generar el documento:\n{error}",
            )
            return False
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(ruta).resolve())))
        QMessageBox.information(
            self, "Generar", f"El horario se generó correctamente:\n{ruta}"
        )
        return True

    def _generar_archivo_pdf(self, ruta):
        semestre, turno = self._semestre_turno()
        numero_control = self.campo_control.text().strip()
        nombre = " ".join(
            parte
            for parte in (
                self.campo_paterno.text().strip(),
                self.campo_materno.text().strip(),
                self.campo_nombres.text().strip(),
            )
            if parte
        )
        return generar_pdf_horario_reinscripcion(
            {
                "alumno_nombre": nombre,
                "numero_control": numero_control,
                "semestre": semestre,
                "turno": turno,
                "correo": correo_institucional(numero_control),
                "materias": self._horario_actual["materias"],
            },
            ruta,
        )

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)
