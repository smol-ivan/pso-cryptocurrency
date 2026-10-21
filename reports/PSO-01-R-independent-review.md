# PSO-01-R — Revisión independiente de invariantes y reproducibilidad

## Identificación y alcance

- **ID:** PSO-01-R
- **Fecha:** 2026-10-20
- **Rama:** `main`, `ahead 1` respecto de `origin/main`
- **Objetivo:** revisar de forma independiente si PSO-01 satisface sus
  criterios de aceptación dentro del alcance autorizado.
- **Modo:** solo lectura sobre implementación, pruebas, diff y reportes; este
  reporte es el único archivo creado por esta revisión.
- **Estado de Git al iniciar:** modificaciones en
  `src/experiments.py`, `src/pso/optimizer.py` y
  `src/pso/velocity_model.py`; `reports/PSO-01-invariants-reproducibility.md`
  y `tests/` sin rastrear. Las eliminaciones y documentos de PSO-00 ya no
  estaban en el estado actual y no se atribuyen a PSO-01.

No se modificaron código, pruebas existentes, documentación previa ni
`docs/ai/ROADMAP.md`. El estado del roadmap que marca PSO-01 como revisada
aprobada era preexistente a esta revisión y no se alteró.

## Archivos y evidencia revisados

### Lectura obligatoria

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `reports/PSO-01-invariants-reproducibility.md`
- `reports/PSO-00-R-documentation-review.md`
- Auditoría histórica `reports/pso_validation_audit.md`, recuperada de
  `git show ea32230:reports/pso_validation_audit.md`, porque ya no existe en
  `HEAD`.

### Implementación y pruebas

- `src/experiments.py`
- `src/pso/optimizer.py`
- `src/pso/velocity_model.py`
- `src/pso/fitness_function.py`
- `src/pso/topology.py`
- `src/run_pso.py`
- `tests/test_pso01.py`

El diff de PSO-01 contiene cambios únicamente en los tres módulos de `src/`
anteriores. El reporte y las pruebas son archivos sin rastrear en el estado
observado, pero forman parte de la entrega revisada.

## Comandos ejecutados y resultados

| Comando | Resultado |
|---|---|
| `git status --short --branch` | `main...origin/main [ahead 1]`; cambios de PSO-01 en `src/`, reporte y `tests/` sin rastrear. |
| `git diff --name-status -- src tests reports/PSO-01-invariants-reproducibility.md` | `M` en los tres módulos de `src/`; los archivos sin rastrear no aparecen en `git diff`. |
| `git diff -- src/experiments.py src/pso/optimizer.py src/pso/velocity_model.py` | Confirmó que el cambio se limita a validación, reparación y semillas. |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 4 pruebas ejecutadas y 4 pasadas. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |
| `rg "\b(random\|rand\|randn\|default_rng\|RandomState)\b\|np\.random\|random\." src tests -n` | Fuentes localizadas en `np.random.rand`, `random.random` y las dos llamadas de siembra. |
| Sondeo Python de tres réplicas y ambos modelos de velocidad | **OK**: semillas `[100, 101, 102]`, repetición completa igual y reparación nula uniforme en `Inertia` y `Constriction`. |

Salida principal de pruebas:

```text
Ran 4 tests in 0.061s
OK
```

## Revisión técnica

### 1. Control de aleatoriedad

Las fuentes usadas por el PSO son:

- `np.random.rand()` en `src/pso/optimizer.py:24`, para posiciones iniciales.
- `random.random()` importado en `src/pso/velocity_model.py:2` y usado en
  `:37` y `:59`, para `r1` y `r2`.

`run_experiments()` deriva `config.seed + seed_index` en
`src/experiments.py:42-43` y fija ambos generadores en `:44-46` antes de
cada réplica. Por tanto, una configuración sembrada con `seed=100` recibe
los flujos de semillas 100, 101 y 102 para `seed_count=3`. El sondeo externo
repitió la ejecución completa y obtuvo igualdad de todos los `best_fitnesses`;
los valores finales de dos réplicas distintas coincidieron en ese caso, pero
eso no demuestra que sus flujos sean iguales: las semillas y los sorteos
iniciales son distintos y el algoritmo puede converger al mismo resultado.

La prueba del repositorio (`test_experiment_seed_reproduces_all_stochastic_outputs`)
comprueba targets, fitness, pesos e historiales de una configuración sembrada
repetida, incluyendo la alteración previa del estado global. Esto satisface
el contrato documentado para ejecuciones con semilla.

**Riesgo que requiere comprobación adicional — estado global:** llamar
`np.random.seed()` y `random.seed()` modifica el estado global del proceso y
no lo restaura al terminar `run_experiments()`. Esto puede afectar código
llamador que use cualquiera de los generadores después de una corrida y hace
que las corridas sin semilla dependan del historial previo. No bloquea el
criterio actual, que está definido para configuraciones con semilla, pero
debería resolverse o documentarse al definir un contrato de RNG aislado.

### 2. Invariantes de pesos

`_repair_position()` en `src/pso/velocity_model.py:16-27`:

- exige vector unidimensional no vacío;
- rechaza valores no finitos;
- recorta componentes negativas;
- normaliza si la suma positiva es mayor que cero;
- reasigna uniformemente `1/N` si el vector queda nulo.

La misma función se usa por `Inertia` (`:46`) y `Constriction` (`:65`), por
lo que ambos modelos preservan la política uniforme. El sondeo externo
confirmó `[0.5, 0.5]` y suma `1.0` para ambos modelos en el caso degenerado.
En una corrida válida, la prueba confirma no negatividad, finitud y suma uno
del mejor vector devuelto; también comprueba la monotonicidad no creciente de
`gbest`.

**Criterio satisfecho:** la reparación ocurre dentro del flujo real de
actualización, no únicamente sobre el helper, aunque la prueba automatizada
directa cubre explícitamente `Inertia` y la verificación externa cubrió
`Constriction`.

### 3. Validación de entradas

`pso()` valida antes de inicializar (`src/pso/optimizer.py:56-64`):

- matriz NumPy no vacía, bidimensional y finita (`:169-175`);
- `swarm_size` entero positivo (`:178-180`);
- target real finito (`:128-134`);
- `patience` y `max_iterations` enteros positivos (`:161-164`);
- `rtol` y `atol` reales finitos no negativos (`:142-145`, `:165-166`).

La inicialización repite validaciones básicas porque también es una función
invocable directamente (`:18-20`) y rechaza fitness no finito (`:29-30`).
Cada fitness de las iteraciones también se valida (`:84-87`).

La prueba automatizada cubre matriz vacía, matriz unidimensional, `NaN`,
`swarm_size=0`, target infinito y no numérico, tolerancias no numéricas,
`patience=0` y `max_iterations=0`, todos con `ValueError` explícito.

**Mejora opcional:** no hay prueba automatizada para `Constriction` con
posición no finita ni para un fitness personalizado que devuelva un objeto no
real; tampoco se validan parámetros de las clases de fitness, `num_points` de
`run_pso()` o `seed_count`. La propia tarea documenta esos límites y no hay
evidencia de que deban pertenecer a PSO-01.

### 4. Calidad y aislamiento de las pruebas

Las cuatro pruebas cubren criterios diferentes y usan una matriz pequeña
construida en `setUp()`. No dependen de datos externos ni de Yahoo Finance.
La prueba de reproducibilidad establece deliberadamente ambos RNG en valores
distintos antes de la segunda ejecución; `run_experiments()` debe restablecer
la semilla declarada, y lo hace.

No se observó dependencia del orden de pruebas: cada caso construye sus
objetos y datos. La prueba de reproducibilidad deja estado global al final,
pero no hay pruebas posteriores que dependan de una secuencia aleatoria
concreta; el resultado es una debilidad de aislamiento, no un fallo observado
en la suite.

### 5. Alcance y regresiones

El diff no modifica:

- `src/pso/fitness_function.py` ni las ecuaciones/penalties;
- parámetros por defecto de PSO;
- `src/pso/topology.py`;
- el criterio de parada de `src/pso/optimizer.py`;
- `src/finance.py`, interfaz o persistencia.

La validación adicional de entradas y la reparación uniforme cambian
intencionalmente los casos inválidos o degenerados autorizados por PSO-01.
Para entradas válidas, la normalización conserva la distribución relativa y
la ejecución sigue usando las mismas dinámicas, topologías y criterio de
parada.

## Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Casos válidos comprueban no negatividad y suma de pesos | **Satisfecho** | `tests/test_pso01.py:test_valid_run_preserves_weight_invariants`; sondeo externo de ambos modelos. |
| Casos inválidos tienen comportamiento explícito y probado | **Satisfecho dentro del alcance revisado** | Validadores en `src/pso/optimizer.py:128-180` y prueba de matrices, parámetros, tolerancias, target y fitness finito. Quedan fuera `run_pso.num_points`, parámetros de fitness y `seed_count`. |
| Reproducibilidad con política concreta y misma semilla | **Satisfecho para configuraciones sembradas** | `src/experiments.py:42-46`, prueba de historial completo y sondeo con tres réplicas. |
| Separación de fallos esperados y comportamiento corregido | **Satisfecho** | El reporte PSO-01 separa hallazgos históricos corregidos de limitaciones pendientes. |
| Reporte con comandos y resultados reales | **Satisfecho para la entrega** | `reports/PSO-01-invariants-reproducibility.md` y esta revisión. |
| Revisión independiente | **Satisfecho por esta revisión** | Este reporte no modifica el roadmap; el estado del roadmap preexistía. |

## Hallazgos clasificados

| ID | Clasificación | Severidad | Evidencia | Impacto |
|---|---|---|---|---|
| R-01 | Riesgo que requiere comprobación adicional | Media | `run_experiments()` modifica los RNG globales en `src/experiments.py:44-46` y no restaura estados. | Efectos secundarios sobre código llamador y corridas posteriores sin semilla. |
| O-01 | Mejora opcional | Baja | No hay prueba directa automatizada para `Constriction` ni para todas las rutas de entradas de `initialize_swarm()`. | Menor cobertura futura; la verificación externa no observó regresión. |
| C-01 | Criterio satisfecho | — | Las fuentes RNG, semillas derivadas, invariantes y validadores cumplen el contrato sembrado. | PSO-01 es funcional dentro de su alcance. |

No se encontraron defectos confirmados bloqueantes en la implementación
revisada. El riesgo R-01 no contradice el contrato explícito de PSO-01, pero
debe quedar considerado antes de diseñar experimentos reproducibles más
amplios.

## Limitaciones de la revisión

- No se ejecutaron descargas de mercado, Streamlit, backtesting ni pruebas
  financieras; están fuera de PSO-01.
- No se comparó contra un solver independiente ni se evaluó optimalidad.
- El archivo histórico de auditoría no está en `HEAD`; se usó la copia del
  commit `ea32230`.
- No se modificaron archivos para probar hipótesis; los sondeos fueron
  procesos Python separados y no alteraron el árbol.
- El reporte PSO-01 declara cuatro pruebas; se verificó que la suite actual
  contiene esas cuatro, incluyendo los casos no numéricos añadidos después de
  la primera revisión.

## Veredicto

**Aprobado con observaciones.** PSO-01 satisface sus criterios dentro del
alcance autorizado: las ejecuciones sembradas son reproducibles en sus
historiales completos, las réplicas usan semillas consecutivas reproducibles,
los pesos válidos conservan sus invariantes y los casos inválidos cubiertos
fallan explícitamente. El único hallazgo relevante es el efecto secundario
esperable de modificar RNG globales; no requiere corrección para aprobar
PSO-01, pero sí una decisión explícita si el protocolo futuro exige aislamiento
entre componentes.

## Recomendación sobre PSO-02

**PSO-02 puede comenzar.** Sus dependencias técnicas están satisfechas para
iniciar la instrumentación de convergencia. Debe conservar la política de RNG
actual para ejecuciones sembradas y registrar el riesgo R-01 como limitación
del protocolo, sin convertir esta revisión en una ampliación del alcance de
PSO-02.
