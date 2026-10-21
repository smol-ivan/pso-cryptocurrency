# PSO-02-R — Revisión independiente de instrumentación y diagnóstico de convergencia

## 1. Identificación, alcance y estado inicial

- **ID:** PSO-02-R.
- **Fecha:** 2026-10-20.
- **Rama:** `main`, `ahead 2` respecto de `origin/main`.
- **Objetivo:** revisar de forma independiente la instrumentación de PSO-02,
  sus métricas, terminación, persistencia y evidencia experimental, sin
  modificar el algoritmo ni iniciar PSO-03.
- **Alcance incluido:** implementación y pruebas de PSO-02, persistencia
  `.psodata`, consumidores actuales, reportes de PSO-01/PSO-01.1 y
  comparación de trayectorias disponible en el árbol.
- **Alcance excluido:** correcciones de código, cambios de pruebas o
  resultados, rediseño de Streamlit, validación matemática/financiera y
  commits.

Se leyeron `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`, `docs/ai/WORK_PROTOCOL.md`, `reports/README.md`,
`docs/ai/prompts/PSO-02.md`, los reportes de implementación y revisión de
PSO-01 y PSO-01.1, el informe de implementación de PSO-02 y los archivos
modificados de `src/`, `tests/` y persistencia. No faltó ninguno de los
informes obligatorios indicados para esta revisión.

El árbol ya contenía cambios de PSO-02 y los reportes/pruebas sin seguimiento.
También estaban modificados `docs/ai/ROADMAP.md` y
`docs/ai/prompts/PSO-02.md`; se conservaron. Esta revisión solo añade este
reporte y actualiza el estado de PSO-02 en el roadmap.

## 2. Estado de Git observado

Comando:

```text
git status --short --branch --untracked-files=all
```

Resultado:

```text
## main...origin/main [ahead 2]
 M docs/ai/ROADMAP.md
 M docs/ai/prompts/PSO-02.md
 M src/persistence.py
 M src/pso/__init__.py
 M src/pso/optimizer.py
 M src/pso/velocity_model.py
 M src/run_pso.py
?? reports/PSO-01.1-R-independent-review.md
?? reports/PSO-02-convergence-diagnostics.md
?? tests/test_pso02.py
```

No se descartaron ni sobrescribieron esos cambios. No se creó ningún commit.

## 3. Comandos y comprobaciones ejecutados

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 12 pruebas ejecutadas y 12 pasadas. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |
| Sondeo con generadores idénticos y `return_diagnostics=False/True` | **OK**, fitness, posición, historial de convergencia e historial de diversidad idénticos. |
| Sondeo de diversidad y movimiento con estados pequeños conocidos | **OK**, la diversidad corresponde a la distancia media al centroide y el movimiento a la distancia entre posiciones antes/después. |
| Sondeo de persistencia con dos semillas | **OK**, `seed_values=[41, 42]` y diagnósticos anidados recuperados para ambas réplicas. |
| Revisión de diff, consumidores UI y referencias de esquema | Sin cambios fuera del alcance funcional documentado; la UI existente continúa consumiendo los historiales anteriores. |

No se ejecutaron Yahoo Finance, Streamlit, backtesting ni una exploración
factorial amplia. Tampoco se modificó el código para fabricar casos de prueba.

## 4. Revisión técnica

### 4.1 Métricas y fase de captura

`ConvergenceTrace` ofrece un contrato agregado versionado (`schema_version=1`)
con una fila por generación completada
(`src/pso/optimizer.py:14-45`). El estado inicial se conserva por separado:
`diversity_history` tiene una entrada inicial y una por generación, mientras
que la traza diagnóstica comienza después del movimiento de la primera
generación. Esta convención es coherente con el flujo observado
(`src/pso/optimizer.py:172-200`) y evita mezclar el estado inicial con
estadísticas de una generación completada.

La optimización es de **minimización**: las comparaciones de `pbest` y `gbest`
usan `<` (`src/pso/optimizer.py:186-193`), por lo que `gbest` es no creciente.
La prueba automatizada confirma esa dirección. `current_best`, media, mediana
y desviación estándar se calculan sobre las evaluaciones de la población
después del movimiento; `pbest_mean/std` se calculan después de actualizar los
mejores personales. La separación entre fitness actual e histórico es
correcta y el sondeo mostró que no son conceptualmente intercambiables.

La mejora histórica es `abs(gbest_t - gbest_(t-1))` y la tolerancia es
`atol + rtol * abs(gbest_t)` (`src/pso/optimizer.py:201-215`). Esto coincide
con la condición de parada existente y no altera su dirección ni su umbral.
La paciencia se actualiza después de registrar la fila y se corrige en la
misma fila al alcanzar el umbral (`src/pso/optimizer.py:236-248`).

La diversidad implementa exactamente:

\[
D_t = \frac{1}{N}\sum_i \lVert x_{i,t}-\bar{x}_t\rVert_2
\]

mediante `distances.mean()` (`src/pso/optimizer.py:197-218,
294-298`). `diversity_max_distance` y la diversidad relativa tienen la
interpretación documentada. Cuando la diversidad inicial es cero, la relativa
queda como `NaN`; no se inventa un cero.

El movimiento compara copias de las posiciones al comienzo de la generación
con las posiciones después de actualizar y reparar las partículas
(`src/pso/optimizer.py:172-199`). El sondeo independiente produjo valores
conocidos no nulos y confirmó que la media y el máximo son distancias
euclídeas por partícula. El cálculo no consume aleatoriedad.

El contador `repairs` se basa en `last_repaired`, que informa si la
proyección/normalización cambió el vector (`src/pso/velocity_model.py:20-36`).
Es una cuenta de proyecciones aplicadas, no una cuenta de errores excepcionales.
La suma de pesos se observa después de reparar. `invalid_values` cuenta
valores no finitos en posiciones, velocidades y fitness después de la
evaluación (`src/pso/optimizer.py:221-228`).

El rendimiento medio del mejor portafolio y su distancia al target se calculan
con `returns_matrix @ best_global_position` (`src/pso/optimizer.py:232-234`).
No se introduce una nueva convención financiera. No se registra por separado
el componente de riesgo de la función objetivo; esto es aceptable para el
alcance de convergencia, pero limita la interpretación financiera del fitness.

### 4.2 Terminación, contadores y ejecuciones prematuras

La condición de parada permanece en `iteration > 5`, `improvement <
tolerance` y paciencia acumulada; la instrumentación solo registra el flujo
(`src/pso/optimizer.py:236-248`). Se distinguen:

- `termination_reason="patience"` al alcanzar el contador.
- `termination_reason="max_iterations"` si se agota el rango.
- `termination_iteration` como índice 0-based de la última generación
  completada.
- `iterations_completed` como cantidad de filas de la traza.

Las pruebas verifican tanto paciencia como máximo de iteraciones
(`tests/test_pso02.py:67-87`). Por tanto, una corrida terminada en una o dos
iteraciones no puede atribuirse aquí a paciencia bajo la regla actual: la
paciencia no comienza antes de la sexta iteración. El informe de implementación
lo explica correctamente. No hay evidencia para afirmar optimalidad ni para
determinar una causa externa de una ejecución prematura que no aparezca en
esta traza.

### 4.3 ¿La instrumentación altera el algoritmo?

La comparación directa entre dos ejecuciones actuales con los mismos datos,
semillas y configuración, una con `return_diagnostics=False` y otra con
`return_diagnostics=True`, dio igualdad exacta de los cuatro valores devueltos:
fitness, posición, convergencia y diversidad. El diff muestra que las
estadísticas se calculan a partir de posiciones, velocidades y fitness ya
producidos; no añade sorteos ni llamadas al generador.

No fue posible una comparación bit a bit contra un ejecutable histórico
independiente, porque PSO-01.1 ya es la base de la versión actual y no existe
un artefacto anterior ejecutable separado en el árbol. La evidencia alternativa
es fuerte para no introducir consumo aleatorio en la ruta instrumentada, pero
no demuestra compatibilidad binaria entre versiones.

### 4.4 Persistencia y consumidores

Los diagnósticos se guardan como JSON agregado por target y las trazas de
réplicas se guardan bajo `seed_results`
(`src/persistence.py:217-260`). La recuperación convierte las series a
`numpy.ndarray` y deja `diagnostic_histories=None` cuando el archivo antiguo
no contiene diagnósticos (`src/persistence.py:322-383`). El sondeo con dos
semillas confirmó la recuperación de los diagnósticos anidados y sus semillas.

La estructura `EfficientFrontier.diagnostic_histories` es consumible sin
acceder a partículas privadas (`src/run_pso.py:16-27, 65-107`). La UI actual
continúa usando `convergence_histories`; no se añadió un rediseño ni se rompió
ese consumidor. Persistir métricas agregadas, en lugar del estado completo de
cada partícula, es una decisión razonable de coste, aunque el tamaño total
crece linealmente con targets, generaciones y réplicas.

## 5. Hallazgos por severidad

| ID | Severidad | Ubicación | Evidencia observada | Impacto | Criterio afectado | Acción recomendada |
|---|---|---|---|---|---|---|
| PSO-02-R-01 | **Media** | `src/experiments.py:10-25`, `src/run_pso.py:38-50`, `src/pso/optimizer.py:105` | `ExperimentConfig` y `run_pso()` no tienen un campo `max_iterations`; las ejecuciones de experimentos usan implícitamente el valor por defecto `1000` de `pso()`. `ConvergenceTrace` tampoco contiene la configuración efectiva completa. | Un consumidor no puede distinguir desde el resultado persistido si `1000` fue una decisión efectiva o un valor implícito, y el análisis de ejecuciones cortas depende de inspección externa del código. | Metadatos/configuración efectiva y contraste entre configuración, historiales y motivo de terminación. | En una tarea posterior, hacer explícito `max_iterations` en el contrato de configuración o documentar formalmente el valor fijo; incorporar metadatos de ejecución completos sin cambiar la regla de parada. |
| PSO-02-R-02 | **Baja** | `tests/test_pso02.py:41-65` | La suite prueba diversidad constante y movimiento nulo, pero no aserta un caso no nulo conocido ni diferencia explícitamente `current_best` frente a `gbest`. Los sondeos independientes sí verificaron las fórmulas. | Una regresión parcial en las fórmulas podría no ser detectada por la suite automatizada. | Métricas definidas y probadas en casos conocidos. | Añadir casos deterministas de diversidad/movimiento no nulos y una aserción de fitness actual frente a histórico en una ampliación de cobertura. |
| PSO-02-R-03 | **Baja** | `src/pso/optimizer.py:180-228` | `invalid_values` solo se registra después de que la reparación y `_validate_fitness()` hayan rechazado valores no finitos. En una ejecución que termina correctamente, normalmente será cero; no diagnostica una ruta abortada por valores inválidos. | El campo puede interpretarse como “no hubo valores inválidos” cuando en realidad la ejecución inválida no produce una fila diagnóstica. | Presencia de valores no finitos y separación entre error e interpretación normal de convergencia. | Documentar el campo como conteo de valores no finitos observados en generaciones completadas y mantener errores inválidos como estados separados; no convertir errores en convergencia. |
| PSO-02-R-04 | **Baja** | `reports/PSO-02-convergence-diagnostics.md:110-159` | El experimento inicial usa dos semillas, una matriz pequeña, una población y dos targets; compara modelos y topologías, pero no cuantifica sensibilidad ni permite conclusiones generales entre semillas. | La tabla respalda un sondeo diagnóstico inicial, no estabilidad, superioridad de configuraciones ni convergencia global. | Evidencia experimental proporcional a las afirmaciones y separación entre observación e hipótesis. | Mantener las conclusiones limitadas a observaciones; ampliar semillas/poblaciones y registrar preguntas factor por factor antes de afirmaciones generales. |
| PSO-02-R-05 | **Baja** | Reporte de PSO-02, sección de trayectoria | No existe una versión histórica independiente ejecutable para comparación bit a bit. La igualdad entre retorno instrumentado/no instrumentado valida la versión actual, no compatibilidad entre versiones. | Queda sin demostrar la equivalencia con cualquier implementación pre-PSO-02 fuera de la ruta actual. | Verificación de que la instrumentación no cambia la trayectoria. | Conservar la limitación y, si se necesita compatibilidad histórica, ejecutar una referencia congelada en una tarea separada. |

No se encontraron hallazgos bloqueantes ni de severidad alta. No observé cambios
no autorizados en la función objetivo, penalización, ecuaciones financieras,
ecuaciones de movimiento, topologías, parámetros predeterminados, tolerancias,
paciencia, condición de parada o política de reparación. La modificación de
`_repair_position()` conserva la salida matemática y añade únicamente el
indicador de reparación.

## 6. Evaluación del diagnóstico experimental

### Observaciones respaldadas

- `gbest` histórico es monótono no creciente; las métricas de población actual
  se registran por separado.
- La diversidad y el movimiento son métricas distintas: se observan casos con
  movimiento final no nulo y diversidad final positiva o nula.
- La tabla de PSO-02 contiene ambos modelos de velocidad, ambas topologías,
  dos targets y semillas `[11, 12]`, con motivo, iteraciones, diversidad,
  movimiento y reparaciones.
- La terminación observada en el sondeo es por paciencia, no por una afirmada
  optimalidad.

### Interpretaciones permitidas

Fitness estancado con diversidad decreciente es compatible con concentración;
fitness estancado con movimiento persistente es compatible con exploración sin
mejora; diversidad positiva al terminar es compatible con población todavía
dispersa. Ninguna de esas observaciones demuestra óptimo global, frontera
eficiente ni superioridad de un modelo.

### Lo que no queda demostrado

Dos semillas no permiten cuantificar robustez o sensibilidad estadística. La
matriz no contiene un segundo tamaño de población ni una fase de sensibilidad
controlada. Tampoco permite separar causalmente el efecto de reparaciones,
penalización, diversidad y semilla. Las conclusiones del informe son válidas
solo como diagnóstico inicial y deben conservar ese alcance.

## 7. Criterios de aceptación

| Criterio | Evaluación independiente |
|---|---|
| Motivo de terminación explícito | **Cumplido**: razón, índice y contador están en la traza y se probaron ambos caminos. |
| Diferencia entre iteraciones, historiales y evaluaciones | **Cumplido con observación**: la convención es coherente, pero `max_iterations` no queda explícito en el contrato de experimento. |
| Fitness, diversidad y movimiento definidos y probados | **Cumplido con observación**: implementación correcta; faltan casos no nulos en la suite automatizada. |
| Distinguir estancamiento, concentración y movimiento | **Cumplido para el sondeo inicial**, sin inferencia de optimalidad. |
| No alterar la trayectoria matemática | **Cumplido dentro de la versión actual**; no demostrable bit a bit frente a una versión histórica independiente. |
| Evidencia reproducible de experimentos iniciales | **Cumplido para diagnóstico inicial**, insuficiente para generalizaciones entre semillas o configuraciones. |
| Estructura consumible por futuros análisis/Streamlit | **Cumplido con observación**: `EfficientFrontier` y persistencia son utilizables, pero falta metadato explícito de `max_iterations`. |
| Separación de evidencia e hipótesis | **Cumplido** en el reporte de implementación y confirmado por esta revisión. |

## 8. Limitaciones de esta revisión

- No se validaron optimalidad, referencias sintéticas, convenciones financieras,
  backtesting ni calidad de frontera; pertenecen a fases posteriores.
- No se ejecutaron Streamlit ni descargas externas.
- No se revisó un archivo histórico real de `.psodata` fuera de fixtures
  construidas por las pruebas; sí se verificó la ruta de compatibilidad de
  ausencia de diagnósticos y la persistencia de dos semillas.
- Los sondeos complementarios no se incorporaron como pruebas del repositorio.
- El estado de Git incluía cambios de implementación y documentación de la
  tarea; se trataron como entrada de revisión y no se alteraron.

## 9. Veredicto y recomendación

**Aprobado con observaciones.**

Los criterios esenciales de PSO-02 se cumplen: las métricas se calculan desde
el estado real después de cada generación, la convención de minimización y la
monotonicidad de `gbest` son coherentes, la terminación conserva sus reglas,
la trayectoria actual no cambia al activar el diagnóstico, los resultados se
persisten de forma compatible y el experimento inicial separa observaciones de
hipótesis. Las observaciones son de contrato explícito, cobertura y fuerza
experimental; no hay un defecto que obligue a rechazar PSO-02.

PSO-02 **puede cerrarse como revisada con observaciones y permite avanzar a
PSO-03**, siempre que las tareas siguientes no traten el sondeo como prueba de
optimalidad ni de robustez estadística. Antes de usar los diagnósticos como
base de conclusiones generales o de un dashboard avanzado, debe hacerse
explícito el `max_iterations` efectivo, mantener separadas las ejecuciones
inválidas de las convergentes y ampliar la cobertura/replicación experimental.
No se inicia PSO-03 en esta revisión.

