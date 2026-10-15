
from logica import validaciones as v
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

    def buscar_alumno(self, ficha):
        return {}

    def _validar_alumno(self, datos):
        errores, limpio = v.validar_numero(datos, "ficha", "Número de ficha / control", 6, 10)
        if errores:
            return errores, limpio
        if self.buscar_alumno(limpio["ficha"]) is None:
            return {"ficha": "No existe un alumno registrado con esa ficha."}, {}
        return {}, limpio

    def guardar(self, datos):
        # TODO: guardar la inscripción en la base de datos (datos ya validados y normalizados).
        return super().guardar(datos)