# CENACE Scraper Microservice - Documentación Completa

> **Última actualización**: 2024 | **Versión**: 0.1.0 | **Estado**: Fase 5 Completada ✅

---

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Instalación y Configuración](#instalación-y-configuración)
5. [Estructura del Proyecto](#estructura-del-proyecto)
6. [API Endpoints](#api-endpoints)
7. [Base de Datos](#base-de-datos)
8. [Scheduler y Tareas Autom áticas](#scheduler-y-tareas-automáticas)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)
12. [Fases de Desarrollo](#fases-de-desarrollo)

---

## Descripción General

El **CENACE Scraper Microservice** es un servicio independiente que realiza web scraping de datos energéticos del portal de CENACE (Corporación Eléctrica Nacional del Ecuador).

### Características Principales

- 🔄 **Scraping Automático**: Extrae datos de producción energética cada 15 minutos
- 📊 **API REST**: Endpoints para consultar producción, demanda, y centrales
- 💾 **Almacenamiento**: Base de datos SQLite con histórico completo
- 📈 **Monitoreo**: Logs de ejecución y métricas de salud
- ⚡ **Async/Await**: Operaciones no-bloqueantes con FastAPI y aiohttp
- 🔐 **Validación**: Schemas Pydantic para entrada/salida de datos
- ✅ **Tested**: 28 tests unitarios cubriendo parser, limpieza y BD

### Objetivo

Proporcionar una fuente confiable de datos de energía en tiempo real sin estar integrado al sistema principal `energetic-marix-ec`, facilitando análisis, visualización y toma de decisiones energéticas.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  (main.py: Inicializa BD, Scheduler, Endpoints)             │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        │          │          │          │
    ┌───▼──┐  ┌───▼──┐  ┌───▼──┐  ┌───▼──┐
    │ API  │  │ SCHED│  │  DB  │  │LOG  │
    │/v1/* │  │ uler │  │ ORM  │  │ging │
    └──────┘  └──────┘  └──────┘  └─────┘
        │          │          │
   [GET endpoints] │    ┌─────▼─────┐
   - /production   │    │ SQLite    │
   - /plants       │    │ (cenace.db)
   - /demand       │    └───────────┘
   - /health       │
   - /logs         │
                   │
            ┌──────▼──────────┐
            │ CENACE Scraper  │
            │ (15 min interval)
            └─────────────────┘
                   │
            ┌──────▼──────────┐
            │ HTML Parser     │
            │ Data Cleaner    │
            │ Validator       │
            └─────────────────┘
                   │
         ┌─────────▼──────────┐
         │ CENACE Website    │
         │ (información.htm)  │
         └────────────────────┘
```

### Pipeline de Datos

```
[CENACE HTML] → [Parser] → [Cleaner] → [Validator] → [Repository] → [SQLite]
                   ↓           ↓          ↓
            Extract tables  Normalize  Validate     Store snapshots,
            using BS4       types,     ranges       plants, curves
                            round
```

---

## Stack Tecnológico

### Backend & Web Framework
- **FastAPI 0.104.1**: Framework web moderno, rápido y async
- **Uvicorn 0.24.0**: Servidor ASGI para FastAPI
- **Python 3.11+**: Runtime con soporte nativo async/await

### Web Scraping
- **BeautifulSoup4 4.12.2**: Parser HTML con múltiples estrategias de selección
- **aiohttp 3.9.1**: Cliente HTTP async para requests no-bloqueantes
- **requests 2.31.0**: Fallback para requests síncronos

### Base de Datos
- **SQLAlchemy 2.0.23**: ORM para mapeo objeto-relacional
- **SQLite 3**: Almacenamiento local (puede reemplazarse por PostgreSQL)

### Validación & Serialización
- **Pydantic 2.4.2**: Validación de datos con schemas automáticos
- **python-dateutil**: Manejo robusto de fechas

### Scheduling
- **APScheduler 3.10.4**: Job scheduler para tareas periódicas
- **asyncio**: Framework async nativo de Python

### Testing & Calidad
- **pytest 7.4.0**: Framework de testing
- **pytest-asyncio 0.21.0**: Soporte para tests async
- **pytest-cov 4.1.0**: Cobertura de código
- **flake8**: Linter
- **black**: Formateador automático
- **mypy**: Type checker

### Utilidades
- **python-dotenv 1.0.0**: Manejo de variables de entorno
- **bleach 6.0.0**: Sanitización de HTML (XSS prevention)
- **click**: CLI utilities

---

## Instalación y Configuración

### Requisitos Previos

- Python 3.11+
- pip (gestor de paquetes)
- Git
- ~500MB de espacio en disco (venv + dependencias)

### Paso 1: Clonar o Descargar el Proyecto

```bash
cd /home/david_montano/Escritorio/Regulacion/matriz_energetica/
ls -la  # Verificar estructura
```

### Paso 2: Crear Virtual Environment

```bash
cd cenace-scraper-service
python3 -m venv venv

# Activar venv
source venv/bin/activate  # En Linux/Mac
# o
venv\\Scripts\\activate  # En Windows
```

### Paso 3: Instalar Dependencias

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Verificar instalación:
```bash
pip list | grep -E "fastapi|sqlalchemy|beautifulsoup4|apscheduler"
```

### Paso 4: Configurar Variables de Entorno

```bash
# Crear .env desde el template
cp .env.example .env

# Editar .env con valores reales (opcional - usan defaults)
nano .env
```

**Archivo .env.example:**
```env
# Aplicación
DEBUG=False
LOG_LEVEL=INFO

# Base de Datos
DATABASE_URL=sqlite:///./cenace.db

# CENACE
CENACE_URL=https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm
CENACE_TIMEOUT=10

# Scheduler
SCRAPER_INTERVAL_MINUTES=15

# API
API_HOST=127.0.0.1
API_PORT=8001
API_RELOAD=True
```

### Paso 5: Inicializar Base de Datos

```bash
# Se inicializa automáticamente al arranca la app,
# pero puedes hacerlo manualmente:
python -c "from src.database.db_session import init_db; init_db()"
```

---

## Estructura del Proyecto

```
cenace-scraper-service/
├── main.py                          # Punto de entrada FastAPI
├── requirements.txt                 # Dependencias Python
├── .env.example                     # Template de variables
├── .gitignore                       # Exclusiones Git
├── cenace.db                        # BD SQLite (generada)
│
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints.py             # Rutas FastAPI
│   │   └── schemas.py               # Modelos Pydantic
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                # Modelos SQLAlchemy
│   │   ├── db_session.py            # Sesiones y engine
│   │   └── repositories.py          # Pattern repository
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── cenace_scraper.py        # Orquestador principal
│   │   ├── html_parser.py           # Parser con BS4
│   │   └── data_cleaner.py          # Limpieza y validación
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── cenace_scheduler.py      # APScheduler jobs
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py                # Variables configurables
│       └── logger.py                # Logging setup
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # pytest fixtures
│   ├── test_parser.py               # Tests HTML parser
│   ├── test_cleaner.py              # Tests data cleaner
│   └── test_database.py             # Tests BD y repositories
│
└── web/                             # (Legacy, no usado)
    ├── css/
    ├── html/
    └── js/
```

---

## API Endpoints

### Base URL
```
http://localhost:8001
```

### Documentación Interactiva
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Endpoints Disponibles

#### Production Endpoints

**GET** `/api/v1/production/latest`
- Producción más reciente
- Respuesta:
```json
{
  "timestamp": "2024-01-15T14:30:00",
  "total_mwh": 50234.5,
  "hydro_mwh": 25000.0,
  "thermal_mwh": 20000.0,
  "renewable_mwh": 5234.5,
  "hydro_percentage": 49.8,
  "thermal_percentage": 39.8,
  "renewable_percentage": 10.4,
  "import_mwh": 0,
  "export_mwh": 0,
  "source": "CENACE"
}
```

**GET** `/api/v1/production/history?days=7`
- Histórico de producción (últimos N días)
- Parámetros:
  - `days`: 1-90 (default: 7)
- Respuesta: Array de ProductionResponse

#### Plant Endpoints

**GET** `/api/v1/plants/latest`
- Generación actual por central
- Respuesta:
```json
[
  {
    "plant_id": "PAUTE001",
    "plant_name": "Paute Hidro",
    "plant_type": "HYDRO",
    "mwh": 1500,
    "percentage_of_total": 15.2,
    "status": "ONLINE"
  },
  ...
]
```

**GET** `/api/v1/plants/{plant_id}/history`
- Histórico de una central específica
- Ejemplo: `/api/v1/plants/PAUTE001/history`

#### Demand Endpoints

**GET** `/api/v1/demand/hourly?date=2024-01-15`
- Curva horaria de demanda
- Parámetros:
  - `date`: YYYY-MM-DD (default: últimas 24h)
- Respuesta:
```json
[
  {
    "date": "2024-01-15",
    "hour": 0,
    "demand_mw": 3850,
    "total_production_mw": 3900,
    "hydro_mw": 1950,
    "thermal_mw": 1600,
    "renewable_mw": 350,
    "balance_mw": 50,
    "reserve_margin": 1.3,
    "risk_level": "SAFE"
  },
  ...
]
```

#### Monitoring Endpoints

**GET** `/api/v1/health`
- Estado de salud del servicio
- Respuesta:
```json
{
  "status": "healthy",
  "last_scrape": "2024-01-15T14:30:05",
  "next_scrape": "2024-01-15T14:45:05",
  "records_stored": 2145,
  "success_rate": 98.5
}
```

**GET** `/api/v1/logs?limit=50`
- Logs de ejecución del scraper
- Parámetros:
  - `limit`: 1-500 (default: 50)

### Códigos de Respuesta HTTP

| Código | Significado |
|--------|------------|
| 200 | OK - Datos retornados exitosamente |
| 404 | No Found - Recurso no disponible |
| 400 | Bad Request - Parámetros inválidos |
| 500 | Server Error - Error interno del servidor |

---

## Base de Datos

### Modelos (Tables)

#### ProductionSnapshot
Capturas puntales de producción energética

```sql
CREATE TABLE production_snapshots (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME UNIQUE NOT NULL,
  total_mwh FLOAT NOT NULL,
  hydro_mwh FLOAT NOT NULL,
  thermal_mwh FLOAT NOT NULL,
  renewable_mwh FLOAT NOT NULL,
  import_mwh FLOAT DEFAULT 0,
  export_mwh FLOAT DEFAULT 0,
  hydro_percentage FLOAT DEFAULT 0,
  thermal_percentage FLOAT DEFAULT 0,
  renewable_percentage FLOAT DEFAULT 0,
  source VARCHAR(50) DEFAULT 'CENACE_SCADA',
  is_validated BOOLEAN DEFAULT 0,
  validation_errors VARCHAR(500),
  created_at DATETIME
);

CREATE INDEX idx_production_timestamp ON production_snapshots(timestamp);
```

#### PlantGeneration
Generación por central individual

```sql
CREATE TABLE plant_generations (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  plant_id VARCHAR(100) NOT NULL,
  plant_name VARCHAR(200) NOT NULL,
  plant_type VARCHAR(50),  -- HYDRO, THERMAL, RENEWABLE, OTHER
  mwh FLOAT,
  mw_current FLOAT,
  percentage_of_total FLOAT,
  status VARCHAR(20),  -- ONLINE, OFFLINE, MAINTENANCE
  created_at DATETIME
);

CREATE INDEX idx_plant_plant_id ON plant_generations(plant_id);
CREATE INDEX idx_plant_timestamp ON plant_generations(timestamp);
```

#### HourlyCurve
Curva horaria de demanda y generación

```sql
CREATE TABLE hourly_curves (
  id INTEGER PRIMARY KEY,
  date DATE NOT NULL,
  hour INTEGER NOT NULL,  -- 0-23
  demand_mw FLOAT,
  total_production_mw FLOAT,
  hydro_mw FLOAT,
  thermal_mw FLOAT,
  renewable_mw FLOAT,
  import_mw FLOAT,
  export_mw FLOAT,
  balance_mw FLOAT,  -- Generación - Demanda
  reserve_margin FLOAT,  -- % vs demanda
  risk_level VARCHAR(20),  -- SAFE, ALERT, CRITICAL
  created_at DATETIME
);

CREATE INDEX idx_hourly_date ON hourly_curves(date);
```

#### ScrapeLog
Log de ejecuciones del scraper

```sql
CREATE TABLE scrape_logs (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  success BOOLEAN NOT NULL,
  error_message VARCHAR(500),
  duration_seconds FLOAT,
  records_inserted INTEGER,
  records_updated INTEGER
);

CREATE INDEX idx_scrape_timestamp ON scrape_logs(timestamp);
```

### Consultas Útiles (SQLite)

```sql
-- Producción promedio diaria
SELECT DATE(timestamp) as fecha, AVG(total_mwh) as promedio
FROM production_snapshots
GROUP BY DATE(timestamp)
ORDER BY fecha DESC
LIMIT 30;

-- Plantas más generadas (últimas 24h)
SELECT plant_name, SUM(mwh) as total_mwh
FROM plant_generations
WHERE timestamp > datetime('now', '-1 day')
GROUP BY plant_name
ORDER BY total_mwh DESC
LIMIT 10;

-- Tasa de éxito del scraper (últimos 7 días)
SELECT 
  COUNT(*) as total_runs,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
  ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM scrape_logs
WHERE timestamp > datetime('now', '-7 days');
```

### Administración de BD

```bash
# Abrir BD en SQLite CLI
sqlite3 cenace.db

# Dentro de sqlite3:
.tables                    # Ver todas las tablas
.schema production_snapshots  # Ver estructura
SELECT COUNT(*) FROM production_snapshots;  # Contar registros
.quit                      # Salir

# Hacer backup
cp cenace.db cenace.db.backup

# Restaurar desde backup
cp cenace.db.backup cenace.db
```

---

## Scheduler y Tareas Automáticas

### Configuración

El scheduler se inicializa automáticamente cuando la app arranca.

**Archivo**: `src/scheduler/cenace_scheduler.py`

### Jobs Configurados

#### 1. CENACE Scraper
- **ID**: `cenace_scraper`
- **Función**: `run_scraper()`
- **Intervalo**: Configurable (default: 15 minutos)
- **Comportamiento**:
  - Ejecuta el scraper
  - Parsea HTML y limpia datos
  - Almacena en BD
  - Registra éxito/error

### Monitoreo

```bash
# Ver próximo scheduled job (verificar salida de logs)
tail -f cenace_scraper.log  # Si está configurado

# Ver logs en BD
curl http://localhost:8001/api/v1/logs

# Endpoint de salud
curl http://localhost:8001/api/v1/health
```

### Customización

Para cambiar el intervalo de scraping:

**Opción 1**: Variable de entorno
```bash
export SCRAPER_INTERVAL_MINUTES=30
```

**Opción 2**: En .env
```
SCRAPER_INTERVAL_MINUTES=30
```

**Opción 3**: Código (src/scheduler/cenace_scheduler.py)
```python
scheduler.add_job(
    ...
    trigger=IntervalTrigger(minutes=30),  # Cambiar aquí
    ...
)
```

---

## Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest tests/ -v

# Solo parser
pytest tests/test_parser.py -v

# Solo cleaner
pytest tests/test_cleaner.py -v

# Solo BD
pytest tests/test_database.py -v

# Con cobertura
pytest tests/ --cov=src --cov-report=html

# Output: htmlcov/index.html
```

### Estadísticas de Tests

```
tests/test_parser.py        8 tests ✅
tests/test_cleaner.py      11 tests ✅
tests/test_database.py      8 tests ✅
─────────────────────────────────────
TOTAL                      28 tests ✅ (100% pass rate)
```

### Cobertura de Código

Áreas cubiertas:
- ✅ HTML Parser (extracción, tipo de plantas, validación)
- ✅ Data Cleaner (limpieza, validación de rangos, outliers)
- ✅ Database (CRUD, queries, logging)
- ✅ Schemas (Pydantic validation)

Áreas pendientes para Phase 6:
- [ ] API Endpoints (tests de integración)
- [ ] Scheduler (tests de jobs)
- [ ] Error handling (edge cases)

---

## Deployment

### Desarrollo Local

```bash
source venv/bin/activate
python main.py

# O con uvicorn directo
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Acceso:
- API: `http://localhost:8001`
- Swagger Docs: `http://localhost:8001/docs`

### Producción

#### Recomendaciones

1. **Usar Gunicorn + Uvicorn Workers**:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 main:app
```

2. **Variables de Entorno**:
```bash
export DEBUG=False
export API_RELOAD=False
export LOG_LEVEL=INFO
```

3. **Base de Datos**:
   - Cambiar de SQLite a PostgreSQL:
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/cenace_db
   ```
   - Ejecutar migraciones

4. **Reverse Proxy** (Nginx):
```nginx
server {
    listen 80;
    server_name cenace-api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

5. **Logging Centralizado**:
   - Configurar ELK Stack o CloudWatch
   - Integrar monitoreo (Prometheus, Grafana)

6. **Docker** (opcional):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "main:app"]
```

---

## Troubleshooting

### Problema: ImportError en src.database.models

**Error**:
```
ImportError: cannot import name 'config' from 'src.utils.config'
```

**Solución**:
- Cambiar `from src.utils.config import config` a `from src.utils.config import DATABASE_URL, DEBUG`

### Problema: Tests no encuentra fixtures

**Error**:
```
fixture 'db' not found
```

**Solución**:
- Verificar que `tests/conftest.py` existe
- Ejecutar desde raíz del proyecto: `pytest tests/`

### Problema: Scraper sin datos

**Error**:
```
"⚠️ El scraper no retornó datos"
```

**Causas & Soluciones**:
1. Sitio web CENACE no disponible → Usar VPN, esperar
2. Formato HTML cambió → Actualizar selectores en `html_parser.py`
3. Timeout → Aumentar `CENACE_TIMEOUT` en .env

### Problema: BD corrupta

**Error**:
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solución**:
```bash
# Eliminar BD corrupta
rm cenace.db

# Reiniciar app (se crea nueva BD vacía)
python main.py
```

### Problema: Port Already in Use

**Error**:
```
OSError: [Errno 48] Address already in use
```

**Solución**:
```bash
# Encontrar proceso usando puerto 8001
lsof -i :8001

# Matar proceso
kill -9 <PID>

# O usar otro puerto
export API_PORT=8002
```

---

## Fases de Desarrollo

### ✅ Phase 1: Setup (Completada)
- [x] Estructura de carpetas
- [x] Virtual environment
- [x] Dependencias instaladas
- [x] Configuración centralizada
- [x] Logging setup

### ✅ Phase 2: Core Scraper (Completada)
- [x] HTML Parser (BeautifulSoup4)
- [x] Data Cleaner
- [x] CENACEScraper (async + sync)
- [x] Tests: 8 parser + 11 cleaner = 19 tests ✅

### ✅ Phase 3: Database (Completada)
- [x] SQLAlchemy Models (4 tables)
- [x] Repository Pattern (4 repositories)
- [x] DB Sessions & engine
- [x] Tests: 8 database tests ✅

### ✅ Phase 4: API Endpoints (Completada)
- [x] FastAPI routers
- [x] Pydantic schemas
- [x] 6 endpoint groups (production, plants, demand, health, logs)
- [x] Swagger/ReDoc docs

### ✅ Phase 5: Scheduler (Completada)
- [x] APScheduler integration
- [x] Periodic scraping job (15 min)
- [x] Error logging
- [x] Automatic startup/shutdown

### ⏳ Phase 6: Testing & Validation (Próxima)
- [ ] Integration tests (end-to-end scraper→BD)
- [ ] Load testing
- [ ] Coverage >80%
- [ ] Mock CENACE HTML responses

### ⏳ Phase 7: Documentation (Próxima)
- [ ] OpenAPI schema generation
- [ ] User guide
- [ ] Admin guide
- [ ] API reference

### ⏳ Phase 8: Deployment & Monitoring (Próxima)
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Monitoring (Prometheus metrics)
- [ ] Health checks
- [ ] Alerting

---

## Notas Finales

### Limitaciones Conocidas

1. **CENACE sin API oficial**: Dependencia del scraping HTML (frágil ante cambios de diseño)
2. **SQLite**: No óptimo para concurrencia alta; usar PostgreSQL en producción
3. **Datos públicos**: Pueden tener delays o estar desactualizados
4. **Rate limiting**: CENACE puede bloquear scraping agresivo

### Mejoras Futuras

1. Implementar cambio automático de selectores (ML detection)
2. Caché en Redis para reducir scraping
3. Alertas en tiempo real para anomalías
4. Dashboard web de visualización
5. Exportar datos a formatos (CSV, Parquet)
6. Integración con sistemas de alertas (Slack, Discord)

### Contacto & Soporte

Para problemas o sugerencias:
1. Revisar logs: `tail -f /path/to/logs`
2. Ejecutar tests: `pytest tests/ -v`
3. Consultar documentación de dependencias
4. Abrir issue en repositorio

---

**Documento generado automáticamente por CENACE Scraper v0.1.0**
