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


    def closeEvent(self, evento):
        if self.menu is not None:
            self.menu.show()
        super().closeEvent(evento)