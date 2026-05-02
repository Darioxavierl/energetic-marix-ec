"""
Scheduler para ejecutar scraper periódicamente con APScheduler
"""

import time
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.orm import Session
from src.utils.config import SCRAPER_INTERVAL_MINUTES
from src.utils.logger import logger
from src.scraper.cenace_scraper import CENACEScraperSync
from src.database.db_session import SessionLocal
from src.database.repositories import (
    ProductionRepository,
    PlantRepository,
    ScrapeLogRepository
)

# Instancia global del scheduler
scheduler = BackgroundScheduler()
scheduler.daemon = False  # Permitir que la app se cierre


def run_scraper():
    """
    Función que ejecuta el scraper y almacena resultados en BD
    """
    start_time = time.time()
    db = None
    
    try:
        db = SessionLocal()
        scraper = CENACEScraperSync()
        
        logger.info(f"🔄 Iniciando scraper (intervalo: {SCRAPER_INTERVAL_MINUTES} min)...")
        
        # Ejecutar scraper
        production_data = scraper.scrape_production_data()
        
        if not production_data:
            logger.warning("⚠️ El scraper no retornó datos")
            raise Exception("No data returned from scraper")
        
        # Guardar en BD
        prod_repo = ProductionRepository(db)
        timestamp = production_data.get('timestamp', datetime.now())
        
        snapshot = prod_repo.create({
            'timestamp': timestamp,
            'total_mwh': production_data.get('total_mwh', 0),
            'hydro_mwh': production_data.get('hydro_mwh', 0),
            'thermal_mwh': production_data.get('thermal_mwh', 0),
            'renewable_mwh': production_data.get('renewable_mwh', 0),
            'import_mwh': production_data.get('import_mwh', 0),
            'export_mwh': production_data.get('export_mwh', 0),
            'hydro_percentage': production_data.get('hydro_percentage', 0),
            'thermal_percentage': production_data.get('thermal_percentage', 0),
            'renewable_percentage': production_data.get('renewable_percentage', 0),
            'source': 'CENACE_SCADA',
            'is_validated': True
        })
        
        # Guardar plantas
        plants_data = production_data.get('plants', [])
        if plants_data:
            plant_repo = PlantRepository(db)
            plant_records = []
            for plant in plants_data:
                plant_records.append({
                    'timestamp': timestamp,
                    'plant_id': plant.get('id', 'UNKNOWN'),
                    'plant_name': plant.get('name', 'UNKNOWN'),
                    'plant_type': plant.get('type', 'OTHER'),
                    'mwh': plant.get('mwh', 0),
                    'percentage_of_total': plant.get('percentage_of_total', 0)
                })
            if plant_records:
                plant_repo.create_batch(plant_records)
        
        # Log exitoso
        duration = time.time() - start_time
        scrape_repo = ScrapeLogRepository(db)
        scrape_repo.log_success(
            duration=duration,
            inserted=1 + len(plants_data),
            updated=0
        )
        
        logger.info(
            f"✅ Scraper exitoso: {production_data.get('total_mwh', 0):.0f} MWh, "
            f"{duration:.2f}s, {1 + len(plants_data)} registros"
        )
        
    except Exception as e:
        logger.error(f"❌ Error en scraper: {str(e)}")
        
        # Log del error
        if db:
            try:
                duration = time.time() - start_time
                scrape_repo = ScrapeLogRepository(db)
                scrape_repo.log_error(e, duration=duration)
            except:
                pass
    
    finally:
        if db:
            db.close()


def init_scheduler():
    """
    Inicializa el scheduler y agrega jobs
    """
    try:
        # Agregar job de scraping
        scheduler.add_job(
            func=run_scraper,
            trigger=IntervalTrigger(minutes=SCRAPER_INTERVAL_MINUTES),
            id='cenace_scraper',
            name='CENACE Scraper',
            replace_existing=True,
            max_instances=1,  # Solo una instancia a la vez
            coalesce=True  # Si se saltó una ejecución, hacerla ahora
        )
        
        logger.info(f"✓ Scheduler configurado: job cada {SCRAPER_INTERVAL_MINUTES} minutos")
        
    except Exception as e:
        logger.error(f"Error inicializando scheduler: {e}")
        raise


def start_scheduler():
    """Inicia el scheduler"""
    if not scheduler.running:
        scheduler.start()
        logger.info("✓ Scheduler iniciado")


def stop_scheduler():
    """Detiene el scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✓ Scheduler detenido")
