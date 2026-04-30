"""
Widget de mapa interactivo con Leaflet y QWebChannel
"""
import json
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject, QUrl

from config.settings import CENTRALES_JSON


class MapBridge(QObject):
    """Puente entre Python y JavaScript"""

    # Señales (Python -> JS)
    add_marker = pyqtSignal(str, float, float, str, str, str)  # id, lat, lon, name, type, color

    # Señales eventos (JS -> Python)
    marker_clicked_event = pyqtSignal(str, float, float)
    map_ready_event = pyqtSignal()

    @pyqtSlot(str, float, float)
    def marker_clicked(self, id: str, lat: float, lon: float):
        self.marker_clicked_event.emit(id, lat, lon)

    @pyqtSlot()
    def map_ready(self):
        self.map_ready_event.emit()


class MapWidget(QWebEngineView):
    """Widget que embebe un mapa OpenStreetMap interactivo"""

    def __init__(self):
        super().__init__()
        self.centrales: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz"""
        # Cargar HTML del mapa
        map_html = self._load_map_html()
        self.setHtml(map_html)

        # Configurar QWebChannel
        self._setup_bridge()

    def _setup_bridge(self):
        """Configura el puente Python-JavaScript"""
        self.channel = QWebChannel()
        self.bridge = MapBridge()

        # Registrar bridge en el canal
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)

    def _load_map_html(self) -> str:
        """Carga plantilla HTML con Leaflet 1.7.1 (versión estable)"""
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <title>Mapa Centrales Energéticas Ecuador</title>

    <!-- Leaflet 1.7.1 (versión más estable) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.js"></script>

    <!-- QWebChannel para comunicación PyQt-JS -->
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html, body {
            width: 100%;
            height: 100%;
        }

        #map {
            width: 100%;
            height: 100%;
            background: #e3e3e3;
        }

        .central-marker {
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            font-weight: bold;
            color: white;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="map"></div>

    <script>
        let map;
        let bridge;
        let markers = {};
        let mapInitialized = false;

        // Inicializar mapa
        function initMap() {
            if (mapInitialized) return;
            mapInitialized = true;

            try {
                map = L.map('map', {
                    center: [-1.8, -78.2],
                    zoom: 7,
                    maxZoom: 19,
                    minZoom: 4
                });

                // Capa base OpenStreetMap
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19,
                    crossOrigin: true
                }).addTo(map);

                // Forzar redibujado
                map.invalidateSize();

                // Control de escala
                L.control.scale({imperial: false}).addTo(map);

                console.log('[OK] Mapa inicializado correctamente');
            } catch(e) {
                console.log('[ERROR] ' + e.message);
            }
        }

        // Agregar marcador de central
        function addMarker(id, lat, lon, name, type, color) {
            try {
                const colorMap = {
                    'HYDRO': '#0066cc',
                    'THERMAL': '#ff6600',
                    'WIND': '#99cc00',
                    'SOLAR': '#ffcc00'
                };

                const markerColor = colorMap[type] || color;

                // Crear icono personalizado
                const icon = L.divIcon({
                    className: 'central-marker',
                    html: '<div style="background-color: ' + markerColor + ';">●</div>',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15],
                    popupAnchor: [0, -15]
                });

                // Crear marcador
                const marker = L.marker([lat, lon], {
                    icon: icon,
                    title: name
                });

                // Popup con información
                const popupContent = '<div style="font-size: 12px; width: 200px;"><h4 style="margin: 0 0 8px 0;">' + name + '</h4><div><strong>Tipo:</strong> ' + type + '</div><div><strong>Latitud:</strong> ' + lat.toFixed(6) + '</div><div><strong>Longitud:</strong> ' + lon.toFixed(6) + '</div></div>';

                marker.bindPopup(popupContent);
                marker.on('click', function() {
                    if (bridge) {
                        bridge.marker_clicked(id, lat, lon);
                    }
                });

                marker.addTo(map);
                markers[id] = marker;

                console.log('[OK] Marcador agregado: ' + name);
            } catch(e) {
                console.log('[ERROR addMarker] ' + e.message);
            }
        }

        // Inicializar cuando todo esté listo
        window.addEventListener('load', function() {
            setTimeout(function() {
                initMap();

                // Conectar QWebChannel
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    bridge = channel.objects.bridge;
                    console.log('[OK] QWebChannel conectado');

                    // Conectar señal add_marker del bridge
                    bridge.add_marker.connect(function(id, lat, lon, name, type, color) {
                        console.log('[JS] Recibido marcador: ' + name);
                        addMarker(id, lat, lon, name, type, color);
                    });

                    // Notificar a Python que JS ha cargado y el mapa está listo
                    bridge.map_ready();
                });
            }, 500);
        });

        // Retry si load no dispara
        setTimeout(function() {
            if (!mapInitialized) {
                console.log('[RETRY] Ejecutando manualmente...');
                window.dispatchEvent(new Event('load'));
            }
        }, 2000);

    </script>
</body>
</html>
        """

    def add_centrales(self, centrales: List[Dict[str, Any]]) -> None:
        """Agrega múltiples centrales al mapa"""
        self.centrales = centrales
        for central in centrales:
            self._add_central_to_map(central)

    def _add_central_to_map(self, central: Dict[str, Any]) -> None:
        """Agrega una central al mapa"""
        if not self.bridge:
            return

        self.bridge.add_marker.emit(
            central["id"],
            central["latitude"],
            central["longitude"],
            central["name"],
            central["type"],
            central["type"]  # El tipo es el color
        )
