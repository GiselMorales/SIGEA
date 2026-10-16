from PySide6.QtWidgets import QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ventanas.ventana import VentanaBase
from conexiondb.db import obtener_conexion

# vista -> consulta, parámetros y textos de la gráfica
VISTAS = {
    "total": {
        "titulo": "Total de alumnos por sexo",
        "xlabel": "Sexo",
        "sql": """
            SELECT sexo, COUNT(*) FROM public.alumnos
            GROUP BY sexo ORDER BY sexo
        """,
        "params": (),
    },
    "hombres": {
        "titulo": "Alumnos hombres por semestre",
        "xlabel": "Semestre",
        "sql": """
            SELECT semestre_actual, COUNT(*) FROM public.alumnos
            WHERE sexo = %s GROUP BY semestre_actual ORDER BY semestre_actual
        """,
        "params": ("Hombre",),
    },
    "mujeres": {
        "titulo": "Alumnas mujeres por semestre",
        "xlabel": "Semestre",
        "sql": """
            SELECT semestre_actual, COUNT(*) FROM public.alumnos
            WHERE sexo = %s GROUP BY semestre_actual ORDER BY semestre_actual
        """,
        "params": ("Mujer",),
    },
}


class VentanaGrafica(VentanaBase):
    def __init__(self, menu=None, vista="total"):
        super().__init__("SIGEA - Estadísticas de alumnos", 900, 650)
        self.menu = menu
        self.vista = vista if vista in VISTAS else "total"

        layout = QVBoxLayout(self)
        self.figura = Figure(figsize=(8, 5))
        self.canvas = FigureCanvasQTAgg(self.figura)
        layout.addWidget(self.canvas)

        self.mostrar_grafica()
        self.centrar_ventana()

    def mostrar_grafica(self):
        conf = VISTAS[self.vista]
        conexion = obtener_conexion()

        if conexion is None:
            QMessageBox.warning(
                self, "Error de conexión",
                "No fue posible conectar con la base de datos.",
            )
            return

        try:
            with conexion.cursor() as cursor:
                cursor.execute(conf["sql"], conf["params"])
                filas = cursor.fetchall()

            if not filas:
                QMessageBox.information(
                    self, "Sin registros",
                    "No hay alumnos registrados para generar la gráfica.",
                )
                return

            etiquetas = [str(fila[0]) for fila in filas]
            cantidades = [int(fila[1]) for fila in filas]

            self.figura.clear()
            ax = self.figura.add_subplot(111)
            barras = ax.bar(etiquetas, cantidades, color="#006BB3")
            ax.bar_label(barras)
            ax.set_title(conf["titulo"])
            ax.set_xlabel(conf["xlabel"])
            ax.set_ylabel("Cantidad de alumnos")
            ax.grid(axis="y", alpha=0.3)

            self.figura.tight_layout()
            self.canvas.draw()

        except Exception as error:
            print(f"Error al generar gráfica: {error}")
            QMessageBox.warning(self, "Error", "No fue posible generar la gráfica.")
        finally:
            conexion.close()

    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)