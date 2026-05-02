"""
Schemas Pydantic para validación de datos
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ============================================================================
# SCHEMAS DE RESPUESTA
# ============================================================================

class ProductionResponse(BaseModel):
    """Respuesta de producción energética"""
    timestamp: datetime = Field(..., description="Timestamp del dato CENACE")
    total_mwh: float = Field(..., description="Producción total en MWh")
    hydro_mwh: float = Field(..., description="Producción hidroeléctrica en MWh")
    thermal_mwh: float = Field(..., description="Producción térmica en MWh")
    renewable_mwh: float = Field(..., description="Producción renovable en MWh")
    import_mwh: float = Field(default=0, description="Importación en MWh")
    export_mwh: float = Field(default=0, description="Exportación en MWh")
    
    # Porcentajes
    hydro_percentage: float = Field(..., description="Porcentaje hidráulica")
    thermal_percentage: float = Field(..., description="Porcentaje térmica")
    renewable_percentage: float = Field(..., description="Porcentaje renovable")
    source: str = Field(default="CENACE", description="Fuente de datos")

class PlantGenerationResponse(BaseModel):
    """Generación por central"""
    plant_id: str
    plant_name: str
    plant_type: Optional[str] = None
    mwh: float
    percentage_of_total: Optional[float] = None
    status: Optional[str] = None

class HourlyCurveResponse(BaseModel):
    """Curva horaria"""
    date: str
    hour: int
    demand_mw: float
    total_production_mw: float
    hydro_mw: float
    thermal_mw: float
    renewable_mw: float
    import_mw: float
    export_mw: float
    balance_mw: Optional[float] = None
    reserve_margin: Optional[float] = None

class HealthResponse(BaseModel):
    """Estado de salud del servicio"""
    status: str = Field(..., description="'healthy' o 'degraded'")
    last_scrape: Optional[datetime] = Field(None, description="Última ejecución de scraper")
    next_scrape: Optional[datetime] = Field(None, description="Próxima ejecución de scraper")
    records_stored: int = Field(default=0, description="Registros en BD")
    success_rate: float = Field(default=0, description="Tasa de éxito en 7 días")

class ValidationResponse(BaseModel):
    """Respuesta de validación"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []

class ScrapeLogResponse(BaseModel):
    """Log de ejecución de scraper"""
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    duration_seconds: float
    records_inserted: int = 0
    records_updated: int = 0

# ============================================================================
# MODELS INTERNOS (para procesar datos)
# ============================================================================

class ProductionData(BaseModel):
    """Datos de producción internos"""
    timestamp: datetime
    total_mwh: float
    hydro_mwh: float
    thermal_mwh: float
    renewable_mwh: float
    import_mwh: float = 0
    export_mwh: float = 0
    
    class Config:
        frozen = False

class DemandData(BaseModel):
    """Datos de demanda internos"""
    timestamp: datetime
    demand_mw: float
