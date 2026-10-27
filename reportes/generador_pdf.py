# reportes/generador_pdf.py
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

AZUL = colors.HexColor("#006BB3")
AZUL_CLARO = colors.HexColor("#EDF3FD")


def _archivo_recurso(nombre):
    """Busca un archivo en la carpeta Recursos"""
    raiz = Path(__file__).resolve().parent.parent
    for carpeta in raiz.iterdir():
        if carpeta.is_dir() and carpeta.name.lower() == "recursos":
            for archivo in carpeta.iterdir():
                if archivo.is_file() and archivo.name.lower() == nombre.lower():
                    return archivo
    return None


def _texto(valor, defecto="N/D"):
    return escape(str(valor)) if valor not in (None, "") else defecto


def _membrete(styles, ancho_total):
    escudo_izq = _archivo_recurso("sigeacircular.png")
    escudo_der = _archivo_recurso("Logotecnm300.png")
    img_left = Image(str(escudo_izq), width=55, height=55) if escudo_izq else ""
    img_right = Image(str(escudo_der), width=70, height=50) if escudo_der else ""

    style_header = ParagraphStyle(
        "HeaderStyle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13, alignment=1,
    )
    texto_membrete = Paragraph(
        "<b>TECNOLÓGICO NACIONAL DE MÉXICO</b><br/>"
        "<b>INSTITUTO TECNOLÓGICO DE ACAPULCO</b><br/>"
        "<font size=8 color='#555555'>Sistema Integral de Gestión Escolar y Académica (SIGEA)</font>",
        style_header,
    )
    tabla = Table([[img_left, texto_membrete, img_right]],
                  colWidths=[70, ancho_total - 140, 70])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return tabla


def generar_pdf_oficial(datos_registro, ruta_salida):
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(ruta_salida),
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()

    # Rutas relativas apuntando directamente a tu carpeta Recursos existente
    raiz_proyecto = Path(__file__).resolve().parent.parent
    escudo_izq = raiz_proyecto / "Recursos" / "sigeacircular.png"
    escudo_der = raiz_proyecto / "Recursos" / "Logotecnm300.png"

    img_left = Image(str(escudo_izq), width=55, height=55) if escudo_izq.exists() else ""
    img_right = Image(str(escudo_der), width=70, height=50) if escudo_der.exists() else ""

    style_header = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        alignment=1 # Centrado
    )

    texto_membrete = Paragraph(
        "<b>TECNOLÓGICO NACIONAL DE MÉXICO</b><br/>"
        "<b>INSTITUTO TECNOLÓGICO DE ACAPULCO</b><br/>"
        "<font size=8 color='#555555'>Sistema Integral de Gestión Escolar y Académica (SIGEA)</font>",
        style_header
    )

    # Tabla con membrete y escudos institucionales
    tabla_encabezado = Table([[img_left, texto_membrete, img_right]], colWidths=[70, 390, 70])
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    
    story.append(tabla_encabezado)
    story.append(Spacer(1, 20))

    # Título del documento
    style_titulo = ParagraphStyle(
        'TituloDoc',
        fontName='Helvetica-Bold',
        fontSize=13,
        alignment=1,
        textColor=colors.HexColor("#1B396A")
    )
    story.append(Paragraph("COMPROBANTE DE REGISTRO OFICIAL", style_titulo))
    story.append(Spacer(1, 15))

    # Cuerpo del reporte
    style_cuerpo = ParagraphStyle('CuerpoDoc', fontName='Helvetica', fontSize=10, leading=16)
    
    cuerpo_texto = f"""
    A quien corresponda:
    <br/><br/>
    Por medio de la presente se hace constar que se encuentra registrado en el sistema SIGEA el siguiente expediente:
    <br/><br/>
    <b>Nombre / Descripción:</b> {datos_registro.get('nombre', datos_registro.get('descripcion', 'N/D'))}<br/>
    <b>Clave / Identificador:</b> {datos_registro.get('ficha', datos_registro.get('numero_control', 'N/D'))}<br/>
    <b>Fecha de Emisión:</b> {datos_registro.get('fecha', 'N/D')}<br/>
    <br/><br/>
    Este documento cuenta con validez oficial dentro de la plataforma y sus datos están respaldados en los servidores institucionales.
    """
    story.append(Paragraph(cuerpo_texto, style_cuerpo))
    story.append(Spacer(1, 40))

    # Firma
    tabla_firma = Table([["________________________________________"], ["Firma y Sello Autorizado"]], colWidths=[250])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(tabla_firma)

    doc.build(story)
    return ruta_salida


def generar_pdf_consulta(titulo, columnas, filas, ruta_salida,
                         anchos=None, filtro="", resumen=""):
    """PDF horizontal con una tabla de resultados.
    columnas: ["No.", ...]   filas: [[valor, ...], ...]   anchos: puntos por columna."""
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)

    pagina = landscape(letter)
    margen = 30
    ancho_util = pagina[0] - 2 * margen

    doc = SimpleDocTemplate(
        str(ruta_salida), pagesize=pagina,
        rightMargin=margen, leftMargin=margen, topMargin=30, bottomMargin=36,
        title=titulo,
    )
    styles = getSampleStyleSheet()
    story = [_membrete(styles, ancho_util), Spacer(1, 12)]

    story.append(Paragraph(
        _texto(titulo),
        ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=14, alignment=1,
                       textColor=colors.HexColor("#1B396A")),
    ))
    story.append(Spacer(1, 6))

    info = ParagraphStyle("I", fontName="Helvetica", fontSize=9, leading=12, alignment=1,
                          textColor=colors.HexColor("#333333"))
    linea = f"<b>Filtro:</b> {_texto(filtro, 'Todos')} &nbsp;&nbsp; " \
            f"<b>Fecha:</b> {datetime.now():%d/%m/%Y %H:%M}"
    story.append(Paragraph(linea, info))
    if resumen:
        story.append(Paragraph(_texto(resumen), info))
    story.append(Spacer(1, 10))

    celda = ParagraphStyle("C", fontName="Helvetica", fontSize=8, leading=10)
    cabecera = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8, leading=10,
                              textColor=colors.white)

    datos = [[Paragraph(_texto(c), cabecera) for c in columnas]]
    for fila in filas:
        datos.append([Paragraph(_texto(v, ""), celda) for v in fila])

    if anchos is None:
        anchos = [ancho_util / len(columnas)] * len(columnas)
    else:
        factor = ancho_util / sum(anchos)
        anchos = [a * factor for a in anchos]

    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, AZUL_CLARO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D8EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tabla)

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(margen, 20, "SIGEA - Instituto Tecnológico de Acapulco")
        canvas.drawRightString(pagina[0] - margen, 20, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return ruta_salida


# ----------------------------------------------------------------------
#  Reportes de horarios y de listas de grupo
# ----------------------------------------------------------------------
DIAS_ORDEN = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
PASTELES = ["#DCEBFA", "#E3F4E1", "#FCEFD2", "#F6DDE8", "#E6E0F5",
            "#D9F0F0", "#FBE3D6", "#EDEDED"]


def _hacer_pie(pagina, margen):
    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(margen, 20, "SIGEA - Instituto Tecnológico de Acapulco")
        canvas.drawRightString(pagina[0] - margen, 20, f"Página {documento.page}")
        canvas.restoreState()
    return pie


def _hora(valor):
    return valor.strftime("%H:%M") if hasattr(valor, "strftime") else str(valor)


def generar_pdf_horario(datos, ruta_salida):
    """PDF horizontal con la cuadrícula semanal del grupo y el detalle de sus materias.
    datos: {periodo, semestre, turno, clave, materias:[{clave, nombre, creditos, docente,
    aula, bloques:[(dia, inicio, fin)]}]}"""
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)

    pagina = landscape(letter)
    margen = 30
    ancho_util = pagina[0] - 2 * margen
    titulo = (
        f"HORARIO DEL ALUMNO · {datos['alumno_nombre']}"
        if datos.get("numero_control")
        else f"HORARIO DEL GRUPO {datos['clave']}"
    )

    doc = SimpleDocTemplate(
        str(ruta_salida), pagesize=pagina,
        rightMargin=margen, leftMargin=margen, topMargin=30, bottomMargin=36,
        title=titulo,
    )
    styles = getSampleStyleSheet()
    story = [_membrete(styles, ancho_util), Spacer(1, 10)]

    story.append(Paragraph(
        _texto(titulo),
        ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=14, alignment=1,
                       textColor=colors.HexColor("#1B396A")),
    ))
    story.append(Spacer(1, 4))
    info = ParagraphStyle("I", fontName="Helvetica", fontSize=9, leading=12, alignment=1,
                          textColor=colors.HexColor("#333333"))
    identificacion = ""
    if datos.get("numero_control"):
        identificacion = (
            f"<b>No. de control:</b> {_texto(datos['numero_control'])} &nbsp;&nbsp; "
            f"<b>Alumno:</b> {_texto(datos.get('alumno_nombre'))}<br/>"
        )
    story.append(Paragraph(
        f"{identificacion}<b>Periodo:</b> {_texto(datos['periodo'])} &nbsp;&nbsp; "
        f"<b>Semestre:</b> {datos['semestre']} &nbsp;&nbsp; "
        f"<b>Turno:</b> {_texto(str(datos['turno']).capitalize())} &nbsp;&nbsp; "
        f"<b>Grupo:</b> {_texto(datos['clave'])} &nbsp;&nbsp; "
        f"<b>Emitido:</b> {datetime.now():%d/%m/%Y %H:%M}",
        info,
    ))
    story.append(Spacer(1, 10))

    materias = datos["materias"]
    color_de = {m["clave"]: colors.HexColor(PASTELES[i % len(PASTELES)])
                for i, m in enumerate(materias)}

    dias = [d for d in DIAS_ORDEN[:5]]
    if any(b[0] == "sábado" for m in materias for b in m["bloques"]):
        dias.append("sábado")
    franjas = sorted({(b[1], b[2]) for m in materias for b in m["bloques"]})

    celda = ParagraphStyle("C", fontName="Helvetica", fontSize=8, leading=10, alignment=1)
    cabecera = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=9, leading=11,
                              alignment=1, textColor=colors.white)

    filas = [[Paragraph("Hora", cabecera)] + [Paragraph(d.capitalize(), cabecera) for d in dias]]
    fondos = []
    for r, (inicio, fin) in enumerate(franjas, start=1):
        fila = [Paragraph(f"<b>{_hora(inicio)} - {_hora(fin)}</b>", celda)]
        for c, dia in enumerate(dias, start=1):
            texto = ""
            for m in materias:
                if any(b[0] == dia and b[1] == inicio and b[2] == fin for b in m["bloques"]):
                    aula = f"<br/>Aula {_texto(m['aula'])}" if m["aula"] else ""
                    texto = f"<b>{_texto(m['nombre'])}</b>{aula}"
                    fondos.append(("BACKGROUND", (c, r), (c, r), color_de[m["clave"]]))
                    break
            fila.append(Paragraph(texto, celda))
        filas.append(fila)

    ancho_hora = 80
    ancho_dia = (ancho_util - ancho_hora) / len(dias)
    cuadricula = Table(filas, colWidths=[ancho_hora] + [ancho_dia] * len(dias), repeatRows=1)
    cuadricula.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9FB3CF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ] + fondos))
    story.append(cuadricula)
    story.append(Spacer(1, 14))

    # Detalle de materias
    celda_izq = ParagraphStyle("CI", fontName="Helvetica", fontSize=8, leading=10)
    encabezados = ["Clave", "Materia", "Docente", "Aula", "Créd.", "Días y horas"]
    detalle = [[Paragraph(e, ParagraphStyle("DH", fontName="Helvetica-Bold", fontSize=8,
                                           leading=10, textColor=colors.white))
                for e in encabezados]]
    abreviatura = {"lunes": "Lun", "martes": "Mar", "miércoles": "Mié",
                   "jueves": "Jue", "viernes": "Vie", "sábado": "Sáb"}
    total_creditos = 0
    for m in materias:
        total_creditos += m["creditos"] or 0
        horas = ", ".join(f"{abreviatura.get(d, d)} {_hora(i)}-{_hora(f)}"
                          for d, i, f in m["bloques"])
        detalle.append([Paragraph(_texto(x, ""), celda_izq) for x in (
            m["clave"], m["nombre"], m["docente"], m["aula"], m["creditos"], horas)])

    pesos = [60, 190, 170, 45, 35, 240]
    factor = ancho_util / sum(pesos)
    tabla = Table(detalle, colWidths=[p * factor for p in pesos], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, AZUL_CLARO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D8EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tabla)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Materias:</b> {len(materias)} &nbsp;&nbsp; <b>Créditos:</b> {total_creditos}", info))

    pie = _hacer_pie(pagina, margen)
    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return str(ruta_salida)


def generar_pdf_lista_grupo(datos, ruta_salida):
    """Lista de alumnos de un grupo (o de una materia del grupo), en tabla.
    datos: {periodo, semestre, turno, clave, materia: None | {clave, nombre, docente},
    alumnos:[{control, nombre, sexo, estatus}]}"""
    alumnos = datos["alumnos"]
    filas = [
        [str(i).zfill(2), a["control"], a["nombre"], a["sexo"], a["estatus"], ""]
        for i, a in enumerate(alumnos, start=1)
    ]
    mujeres = sum(a["sexo"] == "Mujer" for a in alumnos)
    hombres = sum(a["sexo"] == "Hombre" for a in alumnos)

    titulo = f"LISTA DEL GRUPO {datos['clave']}"
    filtro = (
        f"Periodo {datos['periodo']} · Semestre {datos['semestre']} · "
        f"Turno {str(datos['turno']).capitalize()}"
    )
    materia = datos.get("materia")
    if materia:
        titulo += f" - {materia['nombre']}"
        filtro += f" · {materia['clave']} · Docente: {materia['docente']}"

    return generar_pdf_consulta(
        titulo,
        ["No.", "No. control", "Nombre completo", "Sexo", "Estatus", "Observaciones"],
        filas,
        str(ruta_salida),
        anchos=[35, 80, 270, 55, 70, 150],
        filtro=filtro,
        resumen=f"Total: {len(alumnos)}   Mujeres: {mujeres}   Hombres: {hombres}",
    )
