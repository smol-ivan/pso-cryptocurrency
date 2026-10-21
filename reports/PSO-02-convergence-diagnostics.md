# PSO-02 — Diagnóstico de convergencia

## Identificación, dependencias y alcance

- **ID:** PSO-02
- **Fecha:** 2026-10-20
- **Rama:** `main`, con cambios documentales preexistentes conservados.
- **Dependencias:** PSO-01 implementada y revisada; PSO-01.1 implementada y
  aprobada con observaciones en `reports/PSO-01.1-R-independent-review.md`.
- **Objetivo:** registrar estadísticas por generación y el motivo real de
  terminación sin cambiar la dinámica, la función objetivo, los parámetros
  predeterminados ni el criterio de parada.
- **Incluye:** traza agregada estable, métricas de fitness/diversidad/
  movimiento/reparación, persistencia compatible, pruebas focalizadas y
  experimentos controlados iniciales.
- **Excluye:** rediseño de Streamlit, cambios financieros, cambios de
  tolerancias/paciencia, modificación de topologías o modelos de velocidad,
  validación matemática y afirmaciones de optimalidad.

## Auditoría del flujo real

`run_analysis_pipeline()` crea `ExperimentConfig`; `run_experiments()` deriva
semillas por réplica; `run_pso()` ejecuta una optimización por target; y
`pso()` inicializa el enjambre, actualiza cada partícula, actualiza `pbest` y
`gbest`, registra historiales y devuelve el resultado. La función de fitness se
evalúa una vez al inicializar cada partícula y una vez después de cada
movimiento.

La condición existente se conserva literalmente: durante `range(max_iterations)`
se evalúa la mejora absoluta de `gbest` frente a la tolerancia
`atol + rtol * abs(gbest)`. La paciencia solo se empieza a acumular cuando
`iteration > 5`; se detiene al alcanzar `patience`. Si eso no ocurre, la
ejecución termina al agotar `max_iterations` (1000 en la API de `pso()`).
Así, `convergence_history` tiene una fila por generación completada, con índice
0-based; `diversity_history` conserva su contrato previo y contiene la
diversidad inicial más una fila por generación. Las evaluaciones de fitness no
se serializan como una historia separada.

La interfaz existente utiliza `convergence_history[:, 0]` como eje de
iteración. PSO-02 no cambia esa presentación. La nueva traza distingue
explícitamente `iterations_completed`, `termination_iteration` y
`termination_reason`, evitando interpretar el índice mostrado como número de
evaluaciones.

## Contrato de diagnóstico

`src.pso.optimizer.ConvergenceTrace` es una estructura agregada por ejecución
de un target. Tiene `schema_version=1`, una fila por generación completada y
se incorpora a `EfficientFrontier.diagnostic_histories`. La API existente de
`pso()` sigue devolviendo cuatro valores salvo que se solicite
`return_diagnostics=True`; `run_pso()` usa explícitamente esa opción.

Las métricas se definen así:

| Grupo                     | Campos y definición                                                                                                                                                                           |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fitness                   | `gbest` histórico mínimo; `current_best`, `current_mean`, `current_median`, `current_std` de las evaluaciones de la población tras moverse; `pbest_mean/std` de los mejores personales.       |
| Mejora/parada             | `improvement = abs(gbest_t - gbest_(t-1))`; `tolerance`; `patience_wait`; `last_significant_improvement` es el último índice con mejora mayor o igual que la tolerancia.                      |
| Diversidad                | `diversity` es \(N^{-1}\sum_i\|x_i-\bar{x}\|_2\); `diversity_max_distance` es el máximo; `diversity_relative` se divide por la diversidad inicial y es `NaN` cuando esta es cero.             |
| Movimiento                | `movement_mean` y `movement_max` son las distancias euclídeas entre posiciones antes/después del movimiento de la misma generación.                                                           |
| Restricciones             | `repairs` cuenta proyecciones/normalizaciones aplicadas por el modelo; `invalid_values` cuenta valores no finitos observados; `weight_sum_min/max` resume la suma de pesos.                   |
| Interpretación del target | `best_mean_return` es la media de `returns_matrix @ best_global_position`; `best_target_difference` es su distancia absoluta al target. No se introduce una nueva métrica de riesgo.          |
| Metadatos                 | `iterations_completed`, motivo `patience` o `max_iterations`, índice de terminación, diversidad inicial y configuración persistida (`rtol`, `atol`, `patience`, semilla, modelo y topología). |

La diversidad describe dispersión, no optimalidad. Una diversidad relativa no
disponible por diversidad inicial cero no se rellena artificialmente.
`repairs` incluye la normalización al simplex, incluso cuando solo corrige
diferencias numéricas de suma; por eso no debe interpretarse automáticamente
como fallo.

## Cambios realizados

| Archivo                     | Cambio                                                                                                                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/pso/optimizer.py`      | Añade `ConvergenceTrace`, captura métricas por generación, motivo/iteración de terminación y opción compatible `return_diagnostics`.                                                                                   |
| `src/pso/velocity_model.py` | Expone si la actualización aplicó proyección/normalización, sin cambiar el resultado de la reparación.                                                                                                                 |
| `src/run_pso.py`            | Transporta una traza por target en `EfficientFrontier`.                                                                                                                                                                |
| `src/persistence.py`        | Guarda diagnósticos JSON por target, declara esquema 1, los recupera y deja `None` cuando el archivo histórico no los contiene. Excluye estado runtime del RNG/contador de reparación de la configuración serializada. |
| `src/pso/__init__.py`       | Exporta el contrato `ConvergenceTrace`.                                                                                                                                                                                |
| `tests/test_pso02.py`       | Pruebas de forma, alineación, monotonicidad, diversidad/movimiento nulos, paciencia/máximo, persistencia y compatibilidad legacy.                                                                                      |
| `docs/ai/ROADMAP.md`        | Marca PSO-02 implementada y mantiene la revisión independiente pendiente.                                                                                                                                              |

No se rediseñó Streamlit. Los consumidores futuros pueden usar
`frontier.diagnostic_histories[i]` sin acceder al estado privado de partículas.

## Evidencia de pruebas

### Pasadas

| Comando                                               | Resultado                                   |
| ----------------------------------------------------- | ------------------------------------------- |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 12 pruebas ejecutadas y 12 pasadas. |
| `./.venv/bin/python -m compileall -q src tests`       | **OK**, sin errores de compilación.         |
| `git diff --check`                                    | **OK**, sin errores de whitespace.          |

Las pruebas comprueban que `gbest` no aumenta, que las métricas tienen
longitudes alineadas, que una población estática produce movimiento nulo,
que una diversidad constante se conserva, que la paciencia termina en la
generación esperada y que el máximo de iteraciones queda distinguido.
También verifican ida y vuelta de diagnósticos en `.psodata` y que un frontier
sin archivos de diagnóstico se carga con `diagnostic_histories=None`.

La comparación de trayectoria se realiza dentro de la misma ejecución: la
instrumentación se activa como una opción de retorno y las pruebas existentes
de PSO-01 siguen comparando la trayectoria de cuatro valores sin diagnóstico.
No se dispone de una versión ejecutable anterior independiente en el árbol
para una comparación bit a bit entre versiones; esta limitación queda
explícita.

## Experimento controlado inicial

Se usó una matriz sintética fija de cuatro observaciones y tres activos, la
función `Variance`, dos targets (`num_points=2`), `n_swarm=4`, `patience=10`,
semillas `[11, 12]`, ambos modelos de velocidad y ambas topologías. No se
cambiaron valores predeterminados; la matriz pequeña permite reproducir el
sondeo sin descargar datos de mercado.

| Configuración       | Punto de frontera | Iteraciones | Motivo   | Diversidad inicial → final | Movimiento final | Reparaciones |
| ------------------- | ----------------: | ----------: | -------- | -------------------------: | ---------------: | -----------: |
| Inertia/Global      |                 0 |          21 | patience |            0.1352 → 0.0000 |           0.0000 |           74 |
| Inertia/Global      |                 1 |          17 | patience |            0.0459 → 0.0226 |           0.0173 |           59 |
| Inertia/Ring        |                 0 |          18 | patience |            0.1676 → 0.0000 |           0.0000 |           58 |
| Inertia/Ring        |                 1 |          19 | patience |            0.1586 → 0.0317 |           0.0280 |           66 |
| Constriction/Global |                 0 |          17 | patience |            0.0635 → 0.0000 |           0.0000 |           60 |
| Constriction/Global |                 1 |          19 | patience |            0.1155 → 0.0661 |           0.0379 |           66 |
| Constriction/Ring   |                 0 |          16 | patience |            0.0894 → 0.0000 |           0.0000 |           52 |
| Constriction/Ring   |                 1 |          16 | patience |            0.1570 → 0.0616 |           0.0220 |           51 |

La tabla es un sondeo inicial, no una conclusión financiera. El punto 0 en
varias configuraciones muestra estancamiento con colapso de diversidad; los
otros puntos muestran terminación por paciencia mientras todavía existe
diversidad y movimiento. El hecho respaldado es la traza observada; no se
concluye que ninguna corrida sea óptima.

## Interpretación y limitaciones

- **Fitness estancado con movimiento:** aparece en targets con movimiento final
  no nulo; la población todavía se desplaza sin producir mejoras históricas.
- **Fitness estancado con diversidad decreciente:** aparece en varias corridas
  cuyo valor final llega a cero; es concentración, no prueba de optimalidad.
- **Fitness estancado con diversidad alta:** las corridas con diversidad final
  positiva conservan dispersión medible al terminar por paciencia.
- **`gbest` histórico frente a población actual:** ambos quedan separados en la
  traza; la media/mediana actual puede fluctuar aunque `gbest` solo mejore o
  permanezca.
- **Terminación temprana:** en el sondeo no ocurrió en una o dos iteraciones;
  los mínimos observados fueron 16 por la barrera de la sexta iteración y la
  paciencia 10. Un caso de una o dos iteraciones requeriría otro
  `max_iterations` o una interrupción externa.
- **Semillas:** el experimento usa `[11, 12]` y conserva trazas por réplica en
  `seed_results`; no se afirma que semillas distintas deban producir siempre
  soluciones distintas.
- **Reparaciones:** son frecuentes porque la proyección al simplex forma parte
  de cada actualización; el contador permite estudiar la relación, pero no
  demuestra causalidad de la convergencia.

No se ejecutaron descargas Yahoo Finance, Streamlit, backtesting ni una
exploración factorial amplia. Tampoco se cambió la condición de parada para
forzar ejecuciones más largas.

## Persistencia y futuro dashboard

Los resultados principales siguen siendo target, pesos, fitness e historiales
existentes. El diagnóstico avanzado se persiste como JSON agregado por target,
no como estado completo de cada partícula: conserva una fila por generación
con las métricas anteriores y metadatos de terminación. Los resultados por
semilla siguen bajo `seed_results` y `seed_values`.

Los `.psodata` anteriores que no contienen `diagnostics_*.json` se cargan sin
error y exponen el diagnóstico como no disponible. No se reconstruyen campos
ausentes. La revisión de persistencia también corrigió la serialización
accidental del generador runtime y de `last_repaired`, que no son configuración
efectiva.

## Criterios de aceptación

| Criterio                                              | Estado                                                                           | Evidencia                                                                             |
| ----------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Motivo de terminación explícito                       | Cumplido                                                                         | `ConvergenceTrace.termination_reason` y pruebas de paciencia/máximo.                  |
| Iteraciones, historiales y evaluaciones diferenciados | Cumplido                                                                         | Auditoría de flujo y campos `iterations_completed`; longitudes probadas/documentadas. |
| Fitness, diversidad y movimiento definidos y probados | Cumplido                                                                         | Contrato, fórmulas y `tests/test_pso02.py`.                                           |
| Distinguir estancamiento, concentración y movimiento  | Cumplido                                                                         | Experimento controlado y tabla de escenarios.                                         |
| No alterar trayectoria matemática                     | Cumplido dentro de la versión actual; comparación legacy bit a bit no disponible | API compatible por defecto, pruebas PSO-01 verdes y sin sorteos nuevos.               |
| Evidencia reproducible de experimentos iniciales      | Cumplido                                                                         | Matriz, configuración, semillas y salida resumida documentadas.                       |
| Estructura consumible por futuros análisis/Streamlit  | Cumplido                                                                         | `ConvergenceTrace` y `diagnostic_histories` documentados.                             |
| Separar evidencia de hipótesis                        | Cumplido                                                                         | Secciones de interpretación y limitaciones.                                           |
| Revisión independiente                                | Pendiente                                                                        | Debe permanecer pendiente en roadmap.                                                 |

## Siguiente paso

Solicitar una revisión independiente de solo lectura del diff, las pruebas, la
persistencia y este reporte. PSO-03 no debe iniciarse hasta que PSO-02 quede
revisada según el roadmap.
