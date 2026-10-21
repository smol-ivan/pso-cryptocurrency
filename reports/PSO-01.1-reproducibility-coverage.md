# PSO-01.1 — Cierre de brechas de reproducibilidad y cobertura

## Identificación, estado inicial y alcance

- **ID:** PSO-01.1
- **Fecha:** 2026-10-20
- **Rama:** `main`, `ahead 1` respecto de `origin/main`
- **Estado inicial:** PSO-01 estaba implementada y aprobada con observaciones
  en `reports/PSO-01-R-independent-review.md`. El riesgo concreto pendiente
  era que `run_experiments()` modificaba los estados globales de NumPy y
  Python. La suite existente tenía cuatro pruebas y no cubría directamente
  `Constriction`, el aislamiento global, el orden de configuraciones ni la
  trazabilidad de réplicas.
- **Cambios preexistentes conservados:** `docs/ai/prompts/PSO-02.md` ya estaba
  modificado al iniciar esta tarea; no forma parte de PSO-01.1.
- **Dependencias:** PSO-01 implementada y su revisión independiente aprobada.

### Alcance incluido

- Reemplazar el uso de estados globales por generadores locales por ejecución.
- Propagar esos generadores desde la orquestación hasta la inicialización y
  los modelos de velocidad.
- Ampliar pruebas de invariantes, reparación, dimensión unitaria,
  reproducibilidad, aislamiento, orden y réplicas.
- Actualizar el contexto técnico, roadmap y este reporte.

### Alcance excluido

No se modificaron función objetivo, penalización, ecuaciones de movimiento,
parámetros por defecto, topologías, condición de parada, política de
reparación, interfaz, persistencia ni métricas financieras. No se inició
PSO-02 y no se añadieron dependencias.

## Brechas abordadas

La revisión independiente de PSO-01 identificó:

1. `np.random.seed()` y `random.seed()` contaminaban el estado global del
   proceso.
2. La cobertura automatizada ejercitaba principalmente `Inertia`; la ruta de
   `Constriction` no tenía una prueba equivalente.
3. No había pruebas de aislamiento del estado global, independencia del orden
   de configuraciones ni trazabilidad reproducible de varias réplicas.
4. No había cobertura explícita de un solo activo ni de posiciones no finitas
   en ambos modelos.

## Diseño de aislamiento elegido

Se eligieron dos generadores locales explícitos por ejecución:

- `np.random.default_rng(seed)` para las posiciones iniciales.
- `random.Random(seed)` para los sorteos `r1` y `r2` de los modelos de
  velocidad.

`run_experiments()` deriva `seed + seed_index` para cada réplica y construye
ambos generadores sin llamar a `np.random.seed()` ni `random.seed()`.
`run_pso()` y `pso()` reciben los generadores; `initialize_swarm()` usa el
generador NumPy y `VelocityModel` recibe el generador Python mediante
`set_random_generator()`. `Inertia` y `Constriction` usan la misma ruta de
aleatoriedad, sin cambiar sus ecuaciones ni parámetros.

Se consideraron dos alternativas:

- **Guardar/restaurar estados globales:** habría preservado más de la API
  interna, pero seguiría acoplando el PSO a estados compartidos y sería frágil
  ante excepciones o ejecuciones anidadas.
- **Un único generador NumPy para todo:** habría requerido sustituir también
  la fuente Python y cambiar la secuencia de ambos modelos; se prefirió
  conservar sus tipos de sorteo y aislarlos por ejecución.

La solución local evita contaminación global y hace explícitos los flujos,
aunque la API extendida ahora requiere que implementaciones externas de
`VelocityModel` respeten el método heredado `set_random_generator()` si
dependen de aleatoriedad.

## Cambios realizados

| Archivo | Cambio |
|---|---|
| `src/pso/optimizer.py` | Generador NumPy local opcional para inicialización y generador Python local opcional para los modelos. |
| `src/pso/velocity_model.py` | Estado RNG inyectable en la clase base; `Inertia` y `Constriction` consumen ese generador. |
| `src/run_pso.py` | Propagación de ambos generadores a cada ejecución por target. |
| `src/experiments.py` | Derivación de semillas locales por réplica, sin modificar RNG globales. |
| `tests/test_pso01.py` | 9 pruebas totales: ambos modelos, reparación, un activo, finitud, aislamiento, orden y réplicas. |
| `docs/ai/PROJECT_CONTEXT.md` | Actualización del contrato observado de aleatoriedad y pendientes de cobertura. |
| `docs/ai/ROADMAP.md` | Registro de PSO-01.1 como implementada con revisión pendiente y bloqueo de PSO-02 hasta revisión. |

## Pruebas y comprobaciones

### Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 9 pruebas ejecutadas y 9 pasadas. |
| `./.venv/bin/python -m compileall -q src tests` | **OK**, sin errores de compilación. |
| `git diff --check` | **OK**, sin errores de whitespace. |

Las pruebas cubren:

- invariantes de una corrida válida;
- entradas vacías, dimensionalmente incorrectas, no numéricas y no finitas;
- reparación nula, negativa y válida en `Inertia` y `Constriction`;
- ejecución de un solo activo con peso `[1.0]`;
- reproducibilidad de targets, pesos, fitness e historiales;
- conservación de los estados globales de NumPy y Python alrededor de una
  ejecución sembrada;
- independencia del orden `[first, second]` frente a `[second, first]`;
- semillas de réplicas `[100, 101, 102]` y repetición de sus resultados.

### No demostrado por estas pruebas

- Que semillas distintas produzcan necesariamente soluciones finales distintas.
- Optimalidad, convergencia matemática o validez financiera.
- Aislamiento frente a código que modifique directamente el generador
  almacenado dentro de un modelo después de la inyección.
- Compatibilidad bit a bit con la secuencia de PSO-01.

## Cambios potenciales de secuencia y compatibilidad

El cambio de `np.random.rand()` a `np.random.default_rng().random()` y el
reemplazo de `random.random()` global por `random.Random(seed).random()`
modifican la secuencia de números y, por tanto, pueden cambiar pesos,
fitness e historiales respecto de PSO-01 aun con la misma semilla numérica.
No se afirma compatibilidad de resultados entre versiones. La garantía es
reproducibilidad dentro de la versión actual y aislamiento del estado global.

Las trayectorias sin semilla también dejan de depender del historial aleatorio
externo; siguen siendo no deterministas por usar fuentes locales de entropía.

## Limitaciones y riesgos residuales

- `VelocityModel.set_random_generator()` introduce una expectativa nueva para
  implementaciones externas; no existen adaptadores ni plugins en este
  repositorio que requieran migración.
- La prueba de aislamiento cubre `run_experiments()` sembrado, no una
  ejecución de cada API interna con un generador externo mal configurado.
- La semántica de `seed_count <= 0` sigue siendo la existente (`max(1, ...)`)
  y no se redefinió.
- La persistencia `.psodata` no serializa el estado de RNG; la reproducibilidad
  depende de configuración, código y semillas, no de reanudar a mitad de una
  ejecución.
- PSO-02 sigue pendiente y no se instrumentaron motivos ni estadísticas de
  parada.

## Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Misma configuración y semilla reproducen resultados | Cumplido | Pruebas de reproducibilidad y réplicas. |
| La ejecución sembrada no altera RNG globales | Cumplido | `test_seeded_experiments_preserve_global_random_states`. |
| El orden de experimentos no contamina resultados | Cumplido | `test_experiment_order_does_not_change_seeded_results`. |
| Réplicas identificables y reproducibles | Cumplido | `seed_values == [100, 101, 102]` y comparación de frontiers. |
| Ambos modelos reciben aleatoriedad consistente | Cumplido | Inyección común en `VelocityModel`; pruebas de `Inertia` y `Constriction`. |
| Cobertura de invariantes y casos límite abordados | Cumplido | Suite de 9 pruebas. |
| No alterar reglas matemáticas del PSO | Cumplido | Diff limitado a RNG, propagación y tests; no cambian fitness, dinámica, topologías ni parada. |
| Revisión independiente de PSO-01.1 | Pendiente | Debe permanecer pendiente en el roadmap. |

## Conclusión y siguiente paso

La base es suficiente para comenzar el diagnóstico de convergencia desde el
punto de vista de reproducibilidad y cobertura abordado aquí. Sin embargo,
PSO-02 no debe iniciarse hasta que un revisor independiente examine este diff,
las nueve pruebas y este reporte. No se realizó ningún cambio de PSO-02.
