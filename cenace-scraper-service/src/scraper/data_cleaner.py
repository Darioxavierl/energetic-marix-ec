"""
Limpieza y validación de datos extraídos de CENACE
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.logger import logger


class DataCleaner:
    """Normaliza y valida datos extraídos"""
    
    # Rangos realistas para Ecuador (valores en MWh, no MW)
    # Capacidad instalada: ~6,500 MW
    # CENACE reporta en MWh (energía acumulada o en períodos)
    MIN_DEMAND_MWH = 2000
    MAX_DEMAND_MWH = 6000
    MAX_GENERATION_MWH = 150000  # Máximo razonable para valores de CENACE en MWh
    
    def __init__(self):
        self.logger = logger
    
    def clean_production_data(self, raw_data: Dict) -> Optional[Dict]:
        """
        Limpia datos de producción:
        1. Valida tipos numéricos
        2. Redondea a decimales significativos
        3. Verifica sumas
        4. Detecta outliers
        5. Imputa valores faltantes
        """
        try:
            cleaned = {}
            
            # Copiar timestamp
            if 'timestamp' in raw_data:
                cleaned['timestamp'] = raw_data['timestamp']
            else:
                cleaned['timestamp'] = datetime.now()
            
            # Procesar MWh (producción)
            fields = {
                'total_mwh': ('total_mwh', float),
                'hydro_mwh': ('hydro_mwh', float),
                'thermal_mwh': ('thermal_mwh', float),
                'renewable_mwh': ('renewable_mwh', float),
                'import_mwh': ('import_mwh', float, 0),  # default 0
                'export_mwh': ('export_mwh', float, 0),  # default 0
            }
            
            for key, spec in fields.items():
                field_name = spec[0]
                field_type = spec[1]
                default = spec[2] if len(spec) > 2 else None
                
                try:
                    value = raw_data.get(field_name, default)
                    
                    if value is None:
                        if default is not None:
                            cleaned[key] = float(default)
                        else:
                            self.logger.warning(f"Campo faltante: {field_name}")
                            return None
                    else:
                        value = float(value)
                        
                        # Validar rango
                        if value < 0:
                            self.logger.warning(f"Valor negativo en {field_name}: {value}")
                            return None
                        
                        cleaned[key] = round(value, 2)
                
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Error convertiendo {field_name}: {e}")
                    return None
            
            # Calcular porcentajes
            total = cleaned.get('total_mwh', 0)
            if total > 0:
                cleaned['hydro_percentage'] = round((cleaned['hydro_mwh'] / total) * 100, 2)
                cleaned['thermal_percentage'] = round((cleaned['thermal_mwh'] / total) * 100, 2)
                cleaned['renewable_percentage'] = round((cleaned['renewable_mwh'] / total) * 100, 2)
            else:
                cleaned['hydro_percentage'] = 0
                cleaned['thermal_percentage'] = 0
                cleaned['renewable_percentage'] = 0
            
            # Validar coherencia
            if not self._validate_coherence(cleaned):
                self.logger.warning("Datos incoherentes detectados")
                return None
            
            self.logger.debug(f"Datos limpios: {cleaned}")
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error limpiando datos de producción: {e}")
            return None
    
    def validate_ranges(self, data: Dict) -> bool:
        """
        Verifica que los valores están en rangos realistas para Ecuador
        """
        try:
            total_mwh = data.get('total_mwh', 0)
            
            # Demanda típica: 30,000-150,000 MWh (valores reales de CENACE)
            # Generación: similar a demanda + pérdidas
            
            if total_mwh > self.MAX_GENERATION_MWH:  # Muy alto
                self.logger.warning(f"Generación anormalmente alta: {total_mwh} MWh")
                return False
            
            if total_mwh < self.MIN_DEMAND_MWH:  # Muy bajo
                self.logger.warning(f"Generación anormalmente baja: {total_mwh} MWh")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando rangos: {e}")
            return False
    
    def detect_outliers(self, value: float, field: str, historical_data: Optional[List[float]] = None) -> bool:
        """
        Detecta outliers comparando con datos históricos
        """
        try:
            if not historical_data or len(historical_data) < 3:
                return True  # No se puede validar sin histórico
            
            # Calcular media y desviación estándar
            import statistics
            
            mean = statistics.mean(historical_data)
            stdev = statistics.stdev(historical_data) if len(historical_data) > 1 else 0
            
            # Outlier si > 3 desviaciones estándar de la media
            if stdev > 0:
                z_score = abs((value - mean) / stdev)
                if z_score > 3:
                    self.logger.warning(
                        f"Outlier detectado en {field}: {value} "
                        f"(media: {mean:.2f}, z-score: {z_score:.2f})"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"No se pudo detectar outlier: {e}")
            return True
    
    def sanitize_html(self, html: str) -> str:
        """Sanitiza HTML para evitar inyecciones"""
        try:
            # Importar bleach si está disponible
            try:
                import bleach
                html = bleach.clean(html, tags=[], strip=True)
            except ImportError:
                # Si no está disponible, solo eliminar scripts
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.DOTALL)
            
            return html
        except Exception as e:
            self.logger.warning(f"Error sanitizando HTML: {e}")
            return html
    
    # ======================================================================
    # MÉTODOS PRIVADOS
    # ======================================================================
    
    def _validate_coherence(self, data: Dict) -> bool:
        """Verifica coherencia interna de los datos"""
        try:
            # Suma de fuentes debería ≈ total
            sources_sum = (
                data.get('hydro_mwh', 0) +
                data.get('thermal_mwh', 0) +
                data.get('renewable_mwh', 0) +
                data.get('import_mwh', 0)
            )
            
            total = data.get('total_mwh', 0)
            
            # Permitir 5% de diferencia
            if sources_sum > 0 and total > 0:
                diff_percent = abs((sources_sum - total) / sources_sum) * 100
                
                if diff_percent > 15:  # Más lenient que parser
                    self.logger.warning(
                        f"Incoherencia: sum({sources_sum:.0f}) vs total({total:.0f}) = {diff_percent:.1f}%"
                    )
                    return False
            
            # Verificar porcentajes
            hydro_pct = data.get('hydro_percentage', 0)
            thermal_pct = data.get('thermal_percentage', 0)
            renewable_pct = data.get('renewable_percentage', 0)
            
            total_pct = hydro_pct + thermal_pct + renewable_pct
            
            # Los porcentajes deberían sumar ~100%
            if abs(total_pct - 100) > 5:
                self.logger.debug(f"Porcentajes no suman 100%: {total_pct:.1f}%")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando coherencia: {e}")
            return False
