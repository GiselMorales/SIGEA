from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from Logica import docentes as ld
from reportes.generador_pdf import generar_pdf_consulta
from ventanas.base_consulta import VentanaConsulta
from ventanas.componentes import (
    ORDEN_BARRA_DOCENTE,
    destinos_barra_docente,
    navegar_a,
)
from ventanas.ventana import Config

CARPETA_SALIDA = (
    Path(__file__).resolve().parent.parent / "reportes_generados"
)


class VentanaConsultaDocentes(VentanaConsulta):
    COLUMNAS_PDF = ["RFC", "Nombre completo", "Usuario"]
    ANCHOS_PDF = [100, 260, 140]
    OPCIONES_FILTRO = ["Todos", "RFC", "Nombre", "Usuario"]
    ORDEN_BARRA = ORDEN_BARRA_DOCENTE
    INDICE_BARRA = 3
    DESTINOS_BARRA = destinos_barra_docente()

    def __init__(self, menu=None):
        self._docentes = []
        self._filtro_texto = "Todos los docentes"
        super().__init__(
            "SIGEA - Consultas de docentes", "CONSULTAS DE DOCENTES", menu
        )

    def _fila_totales(self):
        fila = QHBoxLayout()
        fila.setSpacing(14)
        tarjeta = self.crear_tarjeta(190, 84, 18)
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(18, 10, 18, 10)
        self._total = self.crear_label_titulo("0", 30, Config.AZUL_ENTRAR)
        layout.addWidget(self._total)
        layout.addWidget(
            self.crear_label_campo(
                "TOTAL", color="rgba(128, 128, 128, 200)"
            )
        )
        fila.addWidget(tarjeta)
        fila.addStretch()
        return fila

    def consultar(self):
        criterio = self.selector_campo.obtener_seleccion()
        valor = self.campo_valor.valor().strip()
        docentes, problema = ld.listar_docentes(criterio, valor)
        if problema:
            QMessageBox.warning(self, "Error de consulta", problema)
            return

        self._docentes = docentes
        self._total_resultados = len(docentes)
        self._filtro_texto = (
            f"{criterio}: {valor}" if valor and criterio != "Todos"
            else (f"«{valor}»" if valor else "Todos los docentes")
        )
        self._mostrar(docentes)

    def _mostrar(self, docentes):
        self._total.setText(str(len(docentes)))

        if not docentes:
            self.mostrar_vacio("No se encontraron docentes con esa búsqueda.")
            self.etiqueta_info.setText("")
            return

        self.limpiar_resultados()
        for docente in docentes[:self.MAX_TARJETAS]:
            self.agregar_resultado(self._tarjeta_docente(docente))
        self.cerrar_resultados()
        self.etiqueta_info.setText(
            f"{len(docentes)} registro(s) encontrado(s)"
            if len(docentes) <= self.MAX_TARJETAS
            else (
                f"{len(docentes)} registro(s). Se muestran los primeros "
                f"{self.MAX_TARJETAS}; el PDF incluye todos."
            )
        )

    def _tarjeta_docente(self, docente):
        tarjeta = QFrame()
        tarjeta.setObjectName("resultadoDocente")
        tarjeta.setAttribute(Qt.WA_StyledBackground, True)
        tarjeta.setFixedHeight(82)
        tarjeta.setStyleSheet(
            "#resultadoDocente { background-color: #FFFFFF; border-radius: 12px; }"
        )
        layout = QHBoxLayout(tarjeta)
        layout.setContentsMargins(16, 10, 16, 10)
        textos = QVBoxLayout()
        nombre = QLabel(docente["nombre_completo"])
        nombre.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 13px; font-weight: bold; "
            "background: transparent;"
        )
        for texto in (
            f"RFC: {docente['rfc']}",
            f"Usuario: {docente['usuario']}",
        ):
            etiqueta = QLabel(texto)
            etiqueta.setStyleSheet(
                f"color: {Config.TEXTO_SUBTITULO}; font-size: 10px; "
                "background: transparent;"
            )
            textos.addWidget(etiqueta)
        textos.insertWidget(0, nombre)
        layout.addLayout(textos, 1)

        return tarjeta

    def generar_pdf(self):
        if not self._docentes:
            self.mostrar_advertencia(
                "SIGEA", "Primero haz una consulta que tenga resultados."
            )
            return

        try:
            CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
            marca = f"{datetime.now():%Y%m%d_%H%M%S}"
            ruta = CARPETA_SALIDA / f"consulta_docentes_{marca}.pdf"
            filas = [
                [
                    docente["rfc"],
                    docente["nombre_completo"],
                    docente["usuario"],
                ]
                for docente in self._docentes
            ]
            generar_pdf_consulta(
                "CONSULTA DE DOCENTES",
                self.COLUMNAS_PDF,
                filas,
                str(ruta),
                anchos=self.ANCHOS_PDF,
                filtro=self._filtro_texto,
                resumen=f"Total de docentes: {len(self._docentes)}",
                orientacion="portrait",
            )
            self.etiqueta_info.setText(f"PDF generado: {ruta.name}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))
        except Exception as error:
            print(f"Error al generar el PDF de docentes: {error}")
            QMessageBox.warning(self, "Error", "No fue posible generar el PDF.")

    def _navegar(self, indice, texto):
        if indice in (0, self.INDICE_BARRA):
            return
        destino = self.DESTINOS_BARRA.get(indice)
        if destino:
            navegar_a(self, destino)
        else:
            self.mostrar_mensaje(texto, "Esta opción aún está en construcción.")
            self._barra.seleccionar(self.INDICE_BARRA)
