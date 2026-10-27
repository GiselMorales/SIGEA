from Logica import validaciones as v
from Logica import gestion_alumnos as ga
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import destinos_barra


class VentanaModificarAlumno(VentanaAlta):
    INDICE_BARRA = 3                       # «Modificar»
    DESTINOS_BARRA = destinos_barra()
    PREGUNTA_CONFIRMACION = "¿Seguro que deseas guardar los cambios de este alumno?"
    TEXTO_SI = "Sí, guardar cambios"

    # campos de texto que se llenan con los datos actuales del alumno
    CAMPOS = (
        "apellido_paterno", "apellido_materno", "nombre", "fecha_nacimiento", "curp",
        "tipo_sangre", "calle", "manzana", "lote", "colonia", "cp", "municipio",
        "estado", "pais", "telefono", "correo", "carrera", "escuela_procedencia",
        "promedio", "contacto_emergencia_nombre", "contacto_emergencia_parentesco",
        "contacto_emergencia_telefono",
    )

    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Modificar alumno", "MODIFICAR ALUMNO", "GUARDAR CAMBIOS", menu
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "ALUMNO A MODIFICAR",
            [self.fila(self.campo("clave", "Número de control o de ficha"), None, pesos=(1, 2))],
            self._validar_alumno,
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
                self.fila(
                    self.campo("fecha_nacimiento", "Fecha de nacimiento (dd/mm/aaaa)"),
                    self.campo("curp", "CURP"),
                    self.campo("tipo_sangre", "Tipo sanguíneo", v.TIPOS_SANGRE),
                    self.selector("sexo", "Sexo", v.SEXOS),
                    pesos=(14, 12, 8, 14),
                ),
            ],
            lambda d: v.validar_datos_personales(d, edad_min=15, edad_max=80),
        )

        self.agregar_seccion(
            "DOMICILIO",
            [
                self.fila(
                    self.campo("calle", "Calle"),
                    self.campo("manzana", "Manzana"),
                    self.campo("lote", "Lote"),
                    self.campo("colonia", "Colonia"),
                ),
                self.fila(
                    self.campo("cp", "Código postal"),
                    self.campo("municipio", "Municipio"),
                    self.campo("estado", "Estado", v.ESTADOS),
                    self.campo("pais", "País"),
                ),
            ],
            v.validar_domicilio,
        )

        self.agregar_seccion(
            "MEDIOS DE CONTACTO",
            [
                self.fila(
                    self.campo("telefono", "Teléfono (10 dígitos)"),
                    self.campo("correo", "Correo electrónico"),
                ),
            ],
            v.validar_contacto,
        )

        self.agregar_seccion(
            "ACADEMICOS",
            [
                self.fila(
                    self.campo("carrera", "Carrera", v.CARRERAS),
                    self.campo("escuela_procedencia", "Escuela de procedencia"),
                    self.campo("promedio", "Promedio de bachillerato"),
                    pesos=(3, 2, 1),
                ),
            ],
            v.validar_academico_alumno,
        )

        self.agregar_seccion(
            "CONTACTO DE EMERGENCIA",
            [
                self.fila(
                    self.campo("contacto_emergencia_nombre", "Nombre completo"),
                    self.campo("contacto_emergencia_parentesco", "Parentesco"),
                    pesos=(2, 1),
                ),
                self.fila(
                    self.campo("contacto_emergencia_telefono", "Teléfono de emergencia"),
                    None,
                    pesos=(1, 2),
                ),
            ],
            v.validar_emergencia,
        )

    # ------------------------------------------------------------------
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

        self._precargar(alumno)
        limpio["numero_control"] = alumno["numero_control"]
        limpio["alumno_nombre"] = alumno["nombre_completo"]
        return {}, limpio

    def _precargar(self, alumno):
        """Llena el formulario con los datos actuales; el usuario cambia lo que necesite."""
        for clave in self.CAMPOS:
            widget = self._lectores[clave][1]
            widget.setText(str(alumno.get(clave) or ""))
        if alumno.get("sexo") in v.SEXOS:
            self._lectores["sexo"][1].seleccionar(v.SEXOS.index(alumno["sexo"]))

    def resumen_confirmacion(self, datos):
        apellidos = f"{datos.get('apellido_paterno', '')} {datos.get('apellido_materno') or ''}".strip()
        lineas = [
            ("Número de control", datos.get("numero_control")),
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
            ("CURP", datos.get("curp")),
            ("Teléfono", datos.get("telefono")),
            ("Correo personal", datos.get("correo")),
        ]
        return lineas, "Se reemplazarán los datos actuales del alumno por los que capturaste."

    def guardar(self, datos):
        return ga.actualizar_alumno(datos)
