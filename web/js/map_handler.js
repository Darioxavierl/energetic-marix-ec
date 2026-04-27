/**
 * Manejador de Leaflet.js para el simulador de matriz energética
 * Gestiona la visualización de centrales eléctricas en el mapa OSM
 */

let map = null;
let markers = {};

/**
 * Inicializa el mapa Leaflet centrado en Ecuador
 */
function initMap() {
    // Centro de Ecuador: aproximadamente -1.8, -78.2
    map = L.map('map').setView([-1.8, -78.2], 7);

    // Agregar capa base de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
        minZoom: 6
    }).addTo(map);
}

/**
 * Obtiene el color según el tipo de central
 * @param {string} plantType - Tipo de central (HYDRO, THERMAL, WIND, SOLAR)
 * @returns {string} Color hexadecimal
 */
function getColorForType(plantType) {
    const colors = {
        'HYDRO': '#0066cc',      // Azul
        'THERMAL': '#ff6600',    // Naranja
        'WIND': '#99cc00',       // Verde lima
        'SOLAR': '#ffcc00'       // Amarillo
    };
    return colors[plantType] || '#999999';
}

/**
 * Obtiene el tamaño del marcador según la potencia instalada
 * @param {number} capacity - Potencia en MW
 * @returns {number} Radio en pixels
 */
function getSizeForCapacity(capacity) {
    if (capacity >= 1000) return 12;
    if (capacity >= 500) return 10;
    if (capacity >= 200) return 8;
    if (capacity >= 100) return 6;
    return 5;
}

/**
 * Agrega un marcador de central al mapa
 * @param {object} central - Objeto con datos de la central
 */
function addMarker(central) {
    const color = getColorForType(central.type);
    const radius = getSizeForCapacity(central.installed_capacity_mw);

    // Determinar opacidad según estado
    const opacity = central.status === 'ONLINE' ? 1.0 : 0.5;
    const fillOpacity = central.status === 'ONLINE' ? 0.7 : 0.3;

    // Crear marcador de círculo
    const marker = L.circleMarker(
        [central.latitude, central.longitude],
        {
            color: color,
            radius: radius,
            weight: 2,
            opacity: opacity,
            fillOpacity: fillOpacity
        }
    ).addTo(map);

    // Crear contenido del popup
    const popupContent = `
        <div style="width: 250px;">
            <h4 style="margin: 0 0 8px 0; color: #333;">${central.name}</h4>
            <div style="font-size: 12px; color: #666;">
                <div><strong>Tipo:</strong> ${getTypeLabel(central.type)}</div>
                <div><strong>Región:</strong> ${central.region}</div>
                <div><strong>Potencia:</strong> ${central.installed_capacity_mw} MW</div>
                <div><strong>Disponible:</strong> ${central.available_capacity_mw} MW</div>
                <div><strong>Estado:</strong> <span style="color: ${getStatusColor(central.status)}; font-weight: bold;">${central.status}</span></div>
                <div><strong>Operador:</strong> ${central.operator}</div>
            </div>
        </div>
    `;

    marker.bindPopup(popupContent, {
        maxWidth: 300,
        className: 'custom-popup'
    });

    // Almacenar marcador por ID
    markers[central.id] = marker;
}

/**
 * Obtiene etiqueta legible para tipo de central
 * @param {string} type - Tipo de central
 * @returns {string} Etiqueta
 */
function getTypeLabel(type) {
    const labels = {
        'HYDRO': 'Hidroeléctrica',
        'THERMAL': 'Termoeléctrica',
        'WIND': 'Eólica',
        'SOLAR': 'Solar'
    };
    return labels[type] || type;
}

/**
 * Obtiene color según estado de la central
 * @param {string} status - Estado
 * @returns {string} Color hexadecimal
 */
function getStatusColor(status) {
    const colors = {
        'ONLINE': '#00aa00',
        'OFFLINE': '#cc0000',
        'MAINTENANCE': '#ff9900'
    };
    return colors[status] || '#999999';
}

/**
 * Agrega múltiples centrales al mapa
 * @param {array} centrales - Array de objetos central
 */
function addCentrales(centrales) {
    if (!Array.isArray(centrales)) {
        console.error('centrales debe ser un array');
        return;
    }
    centrales.forEach(central => addMarker(central));
    console.log(`✓ ${centrales.length} centrales agregadas al mapa`);
}

/**
 * Limpia todos los marcadores del mapa
 */
function clearMarkers() {
    Object.values(markers).forEach(marker => map.removeLayer(marker));
    markers = {};
}

/**
 * Centra el mapa en una coordenada específica
 * @param {number} lat - Latitud
 * @param {number} lng - Longitud
 * @param {number} zoom - Nivel de zoom
 */
function setMapCenter(lat, lng, zoom = 7) {
    map.setView([lat, lng], zoom);
}

/**
 * Obtiene información de un marcador por ID
 * @param {string} centralId - ID de la central
 * @returns {object} Objeto marcador Leaflet o null
 */
function getMarker(centralId) {
    return markers[centralId] || null;
}

// Inicializar mapa cuando el documento carga
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    console.log('✓ Mapa Leaflet inicializado');
});

// Manejo de errores
window.onerror = function(msg, url, line, col, error) {
    console.error(`Error en Leaflet: ${msg} (${line}:${col})`);
};
