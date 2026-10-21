# PSO-03 — Validación de referencias sintéticas y mínima varianza

## Identificación y estado

- **ID:** PSO-03
- **Fecha:** 2026-10-21
- **Rama:** `main`, `ahead 2` respecto de `origin/main`
- **Estado inicial:** pendiente; PSO-01 y PSO-02 implementadas y revisadas con
  observaciones.
- **Estado final:** implementada con limitaciones documentadas; revisión
  independiente pendiente.
- **No se creó ningún commit.**

El árbol ya contenía cambios de PSO-01/01.1/02, reportes, scripts y una
modificación previa de `docs/ai/prompts/PSO-02.md`. Se conservaron sin
revertir, sobrescribir ni reformatear. PSO-03 solo añadió
`tests/test_pso03.py`, este reporte y la actualización de estado del roadmap.

## Alcance ejecutado y excluido

### Ejecutado

- Función sintética Sphere adaptada al simplex long-only con óptimo conocido.
- Referencia independiente de mínima varianza long-only y de inversión
  completa mediante enumeración de conjuntos activos.
- Comparación de PSO contra esa referencia en cinco semillas.
- Casos manuales de CVaR para verificar percentil, cola, signo, retorno medio,
  distancia al target, penalización y suma del fitness.
- Verificación del perfil de configuración de Streamlit, incluyendo las dos
  topologías, 30 puntos, 100 partículas, parámetros de tolerancia, CVaR,
  penalización, semilla única y modelo Inertia.
- Confirmación de que el flujo efectivo produce 30 objetivos, pesos y
  diagnósticos por configuración.

### Excluido

- Cambios a ecuaciones, funciones fitness, modelos de velocidad, topologías,
  reparación, inicialización, interfaz o parámetros de producción.
- Descargas de Yahoo Finance, backtesting y ejecución interactiva de
  Streamlit.
- Solvers externos y dependencias nuevas.
- Matriz factorial de todas las combinaciones disponibles.
- Afirmaciones de optimalidad global del PSO o de validez financiera.
- Certificación independiente del óptimo global de la función CVaR penalizada;
  se validó su cálculo por casos manuales, no una búsqueda global del objetivo
  penalizado.

## Referencias y criterios de aceptación

### Sphere sobre el simplex

Se usó:

\[
f(w)=\sum_i (w_i-1/n)^2,\qquad
w_i\geq0,\quad \sum_iw_i=1.
\]

Para `n=4`, el óptimo conocido es `w=(0.25, 0.25, 0.25, 0.25)` y
`f*=0`. La función se implementa únicamente como adaptador de prueba, no como
función de producción. Se aceptó `f <= 1e-4` y `|w_i-0.25| <= 1e-2`, umbrales
fijados antes de evaluar los resultados porque el caso es cuadrático,
convexo y su solución está en el interior del simplex.

### Mínima varianza long-only

Se usó la matriz simétrica definida positiva:

\[
\Sigma =
\begin{bmatrix}
0.04&0.01&0.00\\
0.01&0.09&0.02\\
0.00&0.02&0.16
\end{bmatrix}.
\]

Para cada conjunto activo no vacío `S`, la referencia calcula:

\[
w_S=\frac{\Sigma_S^{-1}\mathbf1}
{\mathbf1^\top\Sigma_S^{-1}\mathbf1},
\]

descarta candidatos con pesos negativos y compara todos los candidatos
factibles, completando con ceros los activos fuera de `S`. Este procedimiento
enumera las soluciones KKT de cada cara del simplex y es una referencia
independiente, exacta para esta matriz, sin solver externo.

La solución de referencia es:

```text
w* = [0.6461538462, 0.2051282051, 0.1487179487]
f* = 0.027897435897435898
```

Se aceptó factibilidad exacta a precisión numérica (`w_i >= 0`,
`sum(w)=1`) y un gap relativo menor que `1e-4` para las ejecuciones del PSO.
El adaptador de prueba minimiza varianza pura; no se presenta como equivalente
al CVaR penalizado de producción.

### CVaR actual

Para rendimientos de portafolio `[-0.2, -0.1, 0.1, 0.2]` y `alpha=0.50`,
el percentil inferior es `0.0`; la cola seleccionada por el código es
`[-0.2, -0.1]`, con media `-0.15`. La convención implementada produce riesgo
`-CVaR = 0.15`. Con media esperada `0.0`:

- target `0.0`: `fitness = 0.15`;
- target `0.15`, penalty `50`: `fitness = 0.15 + 50*0.15 = 7.65`.

Estos casos verifican por separado la selección `<=` de la cola, la
convención de signo, el rendimiento medio, la diferencia absoluta, la
penalización y la suma final. No resuelven la ambigüedad financiera general de
CVaR; documentan la convención real del repositorio.

## Resultados observados

### Función sintética

Configuración: `n=4`, `swarm_size=30`, Inertia
(`c1=1.7`, `c2=1.7`, `w=0.8`), Global, 200 iteraciones máximas, paciencia 10,
RNG NumPy y Python sembrados con la misma semilla.

| Semilla | Fitness final | Iteraciones | Motivo |
|---:|---:|---:|---|
| 11 | 4.1752716e-06 | 18 | patience |
| 12 | 1.7676514e-06 | 29 | patience |
| 13 | 3.6732731e-09 | 85 | patience |
| 14 | 1.6263431e-06 | 37 | patience |
| 15 | 1.2189781e-08 | 54 | patience |

Las cinco corridas mantuvieron pesos finitos en el simplex y `gbest` no
creciente. Esto valida la operación y la aproximación a un óptimo conocido
para este caso; no demuestra convergencia global para funciones arbitrarias.

### Mínima varianza

Configuración: matriz anterior, objetivo de varianza pura del adaptador,
`swarm_size=50`, Inertia (`1.7`, `1.7`, `0.8`), Global, 300 iteraciones
máximas, paciencia 10. El gap es
`(fitness - f*) / f*`.

| Semilla | Fitness PSO | Gap relativo | Pesos PSO | Iteraciones | Motivo |
|---:|---:|---:|---|---:|---|
| 11 | 0.0278976347 | 7.1274e-06 | [0.64761558, 0.20403876, 0.14834566] | 16 | patience |
| 12 | 0.0278975798 | 5.1583e-06 | [0.64494918, 0.20619739, 0.14885344] | 16 | patience |
| 13 | 0.0278974479 | 4.3038e-07 | [0.64619152, 0.20533909, 0.14846939] | 16 | patience |
| 14 | 0.0278974551 | 6.9008e-07 | [0.64588808, 0.20556389, 0.14854803] | 16 | patience |
| 15 | 0.0278975318 | 3.4360e-06 | [0.64562645, 0.20492745, 0.14944610] | 16 | patience |

El gap máximo fue `7.1274e-06`, inferior al criterio `1e-4`. Todas las
soluciones fueron factibles y finitas. La conclusión autorizada es que el
núcleo se aproxima de forma reproducible a esta referencia independiente en
el caso probado; no es una garantía de optimalidad global en otros problemas.

## Configuración efectiva de Streamlit

La inspección de `app.py` y del controlador confirmó:

| Parámetro | Interfaz | Configuración efectiva verificada |
|---|---:|---:|
| Puntos de frontera | 30 | `ExperimentConfig.num_points=30` |
| Partículas | 100 | `n_swarm=100` |
| `rtol` | `1e-4` | `1e-4` |
| `atol` | `1e-8` | `1e-8` |
| Paciencia | 10 | `10` |
| Semilla reproducible | activada, base 42 | `seed=42` para Ring y `43` para Global por índice de configuración |
| Múltiples semillas | desactivado | `seed_count=1` |
| Fitness | CVaR | `CVaR(alpha=0.95, penalty=500)` |
| Modelo | Inertia | `c1=1.7`, `c2=1.7`, `inertia=0.8` |
| Topologías | Ring y Global disponibles | ambas ejecutadas |

La ejecución fija sobre una matriz sintética de cuatro observaciones y tres
activos produjo:

```text
CVaR | Inertia | Ring:   30 targets, 30 pesos, 30 diagnósticos, seed=42
CVaR | Inertia | Global: 30 targets, 30 pesos, 30 diagnósticos, seed=43
```

Los targets son `linspace(min(mean_return), max(mean_return), 30)`, según
`src/run_pso.py`; no se descargaron datos históricos.

### Discrepancia de `max_iterations`

La UI no expone `max_iterations`; `ExperimentConfig` tampoco lo contiene y
`run_pso()` no lo recibe. El valor efectivo queda implícito en el parámetro
por defecto `max_iterations=1000` de `src/pso/optimizer.py:pso`. La traza
registra si terminó por `patience` o `max_iterations`, pero la configuración
persistida no declara explícitamente ese límite. Esto es una discrepancia de
contrato/metadatos, no se corrigió en PSO-03 para respetar el alcance.

## Pruebas y comandos

### Pasadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 16 pruebas; PSO-01, PSO-02 y PSO-03 pasaron. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**. |
| `git diff --check` | **OK**. |
| Sondeo del perfil efectivo con dos configuraciones y 30 targets | **OK**, 60 optimizaciones sobre matriz sintética; ambos topologías produjeron 30 resultados. |

Las advertencias de Streamlit durante unittest indican que no hay runtime
interactivo y usan almacenamiento de caché en memoria; no fueron fallos de
prueba.

### No ejecutadas

- `streamlit run app.py` interactivo.
- Yahoo Finance, backtesting y datos históricos.
- Todas las combinaciones de objetivos, modelos y topologías.
- Referencia exacta del mínimo global de la función CVaR penalizada actual.
- Comparación contra una versión histórica bit a bit.

## Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Fórmula, óptimo, tolerancia y semilla de cada función sintética | Cumplido | `tests/test_pso03.py` y secciones de referencia/resultados. |
| Referencia independiente long-only y factibilidad | Cumplido | Enumeración de soportes activos y tabla de mínima varianza. |
| Resultados por semilla | Cumplido | Tablas de Sphere y varianza, semillas 11–15. |
| Monotonicidad, finitud y restricciones | Cumplido | Aserciones automatizadas y pruebas heredadas PSO-01/02. |
| CVaR coincide con cálculos manuales | Cumplido para la convención actual | Caso de cola y penalización en `test_cvar_matches_manual_tail_and_penalty_calculation`. |
| Configuración real de Streamlit verificada | Cumplido con discrepancia documentada | Prueba del builder y sondeo de dos topologías. |
| Optimalidad global financiera | No afirmada | CVaR penalizado no certificado; pertenece a una validación posterior. |
| Revisión independiente | Pendiente | Debe ejecutarse en una sesión separada. |

## Limitaciones y riesgos

1. La referencia de varianza usa un adaptador de prueba y no valida CVaR.
2. La coincidencia manual de CVaR valida cálculo, no selección de portafolio
   óptimo ni interpretación financiera universal.
3. La ausencia de `max_iterations` en el contrato efectivo limita la
   trazabilidad de ejecuciones que terminan por el límite.
4. El sondeo usa datos sintéticos; no permite afirmar reproducción con datos
   históricos de criptomonedas.
5. No se evaluaron exhaustivamente `Constriction`, VaR, Semivariance y
   MaxDrawdown; su existencia y selección se revisaron estáticamente, pero no
   se hizo una matriz experimental completa.

## Estado y siguiente paso

PSO-03 queda **implementada con evidencia suficiente para operaciones básicas,
reproducibilidad controlada, CVaR manual y una referencia independiente de
mínima varianza**, pero no aprobada como validación global del algoritmo ni
como validación financiera. La siguiente acción autorizada es una revisión
independiente de solo lectura de este reporte, `tests/test_pso03.py`, los
cálculos de referencia y la discrepancia de `max_iterations`.
