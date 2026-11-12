import re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from reportlab.platypus.doctemplate import LayoutError

from Logica.bitacora import registrar_salida
from Logica.portal_docente import (
    SEMANA_CIERRE,
    SEMANA_UNIDAD,
    guardar_evaluacion,
    guardar_promedio_final,
    listar_grupos_docente,
    obtener_estado_calificaciones,
    obtener_horario_docente,
    obtener_perfil_docente,
)
from reportes.generador_pdf import generar_pdf_consulta
from ventanas.componentes import InsigniaUsuario
from ventanas.ventana import Config, VentanaBase, ruta_recurso

DIAS_SEMANA = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
)
COLORES_HORARIO = (
    "#DCEBFA",
    "#E3F4E1",
    "#FCEFD2",
    "#F6DDE8",
    "#E6E0F5",
    "#D9F0F0",
    "#FBE3D6",
    "#EDEDED",
)
CARPETA_REPORTES = (
    Path(__file__).resolve().parent.parent / "reportes_generados" / "docentes"
)


class VentanaMenuDocente(VentanaBase):
    def __init__(self, usuario, usuario_id, acceso_id=None):
        super().__init__("SIGEA - Portal docente", 1120, 720)
        self.usuario = usuario
        self.nombre_docente = usuario
        self.usuario_id = usuario_id
        self._acceso_id = acceso_id
        self._grupos = []
        self._datos_calificaciones = None
        self._datos_lista = None

        self._crear_interfaz()
        self._cargar_datos_iniciales()
        self.centrar_ventana()

    def _crear_interfaz(self):
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.setSpacing(20)

        self.barra_navegacion = QFrame()
        self.barra_navegacion.setObjectName("barraNavegacionDocente")
        self.barra_navegacion.setFixedWidth(238)
        self.barra_navegacion.setStyleSheet(f"""
            QFrame#barraNavegacionDocente {{
                background: {Config.FONDO_FORM};
                border: 1px solid {Config.FONDO_FORM_BORDE};
                border-radius: 18px;
            }}
        """)
        lateral = QVBoxLayout(self.barra_navegacion)
        lateral.setContentsMargins(12, 16, 12, 16)
        lateral.setSpacing(8)

        self._botones_navegacion = []
        opciones = (
            ("Inicio", "inicio.png"),
            ("Mis grupos", "iconogrupo.png"),
            ("Calificaciones", "iconocalificaciones.png"),
            ("Horario", "iconohorario.png"),
            ("Lista de alumnos", "iconolista.png"),
            ("Reportes", "archivo-pdf.png"),
        )
        for indice, (texto, archivo) in enumerate(opciones):
            boton = QPushButton(texto)
            boton.setCheckable(True)
            boton.setMinimumHeight(52)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setIconSize(QSize(25, 25))
            icono = ruta_recurso(archivo)
            if icono:
                boton.setIcon(QIcon(str(icono)))
            boton.setStyleSheet(f"""
                QPushButton {{
                    color: {Config.TEXTO_OSCURO};
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 12px;
                    padding: 8px 10px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Config.FONDO_TARJETA};
                    border-color: {Config.FONDO_FORM_BORDE};
                }}
                QPushButton:checked {{
                    color: white;
                    background: {Config.AZUL_ENTRAR};
                    border-color: {Config.AZUL_ENTRAR};
                }}
            """)
            boton.clicked.connect(
                lambda _=False, pagina=indice: self._mostrar_pagina(pagina)
            )
            lateral.addWidget(boton)
            self._botones_navegacion.append(boton)
        lateral.addStretch(1)
        lateral.addWidget(
            self.crear_boton_salida("Salir", self.salir, ancho=210, alto=42)
        )
        raiz.addWidget(self.barra_navegacion)

        principal = QVBoxLayout()
        principal.setContentsMargins(4, 0, 4, 0)
        principal.setSpacing(12)

        cabecera = QHBoxLayout()
        cabecera.addWidget(
            self.crear_label_titulo("Bienvenido docente", 26)
        )
        cabecera.addStretch()
        cabecera.addWidget(InsigniaUsuario(self.usuario), 0, Qt.AlignVCenter)
        principal.addLayout(cabecera)

        self.paginas = QStackedWidget()
        self.paginas.setStyleSheet(
            f"QStackedWidget {{ background: {Config.FONDO_FORM}; }}"
        )
        self.paginas.addWidget(self._crear_inicio())
        self.paginas.addWidget(self._crear_grupos())
        self.paginas.addWidget(self._crear_calificaciones())
        self.paginas.addWidget(self._crear_horario())
        self.paginas.addWidget(self._crear_lista())
        self.paginas.addWidget(self._crear_reportes())
        principal.addWidget(self.paginas, 1)
        self._mostrar_pagina(0)
        raiz.addLayout(principal, 1)

    def _crear_inicio(self):
        pagina, layout = self._crear_pagina("")
        layout.setContentsMargins(18, 18, 18, 18)

        tarjetas = QGridLayout()
        tarjetas.setHorizontalSpacing(16)
        tarjetas.setVerticalSpacing(16)
        tarjetas.setAlignment(Qt.AlignCenter)
        accesos = (
            ("Mis grupos", "Consulta los grupos que tienes asignados", 1, "iconogrupo.png"),
            ("Calificaciones", "Captura y modifica evaluaciones", 2, "iconocalificaciones.png"),
            ("Horario", "Consulta tu horario semanal de clases", 3, "iconohorario.png"),
            ("Lista de alumnos", "Consulta las listas de tus grupos", 4, "iconolista.png"),
            ("Reportes", "Genera listas y reportes de tus grupos", 5, "archivo-pdf.png"),
        )
        for posicion, (texto, detalle, indice, archivo) in enumerate(accesos):
            boton = QToolButton()
            boton.setText(texto)
            boton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            boton.setFixedSize(194, 184)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setIconSize(QSize(58, 58))
            boton.setToolTip(detalle)
            icono = ruta_recurso(archivo)
            if icono:
                boton.setIcon(QIcon(str(icono)))
            boton.setStyleSheet(f"""
                QToolButton {{
                    color: {Config.TEXTO_OSCURO};
                    background: {Config.FONDO_FORM};
                    border: 1px solid {Config.FONDO_FORM_BORDE};
                    border-radius: 16px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QToolButton:hover {{
                    border: 2px solid {Config.AZUL_FORM};
                    background: {Config.FONDO_TARJETA};
                }}
                QToolButton:pressed {{
                    background: {Config.AZUL_BRIGHT};
                }}
            """)
            boton.clicked.connect(
                lambda _=False, pagina_indice=indice:
                self._mostrar_pagina(pagina_indice)
            )
            tarjetas.addWidget(boton, posicion // 3, posicion % 3)
        layout.addStretch(1)
        layout.addLayout(tarjetas)
        layout.addStretch(1)
        return pagina

    def _crear_pagina(self, titulo, subtitulo=""):
        pagina = QWidget()
        pagina.setStyleSheet(
            f"QWidget {{ background: {Config.FONDO_FORM}; }}"
        )
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(10)
        if titulo:
            encabezado = QLabel(titulo)
            encabezado.setStyleSheet(
                "color: #102E57; font-size: 25px; font-weight: bold; "
                "background: transparent;"
            )
            layout.addWidget(encabezado)
        if subtitulo:
            descripcion = QLabel(subtitulo)
            descripcion.setWordWrap(True)
            descripcion.setStyleSheet(
                "color: #425D7B; font-size: 13px; background: transparent;"
            )
            layout.addWidget(descripcion)
        return pagina, layout

    def _crear_grupos(self):
        pagina, layout = self._crear_pagina(
            "MIS GRUPOS",
            "Estos son los grupos activos que tienes asignados.",
        )
        self.etiqueta_grupos = QLabel()
        self.etiqueta_grupos.setWordWrap(True)
        self.etiqueta_grupos.setStyleSheet(
            "color: #345B86; background: transparent; font-weight: bold;"
        )
        layout.addWidget(self.etiqueta_grupos)
        self.contenedor_grupos, self.lista_grupos = self._crear_lista_desplazable()
        layout.addWidget(self.contenedor_grupos, 1)
        return pagina

    def _crear_lista_desplazable(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        contenido = QWidget()
        contenido.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(2, 2, 8, 2)
        layout.setSpacing(10)
        layout.addStretch(1)
        area.setWidget(contenido)
        return area, layout

    @staticmethod
    def _limpiar_layout(layout):
        while layout.count():
            elemento = layout.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.deleteLater()

    def _crear_calificaciones(self):
        pagina, layout = self._crear_pagina(
            "CAPTURA DE CALIFICACIONES",
            "Captura las evaluaciones en orden, sin saltar ninguna. Acepta "
            "calificaciones de 70 a 100; las menores a 70 se guardan como 0. "
            "No se redondean (máximo dos decimales). La captura y corrección "
            "se cierran al iniciar la semana 17.",
        )
        self.grupo_calificaciones = self._crear_selector_grupo(
            layout, "Grupo y materia:"
        )
        self.grupo_calificaciones.currentIndexChanged.connect(
            self._cargar_calificaciones
        )

        fila = QHBoxLayout()
        etiqueta = QLabel("Evaluación:")
        etiqueta.setStyleSheet("color: #1E2A3A; font-weight: bold;")
        fila.addWidget(etiqueta)
        self.selector_unidad = QComboBox()
        self._estilizar_combo(self.selector_unidad)
        for unidad, semana in SEMANA_UNIDAD.items():
            self.selector_unidad.addItem(
                f"Evaluación {unidad} · Semana {semana}", unidad
            )
        self.selector_unidad.addItem(
            f"Promedio final · Semana {SEMANA_CIERRE}", "final"
        )
        self.selector_unidad.currentIndexChanged.connect(
            self._cargar_calificaciones
        )
        fila.addWidget(self.selector_unidad)
        fila.addStretch()
        layout.addLayout(fila)

        self.etiqueta_estado_calificaciones = QLabel()
        self.etiqueta_estado_calificaciones.setWordWrap(True)
        self.etiqueta_estado_calificaciones.setStyleSheet(
            "color: #173F6E; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self.etiqueta_estado_calificaciones)

        self.tabla_calificaciones = QTableWidget(
            0, 6
        )
        self.tabla_calificaciones.setHorizontalHeaderLabels(
            [
                "No. control",
                "Nombre",
                "Evaluación 1",
                "Evaluación 2",
                "Evaluación 3",
                "Final",
            ]
        )
        self.tabla_calificaciones.setAlternatingRowColors(True)
        self.tabla_calificaciones.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.tabla_calificaciones.setEditTriggers(QTableWidget.AllEditTriggers)
        self.tabla_calificaciones.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.tabla_calificaciones.horizontalHeader().setStretchLastSection(True)
        self.tabla_calificaciones.setStyleSheet("""
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
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.tabla_calificaciones, 1)

        botones = QHBoxLayout()
        botones.addStretch()
        actualizar = self._crear_boton_accion(
            "Actualizar", self._cargar_calificaciones
        )
        self.boton_guardar_calificaciones = self._crear_boton_accion(
            "Guardar evaluación", self._guardar_calificaciones
        )
        botones.addWidget(actualizar)
        botones.addWidget(self.boton_guardar_calificaciones)
        layout.addLayout(botones)
        return pagina

    def _crear_horario(self):
        pagina, layout = self._crear_pagina(
            "HORARIO",
            "Consulta en una sola vista los horarios de todas tus materias y grupos.",
        )
        self.etiqueta_horario = QLabel()
        self.etiqueta_horario.setWordWrap(True)
        self.etiqueta_horario.setStyleSheet(
            "color: #173F6E; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self.etiqueta_horario)

        self.tabla_horario = QTableWidget(0, len(DIAS_SEMANA) + 1)
        self.tabla_horario.setHorizontalHeaderLabels(
            ["Materia"] + [dia.capitalize() for dia in DIAS_SEMANA]
        )
        self.tabla_horario.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_horario.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_horario.setWordWrap(True)
        self.tabla_horario.setShowGrid(False)
        self.tabla_horario.verticalHeader().setVisible(False)
        self.tabla_horario.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        for columna in range(1, len(DIAS_SEMANA) + 1):
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
        self.tabla_horario.setAlternatingRowColors(False)
        layout.addWidget(self.tabla_horario, 1)
        return pagina

    def _crear_lista(self):
        pagina, layout = self._crear_pagina(
            "LISTA DE ALUMNOS",
            "Consulta los alumnos inscritos en tus grupos. Esta lista no muestra calificaciones.",
        )
        self.grupo_lista = self._crear_selector_grupo(
            layout, "Grupo y materia:"
        )
        self.grupo_lista.currentIndexChanged.connect(
            self._cambiar_grupo_lista
        )
        self.etiqueta_lista = QLabel()
        self.etiqueta_lista.setWordWrap(True)
        self.etiqueta_lista.setStyleSheet(
            "color: #173F6E; font-weight: bold; background: transparent;"
        )
        layout.addWidget(self.etiqueta_lista)
        self.lista_alumnos = QListWidget()
        self.lista_alumnos.setAlternatingRowColors(True)
        self.lista_alumnos.setSelectionMode(QListWidget.NoSelection)
        self.lista_alumnos.setStyleSheet("""
            QListWidget {
                color: #1E2A3A;
                background: white;
                alternate-background-color: #EDF3FD;
                border: 1px solid #C9D8EE;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item { padding: 8px 10px; }
        """)
        layout.addWidget(self.lista_alumnos, 1)
        return pagina

    def _crear_reportes(self):
        pagina, layout = self._crear_pagina(
            "REPORTES E IMPRESIÓN",
            "Genera una lista simple de alumnos o un reporte que incluya las evaluaciones y el promedio final.",
        )
        self.grupo_reportes = self._crear_selector_grupo(
            layout, "Grupo para el reporte:"
        )
        self.grupo_reportes.currentIndexChanged.connect(
            self._cambiar_grupo_reporte
        )

        opciones = QGridLayout()
        opciones.setSpacing(16)
        self.boton_pdf_lista = self._crear_boton_accion(
            "PDF · Lista de alumnos (sin calificaciones)",
            lambda: self._generar_pdf(incluir_calificaciones=False),
            "#E8F2FC",
        )
        self.boton_pdf_calificaciones = self._crear_boton_accion(
            "PDF · Lista con calificaciones",
            lambda: self._generar_pdf(incluir_calificaciones=True),
            "#E5F6F0",
        )
        for boton in (self.boton_pdf_lista, self.boton_pdf_calificaciones):
            boton.setMinimumHeight(92)
            boton.setStyleSheet(boton.styleSheet() + """
                QPushButton {
                    color: #123D70;
                    border: 1px solid #BDD2E9;
                    border-radius: 12px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { border: 2px solid #78A9DB; }
            """)
        opciones.addWidget(self.boton_pdf_lista, 0, 0)
        opciones.addWidget(self.boton_pdf_calificaciones, 0, 1)
        layout.addLayout(opciones)
        layout.addStretch(1)
        return pagina

    def _crear_selector_grupo(self, layout, texto):
        fila = QHBoxLayout()
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(
            "color: #1E2A3A; font-weight: bold; background: transparent;"
        )
        combo = QComboBox()
        self._estilizar_combo(combo)
        combo.setMinimumWidth(300)
        fila.addWidget(etiqueta)
        fila.addWidget(combo, 1)
        fila.addStretch(1)
        layout.addLayout(fila)
        return combo

    @staticmethod
    def _estilizar_combo(combo):
        combo.setMinimumHeight(40)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet("""
            QComboBox {
                color: #1E2A3A;
                background: white;
                border: 1px solid #B8C4D2;
                border-radius: 7px;
                padding: 6px 9px;
            }
            QComboBox QAbstractItemView { color: #1E2A3A; background: white; }
        """)

    @staticmethod
    def _crear_boton_accion(texto, funcion, color=None):
        boton = QPushButton(texto)
        boton.setCursor(Qt.PointingHandCursor)
        fondo = color or Config.AZUL_ENTRAR
        color_texto = "#123D70" if color else "white"
        boton.setStyleSheet(f"""
            QPushButton {{
                color: {color_texto};
                background: {fondo};
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 9px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ border-color: #73A7D8; }}
            QPushButton:disabled {{ color: #7A8796; background: #E1E5EA; }}
        """)
        boton.clicked.connect(funcion)
        return boton

    def _mostrar_pagina(self, indice):
        self.paginas.setCurrentIndex(indice)
        for numero, boton in enumerate(self._botones_navegacion):
            boton.setChecked(numero == indice)

    def _cargar_datos_iniciales(self):
        perfil, problema = obtener_perfil_docente(self.usuario_id)
        if problema:
            QMessageBox.warning(self, "Portal docente", problema)
            self.etiqueta_grupos.setText(
                "No fue posible verificar una cuenta docente activa."
            )
            self.paginas.setEnabled(False)
            return
        self.nombre_docente = perfil["nombre"]

        grupos, problema = listar_grupos_docente(self.usuario_id)
        if problema:
            QMessageBox.warning(self, "Portal docente", problema)
            self.etiqueta_grupos.setText(problema)
            return
        self._grupos = grupos
        self._llenar_grupos()

    def _llenar_grupos(self):
        combos = (
            self.grupo_calificaciones,
            self.grupo_lista,
            self.grupo_reportes,
        )
        for combo in combos:
            combo.blockSignals(True)
            combo.clear()
            for grupo in self._grupos:
                combo.addItem(
                    f"{grupo['clave']} · {grupo['materia']} · "
                    f"{grupo['periodo']} · Sem. {grupo['semestre']}",
                    grupo["grupo_id"],
                )
            combo.blockSignals(False)

        self.etiqueta_grupos.setText(
            f"Tienes {len(self._grupos)} grupo(s) activo(s) asignado(s)."
        )
        self._limpiar_layout(self.lista_grupos)
        if not self._grupos:
            self._agregar_mensaje_vacio(
                self.lista_grupos, "No tienes grupos activos asignados."
            )
        for grupo in self._grupos:
            self.lista_grupos.insertWidget(
                self.lista_grupos.count() - 1,
                self._crear_tarjeta_grupo(grupo),
            )

        self._cargar_calificaciones()
        self._cargar_horario()
        self._cargar_lista()

    def _crear_tarjeta_grupo(self, grupo):
        tarjeta = QFrame()
        tarjeta.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D0DEED;
                border-radius: 11px;
            }
            QLabel { color: #1E2A3A; background: transparent; border: none; }
        """)
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(16, 13, 16, 13)
        contenido = QVBoxLayout()
        titulo = QLabel(f"{grupo['materia']} · Grupo {grupo['clave']}")
        titulo.setStyleSheet(
            "color: #123D70; font-size: 16px; font-weight: bold;"
        )
        detalle = QLabel(
            f"Clave: {grupo['materia_clave']}  ·  Semestre: {grupo['semestre']}  ·  "
            f"Turno: {(grupo['turno'] or 'Sin turno').capitalize()}  ·  "
            f"Periodo: {grupo['periodo']}  ·  Aula: {grupo['aula'] or 'Sin aula'}"
        )
        detalle.setWordWrap(True)
        contenido.addWidget(titulo)
        contenido.addWidget(detalle)
        fila.addLayout(contenido, 1)
        boton = QPushButton("Subir calificaciones")
        boton.setCursor(Qt.PointingHandCursor)
        boton.setStyleSheet("""
            QPushButton {
                color: white; background: #126DB1; border: none;
                border-radius: 7px; padding: 8px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #0B528A; }
        """)
        boton.clicked.connect(
            lambda _=False, grupo_id=grupo["grupo_id"]:
            self._abrir_calificaciones_grupo(grupo_id)
        )
        fila.addWidget(boton)
        return tarjeta

    def _abrir_calificaciones_grupo(self, grupo_id):
        self._seleccionar_grupo(self.grupo_calificaciones, grupo_id)
        self._cargar_calificaciones()
        self._mostrar_pagina(2)

    @staticmethod
    def _seleccionar_grupo(combo, grupo_id):
        indice = combo.findData(grupo_id)
        if indice >= 0:
            combo.setCurrentIndex(indice)

    def _cambiar_grupo_lista(self, *_):
        grupo_id = self.grupo_lista.currentData()
        self._seleccionar_grupo(self.grupo_reportes, grupo_id)
        self._cargar_lista()

    def _cambiar_grupo_reporte(self, *_):
        grupo_id = self.grupo_reportes.currentData()
        self._seleccionar_grupo(self.grupo_lista, grupo_id)

    def _grupo_id(self, combo):
        return combo.currentData()

    @staticmethod
    def _texto_calificacion(valor):
        return "Pendiente" if valor is None else str(valor)

    def _cargar_calificaciones(self, *_):
        grupo_id = self._grupo_id(self.grupo_calificaciones)
        if grupo_id is None:
            self._datos_calificaciones = None
            self.tabla_calificaciones.setRowCount(0)
            self.etiqueta_estado_calificaciones.setText(
                "No tienes grupos activos asignados."
            )
            self.boton_guardar_calificaciones.setEnabled(False)
            return
        datos, problema = obtener_estado_calificaciones(
            self.usuario_id, grupo_id
        )
        if problema:
            self._datos_calificaciones = None
            self.etiqueta_estado_calificaciones.setText(problema)
            self.tabla_calificaciones.setRowCount(0)
            self.boton_guardar_calificaciones.setEnabled(False)
            return
        self._datos_calificaciones = datos
        estado = datos["estado"]
        unidad = self.selector_unidad.currentData()
        es_promedio_final = unidad == "final"
        disponible = (
            False if es_promedio_final else estado["disponibles"][unidad]
        )
        if es_promedio_final:
            estado_texto = f"Promedio final · Semana {SEMANA_CIERRE}"
        elif estado["cerrado"]:
            estado_texto = (
                "Captura cerrada desde la semana 17. Ya no se pueden "
                "modificar las calificaciones."
            )
        elif not disponible:
            evaluacion_previa = next(
                previa
                for previa in range(1, unidad)
                if not estado["completas"][previa]
            )
            estado_texto = (
                f"Completa la evaluación {evaluacion_previa} de todo el grupo "
                f"antes de capturar o corregir la evaluación {unidad}."
            )
        else:
            estado_texto = (
                f"Evaluación {unidad} seleccionada. Puedes capturar o corregir "
                "las calificaciones del grupo."
            )
        if not es_promedio_final and estado["final_generado"]:
            estado_texto += " La calificación final está disponible."
        elif not es_promedio_final and any(
            alumno["evaluaciones"][unidad - 1] is None
            for alumno in datos["alumnos"]
        ):
            estado_texto += (
                " El promedio final seguirá pendiente hasta completar "
                "las evaluaciones."
            )
        self.etiqueta_estado_calificaciones.setText(estado_texto)
        self._mostrar_calificaciones(
            datos["alumnos"],
            unidad,
            disponible and not estado["cerrado"],
            es_promedio_final or estado["final_generado"],
        )
        self.boton_guardar_calificaciones.setEnabled(
            (
                bool(datos["alumnos"])
                and all(estado["completas"].values())
                and not estado["promedio_guardado"]
            )
            if es_promedio_final
            else (
                bool(datos["alumnos"])
                and disponible
                and not estado["cerrado"]
            )
        )

    def _mostrar_calificaciones(self, alumnos, unidad, editable, final_generado):
        self.tabla_calificaciones.setRowCount(len(alumnos))
        for row, alumno in enumerate(alumnos):
            final = (
                self._texto_calificacion(alumno["final"])
                if final_generado
                else (
                    "Pendiente"
                    if self._datos_calificaciones["estado"]["semana"]
                    >= SEMANA_CIERRE
                    else "—"
                )
            )
            valores = [
                alumno["control"],
                alumno["nombre"],
                *[
                    self._texto_calificacion(valor)
                    for valor in alumno["evaluaciones"]
                ],
                final,
            ]
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if (
                    editable
                    and isinstance(unidad, int)
                    and columna == unidad + 1
                ):
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    if alumno["evaluaciones"][unidad - 1] is None:
                        item.setText("")
                self.tabla_calificaciones.setItem(row, columna, item)

    def _guardar_calificaciones(self):
        if self._datos_calificaciones is None:
            return
        if self.selector_unidad.currentData() == "final":
            correcto, mensaje = guardar_promedio_final(
                self.usuario_id,
                self._grupo_id(self.grupo_calificaciones),
            )
            if correcto:
                QMessageBox.information(self, "Calificaciones", mensaje)
                self._cargar_calificaciones()
                self._cargar_lista()
            else:
                QMessageBox.warning(self, "Calificaciones", mensaje)
            return
        unidad = self.selector_unidad.currentData()
        valores = {}
        for row, alumno in enumerate(self._datos_calificaciones["alumnos"]):
            item = self.tabla_calificaciones.item(row, unidad + 1)
            valores[alumno["control"]] = item.text() if item else ""
        correcto, mensaje = guardar_evaluacion(
            self.usuario_id,
            self._grupo_id(self.grupo_calificaciones),
            unidad,
            valores,
        )
        if correcto:
            QMessageBox.information(self, "Calificaciones", mensaje)
            self._cargar_calificaciones()
            self._cargar_lista()
        else:
            QMessageBox.warning(self, "Calificaciones", mensaje)

    def _cargar_horario(self, *_):
        self.tabla_horario.setRowCount(0)
        grupos, problema = obtener_horario_docente(self.usuario_id)
        if problema:
            self.etiqueta_horario.setText(problema)
            return
        if not grupos:
            self.etiqueta_horario.setText(
                "No tienes grupos activos asignados."
            )
            return

        self.tabla_horario.setRowCount(len(grupos))
        total_bloques = 0
        aliases_dia = {"miercoles": "miércoles"}
        for fila, grupo in enumerate(grupos):
            bloques_por_dia = {dia: [] for dia in DIAS_SEMANA}
            for dia, inicio, fin, aula in grupo["bloques"]:
                dia_normalizado = str(dia).strip().casefold()
                dia_normalizado = aliases_dia.get(dia_normalizado, dia_normalizado)
                if dia_normalizado in bloques_por_dia:
                    bloques_por_dia[dia_normalizado].append(
                        (inicio, fin, aula or grupo["aula"])
                    )

            total_bloques += sum(
                len(items) for items in bloques_por_dia.values()
            )
            color = QColor(COLORES_HORARIO[fila % len(COLORES_HORARIO)])
            materia = QTableWidgetItem(
                f"{grupo['materia_clave']} · {grupo['materia']}\n"
                f"Grupo: {grupo['clave']} · Semestre: {grupo['semestre']}\n"
                f"Periodo: {grupo['periodo']}"
            )
            materia.setToolTip(grupo["materia"])
            materia.setBackground(color)
            self.tabla_horario.setItem(fila, 0, materia)

            for columna, dia in enumerate(DIAS_SEMANA, start=1):
                bloques = bloques_por_dia[dia]
                texto = "\n".join(
                    f"{inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}"
                    for inicio, fin, _ in bloques
                )
                if bloques:
                    aulas = list(
                        dict.fromkeys(
                            aula for _, _, aula in bloques if aula
                        )
                    )
                    if aulas:
                        texto += "\n" + "\n".join(
                            f"Aula {aula}" for aula in aulas
                        )
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignCenter)
                if bloques:
                    celda.setBackground(color)
                    celda.setForeground(QColor("#1E2A3A"))
                self.tabla_horario.setItem(fila, columna, celda)

        self.tabla_horario.resizeRowsToContents()
        for fila in range(self.tabla_horario.rowCount()):
            self.tabla_horario.setRowHeight(
                fila, max(68, self.tabla_horario.rowHeight(fila))
            )
        self.etiqueta_horario.setText(
            f"{len(grupos)} materia(s)/grupo(s) · "
            f"{total_bloques} clase(s) programada(s)"
            if total_bloques
            else f"{len(grupos)} materia(s)/grupo(s) · "
            "No hay clases programadas."
        )

    def _cargar_lista(self, *_):
        grupo_id = self._grupo_id(self.grupo_lista)
        self._datos_lista = None
        self.lista_alumnos.clear()
        if grupo_id is None:
            self.etiqueta_lista.setText("No tienes grupos activos asignados.")
            self.lista_alumnos.addItem("No tienes grupos activos asignados.")
            return
        datos, problema = obtener_estado_calificaciones(
            self.usuario_id, grupo_id
        )
        if problema:
            self.etiqueta_lista.setText(problema)
            self.lista_alumnos.addItem(problema)
            return
        self._datos_lista = datos
        grupo = datos["grupo"]
        alumnos = datos["alumnos"]
        self.etiqueta_lista.setText(
            f"{grupo['materia']} · Grupo {grupo['clave']} · "
            f"Semestre {grupo['semestre']} · {grupo['periodo']} · "
            f"{len(alumnos)} alumno(s)"
        )
        if not alumnos:
            self.lista_alumnos.addItem("No hay alumnos inscritos en este grupo.")
            return
        for numero, alumno in enumerate(alumnos, 1):
            item = QListWidgetItem(
                f"{numero}.  {alumno['control']}  —  {alumno['nombre']}"
            )
            self.lista_alumnos.addItem(item)

    @staticmethod
    def _agregar_mensaje_vacio(layout, texto):
        etiqueta = QLabel(texto)
        etiqueta.setWordWrap(True)
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setStyleSheet(
            "color: #61758C; background: #FFFFFF; border: 1px dashed "
            "#B8C9DC; border-radius: 9px; padding: 18px;"
        )
        layout.insertWidget(layout.count() - 1, etiqueta)

    def _generar_pdf(self, incluir_calificaciones):
        grupo_id = self._grupo_id(self.grupo_reportes)
        if grupo_id is None:
            QMessageBox.information(
                self, "PDF", "Selecciona un grupo asignado."
            )
            return
        datos, problema = obtener_estado_calificaciones(
            self.usuario_id, grupo_id
        )
        if problema:
            QMessageBox.warning(self, "PDF", problema)
            return
        grupo = datos["grupo"]
        tipo = "calificaciones" if incluir_calificaciones else "alumnos"
        periodo = re.sub(r'[<>:"/\\|?*]+', "_", str(grupo["periodo"]))
        sugerido = (
            f"lista_{tipo}_{grupo['clave']}_{grupo['materia_clave']}_"
            f"{periodo}.pdf"
        )
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte del grupo",
            str(CARPETA_REPORTES / sugerido),
            "Documentos PDF (*.pdf)",
        )
        if not ruta:
            return

        alumnos = datos["alumnos"]
        if incluir_calificaciones:
            columnas = [
                "No. control",
                "Nombre completo",
                "Evaluación 1",
                "Evaluación 2",
                "Evaluación 3",
                "Final",
            ]
            filas = []
            for alumno in alumnos:
                evaluaciones = [
                    self._texto_calificacion(valor)
                    for valor in alumno["evaluaciones"]
                ]
                if datos["estado"]["final_generado"]:
                    final = self._texto_calificacion(alumno["final"])
                elif datos["estado"]["semana"] >= SEMANA_CIERRE:
                    final = "Pendiente"
                else:
                    final = "—"
                filas.append(
                    [alumno["control"], alumno["nombre"], *evaluaciones, final]
                )
            titulo = f"LISTA DE CALIFICACIONES · GRUPO {grupo['clave']}"
            anchos = [75, 235, 70, 70, 70, 55]
        else:
            columnas = ["No. control", "Nombre completo"]
            filas = [
                [alumno["control"], alumno["nombre"]]
                for alumno in alumnos
            ]
            titulo = f"LISTA DE ALUMNOS · GRUPO {grupo['clave']}"
            anchos = [110, 475]

        filtro = (
            f"Docente: {self.nombre_docente} · Materia: {grupo['materia']} "
            f"({grupo['materia_clave']}) · Grupo: {grupo['clave']} · "
            f"Semestre: {grupo['semestre']} · Periodo: {grupo['periodo']}"
        )
        try:
            generar_pdf_consulta(
                titulo,
                columnas,
                filas,
                ruta,
                anchos=anchos,
                filtro=filtro,
                resumen=(
                    f"Semestre: {grupo['semestre']} · "
                    f"Total de alumnos: {len(alumnos)}"
                ),
            )
        except (OSError, ValueError, LayoutError) as error:
            QMessageBox.critical(
                self, "PDF", f"No fue posible generar el documento:\n{error}"
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(ruta).resolve())))
        QMessageBox.information(
            self, "PDF", f"El documento se generó correctamente:\n{ruta}"
        )

    def salir(self):
        respuesta = QMessageBox.question(
            self,
            "Cerrar sesión",
            "¿Deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            self.close()

    def closeEvent(self, evento):
        if self._acceso_id is not None:
            correcto, problema = registrar_salida(self._acceso_id)
            if not correcto:
                QMessageBox.warning(self, "Bitácora de accesos", problema)
                evento.ignore()
                return
            self._acceso_id = None
        super().closeEvent(evento)
