# Arquitectura Actual del Simulador de Matriz Energetica del Ecuador

Version: 2.0  
Fecha: 2026-05-02  
Estado: Implementado y validado por pruebas

## 1. Objetivo

Este documento describe la arquitectura real implementada en el repositorio y reemplaza la version de diseno inicial.

Alcance cubierto:

- Simulador desktop (PyQt6 + mapa Leaflet embebido)
- Integracion con microservicio CENACE scraper (FastAPI)
- Modos AUTOMATIC y MANUAL
- Calculo de KPI (oferta, balance, reserva, riesgo)
- Persistencia local de escenarios con versionado
- Modelo hidrico simplificado para analisis de sequia

## 2. Arquitectura por Capas

### 2.1 Presentacion (UI)

Archivos principales:

- src/ui/main_window.py
- src/ui/map_widget.py
- src/ui/charts_widget.py
- src/ui/charts_data_mapper.py

Responsabilidades:

- Renderizar controles de simulacion y panel KPI
- Gestionar seleccion/edicion de centrales
- Exponer controles hidricos (embalse por central y sequia global)
- Renderizar panel derecho de graficas (instantaneo + tendencia)
- Publicar y consumir eventos de estado en EventBus
- Proyectar estado operativo en mapa y leyenda

### 2.2 Aplicacion (orquestacion)

Archivos principales:

- src/application/simulation_controller.py
- src/application/scenario_manager.py
- src/application/plant_generation_mapper.py

Responsabilidades:

- Coordinar sincronizacion contra microservicio
- Gestionar transicion AUTOMATIC <-> MANUAL
- Recalcular estado y KPI desde catalogo local en modo manual
- Guardar/restaurar escenarios versionados
- Traducir datos de plantas en vivo a catalogo local para overlay en automatico

### 2.3 Dominio (logica pura)

Archivos principales:

- src/domain/models/simulation_state.py
- src/domain/simulation/balance_calculator.py
- src/domain/simulation/risk_assessor.py
- src/domain/simulation/generation_allocator.py
- src/domain/simulation/generation_aggregator.py
- src/domain/simulation/hydro_physics.py

Responsabilidades:

- Modelo de estado de simulacion y serializacion
- Ecuaciones de oferta total, balance y margen de reserva
- Clasificacion de riesgo por umbrales configurables
- Agregacion por tecnologia y por central
- Modelo fisico simplificado de generacion hidro

### 2.4 Infraestructura

Archivos principales:

- src/infrastructure/api/cenace_client.py
- src/infrastructure/events/event_bus.py
- config/settings.py

Responsabilidades:

- Cliente HTTP para endpoints del microservicio
- Bus de eventos en proceso (pub/sub)
- Configuracion centralizada de umbrales, rutas, intervalos y defaults

## 3. Microservicio CENACE (componente externo integrado)

Ruta:

- cenace_scraper_service/

Stack:

- FastAPI + SQLAlchemy + APScheduler + Playwright

Contrato consumido por el simulador:

- health
- latest production
- hourly demand curve
- latest plants

Regla de integracion:

- En modo AUTOMATIC prevalece el dato externo del microservicio
- En modo MANUAL prevalece el catalogo local editado por usuario

## 4. Flujo de Datos

### 4.1 Modo AUTOMATIC

1. UI solicita sincronizacion periodica o manual.
2. SimulationController consulta CENACEClient.
3. Controller actualiza SimulationState con demanda/generacion import/export.
4. Domain calcula KPI.
5. UI renderiza panel KPI y overlay del mapa.
6. Overlay por planta usa mapper de nombres sobre payload live.
7. Panel de graficas usa curva horaria CENACE cuando esta disponible.

### 4.2 Modo MANUAL

1. Usuario edita demanda, estado de central o controles hidricos.
1. Usuario edita demanda, estado de central, embalse o sequia global.
2. MainWindow envia catalogo local al SimulationController.
3. Controller agrega generacion por central/tipo (incluye hidro fisico).
4. Domain recalcula KPI inmediatamente.
5. UI actualiza KPI y leyenda/mapa en el mismo ciclo.
6. Panel de graficas usa historial de sesion y marca eventos operativos.

## 5. Modelo de Estado

SimulationState incluye:

- schema_version
- mode
- demand_mw
- hydro_mw
- thermal_mw
- renewable_mw
- global_drought_factor
- import_mw
- export_mw
- source_timestamp
- last_manual_edit
- metrics (total_supply_mw, balance_mw, reserve_margin_pct, risk_level)

Compatibilidad:

- from_dict mantiene compatibilidad con escenarios anteriores sin campos nuevos

## 6. Modelo Hidrico Simplificado

La generacion hidro por central sigue:

$$
P_{hidro} = P_{disponible} \times F_{hidraulico}
$$

Donde $F_{hidraulico}$ combina:

- nivel de embalse
- sequia global

Propiedades del modelo:

- Factores acotados para estabilidad numerica
- Salida acotada a $[0, P_{disponible}]$
- OFFLINE/MAINTENANCE produce 0 MW

## 7. KPI y Riesgo

KPI calculados por dominio:

- oferta total
- balance
- margen de reserva
- nivel de riesgo

Umbrales de riesgo configurables en config/settings.py:

- SAFE
- ALERT
- CRITICAL
- FAILURE

## 8. Persistencia de Escenarios

Componente:

- src/application/scenario_manager.py

Estructura de archivo JSON:

- schema_version (escenario)
- name
- saved_at
- state (SimulationState serializado)
- centrales (catalogo operativo normalizado: embalse por central hidro)

Comportamiento:

- save guarda estado + centrales
- load_bundle restaura estado y centrales cuando existen
- load mantiene API previa devolviendo solo SimulationState
- duplicado conserva el bundle completo
- normalizacion elimina campos legacy de caudal/sequia local durante save/load

## 8.1 Analitica Visual (Panel de Graficas)

Visuales principales:

- Estado instantaneo (demanda, oferta, balance)
- Dona de generacion por tipo
- Demanda vs oferta
- Reserva/import/export
- Tendencia temporal con selector de ventana

Contrato Python -> JS:

- mode, risk_level, reserve_margin_pct
- demand_mw, supply_mw, balance_mw
- import_mw, export_mw
- generation_by_type
- timeline_source
- timeline
- recent_events

Politica de timeline:

- AUTOMATIC: preferir curva horaria CENACE
- MANUAL o fallback: usar historial de sesion

## 9. Bus de Eventos

Implementacion:

- src/infrastructure/events/event_bus.py

Eventos usados en UI:

- state_updated
- sync_error

Modelo de ejecucion:

- Sincronico en proceso
- Acoplamiento bajo entre controlador y componentes UI

## 10. Estructura Real del Proyecto

Modulos de simulador usados activamente:

- src/application/
- src/domain/
- src/infrastructure/
- src/ui/
- config/
- data/
- tests/

Componente de integracion externa en el mismo workspace:

- cenace_scraper_service/

## 11. Estrategia de Pruebas

Suite validada:

- Unit tests de calculadoras, agregadores y mapper
- Unit tests de controlador de simulacion
- Pruebas de persistencia de escenarios
- Flujo E2E automatic -> manual -> save -> restore
- Smoke/integration tests con microservicio local

Estado actual:

- 34 pruebas en verde en ejecucion completa

## 12. Decisiones Arquitectonicas Activas

1. Mantener EventBus simple y sincronico para escritorio local.
2. Mantener modelo hidrico determinista en esta fase (sin simulacion temporal de embalse por horizonte).
3. Separar reglas de negocio puras del wiring de UI.
4. Mantener compatibilidad hacia atras de escenarios.
5. Priorizar coherencia central -> KPI por encima de complejidad fisica avanzada.

## 13. Riesgos y Limitaciones

- Mapeo de nombres de plantas live a catalogo local sigue heuristico.
- No hay dinamica temporal multihora de hidrologia (recarga/descarga por paso).
- El KPI es operativo agregado y no un flujo AC completo de red.

## 14. Roadmap Tecnico

Corto plazo:

- Presets de sequia (leve/media/severa)
- Ajuste de alias de mapeo de plantas
- Mejoras de UX para comparacion entre escenarios

Mediano plazo:

- Simulacion temporal de embalse por horizonte
- Parametrizacion regional de riesgo
- Reportes exportables de escenarios

## 15. Trazabilidad Documento <-> Codigo

Cobertura principal:

- UI y controles: src/ui/main_window.py, src/ui/map_widget.py
- Orquestacion: src/application/simulation_controller.py
- Persistencia: src/application/scenario_manager.py
- Modelo estado: src/domain/models/simulation_state.py
- Dominio KPI: src/domain/simulation/balance_calculator.py, src/domain/simulation/risk_assessor.py
- Modelo hidro y agregacion: src/domain/simulation/hydro_physics.py, src/domain/simulation/generation_aggregator.py
- Integracion microservicio: src/infrastructure/api/cenace_client.py
- Eventos: src/infrastructure/events/event_bus.py
- Configuracion: config/settings.py
- Validacion: tests/
