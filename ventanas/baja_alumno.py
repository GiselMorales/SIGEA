from Logica import validaciones as v
from Logica import gestion_alumnos as ga
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import destinos_barra


class VentanaBajaAlumno(VentanaAlta):
    INDICE_BARRA = 2                       # «Baja»
    DESTINOS_BARRA = destinos_barra()
    PREGUNTA_CONFIRMACION = "¿Seguro que deseas dar de baja a este alumno?"
    TEXTO_SI = "Sí, dar de baja"

    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Baja de alumno", "BAJA DE ALUMNO", "DAR DE BAJA", menu
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "ALUMNO",
            [self.fila(self.campo("clave", "Número de control o de ficha"), None, pesos=(1, 2))],
            self._validar_alumno,
            texto_boton="Buscar",
        )
        self.agregar_seccion(
            "CONFIRMACIÓN",
            [self.fila(self.campo("confirmacion", "Escribe BAJA para confirmar"), None, pesos=(1, 2))],
            self._validar_confirmacion,
        )

    def _validar_alumno(self, datos):
        errores, limpio = v.validar_numero(
            datos, "clave", "Número de control o de ficha", min_len=1, max_len=20
        )
        if errores:
            return errores, limpio

        alumno, problema = ga.obtener_alumno(limpio["clave"])
        if problema:
            return {"clave": problema}, {}
        if alumno is None:
            return {"clave": "No existe un alumno con ese número de control o de ficha."}, {}
        if alumno["estado_alumno"] == "egresado":
            return {"clave": "Ese alumno ya egresó; no se puede dar de baja."}, {}

        limpio["numero_control"] = alumno["numero_control"]
        limpio["alumno_nombre"] = alumno["nombre_completo"]
        limpio["alumno_semestre"] = alumno["semestre_actual"]
        limpio["alumno_estado"] = alumno["estado_alumno"]
        return {}, limpio

    def _validar_confirmacion(self, datos):
        if v.espacios(datos.get("confirmacion")).upper() != "BAJA":
            return {"confirmacion": "Escribe la palabra BAJA para confirmar."}, {}
        return {}, {"confirmacion": "BAJA"}

    def resumen_confirmacion(self, datos):
        lineas = [
            ("Alumno", datos.get("alumno_nombre")),
            ("Número de control", datos.get("numero_control")),
            ("Estatus actual", (datos.get("alumno_estado") or "").capitalize()),
            ("Semestre", str(datos.get("alumno_semestre") or "")),
        ]
        aviso = (
            "El alumno pasará a estatus BAJA y se cancelarán sus materias en curso.\n"
            "Su registro y sus documentos se conservan."
        )
        return lineas, aviso

    def guardar(self, datos):
        return ga.dar_de_baja(datos["numero_control"])
