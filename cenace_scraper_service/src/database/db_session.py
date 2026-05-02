"""
Gestión de sesiones SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from src.utils.config import DATABASE_URL, DEBUG
from src.database.models import Base
from src.utils.logger import logger

# Crear engine con pool_pre_ping para detectar conexiones muertas
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    pool_pre_ping=True,
    echo=DEBUG
)

# Session factory
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    """Crea todas las tablas"""
    logger.info(f"Inicializando base de datos: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Base de datos inicializada")


def get_db() -> Session:
    """Genera sesión para dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
