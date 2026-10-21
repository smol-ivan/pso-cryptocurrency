# PSO-02.5-R — Revisión crítica de targets, inicialización y conclusiones matemáticas

## Identificación, objetivo y alcance

- **ID:** PSO-02.5-R.
- **Fecha:** 2026-10-21.
- **Rama:** `main`, `ahead 2` respecto de `origin/main`.
- **Objetivo:** revisar críticamente la construcción de targets, la convención
  de generación 0, la inicialización/colapso del enjambre y la afirmación de
  mínimo global hecha en la evidencia de PSO-02.5.
- **Incluido:** código de producción, scripts diagnósticos, controlador,
  Streamlit, artefacto `.psodata`, informes de PSO-02/PSO-02.5 y una
  reproducción sintética independiente.
- **Excluido:** cambios en la función objetivo, dinámica del PSO, parámetros
  predeterminados, interfaz, datos de mercado, solver externo, búsqueda amplia
  de parámetros y avance a PSO-03.

No se modificaron `src/`, `scripts/`, `tests/` ni la función objetivo. Se creó
este reporte y se actualizó únicamente el estado documental de PSO-02.5-R en
`docs/ai/ROADMAP.md`. No se creó ningún commit.

## Estado inicial y procedencia inspeccionada

El árbol ya contenía cambios de PSO-02 y varios reportes no relacionados con
esta revisión; se conservaron sin sobrescribirlos. La rama y el estado se
comprobaron con:

```text
git status --short --branch
## main...origin/main [ahead 2]
```

Archivos y funciones inspeccionados:

| Área | Archivos/funciones relevantes |
|---|---|
| Targets de la frontera | `src/run_pso.py:38-63`, `src/controllers/experiment_controller.py:81-146`, `src/utils.py:7-29`, `app.py:87-151` |
| Configuración y semillas | `src/experiments.py:10-75`, `src/persistence.py:31-115`, `artifacts/experiments.psodata` |
| Fitness | `src/pso/fitness_function.py:11-125` |
| Inicialización y traza | `src/pso/optimizer.py:68-93`, `src/pso/optimizer.py:121-288` |
| Reparación y movimiento | `src/pso/velocity_model.py:20-81`, `src/pso/particle.py:4-18` |
| Diagnósticos | `scripts/decompose_fitness.py`, `scripts/diagnose_convergence.py` |
| Evidencia previa | `reports/PSO-02-convergence-diagnostics.md`, `reports/PSO-02-R-independent-review.md`, `reports/PSO-02.5-convergence-exploration.md`, `reports/PSO-02.5-penalty-scale-investigation.md` |

El artefacto guardado `artifacts/experiments.psodata` contiene una matriz de
retornos de forma `(1360, 4)`, cuatro configuraciones y 20 réplicas por
configuración. Sus configuraciones incluyen `CVaR`, `Inertia`, `penalty=500`,
`n_swarm=100`, `patience=10`, `rtol=1e-4`, `atol=1e-8` y semillas base 42--45.
El archivo no contiene `diagnostics_*.json`; por tanto, no es evidencia
persistida de las métricas por generación de PSO-02.5.

## Investigación A — Construcción e interpretación de targets

### Fórmula efectiva

`load_crypto_returns()` descarga precios `Close`, calcula:

```python
returns = np.log(close_prices / close_prices.shift(1)).dropna()
mean_return = returns_matrix.mean(axis=0)
```

Así, `mean_return[j]` es el rendimiento logarítmico medio por observación del
activo `j`; no es una tasa anualizada ni un rendimiento simple acumulado.

`run_pso()` construye la frontera con:

```python
lim_inf = input_data.mean_return.min()
lim_sup = input_data.mean_return.max()
target_values = np.linspace(lim_inf, lim_sup, num_points)
```

El controlador no construye otra fórmula: crea `PSOInputData` con el vector de
medias y la matriz de retornos y delega en `run_experiments()`/`run_pso()`.
Streamlit pasa `num_points`, los retornos cargados y el `penalty` elegido a la
misma ruta. Por tanto:

- **Target bajo:** `min_j mean_return[j]`, exactamente la media mínima entre
  activos.
- **Target alto:** `max_j mean_return[j]`, exactamente la media máxima entre
  activos.
- **Target medio:** no es la media de las medias ni un percentil; cuando se
  interpreta como el punto central de la malla, es
  \[
  \tau_\mathrm{mid} =
  \frac{\min_j\bar r_j+\max_j\bar r_j}{2}.
  \]
  Con más puntos, `np.linspace` genera los targets intermedios entre esos dos
  extremos.

La reproducción del artefacto confirma la fórmula con datos guardados:

```text
medias = [0.002120752056, 0.001336364620, 0.001961304213, 0.003434044565]
target inicial = 0.001336364620 = mínimo
target final   = 0.003434044565 = máximo
midpoint       = 0.002385204592
```

Los cuatro experimentos persistidos tienen los mismos extremos, como exige la
construcción común de la frontera.

### Target negativo y significado económico

En la matriz sintética de `scripts/decompose_fitness.py`, generada con
`np.random.default_rng(42)` y medias normales
`[0.0005, 0.0008, 0.0002, 0.0010]`, las medias realizadas son:

```text
[-0.000361693516, 0.000179529821, 0.000048667763, 0.000671226813]
```

El target bajo negativo es, por tanto, una consecuencia de la realización
aleatoria sintética de los retornos, no una elección económica explícita de
“aceptar rendimiento negativo”. El código permite targets finitos negativos y
no añade una restricción de deseabilidad económica.

En términos del modelo, el target es un rendimiento logarítmico medio por
período. Un target dentro del intervalo de medias de los activos es
matemáticamente alcanzable por un portafolio long-only totalmente invertido,
porque el rendimiento medio del portafolio es
`sum_j w_j mean_return[j]`. Eso no implica que sea económicamente deseable:
la deseabilidad depende de horizonte, frecuencia, benchmark, inflación,
costos, riesgo tolerado y de si se acepta una media negativa. “Factible” es
una propiedad geométrica del simplex; “deseable” requiere un criterio
financiero adicional que esta tarea no introduce.

## Investigación B — Inicialización, generación 0 y colapso

### Inicialización y reparación

`initialize_swarm()` genera para cada partícula un vector de `n_assets`
uniformes en `[0,1)`, lo divide por su suma y asigna velocidad cero. No genera
vértices de forma intencional; con variables continuas la probabilidad de
obtener exactamente un vértice en la inicialización es prácticamente nula.
El fitness inicial sí se evalúa y se almacena como `particle.best_val`.

En cada actualización, `Inertia` o `Constriction` calcula la velocidad y llama
a `_repair_position()` sobre `position + velocity`. La reparación recorta
componentes negativas a cero y normaliza si la suma es positiva; si la suma es
cero, usa pesos uniformes. El valor reparado se copia como nuevo `best_pos`
solo si mejora el fitness. Esta política puede producir un vértice cuando
todos los componentes salvo uno quedan no positivos; no es una inicialización
en vértices.

### Convención exacta del historial

En `pso()`:

1. Se inicializa el enjambre y se identifica el mejor fitness inicial.
2. Se añade la diversidad inicial únicamente a `diversity_history`.
3. Se ejecuta la primera actualización para `iteration == 0`.
4. Se evalúan las posiciones movidas, se actualizan `pbest`/`gbest` y recién
   entonces se añade `(0, gbest)` a `convergence_history` y la primera fila a
   `ConvergenceTrace`.

Por ello, la fila llamada **generación 0** es el primer estado posterior al
movimiento y reparación; no es una instantánea de la población inicial. El
mejor fitness de la inicialización no está expuesto en `convergence_history`.
`diversity_history[0]` sí representa la diversidad inicial, mientras que
`trace.diversity[0]` representa la diversidad después de la primera
actualización.

### Reproducción independiente del caso `0.041493`

Comando ejecutado:

```text
./.venv/bin/python scripts/decompose_fitness.py --target-mode low --penalty 500 --seed 42 --topology Global
```

Con la matriz sintética de 300×4 y `CVaR(alpha=0.95, penalty=500)`, la
ejecución actual produjo:

```text
media mínima / target       = -0.000361693516
fitness inicial mínimo     = 0.111187727456
posición inicial ganadora  = [0.66292692, 0.13574549, 0.19417641, 0.00715118]
posición inicial es vértice = False

trace[0].gbest              = 0.041492780742
trace[0].best_mean_return   = -0.000361693516
trace[0].diversity          = 0.282498309
trace[0].movement_mean      = 0.586854997
posición de gbest tras gen0 = [1, 0, 0, 0]
```

La misma ejecución terminó tras 16 filas (`termination_iteration=15`) por
`patience`, con la posición final `[1, 0, 0, 0]`. La secuencia respalda que el
vértice aparece durante la primera actualización, no en la inicialización.
Después, la reparación y la dinámica hacen que la población se concentre:
en la salida actual la diversidad cae a aproximadamente `0.000513` en la
tercera fila y a cero desde la cuarta, y el movimiento también llega a cero.

Hay una discrepancia de procedencia que debe conservarse: el informe previo
`PSO-02.5-penalty-scale-investigation.md` registra para el mismo encabezado
`trace[0].diversity=0.165243` y `movement=0.380720`, mientras que la
reproducción actual da `0.282498` y `0.586855`. El valor de `gbest`, el
vértice y la duración coinciden. No se debe presentar la tabla anterior como
si fuera una traza regenerada por el código actual sin conservar esa
limitación/versionado.

### Discrepancia `penalty=50` frente a `penalty=500`

`app.py` usa por defecto `penalty=500.0`, y el artefacto persistido confirma
`penalty=500.0`. En cambio, `scripts/diagnose_convergence.py` instancia
`CVaR()` sin argumentos; la signatura de producción hace que eso sea
`penalty=50.0`. `scripts/decompose_fitness.py` sí pasa explícitamente
`penalty=500.0` en su reproducción Streamlit.

Por tanto, las observaciones de `diagnose_convergence.py` y las observaciones
de la aplicación no son automáticamente el mismo experimento. El informe
anterior debe corregirse para atribuir cada tabla a su valor de penalización
real, no a la configuración de Streamlit por defecto.

## Investigación C — ¿Es el vértice el mínimo global?

La función implementada es:

\[
F(w)=R(w)+500\,|\bar r_p-\tau|,\qquad
\bar r_p=\sum_jw_j\bar r_j.
\]

Para el target bajo sintético, la media del activo 0 es estrictamente menor
que las otras tres. En el simplex `w_j >= 0`, `sum(w)=1`:

```text
bar_r_p - min_j(bar_r_j) = sum_{j != 0} w_j (bar_r_j - bar_r_0) >= 0
```

La igualdad solo puede darse en `w=[1,0,0,0]`. Esto demuestra el primer hecho:
**el vértice es el único portafolio factible que alcanza exactamente el target
bajo**, para esta matriz y esta realización.

No demuestra por sí solo que minimice `F`: un portafolio con retorno algo mayor
puede reducir `R(w)` lo suficiente para compensar la penalización. Esa es
precisamente la diferencia entre satisfacer exactamente el target y minimizar
la función penalizada.

### Evidencia disponible y alcance

La reproducción actual obtiene en el vértice:

```text
risk CVaR sin penalización = 0.041492780742
penalización               = 0
fitness                    = 0.041492780742
```

Como comprobación independiente, se evaluaron 200.000 pesos de Dirichlet
aleatorios y una malla de 10.001 puntos en cada arista desde el vértice hacia
los otros tres vértices. El mejor valor aleatorio fue `0.047082044844`; las
tres mallas de arista alcanzaron su mínimo en `t=0`, el propio vértice. Estas
comprobaciones no encontraron un contraejemplo, pero son búsquedas finitas y
no una demostración global. Las tres ejecuciones del PSO tampoco serían una
prueba de optimalidad global.

**Conclusión:** con los datos y herramientas autorizados, la afirmación
“el vértice es el mínimo global del fitness penalizado” queda **no
demostrada**. La evidencia correcta es:

1. el target bajo tiene un único portafolio factible que lo alcanza
   exactamente;
2. el PSO, bajo la semilla/configuración reproducida, alcanza ese vértice en
   la primera generación registrada y converge a él en las semillas
   documentadas;
3. las evaluaciones adicionales finitas no hallaron un fitness menor;
4. falta una certificación independiente sobre todo el simplex para elevarlo
   a mínimo global.

No se introdujo solver externo ni se alteró la producción para llenar esa
brecha.

## Correcciones necesarias al lenguaje de PSO-02.5

| Lenguaje previo | Corrección requerida |
|---|---|
| “`gbest` ya es el óptimo en generación 0” | “La primera fila del historial, etiquetada 0, ya contiene el vértice después de la primera actualización; el mejor de la inicialización no era un vértice.” |
| “El colapso demuestra que encontró el mínimo global” | “El colapso demuestra concentración de la población bajo esa dinámica; no prueba optimalidad global.” |
| “El vértice es el mínimo global” | “El vértice es el único portafolio que alcanza exactamente el target bajo; su optimalidad penalizada global no está demostrada.” |
| “La penalización usada fue la de Streamlit” para todas las tablas | Separar `CVaR()` del diagnóstico (`penalty=50`) de la reproducción/app (`penalty=500`). |
| “Las métricas de diversidad/movimiento son la secuencia actual” | Conservar procedencia: los valores de la tabla anterior no coinciden con la reproducción actual, aunque sí coincidan `gbest`, posición y parada. |
| “El target bajo representa baja ganancia elegida” | “Es la media mínima de la muestra sintética; su signo negativo resulta de esa realización de datos.” |

## Pruebas y comprobaciones ejecutadas

### Pasadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python scripts/decompose_fitness.py --target-mode low --penalty 500 --seed 42 --topology Global` | OK; 16 generaciones, `patience`, `gbest=0.041492780742`, posición final `[1,0,0,0]`, verificación de composición con discrepancia `0.00e+00`. |
| Reproducción Python de `initialize_swarm()` y de la primera actualización con NumPy/Python seed 42 | OK; mejor inicial no vértice, mejor tras la primera actualización vértice. |
| Comprobación del artefacto `.psodata` contra `returns_matrix.mean(axis=0)` | OK; extremos persistidos iguales a mínimo/máximo de las medias. |
| Comprobación finita: 200.000 pesos Dirichlet + 10.001 puntos por arista | OK como diagnóstico; no certifica optimalidad global. |
| `./.venv/bin/python -m unittest discover -s tests -v` | OK, 12 pruebas ejecutadas y 12 pasadas. |
| `./.venv/bin/python -m compileall -q src tests scripts` | OK, sin errores de compilación. |
| `git diff --check` | OK, sin errores de whitespace. |

### No ejecutadas

No se ejecutaron Streamlit, Yahoo Finance, backtesting, una búsqueda amplia de
parámetros, un solver externo ni PSO-03. No se regeneró el artefacto
`.psodata`, para conservar su procedencia.

## Limitaciones y preguntas para PSO-03

- La traza no registra el mejor fitness de la población inicial; interpretar
  `convergence_history[0]` requiere la convención documentada arriba.
- El artefacto guardado no tiene diagnósticos por generación y no puede
  reconstruirlos sin volver a ejecutar.
- La discrepancia entre tablas históricas y la reproducción actual queda
  documentada, no resuelta retroactivamente.
- El argumento de target exacto solo usa la unicidad de la media mínima; no
  certifica el mínimo del riesgo penalizado.
- PSO-03 debe comparar contra una referencia independiente en la misma matriz,
  convención de retornos y función objetivo, y debe reportar gap y factibilidad
  sin llamar “óptimo global” a una corrida del PSO.
- La elección de un target económicamente deseable, la escala de la
  penalización y las convenciones financieras quedan fuera de esta revisión y
  deben permanecer separadas de la validación algorítmica.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| Verificar targets bajo/medio/alto en código de producción y Streamlit | Cumplido; fórmula común `linspace(min(media), max(media))` documentada y contrastada con `.psodata`. |
| Explicar target negativo y su interpretación | Cumplido; es consecuencia de medias sintéticas y representa media de retorno logarítmico por período. |
| Explicar inicialización, reparación y convención de generación 0 | Cumplido; reproducción independiente distingue población inicial de primer estado post-movimiento. |
| Verificar la secuencia `gbest=0.041493` y `[1,0,0,0]` | Cumplido para la reproducción actual; se conserva la discrepancia de métricas históricas. |
| Distinguir target exacto, convergencia y optimalidad global | Cumplido; la tercera afirmación queda explícitamente no demostrada. |
| No cambiar función objetivo, dinámica, interfaz ni parámetros de producción | Cumplido; no se modificó código de producción. |
| Dejar PSO-03 sin ejecutar y la revisión independiente pendiente | Cumplido; PSO-03 permanece pendiente y este reporte requiere revisión independiente. |

**Estado final:** revisión ejecutada, pendiente de revisión independiente.
