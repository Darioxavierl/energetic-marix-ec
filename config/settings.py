"""
Configuración centralizada de la aplicación
"""
from pathlib import Path

# Paths absolutos
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CENTRALES_JSON = DATA_DIR / "centrales" / "centrales_ecuador.json"
SCENARIOS_DIR = DATA_DIR / "scenarios"
WEB_DIR = PROJECT_ROOT / "web"
CONFIG_DIR = PROJECT_ROOT / "config"

# Configuración del mapa
MAP_DEFAULTS = {
    "center_lat": -1.8,
    "center_lon": -78.2,
    "zoom": 7,
}

# Colores por tipo de central
PLANT_COLORS = {
    "HYDRO": "#0066cc",
    "THERMAL": "#ff6600",
    "WIND": "#99cc00",
    "SOLAR": "#ffcc00",
}

# Aplicación
APP_TITLE = "Simulador Matriz Energética Ecuador"
APP_VERSION = "0.1.0"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Integracion con microservicio CENACE scraper
MICROSERVICE_BASE_URL = "http://127.0.0.1:8001"
MICROSERVICE_TIMEOUT_SECONDS = 5.0
MICROSERVICE_SYNC_INTERVAL_MS = 30000

# Umbrales de riesgo configurables (% reserva)
RISK_THRESHOLD_SAFE_PCT = 20.0
RISK_THRESHOLD_ALERT_PCT = 10.0
RISK_THRESHOLD_CRITICAL_PCT = 0.0

# Modelo físico simplificado hidro
HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT = 80.0

# Control global de sequía en UI (0-100)
GLOBAL_DROUGHT_MIN = 0.0
GLOBAL_DROUGHT_MAX = 100.0
GLOBAL_DROUGHT_DEFAULT = 0.0

# Charts panel settings
CHART_HISTORY_MAX_POINTS = 120
