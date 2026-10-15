from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt

from ventanas.ventana import VentanaBase, ruta_recurso
from ventanas.alta_alumno import VentanaAltaAlumno
from ventanas.alta_docente import VentanaAltaDocente
from ventanas.inscripcion import VentanaAltaInscripcion

class VentanaMenuAdmin(VentanaBase):
    def __init__(self):
        super().__init__("SIGEA - Menú del administrador", 980, 600)

        self.acciones = { 
            "ALUMNOS/Inscripciones": lambda: self._abrir(VentanaAltaInscripcion),
            "ALUMNOS/Inscripciones/Alta de alumno": lambda: self._abrir(VentanaAltaAlumno),
            "ALUMNOS/Reinscripciones/Alta de alumno": lambda: self._abrir(VentanaAltaInscripcion),
            "DOCENTE/Alta de docente": lambda: self._abrir(VentanaAltaDocente),
        }

        self.crear_interfaz()
        self.centrar_ventana()

    def crear_interfaz(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 32)
        layout.setSpacing(22)

        boton_salir = self.crear_boton_salida("Salir", self.salir, ancho=120, alto=40)
        layout.addWidget(
            self.crear_cabecera_menu("MENU", ruta_recurso("inicio.png"), boton_salir)
        )

        fila = QHBoxLayout()
        fila.setSpacing(24)

        tarjetas = [
            self.crear_tarjeta_menu(
                "ALUMNOS",
                [
                    "Consultas",
                    ("Inscripciones", ["Alta de alumno", "Baja de alumno", "Modificaciones"]),
                    ("Reinscripciones", ["Alta de alumno", "Baja de alumno", "Modificaciones"]),
                    "Constancias",
                ],
                ruta_recurso("alumnos.png"),
            ),
            self.crear_tarjeta_menu(
                "DOCENTE",
                ["Alta de docente", "Baja de docente", "Modificaciones", "Consultas"],
                ruta_recurso("docente.png"),
            ),
            self.crear_tarjeta_menu(
                "ESTADÍSTICAS",
                [
                    ("Generar gráfica", ["Total de alumnos", "Alumnos hombres", "Alumnas mujeres"]),
                    ("Generar archivo", ["PDF"]),
                ],
                ruta_recurso("estadisticas.png"),
            ),
        ]
        for tarjeta in tarjetas:
            tarjeta.seleccionado.connect(self.abrir_opcion)
            fila.addWidget(tarjeta, 1)        

        layout.addLayout(fila, 1)

    def abrir_opcion(self, ruta):
        accion = self.acciones.get(ruta)
        if accion:
            accion()
        else:
            self.mostrar_mensaje("SIGEA", f"Módulo en construcción:\n{ruta.replace('/', '  ›  ')}")

    def _abrir(self, clase_ventana):
        self._modulo = clase_ventana(self)
        self.hide()
        self._modulo.show()

    def salir(self):
        respuesta = QMessageBox.question(
            self, "SIGEA", "¿Deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            self.close()