# PSO-01 — Invariantes y reproducibilidad

## Identificación y alcance

- **ID:** PSO-01
- **Objetivo:** probar entradas, pesos, restricciones, semillas y casos límite
  del núcleo PSO, corrigiendo únicamente el contrato mínimo autorizado.
- **Fecha:** 2026-10-20.
- **Rama:** `main`.
- **Estado inicial:** `main...origin/main`; el árbol ya contenía cambios
  documentales de PSO-00 no realizados por esta tarea y tres eliminaciones
  documentales pendientes de la preparación anterior. No había suite de
  pruebas automatizadas.
- **Dependencias:** PSO-00 completada y PSO-00-R aprobada en
  `reports/PSO-00-R-documentation-review.md`.

### Alcance incluido

- Tests focalizados del optimizador, reparación de posiciones e
  integración de semillas.
- Validación explícita de matriz de retornos, tamaño de enjambre, target,
  tolerancias, paciencia, iteraciones y fitness finito.
- Reparación uniforme cuando el vector recortado queda nulo.
- Sincronización de `numpy.random` y `random` para semillas de experimento.
- Este reporte y actualización del roadmap.

### Alcance excluido

No se cambiaron la función objetivo, penalty, parámetros por defecto,
topologías, condiciones de parada, ecuaciones financieras, interfaz,
persistencia ni resultados financieros. No se añadieron dependencias ni se
realizó un experimento con datos descargados.

## Decisión de política

La posición nula se repara mediante pesos uniformes `1 / N`. Esta política
preserva simultáneamente la restricción long-only y el presupuesto completo,
es determinista y no privilegia un activo concreto. La reparación se aplica
tanto a `Inertia` como a `Constriction`; las posiciones válidas siguen
normalizándose sin cambiar su distribución relativa.

La reproducibilidad se define para una ejecución de experimento con la misma
configuración y semilla registrada. Esa semilla controla las posiciones
iniciales de NumPy y los sorteos `r1`, `r2` de la biblioteca estándar
`random`, incluyendo cada réplica derivada.

## Cambios realizados

| Archivo | Cambio |
|---|---|
| `src/pso/optimizer.py` | Validación de entradas estructurales y finitas; rechazo explícito de tamaños/parámetros inválidos y de fitness no finito. |
| `src/pso/velocity_model.py` | Helper común de reparación; fallback uniforme para la posición nula y rechazo de posiciones no finitas o dimensionalmente inválidas. |
| `src/experiments.py` | Si existe semilla, fija ambos generadores antes de cada réplica. |
| `tests/test_pso01.py` | Cuatro pruebas focalizadas sobre invariantes, entradas, reparación y reproducibilidad. |

## Comandos ejecutados y resultados

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 4 pruebas ejecutadas y 4 pasadas. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |
| `git status --short --branch` | `main...origin/main`; cambios de PSO-01 en `src/` y `tests/`, además de cambios documentales previos conservados. |

Salida esencial de la suite:

```text
Ran 4 tests in 0.081s
OK
```

## Evidencia

### Pruebas pasadas

- Una corrida válida conserva pesos finitos, no negativos y con suma uno; el
  `gbest` no aumenta y la longitud de diversidad mantiene la relación
  observada con la historia de convergencia.
- Matriz vacía, matriz unidimensional, `NaN`, `swarm_size=0`, target infinito,
  `patience=0` y `max_iterations=0` producen `ValueError` con mensajes
  explícitos.
- Un movimiento que habría producido `[0, 0]` se transforma en `[0.5, 0.5]`
  para dos activos, con suma uno.
- Dos ejecuciones con la misma configuración y semilla producen exactamente
  los mismos targets, fitness, pesos e historiales aunque el estado global de
  ambos RNG se altere antes de la segunda ejecución.

### Fallos esperados separados del comportamiento corregido

La auditoría previa demostró que antes de este cambio la misma semilla de
NumPy no reproducía toda la trayectoria y que la reparación nula devolvía
presupuesto cero. Esos comportamientos ya no son el contrato: están cubiertos
por las pruebas de reproducibilidad y reparación uniforme. No se conservaron
como fallos esperados porque PSO-01 autoriza la corrección mínima de ambos
hallazgos.

## Limitaciones y pendientes

- No se validaron las convenciones financieras, la optimalidad de las
  soluciones, la calidad de la frontera ni el backtesting.
- No se modificó la semántica de `run_pso()` para validar `num_points` ni la
  validación de parámetros de fitness; esos temas requieren decisiones
  específicas y quedan fuera de PSO-01.
- El motivo de parada, diversidad por generación y compatibilidad histórica de
  `.psodata` siguen pendientes de PSO-02.
- La primera revisión independiente detectó que tipos no numéricos podían
  producir `TypeError` interno en `np.isfinite()`. Se corrigió con validación
  numérica explícita y se añadieron pruebas para `target_value`, `rtol` y
  `atol` no numéricos. La verificación independiente posterior aprobó el
  arreglo sin hallazgos adicionales.

## Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Casos válidos comprueban no negatividad y suma de pesos | Cumplido | `test_valid_run_preserves_weight_invariants` |
| Casos inválidos tienen comportamiento explícito y probado | Cumplido | `test_invalid_optimizer_inputs_raise_explicit_errors` y validadores del optimizador |
| Reproducibilidad con política concreta y misma semilla | Cumplido | `test_experiment_seed_reproduces_all_stochastic_outputs` |
| Separación de fallos esperados y comportamiento corregido | Cumplido | Sección correspondiente de este reporte y auditoría histórica |
| Comandos y resultados reales documentados | Cumplido | Tabla de comandos y salida de unittest |
| Revisión independiente | Cumplido | La verificación posterior aprobó el arreglo y no encontró regresiones |

## Siguiente paso

PSO-02 puede considerarse habilitada por dependencias, pero debe comenzar en
una tarea separada y respetar su propio prompt; este reporte no incluye
instrumentación de convergencia.
