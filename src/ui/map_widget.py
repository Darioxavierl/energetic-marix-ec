"""
Widget de mapa interactivo con Leaflet.js y QWebEngineView
"""
import json
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

from config.settings import WEB_DIR, CENTRALES_JSON


class MapWidget(QWebEngineView):
    """
    Widget que embebe un mapa OpenStreetMap interactivo usando Leaflet.js
    dentro de una ventana PyQt6
    """

    def __init__(self):
        super().__init__()
        self.centrales: List[Dict[str, Any]] = []
        self._setup_map()

    def _setup_map(self) -> None:
        """Configura y carga el mapa HTML con Leaflet"""
        html_path = WEB_DIR / "html" / "map_container.html"

        if not html_path.exists():
            raise FileNotFoundError(f"Archivo HTML no encontrado: {html_path}")

        # Cargar HTML en el motor web
        self.load(QUrl.fromLocalFile(str(html_path)))

        # Conectar señal de carga completada
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self) -> None:
        """Se ejecuta cuando el mapa ha cargado completamente"""
        try:
            # Cargar centrales desde JSON
            self.centrales = self._load_centrales_from_json()

            # Agregar cada central al mapa
            for central in self.centrales:
                self._add_central_to_map(central)

            print(f"✓ {len(self.centrales)} centrales cargadas en el mapa")

        except Exception as e:
            print(f"❌ Error al cargar centrales: {e}")

    def _load_centrales_from_json(self) -> List[Dict[str, Any]]:
        """
        Carga centrales desde archivo JSON

        Returns:
            Lista de diccionarios con datos de centrales
        """
        if not CENTRALES_JSON.exists():
            raise FileNotFoundError(f"Archivo JSON no encontrado: {CENTRALES_JSON}")

        try:
            with open(CENTRALES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data["data"]["centrales"]

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido en {CENTRALES_JSON}: {e}")

    def _add_central_to_map(self, central: Dict[str, Any]) -> None:
        """
        Agrega un marcador de central al mapa mediante JavaScript

        Args:
            central: Diccionario con datos de la central
        """
        # Serializar central a JSON seguro
        central_json = json.dumps(central, ensure_ascii=False)

        # Ejecutar función JavaScript para agregar marcador
        js_code = f"addMarker({central_json});"

        self.page().runJavaScript(js_code)

    def add_centrales(self, centrales: List[Dict[str, Any]]) -> None:
        """
        Agrega múltiples centrales al mapa

        Args:
            centrales: Lista de diccionarios con datos de centrales
        """
        for central in centrales:
            self._add_central_to_map(central)

    def clear_markers(self) -> None:
        """Elimina todos los marcadores del mapa"""
        self.page().runJavaScript("clearMarkers();")

    def set_map_center(self, latitude: float, longitude: float, zoom: int = 7) -> None:
        """
        Centra el mapa en coordenadas específicas

        Args:
            latitude: Latitud en grados
            longitude: Longitud en grados
            zoom: Nivel de zoom (0-19)
        """
        js_code = f"setMapCenter({latitude}, {longitude}, {zoom});"
        self.page().runJavaScript(js_code)
