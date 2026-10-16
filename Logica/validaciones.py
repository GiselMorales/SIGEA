import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

CARRERAS = ["Ingeniería en Sistemas Computacionales"]
TIPOS_SANGRE = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SEXOS = ["Mujer", "Hombre"]
GRADOS = ["Licenciatura", "Maestría", "Doctorado"]
CONTRATACIONES = ["Tiempo completo", "Medio tiempo", "Por horas"]
TIPOS_INSCRIPCION = ["Inscripción", "Reinscripción"]
SEMESTRES = [str(n) for n in range(1, 13)]
ESTADOS = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango",
    "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco",
    "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
    "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora",
    "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]
PAISES = ["México"]
SEMESTRE_INICIAL = 1        # todo alumno de nuevo ingreso empieza en 1er semestre
PUNTAJE_MATUTINO = 90       # puntaje de admisión mínimo para turno matutino
PDF_MAX_MB = 5          # tamaño máximo por archivo
PDF_MAX_ARCHIVOS = 5    # cuántos PDF se pueden subir como máximo

#Herramientas de validación de datos (para alta de alumnos, docentes, inscripciones, etc.)
def espacios(texto):
    return re.sub(r"\s+", " ", (texto or "").strip())
def sin_acentos(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )

def turno_por_puntaje(puntaje):
    """Matutino si el puntaje del examen de admisión es >= 90; en otro caso, Vespertino."""
    return "Matutino" if float(puntaje) >= PUNTAJE_MATUTINO else "Vespertino"

def periodos_disponibles(hoy=None):
    hoy = hoy or date.today()
    lista = []
    for anio in (hoy.year + 1, hoy.year, hoy.year - 1):
        lista += [f"AGO-DIC {anio}", f"ENE-JUN {anio}"]
    return lista

_LETRAS = r"A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
RE_NOMBRE = re.compile(rf"^[{_LETRAS}]+(?:[ '\-][{_LETRAS}]+)*$")

_ENTIDADES_CURP = (
    "AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE"
)
RE_CURP = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[HMX]"
    rf"({_ENTIDADES_CURP})[B-DF-HJ-NP-TV-Z]{{3}}[A-Z\d]\d$"
)
RE_RFC = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z\d]{3}$")  
RE_CORREO = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
RE_CALLE = re.compile(r"^[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ .,#\-/°º]+$")

def _nombre(valor, etiqueta, obligatorio=True):
    v = espacios(valor)
    if not v:
        return (f"{etiqueta}: es obligatorio." if obligatorio else None), ""
    if not 2 <= len(v) <= 40:
        return f"{etiqueta}: debe tener entre 2 y 40 caracteres.", v
    if not RE_NOMBRE.match(v):
        return f"{etiqueta}: solo letras y espacios (sin números ni símbolos).", v
    return None, v.upper()

def _fecha(valor, etiqueta, edad_min, edad_max):
    """Acepta dd/mm/aaaa (también con - o .). Devuelve (mensaje, date | None, 'dd/mm/aaaa')."""
    v = espacios(valor).replace("-", "/").replace(".", "/")
    if not v:
        return f"{etiqueta}: es obligatoria.", None, ""
    try:
        f = datetime.strptime(v, "%d/%m/%Y").date()
    except ValueError:
        return f"{etiqueta}: usa el formato dd/mm/aaaa y una fecha real (ej. 25/03/2005).", None, v
    hoy = date.today()
    if f > hoy:
        return f"{etiqueta}: no puede ser una fecha futura.", None, v
    edad = hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))
    if not edad_min <= edad <= edad_max:
        return f"{etiqueta}: la edad debe estar entre {edad_min} y {edad_max} años.", None, v
    return None, f, f.strftime("%d/%m/%Y")

_TABLA_CURP = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"

def _digito_curp(curp17):
    suma = sum(_TABLA_CURP.index(c) * (18 - i) for i, c in enumerate(curp17))
    return str((10 - suma % 10) % 10)

def _curp(valor, verificar_digito=True):
    v = espacios(valor).upper().replace(" ", "")
    if not v:
        return "CURP: es obligatoria.", ""
    if len(v) != 18:
        return "CURP: debe tener 18 caracteres.", v
    if not RE_CURP.match(v):
        return "CURP: el formato no es válido (revisa letras, fecha, sexo y entidad).", v
    siglo = 1900 if v[16].isdigit() else 2000
    try:
        date(siglo + int(v[4:6]), int(v[6:8]), int(v[8:10]))
    except ValueError:
        return "CURP: la fecha de nacimiento que contiene no existe.", v
    if verificar_digito and _digito_curp(v[:17]) != v[17]:
        return "CURP: el dígito verificador no coincide, revisa que esté bien escrita.", v
    return None, v

def _rfc(valor):
    v = espacios(valor).upper().replace(" ", "")
    if not v:
        return "RFC: es obligatorio.", ""
    if not RE_RFC.match(v):
        return "RFC: debe tener 13 caracteres (4 letras, 6 dígitos de fecha y 3 de homoclave).", v
    try:
        yy, mm, dd = int(v[4:6]), int(v[6:8]), int(v[8:10])
        date(2000 + yy, mm, dd)
    except ValueError:
        return "RFC: la fecha que contiene no existe.", v
    return None, v

def _sangre(valor):
    v = espacios(valor).upper().replace(" ", "")
    if not v:
        return "Tipo sanguíneo: es obligatorio.", ""
    if v not in TIPOS_SANGRE:
        return f"Tipo sanguíneo: elige uno de {', '.join(TIPOS_SANGRE)}.", v
    return None, v

def _telefono(valor, etiqueta="Teléfono"):
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) == 12 and digitos.startswith("52"):
        digitos = digitos[2:]
    if not digitos:
        return f"{etiqueta}: es obligatorio.", ""
    if len(digitos) != 10:
        return f"{etiqueta}: debe tener 10 dígitos.", digitos
    if len(set(digitos)) == 1:
        return f"{etiqueta}: el número no parece real.", digitos
    return None, digitos

def _correo(valor):
    v = espacios(valor).lower()
    if not v:
        return "Correo: es obligatorio.", ""
    if len(v) > 80 or not RE_CORREO.match(v):
        return "Correo: escribe una dirección válida (ej. nombre@correo.com).", v
    return None, v

def _opcion(valor, etiqueta, opciones, ignorar_acentos=True):
    v = espacios(valor)
    if not v:
        return f"{etiqueta}: campo obligatorio.", ""
    clave = (lambda t: sin_acentos(t).lower()) if ignorar_acentos else (lambda t: t.lower())
    for o in opciones:
        if clave(o) == clave(v):
            return None, o
    return f"{etiqueta}: elige una opción de la lista.", v
#Validar por secciones
def validar_numero(datos, clave="ficha", etiqueta="Número de ficha", min_len=6, max_len=10):
    """Número de ficha / de control / de empleado: solo dígitos."""
    v = espacios(datos.get(clave, ""))
    if not v:
        return {clave: f"{etiqueta}: es obligatorio."}, {}
    if not v.isdigit():
        return {clave: f"{etiqueta}: solo números, sin letras ni espacios."}, {}
    if not min_len <= len(v) <= max_len:
        return {clave: f"{etiqueta}: debe tener entre {min_len} y {max_len} dígitos."}, {}
    return {}, {clave: v}

def validar_datos_personales(datos, edad_min=15, edad_max=80, pedir_rfc=False, pedir_sangre=True):
    errores, limpio = {}, {}

    for clave, etiqueta, obligatorio in (
        ("apellido_paterno", "Apellido paterno", True),
        ("apellido_materno", "Apellido materno", False),
        ("nombre", "Nombre(s)", True),
    ):
        msg, val = _nombre(datos.get(clave), etiqueta, obligatorio)
        limpio[clave] = val
        if msg:
            errores[clave] = msg

    msg, fecha, texto = _fecha(datos.get("fecha_nacimiento"), "Fecha de nacimiento", edad_min, edad_max)
    limpio["fecha_nacimiento"] = texto
    if fecha:
        limpio["fecha_nacimiento_iso"] = fecha.isoformat()
    if msg:
        errores["fecha_nacimiento"] = msg

    msg, curp = _curp(datos.get("curp"))
    limpio["curp"] = curp
    if msg:
        errores["curp"] = msg

    if pedir_sangre:
        msg, sangre = _sangre(datos.get("tipo_sangre"))
        limpio["tipo_sangre"] = sangre
        if msg:
            errores["tipo_sangre"] = msg

    sexo = espacios(datos.get("sexo"))
    limpio["sexo"] = sexo
    if sexo not in SEXOS:
        errores["sexo"] = "Sexo: elige Mujer u Hombre."

    # la CURP debe coincidir con la fecha y el sexo capturados
    if "curp" not in errores and fecha:
        siglo = 1900 if curp[16].isdigit() else 2000
        if date(siglo + int(curp[4:6]), int(curp[6:8]), int(curp[8:10])) != fecha:
            errores["curp"] = "CURP: la fecha que contiene no coincide con la fecha de nacimiento."
    if "curp" not in errores and sexo in SEXOS:
        esperado = "M" if sexo == "Mujer" else "H"
        if curp[10] in "HM" and curp[10] != esperado:
            errores["curp"] = f"CURP: indica sexo '{curp[10]}', pero elegiste {sexo}."

    if pedir_rfc:
        msg, rfc = _rfc(datos.get("rfc"))
        limpio["rfc"] = rfc
        if msg:
            errores["rfc"] = msg
        elif fecha and rfc[4:10] != fecha.strftime("%y%m%d"):
            errores["rfc"] = "RFC: la fecha que contiene no coincide con la fecha de nacimiento."

    return errores, limpio

def validar_domicilio(datos):
    errores, limpio = {}, {}
    # Calle
    calle = espacios(datos.get("calle"))
    limpio["calle"] = calle.upper()

    if not calle:
        errores["calle"] = "Calle: es obligatoria."
    elif (
        not 1 <= len(calle) <= 80
        or not RE_CALLE.match(calle)
        or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", calle)
    ):
        errores["calle"] = "Calle: entre 1 y 80 caracteres válidos."

    # Manzana y lote
    for clave, etiqueta in (
        ("manzana", "Manzana"),
        ("lote", "Lote"),
    ):
        valor = espacios(datos.get(clave))
        limpio[clave] = valor.upper()

        if not valor:
            errores[clave] = f"{etiqueta}: es obligatorio."
        elif (
            len(valor) > 20
            or not re.fullmatch(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ./\- ]+", valor)
        ):
            errores[clave] = f"{etiqueta}: máximo 20 caracteres válidos."

    # Colonia
    colonia = espacios(datos.get("colonia"))
    limpio["colonia"] = colonia.upper()

    if not colonia:
        errores["colonia"] = "Colonia: es obligatoria."
    elif not 3 <= len(colonia) <= 60 or not RE_CALLE.match(colonia):
        errores["colonia"] = "Colonia: entre 3 y 60 caracteres."

    # Código postal
    cp = espacios(datos.get("cp"))
    limpio["cp"] = cp

    if not cp:
        errores["cp"] = "Código postal: es obligatorio."
    elif not (cp.isdigit() and len(cp) == 5):
        errores["cp"] = "Código postal: debe tener 5 dígitos."

    # Municipio
    municipio = espacios(datos.get("municipio"))
    limpio["municipio"] = municipio.upper()

    if not municipio:
        errores["municipio"] = "Municipio: es obligatorio."
    elif (
        not 2 <= len(municipio) <= 100
        or not RE_CALLE.match(municipio)
        or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", municipio)
    ):
        errores["municipio"] = "Municipio: escribe un nombre válido."

    # Estado
    msg, estado = _opcion(datos.get("estado"), "Estado", ESTADOS)
    limpio["estado"] = estado

    if msg:
        errores["estado"] = msg

    # País
    pais = espacios(datos.get("pais")) or "México"
    limpio["pais"] = pais.upper()

    if len(pais) > 60 or not RE_CALLE.match(pais):
        errores["pais"] = "País: máximo 60 caracteres válidos."

    return errores, limpio

def validar_contacto(datos):
    errores, limpio = {}, {}

    msg, tel = _telefono(datos.get("telefono"), "Teléfono")
    limpio["telefono"] = tel
    if msg:
        errores["telefono"] = msg

    msg, correo = _correo(datos.get("correo"))
    limpio["correo"] = correo
    if msg:
        errores["correo"] = msg

    return errores, limpio

def _validar_semestre(valor):
    v = espacios(valor)
    if not v:
        return "Semestre: es obligatorio.", ""
    if v not in SEMESTRES:
        return "Semestre: escribe un número del 1 al 12.", v
    return None, v

def validar_academico_alumno(datos):
    errores, limpio = {}, {}

    msg, carrera = _opcion(datos.get("carrera"), "Carrera", CARRERAS)
    limpio["carrera"] = carrera

    if msg:
        errores["carrera"] = msg

    escuela = espacios(datos.get("escuela_procedencia"))
    limpio["escuela_procedencia"] = escuela.upper()

    if not escuela:
        errores["escuela_procedencia"] = (
            "Escuela de procedencia: es obligatoria."
        )
    elif not 3 <= len(escuela) <= 80 or not RE_CALLE.match(escuela):
        errores["escuela_procedencia"] = (
            "Escuela de procedencia: entre 3 y 80 caracteres."
        )

    prom = espacios(datos.get("promedio")).replace(",", ".")
    limpio["promedio"] = prom

    try:
        valor = float(prom)

        if not 6.0 <= valor <= 10.0:
            raise ValueError

        if len(prom.split(".")[-1]) > 2 and "." in prom:
            raise ValueError

        limpio["promedio"] = f"{valor:.2f}"

    except ValueError:
        errores["promedio"] = (
            "Promedio: número entre 6 y 10, con máximo "
            "2 decimales (ej. 8.7)."
        )

    return errores, limpio

def validar_emergencia(datos):
    errores, limpio = {}, {}

    nombre = espacios(datos.get("contacto_emergencia_nombre"))
    limpio["contacto_emergencia_nombre"] = nombre.upper()

    if not nombre:
        errores["contacto_emergencia_nombre"] = (
            "El nombre del contacto de emergencia es obligatorio."
        )
    elif len(nombre) > 100 or not RE_NOMBRE.match(nombre):
        errores["contacto_emergencia_nombre"] = (
            "Escribe un nombre válido de máximo 100 caracteres."
        )

    parentesco = espacios(datos.get("contacto_emergencia_parentesco"))
    limpio["contacto_emergencia_parentesco"] = parentesco.upper()

    if not parentesco:
        errores["contacto_emergencia_parentesco"] = (
            "El parentesco es obligatorio."
        )
    elif len(parentesco) > 40 or not RE_NOMBRE.match(parentesco):
        errores["contacto_emergencia_parentesco"] = (
            "Escribe un parentesco válido de máximo 40 caracteres."
        )

    msg, telefono = _telefono(
        datos.get("contacto_emergencia_telefono"),
        "Teléfono de emergencia",
    )
    limpio["contacto_emergencia_telefono"] = telefono

    if msg:
        errores["contacto_emergencia_telefono"] = msg

    return errores, limpio

def validar_puntaje_admision(datos):
    errores, limpio = {}, {}

    texto = espacios(datos.get("puntaje_examen_admision"))
    if not texto:
        return {
            "puntaje_examen_admision":
                "El puntaje del examen de admisión es obligatorio."
        }, {}

    try:
        puntaje = float(texto.replace(",", "."))
    except ValueError:
        return {
            "puntaje_examen_admision": "El puntaje debe ser numérico."
        }, {}

    if not 0 <= puntaje <= 100:
        errores["puntaje_examen_admision"] = (
            "El puntaje debe estar entre 0 y 100."
        )
    else:
        limpio["puntaje_examen_admision"] = puntaje

    return errores, limpio

def validar_profesional_docente(datos):
    errores, limpio = {}, {}

    grado = espacios(datos.get("grado"))
    limpio["grado"] = grado
    if grado not in GRADOS:
        errores["grado"] = "Grado académico: elige una opción."

    contratacion = espacios(datos.get("contratacion"))
    limpio["contratacion"] = contratacion
    if contratacion not in CONTRATACIONES:
        errores["contratacion"] = "Contratación: elige una opción."

    cedula = espacios(datos.get("cedula"))
    limpio["cedula"] = cedula
    if not cedula:
        errores["cedula"] = "Cédula profesional: es obligatoria."
    elif not (cedula.isdigit() and len(cedula) in (7, 8)):
        errores["cedula"] = "Cédula profesional: debe tener 7 u 8 dígitos."

    esp = espacios(datos.get("especialidad"))
    limpio["especialidad"] = esp.upper()
    if not esp:
        errores["especialidad"] = "Especialidad: es obligatoria."
    elif not 3 <= len(esp) <= 80 or not RE_CALLE.match(esp):
        errores["especialidad"] = "Especialidad: entre 3 y 80 caracteres."

    departamento = espacios(datos.get("departamento"))
    limpio["departamento"] = departamento
    opciones = CARRERAS + ["Ciencias Básicas", "Ciencias Económico-Administrativas"]
    msg, dep = _opcion(departamento, "Departamento", opciones)
    limpio["departamento"] = dep
    if msg:
        errores["departamento"] = msg

    return errores, limpio

def validar_inscripcion(datos):
    errores, limpio = {}, {}

    tipo = espacios(datos.get("tipo_inscripcion"))
    limpio["tipo_inscripcion"] = tipo
    if tipo not in TIPOS_INSCRIPCION:
        errores["tipo_inscripcion"] = "Tipo de trámite: elige Inscripción o Reinscripción."

    periodo = espacios(datos.get("periodo")).upper()
    limpio["periodo"] = periodo
    if not periodo:
        errores["periodo"] = "Periodo: es obligatorio."
    elif periodo not in periodos_disponibles():
        errores["periodo"] = "Periodo: usa el formato AGO-DIC 2026 o ENE-JUN 2027."

    msg, carrera = _opcion(datos.get("carrera"), "Carrera", CARRERAS)
    limpio["carrera"] = carrera
    if msg:
        errores["carrera"] = msg

    msg, sem = _validar_semestre(datos.get("semestre"))
    limpio["semestre"] = sem
    if msg:
        errores["semestre"] = msg
    elif tipo == "Inscripción" and sem != str(SEMESTRE_INICIAL):
        errores["semestre"] = f"Semestre: una inscripción es de primer semestre ({SEMESTRE_INICIAL})."

    grupo = espacios(datos.get("grupo")).upper().replace(" ", "")
    limpio["grupo"] = grupo
    if not grupo:
        errores["grupo"] = "Grupo: es obligatorio."
    elif not re.fullmatch(r"[A-Z0-9]{1,6}", grupo):
        errores["grupo"] = "Grupo: de 1 a 6 letras o números (ej. 7A)."

    return errores, limpio

#  ARCHIVOS PDF
def validar_pdf(ruta):
    """Devuelve un mensaje de error, o None si el archivo es un PDF aceptable."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return f"{ruta.name}: no se encontró el archivo."
    if ruta.suffix.lower() != ".pdf":
        return f"{ruta.name}: solo se aceptan archivos .pdf."
    tamano = ruta.stat().st_size
    if tamano == 0:
        return f"{ruta.name}: el archivo está vacío."
    if tamano > PDF_MAX_MB * 1024 * 1024:
        return f"{ruta.name}: pesa más de {PDF_MAX_MB} MB."
    try:
        with open(ruta, "rb") as f:
            if f.read(5) != b"%PDF-":
                return f"{ruta.name}: no es un PDF válido (está dañado o fue renombrado)."
    except OSError:
        return f"{ruta.name}: no se pudo leer el archivo."
    return None

TIPOS_DOCUMENTO = {
    "acta_nacimiento": "Acta de nacimiento",
    "curp": "CURP",
    "certificado_bachillerato": "Certificado de bachillerato",
    "comprobante_domicilio": "Comprobante de domicilio",
    "otro": "Otro",
}


def validar_documentos(datos, clave="documentos", minimo=1, maximo=PDF_MAX_ARCHIVOS, etiqueta="Documentos"):
    documentos = list(datos.get(clave) or [])
    if len(documentos) < minimo:
        return {clave: f"{etiqueta}: sube al menos {minimo} archivo PDF."}, {}
    if len(documentos) > maximo:
        return {clave: f"{etiqueta}: máximo {maximo} archivos."}, {}
    errores = []
    tipos_usados = set()
    limpios = []
    for i, documento in enumerate(documentos, start=1):
        if not isinstance(documento, dict):
            errores.append(
                f"Documento {i}: falta seleccionar su tipo."
            )
            continue

        ruta = str(documento.get("ruta") or "").strip()
        tipo = str(documento.get("tipo") or "").strip()

        if not ruta:
            errores.append(f"Documento {i}: falta la ruta del archivo.")
            continue

        if tipo not in TIPOS_DOCUMENTO:
            errores.append(
                f"Documento {i}: selecciona un tipo de documento."
            )
            continue

        if tipo != "otro" and tipo in tipos_usados:
            errores.append(
                f"Solo puedes agregar un PDF de cada tipo. "
                f"Tipo repetido: {TIPOS_DOCUMENTO[tipo]}."
            )
            continue

        problema = validar_pdf(ruta)
        if problema:
            errores.append(problema)
            continue

        tipos_usados.add(tipo)
        limpios.append({
            "ruta": str(Path(ruta)),
            "tipo": tipo,
        })

    if errores:
        return {clave: f"{etiqueta}: " + " ".join(errores)}, {}

    return {}, {clave: limpios}
def validar_inscripcion(datos):
    errores, limpio = {}, {}

    # Tipo de trámite
    tipo = espacios(datos.get("tipo_inscripcion"))
    limpio["tipo_inscripcion"] = tipo
    if tipo not in TIPOS_INSCRIPCION:
        errores["tipo_inscripcion"] = "Tipo de trámite: elige Inscripción o Reinscripción."

    # Periodo (acepta "ago-dic 2026" o "AGO - DIC 2026")
    periodo = re.sub(r"\s*-\s*", "-", espacios(datos.get("periodo")).upper())
    limpio["periodo"] = periodo
    if not periodo:
        errores["periodo"] = "Periodo: es obligatorio."
    elif periodo not in periodos_disponibles():
        anio = date.today().year
        errores["periodo"] = (
            f"Periodo: elige uno de la lista (ej. AGO-DIC {anio} o ENE-JUN {anio + 1})."
        )

    # Carrera
    msg, carrera = _opcion(datos.get("carrera"), "Carrera", CARRERAS)
    limpio["carrera"] = carrera
    if msg:
        errores["carrera"] = msg

    # Semestre según el tipo de trámite
    msg, sem = _validar_semestre(datos.get("semestre"))
    limpio["semestre"] = sem
    if msg:
        errores["semestre"] = msg
    elif tipo == "Inscripción" and sem != str(SEMESTRE_INICIAL):
        errores["semestre"] = (
            f"Semestre: una inscripción es de primer semestre ({SEMESTRE_INICIAL})."
        )
    elif tipo == "Reinscripción" and int(sem) <= SEMESTRE_INICIAL:
        errores["semestre"] = (
            "Semestre: una reinscripción es de segundo semestre en adelante (2 a 12)."
        )

    # Grupo
    grupo = espacios(datos.get("grupo")).upper().replace(" ", "")
    limpio["grupo"] = grupo
    if not grupo:
        errores["grupo"] = "Grupo: es obligatorio."
    elif not re.fullmatch(r"[A-Z0-9]{1,6}", grupo):
        errores["grupo"] = "Grupo: de 1 a 6 letras o números (ej. 7A)."

    return errores, limpio