# Manual de Usuario del Simulador

## 1. Objetivo del Manual

Este manual explica:

- Que hace cada control de la aplicacion.
- Como usar los flujos principales.
- Como cada accion afecta al modelo de simulacion y a los KPI.

## 2. Conceptos Clave

- Modo `AUTOMATIC`: estado alimentado por microservicio, sin edicion operativa.
- Modo `MANUAL`: estado congelado editable para escenarios what-if.
- KPI: oferta total, balance, margen de reserva y riesgo.

## 3. Estructura de la Pantalla

1. Mapa
- Muestra centrales por ubicacion.
- Tamano/brillo del marcador reflejan utilizacion estimada.
- Popup muestra datos por central.

2. Leyenda Operativa
- Resume MW y utilizacion por tecnologia: HYDRO, THERMAL, WIND, SOLAR.

3. Panel de Control
- Estado de sincronizacion.
- Cambio de modo.
- Ajuste de demanda.
- Gestion de escenarios.
- Detalle editable de central.

## 4. Controles y Efecto en el Modelo

1. Sincronizar ahora
- Accion: consulta endpoints del microservicio.
- Efecto: actualiza `SimulationState` en modo automatico.
- KPI afectados: todos.

2. Cambiar a MANUAL / AUTOMATIC
- Accion: transicion de modo.
- Efecto:
  - `AUTOMATIC`: lectura de datos externos.
  - `MANUAL`: habilita edicion local.
- KPI afectados: indirectamente en siguientes cambios.

3. Ajuste de demanda (% demanda)
- Accion: incrementa o reduce demanda en porcentaje.
- Efecto: modifica `state.demand_mw` en manual.
- KPI afectados:
  - balance = oferta - demanda
  - reserva = (oferta - demanda)/demanda
  - riesgo derivado de reserva

4. Detalle de central: Disponible MW y Estado
- Accion: edicion de la central seleccionada en manual.
- Efecto: actualiza capacidades/estado local usados en overlay de mapa.
- KPI afectados: principalmente representacion operativa por planta y consistencia del escenario; el KPI agregado de oferta depende de estado sintetico del `SimulationState`.

5. Escenarios: Guardar
- Accion: persiste snapshot de estado actual.
- Efecto: crea archivo JSON en `data/scenarios`.

6. Escenarios: Restaurar
- Accion: carga snapshot persistido.
- Efecto: reemplaza `SimulationState` activo por el guardado.
- KPI afectados: se restauran exactamente los del snapshot.

7. Escenarios: Duplicar
- Accion: copia de escenario seleccionado.
- Efecto: crea variante para experimentar sin perder base.

8. Escenarios: Descartar
- Accion: elimina escenario seleccionado.
- Efecto: borra archivo de escenario; no modifica estado actual en memoria.

## 5. Flujo Recomendado de Uso

1. Iniciar microservicio y simulador.
2. Verificar estado `AUTOMATIC` y sincronizacion correcta.
3. Guardar escenario base (ejemplo: `base_hoy`).
4. Cambiar a `MANUAL`.
5. Ajustar demanda y centrales.
6. Evaluar KPI y riesgo.
7. Guardar variante (ejemplo: `escasez_hidro`).
8. Restaurar `base_hoy` para comparar.

## 6. Interpretacion de KPI

1. Oferta total MW
- Potencia neta disponible del sistema sintetizado.

2. Balance MW
- Positivo: superavit.
- Negativo: deficit.

3. Reserva %
- Valor clave para estabilidad operativa.
- Menor reserva implica mayor riesgo.

4. Riesgo
- SAFE, ALERT, CRITICAL, FAILURE segun umbrales de reserva.

## 7. Buenas Practicas

- No mezclar analisis manual con datos automaticos sin guardar snapshots intermedios.
- Nombrar escenarios con convencion clara: `fecha_contexto_objetivo`.
- Validar estado del microservicio antes de iniciar sesiones de analisis.

## 8. Limitaciones Actuales

- El mapeo de nombres de plantas CENACE a catalogo local usa heuristicas; algunos casos requieren alias explicitos.
- Persistencia de escenarios en JSON sin versionado de esquema.
- Algunas metricas agregadas no representan flujo electrico completo AC; son metricas operativas simplificadas.

## 9. Glosario Rapido

- Snapshot: captura completa de estado en un instante.
- What-if: simulacion de escenario hipotetico.
- Reserva operativa: margen de oferta sobre demanda.
- Fallback: continuar con ultimo estado valido ante error externo.
