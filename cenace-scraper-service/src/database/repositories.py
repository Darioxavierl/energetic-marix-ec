"""
Repository pattern para acceso a datos
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from src.database.models import (
    ProductionSnapshot,
    PlantGeneration,
    HourlyCurve,
    ScrapeLog
)
from src.utils.logger import logger


class ProductionRepository:
    """Acceso a ProductionSnapshot"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: dict) -> ProductionSnapshot:
        """Crea nueva captura de producción"""
        snapshot = ProductionSnapshot(**data)
        self.db.add(snapshot)
        self.db.commit()
        logger.info(f"ProductionSnapshot creado: {snapshot.timestamp}")
        return snapshot
    
    def get_latest(self) -> Optional[ProductionSnapshot]:
        """Obtiene el snapshot más reciente"""
        return self.db.query(ProductionSnapshot).order_by(
            desc(ProductionSnapshot.timestamp)
        ).first()
    
    def get_by_date_range(self, start: datetime, end: datetime) -> List[ProductionSnapshot]:
        """Obtiene snapshots en rango de fechas"""
        return self.db.query(ProductionSnapshot).filter(
            and_(
                ProductionSnapshot.timestamp >= start,
                ProductionSnapshot.timestamp <= end
            )
        ).order_by(ProductionSnapshot.timestamp).all()
    
    def get_last_n_days(self, days: int = 30) -> List[ProductionSnapshot]:
        """Obtiene últimos N días de datos"""
        start = datetime.now() - timedelta(days=days)
        return self.get_by_date_range(start, datetime.now())


class PlantRepository:
    """Acceso a PlantGeneration"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_batch(self, data_list: List[dict]) -> int:
        """Crea múltiples registros de generación por central"""
        objects = [PlantGeneration(**data) for data in data_list]
        self.db.bulk_save_objects(objects)
        self.db.commit()
        logger.info(f"✓ {len(objects)} registros PlantGeneration insertados")
        return len(objects)
    
    def get_by_timestamp(self, timestamp: datetime) -> List[PlantGeneration]:
        """Obtiene todas las centrales en un timestamp"""
        return self.db.query(PlantGeneration).filter(
            PlantGeneration.timestamp == timestamp
        ).all()
    
    def get_by_plant_id(self, plant_id: str, limit: int = 100) -> List[PlantGeneration]:
        """Obtiene histórico de una central específica"""
        return self.db.query(PlantGeneration).filter(
            PlantGeneration.plant_id == plant_id
        ).order_by(desc(PlantGeneration.timestamp)).limit(limit).all()
    
    def get_latest_by_type(self, plant_type: str) -> List[PlantGeneration]:
        """Obtiene centrales más recientes de un tipo"""
        latest = self.db.query(PlantGeneration.timestamp).order_by(
            desc(PlantGeneration.timestamp)
        ).first()
        
        if not latest:
            return []
        
        return self.db.query(PlantGeneration).filter(
            and_(
                PlantGeneration.timestamp == latest[0],
                PlantGeneration.plant_type == plant_type
            )
        ).all()


class HourlyCurveRepository:
    """Acceso a HourlyCurve"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_batch(self, data_list: List[dict]) -> int:
        """Crea curvas horarias"""
        objects = [HourlyCurve(**data) for data in data_list]
        self.db.bulk_save_objects(objects)
        self.db.commit()
        logger.info(f"✓ {len(objects)} registros HourlyCurve insertados")
        return len(objects)
    
    def get_by_date(self, date) -> List[HourlyCurve]:
        """Obtiene todas las horas de un día"""
        return self.db.query(HourlyCurve).filter(
            HourlyCurve.date == date
        ).order_by(HourlyCurve.hour).all()
    
    def get_latest_24_hours(self) -> List[HourlyCurve]:
        """Obtiene últimas 24 horas"""
        start = datetime.now() - timedelta(hours=24)
        return self.db.query(HourlyCurve).filter(
            HourlyCurve.created_at >= start
        ).order_by(HourlyCurve.created_at).all()


class ScrapeLogRepository:
    """Acceso a logs de scraping"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_success(self, duration: float, inserted: int, updated: int):
        """Registra ejecución exitosa"""
        log = ScrapeLog(
            success=True,
            duration_seconds=duration,
            records_inserted=inserted,
            records_updated=updated
        )
        self.db.add(log)
        self.db.commit()
        logger.info(f"✓ ScrapeLog exitoso: {duration:.2f}s, {inserted} insertados")
    
    def log_error(self, error: Exception, duration: float = 0):
        """Registra error de ejecución"""
        log = ScrapeLog(
            success=False,
            error_message=str(error)[:500],
            duration_seconds=duration
        )
        self.db.add(log)
        self.db.commit()
        logger.error(f"✗ ScrapeLog error: {str(error)[:100]}")
    
    def get_last_n_logs(self, n: int = 50) -> List[ScrapeLog]:
        """Obtiene últimos N logs"""
        return self.db.query(ScrapeLog).order_by(
            desc(ScrapeLog.timestamp)
        ).limit(n).all()
    
    def get_success_rate(self, days: int = 7) -> float:
        """Calcula tasa de éxito en últimos N días"""
        start = datetime.now() - timedelta(days=days)
        total = self.db.query(ScrapeLog).filter(
            ScrapeLog.timestamp >= start
        ).count()
        
        if total == 0:
            return 0.0
        
        success = self.db.query(ScrapeLog).filter(
            and_(
                ScrapeLog.timestamp >= start,
                ScrapeLog.success == True
            )
        ).count()
        
        return (success / total) * 100
