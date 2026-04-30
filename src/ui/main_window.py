"""
Ventana principal de la aplicación PyQt6
"""
import json
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.ui.map_widget import MapWidget
from config.settings import APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, CENTRALES_JSON


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario"""
        # Propiedades de la ventana
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        # Widget central con layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Crear y agregar widget del mapa
        self.map_widget = MapWidget()
        layout.addWidget(self.map_widget)

        # Cargar datos al estar listo el mapa
        self.map_widget.bridge.map_ready_event.connect(self._on_map_ready)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Mostrar mensaje de inicio
        print(f"✓ {APP_TITLE} iniciada")

    def _on_map_ready(self):
        """Manejador para cuando el mapa está listo para recibir instrucciones de PyQt"""
        print("✓ Mapa listo, cargando centrales...")
        try:
            with open(CENTRALES_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                centrales = data.get("data", {}).get("centrales", [])
                self.map_widget.add_centrales(centrales)
                print(f"✓ {len(centrales)} centrales cargadas")
        except Exception as e:
            print(f"Error cargando centrales: {e}")

