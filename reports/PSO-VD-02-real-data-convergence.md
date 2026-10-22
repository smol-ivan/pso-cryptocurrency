# PSO-VD-02 — Diagnóstico experimental de convergencia con datos reales

## 1. Objetivo, estado y alcance

- **ID:** PSO-VD-02
- **Fecha:** 2026-10-22
- **Rama:** `main`
- **Estado:** implementado; revisión independiente pendiente.
- **Objetivo:** ampliar el dashboard independiente de validación con un
  diagnóstico de mercado ejecutable únicamente mediante una acción explícita.
- **Incluido:** carga mediante `src.utils.load_crypto_returns`, ejecución
  reproducible Ring/Global, métricas ya expuestas por `ConvergenceTrace`,
  descomposición CVaR/penalización, pesos finales, casos extremos descriptivos,
  pruebas con descargas simuladas y manejo de errores.
- **Excluido:** cambios en `app.py`, el algoritmo PSO, topologías, función de
  fitness, fórmulas financieras, persistencia de resultados, descargas
  automáticas al cargar y commits.

No se ejecutó una descarga real contra Yahoo Finance durante esta tarea. Por
tanto, no se presentan resultados financieros observados ni se afirma haber
validado convergencia con datos de mercado.

## 2. Archivos modificados

| Archivo | Cambio |
|---|---|
| `validation_dashboard.py` | Sección independiente de mercado, botón explícito, metadatos, gráficas y estado de error. |
| `validation_dashboard_logic.py` | Configuración fija, cargador existente, ejecuciones emparejadas, descomposición y catálogo de casos extremos. |
| `tests/test_validation_dashboard.py` | Pruebas de carga diferida, transformaciones, comparabilidad, errores, diagnósticos y casos extremos. |
| `reports/PSO-VD-02-real-data-convergence.md` | Este informe. |

El cambio preexistente en `artifacts/experiments.psodata` se conservó sin
modificarlo. No se actualizó `docs/ai/ROADMAP.md` porque el alcance solicitado
prohíbe modificar el roadmap.

## 3. Configuración efectiva

La configuración fue contrastada con `app.py`, `experiment_controller.py`,
`experiments.py`, `run_pso.py`, `fitness_function.py` y `utils.py`.

| Parámetro | Valor |
|---|---|
| Activos | BTC-USD, ETH-USD, SOL-USD, ADA-USD |
| Fechas solicitadas | 2020-01-01 a 2024-01-01 |
| Intervalo | `1d` |
| Datos | `Close` de `yfinance`, retornos `log(close / close.shift(1))`, `dropna()` |
| Fitness | CVaR |
| Alpha | 0.95 |
| Penalización | 500.0 |
| Velocidad | Inertia, `c1=1.7`, `c2=1.7`, `w=0.8` |
| Partículas | 100 |
| `rtol`, `atol`, paciencia | `1e-4`, `1e-8`, 10 |
| Máximo efectivo | 1000 iteraciones, implícito en `pso()` |
| Topologías | Ring (`k_neighbors=1`) y Global |
| Semillas | 42, 43 y 44, compartidas por ambas topologías |

La aplicación principal usa 30 puntos de frontera. Esta sección ejecuta dos
targets sobre la misma matriz: `minimum = min(media_por_activo)` y
`intermediate = (min(media_por_activo) + max(media_por_activo)) / 2`. El
selector de la interfaz permite revisar cada objetivo por separado y la
reducción no modifica la configuración de producción.

## 4. Datos y metadatos

`run_market_diagnostic()` llama al cargador existente solo cuando se invoca.
Valida que la matriz sea `T x N`, finita, no vacía, que sus medias coincidan
con las columnas y que el índice temporal coincida con `T`. La interfaz
muestra:

- activos;
- fechas solicitadas y fechas realmente disponibles;
- número de observaciones;
- intervalo;
- timestamp UTC posterior a la recuperación;
- parámetros PSO, semillas, target y penalización.

Como no se ejecutó el botón contra la red, las fechas disponibles y el número
de observaciones efectivos quedan pendientes de la primera ejecución manual.
La prueba automatizada usa una matriz simulada de cinco observaciones y no se
presenta como dato de mercado.

## 5. Métricas disponibles y definiciones

Las métricas proceden de `ConvergenceTrace` y se registran después de actualizar
las posiciones en cada iteración; no existe una fila observada para el estado
inicial antes del primer movimiento.

| Métrica | Definición y unidades |
|---|---|
| `gbest` | Mejor fitness global acumulado; CVaR positivo más penalización por brecha de retorno. |
| `current_best/mean/...` | Estadísticos del fitness calculado para la generación actual. |
| `improvement`, `tolerance` | Mejora absoluta de `gbest` y umbral `atol + rtol*abs(gbest)`. |
| `diversity` | Distancia euclídea media de las posiciones al centroide, en unidades de peso. |
| `diversity_relative` | Diversidad dividida por la diversidad inicial. |
| `movement_mean/max` | Movimiento euclídeo medio/máximo de posiciones frente a la posición previa. |
| `repairs` | Cantidad de partículas cuya posición fue modificada por `_repair_position`. |
| `best_target_difference` | Brecha absoluta entre retorno medio del mejor `gbest` y el target, por observación logarítmica. |
| `weight_sum_min/max` | Mínimo y máximo de la suma de pesos de la población. |
| `invalid_values` | Conteo de valores no finitos en posiciones, velocidades y fitness. |
| `termination` | Motivo devuelto por el optimizador: `patience` o `max_iterations`. |

La magnitud de la corrección, vectores degenerados por iteración y reparación
de velocidad no están instrumentados. `repairs` no se interpreta como
reparación de velocidad ni como medida de magnitud.

## 6. Visualizaciones

La sección muestra, para el objetivo, topología y semilla seleccionados:

1. mejor fitness global por iteración;
2. diversidad y movimiento medio en unidades euclídeas de pesos;
3. brecha absoluta al target;
4. cantidad de partículas reparadas;
5. pesos finales, peso máximo y cantidad de pesos `>= 0.95`;
6. descomposición de retorno medio, target, CVaR, penalización y fitness total.

Las curvas se etiquetan como posteriores al movimiento. Las tres semillas se
comparten entre Ring y Global dentro de cada objetivo, y ambos objetivos usan
la misma matriz y parámetros. Esto permite una comparación descriptiva
emparejada entre topologías y una inspección separada del extremo mínimo frente
al caso intermedio, no una conclusión de superioridad general.

## 7. Casos extremos

Se añadió un catálogo separado de expectativas para:

- vector cero;
- pesos negativos;
- suma distinta de uno;
- vértices del simplex;
- target mínimo, máximo e intermedio;
- target fuera del rango;
- concentración fuerte;
- fitness estable al inicio;
- retornos constantes;
- repetición exacta.

Cada caso queda clasificado como inválido, extremo válido o escenario difícil
de optimización. El catálogo no convierte estos casos en evidencia financiera
ni cambia la política de reparación. En particular, el target fuera de rango
se conserva y se señala como difícil; no se recorta silenciosamente.

## 8. Resultados por topología y semilla

No hay resultados reales por topología/semilla que reportar porque no se
ejecutó la descarga de mercado. La ruta implementada producirá doce
ejecuciones: Ring y Global para cada una de las semillas 42, 43 y 44, tanto
para el target mínimo como para el target intermedio, con la misma matriz de
retornos.

La prueba con datos simulados verificó que las seis llamadas conservan las
semillas emparejadas, alternan Ring/Global, usan una matriz válida y asocian
las trazas a la ejecución correspondiente. No se extrapola ese resultado a
Yahoo Finance.

## 9. Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 12 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 34 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `git diff --check` | **OK** |
| `git status --short --branch` | **OK**, `main`, cambio preexistente en `artifacts/experiments.psodata` conservado |

Las pruebas de Streamlit emitieron advertencias normales de ejecución sin
`ScriptRunContext` y deprecación de `use_container_width`; no fueron fallos.
Las descargas se mockearon; no se usó Yahoo Finance ni la red.

## 10. Limitaciones y preguntas pendientes

1. Ejecutar manualmente el botón y registrar las fechas/observaciones reales y
   los seis resultados, sin confundirlos con una prueba automatizada.
2. Decidir si una futura tarea requiere instrumentar la magnitud de reparación
   y los vectores degenerados sin alterar la estrategia.
3. Evaluar si el diagnóstico debe cubrir todos los 30 targets de la frontera,
   manteniendo el target único actual como experimento acotado.
4. La traza no devuelve estadísticas por generación antes de la actualización
   ni un historial de posiciones completo.
5. No se afirma optimalidad global, causalidad, validez financiera ni
   superioridad de topologías.

## 11. Integridad del algoritmo y fórmulas

No se modificaron las ecuaciones de velocidad, topologías, condiciones de
parada, reparación de posiciones, funciones CVaR, VaR, drawdown,
anualización ni otras fórmulas financieras. El diagnóstico reutiliza la
instrumentación existente y calcula la descomposición con la misma convención
de `CVaR(alpha, penalty=0)` más `penalty * abs(mean_return - target)`.

## 12. Criterios de finalización

| Criterio | Estado |
|---|---|
| Sección independiente y botón explícito | Cumplido |
| Sin carga/PSO al importar o abrir | Cumplido por pruebas de importación y flujo inicial |
| Ejecución reproducible con parámetros y semillas | Cumplido |
| Métricas de convergencia, diversidad, movimiento, target y reparaciones | Cumplido en la medida de `ConvergenceTrace` |
| Casos extremos separados | Cumplido como catálogo de expectativas |
| Errores sin resultados obsoletos | Cumplido y probado para sintético y mercado |
| Suite previa conservada | Cumplido en la ejecución disponible |
| Informe y limitaciones explícitas | Cumplido |
| Evidencia de ejecución real contra mercado | No ejecutada |
| Revisión independiente | Pendiente |

No se considera validada la convergencia financiera por la implementación del
dashboard. La revisión independiente posterior debe evaluar el código, la
evidencia y la eventual ejecución real.
