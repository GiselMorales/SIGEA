from Logica import docentes as ld
from Logica import validaciones as v
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ORDEN_BARRA_DOCENTE, destinos_barra_docente


class VentanaModificarDocente(VentanaAlta):
    ORDEN_BARRA = ORDEN_BARRA_DOCENTE
    INDICE_BARRA = 2
    DESTINOS_BARRA = destinos_barra_docente()
    PREGUNTA_CONFIRMACION = "¿Guardar los cambios de este docente?"
    TEXTO_SI = "Sí, guardar cambios"

    def __init__(self, menu=None):
        self._docente = None
        super().__init__(
            "SIGEA - Modificar docente",
            "MODIFICAR DOCENTE",
            "GUARDAR CAMBIOS",
            menu,
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "DOCENTE A MODIFICAR",
            [
                self.fila(
                    self.campo("rfc_busqueda", "RFC del docente"),
                    None,
                    pesos=(1, 2),
                )
            ],
            self._validar_busqueda,
            texto_boton="Buscar",
        )
        self.agregar_seccion(
            "DATOS PERSONALES",
            [
                self.fila(
                    self.campo("apellido_paterno", "Apellido paterno"),
                    self.campo("apellido_materno", "Apellido materno"),
                    self.campo("nombre", "Nombre(s)"),
                ),
            ],
            self._validar_personales,
        )

    def _validar_busqueda(self, datos):
        mensaje, rfc = v._rfc(datos.get("rfc_busqueda"))
        if mensaje:
            return {"rfc_busqueda": mensaje}, {}

        docente, problema = ld.obtener_docente(rfc)
        if problema:
            return {"rfc_busqueda": problema}, {}
        if docente is None:
            return {"rfc_busqueda": "No existe un docente con ese RFC."}, {}

        self._docente = docente
        self._precargar(docente)
        return {}, {
            "rfc": docente["rfc"],
            "nombre_completo": docente["nombre_completo"],
        }

    def _precargar(self, docente):
        for clave in (
            "apellido_paterno", "apellido_materno", "nombre",
        ):
            self._lectores[clave][1].setText(str(docente.get(clave) or ""))

    def _validar_personales(self, datos):
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

        rfc = self._docente["rfc"] if self._docente else ""
        limpio["rfc"] = rfc
        return errores, limpio

    def resumen_confirmacion(self, datos):
        apellidos = " ".join(
            parte for parte in (
                datos.get("apellido_paterno"), datos.get("apellido_materno")
            ) if parte
        )
        return [
            ("RFC", datos.get("rfc")),
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
        ], "Se actualizarán los datos del docente seleccionado."

    def guardar(self, datos):
        return ld.actualizar_docente(datos)
