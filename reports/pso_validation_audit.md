# Auditoría técnica de PSO y plan de validación

## 1. Resumen ejecutivo

La implementación es modular y ejecutable: separa optimizador, partícula,
modelos de velocidad, topologías, funciones de fitness y el flujo de
experimentos/frontier. Sin embargo, la ejecución sin excepciones no basta para
considerarla validada. La auditoría estática y dos sondeos deterministas
encontraron dos problemas demostrados:

1. **La reproducibilidad declarada es incompleta:** `run_experiments()` fija
   únicamente `np.random.seed()`, pero `Inertia` y `Constriction` obtienen
   `r1,r2` del módulo `random`. Con la misma semilla de NumPy se obtuvieron
   historiales distintos; al reiniciar ambos generadores sí coincidieron.
2. **La reparación no garantiza presupuesto completo:** si todos los pesos
   reparados quedan en cero, el código omite la normalización y conserva el
   vector nulo, por lo que `sum(weights) == 1` no es un invariante.

También hay riesgos pendientes de caracterizar: ausencia de validación de
dimensiones, valores finitos y parámetros; errores con población vacía o
matrices de retornos vacías; y falta de instrumentación explícita del motivo
de terminación. No se cambió el algoritmo ni sus parámetros.

**Recomendación inmediata:** la siguiente tarea debe ser una capa de pruebas
deterministas y una instrumentación de diagnóstico, empezando por corregir
únicamente la infraestructura de semillas y la reparación cuando las pruebas
confirmen el contrato deseado. Después debe compararse el caso de varianza
mínima long-only contra un solver independiente.

## 2. Arquitectura y flujo actual

El flujo principal es:

1. `run_analysis_pipeline()` construye configuraciones para cada combinación de
   objetivo, velocidad y topología (`src/controllers/experiment_controller.py:101-140`).
2. `run_experiments()` deriva semillas consecutivas por configuración y
   réplica, y llama a `run_pso()` (`src/experiments.py:33-64`).
3. `run_pso()` genera una malla de objetivos entre el mínimo y máximo de
   `mean_return`, ejecutando un PSO independiente por punto
   (`src/run_pso.py:52-96`).
4. `pso()` inicializa la población, actualiza cada partícula, actualiza los
   mejores históricos, registra convergencia/diversidad y devuelve el mejor
   resultado (`src/pso/optimizer.py:11-110`).
5. Las métricas financieras se recalculan posteriormente desde los pesos
   (`src/finance.py:16-65`), no desde un estado interno del optimizador.

Los objetivos disponibles son CVaR, VaR, semivarianza, varianza y drawdown
máximo (`src/pso/fitness_function.py:15-125`). Las velocidades disponibles son
inercia y constricción (`src/pso/velocity_model.py:16-65`); las topologías son
anillo y global (`src/pso/topology.py:14-32`).

## 3. Ecuaciones efectivamente implementadas

### 3.1 Inicialización

Para `n_assets = returns_matrix.shape[1]`, cada partícula se inicializa como:

```text
x_i ~ Uniforme([0, 1] ^ n_assets)
x_i <- x_i / sum(x_i), si sum(x_i) > 0
v_i <- 0
pbest_i <- x_i
f(pbest_i) <- fitness_function.evaluate(x_i, returns_matrix, target)
```

Esto está en `src/pso/optimizer.py:17-26`. `np.random.rand()` se usa para
posiciones. En condiciones normales de NumPy la suma inicial es positiva,
pero no hay comprobación explícita de forma, finitud ni `swarm_size > 0`.

### 3.2 Actualización de velocidad y posición

Para `Inertia`:

```text
r1, r2 ~ Uniforme(0, 1)                 # random.random()
v_i <- w v_i
       + c1 r1 (pbest_i - x_i)
       + c2 r2 (reference_i - x_i)
x_i <- x_i + v_i
x_i <- max(0, x_i)                      # componente a componente
x_i <- x_i / sum(x_i), si sum(x_i) > 0
```

Referencia: `src/pso/velocity_model.py:22-40`.

Para `Constriction`:

```text
phi <- c1 + c2
chi <- 2 / |2 - phi - sqrt(phi^2 - 4 phi)|
v_i <- chi [v_i + c1 r1 (pbest_i - x_i)
                + c2 r2 (reference_i - x_i)]
x_i <- x_i + v_i
x_i <- max(0, x_i)
x_i <- x_i / sum(x_i), si sum(x_i) > 0
```

Referencia: `src/pso/velocity_model.py:43-65`. El constructor rechaza
`c1+c2 <= 4` (`:47-50`), pero no valida finitud o positividad individual de
los coeficientes.

Importante: la velocidad se almacena sin límites ni reparación. El recorte y
la normalización se aplican a la posición, no a `v_i`.

### 3.3 `pbest` y `gbest`

Después de mover una partícula se evalúa la nueva posición. El `pbest` solo se
actualiza bajo mejora estricta:

```text
si f(x_i) < pbest_value_i:
    pbest_value_i <- f(x_i)
    pbest_i <- x_i
```

Está en `src/pso/optimizer.py:67-76`. Al final de cada generación, el mejor
`pbest` de la población se compara con el mejor global y también se actualiza
solo bajo mejora estricta (`:78-81`). Por ello el historial de `gbest` debería
ser no creciente cuando los fitness sean finitos y comparables.

### 3.4 Topologías

- **Global:** toda la población es el vecindario; devuelve el menor
  `best_val` (`src/pso/topology.py:30-32`).
- **Ring:** usa índices modulares
  `particle_index + offset`, con `offset` en
  `[-k_neighbors, k_neighbors]`, incluyendo la propia partícula
  (`src/pso/topology.py:14-27`). La configuración del controlador usa
  `k_neighbors=1` (`src/controllers/experiment_controller.py:120`).

Con una población de un elemento, el anillo funciona porque todos los índices
modulares apuntan al mismo elemento. Con población vacía, ambas topologías
fallan indirectamente al buscar el mínimo; el anillo además calcula módulo
por cero.

### 3.5 Límites, reparación e invariantes

La única restricción implementada directamente es:

```text
x_j >= 0
sum(x) = 1, solo si sum(max(0, x)) > 0
```

No hay límites superiores individuales aparte de la normalización implícita,
ni restricciones de cardinalidad, turnover u otras. No se valida que el
resultado sea finito. Si `x` es `[-1, -1]` después de moverlo, la reparación
produce `[0, 0]` y deja la suma en cero.

### 3.6 Terminación y tolerancias

El bucle recorre `range(max_iterations)` (`src/pso/optimizer.py:66`). En cada
iteración registra `(iteration, best_global_value)` y diversidad
(`:83-84`). A partir de `iteration > 5`:

```text
improvement <- abs(gbest_t - gbest_previous)
tolerance   <- atol + rtol * abs(gbest_t)
si improvement < tolerance:
    convergence_wait += 1
    si convergence_wait >= patience: terminar
si no:
    convergence_wait <- 0
```

Referencia: `src/pso/optimizer.py:86-96`. La diversidad contiene un valor
inicial antes de la primera actualización y un valor adicional por iteración;
el historial de fitness solo contiene valores posteriores a cada iteración.
Por tanto sus longitudes difieren en uno por diseño actual.

Con los valores predeterminados, el paro por paciencia no puede ocurrir en una
o dos iteraciones: se requiere superar la barrera `iteration > 5` y acumular
`patience` iteraciones. Una ejecución de una o dos iteraciones implicaría
`max_iterations` externo distinto, una configuración no observada aquí, o una
interrupción fuera de `pso()`.

### 3.7 Semillas

`run_experiments()` hace `np.random.seed(seed)` antes de cada réplica
(`src/experiments.py:41-45`). Las posiciones usan NumPy, pero `r1,r2` usan
`random.random()` (`src/pso/velocity_model.py:23,53`). En consecuencia, la
semilla registrada no gobierna todo el proceso estocástico. Tampoco se usa un
objeto RNG local que aísle configuraciones, y una corrida sin semilla consume
el estado global compartido.

La derivación de semillas es reproducible en intención:
`config.seed + seed_index`, y el controlador asigna
`base_seed + config_index` (`src/experiments.py:42-44`,
`src/controllers/experiment_controller.py:137`). La implementación actual no
es reproducible de extremo a extremo por la mezcla de generadores.

## 4. Auditoría de invariantes

| Invariante | Evidencia actual | Estado |
|---|---|---|
| Pesos no negativos | `np.maximum(0, new_position)` en ambos modelos | Garantizado solo para posiciones finitas antes del recorte; no hay validación posterior |
| Suma igual a uno | Normalización condicional | **No garantizado** si la suma reparada es cero |
| Posiciones finitas | Sin guardas | No garantizado; NaN/Inf pueden propagarse |
| Velocidades finitas | Sin guardas ni límites | No garantizado |
| Fitness finito | Sin validación en funciones de fitness | No garantizado |
| Vector nulo | No hay fallback | **Produce pesos nulos**; luego puede evaluarse como cartera válida por accidente |
| Dimensiones | Solo `@` y operaciones NumPy | No hay contrato explícito ni mensajes de error propios |
| Población pequeña | Una partícula funciona; cero no | Parcial |
| Límites extremos | `alpha`, penalty, tolerancias y tamaños no se validan | Riesgo pendiente |
| Monotonicidad de `gbest` | Actualización estricta por menor fitness | Esperable con valores finitos; no comprobada automáticamente |

Otros riesgos de fitness:

- CVaR y métricas calculan una media de la cola; con entradas vacías fallan.
- Valores no finitos de retornos o pesos pueden producir NaN sin error.
- `MaxDrawdown` divide por `running_max`; retornos que lleven el acumulado a
  cero o valores problemáticos requieren casos de prueba explícitos.
- El objetivo combina riesgo con `penalty * abs(mean_return-target)`, por lo
  que no es una restricción exacta de retorno objetivo.

## 5. Investigación de la convergencia temprana

### Hechos observados

El criterio incorporado impide, con sus parámetros predeterminados, una salida
por paciencia en una o dos iteraciones: la comprobación empieza después de la
sexta iteración. Una población de un solo activo sí puede volverse estática
desde el principio porque toda posición normalizada es `[1]`; eso no prueba
error del algoritmo.

La actualización de `gbest` es histórica y estrictamente no creciente en el
caso finito normal. La pérdida de diversidad no participa en la terminación:
solo se calcula y devuelve.

### Hipótesis que deben distinguirse experimentalmente

1. **Convergencia real del fitness:** `gbest` deja de mejorar y la distribución
   de fitness también se estabiliza.
2. **Pérdida de diversidad:** las posiciones colapsan, pero aún existe
   diferencia entre el mejor y el promedio o entre el mejor y una referencia.
3. **Paciencia/tolerancia:** las mejoras son menores que
   `atol + rtol*abs(gbest)` durante las generaciones requeridas.
4. **Degeneración por reparación:** muchas posiciones terminan en vértices o
   en el vector nulo; el algoritmo parece estable por falta de movimiento.
5. **Efecto de la semilla:** el historial cambia porque los sorteos de
   `random` no están incluidos en la semilla registrada.
6. **Datos/fitness:** el penalty puede dominar el riesgo, o la escala de
   riesgo puede hacer que varias posiciones tengan diferencias por debajo de la
   tolerancia.

### Instrumentación propuesta

Sin cambiar la función objetivo, registrar por generación y por punto de
frontera:

- mínimo, media, mediana, máximo y desviación estándar del `fitness` actual;
- mínimo, media y dispersión de `best_val` por partícula;
- `gbest`, mejora absoluta, tolerancia y contador de paciencia;
- diversidad media actual, distancia máxima al centroide y número de
  posiciones únicas aproximadas;
- media/riesgo del mejor portafolio y distancia al retorno objetivo;
- suma mínima/máxima de pesos, mínimo de pesos y número de violaciones;
- conteos de no finitos en posición, velocidad y fitness;
- iteración final y motivo: `max_iterations` o `patience`.

La instrumentación debe conservar los historiales existentes o versionar el
formato, porque `EfficientFrontier` y la persistencia ya transportan
`convergence_histories` y `diversity_histories` (`src/run_pso.py:18-24`).

## 6. Pruebas existentes y faltantes

No se encontraron directorios ni archivos de pruebas del proyecto. Tampoco se
encontró configuración de pytest, Ruff, mypy o un runner de cobertura fuera de
las dependencias del entorno. Los artefactos `.psodata` existentes son datos,
no evidencia de una suite automatizada.

### Pruebas que pueden escribirse sin modificar la implementación

Estas pruebas son prioritarias porque prueban el comportamiento actual y
permiten convertir los hallazgos en evidencia:

1. `Inertia` y `Constriction`: posición no negativa, suma uno para movimientos
   normales y preservación explícita del caso nulo actual.
2. `RingTopology` y `GlobalTopology`: mejor local/global con tres partículas,
   `k_neighbors=0`, `k_neighbors >= swarm_size` y población de un elemento.
3. Fitness conocido para una matriz pequeña: varianza, VaR, CVaR,
   semivarianza, drawdown y penalty.
4. `pbest/gbest`: una función fitness controlada que fuerce mejora, empate y
   empeoramiento; comprobar que el mejor no empeora.
5. Reproducibilidad: repetir con la misma semilla de NumPy solamente y con
   ambas semillas; documentar la diferencia actual.
6. Invalidación: matrices vacías, dimensiones incompatibles, NaN/Inf, alpha
   fuera de rango, `swarm_size=0`, `max_iterations=0`, `patience <= 0` y
   `num_points <= 0`.
7. Terminación: una función constante para comprobar exactamente la barrera de
   seis iteraciones, paciencia y forma de los historiales.
8. Sintética con óptimo conocido: dos activos y varianza con matriz de
   retornos diseñada para que el activo/mezcla óptima sea calculable.
9. Problema restringido de referencia: varianza mínima long-only y presupuesto
   completo en una matriz de covarianza positiva definida.

Las pruebas que pretendan exigir suma uno ante una reparación nula, o
reproducibilidad completa usando solo `np.random.seed`, deben marcarse como
fallos esperados hasta que se apruebe una tarea de corrección.

## 7. Plan de validación incremental

### Prioridad P0 — congelar el comportamiento observable

- Crear `tests/` con fixtures NumPy pequeños y deterministicos.
- Probar dimensiones, formas de historiales, invariantes normales y
  monotonicidad de `gbest`.
- Añadir casos límite que hoy fallan, sin cambiar todavía el algoritmo.
- Archivos: nuevos `tests/test_fitness.py`,
  `tests/test_velocity_model.py`, `tests/test_topology.py`,
  `tests/test_optimizer.py`.

### Prioridad P1 — hacer válida la reproducibilidad

- Decidir un único contrato: RNG explícito por corrida o sincronización de
  NumPy y `random`.
- Añadir una prueba de igualdad bit a bit para posición, fitness e historiales
  con la misma semilla.
- Mantener compatibilidad de la API pública si es razonable.
- Archivos candidatos: `src/experiments.py`,
  `src/pso/velocity_model.py`, posiblemente `src/pso/optimizer.py` y los
  tests de P0.

No debe afirmarse reproducibilidad en README/UI mientras esta prueba no pase.

### Prioridad P1 — instrumentación de diagnóstico

- Añadir estadísticas por generación y un motivo de terminación explícito.
- Evitar modificar la función fitness o el criterio hasta observar datos.
- Archivos: `src/pso/optimizer.py`, `src/run_pso.py`, `src/experiments.py`,
  y los consumidores de historiales (`src/ui/charts.py`,
  `src/persistence.py`) si se amplía el formato.

### Prioridad P1 — contrato de reparación y entradas

- Especificar qué hacer ante vector nulo, NaN/Inf, matriz vacía y dimensiones
  incompatibles.
- Implementar solo la política aprobada, con pruebas regresivas.
- Archivos probables: `src/pso/velocity_model.py`,
  `src/pso/optimizer.py`, `src/pso/fitness_function.py`.

### Prioridad P2 — solver independiente de varianza mínima

- Construir primero una referencia analítica/numerical pequeña sin introducir
  dependencia nueva.
- Comparar PSO usando exactamente la misma matriz de retornos, la misma
  convención temporal, el mismo presupuesto completo y restricciones
  `w >= 0`, `sum(w)=1`.
- Medir objetivo, pesos, error de restricción y variación entre semillas.
- Solo si el caso base lo justifica, evaluar un solver externo ya disponible o
  añadir una dependencia justificada y fijada en `pyproject.toml`.

### Prioridad P3 — objetivos con retorno objetivo

La comparación debe conservar la misma función que PSO:

```text
min_w  risk(w) + penalty * |mean_return(w) - target|
      sujeto a w >= 0, sum(w)=1
```

No debe compararse contra una optimización de retorno exacto sin penalty,
porque serían problemas distintos. Posteriormente puede compararse también
contra una formulación con restricción exacta
`mean_return(w) >=/== target`, pero como experimento separado.

## 8. Comparación independiente para varianza mínima

Para un caso base sin retorno objetivo, usar:

```text
min_w  w^T Sigma w
sujeto a w_j >= 0 para todo j
         sum_j w_j = 1
```

La implementación PSO equivalente actualmente se aproxima usando
`Variance(penalty=...)` y un `target_value`; para una comparación válida se
debe fijar el target al retorno alcanzable relevante y evitar que el penalty
cambie el problema, o añadir una función de fitness de varianza pura solo como
harness de prueba, sin alterar la aplicación. Esta decisión debe aprobarse
antes de modificar código.

La referencia puede calcularse para matrices pequeñas mediante enumeración de
caras activas o resolución de los sistemas KKT de cada subconjunto de activos:
para un subconjunto activo sin restricciones de desigualdad internas,

```text
w_A = Sigma_A^{-1} 1 / (1^T Sigma_A^{-1} 1)
```

se conserva la solución si es no negativa; se toma la mejor entre
subconjuntos. Así no se añade una dependencia. Para matrices mayores, se
puede evaluar un solver existente en el entorno, pero debe registrarse la
versión y la tolerancia.

Los criterios de aceptación deben incluir: factibilidad de pesos, gap relativo
de varianza frente a la referencia, estabilidad sobre varias semillas,
historial no creciente de `gbest` y ausencia de NaN/Inf.

## 9. Hallazgos clasificados

| ID | Severidad | Clasificación | Evidencia | Impacto |
|---|---|---|---|---|
| F-01 | Alta | Error demostrado | `src/experiments.py:43-44` fija NumPy; `src/pso/velocity_model.py:23,53` usa `random.random()` | La semilla reportada no reproduce toda la corrida |
| F-02 | Alta | Error demostrado | `src/pso/velocity_model.py:35-40,60-65` deja el vector si la suma es cero | Puede devolver cartera que viola presupuesto completo |
| R-01 | Alta | Riesgo demostrado por casos límite | `src/pso/optimizer.py:58`, topologías `:19-24,32` | Población vacía termina en `ValueError` o error de módulo |
| R-02 | Alta | Riesgo demostrado por sondeo | Funciones de fitness sin guardas, `src/pso/fitness_function.py:24-40` | Matriz vacía da error; NaN produce fitness NaN |
| R-03 | Media | Riesgo potencial | No hay validación de dimensiones/finitez en optimizador ni fitness | Errores NumPy crípticos o resultados inválidos |
| R-04 | Media | Riesgo potencial | Velocidad ilimitada, `src/pso/velocity_model.py:31-32,58-59` | Saltos grandes, clipping frecuente y pérdida de diversidad |
| R-05 | Media | Riesgo potencial | Paro solo usa mejora de `gbest`, `src/pso/optimizer.py:86-96` | Puede parar con población degenerada; no distingue convergencia de colapso |
| R-06 | Baja | Riesgo de observabilidad | No se registra motivo, estadísticas de población ni violaciones | No se puede explicar una corrida rápida solo con los historiales actuales |

La severidad es de validación/correctitud experimental, no una afirmación de
que el sistema sea explotable o que todos los casos normales fallen.

## 10. Experimentos ejecutados y limitaciones

### Comando 1 — reproducibilidad y parada

```sh
./.venv/bin/python - <<'PY'
# matriz 4x2; Variance(penalty=50); swarm=4; target=0.005
# np.random.seed(123), dos llamadas a pso()
# después np.random.seed(123) y random.seed(999) antes de cada llamada
PY
```

Resultado observado:

```text
same_numpy_seed_equal_best: True
same_numpy_seed_equal_history: False
history_shapes: (9, 2) (10,)
first_iterations_recorded: 9
reset_both_rng_equal_best: True
reset_both_rng_equal_history: True
weights_sum_nonnegative: 1.0 0.0
```

La igualdad del mejor final no demuestra reproducibilidad; el historial
distinto demuestra que la trayectoria no queda determinada por la semilla de
NumPy. La longitud de diversidad es una mayor que la de convergencia por el
registro inicial.

### Comando 2 — reparación y límites

```sh
./.venv/bin/python - <<'PY'
# Particle([.5,.5], [-1,-1], 0) con Inertia(c1=0,c2=0,inertia=1)
# y casos de swarm vacío, retornos vacíos y posición NaN
PY
```

Resultado observado:

```text
zero_repair_position: [0.0, 0.0]
zero_repair_sum: 0.0
empty_swarm => ValueError min() iterable argument is empty
empty_returns_cvar => IndexError index -1 is out of bounds for axis 0 with size 0
nan_position_variance => nan
```

No se ejecutaron experimentos financieros con datos descargados ni una
comparación con solver independiente. Por tanto no se hacen afirmaciones
sobre calidad de la frontera, optimalidad empírica o rendimiento de mercado.
Los resultados anteriores son sondeos locales mínimos, no una suite de
validación.

## 11. Riesgos, limitaciones y preguntas pendientes

- ¿El contrato deseado ante una posición nula es reasignar uniformemente,
  conservar la posición anterior, o fallar explícitamente?
- ¿La semilla debe controlar solo experimentos completos o también permitir
  reproducir cada modelo de velocidad de forma aislada?
- ¿`target_value` debe ser una penalización blanda como ahora, o el producto
  necesita una restricción exacta en alguna modalidad?
- ¿La comparación de varianza mínima debe usar una nueva fitness pura de
  prueba, sin exponerla en la UI, o una reformulación del flujo?
- ¿Qué valores de `alpha`, penalty, tolerancias, tamaños y matrices vacías
  deben rechazarse en la API pública?
- La malla de `run_pso()` usa min/max de retornos medios de activos, no una
  frontera factible calculada; debe validarse si ese rango es intencional.
- El historial no almacena riesgo, retorno ni motivo de terminación; cualquier
  análisis actual de convergencia es necesariamente incompleto.
- La auditoría no demuestra que todas las combinaciones de datos reales
  produzcan NaN; demuestra que no existe una garantía preventiva y que varios
  casos límite reproducen resultados inválidos.

## 12. Siguiente tarea recomendada

Implementar **la suite P0 de pruebas deterministas y el contrato de
reproducibilidad P1**, sin cambiar todavía objetivos, penalty, topologías,
parámetros ni la política de búsqueda. La tarea debe:

1. Añadir los tests unitarios y de casos límite descritos.
2. Hacer que una semilla de experimento controle todos los sorteos, o
   documentar y probar explícitamente una alternativa equivalente.
3. Añadir una prueba que capture el vector nulo y obligue a decidir su política.
4. Medir con la instrumentación mínima si las corridas rápidas son
   convergencia, pérdida de diversidad o tolerancia/paciencia.

Solo después de que esas pruebas pasen debe abordarse la referencia
independiente de varianza mínima y cualquier corrección de comportamiento.
