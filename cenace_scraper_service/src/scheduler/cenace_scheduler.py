import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from src.utils.config import SCRAPER_INTERVAL_MINUTES
from src.utils.logger import logger
from src.scraper.cenace_scraper import CENACEScraperSync
from src.database.db_session import SessionLocal
from src.database.repositories import (
    ProductionRepository,
    PlantRepository,
    HourlyCurveRepository,
    ScrapeLogRepository
)

# Instancia global del scheduler
scheduler = BackgroundScheduler()

def run_scraper():
    """
    Función que ejecuta el scraper y almacena resultados en BD
    """
    start_time = time.time()
    db = None
    try:
        db = SessionLocal()
        scraper = CENACEScraperSync()
        
        logger.info(f"Iniciando ciclo de scraping programado...")
        production_data = scraper.scrape_production_data()

        if not production_data:
            raise Exception("El scraper no obtuvo información válida de CENACE")

        # 1. Guardar Snapshot de Producción
        prod_repo = ProductionRepository(db)
        timestamp = production_data.get('timestamp', datetime.now())
        prod_repo.create({
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

        # 2. Guardar Detalle de Plantas
        plants_data = production_data.get('plants', [])
        if plants_data:
            plant_repo = PlantRepository(db)
            plant_records = []
            for p in plants_data:
                plant_records.append({
                    'timestamp': timestamp,
                    'plant_id': p.get('plant_id', p.get('plant_name', 'UNKNOWN')),
                    'plant_name': p.get('plant_name', 'UNKNOWN'),
                    'plant_type': p.get('plant_type', 'OTHER'),
                    'mwh': p.get('mwh', 0),
                    'percentage_of_total': p.get('percentage', 0)
                })
            plant_repo.create_batch(plant_records)

        # 3. Guardar Curva Horaria
        hourly_data = production_data.get('hourly_curve', [])
        if hourly_data:
            hourly_repo = HourlyCurveRepository(db)
            hourly_records = []
            for curve in hourly_data:
                hourly_records.append({
                    'date': curve.get('date'),
                    'hour': curve.get('hour', 0),
                    'minute': curve.get('minute', 0),
                    'demand_mw': curve.get('demand_mw', 0),
                    'total_production_mw': curve.get('total_production_mw', 0),
                    'hydro_mw': curve.get('hydro_mw', 0),
                    'thermal_mw': curve.get('thermal_mw', 0),
                    'renewable_mw': curve.get('renewable_mw', 0),
                    'import_mw': curve.get('import_mw', 0),
                    'export_mw': curve.get('export_mw', 0),
                    'balance_mw': curve.get('total_production_mw', 0) - curve.get('demand_mw', 0),
                })
            hourly_repo.create_batch(hourly_records)

        # Registrar éxito en logs
        duration = time.time() - start_time
        ScrapeLogRepository(db).log_success(
            duration=duration, 
            inserted=1 + len(plants_data) + len(hourly_data), 
            updated=0
        )
        logger.info(f"✓ Scraping y guardado completado en {duration:.2f}s")

    except Exception as e:
        logger.error(f"❌ Error en run_scraper: {e}")
        if db:
            try:
                ScrapeLogRepository(db).log_error(e, time.time() - start_time)
            except:
                pass
    finally:
        if db: 
            db.close()

# === FUNCIONES DE CONTROL REQUERIDAS POR MAIN.PY ===

def init_scheduler():
    """
    Configura el job de scraping
    """
    try:
        scheduler.add_job(
    func=run_scraper,
    trigger=IntervalTrigger(minutes=SCRAPER_INTERVAL_MINUTES),
    id='cenace_scraper_job',
    name='CENACE Real Time Scraper',
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    next_run_time=datetime.now() # <--- AGREGA ESTO PARA QUE CORRA AL INICIAR
)
        logger.info(f"Scheduler configurado para ejecutarse cada {SCRAPER_INTERVAL_MINUTES} min.")
    except Exception as e:
        logger.error(f"Error inicializando scheduler: {e}")

def start_scheduler():
    """Arranca el scheduler si no está corriendo"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler iniciado correctamente.")

def stop_scheduler():
    """Detiene el scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler detenido.")