from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from Logica import secretaria as ls
from reportes.generador_pdf import generar_pdf_consulta
from ventanas.base_consulta import VentanaConsulta
from ventanas.componentes import destinos_barra_secretaria, navegar_a
from ventanas.ventana import Config

CARPETA_SALIDA = Path(__file__).resolve().parent.parent / "reportes_generados"
DESTINOS_CONSULTA = destinos_barra_secretaria()


class VentanaConsultaSecretarias(VentanaConsulta):
    COLUMNAS_PDF = ["RFC", "Nombre completo", "CURP", "Puesto", "Grado", "Usuario", "Estado"]
    ANCHOS_PDF = [90, 180, 125, 150, 100, 105, 75]
    OPCIONES_FILTRO = ["Todos", "RFC", "Nombre", "CURP", "Puesto", "Usuario"]

    def __init__(self, menu=None):
        self._secretarias = []
        self._filtro_texto = "Todas las secretarias"
        super().__init__("SIGEA - Consultas de secretarias", "CONSULTAS DE SECRETARIAS", menu)

    def _fila_totales(self):
        fila = QHBoxLayout()
        fila.setSpacing(14)
        self._numeros = {}
        for clave, texto, color in (
            ("total", "Total", Config.AZUL_ENTRAR),
            ("mujeres", "Mujeres", "#C2185B"),
            ("hombres", "Hombres", Config.AZUL_BOTON),
            ("puestos", "Puestos", "#2E7D32"),
        ):
            tarjeta = self.crear_tarjeta(190, 84, 18)
            layout = QVBoxLayout(tarjeta)
            layout.setContentsMargins(18, 10, 18, 10)
            layout.setSpacing(0)
            numero = self.crear_label_titulo("0", 30, color)
            layout.addWidget(numero)
            layout.addWidget(
                self.crear_label_campo(
                    texto.upper(), color="rgba(128, 128, 128, 200)"
                )
            )
            self._numeros[clave] = numero
            fila.addWidget(tarjeta)
        fila.addStretch()
        return fila

    def consultar(self):
        campo = self.selector_campo.obtener_seleccion()
        valor = self.campo_valor.valor().strip()
        secretarias, problema = ls.listar_secretarias(campo, valor)
        if problema:
            QMessageBox.warning(self, "Error de consulta", problema)
            return

        self._secretarias = secretarias
        self._total_resultados = len(secretarias)
        self._filtro_texto = (
            f"{campo}: {valor}" if valor and campo != "Todos"
            else (f"«{valor}»" if valor else "Todas las secretarias")
        )
        self._mostrar(secretarias)

    def _mostrar(self, secretarias):
        self._numeros["total"].setText(str(len(secretarias)))
        self._numeros["mujeres"].setText(
            str(sum(s["sexo"].casefold() == "mujer" for s in secretarias))
        )
        self._numeros["hombres"].setText(
            str(sum(s["sexo"].casefold() == "hombre" for s in secretarias))
        )
        self._numeros["puestos"].setText(
            str(len({s["puesto"] for s in secretarias if s["puesto"]}))
        )

        if not secretarias:
            self.mostrar_vacio("No se encontraron secretarias con esa búsqueda.")
            self.etiqueta_info.setText("")
            return

        self.limpiar_resultados()
        for secretaria in secretarias[:self.MAX_TARJETAS]:
            self.agregar_resultado(self._tarjeta_secretaria(secretaria))
        self.cerrar_resultados()
        self.etiqueta_info.setText(
            f"{len(secretarias)} registro(s) encontrado(s)"
            if len(secretarias) <= self.MAX_TARJETAS
            else (
                f"{len(secretarias)} registro(s). Se muestran los primeros "
                f"{self.MAX_TARJETAS}; el PDF incluye todos."
            )
        )

    def _tarjeta_secretaria(self, secretaria):
        tarjeta = QFrame()
        tarjeta.setObjectName("resultadoSecretaria")
        tarjeta.setAttribute(Qt.WA_StyledBackground, True)
        tarjeta.setFixedHeight(82)
        tarjeta.setStyleSheet(
            "#resultadoSecretaria { background-color: #FFFFFF; border-radius: 12px; }"
        )
        layout = QHBoxLayout(tarjeta)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        textos = QVBoxLayout()
        textos.setSpacing(3)
        nombre = QLabel(secretaria["nombre_completo"])
        nombre.setStyleSheet(
            f"color: {Config.TEXTO_OSCURO}; font-size: 13px; font-weight: bold; "
            "background: transparent;"
        )
        detalle = QLabel(
            f"RFC: {secretaria['rfc']}  •  CURP: {secretaria['curp'] or '-'}  "
            f"•  Usuario: {secretaria['usuario']}"
        )
        puesto = QLabel(
            f"{secretaria['puesto']}  •  {secretaria['grado_academico'] or 'Grado sin especificar'}"
        )
        for etiqueta in (detalle, puesto):
            etiqueta.setStyleSheet(
                f"color: {Config.TEXTO_SUBTITULO}; font-size: 10px; background: transparent;"
            )
        textos.addWidget(nombre)
        textos.addWidget(detalle)
        textos.addWidget(puesto)
        layout.addLayout(textos, 1)

        activo = secretaria["activo"] and secretaria["usuario_activo"]
        color = QColor("#2E7D32" if activo else "#C0392B")
        estado = QLabel("Activa" if activo else "Desactivada")
        estado.setAlignment(Qt.AlignCenter)
        estado.setStyleSheet(
            f"color: {color.name()}; font-size: 11px; font-weight: bold; "
            f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 38); "
            "border-radius: 10px; padding: 4px 14px;"
        )
        layout.addWidget(estado, 0, Qt.AlignVCenter)
        return tarjeta

    def generar_pdf(self):
        if not self._secretarias:
            self.mostrar_advertencia(
                "SIGEA", "Primero haz una consulta que tenga resultados."
            )
            return

        CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        marca = f"{datetime.now():%Y%m%d_%H%M%S}"
        ruta = CARPETA_SALIDA / f"consulta_secretarias_{marca}.pdf"
        filas = [
            [
                secretaria["rfc"],
                secretaria["nombre_completo"],
                secretaria["curp"] or "-",
                secretaria["puesto"],
                secretaria["grado_academico"] or "-",
                secretaria["usuario"],
                "Activa" if secretaria["activo"] and secretaria["usuario_activo"]
                else "Desactivada",
            ]
            for secretaria in self._secretarias
        ]
        try:
            generar_pdf_consulta(
                "CONSULTA DE SECRETARIAS",
                self.COLUMNAS_PDF,
                filas,
                str(ruta),
                anchos=self.ANCHOS_PDF,
                filtro=self._filtro_texto,
                resumen=f"Total de secretarias: {len(self._secretarias)}",
            )
            self.etiqueta_info.setText(f"PDF generado: {ruta.name}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))
        except Exception as error:
            print(f"Error al generar el PDF de secretarias: {error}")
            QMessageBox.warning(self, "Error", "No fue posible generar el PDF.")

    def _navegar(self, indice, texto):
        if indice == 1:
            return
        destinos = {
            2: DESTINOS_CONSULTA.get(1),
            3: DESTINOS_CONSULTA.get(2),
            4: DESTINOS_CONSULTA.get(3),
        }
        destino = destinos.get(indice)
        if destino:
            navegar_a(self, destino)
        else:
            self.mostrar_mensaje(texto, "Esta opción aún está en construcción.")
            self._barra.seleccionar(1)
