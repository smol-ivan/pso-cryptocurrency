# PSO-02.5-R — Revisión independiente

## Identificación, objetivo y alcance

- **ID:** PSO-02.5-R.
- **Fecha:** 2026-10-21.
- **Rama:** `main`, `ahead 2` respecto de `origin/main`.
- **Objetivo:** revisar de forma independiente `reports/PSO-02.5-R-target-and-initialization-review.md`, verificando targets, inicialización, historial, fitness, optimalidad y discrepancias históricas.
- **Incluido:** código de producción y scripts ya existentes, reportes PSO-02/PSO-02.5, el artefacto `.psodata`, semillas y reproducciones sintéticas.
- **Excluido:** cambios en optimizador, función objetivo, penalización, parámetros predeterminados, interfaz o reparación; solvers externos, búsqueda amplia de parámetros, descargas de Yahoo Finance, backtesting y PSO-03.

Se leyeron `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`, `docs/ai/WORK_PROTOCOL.md`, `reports/README.md`,
los reportes de PSO-02 y PSO-02.5, y los módulos relevantes de `src/` y
`scripts/`. El archivo de prompt específico
`docs/ai/prompts/PSO-02.5-R.md` no existe en el árbol; el alcance se tomó del
roadmap y de la solicitud del usuario.

El árbol ya contenía cambios de PSO-02, reportes y scripts no pertenecientes a
esta revisión. Se conservaron. La revisión no modificó código de producción,
tests, scripts ni resultados previos; solo creó este reporte y actualizó el
estado documental del roadmap. No se creó ningún commit.

## Estado inicial e integridad del proyecto

Comando inicial:

```text
git status --short --branch
```

Resultado relevante:

```text
## main...origin/main [ahead 2]
 M docs/ai/ROADMAP.md
 M docs/ai/prompts/PSO-02.md
 M src/persistence.py
 M src/pso/__init__.py
 M src/pso/optimizer.py
 M src/pso/velocity_model.py
 M src/run_pso.py
?? reports/PSO-02-convergence-diagnostics.md
?? reports/PSO-02.5-R-target-and-initialization-review.md
?? reports/PSO-02.5-convergence-exploration.md
?? reports/PSO-02.5-penalty-scale-investigation.md
?? scripts/
?? tests/test_pso02.py
```

Los cambios de `src/` y los reportes previos estaban presentes antes de esta
revisión. La comparación del estado final confirma que no se añadió ninguna
modificación a `src/`, `app.py`, `tests/` ni `scripts/`; el único nuevo reporte
es este archivo. PSO-03 sigue sin reporte ni ejecución y permanece pendiente.

## Hallazgos por severidad

| ID | Severidad | Tipo | Evidencia | Evaluación |
|---|---|---|---|---|
| PSO-02.5-R-01 | **Media** | Error confirmado en una conclusión previa | `reports/PSO-02.5-penalty-scale-investigation.md:393` presenta como “demostrada” la optimalidad global del vértice, pero el mismo conjunto de pruebas solo contiene corridas del PSO y búsquedas finitas. | La conclusión excede la evidencia. El vértice alcanza exactamente el target mínimo, pero eso no basta para minimizar `R(w)+lambda*abs(mean-target)` sobre todo el simplex. |
| PSO-02.5-R-02 | **Media** | Observación de reproducibilidad histórica | `src/experiments.py:43-63` inyecta dos RNG locales; `scripts/diagnose_convergence.py:219-231` solo inyecta `np.random.Generator`, dejando el RNG de Python creado internamente por `pso()`. | Una semilla declarada en el script no fija toda la trayectoria actual. Esto explica variación de diversidad/movimiento, pero no identifica de manera única el origen de los números históricos. |
| PSO-02.5-R-03 | **Baja** | Observación de nomenclatura | `src/pso/optimizer.py:139-146,172-196` evalúa y guarda la población inicial antes del bucle, pero `convergence_history[0]` se agrega después de la primera actualización. | “Generación 0” es correcto solo si se documenta como primer estado post-movimiento. `diversity_history[0]` sí es la diversidad inicial; las dos historias no tienen el mismo índice semántico. |
| PSO-02.5-R-04 | **Baja** | Cuestión no resuelta | `artifacts/experiments.psodata` conserva resultados/configuración, pero no contiene la traza diagnóstica necesaria para reconstruir diversidad y movimiento históricos. | No puede determinarse retrospectivamente si la discrepancia procede de una versión, semilla Python, configuración exacta o convención de medición. |

No se encontraron errores de producción introducidos por esta revisión ni
evidencia de cambios no autorizados en dinámica, penalización, reparación o
interfaz.

## 1. Targets y retornos logarítmicos

La aplicación descarga precios `Close`, calcula
`np.log(close_prices / close_prices.shift(1)).dropna()` y obtiene la media por
activo con `returns_matrix.mean(axis=0)` (`src/utils.py:19-27`). Por tanto,
cada media es un retorno logarítmico medio por observación de la muestra; no es
una tasa anualizada, un retorno simple acumulado ni una media anualizada.

`run_pso()` toma el mínimo y máximo de ese vector y construye:

```python
lim_inf = input_data.mean_return.min()
lim_sup = input_data.mean_return.max()
target_values = np.linspace(lim_inf, lim_sup, num_points)
```

(`src/run_pso.py:57-62`). La ruta del controlador conserva ese vector y delega
la construcción en `run_pso()`; no existe una fórmula alternativa en
Streamlit. Se confirma así:

- target bajo: `min_j(mean_return[j])`;
- target alto: `max_j(mean_return[j])`;
- targets intermedios: puntos equiespaciados entre ambos extremos.

Reproducción con `scripts/decompose_fitness.py` y su matriz sintética
`default_rng(42)`:

```text
medias = [-0.000361693516, 0.000179529821, 0.000048667763, 0.000671226813]
mínimo = -0.000361693516
máximo =  0.000671226813
```

El signo negativo es una propiedad de esa realización sintética y de la media
logarítmica por período; no prueba que la aplicación haya elegido
económicamente un retorno negativo ni que el target sea deseable. El intervalo
entre medias es geométricamente alcanzable por pesos long-only totalmente
invertidos, pero la deseabilidad financiera queda fuera de esta evidencia.

## 2. Inicialización, historial y vértice

`initialize_swarm()` genera componentes uniformes, normaliza cada posición y
asigna velocidad cero (`src/pso/optimizer.py:70-91`). La inicialización no
siembra vértices intencionalmente. La reparación posterior recorta valores
negativos y normaliza el vector; si todos quedan en cero, usa pesos uniformes
(`src/pso/velocity_model.py:23-36`).

La secuencia real es:

1. se evalúan posiciones iniciales y se elige el mejor `pbest` inicial;
2. se guarda la diversidad inicial en `diversity_history[0]`;
3. el bucle de `iteration == 0` mueve y repara todas las partículas;
4. se actualizan `pbest`/`gbest` y después se añade `(0, gbest)` a
   `convergence_history` (`src/pso/optimizer.py:139-196`).

Reproducción ejecutada:

```text
./.venv/bin/python scripts/decompose_fitness.py \
  --target-mode low --penalty 500 --seed 42 --topology Global
```

Resultado observado:

```text
target mínimo                  = -0.000361693516
trace[0].gbest                 = 0.041492780742
trace[0].best_mean_return      = -0.000361693516
trace[0].diversity             = 0.282498309
trace[0].movement_mean         = 0.586854997
posición de gbest tras gen 0  = [1, 0, 0, 0]
iteraciones                   = 16
motivo                        = patience
posición final                = [1, 0, 0, 0]
```

La ejecución independiente reproduce la afirmación material: el vértice no
era la posición inicial ganadora y aparece después de la primera actualización
registrada. No debe describirse como “encontrado en la inicialización” ni como
una fila que represente la población inicial.

## 3. Descomposición del fitness

Para `CVaR`, el código calcula `risk = -cvar` y luego:

\[
F(w;\tau) = R(w) + \lambda|\bar r_p-\tau|
\]

(`src/pso/fitness_function.py:23-40`). En el caso reproducido, la salida de
`decompose_fitness.py` verifica:

```text
riesgo CVaR sin penalización = 0.041492780742
penalización                 = 0.000000000000
fitness total                = 0.041492780742
discrepancia contra gbest    = 0.00e+00
```

Esto confirma la descomposición para el vértice: como su media coincide con el
target mínimo, la penalización es cero. También se evaluaron alternativas sin
alterar el optimizador: 200.000 pesos de Dirichlet y 10.001 puntos en cada una
de las tres aristas desde el vértice. El mejor Dirichlet observado fue
`0.044406150494`, y cada malla de arista alcanzó su mínimo en `t=0`, el
vértice. Estas son comprobaciones finitas; no certifican el mínimo global.

La diferencia conceptual es importante: el vértice es el único portafolio del
simplex que alcanza exactamente el target mínimo cuando esa media de activo es
estrictamente menor que las demás. Sin embargo, un portafolio con retorno algo
mayor podría reducir el riesgo lo suficiente para compensar la penalización.
La unicidad del target exacto no implica optimalidad global del fitness
penalizado.

## 4. Optimalidad

La evidencia disponible respalda solamente lo siguiente:

1. el target bajo es la media mínima de los activos;
2. en la matriz reproducida, el vértice es el único punto factible que alcanza
   exactamente ese target;
3. el PSO llega al vértice en la primera fila post-movimiento y las corridas
   documentadas vuelven a concentrarse allí;
4. las evaluaciones finitas realizadas no hallaron un valor menor.

No respalda que el vértice sea el mínimo global del fitness penalizado. Ni la
convergencia repetida del PSO, ni el colapso de diversidad, ni una muestra
finita de pesos son una demostración global. La afirmación de optimalidad
global del reporte de investigación de penalización debe conservarse como
hipótesis no demostrada, no como conclusión matemática.

## 5. Discrepancia histórica de diversidad y movimiento

El reporte histórico registra para la primera fila `diversity=0.165243` y
`movement=0.380720`, mientras que la reproducción actual, con la configuración
explícita de `decompose_fitness.py`, produce `0.282498309` y `0.586854997`.
`gbest`, el vértice y las 16 generaciones sí coinciden.

Se verificaron estas diferencias:

- `CVaR()` tiene `penalty=50.0` por defecto (`src/pso/fitness_function.py:16`);
  la aplicación pasa `penalty=500.0` desde Streamlit y el script de
  descomposición también lo pasa explícitamente.
- `scripts/diagnose_convergence.py` construye `CVaR()` sin argumento y solo
  pasa `random_generator=rng_np`; el `python_random_generator` no se pasa
  (`scripts/diagnose_convergence.py:219-231`), por lo que `pso()` crea un
  `random.Random()` distinto para la dinámica de velocidad.
- `scripts/decompose_fitness.py` pasa ambos generadores con la semilla 42
  (`scripts/decompose_fitness.py:69-88`).
- PSO-01.1 cambió la generación NumPy heredada a `np.random.default_rng` y
  sustituyó el RNG global de Python por `random.Random` inyectado
  (`src/experiments.py:43-63`, `src/pso/optimizer.py:106-130`). Ese cambio de
  versión puede preservar el `gbest` extremo y cambiar la trayectoria
  geométrica.

Un sondeo actual con la misma matriz, semilla NumPy y `penalty=500` produjo:

```text
ambos RNG sembrados:   div=0.282498309, mov=0.586854997
Python RNG no pasado:  div=0.260378156, mov=0.649953504
```

Esto demuestra que la ruta de RNG de Python sí afecta diversidad y movimiento,
pero no reproduce por sí sola los dos números históricos exactos. Como el
artefacto no guarda diagnósticos por generación y no existe una ejecución
histórica congelada con todos los RNG/configuración, la causa exacta no puede
determinarse. La explicación más sólida es una combinación posible de versión
pre/post PSO-01.1, RNG Python no fijado, configuración efectiva y/o convención
de medición; debe permanecer explícitamente como incertidumbre.

## Comandos y resultados

| Comando | Resultado |
|---|---|
| `./.venv/bin/python scripts/decompose_fitness.py --target-mode low --penalty 500 --seed 42 --topology Global` | **OK**; 16 generaciones, `patience`, `gbest=0.041492780742`, vértice tras la primera actualización, descomposición con error `0.00e+00`. |
| Reproducción de medias sintéticas con `generate_synthetic_returns_300x4(42)` | **OK**; extremos y medias reportados coinciden. |
| Comparación de RNG Python sembrado/no pasado | **OK**; muestra diferencias actuales en diversidad/movimiento y confirma la fuente de variabilidad. |
| 200.000 pesos Dirichlet y 10.001 puntos por arista | **OK** como búsqueda finita; no se usa como prueba de optimalidad global. |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 12 pruebas ejecutadas y 12 pasadas. |
| `./.venv/bin/python -m compileall -q src tests scripts` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |
| Streamlit, Yahoo Finance, backtesting y PSO-03 | **No ejecutados**, fuera del alcance. |

## Criterios de aceptación

| Criterio | Estado independiente |
|---|---|
| Targets basados en medias mínima y máxima | **Cumplido**; fórmula y ruta común verificadas en `src/utils.py` y `src/run_pso.py`. |
| Interpretación de medias logarítmicas | **Cumplido con observación**; son medias por período, no tasas anualizadas ni conclusiones de deseabilidad. |
| Inicialización y generación 0 | **Cumplido**; reproducción distingue estado inicial de primer estado post-movimiento. |
| Aparición de `[1,0,0,0]` | **Cumplido**; aparece en la primera fila registrada, no en la inicialización. |
| Descomposición riesgo/penalización | **Cumplido**; suma verificada para el vértice y alternativas evaluadas. |
| Evaluación de optimalidad global | **Cumplido con limitación**; se rechaza la inferencia global y se documenta la brecha. |
| Investigación de discrepancia histórica | **Cumplido con incertidumbre explícita**; se identifican diferencias de RNG/versión/configuración posibles, sin atribución única. |
| Integridad del proyecto | **Cumplido**; no se modificó producción ni se alteraron resultados previos. |
| PSO-03 pendiente | **Cumplido**; no se ejecutó ni se habilita por esta revisión. |

## Recomendación

**Aprobar con observaciones.**

La revisión bajo examen acierta en la construcción de targets, la convención
de historial, la aparición del vértice y la separación entre target exacto,
convergencia y optimalidad. Debe mantenerse la corrección de lenguaje que
rechaza el mínimo global como hecho demostrado y debe conservarse la
incertidumbre sobre los valores históricos de diversidad/movimiento. Antes de
usar esas métricas para comparaciones históricas, conviene congelar la versión,
la configuración completa y ambos generadores aleatorios. **PSO-03 permanece
pendiente** y no se inicia como consecuencia de este informe.
