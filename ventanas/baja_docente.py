from Logica import docentes as ld
from Logica import validaciones as v
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ORDEN_BARRA_DOCENTE, destinos_barra_docente


class VentanaBajaDocente(VentanaAlta):
    ORDEN_BARRA = ORDEN_BARRA_DOCENTE
    INDICE_BARRA = 2
    DESTINOS_BARRA = destinos_barra_docente()
    PREGUNTA_CONFIRMACION = "¿Desactivar este docente y su cuenta de acceso?"
    TEXTO_SI = "Sí, dar de baja"

    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Baja de docente", "BAJA DE DOCENTE", "DAR DE BAJA", menu
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "DOCENTE",
            [self.fila(self.campo("rfc", "RFC del docente"), None, pesos=(1, 2))],
            self._validar_docente,
            texto_boton="Buscar",
        )
        self.agregar_seccion(
            "CONFIRMACIÓN",
            [
                self.fila(
                    self.campo("confirmacion", "Escribe BAJA para confirmar"),
                    None,
                    pesos=(1, 2),
                )
            ],
            self._validar_confirmacion,
        )

    def _validar_docente(self, datos):
        mensaje, rfc = v._rfc(datos.get("rfc"))
        if mensaje:
            return {"rfc": mensaje}, {}
        return {
            "rfc": (
                "La baja está deshabilitada porque la base de datos no tiene "
                "un campo de estado para bloquear el acceso."
            )
        }, {}

    def _validar_confirmacion(self, datos):
        if v.espacios(datos.get("confirmacion")).upper() != "BAJA":
            return {"confirmacion": "Escribe BAJA para confirmar."}, {}
        return {}, {"confirmacion": "BAJA"}

    def resumen_confirmacion(self, datos):
        return [
            ("Docente", datos.get("nombre_completo")),
            ("RFC", datos.get("rfc")),
            ("Usuario", datos.get("usuario")),
        ], "La baja no está disponible con el esquema actual."

    def guardar(self, datos):
        return ld.dar_de_baja_docente(
            datos["rfc"], getattr(self.menu, "usuario", "")
        )
