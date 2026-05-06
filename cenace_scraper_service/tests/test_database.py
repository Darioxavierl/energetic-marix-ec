"""
Tests para modelos de BD y repositories
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.models import Base, ProductionSnapshot, PlantGeneration, HourlyCurve, ScrapeLog
from src.database.repositories import (
    ProductionRepository,
    DemandRepository,
    PlantRepository,
    HourlyCurveRepository,
    ScrapeLogRepository,
)


@pytest.fixture
def db():
    """Base de datos en memoria para tests"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestProductionRepository:
    """Tests para ProductionRepository"""
    
    def test_create(self, db):
        """Crea snapshot de producción"""
        repo = ProductionRepository(db)
        data = {
            'timestamp': datetime.now(),
            'total_mwh': 50000,
            'hydro_mwh': 25000,
            'thermal_mwh': 20000,
            'renewable_mwh': 5000,
            'hydro_percentage': 50,
            'thermal_percentage': 40,
            'renewable_percentage': 10
        }
        
        snapshot = repo.create(data)
        assert snapshot.id is not None
        assert snapshot.total_mwh == 50000
    
    def test_get_latest(self, db):
        """Obtiene snapshot más reciente"""
        repo = ProductionRepository(db)
        
        for i in range(3):
            data = {
                'timestamp': datetime.now() + timedelta(minutes=i),
                'total_mwh': 50000 + i * 100,
                'hydro_mwh': 25000,
                'thermal_mwh': 20000,
                'renewable_mwh': 5000,
                'hydro_percentage': 50,
                'thermal_percentage': 40,
                'renewable_percentage': 10
            }
            repo.create(data)
        
        latest = repo.get_latest()
        assert latest.total_mwh == 50200  # Último insertado
    
    def test_get_by_date_range(self, db):
        """Obtiene snapshots por rango de fechas"""
        repo = ProductionRepository(db)
        
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(5):
            data = {
                'timestamp': base_time + timedelta(hours=i),
                'total_mwh': 50000,
                'hydro_mwh': 25000,
                'thermal_mwh': 20000,
                'renewable_mwh': 5000,
                'hydro_percentage': 50,
                'thermal_percentage': 40,
                'renewable_percentage': 10
            }
            repo.create(data)
        
        start = base_time + timedelta(hours=1)
        end = base_time + timedelta(hours=3)
        results = repo.get_by_date_range(start, end)
        
        assert len(results) == 3


class TestPlantRepository:
    """Tests para PlantRepository"""
    
    def test_create_batch(self, db):
        """Crea múltiples registros de plantas"""
        repo = PlantRepository(db)
        
        data_list = [
            {
                'timestamp': datetime.now(),
                'plant_id': 'PAUTE001',
                'plant_name': 'Paute Hidro',
                'plant_type': 'HYDRO',
                'mwh': 150,
                'mw_current': 150,
                'percentage_of_total': 25
            },
            {
                'timestamp': datetime.now(),
                'plant_id': 'TERMO001',
                'plant_name': 'Termo Guayaquil',
                'plant_type': 'THERMAL',
                'mwh': 100,
                'mw_current': 100,
                'percentage_of_total': 15
            }
        ]
        
        count = repo.create_batch(data_list)
        assert count == 2


class TestDemandRepository:
    """Tests para DemandRepository"""

    def test_create_and_get_latest(self, db):
        repo = DemandRepository(db)

        repo.create(
            {
                "timestamp": datetime.now(),
                "demand_total_mw": 4200.0,
                "demand_cnel_mw": 2900.0,
                "demand_empresas_mw": 1300.0,
            }
        )
        repo.create(
            {
                "timestamp": datetime.now() + timedelta(minutes=1),
                "demand_total_mw": 4250.0,
                "demand_cnel_mw": 2920.0,
                "demand_empresas_mw": 1330.0,
            }
        )

        latest = repo.get_latest()
        assert latest is not None
        assert latest.demand_total_mw == 4250.0


class TestHourlyCurveRepository:
    """Tests para HourlyCurveRepository"""
    
    def test_create_batch(self, db):
        """Crea curvas horarias"""
        repo = HourlyCurveRepository(db)
        
        data_list = []
        for hour in range(24):
            data_list.append({
                'date': datetime.now().date(),
                'hour': hour,
                'minute': 0,
                'demand_mw': 4000 + hour * 50,
                'total_production_mw': 4100 + hour * 40,
                'hydro_mw': 2000,
                'thermal_mw': 1500,
                'renewable_mw': 600,
                'balance_mw': 100,
                'reserve_margin': 2.5
            })
        
        count = repo.create_batch(data_list)
        assert count == 24


class TestScrapeLogRepository:
    """Tests para ScrapeLogRepository"""
    
    def test_log_success(self, db):
        """Registra ejecución exitosa"""
        repo = ScrapeLogRepository(db)
        
        repo.log_success(duration=12.5, inserted=100, updated=50)
        
        logs = repo.get_last_n_logs(1)
        assert len(logs) == 1
        assert logs[0].success == True
        assert logs[0].duration_seconds == 12.5
    
    def test_log_error(self, db):
        """Registra error de ejecución"""
        repo = ScrapeLogRepository(db)
        
        error = Exception("Test error")
        repo.log_error(error, duration=5.0)
        
        logs = repo.get_last_n_logs(1)
        assert len(logs) == 1
        assert logs[0].success == False
        assert "Test error" in logs[0].error_message
    
    def test_success_rate(self, db):
        """Calcula tasa de éxito"""
        repo = ScrapeLogRepository(db)
        
        # 3 exitosos, 1 fallido
        for _ in range(3):
            repo.log_success(duration=10, inserted=50, updated=0)
        
        repo.log_error(Exception("Error"), duration=5)
        
        success_rate = repo.get_success_rate(days=1)
        assert success_rate == 75.0  # 3/4 * 100
