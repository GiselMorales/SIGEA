from Logica import validaciones as v
from Logica.docentes import registrar_docente 
from ventanas.base_alta import VentanaAlta


class VentanaAltaDocente(VentanaAlta):

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
                self.fila(
                    self.campo("fecha_nacimiento", "Fecha de nacimiento (dd/mm/aaaa)"),
                    self.campo("curp", "CURP"),
                    self.campo("rfc", "RFC"),
                ),
                self.fila(
                    self.selector("sexo", "Sexo", v.SEXOS),
                    None,
                    pesos=(2, 3),
                ),
            ],
            lambda d: v.validar_datos_personales(
                d, edad_min=21, edad_max=75, pedir_rfc=True, pedir_sangre=False
            ),
        )

        self.agregar_seccion(
            "DATOS ACADÉMICOS",
            [
                self.fila(
                    self.selector("grado_academico", "Grado académico", v.GRADOS),
                    None,
                    pesos=(3, 2),
                ),
            ],
            self._validar_grado,
        )

    def _validar_grado(self, datos):
        grado = (datos.get("grado_academico") or "").strip()
        if grado not in v.GRADOS:
            return {"grado_academico": "Grado académico: elige una opción."}, {}
        return {}, {"grado_academico": grado}


    
    def resumen_confirmacion(self, datos):
        apellidos = f"{datos.get('apellido_paterno', '')} {datos.get('apellido_materno') or ''}".strip()
        lineas = [
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
            ("RFC", datos.get("rfc")),
            ("CURP", datos.get("curp")),
            ("Grado académico", datos.get("grado_academico")),
        ]
        aviso = (
            "Al registrar se crearán automáticamente:\n"
            "•  Nombre de usuario\n"
            "•  Contraseña inicial (se mostrará una sola vez al terminar)"
        )
        return lineas, aviso
 
    def guardar(self, datos):
        return registrar_docente(datos)