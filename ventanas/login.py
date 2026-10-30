from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer

from Logica.bitacora import registrar_salida
from Logica.login import autenticar
from ventanas.ventana import VentanaBase, Config, ruta_recurso
from ventanas.menu_secretaria import VentanaMenuAdmin

carpeta_recursos = Path(__file__).resolve().parent.parent / "Recursos"
TEXTO_BOTON = "INGRESAR"


class VentanaLogin(VentanaBase):

    def __init__(self):
        super().__init__("SIGEA - Portal de Gestión Académica", 980, 600)
        self._verificando = False
        self._acceso_id = None
        self.crear_interfaz()
        self.centrar_ventana()

    def crear_interfaz(self):
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        panel_izquierdo = QFrame()
        panel_izquierdo.setFixedWidth(460)
        panel_izquierdo.setStyleSheet(f"QFrame {{ background-color: {Config.AZUL_OSCURO}; }}")

        panel_derecho = QFrame()
        panel_derecho.setStyleSheet(f"QFrame {{ background-color: {Config.AZUL_OSCURO}; }}")

        layout_principal.addWidget(panel_izquierdo)
        layout_principal.addWidget(panel_derecho)

        self.crear_panel_institucional(
            panel_izquierdo,
            rutas_logos=[ruta_recurso("sigeacircular.png")],
        )
        self.crear_formulario_login(panel_derecho)

    def crear_formulario_login(self, parent):
        layout_exterior = QVBoxLayout(parent)
        layout_exterior.setContentsMargins(40, 40, 40, 40)
        layout_exterior.setAlignment(Qt.AlignCenter)

        formulario = self.crear_formulario(
            "INICIAR SESIÓN",
            "Bienvenido(a) al sistema SIGEA.\n"
            "\nIngresa tu clave personal y contraseña para continuar",
            texto_boton=None,
            ancho=410,
            icono=ruta_recurso("iconosesion.png"),
        )
        formulario.agregar_logo(ruta_recurso("logo-ita300.png"), ancho=120, alto=80)
        formulario.agregar_logo(ruta_recurso("Logotecnm300.png"), ancho=120, alto=80)
        formulario.agregar_widget(
            self.crear_label_campo("TIPO DE USUARIO", color="rgba(128, 128, 128, 178)")
        )
        self.selector_tipo = self.crear_glass_radio_group(["Secretaría", "Docente"])
        formulario.agregar_widget(self.selector_tipo)

        self.campo_usuario = formulario.agregar_campo("Clave personal / Usuario")
        self.campo_password = formulario.agregar_campo("Contraseña", password=True)
        self.boton_login = self.crear_boton_entrar(
            TEXTO_BOTON, self.verificar_credenciales, ancho=170, alto=54
        )
        formulario.agregar_widget(self.boton_login, Qt.AlignHCenter)

        # indicador de carga
        self.spinner = self.crear_spinner(22, Config.TEXTO_CLARO)
        self.spinner.setParent(self.boton_login)
        self.spinner.setGeometry(
            self.boton_login.width() - 35,
            (self.boton_login.height() - 22) // 2,
            22, 22,
        )
        self.spinner.hide()

        layout_exterior.addWidget(formulario, alignment=Qt.AlignCenter)

        self.campo_usuario.entrada.returnPressed.connect(self.verificar_credenciales)
        self.campo_password.entrada.returnPressed.connect(self.verificar_credenciales)

    def verificar_credenciales(self):
        if self._verificando:
            return

        if self._acceso_id is not None:
            cerrado, problema = registrar_salida(self._acceso_id)
            if not cerrado:
                self.mostrar_advertencia("Bitácora de accesos", problema)
                return
            self._acceso_id = None

        usuario = self.campo_usuario.valor().strip()
        contrasena = self.campo_password.valor()
        tipo_usuario = self.selector_tipo.obtener_seleccion()

        correcto, mensaje, acceso_id = autenticar(
            usuario, contrasena, tipo_usuario
        )

        if not correcto:
            self.mostrar_advertencia("No se pudo iniciar sesión", mensaje)
            return

        self._verificando = True
        self.boton_login.setEnabled(False)
        self.boton_login.setText("")
        self.spinner.show()
        self.spinner.iniciar()

        self._acceso_id = acceso_id
        QTimer.singleShot(
            1200,
            lambda: self._finalizar_verificacion(
                usuario, tipo_usuario, acceso_id
            ),
        )

    def _finalizar_verificacion(self, usuario, tipo_usuario, acceso_id):
        self.spinner.detener()
        self._verificando = False
        self.boton_login.setEnabled(True)
        self.boton_login.setText(TEXTO_BOTON)

        if tipo_usuario in ("Secretaría", "Administrativo"):
            self.ventana_menu = VentanaMenuAdmin(usuario, acceso_id)
            self._acceso_id = None
            self.ventana_menu.show()
            self.close()
        else:
            self.mostrar_mensaje("SIGEA", f"Bienvenido(a), {usuario}. Acceso como docente.")

    def closeEvent(self, evento):
        if self._acceso_id is not None:
            registrar_salida(self._acceso_id)
            self._acceso_id = None
        super().closeEvent(evento)