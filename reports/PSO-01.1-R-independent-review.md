# PSO-01.1-R — Revisión independiente de reproducibilidad y cobertura

## Identificación y alcance

- **ID:** PSO-01.1-R
- **Fecha:** 2026-10-20
- **Rama:** `main`, `ahead 2` respecto de `origin/main`
- **Objetivo:** revisar de forma independiente la implementación de PSO-01.1
  contra sus criterios originales de aislamiento aleatorio, reproducibilidad,
  cobertura y no regresión.
- **Modo:** revisión de solo lectura de la implementación, pruebas, diff,
  reportes y ejecución de comprobaciones. No se modificaron código ni pruebas
  de PSO-01.1.
- **Cambio preexistente conservado:** `docs/ai/prompts/PSO-02.md` estaba
  modificado al iniciar la revisión y no forma parte de este resultado.

### Criterios originales revisados

1. Reproducibilidad aislada dentro de la versión actual.
2. Semillas de réplicas trazables.
3. Cobertura focalizada de ambos modelos, reparación, dimensión unitaria,
   aislamiento global, orden y réplicas.
4. No alterar función objetivo, dinámica, parámetros, topologías, parada,
   interfaz ni métricas financieras.
5. Reporte con limitaciones reales y evidencia ejecutable.

### Archivos inspeccionados

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `docs/ai/WORK_PROTOCOL.md`
- `reports/README.md`
- `reports/PSO-01-invariants-reproducibility.md`
- `reports/PSO-01-R-independent-review.md`
- `reports/PSO-01.1-reproducibility-coverage.md`
- Auditoría histórica `reports/pso_validation_audit.md`, recuperada mediante
  `git show ea32230:reports/pso_validation_audit.md`
- `src/experiments.py`
- `src/pso/optimizer.py`
- `src/pso/velocity_model.py`
- `src/run_pso.py`
- `src/pso/fitness_function.py`
- `src/pso/topology.py`
- `tests/test_pso01.py`
- `src/persistence.py` y consumidores de `seed_results`,
  `seed_values` y `diversity_histories`

## Estado observado

El árbol tenía únicamente el cambio preexistente en
`docs/ai/prompts/PSO-02.md`; los cambios de PSO-01.1 estaban incluidos en el
commit `05cfaaa` junto con su reporte y pruebas. No había archivos sin
seguimiento adicionales ni cambios locales en la implementación revisada.

El roadmap marcaba PSO-01.1 como implementada con revisión pendiente y PSO-02
como pendiente. La revisión no inició PSO-02.

## Revisión técnica

### Aislamiento y reproducibilidad

`run_experiments()` deriva `config.seed + seed_index` y crea un
`np.random.default_rng(seed)` junto con `random.Random(seed)` para cada
réplica (`src/experiments.py:39-64`). Esos generadores se propagan a
`run_pso()` (`src/run_pso.py:41-57`) y finalmente a `pso()`
(`src/pso/optimizer.py:49-72`). El modelo de velocidad recibe el generador
Python mediante `set_random_generator()`, y tanto `Inertia` como `Constriction`
usan exclusivamente ese estado para `r1` y `r2`
(`src/pso/velocity_model.py:44-45,67-68`).

El sondeo de usos aleatorios no encontró llamadas de producción a
`np.random.seed()`, `np.random.random()` global, `random.seed()` ni
`random.random()` global. Las únicas llamadas globales aparecen en las pruebas
para preparar o verificar estados. Las rutas no sembradas también crean
generadores locales (`src/experiments.py:47-49`); por tanto, no dependen del
historial de los RNG globales.

La prueba automatizada de aislamiento conserva los estados globales de NumPy
y Python. Además, un sondeo independiente repitió ejecuciones de `Inertia` y
`Constriction` con `seed_count=2`, verificó `seed_values == [123, 124]`,
comparó fitness e historiales de diversidad y confirmó que una corrida
sembrada no altera los estados globales. Otro recorrido de configuraciones en
orden inverso produjo los mismos frontiers por nombre en la prueba existente.

La reutilización de una instancia de `VelocityModel` entre réplicas no
introduce contaminación observable: `pso()` reemplaza el generador del modelo
antes de cada ejecución (`src/pso/optimizer.py:70-71`). La secuencia se
consume de forma continua dentro de cada frontera, sin añadir sorteos
durante el registro.

### Invariantes y cobertura

Las pruebas cubren ambos modelos para reparación nula, negativa y válida;
también cubren una dimensión, posiciones no finitas, pesos no negativos y suma
unitaria. La reparación común en `src/pso/velocity_model.py:20-32` mantiene
la política uniforme autorizada por PSO-01.

La suite cubre entradas inválidas del optimizador, reproducibilidad de una
configuración sembrada, aislamiento de RNG globales, independencia del orden
de configuraciones y semillas consecutivas de réplicas. La prueba de
reproducibilidad compara targets, fitness, pesos e historiales de
convergencia; el sondeo independiente amplió esa comprobación a diversidad y
al modelo `Constriction` a través de la orquestación.

### Regresión y alcance

El diff de PSO-01.1 modifica únicamente:

- validación y generadores locales en `src/pso/optimizer.py`;
- inyección de RNG en `src/pso/velocity_model.py`;
- propagación en `src/run_pso.py` y `src/experiments.py`;
- pruebas en `tests/test_pso01.py`;
- documentación y reporte.

No cambia `src/pso/fitness_function.py`, `src/pso/topology.py`, las fórmulas
de riesgo, las ecuaciones de movimiento, los parámetros por defecto, las
tolerancias, la condición de parada, la política de reparación, Streamlit ni
la serialización. `src/persistence.py` ya conserva `seed_values` y los
frontiers de réplicas; los campos nuevos de PSO-01.1 no requieren una
migración adicional.

La secuencia numérica puede diferir de PSO-01 por el cambio intencional a
generadores locales, pero la compatibilidad declarada es reproducibilidad
dentro de esta versión, no igualdad bit a bit entre versiones.

## Hallazgos clasificados

| ID | Severidad | Archivo/ubicación | Evidencia e impacto | ¿Incumple PSO-01.1? | Recomendación |
|---|---|---|---|---|---|
| O-01 | Baja | `tests/test_pso01.py:228-239` | `_assert_frontiers_equal()` no compara `diversity_histories`; una regresión exclusiva de esa traza podría pasar las pruebas de réplicas. | No; la cobertura focalizada y el contrato principal sí están cubiertos, y un sondeo independiente comprobó diversidad. | Añadir la comparación de diversidad en una ampliación de cobertura futura. |
| O-02 | Baja | `tests/test_pso01.py:125-145` | La prueba directa de ambos modelos verifica reparación, pero no reproduce mediante `run_experiments()` la trayectoria completa de `Constriction`. | No; la inyección común y el uso del RNG están cubiertos por código y por sondeo independiente. | Añadir una prueba parametrizada de reproducibilidad de ambos modelos en la suite. |
| R-01 | Media | `src/persistence.py:200-235` | La persistencia registra `seed_values` cuando hay réplicas, mientras que para `seed_count=1` la semilla permanece en la configuración serializada y no en un campo del frontier. | No; la semilla sigue siendo trazable desde `ExperimentConfig`, y no se requiere un nuevo esquema. | Mantener la configuración como fuente de verdad; considerar un campo explícito solo si un futuro contrato de análisis lo exige. |

No se encontraron defectos confirmados bloqueantes, rutas de producción que
usen RNG globales ni regresiones dentro del alcance revisado.

## Comandos y resultados

| Comando | Resultado |
|---|---|
| `git status --short --branch --untracked-files=all` | **OK**: `main...origin/main [ahead 2]`; únicamente `docs/ai/prompts/PSO-02.md` modificado al iniciar. |
| `git show --stat --oneline 05cfaaa` | **OK**: confirmó los archivos y el commit de PSO-01.1. |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 9 pruebas ejecutadas y 9 pasadas. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |
| Sondeo de usos aleatorios con `rg` | **OK**: las llamadas globales solo están en pruebas; producción usa generadores locales o el estado inyectado. |
| Sondeo Python independiente de ambos modelos, réplicas, diversidad y RNG global | **OK**, reproducibilidad, semillas `[123, 124]` y aislamiento confirmados. |

## Limitaciones

- La revisión no demuestra optimalidad, convergencia matemática ni validez
  financiera.
- No se ejecutaron descargas de mercado, Streamlit, backtesting ni una
  migración de archivos históricos; están fuera del alcance de PSO-01.1.
- No se comparó bit a bit contra una versión anterior porque PSO-01.1 cambia
  deliberadamente la fuente y secuencia aleatoria.
- La cobertura de persistencia se inspeccionó estáticamente; no existe en la
  suite una fixture `.psodata` específica de semillas para esta revisión.
- Las semillas distintas pueden converger al mismo resultado; eso no invalida
  la independencia de sus generadores.

## Veredicto

**Aprobado con observaciones.**

Los criterios esenciales se cumplen: las ejecuciones sembradas son
reproducibles dentro de la versión actual, no alteran los RNG globales, el
orden de configuraciones no contamina resultados, las réplicas quedan
identificadas, ambos modelos reciben el generador previsto y la cobertura
incluye los invariantes y casos límite autorizados. Las observaciones son
brechas menores de aserciones y una consideración de representación de
semillas, no defectos que invaliden PSO-01.1.

Las observaciones **no impiden comenzar PSO-02**. PSO-02 puede conservarlas
como limitaciones de cobertura y debe evitar convertirlas en cambios de
matemática, parada o persistencia no autorizados.

## Recomendación

Marcar PSO-01.1 como revisada y aprobada con observaciones en el roadmap.
Mantener PSO-02 pendiente hasta ejecutar su propia tarea; esta revisión no
implementa ni inicia PSO-02.
