import re
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
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
    QVBoxLayout,
    QWidget,
)
from reportlab.platypus.doctemplate import LayoutError

from Logica.bitacora import registrar_salida
from Logica.portal_docente import (
    SEMANA_CIERRE,
    SEMANA_UNIDAD,
    guardar_evaluacion,
    listar_grupos_docente,
    obtener_estado_calificaciones,
    obtener_horario_docente,
    obtener_perfil_docente,
)
from reportes.generador_pdf import generar_pdf_consulta
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
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        self.barra_lateral = QFrame()
        self.barra_lateral.setObjectName("barraLateral")
        self.barra_lateral.setFixedWidth(232)
        self.barra_lateral.setStyleSheet("""
            QFrame#barraLateral {
                background: #0B3768;
                border-right: 1px solid #174A7E;
            }
        """)
        lateral = QVBoxLayout(self.barra_lateral)
        lateral.setContentsMargins(11, 12, 11, 12)
        lateral.setSpacing(5)

        perfil = QVBoxLayout()
        perfil.setAlignment(Qt.AlignCenter)
        avatar = QLabel()
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background: #E8F2FC; border: 3px solid #FFFFFF; "
            "border-radius: 39px; color: #15518A; font-size: 30px;"
        )
        icono_usuario = ruta_recurso("iconosesion.png")
        if icono_usuario:
            avatar.setPixmap(
                QPixmap(str(icono_usuario)).scaled(
                    44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            avatar.setText(self.nombre_docente[:1].upper())
        nombre = QLabel(self.usuario)
        nombre.setAlignment(Qt.AlignCenter)
        nombre.setWordWrap(True)
        nombre.setStyleSheet(
            "color: white; font-size: 14px; font-weight: bold; "
            "background: transparent; padding-top: 6px;"
        )
        rol = QLabel("Docente")
        rol.setAlignment(Qt.AlignCenter)
        rol.setStyleSheet(
            "color: #D7E8F8; font-size: 12px; background: transparent;"
        )
        perfil.addWidget(avatar)
        perfil.addWidget(nombre)
        perfil.addWidget(rol)
        lateral.addLayout(perfil)

        separador = QFrame()
        separador.setFixedHeight(2)
        separador.setStyleSheet("background: #B7D5F2; border: none;")
        lateral.addSpacing(5)
        lateral.addWidget(separador)
        lateral.addSpacing(5)

        self._botones_navegacion = []
        opciones = (
            ("Inicio", "inicio.png", 0),
            ("Mis grupos", "altadocente-icono.png", 1),
            ("Captura de calificaciones", "archivo.png", 2),
            ("Horario", "consulta-icono.png", 3),
            ("Lista de alumnos", "consulta-icono.png", 4),
            ("Reportes e impresión", "archivo-pdf.png", 5),
        )
        for texto, archivo_icono, pagina in opciones:
            boton = self._crear_boton_navegacion(texto, archivo_icono)
            boton.clicked.connect(
                lambda _=False, indice=pagina: self._mostrar_pagina(indice)
            )
            lateral.addWidget(boton)
            self._botones_navegacion.append(boton)

        lateral.addStretch(1)
        separador_salida = QFrame()
        separador_salida.setFixedHeight(2)
        separador_salida.setStyleSheet("background: #B7D5F2; border: none;")
        lateral.addWidget(separador_salida)
        salir = self._crear_boton_navegacion("Cerrar sesión", "iconosesion.png")
        salir.clicked.connect(self.salir)
        lateral.addWidget(salir)
        raiz.addWidget(self.barra_lateral)

        contenido = QFrame()
        contenido.setObjectName("contenidoPrincipal")
        contenido.setStyleSheet(
            "QFrame#contenidoPrincipal { background: #F3F7FC; border: none; }"
        )
        principal = QVBoxLayout(contenido)
        principal.setContentsMargins(0, 0, 0, 0)
        principal.setSpacing(0)
        principal.addWidget(self._crear_membrete())

        self.paginas = QStackedWidget()
        self.paginas.setStyleSheet("QStackedWidget { background: #F3F7FC; }")
        self.paginas.addWidget(self._crear_inicio())
        self.paginas.addWidget(self._crear_grupos())
        self.paginas.addWidget(self._crear_calificaciones())
        self.paginas.addWidget(self._crear_horario())
        self.paginas.addWidget(self._crear_lista())
        self.paginas.addWidget(self._crear_reportes())
        principal.addWidget(self.paginas, 1)

        pie = QLabel("SIGEA · Sistema Integral de Gestión Escolar y Académica")
        pie.setAlignment(Qt.AlignCenter)
        pie.setStyleSheet(
            "color: #375477; background: #E4EDF8; padding: 9px; "
            "font-size: 11px; border-top: 1px solid #C5D6EB;"
        )
        principal.addWidget(pie)
        raiz.addWidget(contenido, 1)
        self._mostrar_pagina(0)

    def _crear_boton_navegacion(self, texto, archivo_icono):
        boton = QPushButton(texto)
        boton.setMinimumHeight(54)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setIconSize(QSize(26, 26))
        icono = ruta_recurso(archivo_icono)
        if icono:
            boton.setIcon(QIcon(str(icono)))
        boton.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 8px 12px;
                text-align: left;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #155E9E;
                border-color: #4B92CF;
            }
            QPushButton:checked {
                color: #102A4B;
                background: #E7F0FA;
                border-color: #C8D9EC;
            }
        """)
        return boton

    def _crear_membrete(self):
        marco = QFrame()
        marco.setMinimumHeight(126)
        marco.setMaximumHeight(136)
        marco.setStyleSheet(
            "QFrame { background: #E9F2FC; border: none; "
            "border-bottom: 4px solid #C5DDF4; }"
        )
        fila = QHBoxLayout(marco)
        fila.setContentsMargins(16, 8, 16, 8)
        fila.setSpacing(12)
        for archivo in ("Logotecnm300.png", "logo-ita300.png"):
            etiqueta = QLabel()
            etiqueta.setAlignment(Qt.AlignCenter)
            etiqueta.setFixedWidth(128)
            ruta = ruta_recurso(archivo)
            if ruta:
                etiqueta.setPixmap(
                    QPixmap(str(ruta)).scaled(
                        120, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
            fila.addWidget(etiqueta)

        linea = QFrame()
        linea.setFixedWidth(3)
        linea.setStyleSheet("background: #143F73; border: none;")
        fila.addWidget(linea)
        institucion = QVBoxLayout()
        institucion.setAlignment(Qt.AlignCenter)
        titulo = QLabel("Instituto Tecnológico de Acapulco")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            "color: #123D70; font-size: 20px; font-weight: bold; "
            "background: transparent;"
        )
        subtitulo = QLabel("Sistema Integral de Gestión Escolar y Académica")
        subtitulo.setAlignment(Qt.AlignCenter)
        subtitulo.setStyleSheet(
            "color: #345B86; font-size: 13px; background: transparent;"
        )
        institucion.addWidget(titulo)
        institucion.addWidget(subtitulo)
        fila.addLayout(institucion, 1)
        return marco

    def _crear_pagina(self, titulo, subtitulo=""):
        pagina = QWidget()
        pagina.setStyleSheet("QWidget { background: #F3F7FC; }")
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

    def _crear_inicio(self):
        pagina, layout = self._crear_pagina("")
        layout.setContentsMargins(28, 14, 28, 14)
        bienvenida = QLabel(f"Bienvenido(a), {self.usuario}")
        bienvenida.setAlignment(Qt.AlignCenter)
        bienvenida.setWordWrap(True)
        bienvenida.setStyleSheet(
            "color: #102E57; font-size: 23px; font-weight: bold; "
            "background: transparent;"
        )
        modulo = QLabel("Módulo de Docentes · SIGEA")
        modulo.setAlignment(Qt.AlignCenter)
        modulo.setStyleSheet(
            "color: #164A86; font-size: 16px; font-style: italic; "
            "background: transparent;"
        )
        layout.addWidget(bienvenida)
        layout.addWidget(modulo)

        aviso = QLabel(
            "Gestiona tus grupos, registra calificaciones y consulta tu "
            "horario de manera fácil y segura."
        )
        aviso.setWordWrap(True)
        aviso.setAlignment(Qt.AlignCenter)
        aviso.setStyleSheet("""
            QLabel {
                color: #123D70;
                background: #D9EAFB;
                border: 1px solid #9CC4EE;
                border-radius: 13px;
                padding: 11px 18px;
                font-size: 15px;
                font-weight: bold;
            }
        """)
        layout.addWidget(aviso)

        tarjetas = QGridLayout()
        tarjetas.setSpacing(14)
        accesos = (
            ("Mis grupos", "Consulta los grupos que tienes asignados", "#E8F2FC", 1, "altadocente-icono.png"),
            ("Captura de calificaciones", "Registra y modifica evaluaciones", "#E5F6F0", 2, "archivo.png"),
            ("Horario", "Consulta tu horario semanal de clases", "#F0ECFA", 3, "consulta-icono.png"),
            ("Lista de alumnos", "Consulta e imprime las listas de tus grupos", "#FFF3E5", 4, "archivo-pdf.png"),
        )
        for posicion, (texto, detalle, color, indice, archivo) in enumerate(accesos):
            boton = QPushButton(f"{texto}\n\n{detalle}")
            boton.setMinimumHeight(122)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setIconSize(QSize(42, 42))
            ruta = ruta_recurso(archivo)
            if ruta:
                boton.setIcon(QIcon(str(ruta)))
            boton.setStyleSheet(f"""
                QPushButton {{
                    color: #102E57;
                    background: {color};
                    border: 1px solid #C6D9EE;
                    border-radius: 13px;
                    padding: 11px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid #78A9DB;
                    background: #FFFFFF;
                }}
            """)
            boton.clicked.connect(
                lambda _=False, pagina_indice=indice:
                self._mostrar_pagina(pagina_indice)
            )
            tarjetas.addWidget(boton, posicion // 2, posicion % 2)
        layout.addLayout(tarjetas, 1)
        return pagina

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
            "Captura o corrige la evaluación habilitada para el grupo seleccionado.",
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
        self.tabla_calificaciones.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
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
            boton.setCheckable(True)
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
        boton = QPushButton("Ver horario completo")
        boton.setCursor(Qt.PointingHandCursor)
        boton.setStyleSheet("""
            QPushButton {
                color: white; background: #126DB1; border: none;
                border-radius: 7px; padding: 8px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #0B528A; }
        """)
        boton.clicked.connect(self._abrir_horario_completo)
        fila.addWidget(boton)
        return tarjeta

    def _abrir_horario_completo(self):
        self._cargar_horario()
        self._mostrar_pagina(3)

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
        semana_apertura = SEMANA_UNIDAD[unidad]
        if estado["cerrado"]:
            estado_texto = (
                "Captura cerrada. Las evaluaciones ya no se pueden modificar."
            )
        elif estado["semana"] < semana_apertura:
            estado_texto = (
                f"Evaluación {unidad}: se habilita en la semana "
                f"{semana_apertura}."
            )
        elif not all(
            estado["completas"][n] for n in range(1, unidad)
        ):
            estado_texto = (
                f"Completa la(s) evaluación(es) anterior(es) de todo el grupo "
                f"antes de capturar la evaluación {unidad}."
            )
        else:
            estado_texto = (
                f"Semana del periodo: {estado['semana']}. "
                f"Evaluación {unidad} habilitada para captura o corrección."
            )
        if estado["final_generado"]:
            estado_texto += " La calificación final está disponible."
        elif estado["semana"] >= SEMANA_CIERRE:
            estado_texto += (
                " El promedio final queda pendiente mientras falten evaluaciones."
            )
        self.etiqueta_estado_calificaciones.setText(estado_texto)
        self._mostrar_calificaciones(
            datos["alumnos"],
            unidad,
            estado["disponibles"][unidad] and not estado["cerrado"],
            estado["final_generado"],
        )
        self.boton_guardar_calificaciones.setEnabled(
            bool(datos["alumnos"])
            and estado["disponibles"][unidad]
            and not estado["cerrado"]
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
                if columna == unidad + 1 and editable:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    if alumno["evaluaciones"][unidad - 1] is None:
                        item.setText("")
                self.tabla_calificaciones.setItem(row, columna, item)

    def _guardar_calificaciones(self):
        if self._datos_calificaciones is None:
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
