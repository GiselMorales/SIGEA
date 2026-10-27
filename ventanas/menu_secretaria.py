from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox, QWidget
from PySide6.QtCore import Qt

import traceback

from ventanas.ventana import VentanaBase, ruta_recurso
from ventanas.componentes import InsigniaUsuario
from ventanas.alta_alumno import VentanaAltaAlumno
from ventanas.alta_docente import VentanaAltaDocente
from ventanas.inscripcion import VentanaAltaInscripcion
from ventanas.consulta_alumnos import VentanaConsultaAlumnos
from ventanas.grafica_alumnos import VentanaGrafica
from ventanas.alta_secretaria import VentanaAltaSecretaria

# Icono de cada opción: "RUTA DE LA OPCIÓN": "archivo.png" (dentro de la carpeta recursos).
# Si un archivo no existe, se avisa en la consola y la opción se muestra sin icono.
ICONOS_ALUMNOS = {
    "ALUMNOS/Consultas": "consulta-icono.png",
    "ALUMNOS/Inscripciones": "inscripcion-icono.png",
    "ALUMNOS/Inscripciones/Alta de alumno": "altaalumno-icono.png",
    "ALUMNOS/Inscripciones/Baja de alumno": "baja-icono.png",
    "ALUMNOS/Inscripciones/Modificaciones": "modificar-icono.png",
    "ALUMNOS/Reinscripciones": "reinscripciones.png",
    "ALUMNOS/Reinscripciones/Alta de alumno": "altaalumno-icono.png",
    "ALUMNOS/Reinscripciones/Baja de alumno": "baja-icono.png",
    "ALUMNOS/Reinscripciones/Modificaciones": "modificar-icono.png",
    "ALUMNOS/Constancias": "archivo-pdf.png",
}
ICONOS_DOCENTE = {
    "DOCENTE/Alta de docente": "altadocente-icono.png",
    "DOCENTE/Baja de docente": "bajadocente-icono.png",
    "DOCENTE/Modificaciones": "modificar-icono.png",
    "DOCENTE/Consultas": "consulta-icono.png",
}
ICONOS_ESTADISTICAS = {
    "ESTADÍSTICAS/Generar gráfica": "grafica-icono.png",
    "ESTADÍSTICAS/Generar gráfica/Total de alumnos": "grafica-icono.png",
    "ESTADÍSTICAS/Generar gráfica/Alumnos hombres": "hombre.png",
    "ESTADÍSTICAS/Generar gráfica/Alumnas mujeres": "chica.png",
    "ESTADÍSTICAS/Generar archivo": "archivo.png",
    "ESTADÍSTICAS/Generar archivo/PDF": "archivo-pdf.png",
}


class VentanaMenuAdmin(VentanaBase):

    def __init__(self, usuario=""):
        super().__init__("SIGEA - Menú del administrador", 980, 600)
        self.usuario = usuario or "Usuario"

        self.acciones = {
            "ALUMNOS/Consultas": lambda: self._abrir(VentanaConsultaAlumnos),
            "ALUMNOS/Inscripciones": lambda: self._abrir(VentanaAltaInscripcion),
            "ALUMNOS/Inscripciones/Alta de alumno": lambda: self._abrir(VentanaAltaAlumno),
            "ALUMNOS/Reinscripciones/Alta de alumno": lambda: self._abrir(VentanaAltaInscripcion),
            "DOCENTE/Alta de docente": lambda: self._abrir(VentanaAltaDocente),
            "ESTADÍSTICAS/Generar gráfica": lambda: self._abrir(VentanaGrafica),
            "ESTADÍSTICAS/Generar gráfica/Total de alumnos": lambda: self._abrir(VentanaGrafica, vista="total"),
            "ESTADÍSTICAS/Generar gráfica/Alumnos hombres": lambda: self._abrir(VentanaGrafica, vista="hombres"),
            "ESTADÍSTICAS/Generar gráfica/Alumnas mujeres": lambda: self._abrir(VentanaGrafica, vista="mujeres"),
            "SECRETARIA/Alta de secretaria": lambda: self._abrir(VentanaAltaSecretaria),
        }

        self.crear_interfaz()
        self.centrar_ventana()

    # ------------------------------------------------------------------
    def crear_interfaz(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 32)
        layout.setSpacing(22)

        # esquina superior derecha: [icono + nombre del usuario]  [Salir]
        boton_salir = self.crear_boton_salida("Salir", self.salir, ancho=120, alto=40)
        esquina = QWidget()
        esquina.setStyleSheet("background: transparent;")
        lay_esquina = QHBoxLayout(esquina)
        lay_esquina.setContentsMargins(0, 0, 0, 0)
        lay_esquina.setSpacing(14)
        lay_esquina.addWidget(InsigniaUsuario(self.usuario), 0, Qt.AlignVCenter)
        lay_esquina.addWidget(boton_salir, 0, Qt.AlignVCenter)

        layout.addWidget(
            self.crear_cabecera_menu("MENU", ruta_recurso("inicio.png"), esquina)
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
                iconos=ICONOS_ALUMNOS,
            ),
            self.crear_tarjeta_menu(
                "DOCENTE",
                ["Alta de docente", "Baja de docente", "Modificaciones", "Consultas"],
                ruta_recurso("docente.png"),
                iconos=ICONOS_DOCENTE,
            ),
            self.crear_tarjeta_menu(
                "ESTADÍSTICAS",
                [
                    ("Generar gráfica", ["Total de alumnos", "Alumnos hombres", "Alumnas mujeres"]),
                    ("Generar archivo", ["PDF"]),
                ],
                ruta_recurso("estadisticas.png"),
                iconos=ICONOS_ESTADISTICAS,
            ),
                        self.crear_tarjeta_menu(
                "SECRETARIA",
                ["Alta de secretaria", "Baja de secretaria", "Modificaciones", "Consultas"],
                ruta_recurso("secretaria.png"),
                iconos=ICONOS_DOCENTE,
            )
        ]
        for tarjeta in tarjetas:
            tarjeta.seleccionado.connect(self.abrir_opcion)
            fila.addWidget(tarjeta, 1)          # las tres con el mismo ancho y alto

        layout.addLayout(fila, 1)

    # ------------------------------------------------------------------
    def abrir_opcion(self, ruta):
        accion = self.acciones.get(ruta)
        if accion:
            accion()
        else:
            self.mostrar_mensaje("SIGEA", f"Módulo en construcción:\n{ruta.replace('/', '  ›  ')}")

    def _abrir(self, clase_ventana, **opciones):
        try:
            modulo = clase_ventana(self, **opciones)
        except Exception as e:
            traceback.print_exc()
            self.mostrar_mensaje("Error al abrir módulo", str(e))
            return
        self._modulo = clase_ventana(self, **opciones)
        self.hide()
        self._modulo.show()

    def salir(self):
        respuesta = QMessageBox.question(
            self, "SIGEA", "¿Deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            self.close()