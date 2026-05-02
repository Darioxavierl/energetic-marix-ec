"""
Punto de entrada: aplicación FastAPI
"""

import uvicorn
from fastapi import FastAPI
from src.utils.logger import logger
from src.utils.config import API_HOST, API_PORT, API_RELOAD, APP_NAME, APP_VERSION
from src.database.db_session import init_db
from src.api.endpoints import router as api_router
from src.scheduler.cenace_scheduler import init_scheduler, start_scheduler, stop_scheduler

# Crear aplicación FastAPI
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Microservicio de scraping para CENACE",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Incluir routers
app.include_router(api_router)

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1"
    }

@app.on_event("startup")
async def startup_event():
    """Evento al iniciar la aplicación"""
    logger.info(f"✓ {APP_NAME} iniciado en {API_HOST}:{API_PORT}")
    # Inicializar base de datos
    init_db()
    # Inicializar y arrancar scheduler
    init_scheduler()
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Evento al cerrar la aplicación"""
    stop_scheduler()
    logger.info(f"✓ {APP_NAME} cerrado")

if __name__ == "__main__":
    logger.info(f"Iniciando {APP_NAME}...")
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level="info"
    )
