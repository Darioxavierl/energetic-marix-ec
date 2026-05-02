"""
Core scraper: extrae datos de CENACE
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict
import aiohttp
import requests
from src.scraper.html_parser import CENACEHTMLParser
from src.scraper.data_cleaner import DataCleaner
from src.utils.logger import logger
from src.utils.config import CENACE_URL, CENACE_TIMEOUT


class CENACEScraper:
    """Extrae datos de CENACE con reintentos y manejo de errores"""
    
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    
    def __init__(self):
        self.parser = CENACEHTMLParser()
        self.cleaner = DataCleaner()
        self.logger = logger
        self.base_url = CENACE_URL
        self.timeout = CENACE_TIMEOUT
    
    async def scrape_production_data(self) -> Optional[Dict]:
        """
        Extrae datos de producción energética
        
        Retorna dict con:
        - timestamp
        - total_mwh, hydro_mwh, thermal_mwh, renewable_mwh
        - import_mwh, export_mwh
        - hydro_percentage, thermal_percentage, renewable_percentage
        """
        try:
            self.logger.info("Iniciando scrape de CENACE...")
            
            # Obtener HTML
            html = await self._fetch_page()
            
            if not html:
                self.logger.error("No se pudo obtener HTML de CENACE")
                return None
            
            # Parsear
            raw_data = self.parser.parse_production_summary(html)
            
            if not raw_data:
                self.logger.error("Parser no extrajo datos de producción")
                return None
            
            # Limpiar
            cleaned_data = self.cleaner.clean_production_data(raw_data)
            
            if not cleaned_data:
                self.logger.error("Cleaner rechazó los datos")
                return None
            
            # Validar
            if not self.parser.validate_data(cleaned_data):
                self.logger.error("Validación de datos fallida")
                return None
            
            self.logger.info(
                f"✓ Scrape exitoso. Producción total: {cleaned_data['total_mwh']:.0f} MWh "
                f"({cleaned_data['hydro_percentage']:.1f}% hidro, "
                f"{cleaned_data['thermal_percentage']:.1f}% térmica)"
            )
            
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Error en scrape_production_data: {e}")
            return None
    
    async def scrape_demand_data(self) -> Optional[Dict]:
        """Extrae datos de demanda nacional"""
        try:
            html = await self._fetch_page()
            
            if not html:
                return None
            
            # Buscar en HTML referencias a demanda
            # Por ahora retornar None hasta que tengamos más info de CENACE
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
            
            # En CENACE el timestamp está usualmente en un span o párrafo
            # Por ahora retornar la hora actual
            return datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error en get_last_update_time: {e}")
            return None
    
    # ======================================================================
    # MÉTODOS PRIVADOS
    # ======================================================================
    
    async def _fetch_page(self) -> Optional[str]:
        """
        Obtiene HTML de CENACE con reintentos exponenciales
        Timeout: CENACE_TIMEOUT segundos
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.debug(f"Intento {attempt + 1}/{self.MAX_RETRIES} para obtener HTML de CENACE...")
                
                # Usar aiohttp para requests async
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            self.base_url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=self.timeout),
                            ssl=False  # Ignorar certificados SSL para testing
                        ) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                self.logger.debug(f"HTML obtenido exitosamente ({len(html)} bytes)")
                                return html
                            else:
                                self.logger.warning(f"HTTP {resp.status} al conectar con CENACE")
                
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout al conectar (intento {attempt + 1})")
                
                except Exception as e:
                    self.logger.debug(f"Error con aiohttp: {e}, usando requests como fallback...")
                    
                    # Fallback a requests (sincrónico)
                    try:
                        resp = requests.get(
                            self.base_url,
                            headers=headers,
                            timeout=self.timeout,
                            verify=False
                        )
                        if resp.status_code == 200:
                            self.logger.debug(f"HTML obtenido con requests")
                            return resp.text
                    except Exception as e2:
                        self.logger.debug(f"Error con requests: {e2}")
                
                # Backoff exponencial antes de reintentar
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BACKOFF_FACTOR ** attempt
                    self.logger.debug(f"Esperando {wait_time}s antes de reintentar...")
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                self.logger.error(f"Error inesperado en _fetch_page (intento {attempt + 1}): {e}")
        
        self.logger.error(f"No se pudo obtener HTML después de {self.MAX_RETRIES} intentos")
        return None


# ============================================================================
# INTERFAZ SINCRÓNICA (para compatibilidad)
# ============================================================================

class CENACEScraperSync(CENACEScraper):
    """Versión sincrónica del scraper (para uso en scheduler)"""
    
    def scrape_production_data_sync(self) -> Optional[Dict]:
        """Versión sincrónica"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.scrape_production_data())
        finally:
            loop.close()
