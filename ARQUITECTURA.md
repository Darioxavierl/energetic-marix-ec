# Arquitectura del Simulador de Matriz Energética del Ecuador

**Versión:** 1.0  
**Fecha:** 2026-04-27  
**Responsable:** Arquitectura Senior - Python / PyQt6 / GIS  
**Estado:** Documento de Diseño

---

## Índice

1. [Visión General](#visión-general)
2. [Arquitectura de Alto Nivel](#arquitectura-de-alto-nivel)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Componentes Principales](#componentes-principales)
5. [Tecnologías Recomendadas](#tecnologías-recomendadas)
6. [Plan de Implementación](#plan-de-implementación)
7. [Decisiones Arquitectónicas Críticas](#decisiones-arquitectónicas-críticas)
8. [Análisis de Riesgos](#análisis-de-riesgos)
9. [Estrategia de Escalabilidad](#estrategia-de-escalabilidad)
10. [Metrificación y Monitoreo](#metrificación-y-monitoreo)

---

## Visión General

### Objetivo
Desarrollar un simulador visual e interactivo de la matriz energética ecuatoriana que permita:
- Visualizar en tiempo real (o simulado) el estado del sistema eléctrico nacional
- Modelar escenarios hipotéticos (contingencias, crecimiento de demanda, sequías)
- Calcular indicadores de estabilidad y riesgo de desabastecimiento
- Analizar dependencia de fuentes (hidroeléctrica, térmica, renovables)

### Ámbito de Aplicación
- Análisis académico
- Planificación energética
- Investigación de políticas públicas
- Capacitación a operadores de red
- Herramienta de decisión para CENACE/CELEC

### Horizonte Técnico
- Fase 1: MVP funcional (6-8 semanas)
- Fase 2-5: Maduración progresiva hacia solución tipo SCADA-lite (6-12 meses)

---

## Arquitectura de Alto Nivel

### Diagrama Conceptual

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA PRESENTACIÓN (PyQt6)                │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│ │   UI Principal   │  │  Mapa OSM Web    │  │ Dashboard  │  │
│ │  (Main Window)   │  │  (QWebEngineView)│  │ (Métricas) │  │
│ └──────────────────┘  └──────────────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    CAPA APLICACIÓN                          │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Controllers  │  │   Services   │  │ Event Bus        │   │
│ │  (Lógica UI) │  │  (Orquesta)  │  │ (Comunicación)   │   │
│ └──────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA LÓGICA DE NEGOCIOS                  │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────┐   │
│ │           MOTOR DE SIMULACIÓN                         │   │
│ │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│ │  │   Generación │  │   Demanda    │  │ Calc.      │  │   │
│ │  │   (Modelos)  │  │   (Modelos)  │  │ Balance    │  │   │
│ │  └──────────────┘  └──────────────┘  └────────────┘  │   │
│ │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│ │  │ Reglas Red   │  │  Eventos/    │  │Indicadores│  │   │
│ │  │ (Física el)  │  │  Fallas      │  │ de Riesgo │  │   │
│ │  └──────────────┘  └──────────────┘  └────────────┘  │   │
│ └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              CAPA GIS Y GEOESPACIAL                         │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│ │ Gestión Capas    │  │ OSM Rendering    │  │ Proyec.    │ │
│ │ (WMS, Tile)      │  │ (Leaflet.js)     │  │ (UTM Z17S) │ │
│ └──────────────────┘  └──────────────────┘  └────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                CAPA DATOS Y PERSISTENCIA                    │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ BD Local     │  │   Cache      │  │ Archivos Config  │   │
│ │ (SQLite3)    │  │  (Redis opt) │  │ (JSON/YAML)      │   │
│ └──────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│          CAPA CONECTIVIDAD E INTEGRACIÓN                   │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ CENACE API   │  │ CELEC EP API │  │ Servicios Web    │   │
│ │ (REST)       │  │ (REST/Datos) │  │ Externos         │   │
│ └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Patrones Arquitectónicos

**Patrón Principal:** Clean Architecture + MVVM (Model-View-ViewModel)

- **Separación clara** entre UI, lógica y datos
- **Dependencias unidireccionales** hacia el core de negocio
- **Testabilidad** de cada capa independientemente
- **Escalabilidad** mediante inyección de dependencias

**Justificación:**
- PyQt6 es complejo; MVVM reduce acoplamiento
- GIS requiere manejo asincrónico; arquitectura reactiva
- Simulación física necesita lógica aislada y testeable

---

## Estructura del Proyecto

```
energetico/
│
├── 📁 src/                              # Código fuente principal
│   ├── 📁 ui/                          # Interfaz de usuario PyQt6
│   │   ├── __init__.py
│   │   ├── main_window.py              # Ventana principal
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── map_widget.py           # QWebEngineView integrado
│   │   │   ├── control_panel.py        # Panel lateral de controles
│   │   │   ├── metrics_panel.py        # Panel de métricas
│   │   │   ├── alerts_panel.py         # Panel de alertas
│   │   │   └── scenario_editor.py      # Editor de escenarios
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── about_dialog.py
│   │   │   ├── settings_dialog.py
│   │   │   └── export_dialog.py
│   │   ├── styles/
│   │   │   ├── __init__.py
│   │   │   ├── dark_theme.qss
│   │   │   ├── light_theme.qss
│   │   │   └── variables.qss
│   │   └── resources.qrc               # Recursos (íconos, imágenes)
│   │
│   ├── 📁 application/                 # Capa aplicación (Controllers)
│   │   ├── __init__.py
│   │   ├── app_controller.py           # Controlador principal
│   │   ├── map_controller.py           # Lógica del mapa
│   │   ├── simulation_controller.py    # Orquesta simulación
│   │   └── scenario_manager.py         # Gestión de escenarios
│   │
│   ├── 📁 domain/                      # Capa de negocio (Lógica pura)
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── power_plant.py          # Modelo Central Eléctrica
│   │   │   ├── power_grid.py           # Modelo Red Eléctrica
│   │   │   ├── demand.py               # Modelo Demanda
│   │   │   ├── transmission_line.py    # Modelo Línea Transmisión
│   │   │   ├── substation.py           # Modelo Subestación
│   │   │   └── scenario.py             # Modelo Escenario
│   │   │
│   │   ├── simulation/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py               # Motor principal simulación
│   │   │   ├── generation_model.py     # Cálculos generación
│   │   │   ├── demand_model.py         # Cálculos demanda
│   │   │   ├── balance_calculator.py   # Balancing energético
│   │   │   ├── risk_assessor.py        # Evaluador de riesgos
│   │   │   └── events_simulator.py     # Simulador de eventos
│   │   │
│   │   ├── rules/
│   │   │   ├── __init__.py
│   │   │   ├── grid_rules.py           # Reglas operacionales
│   │   │   ├── constraints.py          # Restricciones técnicas
│   │   │   └── stability_rules.py      # Reglas de estabilidad
│   │   │
│   │   └── exceptions/
│   │       ├── __init__.py
│   │       └── domain_exceptions.py    # Excepciones de dominio
│   │
│   ├── 📁 infrastructure/              # Capa infraestructura
│   │   ├── __init__.py
│   │   ├── 📁 data/                    # Acceso a datos
│   │   │   ├── __init__.py
│   │   │   ├── repository.py           # Patrón Repository abstracto
│   │   │   ├── sqlite_repository.py    # Implementación SQLite
│   │   │   ├── json_loader.py          # Cargador JSON
│   │   │   ├── csv_importer.py         # Importador CSV
│   │   │   └── migrations.py           # Migraciones BD
│   │   │
│   │   ├── 📁 gis/                     # Componentes geoespaciales
│   │   │   ├── __init__.py
│   │   │   ├── geo_manager.py          # Gestor coordinadas WGS84/UTM
│   │   │   ├── leaflet_bridge.py       # Bridge PyQt6 ↔ Leaflet
│   │   │   ├── layer_manager.py        # Gestor de capas OSM
│   │   │   └── utils.py                # Utilidades GIS
│   │   │
│   │   ├── 📁 api/                     # Integración con APIs externas
│   │   │   ├── __init__.py
│   │   │   ├── cenace_client.py        # Cliente CENACE
│   │   │   ├── celec_client.py         # Cliente CELEC EP
│   │   │   ├── http_client.py          # HTTP genérico
│   │   │   └── cache_manager.py        # Caché de API
│   │   │
│   │   ├── 📁 events/                  # Bus de eventos
│   │   │   ├── __init__.py
│   │   │   ├── event_bus.py            # Event bus principal
│   │   │   ├── event_types.py          # Tipos de eventos definidos
│   │   │   └── handlers.py             # Manejadores de eventos
│   │   │
│   │   └── 📁 logging/                 # Logging centralizado
│   │       ├── __init__.py
│   │       ├── logger.py               # Configuración logging
│   │       └── formatters.py           # Formatos personalizados
│   │
│   ├── 📁 shared/                      # Código compartido
│   │   ├── __init__.py
│   │   ├── decorators.py               # Decoradores útiles
│   │   ├── constants.py                # Constantes globales
│   │   ├── types.py                    # Type hints compartidos
│   │   └── utils.py                    # Funciones utilidad
│   │
│   └── main.py                         # Punto de entrada
│
├── 📁 config/                          # Configuración
│   ├── __init__.py
│   ├── settings.py                     # Configuración principal
│   ├── defaults.yaml                   # Valores por defecto
│   ├── logging_config.json             # Configuración logging
│   └── environment.example              # Plantilla variables ambiente
│
├── 📁 data/                            # Datos y recursos
│   ├── 📁 centrales/                   # Datos centrales eléctricas
│   │   ├── centrales_ecuador.json      # Catálogo principal
│   │   ├── centrales_hidro.json
│   │   ├── centrales_termicas.json
│   │   ├── centrales_renovables.json
│   │   └── demanda_historica.csv
│   ├── 📁 maps/                        # Recursos GIS
│   │   ├── ecuador_boundary.geojson
│   │   └── transmission_network.geojson
│   └── 📁 fixtures/                    # Datos de prueba
│       └── mock_scenario.json
│
├── 📁 tests/                           # Suite de testing
│   ├── __init__.py
│   ├── pytest.ini
│   ├── conftest.py                     # Configuración pytest
│   ├── 📁 unit/
│   │   ├── test_power_plant.py
│   │   ├── test_balance_calculator.py
│   │   ├── test_risk_assessor.py
│   │   └── test_generation_model.py
│   ├── 📁 integration/
│   │   ├── test_simulation_engine.py
│   │   ├── test_repository.py
│   │   └── test_leaflet_bridge.py
│   └── 📁 e2e/
│       ├── test_scenario_workflow.py
│       └── test_ui_interactions.py
│
├── 📁 docs/                            # Documentación
│   ├── ARQUITECTURA.md                 # Este archivo
│   ├── API.md                          # Especificación API interna
│   ├── GIS_GUIDE.md                    # Guía GIS/Proyecciones
│   ├── SIMULATOR_GUIDE.md              # Guía motor simulación
│   ├── DEVELOPMENT.md                  # Guía desarrollo
│   └── 📁 diagrams/                    # Diagramas (PlantUML, etc)
│       ├── architecture.puml
│       ├── data_model.puml
│       └── sequence_diagrams.puml
│
├── 📁 scripts/                         # Scripts utilidad
│   ├── init_db.py                      # Inicializar BD
│   ├── import_data.py                  # Importar datos centrales
│   ├── generate_report.py              # Generar reportes
│   └── deploy.py                       # Script despliegue
│
├── 📁 web/                             # Recursos web (Leaflet, etc)
│   ├── 📁 js/
│   │   ├── map_handler.js              # Controlador Leaflet
│   │   ├── markers.js                  # Gestión marcadores
│   │   └── layers.js                   # Gestión capas
│   ├── 📁 css/
│   │   └── map_styles.css
│   ├── 📁 html/
│   │   └── map_container.html          # HTML contenedor mapa
│   └── lib/                            # Librerías JS (Leaflet, etc)
│
├── .env.example                        # Plantilla variables ambiente
├── .gitignore
├── requirements.txt                    # Dependencias Python
├── requirements-dev.txt                # Dependencias desarrollo
├── pyproject.toml                      # Configuración proyecto
├── setup.py                            # Setup para distribución
├── Makefile                            # Comandos frecuentes
├── README.md                           # README del proyecto
└── VERSION                             # Versión del proyecto

```

---

## Componentes Principales

### 1. Módulo UI (Presentación)

#### `main_window.py`
```python
# Responsabilidades:
# - Crear ventana principal PyQt6
# - Establecer layout general (panel lateral, mapa, métricas)
# - Conectar controles con controladores
# - Iniciar aplicación
```

**Estructura visual propuesta:**
```
┌─ Menú (Archivo, Simulación, Ver, Ayuda) ─────────────────┐
├─ Toolbar (Reproducir, Pausa, Reset, Exportar) ───────────┤
├──────────────────────────────────────────────────────────┤
│ │ Panel         │                                        │
│ │ Lateral       │        MAPA OPENSTREETMAP             │
│ │ (Controles)   │      (QWebEngineView)                 │
│ │               │                                        │
│ │ • Escenarios  │                                        │
│ │ • Generación  │                                        │
│ │ • Demanda     │                                        │
│ │ • Eventos     │                                        │
│ │               │                                        │
├──────────────────────────────────────────────────────────┤
│ Panel de Métricas (Inferior)                             │
│ • Balance actual                                         │
│ • Reserva operativa                                      │
│ • Indicador de riesgo                                    │
│ • Eventos recientes                                      │
└──────────────────────────────────────────────────────────┘
```

#### `map_widget.py`
```python
# Integración QWebEngineView + Leaflet.js
# Responsabilidades:
# - Cargar mapa OSM en iframe Leaflet
# - QWebChannel para comunicación bidireccional PyQt ↔ JS
# - Renderizar marcadores de centrales
# - Manejar eventos del usuario (click, zoom)
# - Dibujar capas geográficas
```

**Tecnología:** 
- QWebEngineView (PyQt6) + Leaflet.js (JavaScript)
- QWebChannel para API bridge
- JSON como formato intercambio datos

#### `control_panel.py`
```python
# Panel lateral con controles de simulación
# Widgets:
# - ComboBox seleccionar escenario
# - Slider incremento demanda (%)
# - Checkbox centrales a apagar
# - Button reproducir/pausa simulación
# - Tabla de centrales (nombre, potencia, estado)
```

### 2. Módulo Application (Controladores)

#### `app_controller.py`
```python
# Orquestador principal
# Responsabilidades:
# - Inicializar controladores especializados
# - Coordinar flujos entre UI y lógica
# - Manejar estado global
# - Gestionar ciclo de vida de la aplicación
```

#### `map_controller.py`
```python
# Lógica específica del mapa
# Responsabilidades:
# - Traducir clicks del mapa a eventos de aplicación
# - Actualizar visualización de centrales
# - Manejar zoom/paneo
# - Codificar/decodificar posiciones UTM/WGS84
```

#### `simulation_controller.py`
```python
# Orquesta el motor de simulación
# Responsabilidades:
# - Disparar cálculos del motor
# - Actualizar UI con resultados
# - Manejar pausa/reanudación
# - Recolectar métricas
```

### 3. Módulo Domain (Lógica de Negocio)

#### `models/power_plant.py`
```python
@dataclass
class PowerPlant:
    """Modelo de Central Eléctrica"""
    id: str                          # ID único
    name: str                         # Nombre central
    plant_type: PlantType             # Tipo (HYDRO, THERMAL, WIND, SOLAR)
    latitude: float                   # Coordenada geográfica
    longitude: float
    installed_capacity_mw: float      # Capacidad instalada (MW)
    available_capacity_mw: float      # Disponible ahora
    operational_status: OperationalStatus
    fuel_type: Optional[FuelType]     # Tipo combustible (gas, carbón, etc)
    efficiency: float                 # Eficiencia (0-1)
    region: str                       # Región Ecuador
    operator: str                     # Operador (CELEC, privado, etc)
    metadata: Dict                    # Datos adicionales
    
    def get_output_mw(self) -> float:
        """Calcula potencia real según disponibilidad y estado"""
        
    def simulate_failure(self) -> "PowerPlant":
        """Simula falla de la central"""
        
    def reduce_capacity(self, percentage: float) -> "PowerPlant":
        """Reduce capacidad por sequía, mantenimiento, etc"""
```

#### `models/power_grid.py`
```python
class PowerGrid:
    """Modelo de la red eléctrica nacional"""
    
    plants: List[PowerPlant]          # Todas las centrales
    substations: List[Substation]
    transmission_lines: List[TransmissionLine]
    demand: Demand                    # Demanda actual
    
    def get_total_capacity_mw(self) -> float:
        """Capacidad total instalada"""
        
    def get_total_available_mw(self) -> float:
        """Capacidad disponible después de contingencias"""
        
    def get_plants_by_type(self, plant_type: PlantType) -> List[PowerPlant]:
        """Filtra centrales por tipo"""
        
    def get_plants_by_region(self, region: str) -> List[PowerPlant]:
        """Filtra centrales por región"""
```

#### `simulation/engine.py`
```python
class SimulationEngine:
    """Motor principal de simulación"""
    
    def __init__(self, grid: PowerGrid, config: SimConfig):
        self.grid = grid
        self.config = config
        self.timestep = 0
        self.history = []
        
    def step(self, delta_time_minutes: int = 15) -> SimulationResult:
        """
        Avanza simulación un paso de tiempo
        
        1. Actualizar demanda según parámetros
        2. Calcular generación disponible
        3. Ejecutar eventos programados
        4. Balancear red
        5. Evaluar riesgos
        6. Retornar resultado
        """
        generation = self._calculate_generation()
        demand = self._calculate_demand()
        balance = self._balance(generation, demand)
        risks = self._assess_risks(balance)
        
        result = SimulationResult(
            timestep=self.timestep,
            generation_mw=generation,
            demand_mw=demand,
            balance_mw=balance,
            risks=risks,
            plants_status=self.grid.plants
        )
        
        self.history.append(result)
        self.timestep += 1
        return result
        
    def _calculate_generation(self) -> float:
        """Suma potencia de todas centrales según estado"""
        
    def _calculate_demand(self) -> float:
        """Calcula demanda según modelo + variaciones"""
        
    def _balance(self, generation: float, demand: float) -> float:
        """Retorna diferencia (> 0 = superávit, < 0 = déficit)"""
        
    def _assess_risks(self, balance: float) -> RiskAssessment:
        """Evalúa riesgo de apagón, dependencia, etc"""
```

#### `simulation/balance_calculator.py`
```python
class BalanceCalculator:
    """Cálculos de balance energético"""
    
    @staticmethod
    def calculate_reserve_margin(generation: float, demand: float) -> float:
        """
        Margen de reserva operativa (%)
        Recomendación: > 15% seguro
        """
        if demand == 0:
            return 0
        return ((generation - demand) / demand) * 100
    
    @staticmethod
    def calculate_energy_unmet(generation: float, demand: float) -> float:
        """Energía no suministrada (ENS) en MWh"""
        return max(0, demand - generation)
    
    @staticmethod
    def calculate_dependency(
        hydro_mw: float, 
        thermal_mw: float, 
        renewable_mw: float
    ) -> Dict[str, float]:
        """Porcentaje de dependencia por fuente"""
        total = hydro_mw + thermal_mw + renewable_mw
        if total == 0:
            return {}
        return {
            "hydro": (hydro_mw / total) * 100,
            "thermal": (thermal_mw / total) * 100,
            "renewable": (renewable_mw / total) * 100
        }
```

#### `simulation/risk_assessor.py`
```python
class RiskAssessor:
    """Evaluación de riesgos del sistema"""
    
    @staticmethod
    def calculate_blackout_risk(balance_mw: float, demand_mw: float) -> RiskLevel:
        """
        Escala de riesgo:
        - SAFE: balance > 20% de demanda
        - ALERT: balance 10-20% de demanda
        - CRITICAL: balance 0-10% de demanda
        - FAILURE: balance < 0 (hay déficit)
        """
        if demand_mw == 0:
            return RiskLevel.SAFE
        
        margin_percent = (balance_mw / demand_mw) * 100
        
        if margin_percent >= 20:
            return RiskLevel.SAFE
        elif margin_percent >= 10:
            return RiskLevel.ALERT
        elif margin_percent >= 0:
            return RiskLevel.CRITICAL
        else:
            return RiskLevel.FAILURE
    
    @staticmethod
    def calculate_hydro_dependency_risk(hydro_percent: float) -> RiskLevel:
        """
        Si > 60% es hidroeléctrica, vulnerable a sequías
        """
        if hydro_percent > 70:
            return RiskLevel.CRITICAL
        elif hydro_percent > 60:
            return RiskLevel.ALERT
        else:
            return RiskLevel.SAFE
```

### 4. Módulo Infrastructure (Datos e Integración)

#### `data/repository.py`
```python
from abc import ABC, abstractmethod

class PowerPlantRepository(ABC):
    """Patrón Repository para persistencia"""
    
    @abstractmethod
    def get_all(self) -> List[PowerPlant]:
        """Obtiene todas las centrales"""
        
    @abstractmethod
    def get_by_id(self, plant_id: str) -> Optional[PowerPlant]:
        """Obtiene central por ID"""
        
    @abstractmethod
    def save(self, plant: PowerPlant) -> None:
        """Guarda o actualiza central"""
        
    @abstractmethod
    def delete(self, plant_id: str) -> None:
        """Elimina central"""
```

#### `data/sqlite_repository.py`
```python
class SQLitePowerPlantRepository(PowerPlantRepository):
    """Implementación SQLite del repositorio"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()
        
    def _init_schema(self):
        """Crea tablas si no existen"""
        # CREATE TABLE power_plants (...)
        
    def get_all(self) -> List[PowerPlant]:
        # SELECT * FROM power_plants
        
    # ... otras implementaciones
```

#### `gis/leaflet_bridge.py`
```python
class LeafletBridge(QWebChannel):
    """Bridge comunicación PyQt6 ↔ Leaflet.js"""
    
    def __init__(self):
        super().__init__()
        self.setupWebChannel()
        
    def add_marker(self, plant: PowerPlant, icon_url: str) -> None:
        """Agrega marcador al mapa desde Python"""
        # Invoca JavaScript: mapHandler.addMarker(...)
        
    def update_marker_status(self, plant_id: str, status: str) -> None:
        """Actualiza estado visual de marcador"""
        
    def set_map_center(self, lat: float, lon: float, zoom: int) -> None:
        """Centra mapa a coordenadas"""
        
    @pyqtSlot(str, float, float)
    def on_marker_clicked(self, plant_id: str, lat: float, lon: float):
        """Slot disparado cuando usuario clickea marcador en mapa"""
        # Emite señal que captura UI Controller
```

#### `gis/geo_manager.py`
```python
class GeoManager:
    """Gestión de coordinadas y proyecciones geoespaciales"""
    
    ECUADOR_BOUNDS = {
        "north": -0.1,      # Ecuador pasa por línea ecuatorial
        "south": -5.3,
        "west": -81.0,
        "east": -75.0
    }
    
    @staticmethod
    def wgs84_to_utm(lat: float, lon: float) -> Tuple[int, int]:
        """Convierte WGS84 a UTM Zona 17S (Ecuador)"""
        # Usa librería pyproj
        
    @staticmethod
    def utm_to_wgs84(easting: int, northing: int) -> Tuple[float, float]:
        """Convierte UTM Zona 17S a WGS84"""
        
    @staticmethod
    def is_in_ecuador(lat: float, lon: float) -> bool:
        """Valida si punto está dentro de Ecuador"""
```

#### `api/cenace_client.py`
```python
class CENACEClient:
    """Cliente para consumir datos CENACE"""
    
    BASE_URL = "https://api.cenace.gob.ec"  # Endpoint a verificar
    
    async def get_real_time_demand(self) -> float:
        """Demanda en tiempo real (MW)"""
        
    async def get_generation_by_source(self) -> Dict[str, float]:
        """Generación por fuente (hidro, térmica, etc)"""
        
    async def get_transmission_status(self) -> Dict:
        """Estado de líneas de transmisión"""
        
    async def get_maintenance_schedule(self) -> List[Dict]:
        """Mantenimiento programado"""
```

#### `events/event_bus.py`
```python
class EventBus:
    """Bus de eventos para comunicación desacoplada"""
    
    def __init__(self):
        self._subscribers = defaultdict(list)
        
    def subscribe(self, event_type: str, handler: Callable):
        """Se suscribe a tipo de evento"""
        self._subscribers[event_type].append(handler)
        
    def emit(self, event: DomainEvent):
        """Emite evento a todos suscriptores"""
        for handler in self._subscribers[event.__class__.__name__]:
            handler(event)

# Tipos de eventos definidos:
class SimulationStartedEvent(DomainEvent):
    scenario_name: str
    
class PowerPlantFailureEvent(DomainEvent):
    plant_id: str
    plant_name: str
    
class DemandIncreaseEvent(DomainEvent):
    previous_mw: float
    new_mw: float
```

---

## Tecnologías Recomendadas

### Frontend / UI

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **PyQt6** | 6.6+ | UI Escritorio | Estándar industria, buena integración, multiplataforma |
| **QWebEngineView** | Integrado | Render web en PyQt | Mejor que QPainter para mapas, compatible con Leaflet |
| **Leaflet.js** | 1.9+ | Mapas OSM | Ligero, responsive, fácil de embeber |
| **OpenStreetMap** | Tiles públicos | Datos cartográficos | Gratuito, cobertura Ecuador completa, licencia abierta |
| **Qt Designer** | Integrado | Diseño UI | Acelera desarrollo de formularios |

**Alternativas consideradas:**
- ~~PySimpleGUI~~ → No escalable para app profesional
- ~~Tkinter~~ → Muy limitado en capacidades gráficas
- ~~PySide6~~ → Similar a PyQt6, mantenimiento menos activo
- ~~PyGObject~~ → Overkill para este caso

### Backend / Lógica

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **Python** | 3.11+ | Runtime principal | Estándar científico, ecosistema GIS maduro |
| **NumPy** | 1.24+ | Cálculos numéricos | Optimizado, velocidad C |
| **Pandas** | 2.0+ | Manipulación datos | Análisis de series temporales, demanda histórica |
| **SQLite3** | 3.40+ | BD local | Cero dependencias, embedded, perfecto para app escritorio |
| **SQLAlchemy** | 2.0+ | ORM/Query builder | Abstracción BD, migraciones, testeable |
| **Pydantic** | 2.0+ | Validación datos | Type hints, serialización JSON, muy usado |

### GIS / Geoespacial

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **Pyproj** | 3.5+ | Proyecciones cartográficas | Conversión WGS84 ↔ UTM, preciso |
| **Shapely** | 2.0+ | Geometría geoespacial | Operaciones con polígonos (regiones, líneas) |
| **Folium** | 0.14+ (opt) | Generar mapas Leaflet | Si genera mapas estáticos para reportes |
| **GeoPandas** | 0.13+ (opt) | DataFrames geoespaciales | Si maneja capas GIS complejas |

**Nota:** Para Fase 1 es suficiente Pyproj + Leaflet. GeoPandas/Shapely para futuro.

### Simulación / Cálculos

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **SciPy** | 1.10+ | Optimización, estadística | Para balancing y cálculos avanzados |
| **Matplotlib** | 3.7+ | Gráficas estáticas | Reportes, análisis post-simulación |
| **Plotly** | 5.13+ (opt) | Visualización interactiva | Dashboards dinámicos (Fase 3) |

### Testing

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **pytest** | 7.4+ | Framework testing | Estándar Python, fixtures poderosas |
| **pytest-cov** | 4.1+ | Cobertura código | Métricas de calidad |
| **pytest-mock** | 3.11+ | Mocking | Aislar componentes |
| **hypothesis** | 6.82+ | Property-based testing | Encontrar edge cases |
| **tox** | 4.6+ | Testing multi-env | Verificar en Python 3.11, 3.12 |

### DevOps / Packaging

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **PyInstaller** | 6.0+ | Empaquetado ejecutable | Distribuir .exe sin Python instalado |
| **Poetry** | 1.5+ | Gestión dependencias | Reproducibilidad, lock files |
| **pre-commit** | 3.3+ | Git hooks | Lint automático antes de commit |
| **Black** | 23.7+ | Formateo código | Consistencia, PEP 8 |
| **Ruff** | 0.1+ | Linting rápido | Reemplaza flake8/isort/black |
| **mypy** | 1.4+ | Type checking | Prevenir errores de tipos |

### Opcional (Futuro)

| Tecnología | Propósito |
|---|---|
| **Redis** | Caché en memoria (si se federan múltiples instancias) |
| **FastAPI** | API REST si se convierte a arquitectura cliente-servidor |
| **Celery** | Task queue si simulaciones son muy pesadas |
| **PostgreSQL** | Escalar BD más allá de SQLite |

---

## Plan de Implementación

### Fase 1: MVP Funcional (6-8 semanas)
**Objetivo:** Ventana PyQt6 + Mapa OSM + Visualización básica de centrales

#### Hito 1.1: Setup Proyecto (Semana 1)
- ✅ Estructura carpetas
- ✅ Configuración Poetry
- ✅ Setup linters (Black, Ruff, mypy)
- ✅ Configuración pytest
- ✅ BD SQLite inicial
- **Entrega:** Skeleton proyecto ejecutable

#### Hito 1.2: Interfaz Básica PyQt6 (Semanas 1-2)
- ✅ MainWindow con layout
- ✅ Panel lateral con widgets básicos
- ✅ Toolbar con acciones (Play, Pause, Reset)
- ✅ Integración QWebEngineView (blanco)
- **Entrega:** UI "shell" sin lógica

#### Hito 1.3: Integración Leaflet (Semanas 2-3)
- ✅ HTML contenedor Leaflet.js
- ✅ Recursos web (CSS, JS)
- ✅ QWebChannel bridge PyQt ↔ JavaScript
- ✅ Cargar mapa centrado en Ecuador
- ✅ Controles básicos zoom/paneo
- **Entrega:** Mapa OSM interactivo

#### Hito 1.4: Carga de Datos (Semana 3)
- ✅ Crear centrales_ecuador.json con 30 centrales principales
- ✅ Esquema PowerPlant (JSON)
- ✅ Validación con Pydantic
- ✅ Cargador JSON → BD SQLite
- **Datos:** 
  - 10 centrales hidroeléctricas principales (Coca-Codo, Paute, etc)
  - 5 centrales térmicas (Termo gas, etc)
  - 15 pequeñas centrales (hidro, eólica, solar)
- **Entrega:** BD con centrales, datos validados

#### Hito 1.5: Visualización en Mapa (Semanas 3-4)
- ✅ Obtener centrales de BD
- ✅ Generar iconos por tipo (SVG/PNG)
- ✅ Renderizar marcadores en Leaflet
- ✅ Popup con info básica (nombre, MW)
- ✅ Colorear por estado (rojo=offline, verde=online)
- **Entrega:** Mapa con centrales visualizadas

#### Hito 1.6: Interactividad Inicial (Semana 4)
- ✅ Click en marcador → Panel lateral muestra detalles
- ✅ Tabla de centrales en panel lateral
- ✅ Click en tabla → Resalta marcador
- ✅ Campos editables en panel (estado, capacidad)
- **Entrega:** Mapa + Sidebar integrados

#### Hito 1.7: Motor Básico (Semana 5)
- ✅ Clase PowerGrid y PowerPlant
- ✅ SimulationEngine básico (sin escenarios)
- ✅ Cálculo balance: Σ generación - demanda
- ✅ Reserva operativa
- ✅ Dependencia por fuente (hidro/térmica)
- **Entrega:** Simulación sin GUI

#### Hito 1.8: Integración Simulación UI (Semana 5-6)
- ✅ Button "Simular" en toolbar
- ✅ Slider demanda + 0-30%
- ✅ Checkboxes para apagar centrales
- ✅ Button ejecutar simulación
- ✅ Panel inferior muestra resultados (balance, reserva, riesgo)
- **Entrega:** Simulación básica con UI

#### Hito 1.9: Métricas y Alertas (Semana 6)
- ✅ Cálculo Risk Level (Safe/Alert/Critical/Failure)
- ✅ Indicador visual (semáforo: verde/amarillo/rojo)
- ✅ Panel de alertas con eventos
- ✅ Gráfica simple (matplotlib embedded) de balance temporal
- **Entrega:** Dashboard con KPIs

#### Hito 1.10: Testing y Polish (Semana 6-7)
- ✅ Tests unitarios (motor, cálculos)
- ✅ Tests integración (BD, UI)
- ✅ Bug fixes
- ✅ Documentación usuario
- ✅ Ejecutable con PyInstaller
- **Entrega:** MVP v1.0 instalable

**Riesgos Fase 1:**
- QWebChannel puede tener delays en comunicación (solución: asyncio)
- Proyecciones WGS84 complejas (solución: usar Pyproj testeado)

**Criterios de Aceptación:**
- ✅ Aplicación abre sin errores
- ✅ Mapa se carga y es interactivo
- ✅ 10+ centrales visualizadas correctamente
- ✅ Simulación calcula balance sin crashes
- ✅ 80%+ cobertura tests

---

### Fase 2: Motor Simulación Avanzado (4-5 semanas)
**Objetivo:** Escenarios complejos, eventos, contingencias

#### Hito 2.1: Modelo Demanda Avanzado (Semana 7-8)
- Demanda base por región (Costa/Sierra/Oriente)
- Curva de demanda horaria (picos en mañana/noche)
- Crecimiento anual
- Simulación eventos (fin de semana, feriados)
- Tests de curvas históricas

#### Hito 2.2: Eventos y Contingencias (Semana 8)
- Sistema de eventos (ScheduledEvent, FaultEvent)
- Falla central aleatoria
- Salida línea transmisión
- Sequía → reducción hidro
- Simulador de eventos programados

#### Hito 2.3: Escenarios (Semana 8-9)
- Modelo Scenario (JSON con cambios de estado)
- Guardar/cargar escenarios
- Preset scenarios (sequía, crisis térmica, demanda pico)
- Comparación escenarios

#### Hito 2.4: Histórico y Replay (Semana 9)
- Almacenar resultados simulación temporal
- Exportar serie de tiempo (CSV)
- Gráficas temporales Matplotlib/Plotly
- Análisis retrospectivo

---

### Fase 3: Dashboards e Interfaces Avanzadas (4 semanas)
**Objetivo:** Reportes, visualizaciones, análisis avanzado

#### Hito 3.1: Dashboards (Semana 10-11)
- Widget de gráficas interactivas (Plotly)
- KPIs dashboards
- Histórico 24h/7d/30d
- Tendencias

#### Hito 3.2: Reportes (Semana 11-12)
- Generar PDF de simulación
- Exportar datos Excel
- Gráficas impresas
- Resumen ejecutivo

#### Hito 3.3: Análisis Sensibilidad (Semana 12)
- Variar parámetro sistemáticamente
- Graficar impacto en balance/riesgo
- Identificar factores críticos
- Curvas "qué pasa si"

---

### Fase 4: Optimización y Escalabilidad (3-4 semanas)
**Objetivo:** Performance, multi-usuario, cloud-ready

#### Hito 4.1: Optimización (Semana 13)
- Profiling código crítico
- Paralelización cálculos (multiprocessing)
- Caché de simulaciones
- Compresión datos

#### Hito 4.2: APIs REST (Semana 13-14)
- FastAPI endpoints básicos
- Autenticación simple
- CORS configurado
- Documentación OpenAPI

#### Hito 4.3: Persistencia Avanzada (Semana 14)
- PostgreSQL alternativa SQLite
- Migraciones versionadas
- Backups automáticos
- Auditoría cambios

---

### Fase 5: Hardening y Distribución (2-3 semanas)
**Objetivo:** Versión profesional distribuble

#### Hito 5.1: Empaquetado (Semana 15)
- PyInstaller configurado
- Instalador NSIS (Windows)
- Códigos de versión
- Auto-update

#### Hito 5.2: Documentación (Semana 15)
- Manual usuario (PDF)
- Guía técnica arquitectura
- API documentation
- Video tutoriales

#### Hito 5.3: QA Final (Semana 16)
- Testing cross-platform
- Prueba de usabilidad
- Performance benchmarks
- Security audit

---

## Decisiones Arquitectónicas Críticas

### 1. Clean Architecture + MVVM vs. Monolítico

**Decisión:** Clean Architecture + MVVM

**Razones:**
- Permite testear lógica sin UI
- Fácil migrar a cliente-servidor (FastAPI frontend)
- Escalar a múltiples usuarios sin reescribir core
- PyQt6 es complejo; MVVM reduce coupling

**Trade-off:** Más boilerplate inicial, pero ROI alto a largo plazo

---

### 2. Datos: Híbrido JSON + SQLite

**Decisión:** SQLite como BD principal, JSON para export/import

**Razones:**
- SQLite: sin dependencias, embedded, perfecto escriborio
- JSON: portabilidad, versionable en git, scenarios
- Hybrid: lo mejor de ambos mundos

**Trade-off:** Sincronización JSON ↔ SQLite requiere cuidado

**Alternativa rechazada:** PostgreSQL desde inicio (overkill Fase 1)

---

### 3. GIS: Leaflet.js en QWebEngineView

**Decisión:** Leaflet.js embebido, no QPainter

**Razones:**
- Leaflet es especializado en mapas (mejor UX)
- OSM es estándar, mantenido, gratuito
- QWebChannel es sólido (Qt 5.4+)
- Reutilizable en web (FastAPI + Leaflet frontend)

**Trade-off:** Overhead comunicación PyQt ↔ JavaScript (mitigable)

**Alternativa rechazada:** Folium (genera mapas estáticos, no interactivos)

---

### 4. Simulación: Cálculos Sincronos vs. Async

**Decisión:** Sincronos en Fase 1, Async en Fase 4

**Razón Fase 1:** Simplicidad, no es bloqueante
**Razón Fase 4:** MultiProcessing paralelizar 1000+ escenarios

**Migración:** Threading + QThread para no bloquear UI

---

### 5. Versionado Datos: Migraciones BD

**Decisión:** SQLAlchemy + Alembic para migraciones

**Razón:** Reproducibilidad, versionable en git, rollback

**Impacto:** Requiere disciplina, pero escalabilidad industrial

---

## Análisis de Riesgos

### Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| **QWebEngine inestable** | Media | Alto | Usar versión LTS PyQt6 (6.5+), tests exhaustivos bridge |
| **Proyecto GIS más complejo que esperado** | Media | Medio | Usar Pyproj testeado, no reinventar rueda GIS |
| **Datos centrales desactualizados** | Baja | Medio | Versionar, documentar fuente, update schedule |
| **Performance motor simulación (1000 iteraciones)** | Baja | Medio | NumPy + SciPy, no loops Python puros |
| **Especificación CENACE API no pública** | Alta | Bajo | Plan B: datos JSON locales suficientes Fase 1 |
| **Cambios requisitos en mitad proyecto** | Media | Alto | SCRUM 2-week sprints, reviews regulares |

### Riesgos No Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| **Falta de datos públicos precisos** | Media | Muy Alto | Contactar CENACE/CELEC EP temprano, conseguir historiales |
| **Validación de modelos físicos (experto)** | Media | Muy Alto | Colaborar con ingeniero eléctrico especialista |
| **Cambios regulatorios** | Baja | Medio | Modular, poder actualizar reglas sin cambiar código core |
| **Burnout equipo (proyecto largo)** | Media | Alto | Documentar bien, evitar deuda técnica, releases pequeñas |

---

## Estrategia de Escalabilidad

### Escenario 1: Local Desktop (Fase 1-2)
- SQLite file-based
- Simulación sincrónica
- Máx. 500 iteraciones
- 1 usuario concurrente

### Escenario 2: Workstation Poderosa (Fase 3-4)
- SQLite + caché RAM
- Parallelización MultiProcessing
- 10,000+ iteraciones
- 5-10 usuarios (conexión remota SSH)

### Escenario 3: Servidor Multi-usuario (Fase 5+)
```
┌─────────────────────┐
│   Cliente Web       │ (Navegador + React/Vue)
│  (Leaflet + Chart)  │
└──────────┬──────────┘
           │ REST API
┌──────────▼──────────┐
│  FastAPI Backend    │
│  - Sessions         │
│  - Autenticación    │
│  - Rate limiting    │
└──────────┬──────────┘
           │ ORM/SQLAlchemy
┌──────────▼──────────┐
│   PostgreSQL        │
│ - Multi-tenant      │
│ - Backups           │
│ - Auditoría         │
└─────────────────────┘

Bonus: Celery task queue
  - Simulaciones pesadas async
  - Worker pool
  - Monitoring con Flower
```

### Crecimiento Datos

| Fase | Centrales | Líneas TX | Subestaciones | BD Size |
|---|---|---|---|---|
| 1 | 30 | 0 | 5 | ~500 KB |
| 3 | 100 | 50 | 30 | ~10 MB |
| 5 | 500+ | 200+ | 100+ | ~500 MB |

**Estrategia:**
- Índices en BD en campos clave (tipo, región)
- Particionamiento temporal en histórico
- Archiving escenarios antiguos
- Compresión geoJSON

---

## Metrificación y Monitoreo

### Métricas Clave Simulación

```python
@dataclass
class SimulationMetrics:
    """KPIs del sistema eléctrico"""
    
    # Balancing
    generation_mw: float              # MW producidos
    demand_mw: float                  # MW consumidos
    balance_mw: float                 # Diferencia (> 0 = superávit)
    reserve_margin_percent: float     # % de margen
    
    # Riesgo
    risk_level: RiskLevel             # Safe/Alert/Critical/Failure
    blackout_probability: float       # 0-1
    
    # Dependencia
    hydro_percent: float              # % generación hidro
    thermal_percent: float            # % generación térmica
    renewable_percent: float          # % generación renovable
    
    # Disponibilidad
    plants_online: int                # Centrales activas
    plants_offline: int               # Centrales fuera
    capacity_factor: float            # (Actual / Instalada)
    
    # Eventos
    events_in_period: int
    contingencies_active: int
```

### Logging

```python
# Configurar logging estructurado con JSON
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# En código
logger.info("Simulación iniciada", extra={
    "scenario": "sequía_2026",
    "duration_hours": 24,
    "timestep_minutes": 15
})

logger.warning("Margen de reserva bajo", extra={
    "current_margin": 12.5,
    "threshold": 15.0
})

logger.error("Falla motor simulación", exc_info=True)
```

### Tests Cobertura Objetivo

- **Unit:** 85%+ (lógica de negocio)
- **Integration:** 70%+ (repositorio, APIs)
- **E2E:** 50%+ (flujos críticos)
- **Performance:** Benchmarks críticos

---

## Recomendaciones Finales

### Buenas Prácticas Aplicadas

1. **Separation of Concerns**
   - Cada módulo responsable de una cosa
   - UI no conoce detalles BD
   - Simulación no conoce PyQt6

2. **Testabilidad**
   - Inyección dependencias
   - Interfaces claras (ABC)
   - Fixtures pytest completas

3. **Escalabilidad**
   - Arquitectura permite migración cloud
   - BD agnóstica (swap SQLite por PostgreSQL)
   - APIs listas para exposición REST

4. **Mantenibilidad**
   - Documentación arquitectura
   - Type hints en todo código
   - Linting automático (pre-commit)

### Próximos Pasos Accionables

1. **Semana 0 (Esta):**
   - Reunión con experto eléctrico (validar modelos)
   - Contactar CENACE (datos disponibles)
   - Setup repositorio git

2. **Semana 1:**
   - Crear estructura proyecto
   - Poetry + pytest running
   - Primeros tests verdes

3. **Semana 2:**
   - PyQt6 MainWindow básica
   - Leaflet.js integrado
   - Primer marcador en mapa

### Convertir a Herramienta Profesional SCADA-lite

**Año 1 (Fases 1-3):**
- Desktop app standalone
- Simulación determinista

**Año 2 (Fases 4-5):**
- APIs REST
- Múltiples usuarios
- Datos pseudo-reales CENACE

**Año 3+ (SCADA-lite):**
- Integración SCADA real
- Time-series DB (InfluxDB)
- Dashboards profesionales (Grafana)
- Alerting automatizado
- Machine Learning (forecasting)

---

## Bibliografía / Referencias

### Técnicas GIS
- Pyproj Documentation: https://proj.org/
- Leaflet.js Guide: https://leafletjs.com/reference.html
- UTM Ecuador: Zona 17S (proyección estándar)

### Simulación Energética
- Modelos CENACE Ecuador (contactar institución)
- IEEE Standard Power Flow (Newton-Raphson)
- Reserva Operativa: mejor práctica > 15-20%

### Arquitectura Software
- Clean Architecture (Robert C. Martin)
- MVVM Pattern (WPF/Qt best practices)
- Domain Driven Design (Eric Evans)

### Python Tools
- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- pytest: https://docs.pytest.org/

---

## Anexo A: Checklist Inicio Proyecto

- [ ] Repositorio Git creado
- [ ] Python 3.11+ instalado
- [ ] Poetry configurado
- [ ] Linters activos (Black, Ruff, mypy)
- [ ] Pytest corriendo
- [ ] Primer commit ("Initial commit: project setup")
- [ ] Documentación README.md
- [ ] Contacto CENACE iniciado
- [ ] Experto eléctrico identificado
- [ ] Datos centrales validados

---

**Documento elaborado por:** Arquitecto Senior Python/PyQt6/GIS  
**Fecha:** 2026-04-27  
**Versión:** 1.0  
**Estado:** Aprobado para implementación Fase 1

---

## Adenda de Implementación (2026-05-02)

### Estado Arquitectónico Real

El sistema evolucionó desde el diseño base y actualmente opera con una arquitectura integrada en producción local:

- Simulador desktop en PyQt6 como capa de presentación y orquestación visual.
- Microservicio externo `cenace_scraper_service` como fuente oficial de datos operativos.
- Modo dual `AUTOMATIC`/`MANUAL` con reglas de edición y control de consistencia.
- Persistencia local de escenarios sobre JSON versionado para reproducibilidad.

### Contrato Operativo con Microservicio

El simulador consume de forma periódica:

- `GET /api/v1/production/latest`
- `GET /api/v1/plants/latest`
- `GET /api/v1/demand/hourly`
- `GET /api/v1/health`

Principio de robustez: ante fallos transitorios del microservicio, la aplicación conserva el último estado válido y reporta degradación de sincronización sin bloquear la UI.

### Capas y Componentes Implementados

1. Dominio
- Modelado de `SimulationState` y `SimulationMetrics`.
- Cálculos puros de balance, margen de reserva y clasificación de riesgo.

2. Aplicación
- `SimulationController` con transición `AUTOMATIC ↔ MANUAL`.
- `ScenarioManager` para guardar/restaurar/duplicar/descartar escenarios.
- Mapper de generación por planta con reconciliación por nombre y fallback por capacidad.

3. Infraestructura
- Cliente HTTP `CENACEClient` para endpoints del microservicio.
- `EventBus` interno para desacoplar sincronización, rendering y feedback de estado.

4. Presentación
- `MainWindow` con panel de control, escenarios y edición por central en modo manual.
- `MapWidget` con leyenda operativa, overlay por tecnología y por central, y selección bidireccional mapa-panel.

### Fases Implementadas a la Fecha

- Fase 0: Alineación de alcance y contrato de datos.
- Fase 1: Núcleo de simulación (estado, KPIs, balance, riesgo).
- Fase 2: Integración con microservicio.
- Fase 3: Orquestación + gestor de escenarios + bus de eventos.
- Fase 4: UI funcional completa (incluye edición manual por central y selección bidireccional).
- Fase 5: Persistencia local de escenarios.
- Fase 6: Pruebas, hardening e integración en vivo.
- Fase 7: Cierre documental en curso (esta adenda y documentos operativos).

### Nueva Fase Agregada

#### Fase 8 — Manual de Usuario y Trazabilidad de Impacto

Objetivo: documentar para usuario final qué hace cada control, cómo usar cada flujo y cómo cada acción afecta el modelo de simulación.

Entregables de fase:
- `MANUAL_USUARIO.md`: guía funcional detallada.
- Matriz control → variable de estado → impacto en KPIs.
- Flujos operativos recomendados para análisis reproducible.

### Criterios de Aceptación del Cierre Documental

- Arquitectura oficial refleja diseño real implementado.
- Estado del checkpoint actualizado a hito funcional integrado.
- Guía operativa y manual de usuario disponibles y consistentes con el código.

