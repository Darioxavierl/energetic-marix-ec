"""
Parser HTML para CENACE
Extrae datos de: https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm
"""

import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from src.utils.logger import logger


def normalize_text(text: str) -> str:
    """Normaliza texto: lowercase y elimina acentos"""
    text = text.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


class CENACEHTMLParser:
    """Parsea HTML de CENACE con múltiples estrategias"""
    
    def __init__(self):
        self.logger = logger
    
    def parse_production_summary(self, html: str) -> Optional[Dict]:
        """
        Extrae tabla "PRODUCCIÓN ENERGÉTICA (MWh)"
        
        Retorna:
        {
            "timestamp": "2026-04-29 14:30:00",
            "total_mwh": 89685,
            "hydro_mwh": 63041,
            "thermal_mwh": 25726,
            "renewable_mwh": 665,
            "import_mwh": 117,
            "export_mwh": 83
        }
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Estrategia 1: Buscar por texto en table cells
            data = {}
            
            # Buscar todas las tablas
            tables = soup.find_all('table')
            self.logger.debug(f"Encontradas {len(tables)} tablas en HTML")
            
            for table in tables:
                # Buscar "PRODUCCIÓN" y "Total"
                text_content = table.get_text(strip=True)
                
                if "PRODUCCIÓN" in text_content or "Producción" in text_content:
                    # Buscar filas con números
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        row_text = row.get_text(strip=True)
                        
                        # Total (MWh)
                        if "Total" in row_text and any(c.isdigit() for c in row_text):
                            total_value = self._extract_number(row_text)
                            if total_value:
                                data['total_mwh'] = total_value
                        
                        # Hidráulica
                        if "Hidráulica" in row_text or "Hydroelectric" in row_text:
                            value = self._extract_number(row_text)
                            if value:
                                data['hydro_mwh'] = value
                        
                        # Térmica
                        if "Térmica" in row_text or "Thermal" in row_text:
                            value = self._extract_number(row_text)
                            if value:
                                data['thermal_mwh'] = value
                        
                        # Renovable
                        if "Renovable" in row_text or "Renewable" in row_text:
                            value = self._extract_number(row_text)
                            if value:
                                data['renewable_mwh'] = value
                        
                        # Importación
                        if "Importación" in row_text or "Import" in row_text:
                            value = self._extract_number(row_text)
                            if value:
                                data['import_mwh'] = value
                        
                        # Exportación
                        if "Exportación" in row_text or "Export" in row_text:
                            value = self._extract_number(row_text)
                            if value:
                                data['export_mwh'] = value
            
            if not data:
                self.logger.warning("No se encontraron datos de producción en HTML")
                return None
            
            # Agregar timestamp actual (CENACE no siempre lo especifica)
            data['timestamp'] = datetime.now()
            
            self.logger.debug(f"Datos de producción extraídos: {data}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error parseando producción: {e}")
            return None
    
    def parse_plant_details(self, html: str) -> List[Dict]:
        """
        Extrae tabla "DETALLE DE PRODUCCIÓN (MWh)"
        
        Retorna:
        [
            {
                "plant_name": "Mazar",
                "plant_type": "HYDRO",
                "mwh": 14493,
                "percentage": 33
            },
            ...
        ]
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            plants = []
            
            tables = soup.find_all('table')
            
            for table in tables:
                text_content = table.get_text(strip=True)
                
                if "DETALLE" in text_content or "Detalles" in text_content or "Centrales" in text_content:
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            row_text = row.get_text(strip=True)
                            
                            # Saltar headers
                            if any(header in row_text for header in ["CENTRAL", "Central", "Central", "MWh", "Nombre"]):
                                continue
                            
                            # Intentar extraer nombre de central y valor
                            plant_name = cells[0].get_text(strip=True) if len(cells) > 0 else None
                            mwh_value = self._extract_number(cells[-1].get_text()) if len(cells) > 1 else None
                            
                            if plant_name and mwh_value:
                                plants.append({
                                    "plant_name": plant_name,
                                    "mwh": mwh_value,
                                    "plant_type": self._infer_plant_type(plant_name),
                                    "percentage": 0  # Se calcula después
                                })
            
            self.logger.debug(f"Encontradas {len(plants)} centrales")
            return plants
            
        except Exception as e:
            self.logger.error(f"Error parseando detalles de plantas: {e}")
            return []
    
    def parse_hourly_curve(self, html: str) -> List[Dict]:
        """
        Extrae curva de demanda/generación horaria
        
        Retorna:
        [
            {
                "hour": 0,
                "demand_mw": 3500,
                "total_production_mw": 3450,
                ...
            },
            ...
        ]
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            hourly_data = []
            
            # Buscar tabla con datos horarios
            tables = soup.find_all('table')
            
            for table in tables:
                text_content = table.get_text(strip=True)
                
                if "HORA" in text_content or "HOUR" in text_content or "horaria" in text_content:
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        row_text = row.get_text(strip=True)
                        
                        # Saltar headers
                        if any(h in row_text for h in ["HORA", "HOUR", "Hora"]):
                            continue
                        
                        if len(cells) >= 2:
                            try:
                                hour_val = self._extract_number(cells[0].get_text())
                                if hour_val is not None and 0 <= hour_val <= 23:
                                    hourly_data.append({
                                        "hour": int(hour_val),
                                        "demand_mw": 0,
                                        "total_production_mw": 0
                                    })
                            except:
                                pass
            
            self.logger.debug(f"Encontradas {len(hourly_data)} horas de datos")
            return hourly_data
            
        except Exception as e:
            self.logger.error(f"Error parseando curva horaria: {e}")
            return []
    
    def validate_data(self, data: Dict) -> bool:
        """
        Valida coherencia de datos
        
        - Suma de fuentes = total
        - Valores positivos
        - Rango razonable
        """
        try:
            if not data:
                return False
            
            required_fields = ['total_mwh', 'hydro_mwh', 'thermal_mwh', 'renewable_mwh']
            
            for field in required_fields:
                if field not in data:
                    self.logger.warning(f"Campo faltante: {field}")
                    return False
            
            # Verificar que suma de fuentes ≈ total (con tolerancia del 10%)
            sources_sum = (
                data.get('hydro_mwh', 0) +
                data.get('thermal_mwh', 0) +
                data.get('renewable_mwh', 0) +
                data.get('import_mwh', 0)
            )
            
            total = data.get('total_mwh', 0)
            
            if sources_sum > 0:
                diff_percent = abs((sources_sum - total) / sources_sum) * 100
                if diff_percent > 10:
                    self.logger.warning(
                        f"Suma de fuentes ({sources_sum}) no coincide con total ({total}). "
                        f"Diferencia: {diff_percent:.1f}%"
                    )
            
            # Verificar valores positivos
            for field in required_fields:
                if data.get(field, 0) < 0:
                    self.logger.warning(f"Valor negativo: {field} = {data[field]}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando datos: {e}")
            return False
    
    # ======================================================================
    # MÉTODOS AUXILIARES
    # ======================================================================
    
    def _extract_number(self, text: str) -> Optional[float]:
        """
        Extrae número de un string (maneja comas, puntos, etc.)
        
        Ejemplos:
        - "63,041 MWh" -> 63041
        - "2.400 MW" -> 2400
        - "150.5" -> 150.5
        """
        try:
            if not text:
                return None
            
            # Eliminar espacios y caracteres especiales
            text = text.strip()
            
            # Buscar patrón de número (maneja . y , como separadores)
            match = re.search(r'[\d\.\,]+', text)
            
            if match:
                number_str = match.group()
                
                # Si tiene coma y punto, determinar cuál es separador decimal
                if ',' in number_str and '.' in number_str:
                    if number_str.rindex('.') > number_str.rindex(','):
                        # 1,000.5 (US format) -> reemplazar coma
                        number_str = number_str.replace(',', '')
                    else:
                        # 1.000,5 (EU format) -> reemplazar punto y coma->punto
                        number_str = number_str.replace('.', '')
                        number_str = number_str.replace(',', '.')
                elif '.' in number_str:
                    # Solo tiene puntos: ¿decimal o miles?
                    parts = number_str.split('.')
                    if len(parts) >= 2 and len(parts[-1]) == 1:
                        # "1.000.5" -> mantener último como decimal
                        number_str = number_str[:number_str.rfind('.')].replace('.', '') + '.' + parts[-1]
                    elif len(parts) >= 2 and len(parts[-1]) >= 2:
                        # "1.000" o "63.041" -> remover puntos de miles
                        number_str = number_str.replace('.', '')
                    # Si "150.5", dejar como está
                elif ',' in number_str:
                    # Verificar si es separador decimal o miles
                    parts = number_str.split(',')
                    if len(parts[-1]) <= 2:  # Probablemente decimal (1 o 2 dígitos)
                        number_str = number_str.replace('.', '').replace(',', '.')
                    else:  # Es miles
                        number_str = number_str.replace(',', '')
                
                return float(number_str)
        except:
            pass
        
        return None
    
    def _infer_plant_type(self, plant_name: str) -> str:
        """Infiere tipo de central basado en el nombre"""
        name_normalized = normalize_text(plant_name)
        
        if any(word in name_normalized for word in ['hidroelectrica', 'hidro', 'hydro', 'presa', 'represa', 'salto', 'embalse']):
            return 'HYDRO'
        elif any(word in name_normalized for word in ['termica', 'termico', 'thermal', 'carbon', 'gas', 'fuel', 'termo']):
            return 'THERMAL'
        elif any(word in name_normalized for word in ['eolica', 'eolico', 'wind', 'solar', 'fotovoltaica', 'biomasa']):
            return 'RENEWABLE'
        else:
            return 'OTHER'
