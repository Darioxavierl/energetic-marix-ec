"""
Configuración de pytest
"""

import pytest
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def anyio_backend():
    """Configuración para pytest-asyncio"""
    return "asyncio"
