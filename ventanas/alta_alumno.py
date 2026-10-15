from logica import validaciones as v
from logica import alumnos as la
from ventanas.base_alta import VentanaAlta

class VentanaAltaAlumno(VentanaAlta):
    def __init__(self, menu=None):
        super().__init__("SIGEA - Alta de alumno", "ALTA DE ALUMNO", "REGISTRAR ALUMNO", menu)

    def construir_secciones(self):
        self.agregar_seccion(
            "NÚMERO DE FICHA",
            [self.fila(self.campo("ficha", "Número de ficha"), None, pesos=(1, 2))],
            lambda d: v.validar_numero(d, "ficha", "Número de ficha", 6, 10),
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
                    pesos=(3,  2, 1),
                ),
            ],
            v.validar_academico_alumno,
        )
        
        self.agregar_seccion(
            "DATOS DE ADMISIÓN",
            [
                self.fila(
                    self.campo("puntaje_examen_admision", "Puntaje del examen de admisión"),
                ),
            ],
            v.validar_puntaje_admision,
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

        self.agregar_seccion(
            "SUBIR ARCHIVOS EN PDF",
            [self.zona_pdf("documentos")],
            lambda d: v.validar_documentos(
                d, minimo=1, etiqueta="Documentos (acta, CURP, certificado...)"
            ),
        )


    def resumen_confirmacion(self, datos):
        apellidos = f"{datos.get('apellido_paterno', '')} {datos.get('apellido_materno') or ''}".strip()
        lineas = [
            ("Número de ficha", datos.get("ficha")),
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
            ("CURP", datos.get("curp")),
            ("Carrera", datos.get("carrera")),
            ("Correo personal", datos.get("correo")),
        ]
        aviso = (
            "Al registrar se crearán automáticamente:\n"
            "•  Número de control\n"
            "•  Correo institucional (l<número de control>@acapulco.tecnm.mx)"
        )
        return lineas, aviso
    
    def guardar(self, datos):
        return la.registrar_alumno(datos)