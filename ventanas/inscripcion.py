from Logica import validaciones as v
from Logica import inscripciones as li
from ventanas.base_alta import VentanaAlta


class VentanaAltaInscripcion(VentanaAlta):
    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Alta de inscripción", "ALTA DE INSCRIPCIÓN", "REGISTRAR INSCRIPCIÓN", menu
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "NÚMERO DE FICHA O DE CONTROL",
            [self.fila(self.campo("ficha", "Número de ficha / control"), None, pesos=(1, 2))],
            self._validar_alumno,
        )

        self.agregar_seccion(
            "DATOS DE LA INSCRIPCIÓN",
            [
                self.fila(
                    self.campo("periodo", "Periodo (ej. AGO-DIC 2026)", v.periodos_disponibles()),
                    self.selector("tipo_inscripcion", "Tipo de trámite", v.TIPOS_INSCRIPCION),
                    pesos=(1, 1),
                ),
                self.fila(
                    self.campo("carrera", "Carrera", v.CARRERAS),
                    self.campo("semestre", "Semestre", v.SEMESTRES),
                    self.campo("grupo", "Grupo"),
                    pesos=(4, 1, 1),
                ),
            ],
            v.validar_inscripcion,
        )

        self.agregar_seccion(
            "COMPROBANTES EN PDF",
            [self.zona_pdf("documentos")],
            lambda d: v.validar_documentos(
                d, minimo=1, etiqueta="Comprobantes (pago, horario...)"
            ),
        )

    def _validar_alumno(self, datos):
        # Acepta cualquier número (solo dígitos) y lo busca como control o como ficha.
        errores, limpio = v.validar_numero(
            datos, "ficha", "Número de ficha / control", min_len=1, max_len=20
        )
        if errores:
            return errores, limpio

        alumno, problema = li.buscar_alumno(limpio["ficha"])
        if problema:
            return {"ficha": problema}, {}
        if alumno is None:
            return {"ficha": "No existe un alumno con ese número de ficha o de control."}, {}

        limpio["numero_control"] = alumno["numero_control"]
        limpio["alumno_nombre"] = alumno["nombre"]
        return {}, limpio

    def resumen_confirmacion(self, datos):
        lineas = [
            ("Alumno", datos.get("alumno_nombre")),
            ("Número de control", datos.get("numero_control")),
            ("Trámite", datos.get("tipo_inscripcion")),
            ("Periodo", datos.get("periodo")),
            ("Semestre", datos.get("semestre")),
            ("PDF adjuntos", str(len(datos.get("documentos") or []))),
        ]
        return lineas, ""

    def guardar(self, datos):
        return li.registrar_tramite(datos)