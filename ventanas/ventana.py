from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QRectF,
    QPointF,
    QRect,
    QSize,
    QTimer,
    Signal,
    Property,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPixmap,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPen,
    QBrush,
    QPolygonF,
)

import sys
from pathlib import Path


class Config:

    AZUL_PRINCIPAL = "#354277"
    AZUL_OSCURO = "#0F172A"
    AZUL_MEDIO = "#1D4ED8"
    AZUL_CLARO = "#38BDF8"
    CIAN = "#00D4E0"

    FONDO_VENTANA = "#15477D"
    FONDO_TARJETA = "#FFFFFF"
    FONDO_CAMPO = "#F2F4F7"

    TEXTO_TITULO = "#FBFBFB"
    TEXTO_SUBTITULO = "#5B6B79"
    TEXTO_LABEL = "#343B41"
    TEXTO_PLACEHOLDER = "#9AA5B1"
    TEXTO_CLARO = "#FFFFFF"
    TEXTO_ERROR = "#C0392B"
    AZUL_BOTON = "#1558D6"
    AZUL_GLOW = "#38BDF8"
    AZUL_BRIGHT = "#D9F7FF"
    BOTON_OSCURO = "#0B2A55"
    COLOR_INTERIOR_BOTON = "#35383B"
    COLOR_INTERIOR_BOTON_PRESIONADO = "#056DD5"

    ROJO = "#E11D2E"
    ROJO_OSCURO = "#9B0F1E"
    AZUL_SOMBRA = "#008CFF"      
    AZUL_ENTRAR = "#006BB3"      
    GRIS_CAMPO = "#F3F3F3"       
    AZUL_INPUT = "#4A9DEC"      
    FONDO_FORM = "#EDF3FD"       
    FONDO_FORM_CAMPO = "#E4ECF5"
    AZUL_FORM = "#00BFFF"
    FONDO_FORM_BORDE = "#C9D8EE"
    TEXTO_OSCURO = "#1E2A3A"       # texto sobre campos, tarjetas y menús claros

    # Recursos (imágenes) del proyecto
    CARPETA_RECURSOS = "recursos"  # también se acepta "Recursos", "RECURSOS", etc.
    LOGO_PRINCIPAL = "sigeacircular.png"
    LOGO_ZAFIRO = "zafiroclaroclaroo45.png"
    ICONO_APP = ["icono.ico", "icono.png", "sigea.ico", "sigea.png", "sigeacircular.png"]

    FUENTE_BASE = "poppins"

    FONT_LOGO = 40
    FONT_TITULO = 26
    FONT_SUBTITULO = 11
    FONT_LABEL = 10
    FONT_INPUT = 12
    FONT_BOTON = 12

def mezclar(c1, c2, t):
    """Interpola entre dos colores (t=0 -> c1, t=1 -> c2)."""
    a, b = QColor(c1), QColor(c2)
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def fuente(tam, negrita=True, espaciado=0.0):
    f = QFont(Config.FUENTE_BASE)
    f.setPointSizeF(tam)
    f.setBold(negrita)
    f.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return f


def sombra(widget, color, blur=20, dy=0, alpha=255):
    efecto = QGraphicsDropShadowEffect(widget)
    c = QColor(color)
    c.setAlpha(alpha)
    efecto.setColor(c)
    efecto.setBlurRadius(blur)
    efecto.setOffset(0, dy)
    widget.setGraphicsEffect(efecto)
    return efecto

def carpeta_recursos():
    """Carpeta de recursos del proyecto (sin importar mayúsculas); None si no existe."""
    bases = []
    if getattr(sys, "_MEIPASS", None):               # ejecutable de PyInstaller
        bases.append(Path(sys._MEIPASS))
    aqui = Path(__file__).resolve().parent
    bases += [aqui.parent, aqui, Path.cwd()]          # raíz del proyecto (donde está main.py)
    objetivo = Config.CARPETA_RECURSOS.lower()
    for base in bases:
        if not base.is_dir():
            continue
        for hijo in base.iterdir():
            if hijo.is_dir() and hijo.name.lower() == objetivo:
                return hijo
    return None


def ruta_recurso(nombre):
    """Path de un archivo dentro de la carpeta de recursos (sin importar mayúsculas), o None."""
    carpeta = carpeta_recursos()
    if carpeta is None:
        return None
    for archivo in carpeta.iterdir():
        if archivo.is_file() and archivo.name.lower() == nombre.lower():
            return archivo
    return None


def buscar_icono_app():
    """Ruta (str) del icono de SIGEA según Config.ICONO_APP, o None."""
    for nombre in Config.ICONO_APP:
        ruta = ruta_recurso(nombre)
        if ruta:
            return str(ruta)
    return None


class _BotonAnimado(QPushButton):

    def __init__(self, texto="", icono=None, parent=None):
        super().__init__(texto, parent)
        self._t = 0.0
        self._presionado = False
        self._texto = texto
        self.setCursor(Qt.PointingHandCursor)
        if icono:
            self.setIcon(icono if isinstance(icono, QIcon) else QIcon(str(icono)))
        self._anim = QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def setText(self, texto):
       self._texto = texto
       super().setText(texto)

    def _get_hover(self):
        return self._t

    def _set_hover(self, v):
        self._t = v
        self._al_cambiar()
        self.update()

    hover = Property(float, _get_hover, _set_hover)

    def _al_cambiar(self):
        pass

    def _ir_a(self, destino):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(destino)
        self._anim.start()

    def enterEvent(self, e):
        self._ir_a(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._ir_a(0.0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._presionado = True
        self._al_cambiar()
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._presionado = False
        self._al_cambiar()
        self.update()
        super().mouseReleaseEvent(e)

    def _dibujar_icono(self, p, x, y, tam=18):
        if self.icon().isNull():
            return
        p.drawPixmap(int(x), int(y), self.icon().pixmap(tam, tam))

class BotonSombra(_BotonAnimado):
    def __init__(self, texto="", icono=None, parent=None):
        super().__init__(texto.upper(), icono, parent)
        self.setFont(fuente(11, True, 4))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Config.AZUL_SOMBRA};
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 10px 20px;
            }}
            QPushButton:pressed {{
                background-color: #0077DD;
            }}
        """)
        self._efecto = sombra(self, Config.AZUL_SOMBRA, 25)
        self._anim.setDuration(500)

    def _al_cambiar(self):
        self._efecto.setBlurRadius(25 + 70 * self._t)

class BotonSalida(_BotonAnimado):
    def __init__(self, texto="", icono=None, parent=None):
        super().__init__(texto, icono, parent)
        self.setFont(fuente(11, False, 0.6))
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        s = 0.95 if self._presionado else 1.0
        p.translate(w / 2, h / 2)
        p.scale(s, s)
        p.translate(-w / 2, -h / 2)

        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, w, h), h * 0.3, h * 0.3)
        p.setClipPath(ruta)

        deg = QLinearGradient(0, 0, w, 0)
        deg.setColorAt(0, QColor(Config.ROJO))
        deg.setColorAt(1, QColor(Config.ROJO_OSCURO))
        p.fillPath(ruta, QBrush(deg))

        # franja negra inclinada (skew 30°) que sale hacia la derecha
        off = self._t * 1.2 * w
        sk = h * 0.577 / 2
        franja = QPolygonF([
            QPointF(-0.1 * w + off - sk, 0),
            QPointF(1.1 * w + off - sk, 0),
            QPointF(1.1 * w + off + sk, h),
            QPointF(-0.1 * w + off + sk, h),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#000000"))
        p.drawPolygon(franja)

        p.setFont(self.font())
        p.setPen(QColor("#F8F8FF"))
        fm = QFontMetrics(self.font())
        tw = fm.horizontalAdvance(self._texto)
        ic = 0 if self.icon().isNull() else 24
        x0 = (w - tw - ic) / 2
        if ic:
            self._dibujar_icono(p, x0, (h - 18) / 2)
        p.drawText(QRectF(x0 + ic, 0, tw + 4, h), Qt.AlignVCenter | Qt.AlignLeft, self._texto)

class BotonSecundario(_BotonAnimado):
    def __init__(self, texto="", icono=None, parent=None):
        super().__init__(texto.upper(), icono, parent)
        self._efecto = sombra(self, "#000000", 8, 0, 14)
        self._anim.setDuration(500)

    def _al_cambiar(self):
        t = self._t
        c = mezclar("#000000", Config.AZUL_PRINCIPAL, t)
        c.setAlpha(int(14 + 226 * t))
        self._efecto.setColor(c)
        self._efecto.setBlurRadius(8 + 21 * t)
        self._efecto.setOffset(0, 0 if self._presionado else 7 * t)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._t
        w, h = self.width(), self.height()
        caja = QRectF(0, 0, w, h - 8)
        if self._presionado:
            caja.translate(0, 6)

        p.setPen(Qt.NoPen)
        p.setBrush(mezclar("#FFFFFF", Config.AZUL_PRINCIPAL, t))
        p.drawRoundedRect(caja, caja.height() / 2, caja.height() / 2)

        f = fuente(10, False, 1.5 + 1.5 * t)
        p.setFont(f)
        p.setPen(mezclar(Config.TEXTO_OSCURO, "#FFFFFF", t))
        tw = QFontMetrics(f).horizontalAdvance(self._texto)
        ic = 0 if self.icon().isNull() else 26
        x0 = (w - tw - ic) / 2
        if ic:
            self._dibujar_icono(p, x0, caja.top() + (caja.height() - 18) / 2)
        p.drawText(QRectF(x0 + ic, caja.top(), tw + 8, caja.height()), Qt.AlignVCenter | Qt.AlignLeft, self._texto)

class BotonEntrar(_BotonAnimado):
    def __init__(self, texto="", icono=None, parent=None):
        super().__init__(texto, icono, parent)
        self._brillo = 0.0
        self._efecto = sombra(self, "#000000", 20, 10, 51)
        self._anim_brillo = QPropertyAnimation(self, b"brillo", self)
        self._anim_brillo.setDuration(1500)
        self._anim_brillo.setLoopCount(-1)
        self._anim_brillo.setKeyValueAt(0.0, 0.0)
        self._anim_brillo.setKeyValueAt(0.6, 1.0)
        self._anim_brillo.setKeyValueAt(1.0, 1.0)

    def _get_brillo(self):
        return self._brillo

    def _set_brillo(self, v):
        self._brillo = v
        self.update()

    brillo = Property(float, _get_brillo, _set_brillo)

    def enterEvent(self, e):
        self._anim_brillo.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_brillo.stop()
        self._brillo = 0.0
        super().leaveEvent(e)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._t
        w, h = self.width(), self.height()
        s = (1 + 0.05 * t) / 1.05 * (0.97 if self._presionado else 1.0)
        p.translate(w / 2, h / 2)
        p.scale(s, s)
        p.translate(-w / 2, -h / 2)

        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(1.5, 1.5, w - 3, h - 3), (h - 3) / 2, (h - 3) / 2)
        p.fillPath(ruta, QColor(Config.AZUL_ENTRAR))

        p.save()
        p.setClipPath(ruta)
        if t > 0:
            x = -100 + self._brillo * (w + 100)
            g = QLinearGradient(x, 0, x + 100, 0)
            g.setColorAt(0.3, QColor(255, 255, 255, 0))
            g.setColorAt(0.5, QColor(255, 255, 255, 204))
            g.setColorAt(0.7, QColor(255, 255, 255, 0))
            p.setOpacity(0.6)
            p.fillRect(QRectF(x, 0, 100, h), QBrush(g))
        p.restore()

        p.setPen(QPen(QColor(255, 255, 255, int(77 + 76 * t)), 3))
        p.setBrush(Qt.NoBrush)
        p.drawPath(ruta)

        f = fuente(11, True, 0.3)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        tw = QFontMetrics(f).horizontalAdvance(self._texto)
        total = tw + 10 + 24
        x0 = (w - total) / 2
        p.drawText(QRectF(x0, 0, tw + 4, h), Qt.AlignVCenter | Qt.AlignLeft, self._texto)

        # flecha que se desplaza 4px en hover
        ax = x0 + tw + 10 + 4 * t
        cy = h / 2
        pen = QPen(QColor("#FFFFFF"), 2.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(QPointF(ax + 2, cy), QPointF(ax + 20, cy))
        p.drawLine(QPointF(ax + 14, cy - 6), QPointF(ax + 20, cy))
        p.drawLine(QPointF(ax + 14, cy + 6), QPointF(ax + 20, cy))

# CARGANDO 
class Spinner(QWidget):
    def __init__(self, tam=28, color="#69717D", parent=None):
        super().__init__(parent)
        self.setFixedSize(tam, tam)
        self._color = QColor(color)
        self._fase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._avanzar)

    def _avanzar(self):
        self._fase = (self._fase + 0.016) % 1.0
        self.update()

    def iniciar(self):
        self._timer.start()
        self.show()

    def detener(self):
        self._timer.stop()
        self.hide()

    def showEvent(self, e):
        if not self._timer.isActive():
            self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        em = self.width()
        p.translate(em / 2, em / 2)
        for i in range(12):
            fase = (self._fase - i * 0.083) % 1.0
            c = QColor(self._color)
            c.setAlpha(int(255 * (1 - fase)))
            p.save()
            p.rotate(30 * i)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(
                QRectF(-0.037 * em, -0.5 * em, 0.074 * em, 0.2777 * em),
                0.0555 * em,
                0.0555 * em,
            )
            p.restore()

class CampoTexto(QLineEdit):

    def __init__(self, placeholder="", password=False, alto=40, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(alto)
        if password:
            self.setEchoMode(QLineEdit.Password)
        self.setFont(fuente(10, False))
        self._hover = False
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Config.GRIS_CAMPO};
                border: 2px solid transparent;
                border-radius: 10px;
                padding-left: 12px;
                color: {Config.TEXTO_OSCURO};
            }}
            QLineEdit:hover, QLineEdit:focus {{
                background-color: #FFFFFF;
                border: 2px solid {Config.AZUL_INPUT};
            }}
        """)
        self._efecto = sombra(self, Config.AZUL_INPUT, 0, 0, 70)
        self._anim = QPropertyAnimation(self._efecto, b"blurRadius", self)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def _resplandor(self):
        activo = self._hover or self.hasFocus()
        self._anim.stop()
        self._anim.setStartValue(self._efecto.blurRadius())
        self._anim.setEndValue(16 if activo else 0)
        self._anim.start()

    def enterEvent(self, e):
        self._hover = True
        self._resplandor()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._resplandor()
        super().leaveEvent(e)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._resplandor()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._resplandor()

class GlassRadioGroup(QWidget):
    seleccion_cambiada = Signal(int, str)

    def __init__(
        self,
        opciones,
        colores=None,
        color_fondo="rgba(53, 66, 119, 24)",
        color_texto="#7D8A95",
        color_texto_activo="#FFFFFF",
        parent=None,
    ):
        super().__init__(parent)
        self._opciones = list(opciones)
        self._colores = colores or [Config.AZUL_BOTON, Config.AZUL_ENTRAR, Config.AZUL_PRINCIPAL]
        self._indice = 0
        self._botones = []

        self.setObjectName("glassRadioGroup")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #glassRadioGroup {{
                background-color: {color_fondo};
                border: 1px solid rgba(53, 66, 119, 50);
                border-radius: 16px;
            }}
        """)
        self.setMinimumHeight(48)

        self._glider = QFrame(self)
        self._glider.setObjectName("glassGlider")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(0)

        for i, texto in enumerate(self._opciones):
            b = QPushButton(texto)
            b.setCheckable(True)
            b.setFlat(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(fuente(9, True, 0.3))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none;
                    color: {color_texto}; padding: 10px 18px;
                }}
                QPushButton:hover, QPushButton:checked {{ color: {color_texto_activo}; }}
            """)
            b.clicked.connect(lambda _=False, k=i: self.seleccionar(k))
            lay.addWidget(b, 1)
            self._botones.append(b)

        self._botones[0].setChecked(True)
        self._glider.lower()
        self._anim = QPropertyAnimation(self._glider, b"geometry", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.OutBack)

    def _colorear(self):
        c = QColor(self._colores[self._indice % len(self._colores)])
        claro = QColor(c).lighter(130).name()
        self._glider.setStyleSheet(f"""
            #glassGlider {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {c.name()}, stop:1 {claro});
                border-radius: 13px;
            }}
        """)

    def seleccionar(self, indice):
        if not 0 <= indice < len(self._botones):
            return
        for i, b in enumerate(self._botones):
            b.setChecked(i == indice)
        self._indice = indice
        self._colorear()
        self._anim.stop()
        self._anim.setStartValue(self._glider.geometry())
        self._anim.setEndValue(self._botones[indice].geometry())
        self._anim.start()
        self.seleccion_cambiada.emit(indice, self._opciones[indice])

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._glider.setGeometry(self._botones[self._indice].geometry())
        self._colorear()

    def showEvent(self, e):
        super().showEvent(e)
        self._glider.setGeometry(self._botones[self._indice].geometry())
        self._colorear()

    def obtener_seleccion(self):
        return self._opciones[self._indice]

    def indice_actual(self):
        return self._indice

# NAVEGACIÓN VERTICAL  
class _ItemBarra(_BotonAnimado):
    def __init__(self, texto, icono=None, parent=None):
        super().__init__(texto, icono, parent)
        self.setFixedHeight(46)
        self._expansion = 0.0
        self._activo = False
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.InQuad)

    def poner_expansion(self, v):
        self._expansion = v
        self.update()

    def poner_activo(self, activo):
        self._activo = activo
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
        p.setClipPath(ruta)

        if self._activo:
            c = QColor(Config.AZUL_PRINCIPAL)
            c.setAlpha(34)
            p.fillPath(ruta, c)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEEEEE"))
        p.drawRoundedRect(QRectF((1 - self._t) * w, 0, w, h), 8, 8)

        ix, iy = 14, (h - 24) / 2
        if not self.icon().isNull():
            p.drawPixmap(int(ix), int(iy), self.icon().pixmap(24, 24))
        else:
            p.setPen(QPen(QColor(Config.AZUL_PRINCIPAL), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(ix, iy, 24, 24))
            p.setFont(fuente(9, True))
            p.drawText(QRectF(ix, iy, 24, 24), Qt.AlignCenter, self._texto[:1].upper())

        if self._expansion > 0.05:
            p.setOpacity(self._expansion)
            p.setFont(fuente(9, True))
            p.setPen(QColor(Config.TEXTO_OSCURO))
            p.translate((1 - self._expansion) * 20, 0)
            p.drawText(QRectF(52, 0, w - 52, h), Qt.AlignVCenter | Qt.AlignLeft, self._texto)


class _Panel(QFrame):
    def __init__(self, al_entrar, al_salir, parent=None):
        super().__init__(parent)
        self._entrar, self._salir = al_entrar, al_salir

    def enterEvent(self, e):
        self._entrar()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._salir()
        super().leaveEvent(e)


class BarraVertical(QWidget):
    seleccionado = Signal(int, str)
    ANCHO_MIN = 70
    ANCHO_MAX = 190

    def __init__(self, opciones, parent=None):
        super().__init__(parent)
        self._exp = 0.0
        self._items = []
        self._textos = []
        self.setFixedWidth(self.ANCHO_MAX)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._panel = _Panel(lambda: self._ir(1.0), lambda: self._ir(0.0))
        self._panel.setObjectName("barraPanel")
        self._panel.setAttribute(Qt.WA_StyledBackground, True)
        self._panel.setStyleSheet(f"""
            #barraPanel {{ background-color: #FFFFFF; border-radius: 15px; }}
        """)
        self._panel.setFixedWidth(self.ANCHO_MIN)
        sombra(self._panel, "#000000", 28, 8, 60)
        lay.addWidget(self._panel, 0, Qt.AlignLeft | Qt.AlignTop)

        col = QVBoxLayout(self._panel)
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(4)
        for i, op in enumerate(opciones):
            texto, funcion, icono = (tuple(op) + (None, None))[:3]
            item = _ItemBarra(texto, icono)
            item.clicked.connect(lambda _=False, k=i, f=funcion: self._elegir(k, f))
            col.addWidget(item)
            self._items.append(item)
            self._textos.append(texto)

        self._anim = QPropertyAnimation(self, b"expansion", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_exp(self):
        return self._exp

    def _set_exp(self, v):
        self._exp = v
        self._panel.setFixedWidth(int(self.ANCHO_MIN + (self.ANCHO_MAX - self.ANCHO_MIN) * v))
        for it in self._items:
            it.poner_expansion(v)

    expansion = Property(float, _get_exp, _set_exp)

    def _ir(self, destino):
        self._anim.stop()
        self._anim.setStartValue(self._exp)
        self._anim.setEndValue(destino)
        self._anim.start()

    def _elegir(self, indice, funcion):
        self.seleccionar(indice)
        if funcion:
            funcion()

    def seleccionar(self, indice):
        for i, it in enumerate(self._items):
            it.poner_activo(i == indice)
        self.seleccionado.emit(indice, self._textos[indice])


# --------------------------------------------------------------------------
# ACCIONES DEL SISTEMA  (.radio-group de tarjetas)
# --------------------------------------------------------------------------
class _ItemAccion(_BotonAnimado):
    def __init__(self, texto, parent=None):
        super().__init__(texto, None, parent)
        self._s = 0.0
        self.setFixedHeight(54)
        self._anim_sel = QPropertyAnimation(self, b"seleccion", self)
        self._anim_sel.setDuration(300)
        self._anim_sel.setEasingCurve(QEasingCurve.OutBack)

    def _get_s(self):
        return self._s

    def _set_s(self, v):
        self._s = v
        self.update()

    seleccion = Property(float, _get_s, _set_s)

    def marcar(self, activo):
        self._anim_sel.stop()
        self._anim_sel.setStartValue(self._s)
        self._anim_sel.setEndValue(1.0 if activo else 0.0)
        self._anim_sel.start()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t, s = self._t, self._s
        w, h = self.width(), self.height()
        k = 0.97 if self._presionado else 1.0
        p.translate(w / 2, h / 2)
        p.scale(k, k)
        p.translate(-w / 2, -h / 2)

        oscuro = Config.BOTON_OSCURO
        caja = QRectF(0.5 + 5 * t, 0.5, w - 9, h - 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(22 * max(t, s))))
        p.drawRoundedRect(caja.translated(0, 3), 14, 14)

        borde = mezclar(mezclar("#DDDDDD", oscuro, t), oscuro, s)
        p.setPen(QPen(borde, 1))
        p.setBrush(mezclar("#FFFFFF", oscuro, s))
        p.drawRoundedRect(caja, 14, 14)

        cx, cy = caja.left() + 29, caja.center().y()
        if s > 0:
            p.setPen(QPen(QColor(255, 255, 255, int(64 * s)), 1))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 18 * (0.4 + 0.6 * s), 18 * (0.4 + 0.6 * s))
        col = mezclar(oscuro, "#FFFFFF", s)
        p.setPen(QPen(col, 2))
        p.setBrush(mezclar("#FFFFFF", oscuro, s))
        p.drawEllipse(QPointF(cx, cy), 10, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(cx, cy), 4 * s, 4 * s)

        p.setFont(fuente(10, True, 0.3))
        p.setPen(col)
        p.drawText(QRectF(cx + 25 + 3 * t, caja.top(), w, caja.height()), Qt.AlignVCenter | Qt.AlignLeft, self._texto)


class ListaAcciones(QWidget):
    """Lista vertical de acciones (Alta, Baja, Modificar, ...). acciones = [texto | (texto, funcion)]"""

    accion_elegida = Signal(int, str)

    def __init__(self, acciones, ancho=260, parent=None):
        super().__init__(parent)
        self.setFixedWidth(ancho)
        self._items = []
        self._textos = []
        self._indice = -1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        for i, a in enumerate(acciones):
            texto, funcion = (a, None) if isinstance(a, str) else ((tuple(a) + (None,))[:2])
            item = _ItemAccion(texto)
            item.clicked.connect(lambda _=False, k=i, f=funcion: self._elegir(k, f))
            lay.addWidget(item)
            self._items.append(item)
            self._textos.append(texto)

    def _elegir(self, indice, funcion):
        self.seleccionar(indice)
        if funcion:
            funcion()

    def seleccionar(self, indice):
        self._indice = indice
        for i, it in enumerate(self._items):
            it.marcar(i == indice)
        self.accion_elegida.emit(indice, self._textos[indice])

    def seleccion_actual(self):
        return self._textos[self._indice] if self._indice >= 0 else None


# --------------------------------------------------------------------------
# FORMULARIOS / TARJETA OSCURA  (.form)
# --------------------------------------------------------------------------
from PySide6.QtCore import QEvent  # noqa: E402


class CampoFlotante(QWidget):
    def __init__(self, etiqueta, password=False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self._f = 0.0
        self.entrada = QLineEdit(self)
        if password:
            self.entrada.setEchoMode(QLineEdit.Password)
        self.entrada.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Config.FONDO_FORM_CAMPO};
                color: #3c3c3c;
                border: 1px solid rgba(105, 105, 105, 100);
                border-radius: 10px;
                padding: 19px 5px 3px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {Config.AZUL_FORM}; }}
        """)
        self._etiqueta = QLabel(etiqueta, self)
        self._etiqueta.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._anim = QPropertyAnimation(self, b"flota", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.entrada.textChanged.connect(lambda _texto: self._revisar())
        self.entrada.installEventFilter(self)
        self._colocar()

    def _get_f(self):
        return self._f

    def _set_f(self, v):
        self._f = v
        self._colocar()

    flota = Property(float, _get_f, _set_f)

    def _revisar(self, foco=None):
        if foco is None:
            foco = self.entrada.hasFocus()
        destino = 1.0 if (foco or self.entrada.text()) else 0.0
        if destino != self._anim.endValue():
            self._anim.stop()
            self._anim.setStartValue(self._f)
            self._anim.setEndValue(destino)
            self._anim.start()

    def eventFilter(self, obj, ev):
        # Se reacciona al evento directamente (sin QTimer diferido): un temporizador
        # pendiente fallaba con "already deleted" al cerrar la ventana.
        if obj is self.entrada:
            if ev.type() == QEvent.FocusIn:
                self._revisar(True)
            elif ev.type() == QEvent.FocusOut:
                self._revisar(False)
        return super().eventFilter(obj, ev)

    def _colocar(self):
        f = self._f
        c = mezclar(QColor(128, 128, 128, 128), Config.AZUL_FORM, f)
        self._etiqueta.setFont(fuente(9.5 - 2.5 * f, f > 0.5, 0))
        self._etiqueta.setStyleSheet(
            f"color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()}); background: transparent;"
        )
        self._etiqueta.adjustSize()
        self._etiqueta.move(11, int(14 * (1 - f) + 3 * f))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.entrada.setGeometry(0, 0, self.width(), self.height())
        self._etiqueta.raise_()

    def valor(self):
        return self.entrada.text()

    def limpiar(self):
        self.entrada.clear()

class TituloPulso(QWidget):
    def __init__(self, texto, icono=None, parent=None):
        super().__init__(parent)
        self._texto = texto
        self._p = 0.0
        self._pixmap = None

        if icono:
            pm = QPixmap(str(icono))
            if not pm.isNull():
                self._pixmap = pm.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.setFixedHeight(40 if self._pixmap else 36)

        # La bolita animada solo se usa cuando no hay icono
        self._anim = QPropertyAnimation(self, b"pulso", self)
        self._anim.setDuration(1000)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Linear)
        if self._pixmap is None:
            self._anim.start()

    def _get_p(self):
        return self._p

    def _set_p(self, v):
        self._p = v
        self.update()

    pulso = Property(float, _get_p, _set_p)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        h = self.height()
        c = QColor(Config.AZUL_FORM)

        if self._pixmap is not None:
            p.drawPixmap(0, (h - self._pixmap.height()) // 2, self._pixmap)
            x_texto = self._pixmap.width() + 10
        else:
            centro = QPointF(10, h / 2)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawEllipse(centro, 9, 9)
            onda = QColor(c)
            onda.setAlphaF(1 - self._p)
            p.setBrush(onda)
            r = 9 * (0.9 + 0.9 * self._p)
            p.drawEllipse(centro, r, r)
            x_texto = 32

        p.setFont(fuente(17, True, -1))
        p.setPen(c)
        p.drawText(QRectF(x_texto, 0, self.width() - x_texto, h), Qt.AlignVCenter | Qt.AlignLeft, self._texto)
        
class TarjetaFormulario(QFrame):
    enviado = Signal()

    def __init__(self, titulo, mensaje="", campos=(), texto_boton="Enviar", pie="", ancho=350, parent=None, icono=None):
        super().__init__(parent)
        self.setObjectName("tarjetaFormulario")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(ancho)
        self.setStyleSheet(f"""
            #tarjetaFormulario {{
                background-color: {Config.FONDO_FORM};
                border: 1px solid {Config.FONDO_FORM_BORDE};
                border-radius: 20px;
            }}
        """)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(20, 20, 20, 20)
        self._lay.setSpacing(10)
        # Fila de logos: se inserta arriba la primera vez que se llama a agregar_logo()
        self.fila_logos = QHBoxLayout()
        self.fila_logos.setAlignment(Qt.AlignCenter)
        self.fila_logos.setSpacing(50)
        self._fila_logos_puesta = False

        self._lay.addWidget(TituloPulso(titulo, icono))
        if mensaje:
            m = QLabel(mensaje)
            m.setWordWrap(True)
            m.setStyleSheet("color: rgba(0,0,0,178); font-size: 14px; background: transparent; font-weight:bold;")
            self._lay.addWidget(m)

        self.campos = {}
        for c in campos:
            etiqueta, pw = (c, False) if isinstance(c, str) else (c[0], bool(c[1]))
            campo = CampoFlotante(etiqueta, pw)
            self.campos[etiqueta] = campo
            self._lay.addWidget(campo)

        # texto_boton=None -> sin botón de envío (el módulo pone el suyo con agregar_widget)
        self.boton_enviar = None
        if texto_boton:
            self.boton_enviar = QPushButton(texto_boton)
            self.boton_enviar.setCursor(Qt.PointingHandCursor)
            self.boton_enviar.setFont(fuente(11, False))
            self.boton_enviar.setFixedHeight(42)
            self.boton_enviar.setStyleSheet(f"""
                QPushButton {{ background-color: {Config.AZUL_FORM}; color: #FFFFFF;
                               border: none; border-radius: 10px; }}
                QPushButton:hover {{ background-color: #00A6E0; }}
            """)
            self.boton_enviar.clicked.connect(self.enviado.emit)
            self._lay.addWidget(self.boton_enviar)

        if pie:
            f = QLabel(pie)
            f.setAlignment(Qt.AlignCenter)
            f.setStyleSheet(f"color: {Config.TEXTO_SUBTITULO}; font-size: 12px; background: transparent;")
            self._lay.addWidget(f)

    def agregar_logo(self, ruta, ancho=100, alto=70):
        imagen = QPixmap(str(ruta))

        if imagen.isNull():
            print(f"No se pudo cargar el logo: {ruta}")
            return

        etiqueta = QLabel()
        etiqueta.setFixedSize(ancho, alto)
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setStyleSheet(
            "background: transparent; border: none;"
        )
        etiqueta.setPixmap(
            imagen.scaled(
                ancho,
                alto,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.fila_logos.addWidget(etiqueta)
        if not self._fila_logos_puesta:
            self._lay.insertLayout(0, self.fila_logos)
            self._fila_logos_puesta = True

    def _posicion_insercion(self):
        if self.boton_enviar is not None:
            return self._lay.indexOf(self.boton_enviar)
        return self._lay.count()

    def agregar_widget(self, widget, alineacion=None):
        """Inserta un widget antes del botón de envío (o al final si no hay botón)."""
        if alineacion is None:
            self._lay.insertWidget(self._posicion_insercion(), widget)
        else:
            self._lay.insertWidget(self._posicion_insercion(), widget, 0, alineacion)

    def agregar_campo(self, etiqueta, password=False):
        """Agrega un campo flotante en el orden actual y lo devuelve."""
        campo = CampoFlotante(etiqueta, password)
        self.campos[etiqueta] = campo
        self.agregar_widget(campo)
        return campo

    def valores(self):
        return {k: v.valor() for k, v in self.campos.items()}

    def limpiar(self):
        for c in self.campos.values():
            c.limpiar()

# ======================================================================
#  MENÚ PRINCIPAL: cabecera + tarjetas con opciones y subopciones
# ======================================================================
def icono_casa(tam=44, color="#FFFFFF"):
    """Casita dibujada por código (se usa si no hay imagen en recursos)."""
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c, tam * 0.07, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    m = tam * 0.12
    techo = QPolygonF([QPointF(m, tam * 0.48), QPointF(tam / 2, m), QPointF(tam - m, tam * 0.48)])
    p.drawPolyline(techo)
    p.drawRect(QRectF(tam * 0.22, tam * 0.48, tam * 0.56, tam * 0.40))      # cuerpo
    p.drawRect(QRectF(tam * 0.43, tam * 0.62, tam * 0.14, tam * 0.26))      # puerta
    p.end()
    return pm


class CabeceraMenu(QWidget):
    """Fila superior: [icono] TÍTULO ........ [botón a la derecha]."""

    def __init__(self, titulo, icono=None, boton=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        etiqueta_icono = QLabel()
        etiqueta_icono.setFixedSize(46, 46)
        etiqueta_icono.setAlignment(Qt.AlignCenter)
        if icono:
            pm = (icono if isinstance(icono, QIcon) else QIcon(str(icono))).pixmap(44, 44)
        else:
            pm = QPixmap()
        if pm.isNull():
            pm = icono_casa(44, Config.TEXTO_CLARO)
        etiqueta_icono.setPixmap(pm)
        lay.addWidget(etiqueta_icono)

        self.titulo = QLabel(titulo)
        self.titulo.setFont(fuente(30, True, 2))
        self.titulo.setStyleSheet(f"color: {Config.TEXTO_CLARO}; background: transparent;")
        lay.addWidget(self.titulo)
        lay.addStretch()

        if boton is not None:
            lay.addWidget(boton, 0, Qt.AlignVCenter)


class _ItemMenu(QPushButton):
    """Opción clicable de una tarjeta de menú (texto plano, resalta al pasar el mouse)."""

    def __init__(self, texto, nivel=0, parent=None):
        super().__init__(texto, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setFixedHeight(32)
        self.setFont(fuente(10.5, False, 0.2))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Config.TEXTO_OSCURO};
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: {10 + nivel * 20}px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 191, 255, 38);
                color: {Config.AZUL_ENTRAR};
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 191, 255, 80);
            }}
        """)


class TarjetaMenu(QFrame):
    """
    Tarjeta clara con título (y icono opcional) y una lista de opciones.
    items: ["Consultas",
            ("Inscripciones", ["Alta de alumno", "Baja de alumno"]),   # grupo con subopciones
            ...]
    Al hacer clic emite  seleccionado("TÍTULO/Grupo/Opción").
    """
    seleccionado = Signal(str)

    def __init__(self, titulo, items, icono=None, parent=None, iconos=None):
        super().__init__(parent)
        self._titulo = titulo
        self._iconos = iconos or {}      # {"TÍTULO/Opción": "archivo.png"} (carpeta recursos)
        self.setObjectName("tarjetaMenu")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #tarjetaMenu {{
                background-color: {Config.FONDO_FORM};
                border: 1px solid {Config.FONDO_FORM_BORDE};
                border-radius: 18px;
            }}
        """)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(18, 18, 18, 18)
        self._lay.setSpacing(2)

        # encabezado: icono + título
        fila = QHBoxLayout()
        fila.setSpacing(10)
        if icono:
            et = QLabel()
            et.setStyleSheet("background: transparent;")
            qicono = icono if isinstance(icono, QIcon) else QIcon(str(icono))
            et.setPixmap(qicono.pixmap(24, 24))
            fila.addWidget(et)
        t = QLabel(titulo)
        t.setFont(fuente(13, True, 1))
        t.setStyleSheet(f"color: {Config.TEXTO_OSCURO}; background: transparent;")
        fila.addWidget(t)
        fila.addStretch()
        self._lay.addLayout(fila)

        linea = QFrame()
        linea.setFixedHeight(2)
        linea.setStyleSheet(f"background-color: {Config.AZUL_FORM}; border: none; border-radius: 1px;")
        self._lay.addSpacing(4)
        self._lay.addWidget(linea)
        self._lay.addSpacing(8)

        for item in items:
            self._agregar(item, 0, titulo)
        self._lay.addStretch()

    def _poner_icono(self, boton, ruta):
        nombre = self._iconos.get(ruta)
        archivo = ruta_recurso(nombre) if nombre else None
        if archivo:
            boton.setIcon(QIcon(str(archivo)))
            boton.setIconSize(QSize(18, 18))

    def _agregar(self, item, nivel, ruta):
        if isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[1], (list, tuple)):
            grupo, hijos = item
            etiqueta = _ItemMenu(grupo, nivel, self)          # el grupo también se puede abrir
            etiqueta.setFont(fuente(10.5, True, 0.2))
            etiqueta.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {Config.AZUL_ENTRAR};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: {10 + nivel * 20}px;
                }}
                QPushButton:hover {{ background-color: rgba(0, 191, 255, 38); }}
                QPushButton:pressed {{ background-color: rgba(0, 191, 255, 80); }}
            """)
            etiqueta.clicked.connect(lambda _=False, r=f"{ruta}/{grupo}": self.seleccionado.emit(r))
            self._poner_icono(etiqueta, f"{ruta}/{grupo}")
            self._lay.addWidget(etiqueta)
            for hijo in hijos:
                self._agregar(hijo, nivel + 1, f"{ruta}/{grupo}")
        else:
            boton = _ItemMenu(item, nivel, self)
            boton.clicked.connect(lambda _=False, r=f"{ruta}/{item}": self.seleccionado.emit(r))
            self._poner_icono(boton, f"{ruta}/{item}")
            self._lay.addWidget(boton)


class VentanaBase(QWidget):

    def __init__(self, titulo="SIGEA", ancho=900, alto=600):
        super().__init__()
        self.configurar_ventana(titulo, ancho, alto)

    # ---------- ventana ----------
    def configurar_ventana(self, titulo, ancho, alto):
        self.setWindowTitle(titulo)
        self.setFixedSize(ancho, alto)
        icono = buscar_icono_app()
        if icono:
            self.setWindowIcon(QIcon(icono))
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Config.FONDO_VENTANA};
                color: {Config.TEXTO_TITULO};
                font-family: "{Config.FUENTE_BASE}";
            }}
        """)

    def centrar_ventana(self):
        pantalla = self.screen().availableGeometry()
        ventana = self.frameGeometry()
        self.move(pantalla.center() - ventana.center())

    def mostrar_mensaje(self, titulo, mensaje):
        QMessageBox.information(self, titulo, mensaje)

    def mostrar_advertencia(self, titulo, mensaje):
        QMessageBox.warning(self, titulo, mensaje)

    #  botones 
    def _preparar(self, boton, funcion, ancho, alto):
        boton.setFixedSize(ancho, alto)
        if funcion:
            boton.clicked.connect(funcion)
        return boton

    def crear_boton(self, texto, funcion=None, ancho=320, alto=52, icono=None):
        """Botón inicial / general (azul con halo)."""
        return self._preparar(BotonSombra(texto, icono, self), funcion, ancho, alto)

    def crear_boton_salida(self, texto, funcion=None, ancho=200, alto=48, icono=None):
        """Botón de salida (rojo)."""
        return self._preparar(BotonSalida(texto, icono, self), funcion, ancho, alto)

    def crear_boton_secundario(self, texto, funcion=None, ancho=200, alto=50, icono=None):
        """Botón secundario (pill blanco -> azul)."""
        return self._preparar(BotonSecundario(texto, icono, self), funcion, ancho, alto)

    def crear_boton_entrar(self, texto, funcion=None, ancho=308, alto=52, icono=None):
        """Botón para entrar al sistema (con brillo y flecha)."""
        return self._preparar(BotonEntrar(texto, icono, self), funcion, ancho, alto)

    #  cargando 
    def crear_spinner(self, tam=28, color="#69717D"):
        return Spinner(tam, color, self)

    #  selectores y navegación 
    def crear_glass_radio_group(self, opciones, **kw):
        return GlassRadioGroup(opciones, parent=self, **kw)

    def crear_barra_vertical(self, opciones):
        """opciones: [(texto, funcion[, icono]), ...]"""
        return BarraVertical(opciones, self)

    def crear_lista_acciones(self, acciones, ancho=260):
        """acciones: ['Alta', 'Baja', ...] o [(texto, funcion), ...]"""
        return ListaAcciones(acciones, ancho, self)

    #  tarjetas y formularios 
    def crear_tarjeta(self, ancho, alto, radio=24):
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        tarjeta.setFixedSize(ancho, alto)
        tarjeta.setStyleSheet(f"""
            #tarjeta {{
                background-color: {Config.FONDO_TARJETA};
                border-radius: {radio}px;
            }}
        """)
        return tarjeta

    def crear_formulario(self, titulo, mensaje="", campos=(), texto_boton="Enviar", pie="", ancho=250, icono=None):
        return TarjetaFormulario(titulo, mensaje, campos, texto_boton, pie, ancho, self, icono)

    def crear_cabecera_menu(self, titulo, icono=None, boton=None):
        """Fila superior del menú: icono + título a la izquierda y un botón (Salir) a la derecha."""
        return CabeceraMenu(titulo, icono, boton, self)

    def crear_tarjeta_menu(self, titulo, items, icono=None, iconos=None):
        """Tarjeta del menú principal con opciones y subopciones (ver TarjetaMenu).
        iconos: {"ALUMNOS/Consultas": "consultas.png", ...} icono por opción."""
        return TarjetaMenu(titulo, items, icono, self, iconos)

    #  campos y labels 
    def crear_campo_texto(self, placeholder="", password=False, alto=40):
        return CampoTexto(placeholder, password, alto)

    def crear_label_titulo(self, texto, tamano=26, color=None):
        label = QLabel(texto)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color or Config.TEXTO_TITULO};
                font-size: {tamano}px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        return label

    def crear_label_subtitulo(self, texto, tamano=10, color=None, wrap=True):
        label = QLabel(texto)
        label.setWordWrap(wrap)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color or Config.TEXTO_SUBTITULO};
                font-size: {tamano}px;
                background: transparent;
            }}
        """)
        return label

    def crear_label_campo(self, texto, color=None):
        label = QLabel(texto)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color or Config.TEXTO_LABEL};
                font-size: 10px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        return label

    def crear_label_error(self, tamano=9):
        label = QLabel()
        label.setStyleSheet(f"""
            QLabel {{
                color: {Config.TEXTO_ERROR};
                font-size: {tamano}px;
                background: transparent;
            }}
        """)
        return label

    # ---------- panel institucional (columna izquierda) ----------
    def crear_panel_institucional(
        self,
        parent,
        titulo="SIGEA",
        subtitulo="Sistema de Gestión Académica",
        institucion="ZAFIRO TECH",
        rutas_logos=None,
    ):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(0)

        if rutas_logos is None:
            rutas_logos = [ruta_recurso(Config.LOGO_PRINCIPAL)]

        fila_logos = QHBoxLayout()
        fila_logos.setSpacing(14)

        for ruta in rutas_logos:
            if not ruta:
                print(f"No se encontró '{Config.LOGO_PRINCIPAL}' en la carpeta de recursos")
                continue
            imagen = QPixmap(str(ruta))

            if imagen.isNull():
                print(f"No se pudo cargar el logo: {ruta}")
                continue

            etiqueta = QLabel()
            etiqueta.setFixedSize(190, 190)
            etiqueta.setAlignment(Qt.AlignCenter)
            etiqueta.setStyleSheet("background: transparent; border: none;")
            etiqueta.setPixmap(
                imagen.scaled(
                    190,
                    190,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            fila_logos.addWidget(etiqueta)
        layout.addLayout(fila_logos)
        layout.addSpacing(35)

        layout.addWidget(self.crear_label_titulo(titulo, Config.FONT_LOGO, Config.TEXTO_CLARO))
        layout.addWidget(self.crear_label_subtitulo(subtitulo, 13, Config.CIAN, wrap=False))

        linea = QFrame()
        linea.setFixedSize(70, 3)
        linea.setStyleSheet(f"QFrame {{ background-color: {Config.CIAN}; border-radius: 1px; }}")
        layout.addSpacing(22)
        layout.addWidget(linea)
        layout.addStretch()

        pie = QHBoxLayout()
        pie.setSpacing(10)

        ruta_zafiro = ruta_recurso(Config.LOGO_ZAFIRO)
        imagen_zafiro = QPixmap(str(ruta_zafiro)) if ruta_zafiro else QPixmap()

        if not imagen_zafiro.isNull():
            logo_zafiro = QLabel()
            logo_zafiro.setFixedSize(45, 45)
            logo_zafiro.setAlignment(Qt.AlignCenter)
            logo_zafiro.setStyleSheet(
                "background: transparent; border: none;"
            )
            logo_zafiro.setPixmap(
                imagen_zafiro.scaled(
                    45,
                    45,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            pie.addWidget(logo_zafiro)
        else:
            print(f"No se encontró '{Config.LOGO_ZAFIRO}' en la carpeta de recursos")

        campus = QLabel(institucion)
        campus.setStyleSheet(
            "QLabel { color: #CBD5E1; font-size: 12px; background: transparent; }"
        )
        pie.addWidget(campus)

        layout.addLayout(pie)
        return layout