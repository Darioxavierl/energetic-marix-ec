"""
Core scraper: extrae datos de CENACE usando Playwright (browser real)
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from src.scraper.html_parser import CENACEHTMLParser
from src.scraper.data_cleaner import DataCleaner
from src.utils.logger import logger
from src.utils.config import (
    CENACE_URL,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_WAIT_SELECTOR,
    PLAYWRIGHT_WAIT_UNTIL,
)


class CENACEScraper:
    """Extrae datos de CENACE usando un browser real (Playwright/Chromium)"""

    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2

    def __init__(self):
        self.parser = CENACEHTMLParser()
        self.cleaner = DataCleaner()
        self.logger = logger
        self.base_url = CENACE_URL

    async def scrape_production_data(self) -> Optional[Dict]:
        try:
            html = await self._fetch_page()
            if not html:
                return None

            # 1. Obtener Resumen
            raw_data = self.parser.parse_production_summary(html)
            cleaned_data = self.cleaner.clean_production_data(raw_data)

            if cleaned_data:
                # 2. Integrar detalle por planta
                cleaned_data["plants"] = self.parser.parse_plant_details(html)

                # 3. Integrar curva horaria
                cleaned_data["hourly_curve"] = self.parser.parse_hourly_curve(html)

            return cleaned_data
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return None

    async def scrape_demand_data(self) -> Optional[Dict]:
        """Extrae datos de demanda nacional"""
        try:
            html = await self._fetch_page()
            if not html:
                return None
            self.logger.debug("scrape_demand_data: No implementado aún")
            return None
        except Exception as e:
            self.logger.error(f"Error en scrape_demand_data: {e}")
            return None

    async def get_last_update_time(self) -> Optional[datetime]:
        """Obtiene timestamp del último dato CENACE disponible"""
        try:
            html = await self._fetch_page()
            if not html:
                return None
            return datetime.now()
        except Exception as e:
            self.logger.error(f"Error en get_last_update_time: {e}")
            return None

    # ======================================================================
    # MÉTODOS PRIVADOS
    # ======================================================================

    async def _fetch_page(self) -> Optional[str]:
        """
        Obtiene el HTML completamente renderizado de CENACE usando Playwright.
        Reintenta con backoff exponencial ante fallos.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.debug(
                    f"Playwright — intento {attempt + 1}/{self.MAX_RETRIES}"
                )
                html = await self._playwright_fetch()
                if html:
                    return html

            except Exception as e:
                self.logger.warning(f"Error en intento {attempt + 1}: {e}")

            if attempt < self.MAX_RETRIES - 1:
                wait_time = self.BACKOFF_FACTOR ** attempt
                self.logger.debug(f"Esperando {wait_time}s antes de reintentar...")
                await asyncio.sleep(wait_time)

        self.logger.error(
            f"No se pudo obtener HTML después de {self.MAX_RETRIES} intentos"
        )
        return None

    async def _playwright_fetch(self) -> Optional[str]:
        """
        Abre la URL con Chromium, espera que el JS renderice los datos,
        y devuelve el HTML completo del DOM.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
            context = await browser.new_context(
                ignore_https_errors=True,  # SSL roto en servidor CENACE
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-EC",
                timezone_id="America/Guayaquil",
            )
            page = await context.new_page()

            try:
                self.logger.debug(f"Navegando a: {self.base_url}")

                await page.goto(
                    self.base_url,
                    timeout=PLAYWRIGHT_TIMEOUT,
                    wait_until=PLAYWRIGHT_WAIT_UNTIL,
                )

                # Esperar al selector configurado (por defecto "table")
                # Si la página usa otro elemento para los datos, ajustar
                # PLAYWRIGHT_WAIT_SELECTOR en el .env
                try:
                    await page.wait_for_selector(
                        PLAYWRIGHT_WAIT_SELECTOR,
                        timeout=15000,
                        state="visible",
                    )
                    self.logger.debug(
                        f"Selector '{PLAYWRIGHT_WAIT_SELECTOR}' encontrado"
                    )
                except PlaywrightTimeout:
                    self.logger.warning(
                        f"Selector '{PLAYWRIGHT_WAIT_SELECTOR}' no apareció "
                        f"en 15s — continuando con el HTML disponible"
                    )

                # Pausa extra para que terminen renders lentos de dashboards
                await page.wait_for_timeout(2000)

                html = await page.content()
                self.logger.debug(
                    f"HTML obtenido exitosamente ({len(html):,} bytes)"
                )
                return html

            except PlaywrightTimeout:
                self.logger.error(
                    f"Timeout ({PLAYWRIGHT_TIMEOUT}ms) esperando la página"
                )
                return None

            except Exception as e:
                self.logger.error(f"Error inesperado en Playwright: {e}")
                return None

            finally:
                await browser.close()


# ============================================================================
# INTERFAZ SINCRÓNICA (para uso en el scheduler con APScheduler)
# ============================================================================

class CENACEScraperSync(CENACEScraper):
    """
    Versión sincrónica — envuelve el scraper async para APScheduler
    (BackgroundScheduler ejecuta jobs en threads, no en event loop).
    """

    @staticmethod
    def _build_event_loop() -> asyncio.AbstractEventLoop:
        """Create an event loop compatible with subprocess-based Playwright launch."""

        if sys.platform.startswith("win") and hasattr(asyncio, "ProactorEventLoop"):
            return asyncio.ProactorEventLoop()
        return asyncio.new_event_loop()

    def scrape_production_data(self) -> Optional[Dict]:  # type: ignore[override]
        """Versión sincrónica: crea un event loop nuevo por ejecución"""
        loop = self._build_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(super().scrape_production_data())
        finally:
            loop.close()
            asyncio.set_event_loop(None)