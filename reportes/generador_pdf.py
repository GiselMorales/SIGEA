import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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