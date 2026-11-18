from Logica import validaciones as v
from Logica.docentes import registrar_docente 
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ORDEN_BARRA_DOCENTE, destinos_barra_docente


class VentanaAltaDocente(VentanaAlta):
    ORDEN_BARRA = ORDEN_BARRA_DOCENTE
    DESTINOS_BARRA = destinos_barra_docente()

    def __init__(self, menu=None):
        super().__init__("SIGEA - Alta de docente", "ALTA DE DOCENTE", "REGISTRAR DOCENTE", menu)

    def construir_secciones(self):
        self.agregar_seccion(
            "DATOS PERSONALES",
            [
                self.fila(
                    self.campo("apellido_paterno", "Apellido paterno"),
                    self.campo("apellido_materno", "Apellido materno"),
                    self.campo("nombre", "Nombre(s)"),
                ),
                self.fila(self.campo("rfc", "RFC"), None, pesos=(1, 2)),
            ],
            self._validar_docente,
        )

    @staticmethod
    def _validar_docente(datos):
        errores, limpio = {}, {}
        for clave, etiqueta, obligatorio in (
            ("apellido_paterno", "Apellido paterno", True),
            ("apellido_materno", "Apellido materno", False),
            ("nombre", "Nombre(s)", True),
        ):
            mensaje, valor = v._nombre(datos.get(clave), etiqueta, obligatorio)
            limpio[clave] = valor
            if mensaje:
                errores[clave] = mensaje
        mensaje, rfc = v._rfc(datos.get("rfc"))
        limpio["rfc"] = rfc
        if mensaje:
            errores["rfc"] = mensaje
        return errores, limpio

    def resumen_confirmacion(self, datos):
        apellidos = f"{datos.get('apellido_paterno', '')} {datos.get('apellido_materno') or ''}".strip()
        lineas = [
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
            ("RFC", datos.get("rfc")),
        ]
        aviso = (
            "Al registrar se crearán automáticamente:\n"
            "•  Nombre de usuario\n"
            "•  Contraseña inicial (se mostrará una sola vez al terminar)"
        )
        return lineas, aviso
 
    def guardar(self, datos):
        return registrar_docente(datos)