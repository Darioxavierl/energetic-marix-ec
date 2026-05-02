"""
Gestión de sesiones SQLAlchemy
"""

from sqlalchemy import create_engine, inspect, text
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
    _apply_sqlite_compat_migrations()
    logger.info("✓ Base de datos inicializada")


def _apply_sqlite_compat_migrations():
    """
    Aplica migraciones mínimas para mantener compatibilidad con BDs SQLite
    creadas antes de agregar nuevas columnas.
    """
    if "sqlite" not in DATABASE_URL:
        return

    inspector = inspect(engine)
    if "hourly_curves" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("hourly_curves")}
    if "minute" in columns:
        return

    logger.info("Aplicando migración SQLite: agregando columna hourly_curves.minute")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE hourly_curves ADD COLUMN minute INTEGER NOT NULL DEFAULT 0"))


def get_db() -> Session:
    """Genera sesión para dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
