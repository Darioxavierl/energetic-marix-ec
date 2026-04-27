"""
Punto de entrada principal de la aplicación
Simulador de Matriz Energética del Ecuador
"""
import sys
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main():
    """Función principal que inicia la aplicación"""
    app = QApplication(sys.argv)

    # Crear ventana principal
    window = MainWindow()
    window.show()

    # Ejecutar bucle de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
