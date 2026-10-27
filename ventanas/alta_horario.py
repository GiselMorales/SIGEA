import re
from datetime import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QSpinBox,
    QTimeEdit, QPushButton, QCheckBox,
)
from PySide6.QtCore import Qt, QTime

from Logica import validaciones as v
from Logica import horarios as lh
from ventanas.base_alta import VentanaAlta
from ventanas.ventana import Config
from ventanas.componentes import (
    ESTILO_BOTON_SUBIR, ESTILO_BOTON_QUITAR, ESTILO_COMBO_TIPO,
)

ESTILO_ENTRADA = """
QLineEdit, QSpinBox, QTimeEdit {
    background-color: #FFFFFF; color: #1B2A3A;
    border: 1px solid #B8C4D2; border-radius: 8px;
    padding: 4px 8px; min-height: 28px;
}
"""
RE_AULA = re.compile(r"^[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ ]{1,30}$")
ABREVIATURA = {
    "lunes": "Lun", "martes": "Mar", "miércoles": "Mié",
    "jueves": "Jue", "viernes": "Vie",
}


def texto_bloques(bloques):
    return ", ".join(
        f"{ABREVIATURA[d]} {lh.formato_hora(i)}-{lh.formato_hora(f)}" for d, i, f in bloques
    )


class VentanaAltaHorario(VentanaAlta):

    al_cerrar = None                 # función que se llama al cerrar la ventana

    def __init__(self, menu=None):
        super().__init__(
            "SIGEA - Alta de horario", "ALTA DE HORARIO", "REGISTRAR HORARIO", menu
        )

    def construir_secciones(self):
        self._materias_semestre = []
        self._docentes = []
        self._agregadas = []          # materias ya armadas para este horario
        self._ya_en_bd = set()        # materias que el grupo ya tiene guardadas
        self._bloques = []            # días y horas de la materia que se está armando
        self._contexto = None         # (periodo, semestre, turno, clave) cargado en el panel
        self._grupos_existentes = []
        self._clave_nueva = None

        self.agregar_seccion(
            "DATOS DEL HORARIO",
            [
                self.fila(
                    self.campo(
                        "periodo", "Periodo (ej. AGO-DIC 2026)",
                        lh.listar_periodos() or v.periodos_disponibles(),
                    ),
                    self.campo("semestre", "Semestre", v.SEMESTRES),
                    self.selector("turno", "Turno", ["Matutino", "Vespertino"]),
                    pesos=(3, 1, 3),
                ),
            ],
            self._validar_datos,
        )
        self.agregar_seccion(
            "GRUPO",
            [self._selector_grupo()],
            self._validar_grupo,
        )
        self.agregar_seccion(
            "MATERIAS DEL GRUPO",
            [self._panel_materias()],
            self._validar_materias,
        )

    # ------------------------------------------------------------------
    #  Sección 1: periodo, semestre y turno
    # ------------------------------------------------------------------
    def _validar_datos(self, datos):
        errores, limpio = {}, {}

        periodo = re.sub(r"\s*-\s*", "-", v.espacios(datos.get("periodo")).upper())
        limpio["periodo"] = periodo
        periodos = lh.listar_periodos()
        if not periodo:
            errores["periodo"] = "Periodo: es obligatorio."
        elif periodo not in periodos:
            errores["periodo"] = (
                "Periodo: no está dado de alta en periodos_escolares "
                "(ejecuta sql/horarios_grupos.sql o agrégalo)."
            )

        msg, semestre = v._validar_semestre(datos.get("semestre"))
        limpio["semestre"] = semestre
        if msg:
            errores["semestre"] = msg

        turno = v.espacios(datos.get("turno"))
        if turno not in ("Matutino", "Vespertino"):
            errores["turno"] = "Turno: elige Matutino o Vespertino."
        limpio["turno"] = turno.lower()

        if errores:
            return errores, limpio

        self._grupos_existentes = lh.listar_grupos_horario(periodo, semestre, turno)
        claves_existentes = lh.listar_claves_grupo(periodo, semestre, turno)
        self._clave_nueva = lh.siguiente_clave_grupo(
            semestre, turno, claves_existentes
        )
        self._combo_grupo.blockSignals(True)
        self._combo_grupo.clear()
        self._combo_grupo.addItem("Selecciona un grupo", None)
        for grupo in self._grupos_existentes:
            self._combo_grupo.addItem(
                f"Completar {grupo['clave']} · {grupo['materias']} materias",
                grupo["clave"],
            )
        etiqueta_nuevo = (
            f"Crear grupo nuevo ({self._clave_nueva})"
            if self._grupos_existentes else f"Crear grupo ({self._clave_nueva})"
        )
        self._combo_grupo.addItem(etiqueta_nuevo, "__nuevo__")
        self._combo_grupo.blockSignals(False)
        return {}, limpio

    # ------------------------------------------------------------------
    #  Sección 2: seleccionar un grupo existente o crear uno nuevo
    # ------------------------------------------------------------------
    def _selector_grupo(self):
        self._combo_grupo = QComboBox()
        self._combo_grupo.setFixedHeight(38)
        self._combo_grupo.setCursor(Qt.PointingHandCursor)
        self._combo_grupo.setStyleSheet(ESTILO_COMBO_TIPO)
        self._combo_grupo.addItem("Valida primero periodo, semestre y turno", None)
        self._combo_grupo.currentIndexChanged.connect(
            lambda _i: self._cambio("grupo_seleccion")
        )
        self._registrar_lector(
            "grupo_seleccion", self._combo_grupo.currentData, self._combo_grupo
        )
        caja = self._contenedor("selectorGrupoHorario")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.crear_label_campo(
            "GRUPO EXISTENTE O NUEVO", color="rgba(128, 128, 128, 178)"
        ))
        lay.addWidget(self._combo_grupo)
        return caja

    def _validar_grupo(self, datos):
        seleccion = datos.get("grupo_seleccion")
        if not seleccion:
            return {"grupo_seleccion": "Selecciona un grupo existente o crea uno nuevo."}, {}

        crear_nuevo = seleccion == "__nuevo__"
        if crear_nuevo:
            clave = self._clave_nueva
        elif any(g["clave"] == seleccion for g in self._grupos_existentes):
            clave = seleccion
        else:
            return {"grupo_seleccion": "El grupo seleccionado ya no está disponible."}, {}

        datos_base = self._secciones[0].datos
        periodo = datos_base["periodo"]
        semestre = datos_base["semestre"]
        turno = datos_base["turno"]
        materias = lh.listar_materias(semestre)
        if not materias:
            return {"grupo_seleccion": f"No hay materias registradas para el semestre {semestre}."}, {}
        docentes = lh.listar_docentes()
        if not docentes:
            return {"grupo_seleccion": "No hay docentes activos. Registra al menos uno en DOCENTE."}, {}

        self._cargar_panel(
            materias, docentes, lh.materias_en_grupo(periodo, clave),
            (periodo, int(semestre), turno, clave),
        )
        return {}, {"clave_grupo": clave, "crear_grupo_nuevo": crear_nuevo}

    # ------------------------------------------------------------------
    #  Sección 3: panel para armar las materias
    # ------------------------------------------------------------------
    def _con_etiqueta(self, texto, widget):
        caja = self._contenedor("campoPanel")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.crear_label_campo(texto, color="rgba(128, 128, 128, 178)"))
        lay.addWidget(widget)
        return caja

    def _panel_materias(self):
        self._combo_materia = QComboBox()
        self._combo_docente = QComboBox()
        for combo in (self._combo_materia, self._combo_docente):
            combo.setFixedHeight(38)
            combo.setCursor(Qt.PointingHandCursor)
            combo.setStyleSheet(ESTILO_COMBO_TIPO)

        self._aula = QLineEdit()
        self._aula.setPlaceholderText("Ej. 701")
        self._aula.setMaxLength(30)
        self._cupo = QSpinBox()
        self._cupo.setRange(1, 60)
        self._cupo.setValue(30)

        self._checks_dias = {}
        caja_dias = QWidget()
        fila_dias = QHBoxLayout(caja_dias)
        fila_dias.setContentsMargins(0, 0, 0, 0)
        fila_dias.setSpacing(10)
        for dia in lh.DIAS:
            check = QCheckBox(dia.capitalize())
            self._checks_dias[dia] = check
            fila_dias.addWidget(check)
        seleccionar_todos = QPushButton("Lun-Vie")
        seleccionar_todos.setFixedSize(78, 32)
        seleccionar_todos.setCursor(Qt.PointingHandCursor)
        seleccionar_todos.setToolTip("Seleccionar todos los días hábiles")
        seleccionar_todos.setStyleSheet(ESTILO_BOTON_SUBIR)
        seleccionar_todos.clicked.connect(
            lambda _checked=False: [
                check.setChecked(True) for check in self._checks_dias.values()
            ]
        )
        fila_dias.addWidget(seleccionar_todos)
        fila_dias.addStretch(1)
        self._hora_ini = QTimeEdit(QTime(7, 0))
        self._hora_fin = QTimeEdit(QTime(8, 0))
        self._hora_ini.setTimeRange(QTime(7, 0), QTime(19, 59))
        self._hora_fin.setTimeRange(QTime(7, 0), QTime(20, 0))
        for edit in (self._hora_ini, self._hora_fin):
            edit.setDisplayFormat("HH:mm")

        boton_bloque = QPushButton("+ Añadir bloque")
        boton_bloque.setFixedSize(140, 38)
        boton_bloque.setCursor(Qt.PointingHandCursor)
        boton_bloque.setStyleSheet(ESTILO_BOTON_SUBIR)
        boton_bloque.clicked.connect(self._añadir_bloque)

        boton_quitar_bloque = QPushButton("Quitar último")
        boton_quitar_bloque.setFixedSize(120, 38)
        boton_quitar_bloque.setCursor(Qt.PointingHandCursor)
        boton_quitar_bloque.setStyleSheet(ESTILO_BOTON_QUITAR)
        boton_quitar_bloque.clicked.connect(self._quitar_ultimo_bloque)

        self._lbl_bloques = self.crear_label_subtitulo("", 10, Config.TEXTO_OSCURO)
        self._lbl_bloques.setWordWrap(True)

        boton_materia = QPushButton("Agregar materia al horario")
        boton_materia.setFixedSize(240, 42)
        boton_materia.setCursor(Qt.PointingHandCursor)
        boton_materia.setStyleSheet(ESTILO_BOTON_SUBIR)
        boton_materia.clicked.connect(self._agregar_materia)

        self._lbl_aviso = self.crear_label_error(9)
        self._lbl_aviso.setWordWrap(True)
        self._lbl_aviso.setAlignment(Qt.AlignLeft)
        self._lbl_aviso.hide()

        self._lbl_faltan = self.crear_label_subtitulo("", 10, Config.TEXTO_OSCURO)
        self._lbl_faltan.setWordWrap(True)

        self._lay_agregadas = QVBoxLayout()
        self._lay_agregadas.setSpacing(6)

        caja = self._contenedor("panelMaterias")
        caja.setStyleSheet(ESTILO_ENTRADA + "#panelMaterias { background: transparent; }")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        fila1 = QHBoxLayout()
        fila1.setSpacing(12)
        fila1.addWidget(self._con_etiqueta("MATERIA", self._combo_materia), 3)
        fila1.addWidget(self._con_etiqueta("DOCENTE", self._combo_docente), 3)
        lay.addLayout(fila1)

        fila2 = QHBoxLayout()
        fila2.setSpacing(12)
        fila2.addWidget(self._con_etiqueta("AULA", self._aula), 3)
        fila2.addWidget(self._con_etiqueta("CUPO", self._cupo), 1)
        fila2.addStretch(2)
        lay.addLayout(fila2)

        fila3 = QHBoxLayout()
        fila3.setSpacing(12)
        lay.addWidget(self._con_etiqueta(
            "DÍAS DE CLASE (marca uno o varios)", caja_dias
        ))

        fila3.addWidget(self._con_etiqueta("INICIO (07:00–19:59)", self._hora_ini), 1)
        fila3.addWidget(self._con_etiqueta("FIN (hasta 20:00)", self._hora_fin), 1)
        fila3.addWidget(boton_bloque, 0, Qt.AlignBottom)
        fila3.addWidget(boton_quitar_bloque, 0, Qt.AlignBottom)
        lay.addLayout(fila3)

        lay.addWidget(self._lbl_bloques)
        lay.addWidget(self._lbl_aviso)
        lay.addWidget(boton_materia, 0, Qt.AlignLeft)
        lay.addWidget(self._lbl_faltan)
        lay.addLayout(self._lay_agregadas)

        self._registrar_lector("materias", lambda: list(self._agregadas), None)
        return caja

    def _cargar_panel(self, materias, docentes, ya_en_bd, contexto):
        self._materias_semestre = materias
        self._docentes = docentes
        self._ya_en_bd = set(ya_en_bd)
        if contexto != self._contexto:                    # otro grupo: se empieza de cero
            self._agregadas.clear()
            self._bloques.clear()
            self._contexto = contexto
        self._combo_docente.clear()
        self._combo_docente.addItem("Selecciona el docente", None)
        for d in docentes:
            self._combo_docente.addItem(d["nombre"], d["rfc"])
        self._redibujar_agregadas()
        self._refrescar_materias()
        self._mostrar_bloques()

    def _refrescar_materias(self):
        usadas = self._ya_en_bd | {m["materia_id"] for m in self._agregadas}
        self._combo_materia.clear()
        self._combo_materia.addItem("Selecciona la materia", None)
        faltan = []
        for m in self._materias_semestre:
            if m["id"] not in usadas:
                self._combo_materia.addItem(f"{m['clave']} · {m['nombre']}", m["id"])
                faltan.append(m["clave"])
        partes = []
        if self._ya_en_bd:
            partes.append(f"Este grupo ya tiene {len(self._ya_en_bd)} materia(s) guardada(s).")
        partes.append(
            "Faltan por agregar: " + ", ".join(faltan) + "."
            if faltan else "Ya están todas las materias del semestre."
        )
        self._lbl_faltan.setText(" ".join(partes))

    # --- bloques (día + hora de inicio + hora de fin) ------------------
    @staticmethod
    def _hora(edit):
        t = edit.time()
        return time(t.hour(), t.minute())

    def _aviso(self, texto=""):
        self._lbl_aviso.setText(texto)
        self._lbl_aviso.setVisible(bool(texto))

    def _mostrar_bloques(self):
        self._lbl_bloques.setText(
            "Días y horas de esta materia: " + texto_bloques(self._bloques)
            if self._bloques else "Aún no agregas días y horas a la materia."
        )

    def _añadir_bloque(self):
        dias = [dia for dia, check in self._checks_dias.items() if check.isChecked()]
        if not dias:
            self._aviso("Marca al menos un día de clase.")
            return
        inicio = self._hora(self._hora_ini)
        fin = self._hora(self._hora_fin)
        nuevos = [(dia, inicio, fin) for dia in dias]
        problema = lh.validar_bloques(self._bloques + nuevos)
        if problema:
            self._aviso(problema)
            return
        self._aviso()
        self._bloques.extend(nuevos)
        self._mostrar_bloques()

    def _quitar_ultimo_bloque(self):
        if self._bloques:
            self._bloques.pop()
        self._aviso()
        self._mostrar_bloques()

    # --- materias agregadas --------------------------------------------
    def _choque_local(self, nueva):
        """Empalmes con las materias que ya se armaron en esta pantalla."""
        for otra in self._agregadas:
            for dia, ini, fin in nueva["bloques"]:
                for dia2, ini2, fin2 in otra["bloques"]:
                    if dia == dia2 and ini < fin2 and fin > ini2:
                        horas = f"{lh.formato_hora(ini)}-{lh.formato_hora(fin)}"
                        if nueva["docente_rfc"] == otra["docente_rfc"]:
                            return (f"El docente ya da {otra['nombre']} el {dia} "
                                    f"en ese horario ({horas}).")
                        return (f"{nueva['nombre']} se empalma con {otra['nombre']} "
                                f"el {dia} ({horas}).")
        return None

    def _agregar_materia(self):
        materia_id = self._combo_materia.currentData()
        if materia_id is None:
            self._aviso("Elige la materia.")
            return
        rfc = self._combo_docente.currentData()
        if not rfc:
            self._aviso("Elige el docente de la materia.")
            return
        problema = lh.validar_bloques(self._bloques)
        if problema:
            self._aviso(problema)
            return
        aula = v.espacios(self._aula.text())
        if aula and not RE_AULA.match(aula):
            self._aviso("Aula: máximo 30 caracteres, solo letras, números y espacios.")
            return

        materia = next(m for m in self._materias_semestre if m["id"] == materia_id)
        nueva = {
            "materia_id": materia_id,
            "clave": materia["clave"],
            "nombre": materia["nombre"],
            "docente_rfc": rfc,
            "docente": self._combo_docente.currentText(),
            "aula": aula,
            "cupo": self._cupo.value(),
            "bloques": list(self._bloques),
        }
        choque = self._choque_local(nueva)
        if choque:
            self._aviso(choque)
            return

        self._aviso()
        self._agregadas.append(nueva)
        self._bloques.clear()
        self._aula.clear()
        self._cupo.setValue(10)
        self._combo_docente.setCurrentIndex(0)
        self._redibujar_agregadas()
        self._refrescar_materias()
        self._mostrar_bloques()
        self._cambio("materias")

    def _quitar_materia(self, materia):
        if materia in self._agregadas:
            self._agregadas.remove(materia)
        self._redibujar_agregadas()
        self._refrescar_materias()
        self._cambio("materias")

    def _redibujar_agregadas(self):
        while self._lay_agregadas.count():
            item = self._lay_agregadas.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for materia in self._agregadas:
            fila = self._contenedor("filaMateria")
            lay = QHBoxLayout(fila)
            lay.setContentsMargins(0, 4, 0, 4)
            lay.setSpacing(10)
            texto = self.crear_label_subtitulo(
                f"{materia['clave']} · {materia['nombre']}  —  {materia['docente']}\n"
                f"Aula: {materia['aula'] or '-'}   Cupo: {materia['cupo']}   "
                f"{texto_bloques(materia['bloques'])}",
                10, Config.TEXTO_OSCURO,
            )
            texto.setWordWrap(True)
            quitar = QPushButton("Quitar")
            quitar.setFixedSize(84, 34)
            quitar.setCursor(Qt.PointingHandCursor)
            quitar.setStyleSheet(ESTILO_BOTON_QUITAR)
            quitar.clicked.connect(lambda _c=False, m=materia: self._quitar_materia(m))
            lay.addWidget(texto, 1)
            lay.addWidget(quitar, 0)
            self._lay_agregadas.addWidget(fila)

    def _validar_materias(self, datos):
        agregadas = datos.get("materias") or []
        if not agregadas:
            return {
                "materias": "Agrega al menos una materia con su docente, días y horas "
                            "(botón «Agregar materia al horario»)."
            }, {}
        return {}, {"materias": agregadas}

    # ------------------------------------------------------------------
    def resumen_confirmacion(self, datos):
        lineas = [
            ("Periodo", datos.get("periodo")),
            ("Grupo", datos.get("clave_grupo")),
            ("Turno", (datos.get("turno") or "").capitalize()),
            ("Semestre", datos.get("semestre")),
            ("Materias que se agregan", str(len(datos.get("materias") or []))),
        ]
        aviso = "\n".join(
            f"• {m['clave']} {m['nombre']} — {m['docente']}" for m in datos.get("materias") or []
        )
        return lineas, aviso

    def guardar(self, datos):
        return lh.crear_horario_grupo({
            "periodo": datos["periodo"],
            "semestre": datos["semestre"],
            "turno": datos["turno"],
            "clave_grupo": datos["clave_grupo"],
            "crear_grupo_nuevo": datos["crear_grupo_nuevo"],
            "materias": datos["materias"],
        })

    def closeEvent(self, evento):
        if self.al_cerrar is not None:
            try:
                self.al_cerrar()
            except RuntimeError:          # la ventana que lo pidió ya se cerró
                pass
        super().closeEvent(evento)

    def limpiar(self):
        super().limpiar()
        self._agregadas.clear()
        self._bloques.clear()
        self._ya_en_bd = set()
        self._materias_semestre = []
        self._docentes = []
        self._grupos_existentes = []
        self._clave_nueva = None
        self._contexto = None
        self._combo_grupo.blockSignals(True)
        self._combo_grupo.clear()
        self._combo_grupo.addItem("Valida primero periodo, semestre y turno", None)
        self._combo_grupo.blockSignals(False)
        for check in self._checks_dias.values():
            check.setChecked(False)
        self._aviso()
        self._redibujar_agregadas()
        self._combo_materia.clear()
        self._combo_materia.addItem("Valida primero periodo, semestre y turno", None)
        self._combo_docente.clear()
        self._combo_docente.addItem("Valida primero periodo, semestre y turno", None)
        self._mostrar_bloques()
        self._lbl_faltan.setText("")
