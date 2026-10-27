from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap

from ventanas.ventana import Config, ruta_recurso

# ----------------------------------------------------------------------
#  Estilos de la zona "Subir archivos PDF"
# ----------------------------------------------------------------------
def _estilo_boton(color, hover):
    return f"""
        QPushButton {{
            background-color: {color};
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            padding: 0 16px;
            font-size: 11px;
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:pressed {{ background-color: {hover}; padding-top: 2px; }}
    """


ESTILO_BOTON_SUBIR = _estilo_boton(Config.AZUL_ENTRAR, "#00507F")
ESTILO_BOTON_QUITAR = _estilo_boton(Config.ROJO, Config.ROJO_OSCURO)

ESTILO_COMBO_TIPO = f"""
    QComboBox {{
        background-color: #FFFFFF;
        color: {Config.TEXTO_OSCURO};
        border: 2px solid {Config.AZUL_ENTRAR};
        border-radius: 10px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: bold;
    }}
    QComboBox:hover {{ border-color: {Config.AZUL_FORM}; }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        color: {Config.TEXTO_OSCURO};
        selection-background-color: {Config.AZUL_ENTRAR};
        selection-color: #FFFFFF;
        border: 1px solid {Config.FONDO_FORM_BORDE};
        outline: 0;
    }}
"""

# ----------------------------------------------------------------------
#  Barra lateral con iconos (los archivos están en la carpeta recursos)
# ----------------------------------------------------------------------
ICONOS_BARRA = {
    "Menú principal": "inicio.png",
    "Alta": "altaalumno-icono.png",
    "Baja": "baja-icono.png",
    "Modificar": "modificar-icono.png",
    "Consultar": "consulta-icono.png",
}


def opciones_barra(volver, orden=("Alta", "Baja", "Modificar", "Consultar")):
    """Opciones para crear_barra_vertical: [(texto, funcion, icono), ...]."""
    items = [("Menú principal", volver, ruta_recurso(ICONOS_BARRA["Menú principal"]))]
    for nombre in orden:
        items.append((nombre, None, ruta_recurso(ICONOS_BARRA[nombre])))
    return items


# ----------------------------------------------------------------------
#  Insignia de usuario (esquina del menú)
# ----------------------------------------------------------------------
def icono_usuario(tam=28, color=Config.AZUL_ENTRAR):
    """Persona dibujada por código (se usa si no existe iconosesion.png)."""
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QPointF(tam / 2, tam * 0.34), tam * 0.19, tam * 0.19)
    p.drawEllipse(QRectF(tam * 0.16, tam * 0.60, tam * 0.68, tam * 0.80))
    p.end()
    return pm


class InsigniaUsuario(QFrame):
    """Píldora blanca con el icono de sesión y el nombre de quien inició sesión."""

    def __init__(self, nombre, parent=None):
        super().__init__(parent)
        self.setObjectName("insigniaUsuario")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(40)
        self.setStyleSheet(
            "#insigniaUsuario { background-color: #FFFFFF; border-radius: 20px; }"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 16, 4)
        lay.setSpacing(8)

        icono = QLabel()
        icono.setFixedSize(28, 28)
        icono.setAlignment(Qt.AlignCenter)
        icono.setStyleSheet("background: transparent;")
        ruta = ruta_recurso("iconosesion.png")
        pm = QPixmap(str(ruta)) if ruta else QPixmap()
        if pm.isNull():
            pm = icono_usuario(28)
        else:
            pm = pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icono.setPixmap(pm)
        lay.addWidget(icono)

        nombre = nombre or "Usuario"
        etiqueta = QLabel(nombre)
        etiqueta.setToolTip(nombre)
        etiqueta.setMaximumWidth(220)
        etiqueta.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 12px; font-weight: bold; "
            "background: transparent;"
        )
        lay.addWidget(etiqueta)