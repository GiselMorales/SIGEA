import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QVBoxLayout

from Logica import validaciones as v
from Logica import horarios as lh
from reportes.generador_pdf import generar_pdf_horario, generar_pdf_lista_grupo
from ventanas.base_alta import VentanaAlta
from ventanas.componentes import ESTILO_COMBO_TIPO

# Los PDF se guardan en <proyecto>/reportes_generados
CARPETA_SALIDA = Path(__file__).resolve().parent.parent / "reportes_generados"
RE_CLAVE_MATERIA = re.compile(r"^[A-Z]{3}-\d{4}$")


class _VentanaReporte(VentanaAlta):
    """Pide periodo, semestre y turno y genera el PDF (se abre solo al terminar)."""

    PIDE_MATERIA = False
    PIDE_GRUPO = True

    def __init__(self, titulo_ventana, titulo, menu=None):
        super().__init__(titulo_ventana, titulo, "GENERAR PDF", menu)

    def construir_secciones(self):
        self._grupos_reporte = []
        campos = [
            self.campo("periodo", "Periodo (ej. AGO-DIC 2026)",
                       lh.listar_periodos() or v.periodos_disponibles()),
            self.campo("semestre", "Semestre", v.SEMESTRES),
            self.selector("turno", "Turno", ["Matutino", "Vespertino"]),
        ]
        filas = [self.fila(*campos, pesos=(3, 1, 3))]
        if self.PIDE_MATERIA:
            filas.append(self.fila(
                self.campo("materia", "Materia (opcional, ej. ACF-0901)"), None, pesos=(1, 1),
            ))
        self.agregar_seccion(
            "DATOS DEL REPORTE", filas, self._validar_datos_reporte
        )
        if self.PIDE_GRUPO:
            selector = self._selector_grupo()
            self.agregar_seccion(
                "GRUPO DEL REPORTE", [selector], self._validar_grupo
            )

    def _selector_grupo(self):
        self._combo_grupo = QComboBox()
        self._combo_grupo.setFixedHeight(40)
        self._combo_grupo.setCursor(Qt.PointingHandCursor)
        self._combo_grupo.setStyleSheet(ESTILO_COMBO_TIPO)
        self._combo_grupo.addItem("Valida primero periodo, semestre y turno", None)
        self._combo_grupo.currentIndexChanged.connect(
            lambda _i: self._cambio("clave_grupo")
        )
        self._registrar_lector(
            "clave_grupo", self._combo_grupo.currentData, self._combo_grupo
        )
        caja = self._contenedor("selectorGrupoReporte")
        layout = QVBoxLayout(caja)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.crear_label_campo(
            "GRUPO", color="rgba(128, 128, 128, 178)"
        ))
        layout.addWidget(self._combo_grupo)
        return caja

    def _validar_datos_reporte(self, datos):
        errores, limpio = {}, {}

        periodo = re.sub(r"\s*-\s*", "-", v.espacios(datos.get("periodo")).upper())
        limpio["periodo"] = periodo
        if not periodo:
            errores["periodo"] = "Periodo: es obligatorio."
        elif periodo not in lh.listar_periodos():
            errores["periodo"] = "Periodo: no está dado de alta en periodos_escolares."

        msg, semestre = v._validar_semestre(datos.get("semestre"))
        limpio["semestre"] = semestre
        if msg:
            errores["semestre"] = msg

        turno = v.espacios(datos.get("turno"))
        limpio["turno"] = turno.lower()
        if turno not in ("Matutino", "Vespertino"):
            errores["turno"] = "Turno: elige Matutino o Vespertino."

        if self.PIDE_MATERIA:
            materia = v.espacios(datos.get("materia")).upper()
            limpio["materia"] = materia
            if materia and not RE_CLAVE_MATERIA.match(materia):
                errores["materia"] = "Materia: usa la clave completa (ej. ACF-0901) o déjala vacía."

        if not errores and self.PIDE_GRUPO:
            grupos = lh.grupos_disponibles(periodo, semestre)
            self._grupos_reporte = [
                grupo for grupo in grupos
                if not grupo["turno"] or grupo["turno"].lower() == turno.lower()
            ]
            self._combo_grupo.blockSignals(True)
            self._combo_grupo.clear()
            self._combo_grupo.addItem("Selecciona el grupo", None)
            for grupo in self._grupos_reporte:
                self._combo_grupo.addItem(
                    f"Grupo {grupo['clave']} · {grupo['materias']} materias",
                    grupo["clave"],
                )
            self._combo_grupo.blockSignals(False)
            if not self._grupos_reporte:
                errores["turno"] = (
                    f"No hay grupos registrados para el semestre {semestre}, "
                    f"turno {turno} y periodo {periodo}."
                )

        return errores, limpio

    def _validar_grupo(self, datos):
        clave = datos.get("clave_grupo")
        if not clave:
            return {"clave_grupo": "Selecciona un grupo para el reporte."}, {}
        if not any(grupo["clave"] == clave for grupo in self._grupos_reporte):
            return {"clave_grupo": "El grupo seleccionado ya no está disponible."}, {}
        return {}, {"clave_grupo": clave}

    # el reporte se puede generar varias veces sin volver a capturar
    def confirmar_registro(self, datos):
        return True

    def limpiar(self):
        pass

    def _abrir(self, prefijo, datos):
        CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        periodo = datos["periodo"].replace(" ", "_")
        return CARPETA_SALIDA / f"{prefijo}_{periodo}_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    def _finalizar_pdf(self, ruta):
        ruta = Path(ruta)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))
        return True, f"PDF generado:\n{ruta.name}\n\nCarpeta: {CARPETA_SALIDA}"


class VentanaReporteHorarios(_VentanaReporte):
    def __init__(self, menu=None):
        super().__init__("SIGEA - Reporte de horarios", "REPORTE DE HORARIOS", menu)

    def guardar(self, datos):
        horario = lh.obtener_horario(
            datos["periodo"], datos["semestre"], datos["turno"],
            datos["clave_grupo"],
        )
        if horario is None:
            return False, (
                f"No hay un horario registrado para el grupo "
                f"{datos['clave_grupo']} en {datos['periodo']}."
            )
        ruta = self._abrir(f"horario_{horario['clave']}", datos)
        try:
            generar_pdf_horario(horario, str(ruta))
        except Exception as error:
            print(f"Error al generar el PDF del horario: {error}")
            return False, "No fue posible generar el PDF."
        return self._finalizar_pdf(ruta)


class VentanaReporteListaGrupo(_VentanaReporte):
    PIDE_MATERIA = True

    def __init__(self, menu=None):
        super().__init__("SIGEA - Lista de grupo", "LISTA DE GRUPO", menu)

    def guardar(self, datos):
        lista, problema = lh.lista_grupo(
            datos["periodo"], datos["semestre"], datos["turno"],
            datos.get("materia") or None,
            clave_grupo_seleccionada=datos["clave_grupo"],
        )
        if problema:
            return False, problema
        if not lista["alumnos"]:
            return False, (
                f"No hay alumnos inscritos en el grupo {lista['clave']} "
                f"del periodo {datos['periodo']}."
            )
        ruta = self._abrir(f"lista_{lista['clave']}", datos)
        try:
            generar_pdf_lista_grupo(lista, str(ruta))
        except Exception as error:
            print(f"Error al generar la lista del grupo: {error}")
            return False, "No fue posible generar el PDF."
        return self._finalizar_pdf(ruta)
