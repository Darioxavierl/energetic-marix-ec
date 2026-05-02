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

## Flujo Reproducible de Sequia

1. Sincronizar en `AUTOMATIC` y guardar escenario base (ejemplo: `base_hoy`).
2. Cambiar a `MANUAL`.
3. Seleccionar una central `HYDRO` y ajustar `Embalse`.
4. Ajustar `Sequia global` para escalar el estres hidrico del sistema.
5. Confirmar en panel KPI el impacto en `Hidro MW`, `Oferta total`, `Reserva %` y `Riesgo`.
6. Si el escenario manual queda degradado por pruebas previas, usar `Reset MANUAL` para reiniciar baseline.
7. Guardar escenario variante (ejemplo: `sequia_media` o `sequia_severa`).
8. Restaurar el escenario base para comparar nuevamente.

Resultado esperado: al bajar embalse o subir sequia global, la generacion hidro debe caer de forma monotona.

## Flujo Recomendado de Analisis Visual

1. Verificar en panel de graficas el estado instantaneo (Demanda, Oferta, Balance).
2. Revisar el mix de generacion por tipo para confirmar distribucion de fuentes.
3. Usar la grafica de tendencia temporal con ventana `Ult 15` o `Ult 30` para identificar cambios recientes.
4. Correlacionar cambios de curvas con la lista de eventos (`manual_adjust`, `central_edit`, `mode_switch`, `manual_reset`).
5. Para analisis historico de sesion, volver a ventana `Sesion`.

## Troubleshooting Basico

1. Error de conexion al microservicio
- Verificar que `http://127.0.0.1:8001/api/v1/health` responda.
- Reiniciar microservicio y luego simulador.

2. No aparecen escenarios
- Verificar carpeta `data/scenarios`.
- Guardar un escenario nuevo desde la UI para inicializar.

3. Restaurar escenario no refleja cambios hidricos esperados
- Verificar que el escenario haya sido guardado despues de editar controles hidro.
- Confirmar que la restauracion se realizo en modo `MANUAL` para recomputo de KPI por catalogo local.

4. Cambio AUTOMATIC -> MANUAL cae en riesgo alto inmediatamente
- Usar `Reset MANUAL` para reconstruir baseline manual limpio.
- Verificar que `Sequia global` este en 0% antes de iniciar nuevo what-if.

5. Datos no cambian en automatico
- Confirmar scheduler activo en microservicio.
- Ejecutar boton `Sincronizar ahora` en el simulador.
