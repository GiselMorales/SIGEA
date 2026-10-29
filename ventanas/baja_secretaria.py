from Logica import validaciones as v
from Logica import secretaria as ls
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import destinos_barra_secretaria


class VentanaBajaSecretaria(VentanaAlta):
    INDICE_BARRA = 2
    DESTINOS_BARRA = destinos_barra_secretaria()
    PREGUNTA_CONFIRMACION = "¿Eliminar permanentemente esta secretaria y su cuenta?"
    TEXTO_SI = "Sí, eliminar"

    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Baja de secretaria", "BAJA DE SECRETARIA", "ELIMINAR SECRETARIA", menu
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "SECRETARIA",
            [self.fila(self.campo("rfc", "RFC de la secretaria"), None, pesos=(1, 2))],
            self._validar_secretaria,
            texto_boton="Buscar",
        )
        self.agregar_seccion(
            "CONFIRMACIÓN",
            [self.fila(self.campo("confirmacion", "Escribe ELIMINAR para confirmar"), None, pesos=(1, 2))],
            self._validar_confirmacion,
        )

    def _validar_secretaria(self, datos):
        mensaje, rfc = v._rfc(datos.get("rfc"))
        if mensaje:
            return {"rfc": mensaje}, {}

        secretaria, problema = ls.obtener_secretaria(rfc)
        if problema:
            return {"rfc": problema}, {}
        if secretaria is None:
            return {"rfc": "No existe una secretaria con ese RFC."}, {}

        usuario_activo = str(getattr(self.menu, "usuario", "")).casefold()
        if usuario_activo and secretaria["usuario"].casefold() == usuario_activo:
            return {
                "rfc": "No puedes eliminar la cuenta con la que iniciaste sesión."
            }, {}

        return {}, {
            "rfc": secretaria["rfc"],
            "nombre_completo": secretaria["nombre_completo"],
            "puesto": secretaria["puesto"],
            "usuario": secretaria["usuario"],
        }

    def _validar_confirmacion(self, datos):
        if v.espacios(datos.get("confirmacion")).upper() != "ELIMINAR":
            return {"confirmacion": "Escribe ELIMINAR para confirmar."}, {}
        return {}, {"confirmacion": "ELIMINAR"}

    def resumen_confirmacion(self, datos):
        lineas = [
            ("Secretaria", datos.get("nombre_completo")),
            ("RFC", datos.get("rfc")),
            ("Puesto", datos.get("puesto")),
            ("Usuario", datos.get("usuario")),
        ]
        return lineas, (
            "Esta operación elimina permanentemente el registro y la cuenta de acceso. "
            "No se puede deshacer."
        )

    def guardar(self, datos):
        return ls.dar_de_baja_secretaria(datos["rfc"])
