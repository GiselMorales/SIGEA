from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout,
)

from Logica.constancias import obtener_datos_constancia
from reportes.generador_pdf import generar_pdf_constancia
from ventanas.componentes import (
    ORDEN_BARRA_CONSTANCIAS, destinos_barra_constancias, navegar_a, opciones_barra,
)
from ventanas.ventana import Config, VentanaBase

CARPETA_SALIDA = (
    Path(__file__).resolve().parent.parent / "reportes_generados"
)


class VentanaConstanciaEstudios(VentanaBase):
    ORDEN_BARRA = ORDEN_BARRA_CONSTANCIAS
    INDICE_BARRA = 7
    DESTINOS_BARRA = destinos_barra_constancias()

    def __init__(self, menu=None):
        super().__init__("SIGEA - Constancia de estudios", 1000, 650)
        self.menu = menu
        self._navegando = False
        self._alumno = None
        self._crear_interfaz()
        self.centrar_ventana()

    def _crear_interfaz(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 22, 28, 24)
        raiz.setSpacing(16)

        encabezado = QHBoxLayout()
        encabezado.addWidget(self.crear_label_titulo("CONSTANCIA DE ESTUDIOS", 28))
        encabezado.addStretch()
        encabezado.addWidget(
            self.crear_boton_salida("Menú", self.close, ancho=120, alto=40)
        )
        raiz.addLayout(encabezado)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(18)
        self._barra = self.crear_barra_vertical(
            opciones_barra(self.close, orden=self.ORDEN_BARRA)
        )
        self._barra.seleccionado.connect(self._navegar)
        cuerpo.addWidget(self._barra, 0, Qt.AlignTop)

        contenido = QVBoxLayout()
        contenido.setSpacing(14)
        intro = self.crear_label_campo(
            "Busca al alumno por número de control y descarga la constancia "
            "sin calificaciones o con sus evaluaciones actuales."
        )
        intro.setWordWrap(True)
        contenido.addWidget(intro)

        tarjeta_busqueda = self.crear_tarjeta(740, 96, 18)
        fila = QHBoxLayout(tarjeta_busqueda)
        fila.setContentsMargins(18, 12, 18, 12)
        fila.setSpacing(12)
        self.numero_control = QLineEdit()
        self.numero_control.setPlaceholderText("Número de control")
        self.numero_control.setStyleSheet(
            f"QLineEdit {{ background: white; color: {Config.TEXTO_OSCURO}; "
            f"border: 1px solid {Config.FONDO_FORM_BORDE}; border-radius: 10px; "
            "padding: 10px; font-size: 13px; }"
        )
        self.numero_control.returnPressed.connect(self.consultar)
        fila.addWidget(self.numero_control, 1)
        fila.addWidget(self.crear_boton("Consultar", self.consultar, 150, 44))
        contenido.addWidget(tarjeta_busqueda)

        self.info_alumno = QLabel("Ingresa un número de control para consultar.")
        self.info_alumno.setWordWrap(True)
        self.info_alumno.setStyleSheet(
            f"color: {Config.TEXTO_CLARO}; font-size: 13px; background: transparent;"
        )
        contenido.addWidget(self.info_alumno)
        self.lista_materias = QLabel("")
        self.lista_materias.setWordWrap(True)
        self.lista_materias.setStyleSheet(
            f"color: {Config.TEXTO_CLARO}; font-size: 12px; background: transparent;"
        )
        contenido.addWidget(self.lista_materias)
        contenido.addStretch(1)

        acciones = QHBoxLayout()
        acciones.addStretch()
        self.boton_sin_calificaciones = self.crear_boton(
            "Descargar sin calificaciones",
            lambda: self.descargar(False),
            250,
            48,
        )
        self.boton_con_calificaciones = self.crear_boton(
            "Descargar con calificaciones",
            lambda: self.descargar(True),
            250,
            48,
        )
        for boton in (
            self.boton_sin_calificaciones,
            self.boton_con_calificaciones,
        ):
            boton.setEnabled(False)
            acciones.addWidget(boton)
        acciones.addStretch()
        contenido.addLayout(acciones)

        cuerpo.addLayout(contenido, 1)
        raiz.addLayout(cuerpo, 1)
        self._barra.seleccionar(self.INDICE_BARRA)

    def consultar(self):
        control = self.numero_control.text().strip()
        if not control:
            QMessageBox.information(
                self, "Constancia", "Escribe el número de control del alumno."
            )
            self.numero_control.setFocus()
            return

        alumno, problema = obtener_datos_constancia(control)
        if problema:
            QMessageBox.warning(self, "Consulta de alumno", problema)
            self._alumno = None
            self.info_alumno.setText(problema)
            self.lista_materias.clear()
            self._actualizar_estado()
            return

        self._alumno = alumno
        self.info_alumno.setText(
            f"{alumno['nombre']}\n"
            f"Número de control: {alumno['numero_control']}  •  "
            f"Carrera: {alumno['carrera']}  •  "
            f"Semestre: {alumno['semestre_actual'] or '-'}  •  "
            f"Turno: {alumno['turno'] or '-'}  •  "
            f"Estatus: {alumno['estado'] or '-'}"
        )
        materias = alumno["materias"]
        if materias:
            lista = "\n".join(
                f"• {m['periodo']} · Semestre {m['semestre']} · "
                f"{m['clave']} {m['materia']} (Grupo {m['grupo']})"
                for m in materias
            )
            self.lista_materias.setText(
                "Materias actualmente inscritas:\n" + lista
            )
        else:
            self.lista_materias.setText(
                "El alumno no tiene materias inscritas actualmente."
            )
        self._actualizar_estado()

    def _actualizar_estado(self):
        habilitado = self._alumno is not None
        self.boton_sin_calificaciones.setEnabled(habilitado)
        self.boton_con_calificaciones.setEnabled(habilitado)

    def descargar(self, incluir_calificaciones):
        if self._alumno is None:
            QMessageBox.information(
                self, "Constancia", "Primero consulta un alumno."
            )
            return

        try:
            CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"No se pudo crear la carpeta de constancias: {error}")
            QMessageBox.warning(
                self, "Error", "No se pudo preparar la carpeta para guardar la constancia."
            )
            return
        tipo = "con_calificaciones" if incluir_calificaciones else "sin_calificaciones"
        sugerido = CARPETA_SALIDA / (
            f"constancia_{self._alumno['numero_control']}_{tipo}_"
            f"{datetime.now():%Y%m%d_%H%M%S}.pdf"
        )
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar constancia", str(sugerido), "Documento PDF (*.pdf)"
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        try:
            generar_pdf_constancia(
                self._alumno, ruta, incluir_calificaciones
            )
            QMessageBox.information(
                self,
                "Constancia generada",
                f"El documento se guardó correctamente en:\n{ruta}",
            )
        except Exception as error:
            print(f"Error al generar la constancia: {error}")
            QMessageBox.warning(
                self, "Error", "No fue posible generar la constancia."
            )

    def _navegar(self, indice, texto):
        if indice in (0, self.INDICE_BARRA):
            return
        destino = self.DESTINOS_BARRA.get(indice)
        if destino:
            navegar_a(self, destino)
        else:
            self.mostrar_mensaje(texto, "Esta opción aún está en construcción.")
            self._barra.seleccionar(self.INDICE_BARRA)

    def closeEvent(self, evento):
        if self.menu is not None and not self._navegando:
            self.menu.show()
        super().closeEvent(evento)
