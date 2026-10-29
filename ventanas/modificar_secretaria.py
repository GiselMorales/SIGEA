from datetime import date

from Logica import validaciones as v
from Logica import secretaria as ls
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import destinos_barra_secretaria


class VentanaModificarSecretaria(VentanaAlta):
    INDICE_BARRA = 3
    DESTINOS_BARRA = destinos_barra_secretaria()
    PREGUNTA_CONFIRMACION = "¿Guardar los cambios de esta secretaria?"
    TEXTO_SI = "Sí, guardar cambios"

    def __init__(self, menu=None):
        self._secretaria = None
        super().__init__(
            "SIGEA - Modificar secretaria",
            "MODIFICAR SECRETARIA",
            "GUARDAR CAMBIOS",
            menu,
        )

    def construir_secciones(self):
        self.agregar_seccion(
            "SECRETARIA A MODIFICAR",
            [self.fila(self.campo("rfc_busqueda", "RFC de la secretaria"), None, pesos=(1, 2))],
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
                self.fila(
                    self.campo("fecha_nacimiento", "Fecha de nacimiento (dd/mm/aaaa)"),
                    self.campo("curp", "CURP (opcional)"),
                    self.selector("sexo", "Sexo", v.SEXOS),
                ),
            ],
            self._validar_personales,
        )
        self.agregar_seccion(
            "DATOS DEL PUESTO",
            [
                self.fila(
                    self.selector(
                        "grado_academico",
                        "Grado académico",
                        ["Sin especificar", *v.GRADOS],
                    ),
                    self.selector("puesto", "Puesto", v.PUESTOS_SECRETARIA),
                ),
            ],
            self._validar_puesto,
        )

    def _validar_busqueda(self, datos):
        mensaje, rfc = v._rfc(datos.get("rfc_busqueda"))
        if mensaje:
            return {"rfc_busqueda": mensaje}, {}

        secretaria, problema = ls.obtener_secretaria(rfc)
        if problema:
            return {"rfc_busqueda": problema}, {}
        if secretaria is None:
            return {"rfc_busqueda": "No existe una secretaria con ese RFC."}, {}

        self._secretaria = secretaria
        self._precargar(secretaria)
        return {}, {
            "rfc": secretaria["rfc"],
            "nombre_completo": secretaria["nombre_completo"],
        }

    def _precargar(self, secretaria):
        for clave in (
            "apellido_paterno", "apellido_materno", "nombre",
            "fecha_nacimiento", "curp",
        ):
            self._lectores[clave][1].setText(str(secretaria.get(clave) or ""))

        if secretaria["sexo"] in v.SEXOS:
            self._lectores["sexo"][1].seleccionar(v.SEXOS.index(secretaria["sexo"]))

        grados = ["Sin especificar", *v.GRADOS]
        grado = secretaria.get("grado_academico") or "Sin especificar"
        if grado in grados:
            self._lectores["grado_academico"][1].seleccionar(grados.index(grado))

        if secretaria["puesto"] in v.PUESTOS_SECRETARIA:
            self._lectores["puesto"][1].seleccionar(
                v.PUESTOS_SECRETARIA.index(secretaria["puesto"])
            )

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

        fecha_texto = v.espacios(datos.get("fecha_nacimiento"))
        fecha = None
        if fecha_texto:
            mensaje, fecha, fecha_formateada = v._fecha(
                fecha_texto, "Fecha de nacimiento", 0, 120
            )
            limpio["fecha_nacimiento"] = fecha_formateada
            if mensaje:
                errores["fecha_nacimiento"] = mensaje
        else:
            limpio["fecha_nacimiento"] = ""
        limpio["fecha_nacimiento_iso"] = fecha.isoformat() if fecha else None

        curp_texto = v.espacios(datos.get("curp"))
        if curp_texto:
            mensaje, curp = v._curp(curp_texto)
            limpio["curp"] = curp
            if mensaje:
                errores["curp"] = mensaje
        else:
            curp = ""
            limpio["curp"] = None

        sexo = v.espacios(datos.get("sexo"))
        limpio["sexo"] = sexo
        if sexo not in v.SEXOS:
            errores["sexo"] = "Sexo: elige Mujer u Hombre."

        if curp and "curp" not in errores:
            if fecha:
                siglo = 1900 if curp[16].isdigit() else 2000
                fecha_curp = date(
                    siglo + int(curp[4:6]), int(curp[6:8]), int(curp[8:10])
                )
                if fecha_curp != fecha:
                    errores["curp"] = (
                        "CURP: la fecha que contiene no coincide con la fecha de nacimiento."
                    )
            if sexo in v.SEXOS:
                sexo_curp = "M" if sexo == "Mujer" else "H"
                if curp[10] in "HM" and curp[10] != sexo_curp:
                    errores["curp"] = (
                        f"CURP: indica sexo '{curp[10]}', pero elegiste {sexo}."
                    )

        rfc = self._secretaria["rfc"] if self._secretaria else ""
        if fecha and rfc[4:10] != fecha.strftime("%y%m%d"):
            errores["fecha_nacimiento"] = (
                "La fecha de nacimiento debe coincidir con la fecha de su RFC."
            )
        limpio["rfc"] = rfc
        return errores, limpio

    def _validar_puesto(self, datos):
        errores, limpio = {}, {}
        grado = v.espacios(datos.get("grado_academico"))
        puesto = v.espacios(datos.get("puesto"))

        if grado == "Sin especificar":
            limpio["grado_academico"] = None
        elif grado in v.GRADOS:
            limpio["grado_academico"] = grado
        else:
            errores["grado_academico"] = "Grado académico: elige una opción."

        if puesto not in v.PUESTOS_SECRETARIA:
            errores["puesto"] = "Puesto: elige una opción."
        else:
            limpio["puesto"] = puesto
        return errores, limpio

    def resumen_confirmacion(self, datos):
        apellidos = " ".join(
            parte for parte in (
                datos.get("apellido_paterno"), datos.get("apellido_materno")
            ) if parte
        )
        lineas = [
            ("RFC", datos.get("rfc")),
            ("Nombre(s)", datos.get("nombre")),
            ("Apellidos", apellidos),
            ("CURP", datos.get("curp")),
            ("Puesto", datos.get("puesto")),
            ("Grado académico", datos.get("grado_academico") or "Sin especificar"),
        ]
        return lineas, "Se actualizarán los datos de la secretaria seleccionada."

    def guardar(self, datos):
        return ls.actualizar_secretaria(datos)
