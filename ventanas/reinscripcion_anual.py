from ventanas.inscripcion import VentanaAltaInscripcion


class VentanaReinscripcionAnual(VentanaAltaInscripcion):

    def __init__(self, menu=None, numero_control=None):
        super().__init__(
            menu,
            ficha=numero_control,
            modo_reinscripcion_anual=True,
        )
