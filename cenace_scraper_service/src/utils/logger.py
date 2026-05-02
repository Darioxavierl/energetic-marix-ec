"""
Configuración de logging centralizado
"""

import logging
import sys
from src.utils.config import LOG_LEVEL, LOG_FORMAT

def setup_logging():
    """Configura logging para toda la aplicación"""
    
    # Crear logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(formatter)
    
    # Agregar handler al root logger
    root_logger.addHandler(console_handler)
    
    return root_logger

# Logger global
logger = setup_logging()
