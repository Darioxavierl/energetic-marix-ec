"""
Endpoints de API para CENACE Scraper
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database.db_session import get_db
from src.database.repositories import (
    ProductionRepository,
    PlantRepository,
    HourlyCurveRepository,
    ScrapeLogRepository
)
from src.api.schemas import (
    ProductionResponse,
    PlantGenerationResponse,
    HourlyCurveResponse,
    HealthResponse,
    ScrapeLogResponse
)
from src.utils.config import SCRAPER_INTERVAL_MINUTES
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["CENACE Data"])


# ====== PRODUCTION ENDPOINTS ======

@router.get("/production/latest", response_model=ProductionResponse)
async def get_latest_production(db: Session = Depends(get_db)):
    """Obtiene la captura más reciente de producción"""
    repo = ProductionRepository(db)
    snapshot = repo.get_latest()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="No production data available")
    
    return ProductionResponse(
        timestamp=snapshot.timestamp,
        total_mwh=snapshot.total_mwh,
        hydro_mwh=snapshot.hydro_mwh,
        thermal_mwh=snapshot.thermal_mwh,
        renewable_mwh=snapshot.renewable_mwh,
        hydro_percentage=snapshot.hydro_percentage,
        thermal_percentage=snapshot.thermal_percentage,
        renewable_percentage=snapshot.renewable_percentage,
        import_mwh=snapshot.import_mwh,
        export_mwh=snapshot.export_mwh,
        source=snapshot.source
    )


@router.get("/production/history", response_model=List[ProductionResponse])
async def get_production_history(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Obtiene histórico de producción (últimos N días)"""
    repo = ProductionRepository(db)
    snapshots = repo.get_last_n_days(days)
    
    return [
        ProductionResponse(
            timestamp=s.timestamp,
            total_mwh=s.total_mwh,
            hydro_mwh=s.hydro_mwh,
            thermal_mwh=s.thermal_mwh,
            renewable_mwh=s.renewable_mwh,
            hydro_percentage=s.hydro_percentage,
            thermal_percentage=s.thermal_percentage,
            renewable_percentage=s.renewable_percentage,
            import_mwh=s.import_mwh,
            export_mwh=s.export_mwh,
            source=s.source
        )
        for s in snapshots
    ]


# ====== PLANT ENDPOINTS ======

@router.get("/plants/latest", response_model=List[PlantGenerationResponse])
async def get_latest_plants(db: Session = Depends(get_db)):
    """Obtiene generación más reciente por central"""
    from src.database.models import PlantGeneration
    from sqlalchemy import func
    
    # Obtener timestamp más reciente
    latest_timestamp = db.query(func.max(PlantGeneration.timestamp)).scalar()
    
    if not latest_timestamp:
        raise HTTPException(status_code=404, detail="No plant data available")
    
    plants = db.query(PlantGeneration).filter(
        PlantGeneration.timestamp == latest_timestamp
    ).all()
    
    return [
        PlantGenerationResponse(
            plant_id=p.plant_id,
            plant_name=p.plant_name,
            plant_type=p.plant_type,
            mwh=p.mwh,
            percentage_of_total=p.percentage_of_total,
            status=p.status
        )
        for p in plants
    ]


@router.get("/plants/{plant_id}/history", response_model=List[PlantGenerationResponse])
async def get_plant_history(plant_id: str, db: Session = Depends(get_db)):
    """Obtiene histórico de una central específica"""
    repo = PlantRepository(db)
    plants = repo.get_by_plant_id(plant_id)
    
    if not plants:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")
    
    return [
        PlantGenerationResponse(
            plant_id=p.plant_id,
            plant_name=p.plant_name,
            plant_type=p.plant_type,
            mwh=p.mwh,
            percentage_of_total=p.percentage_of_total,
            status=p.status
        )
        for p in plants
    ]


# ====== HOURLY CURVE ENDPOINTS ======

@router.get("/demand/hourly", response_model=List[HourlyCurveResponse])
async def get_hourly_demand(
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtiene curva horaria de demanda"""
    repo = HourlyCurveRepository(db)
    
    if date:
        try:
            target_date = datetime.fromisoformat(date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        curves = repo.get_by_date(target_date)
    else:
        curves = repo.get_latest_24_hours()
    
    if not curves:
        raise HTTPException(status_code=404, detail="No hourly data available")
    
    return [
        HourlyCurveResponse(
            date=c.date,
            hour=c.hour,
            minute=c.minute,
            demand_mw=c.demand_mw,
            total_production_mw=c.total_production_mw,
            hydro_mw=c.hydro_mw,
            thermal_mw=c.thermal_mw,
            renewable_mw=c.renewable_mw,
            import_mw=c.import_mw,
            export_mw=c.export_mw,
            balance_mw=c.balance_mw,
            reserve_margin=c.reserve_margin,
            risk_level=c.risk_level
        )
        for c in curves
    ]


# ====== HEALTH / MONITORING ENDPOINTS ======

@router.get("/health", response_model=HealthResponse)
async def get_health(db: Session = Depends(get_db)):
    """Estado de salud del servicio con conteo real"""
    try:
        from src.database.models import ProductionSnapshot
        
        scrape_repo = ScrapeLogRepository(db)
        success_rate = scrape_repo.get_success_rate(days=7)
        last_logs = scrape_repo.get_last_n_logs(1)
        
        # Conteo real de datos
        total_records = db.query(ProductionSnapshot).count()
        
        last_scrape = last_logs[0].timestamp if last_logs else None
        next_scrape = (
            last_scrape + timedelta(minutes=SCRAPER_INTERVAL_MINUTES)
            if last_scrape else None
        )

        return HealthResponse(
            status="healthy" if success_rate >= 50 else "degraded",
            last_scrape=last_scrape,
            next_scrape=next_scrape,
            records_stored=total_records,
            success_rate=success_rate
        )
    except Exception as e:
        logger.error(f"Health check fallido: {e}")
        raise HTTPException(status_code=500, detail="Error interno en health check")


@router.get("/logs", response_model=List[ScrapeLogResponse])
async def get_scrape_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Obtiene logs de scraping"""
    repo = ScrapeLogRepository(db)
    logs = repo.get_last_n_logs(limit)
    
    return [
        ScrapeLogResponse(
            timestamp=log.timestamp,
            success=log.success,
            error_message=log.error_message,
            duration_seconds=log.duration_seconds,
            records_inserted=log.records_inserted,
            records_updated=log.records_updated
        )
        for log in logs
    ]
