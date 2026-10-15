import sys
 
from PySide6.QtWidgets import QApplication
from ventanas.login import VentanaLogin
 
 
app = QApplication(sys.argv)
 
ventana = VentanaLogin()
ventana.show()

 
sys.exit(app.exec())

