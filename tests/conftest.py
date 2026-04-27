"""
Configuración de pytest
"""
import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Retorna la raíz del proyecto"""
    return Path(__file__).parent.parent


@pytest.fixture
def data_dir(project_root):
    """Retorna directorio de datos"""
    return project_root / "data"


@pytest.fixture
def centrales_json(data_dir):
    """Retorna ruta del archivo de centrales"""
    return data_dir / "centrales" / "centrales_ecuador.json"
