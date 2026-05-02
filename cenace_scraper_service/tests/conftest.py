"""
Configuración de pytest — incluye mock de Playwright para tests
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def anyio_backend():
    """Configuración para pytest-asyncio"""
    return "asyncio"


@pytest.fixture
def mock_playwright_html():
    """
    HTML simulado que el browser devolvería al visitar CENACE.
    Úsalo en tests del scraper para no lanzar un browser real.
    """
    return """
    <html>
        <body>
            <table>
                <tr><td>PRODUCCIÓN ENERGÉTICA (MWh)</td></tr>
                <tr><td>Total</td><td>89685</td></tr>
                <tr><td>Hidráulica</td><td>63041</td></tr>
                <tr><td>Térmica</td><td>25726</td></tr>
                <tr><td>Renovable</td><td>665</td></tr>
                <tr><td>Importación</td><td>117</td></tr>
                <tr><td>Exportación</td><td>83</td></tr>
            </table>
        </body>
    </html>
    """


@pytest.fixture
def mock_scraper_fetch(mock_playwright_html):
    """
    Parchea _fetch_page() del scraper para devolver HTML falso
    sin abrir ningún browser. Úsalo en tests de integración del scraper.

    Uso:
        async def test_algo(mock_scraper_fetch):
            scraper = CENACEScraper()
            data = await scraper.scrape_production_data()
            assert data is not None
    """
    with patch(
        "src.scraper.cenace_scraper.CENACEScraper._fetch_page",
        new_callable=AsyncMock,
        return_value=mock_playwright_html,
    ):
        yield