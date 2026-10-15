from logica.login import autenticar
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout
from ventanas.ventana import VentanaBase, Config, ruta_recurso
from ventanas.menu_secretaria import VentanaMenuAdmin

carpeta_recursos = Path(__file__).resolve().parent.parent / "Recursos"

class VentanaLogin(VentanaBase):

    def __init__(self):
        super().__init__("SIGEA - Portal de Gestión Académica", 980, 600)

        self.tipo_usuario = "Administrativo"
        self._verificando = False

        self.crear_interfaz()
        self.centrar_ventana()

    def crear_interfaz(self):
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        panel_izquierdo = QFrame()
        panel_izquierdo.setFixedWidth(460)
        panel_izquierdo.setStyleSheet(f"""
            QFrame {{
                background-color: {Config.AZUL_OSCURO};
            }}
        """)

        panel_derecho = QFrame()
        panel_derecho.setStyleSheet(f"""
            QFrame {{
                background-color: {Config.AZUL_OSCURO};
            }}
        """)

        layout_principal.addWidget(panel_izquierdo)
        layout_principal.addWidget(panel_derecho)

        self.crear_panel_institucional(
            panel_izquierdo,
            rutas_logos=[
                carpeta_recursos / "sigeacircular.png",
            ],
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
            icono=ruta_recurso("iconosesion.png")
        )
        formulario.agregar_logo(
            carpeta_recursos / "logo-ita300.png",
            ancho=120,
            alto=80,
        )

        formulario.agregar_logo(
            carpeta_recursos / "Logotecnm300.png",
        ancho=120,
        alto=80,
        )
        formulario.agregar_widget(
            self.crear_label_campo("TIPO DE USUARIO", color="rgba(128, 128, 128, 178)")
        )
        self.selector_tipo = self.crear_glass_radio_group(["Secretaría", "Docente"])
        self.selector_tipo.seleccion_cambiada.connect(self._cambiar_tipo_usuario)
        formulario.agregar_widget(self.selector_tipo)

        self.campo_usuario = formulario.agregar_campo("Clave personal / Usuario")
        self.campo_password = formulario.agregar_campo("Contraseña", password=True)
        self.boton_login = self.crear_boton_entrar(
            "INGRESAR",
            self.verificar_credenciales,
            ancho=170,
            alto=54,
        )
        formulario.agregar_widget(self.boton_login, Qt.AlignHCenter)

        #  cargando
        self.spinner = self.crear_spinner(22, Config.TEXTO_CLARO)
        self.spinner.setParent(self.boton_login)
        self.spinner.setGeometry(
            (self.boton_login.width() - 35),
            (self.boton_login.height() - 22) // 2,
            22,
            22,
        )
        self.spinner.hide()

        layout_exterior.addWidget(formulario, alignment=Qt.AlignCenter)

        self.campo_usuario.entrada.returnPressed.connect(self.verificar_credenciales)
        self.campo_password.entrada.returnPressed.connect(self.verificar_credenciales)

    def _cambiar_tipo_usuario(self, indice, texto):
        self.tipo_usuario = texto

    def verificar_credenciales(self):
        if self._verificando:
            return

        usuario = self.campo_usuario.valor().strip()
        contrasena = self.campo_password.valor()

        correcto, mensaje = autenticar(
            usuario,
            contrasena,
            self.selector_tipo.obtener_seleccion(),
        )

        if not correcto:
            self.mostrar_advertencia(
                "No se pudo iniciar sesión",
                mensaje,
            )
            return

        self._verificando = True
        self.boton_login.setEnabled(False)
        self.boton_login.setText("")
        self.spinner.show()
        self.spinner.iniciar()

        QTimer.singleShot(
            1200,
            lambda: self._finalizar_verificacion(
            usuario,
            self.selector_tipo.obtener_seleccion(),
        ),
)

    def _finalizar_verificacion(self, usuario, tipo_usuario):
        self.spinner.detener()
        self._verificando = False
        self.boton_login.setEnabled(True)

        if tipo_usuario in ("Secretaría", "Administrativo"):
            self.ventana_menu = VentanaMenuAdmin()
            self.ventana_menu.show()
            self.close()
        else:
            self.mostrar_mensaje(
                "SIGEA",
                f"Bienvenido(a), {usuario}. Acceso como docente."
            )
