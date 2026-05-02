"""
Modelos SQLAlchemy para CENACE Scraper
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Date, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ProductionSnapshot(Base):
    """Captura puntual de producción energética"""
    __tablename__ = "production_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, unique=True, nullable=False, index=True)
    
    # Producción en MWh
    total_mwh = Column(Float, nullable=False)
    hydro_mwh = Column(Float, nullable=False)
    thermal_mwh = Column(Float, nullable=False)
    renewable_mwh = Column(Float, nullable=False)
    import_mwh = Column(Float, default=0)
    export_mwh = Column(Float, default=0)
    
    # Porcentajes
    hydro_percentage = Column(Float, default=0)
    thermal_percentage = Column(Float, default=0)
    renewable_percentage = Column(Float, default=0)
    
    # Metadata
    source = Column(String(50), default="CENACE_SCADA")
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(String(500))
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return (
            f"<ProductionSnapshot(timestamp={self.timestamp}, "
            f"total={self.total_mwh:.0f}MWh, hydro={self.hydro_percentage:.1f}%)>"
        )


class PlantGeneration(Base):
    """Generación por central individual"""
    __tablename__ = "plant_generations"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Identificación de central
    plant_id = Column(String(100), nullable=False, index=True)
    plant_name = Column(String(200), nullable=False)
    plant_type = Column(String(50))  # HYDRO, THERMAL, RENEWABLE, OTHER
    
    # Generación
    mwh = Column(Float)  # Energía en MWh
    mw_current = Column(Float)  # Potencia instantánea extrapolada
    percentage_of_total = Column(Float)
    
    # Estado
    status = Column(String(20))  # ONLINE, OFFLINE, MAINTENANCE
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<PlantGeneration(name={self.plant_name}, mwh={self.mwh})>"


class HourlyCurve(Base):
    """Curva de demanda/generación horaria"""
    __tablename__ = "hourly_curves"
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)  # 0-23
    minute = Column(Integer, nullable=False, default=0)  # 0-59 (CENACE usa 0 y 30)
    
    # Demanda (MW)
    demand_mw = Column(Float)
    
    # Generación (MW)
    total_production_mw = Column(Float)
    hydro_mw = Column(Float)
    thermal_mw = Column(Float)
    renewable_mw = Column(Float)
    import_mw = Column(Float)
    export_mw = Column(Float)
    
    # Métricas calculadas
    balance_mw = Column(Float)  # Generación - Demanda
    reserve_margin = Column(Float)  # % respecto demanda
    risk_level = Column(String(20))  # SAFE, ALERT, CRITICAL, FAILURE
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return (
            f"<HourlyCurve(date={self.date}, hour={self.hour}:{self.minute:02d}, "
            f"demand={self.demand_mw:.0f}MW, balance={self.balance_mw:.0f}MW)>"
        )


class ScrapeLog(Base):
    """Log de ejecuciones del scraper"""
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Resultado
    success = Column(Boolean)
    error_message = Column(String(500))
    
    # Estadísticas
    duration_seconds = Column(Float)
    records_inserted = Column(Integer)
    records_updated = Column(Integer)
    
    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"<ScrapeLog({status} {self.timestamp} - {self.duration_seconds:.2f}s)>"
