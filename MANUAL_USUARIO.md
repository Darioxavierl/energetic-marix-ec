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

4. Panel de Graficas (lado derecho)
- Estado operativo instantaneo: demanda, oferta y balance.
- Mix de generacion por tipo: HYDRO, THERMAL, RENEWABLE.
- Comparativo demanda vs oferta y barra de reserva/import/export.
- Tendencia temporal con selector de ventana (`Sesion`, `Ult 60`, `Ult 30`, `Ult 15`).
- Lista de eventos recientes de simulacion (manual_adjust, central_edit, mode_switch, manual_reset, scenario_load).

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
- Efecto: actualiza capacidades/estado local y dispara recomputo inmediato de generacion agregada.
- KPI afectados: `hydro_mw`, `thermal_mw`, `renewable_mw`, oferta total, balance, reserva y riesgo en el mismo ciclo de UI.

5. Controles hidricos por central (solo HYDRO en modo MANUAL)
- Variables:
  - `Embalse (%)`
- Efecto: modifica la generacion hidro de la central seleccionada.
- KPI afectados: reduccion o aumento de generacion hidro efectiva y, por arrastre, de oferta/balance/reserva/riesgo.

6. Sequia global
- Accion: slider global (0% a 100%) en modo manual.
- Efecto: aplica penalizacion hidrica comun a todas las centrales hidro.
- KPI afectados: generacion hidro agregada y riesgo del sistema.

7. Escenarios: Guardar
- Accion: persiste snapshot de estado actual.
- Efecto: crea archivo JSON en `data/scenarios` con version de esquema y catalogo operativo de centrales (incluye embalse por central hidro y excluye campos legacy de caudal/sequia local).

8. Escenarios: Restaurar
- Accion: carga snapshot persistido.
- Efecto: restaura `SimulationState` y, si existe en el escenario, restaura tambien el estado operativo de centrales (capacidad, estado, embalse).
- KPI afectados: se restauran exactamente los del snapshot.

11. Reset MANUAL
- Accion: restablece baseline manual durante sesion.
- Efecto: recarga catalogo base de centrales y reinicia sequia global a 0%.
- KPI afectados: recalculo completo inmediato con baseline limpio.

12. Selector de ventana temporal (Panel de graficas)
- Accion: limita cantidad de puntos visibles en la grafica de tendencia.
- Efecto: facilita lectura de cambios recientes sin perder historial completo de sesion.

13. Marcadores/lista de eventos (Panel de graficas)
- Accion: visualiza eventos operativos relevantes sobre la tendencia y en lista auxiliar.
- Efecto: permite correlacionar saltos de demanda/oferta con acciones del usuario o transiciones de modo.

9. Escenarios: Duplicar
- Accion: copia de escenario seleccionado.
- Efecto: crea variante para experimentar sin perder base.

10. Escenarios: Descartar
- Accion: elimina escenario seleccionado.
- Efecto: borra archivo de escenario; no modifica estado actual en memoria.

## 5. Flujo Recomendado de Uso

1. Iniciar microservicio y simulador.
2. Verificar estado `AUTOMATIC` y sincronizacion correcta.
3. Guardar escenario base (ejemplo: `base_hoy`).
4. Cambiar a `MANUAL`.
6. Ajustar demanda, disponibilidad de centrales, embalse por central hidro y sequia global.
7. Usar `Reset MANUAL` si se desea reiniciar el escenario manual sin volver a abrir la aplicacion.
8. Evaluar KPI y riesgo.
9. Guardar variante (ejemplo: `escasez_hidro`).
10. Restaurar `base_hoy` para comparar.

## 6. Modelo Hidrico Simplificado

La generacion hidro por central se estima como:

$$
P_{hidro} = P_{disponible} \times F_{hidraulico}
$$

donde $F_{hidraulico}$ depende de:

- nivel de embalse
- sequia global

Todos los factores se acotan al rango $[0,1]$ para mantener estabilidad numerica.

## 7. Interpretacion de KPI

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

## 8. Buenas Practicas

- No mezclar analisis manual con datos automaticos sin guardar snapshots intermedios.
- Nombrar escenarios con convencion clara: `fecha_contexto_objetivo`.
- Validar estado del microservicio antes de iniciar sesiones de analisis.
- Para analisis de sequia, variar una sola variable por iteracion y guardar escenarios intermedios comparables.

## 9. Limitaciones Actuales

- El mapeo de nombres de plantas CENACE a catalogo local usa heuristicas; algunos casos requieren alias explicitos.
- Modelo hidrico simplificado: no modela dinamica temporal horaria de recarga de embalse.
- Algunas metricas agregadas no representan flujo electrico completo AC; son metricas operativas simplificadas.

## 10. Glosario Rapido

- Snapshot: captura completa de estado en un instante.
- What-if: simulacion de escenario hipotetico.
- Reserva operativa: margen de oferta sobre demanda.
- Fallback: continuar con ultimo estado valido ante error externo.
