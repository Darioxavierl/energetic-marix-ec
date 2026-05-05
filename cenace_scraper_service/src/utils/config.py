"""
Configuración centralizada del microservicio
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(ENV_FILE)

# Rutas base
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

# Configuración de la aplicación
APP_NAME = "CENACE Scraper Service"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Configuración de BD
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cenace.db")
DATABASE_PATH = BASE_DIR / "cenace.db"

# Configuración de CENACE
CENACE_URL = os.getenv("CENACE_URL", "https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm")
CENACE_TIMEOUT = int(os.getenv("CENACE_TIMEOUT", "10"))

# Configuración de scheduler
SCRAPER_INTERVAL_MINUTES = int(os.getenv("SCRAPER_INTERVAL_MINUTES", "15"))

# Configuración de API
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8001"))
API_RELOAD = os.getenv("API_RELOAD", "False").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Configuración de Playwright
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "True").lower() == "true"
PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))  # ms
PLAYWRIGHT_WAIT_SELECTOR = os.getenv("PLAYWRIGHT_WAIT_SELECTOR", ".resumen-box.total")
PLAYWRIGHT_WAIT_UNTIL = os.getenv("PLAYWRIGHT_WAIT_UNTIL", "networkidle")