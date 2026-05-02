"""Widget de mapa interactivo con Leaflet y QWebChannel."""

import json
from typing import Any, Dict, List

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject, QUrl

class MapBridge(QObject):
    """Puente entre Python y JavaScript"""

    # Señales (Python -> JS)
    add_marker = pyqtSignal(str, float, float, str, str, str)  # id, lat, lon, name, type, color
    focus_marker = pyqtSignal(str)

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
        # 1. Configurar un User-Agent propio (Cumple con las políticas de OSM)
        profile = self.page().profile()
        profile.setHttpUserAgent("SimuladorEnergeticoEcuador/0.1.0 (Contacto: darport0212@gmail.com)")
        # Cargar HTML del mapa
        map_html = self._load_map_html()
        self.setHtml(map_html, QUrl("http://simulador-energetico.local/"))

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

        .map-legend {
            position: absolute;
            right: 12px;
            bottom: 12px;
            z-index: 1000;
            width: 250px;
            background: rgba(255,255,255,0.93);
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 10px 12px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.18);
            font-family: "Segoe UI", sans-serif;
            color: #111827;
        }

        .legend-title {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .legend-row {
            display: grid;
            grid-template-columns: 12px 1fr;
            grid-column-gap: 8px;
            margin-bottom: 8px;
            align-items: center;
        }

        .legend-swatch {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.7);
        }

        .legend-top {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            line-height: 1.2;
        }

        .legend-bar {
            margin-top: 3px;
            height: 5px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
        }

        .legend-fill {
            height: 100%;
            width: 0%;
            transition: width .25s ease;
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
    <div id="legend" class="map-legend"></div>

    <script>
        let map;
        let bridge;
        let markers = {};
        let mapInitialized = false;

        function clamp01(value) {
            return Math.max(0, Math.min(1, value));
        }

        function hexToRgb(hex) {
            const normalized = (hex || '#808080').replace('#', '');
            const full = normalized.length === 3
                ? normalized.split('').map(ch => ch + ch).join('')
                : normalized;
            const intVal = parseInt(full, 16);
            return {
                r: (intVal >> 16) & 255,
                g: (intVal >> 8) & 255,
                b: intVal & 255
            };
        }

        function styleFromIntensity(baseHex, intensity) {
            const c = hexToRgb(baseHex);
            const t = clamp01(intensity);
            const alpha = 0.45 + (0.55 * t);
            const size = 16 + Math.round(18 * t);
            return {
                background: 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + alpha.toFixed(2) + ')',
                border: 'rgba(255,255,255,' + (0.65 + 0.35 * t).toFixed(2) + ')',
                glow: '0 0 ' + (6 + Math.round(10 * t)) + 'px rgba(' + c.r + ',' + c.g + ',' + c.b + ',0.55)',
                size: size
            };
        }

        function buildIcon(baseColor, type, utilizationByType) {
            const intensity = clamp01((utilizationByType || {})[type] || 0);
            const styled = styleFromIntensity(baseColor, intensity);
            const html =
                '<div style="' +
                    'width:' + styled.size + 'px;' +
                    'height:' + styled.size + 'px;' +
                    'border-radius:50%;' +
                    'background:' + styled.background + ';' +
                    'border:3px solid ' + styled.border + ';' +
                    'box-shadow:' + styled.glow + ';' +
                '"></div>';

            return L.divIcon({
                className: 'central-marker',
                html: html,
                iconSize: [styled.size, styled.size],
                iconAnchor: [styled.size / 2, styled.size / 2],
                popupAnchor: [0, -12]
            });
        }

        function updateMarkerPopup(markerData, generationByType, utilizationByType) {
            const generated = (generationByType[markerData.type] || 0).toFixed(2);
            const utilization = ((utilizationByType[markerData.type] || 0) * 100).toFixed(1);
            const popupContent =
                '<div style="font-size: 12px; width: 220px;">' +
                    '<h4 style="margin: 0 0 8px 0;">' + markerData.name + '</h4>' +
                    '<div><strong>Tipo:</strong> ' + markerData.type + '</div>' +
                    '<div><strong>Generacion tipo:</strong> ' + generated + ' MW</div>' +
                    '<div><strong>Uso estimado tipo:</strong> ' + utilization + '%</div>' +
                    '<div><strong>Latitud:</strong> ' + markerData.lat.toFixed(6) + '</div>' +
                    '<div><strong>Longitud:</strong> ' + markerData.lon.toFixed(6) + '</div>' +
                '</div>';
            markerData.marker.bindPopup(popupContent);
        }

        function buildLegend(generationByType, utilizationByType) {
            const legend = document.getElementById('legend');
            if (!legend) return;

            const rows = [
                { key: 'HYDRO', label: 'Hidraulica', color: '#0066cc' },
                { key: 'THERMAL', label: 'Termica', color: '#ff6600' },
                { key: 'WIND', label: 'Eolica', color: '#99cc00' },
                { key: 'SOLAR', label: 'Solar', color: '#ffcc00' }
            ];

            let html = '<div class="legend-title">Leyenda Operativa</div>';
            rows.forEach(function(row) {
                const gen = (generationByType[row.key] || 0);
                const util = clamp01(utilizationByType[row.key] || 0);
                html +=
                    '<div class="legend-row">' +
                        '<span class="legend-swatch" style="background:' + row.color + ';"></span>' +
                        '<div>' +
                            '<div class="legend-top"><span>' + row.label + '</span><span>' + gen.toFixed(0) + ' MW</span></div>' +
                            '<div class="legend-bar"><div class="legend-fill" style="background:' + row.color + ';width:' + (util * 100).toFixed(1) + '%;"></div></div>' +
                        '</div>' +
                    '</div>';
            });
            html += '<div style="font-size:10px;color:#4b5563;">El tamano y brillo de cada marcador representan uso estimado.</div>';
            legend.innerHTML = html;
        }

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

                const icon = buildIcon(markerColor, type, {});

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
                markers[id] = {
                    marker: marker,
                    id: id,
                    name: name,
                    type: type,
                    lat: lat,
                    lon: lon,
                    baseColor: markerColor
                };

                console.log('[OK] Marcador agregado: ' + name);
            } catch(e) {
                console.log('[ERROR addMarker] ' + e.message);
            }
        }

        function updateTypeGeneration(generationByType, utilizationByType, generationByPlant, utilizationByPlant) {
            try {
                const generation = generationByType || {};
                const utilization = utilizationByType || {};
                const plantGeneration = generationByPlant || {};
                const plantUtilization = utilizationByPlant || {};

                Object.keys(markers).forEach(function(id) {
                    const markerData = markers[id];
                    const plantUtil = plantUtilization[id];
                    const typeUtil = utilization[markerData.type];
                    const mergedUtil = (typeof plantUtil === 'number') ? plantUtil : typeUtil;
                    const utilMap = {};
                    utilMap[markerData.type] = mergedUtil || 0;
                    markerData.marker.setIcon(buildIcon(markerData.baseColor, markerData.type, utilMap));
                    updateMarkerPopup(markerData, generation, utilization);

                    const plantGen = plantGeneration[id];
                    if (typeof plantGen === 'number') {
                        const popupContent =
                            '<div style="font-size: 12px; width: 220px;">' +
                                '<h4 style="margin: 0 0 8px 0;">' + markerData.name + '</h4>' +
                                '<div><strong>Tipo:</strong> ' + markerData.type + '</div>' +
                                '<div><strong>Generacion central:</strong> ' + plantGen.toFixed(2) + ' MW</div>' +
                                '<div><strong>Uso central:</strong> ' + (((mergedUtil || 0) * 100).toFixed(1)) + '%</div>' +
                                '<div><strong>Latitud:</strong> ' + markerData.lat.toFixed(6) + '</div>' +
                                '<div><strong>Longitud:</strong> ' + markerData.lon.toFixed(6) + '</div>' +
                            '</div>';
                        markerData.marker.bindPopup(popupContent);
                    }
                });

                buildLegend(generation, utilization);
            } catch (e) {
                console.log('[ERROR updateTypeGeneration] ' + e.message);
            }
        }

        window.updateTypeGeneration = updateTypeGeneration;

        function focusMarker(id) {
            try {
                if (!markers[id]) return;
                const markerData = markers[id];
                map.setView([markerData.lat, markerData.lon], Math.max(map.getZoom(), 8), { animate: true });
                markerData.marker.openPopup();
            } catch (e) {
                console.log('[ERROR focusMarker] ' + e.message);
            }
        }

        window.focusMarker = focusMarker;

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

                    bridge.focus_marker.connect(function(id) {
                        focusMarker(id);
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

    def update_generation_overlay(
        self,
        generation_by_type_mw: Dict[str, float],
        utilization_by_type: Dict[str, float],
        generation_by_plant_id_mw: Dict[str, float] | None = None,
        utilization_by_plant_id: Dict[str, float] | None = None,
    ) -> None:
        """Actualiza intensidad visual de marcadores con datos operativos en vivo."""

        generation_json = json.dumps(generation_by_type_mw)
        utilization_json = json.dumps(utilization_by_type)
        plant_generation_json = json.dumps(generation_by_plant_id_mw or {})
        plant_utilization_json = json.dumps(utilization_by_plant_id or {})
        self.page().runJavaScript(
            f"window.updateTypeGeneration({generation_json}, {utilization_json}, {plant_generation_json}, {plant_utilization_json});"
        )

    def focus_marker(self, marker_id: str) -> None:
        """Center and open popup for a marker from Python selection events."""

        if not marker_id:
            return
        self.bridge.focus_marker.emit(marker_id)
