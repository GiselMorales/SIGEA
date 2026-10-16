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
    """Busca un archivo en la carpeta Recursos/recursos sin importar mayúsculas."""
    raiz = Path(__file__).resolve().parent.parent
    for carpeta in raiz.iterdir():
        if carpeta.is_dir() and carpeta.name.lower() == "recursos":
            for archivo in carpeta.iterdir():
                if archivo.is_file() and archivo.name.lower() == nombre.lower():
                    return archivo
    return None


def _texto(valor, defecto="N/D"):
    """Escapa &, < y > para que reportlab no falle con nombres como 'PÉREZ & HIJOS'."""
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
        str(ruta_salida), pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    story = [_membrete(styles, 530), Spacer(1, 20)]

    style_titulo = ParagraphStyle(
        "TituloDoc", fontName="Helvetica-Bold", fontSize=13, alignment=1,
        textColor=colors.HexColor("#1B396A"),
    )
    story.append(Paragraph("COMPROBANTE DE REGISTRO OFICIAL", style_titulo))
    story.append(Spacer(1, 15))

    style_cuerpo = ParagraphStyle("CuerpoDoc", fontName="Helvetica", fontSize=10, leading=16)

    nombre = datos_registro.get("nombre") or datos_registro.get("descripcion")
    clave = datos_registro.get("ficha") or datos_registro.get("numero_control")
    fecha = datos_registro.get("fecha") or date.today().strftime("%d/%m/%Y")

    cuerpo_texto = f"""
    A quien corresponda:
    <br/><br/>
    Por medio de la presente se hace constar que se encuentra registrado en el sistema SIGEA el siguiente expediente:
    <br/><br/>
    <b>Nombre / Descripción:</b> {_texto(nombre)}<br/>
    <b>Clave / Identificador:</b> {_texto(clave)}<br/>
    <b>Fecha de Emisión:</b> {_texto(fecha)}<br/>
    <br/><br/>
    Este documento cuenta con validez oficial dentro de la plataforma y sus datos están respaldados en los servidores institucionales.
    """
    story.append(Paragraph(cuerpo_texto, style_cuerpo))
    story.append(Spacer(1, 40))

    tabla_firma = Table(
        [["________________________________________"], ["Firma y Sello Autorizado"]],
        colWidths=[250],
    )
    tabla_firma.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
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