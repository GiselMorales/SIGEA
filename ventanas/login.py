from logica.login import autenticar
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer

from ventanas.ventana import VentanaBase, Config

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

        self.crear_panel_institucional(panel_izquierdo)
        self.crear_formulario_login(panel_derecho)

    # ------------------------------------------------------------------
    def crear_formulario_login(self, parent):
        layout_exterior = QVBoxLayout(parent)
        layout_exterior.setContentsMargins(40, 40, 40, 40)
        layout_exterior.setAlignment(Qt.AlignCenter)

        formulario = self.crear_formulario(
            "INICIAR SESIÓN",
            "Bienvenido"
            "Ingresa tu clave personal y contraseña para continuar",
            texto_boton=None,
            ancho=410,
        )

        formulario.agregar_widget(
            self.crear_label_campo("TIPO DE USUARIO", color="rgba(128, 128, 128, 178)")
        )
        self.selector_tipo = self.crear_glass_radio_group(["Secretaría", "Docente"])
        self.selector_tipo.seleccion_cambiada.connect(self._cambiar_tipo_usuario)
        formulario.agregar_widget(self.selector_tipo)

        self.campo_usuario = formulario.agregar_campo("Usuario / Matrícula")
        self.campo_password = formulario.agregar_campo("Contraseña", password=True)

        self.etiqueta_error = self.crear_label_error()
        formulario.agregar_widget(self.etiqueta_error)

        self.boton_login = self.crear_boton_entrar(
            "INGRESAR AL SISTEMA",
            self.verificar_credenciales,
            ancho=170,
            alto=54,
        )
        formulario.agregar_widget(self.boton_login, Qt.AlignHCenter)

        #  cargando
        self.spinner = self.crear_spinner(28, Config.GRIS_CAMPO)
        politica = self.spinner.sizePolicy()
        politica.setRetainSizeWhenHidden(True)
        self.spinner.setSizePolicy(politica)
        self.spinner.detener()
        formulario.agregar_widget(self.spinner, Qt.AlignHCenter)

        layout_exterior.addWidget(formulario, alignment=Qt.AlignCenter)

        self.campo_usuario.entrada.returnPressed.connect(self.verificar_credenciales)
        self.campo_password.entrada.returnPressed.connect(self.verificar_credenciales)

    def _cambiar_tipo_usuario(self, indice, texto):
        self.tipo_usuario = texto

    def verificar_credenciales(self):
        correcto, mensaje = autenticar(
            self.campo_usuario.valor().strip(),
            self.campo_password.valor(),
            self.selector_tipo.obtener_seleccion(),
        )

        if correcto:
            self.mostrar_mensaje("SIGEA", mensaje)
        else:
            self.mostrar_advertencia("No se pudo iniciar sesión", mensaje)

     
            self._verificando = True
            self.spinner.iniciar()
            QTimer.singleShot(1200, lambda: self._finalizar_verificacion(usuario))

        def _finalizar_verificacion(self, usuario):
            self.spinner.detener()
            self._verificando = False
            self.mostrar_mensaje(
                "SIGEA",
                f"Bienvenido(a), {usuario}. Acceso como {self.tipo_usuario}."
            )