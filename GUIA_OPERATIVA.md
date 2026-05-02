# Guia Operativa Integrada

## Objetivo

Esta guia describe el orden recomendado para operar el sistema integrado:

- Microservicio `cenace_scraper_service`
- Simulador desktop `energetic-marix-ec`
- Pruebas rapidas de salud

## Precondiciones

- Python 3.11+
- Entorno virtual disponible en `cenace_scraper_service/.venv`
- Dependencias instaladas en ambos componentes

## Secuencia de Arranque

1. Iniciar microservicio CENACE

```powershell
Push-Location "g:/My Drive/Universidad/10. DECIMO/Regulacion/Energetico/energetic-marix-ec/cenace_scraper_service"
& "./.venv/Scripts/python.exe" -m main
```

2. Verificar salud del microservicio

```powershell
Push-Location "g:/My Drive/Universidad/10. DECIMO/Regulacion/Energetico/energetic-marix-ec"
& "./cenace_scraper_service/.venv/Scripts/python.exe" -c "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health'))['status'])"
```

3. Iniciar simulador

```powershell
Push-Location "g:/My Drive/Universidad/10. DECIMO/Regulacion/Energetico/energetic-marix-ec"
python -m src.main
```

## Pruebas Rapidas Recomendadas

1. Pruebas de simulador + integracion local

```powershell
Push-Location "g:/My Drive/Universidad/10. DECIMO/Regulacion/Energetico/energetic-marix-ec"
& "./cenace_scraper_service/.venv/Scripts/python.exe" -m pytest tests/test_event_bus.py tests/test_scenario_manager.py tests/test_simulation_controller.py tests/test_e2e_simulation_flow.py tests/test_integration_microservice_live.py
```

2. Prueba de smoke de API del microservicio

```powershell
Push-Location "g:/My Drive/Universidad/10. DECIMO/Regulacion/Energetico/energetic-marix-ec"
& "./cenace_scraper_service/.venv/Scripts/python.exe" -m pytest tests/test_integration_microservice_live.py
```

## Operacion Segura

- Usar `AUTOMATIC` para observar estado real sincronizado.
- Cambiar a `MANUAL` antes de editar demanda o centrales.
- Guardar escenario antes y despues de cambios significativos.
- Si hay error de sincronizacion, continuar en manual con ultimo estado valido.

## Troubleshooting Basico

1. Error de conexion al microservicio
- Verificar que `http://127.0.0.1:8001/api/v1/health` responda.
- Reiniciar microservicio y luego simulador.

2. No aparecen escenarios
- Verificar carpeta `data/scenarios`.
- Guardar un escenario nuevo desde la UI para inicializar.

3. Datos no cambian en automatico
- Confirmar scheduler activo en microservicio.
- Ejecutar boton `Sincronizar ahora` en el simulador.
