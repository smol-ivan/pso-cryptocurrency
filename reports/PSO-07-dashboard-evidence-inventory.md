# PSO-07 — Inventario de evidencia y diseño del dashboard de validación

## 1. Identificación, alcance y estado

- **Fecha de inspección:** 2026-10-21.
- **Rama observada:** `main`, `ahead 2` respecto de `origin/main`.
- **Objetivo:** inventariar la evidencia existente y proponer una aplicación
  Streamlit independiente, estrictamente de solo lectura, para presentarla.
- **Alcance incluido:** código del PSO, persistencia, artefacto histórico,
  scripts diagnósticos, pruebas, reportes de PSO-01 a PSO-04 y revisiones
  independientes.
- **Alcance excluido:** implementación de la aplicación, ejecución de PSO,
  descarga de Yahoo Finance, backtesting nuevo, modificación de producción,
  tests, artefactos o interfaz principal.
- **Cambios realizados:** únicamente este reporte. No se creó ningún commit.

Existe una discrepancia de nomenclatura que debe conservarse: el roadmap usa
PSO-07 para “Diseñar experimentos reproducibles” y lo mantiene pendiente por
dependencias PSO-05/PSO-06; la solicitud actual usa PSO-07 para el inventario y
diseño conceptual del dashboard. Este reporte documenta la solicitud actual
como una entrega documental separada y no cambia el estado del roadmap
preexistente.

## 2. Comprobaciones realizadas

Se inspeccionaron `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`, `docs/ai/WORK_PROTOCOL.md`, `docs/ai/prompts/README.md`,
`reports/README.md`, los reportes de PSO-01, PSO-01.1, PSO-02, PSO-02.5,
PSO-03 y PSO-04, sus revisiones independientes, los módulos relevantes de
`src/`, `app.py`, las pruebas existentes, los scripts diagnósticos y
`artifacts/experiments.psodata`.

También se inspeccionó el contenedor `.psodata` sin ejecutar experimentos:

| Comprobación | Resultado observado |
|---|---|
| Tipo de archivo | ZIP comprimido `.psodata`; no es un pickle legacy |
| Activos | `BTC-USD`, `ETH-USD`, `SOL-USD`, `ADA-USD` |
| Ventana | `2020-01-01` a `2024-01-01`, intervalo `1d` |
| Alpha persistido | `0.95` |
| Retornos de optimización | 1.360 fechas y matriz persistida `arrays/returns_matrix.npy` |
| Retornos de backtesting | 1.017 fechas y matriz `arrays/bt_returns_matrix.npy` |
| Configuraciones | 4: CVaR/MaxDrawdown × Inertia × Ring/Global |
| Puntos por frontera | 30 por configuración |
| Réplicas | 20 por configuración; semillas base 42, 43, 44 y 45 |
| Semillas persistidas | 42–61, 43–62, 44–63 y 45–64 |
| Historiales de convergencia | 2.520 archivos `convergence_<i>.npy` |
| Trazas diagnósticas | 0 archivos `diagnostics_<i>.json` |
| Tablas de métricas | 4 tablas de 30 filas y 4 tablas por semilla de 600 filas |

La inspección de las tablas persistidas confirmó las columnas históricas
`mean_return`, `cvar`, `var`, `variance`, `semivariance`, `max_drawdown`,
`volatility`, `sharpe_ratio` y `fitness`; las tablas por semilla añaden
`seed_index`, `portfolio_index` y `target_return`.

No se ejecutaron `scripts/diagnose_convergence.py`,
`scripts/decompose_fitness.py`, la suite de tests, Streamlit, Yahoo Finance ni
backtesting. Los números de esos scripts y reportes se tratan como resultados
históricos documentados, no como resultados generados durante esta inspección.

## 3. Inventario de archivos y artefactos relevantes

### Núcleo y flujo de ejecución

| Ruta | Contenido relevante para el dashboard |
|---|---|
| `src/pso/optimizer.py` | Inicialización, actualización, `gbest`, historiales, criterio de parada y `ConvergenceTrace`. |
| `src/pso/particle.py` | Posición, velocidad, `best_pos` y `best_val` de cada partícula. |
| `src/pso/velocity_model.py` | Inertia, Constriction, sorteos aleatorios y reparación al simplex. |
| `src/pso/topology.py` | Topologías Ring y Global. |
| `src/pso/fitness_function.py` | CVaR, VaR, varianza, semivarianza y máximo drawdown penalizados. |
| `src/run_pso.py` | Construcción de targets con `linspace(min(mean), max(mean))` y `EfficientFrontier`. |
| `src/experiments.py` | Parámetros de configuración, semillas derivadas y réplicas. |
| `src/controllers/experiment_controller.py` | Perfil de Streamlit, combinación de configuraciones y persistencia. |

### Datos, métricas y persistencia

| Ruta | Contenido relevante |
|---|---|
| `src/utils.py` | Descarga de `Close`, retornos logarítmicos por observación y `mean_return`. |
| `src/finance.py` | Métricas de cartera, VaR/CVaR, drawdown, Sharpe y anualización. |
| `src/models/state.py` | Estructura `ExperimentsPayload` y campos históricos. |
| `src/persistence.py` | Formato ZIP `.psodata`, arrays, Parquet, configuraciones, pesos, convergencia y diagnósticos opcionales. |
| `artifacts/experiments.psodata` | Único artefacto histórico inspeccionado; contiene resultados persistidos, pero no diagnósticos PSO-02 por generación. |

### Diagnósticos y evidencia verificable

| Ruta | Evidencia y alcance |
|---|---|
| `scripts/diagnose_convergence.py` | Diagnóstico por target de `gbest`, diversidad, movimiento, reparaciones, distancia al target y terminación; usa matrices sintéticas de 4×200 y 3×4. |
| `scripts/decompose_fitness.py` | Descomposición observacional de riesgo y penalización; reproduce configuración Streamlit con matriz sintética 300×4 y `penalty=500`. |
| `tests/test_pso01.py` | Invariantes, reparación, finitud, semillas, aislamiento y réplicas. |
| `tests/test_pso02.py` | Forma de trazas, monotonicidad, paciencia, máximo de iteraciones, persistencia y compatibilidad sin diagnósticos. |
| `tests/test_pso03.py` | Sphere en simplex, referencia independiente de mínima varianza, CVaR manual y perfil Streamlit. |
| `tests/test_pso04.py` | Retornos logarítmicos, VaR/CVaR, empates, drawdown simple y anualización. |

### Reportes y revisiones

| Ruta | Aporte |
|---|---|
| `reports/PSO-01-invariants-reproducibility.md` | Contrato de invariantes y reproducibilidad de la versión actual. |
| `reports/PSO-01.1-reproducibility-coverage.md` | Generadores locales, semillas de réplicas y limitaciones de compatibilidad histórica. |
| `reports/PSO-02-convergence-diagnostics.md` | Contrato de `ConvergenceTrace`, métricas y sondeo controlado. |
| `reports/PSO-02.5-convergence-exploration.md` | Exploración sintética de estancamiento, colapso y semillas. |
| `reports/PSO-02.5-penalty-scale-investigation.md` | Discrepancia `penalty=50`/`500`, descomposición y sensibilidad histórica. |
| `reports/PSO-02.5-R-target-and-initialization-review.md` | Corrección de la interpretación de target, generación 0 y optimalidad. |
| `reports/PSO-03-reference-validation.md` | Resultados de Sphere, mínima varianza y CVaR manual. |
| `reports/PSO-04-financial-conventions.md` | Convenciones efectivas de retornos, riesgo, drawdown y anualización. |
| `reports/*-R-*.md` | Revisiones independientes; deben mostrarse como estado de revisión, no como evidencia experimental adicional. |

## 4. Hechos que el dashboard puede mostrar

### 4.1 Núcleo del PSO

Está respaldado por código y pruebas que la versión actual:

- mantiene pesos no negativos, finitos y con suma uno en ejecuciones válidas;
- repara posiciones nulas con pesos uniformes;
- usa `np.random.default_rng` y `random.Random` locales en la ruta de
  experimentos;
- deriva las réplicas como `seed + seed_index`;
- distingue `gbest` histórico de las métricas de la población actual;
- conserva la diversidad inicial separada de la diversidad posterior al
  movimiento;
- registra `patience` o `max_iterations` en `ConvergenceTrace` cuando la
  traza existe.

Esto permite una sección de estado de validación con enlaces a tests y
reportes. No permite presentar una prueba aprobada como si fuera un conjunto
de resultados de mercado.

### 4.2 Convergencia y estancamiento

La traza nueva contiene, cuando fue persistida, `gbest`, fitness actual,
media/mediana/desviación, `pbest`, mejora, tolerancia, espera de paciencia,
diversidad, distancia máxima al centroide, diversidad relativa, movimiento,
reparaciones, valores inválidos, suma de pesos, retorno medio del mejor y
distancia al target.

Sin embargo, el artefacto histórico inspeccionado no contiene ningún
`diagnostics_*.json`. Por ello:

- sí pueden graficarse los historiales `convergence_<i>.npy` persistidos;
- sí pueden mostrarse sus longitudes y `gbest` histórico;
- no pueden reconstruirse retrospectivamente diversidad por generación,
  movimiento, reparaciones, retorno al target ni causa de terminación para
  ese artefacto;
- no debe rellenarse la ausencia con cálculos inventados ni con una nueva
  ejecución automática.

Los reportes PSO-02 y PSO-02.5 sí aportan tablas históricas de diagnósticos
sintéticos, pero esas tablas deben rotularse con matriz, semilla, versión,
topología, `penalty` y script de origen.

### 4.3 Comparación de experimentos

El artefacto permite comparar directamente:

- CVaR frente a MaxDrawdown;
- Ring frente a Global;
- 30 targets alineados por la misma frontera persistida;
- 20 semillas por configuración;
- pesos, fitness y métricas financieras por target;
- tablas agregadas y tablas por semilla.

La comparación es interpretable solo dentro de grupos con activos, ventana,
intervalo, alpha, número de puntos, enjambre, tolerancias, paciencia,
penalización, modelo de velocidad y política de semillas iguales. En el
artefacto, las cuatro configuraciones comparten esos valores salvo objetivo,
topología y semilla base, por lo que esas comparaciones son razonablemente
controladas para describir diferencias observadas.

No se debe comparar directamente las tablas históricas del artefacto con los
sondeos sintéticos de PSO-02.5: usan matrices, fechas y procedencias
distintas.

### 4.4 Validación matemática

La evidencia más fuerte para presentación es:

- Sphere sobre el simplex: óptimo conocido uniforme, con fitness final y
  pesos por semilla.
- Mínima varianza long-only: referencia independiente por enumeración de
  conjuntos activos, pesos de referencia, fitness de referencia, gap relativo
  y factibilidad.
- CVaR manual: percentil, cola con `<=`, signo positivo de riesgo, distancia al
  target y suma `riesgo + penalización`.
- Tests de entradas, reparación, reproducibilidad y persistencia.

El dashboard debe mostrar valores esperados/obtenidos solamente donde el test
o el reporte los conserva. Para tests que solo devuelven aprobación sin
valores, debe mostrar “aprobado sin resultado numérico persistido”, no
fabricar una tabla.

### 4.5 Convenciones financieras

La evidencia permite presentar las fórmulas actuales:

- `Close` → `log(P_t/P_{t-1})` → matriz `T × N`;
- retorno de cartera implementado como `returns_matrix @ weights`;
- VaR y CVaR en el percentil inferior, con empates incluidos por `<=`;
- riesgo reportado con signo positivo mediante negación;
- drawdown calculado con `cumprod(1 + portfolio_return)`;
- anualización implementada como `(1 + r) ** 252 - 1` por defecto.

Las dos últimas convenciones deben aparecer con advertencias prominentes:
la entrada de producción es logarítmica, mientras que drawdown y
anualización tratan la magnitud como retorno simple diario; además, la UI
ofrece `1wk` y `1mo` sin cambiar automáticamente el factor 252. El dashboard
debe presentar la convención observada, no sustituirla silenciosamente.

## 5. Matriz obligatoria de evidencia

| Tema | Fuente | Tipo de evidencia | Información disponible | Visualización propuesta | Requisitos de comparación | Limitaciones | Estado |
|---|---|---|---|---|---|---|---|
| Invariantes de pesos | `tests/test_pso01.py`, `src/pso/velocity_model.py` | Test y código | No negatividad, finitud, suma uno, reparación uniforme | Tabla de casos con entrada, salida y aserción | Misma versión y política de reparación | No es evidencia de rendimiento financiero | Disponible |
| Reproducibilidad | `tests/test_pso01.py`, `reports/PSO-01.1-reproducibility-coverage.md` | Test y reporte | Semillas, igualdad de pesos/fitness/historias, aislamiento RNG | Tabla de semillas y estado de aprobación | Misma versión, configuración y semilla | No prueba compatibilidad bit a bit con PSO-01 | Disponible |
| Réplicas históricas | `artifacts/experiments.psodata`, `src/experiments.py` | Datos persistidos | 20 semillas por configuración; semillas exactas 42–64 | Selector de configuración, distribución por seed y tabla | Misma configuración salvo seed | No hay estado completo de partículas | Disponible |
| Historial de `gbest` | `artifacts/experiments.psodata/experiments/*/convergence_*.npy` | Historial persistido | 30 historiales por configuración y sus índices/fitness | Curvas individuales, superposición controlada y resumen de longitud | Targets y configuración alineados | No incluye el fitness inicial pre-movimiento separado | Disponible |
| Diagnóstico de diversidad | `src/pso/optimizer.py`, `reports/PSO-02-convergence-diagnostics.md` | Código, reporte y traza opcional | Fórmula, diversidad inicial/post-movimiento, diversidad relativa | Curva de diversidad y relación con `gbest` | Solo trazas con mismo esquema y convención temporal | Ausente en el `.psodata` histórico | Disponible parcialmente |
| Movimiento | `src/pso/optimizer.py`, `reports/PSO-02.5-*` | Código y sondeo sintético | Media/máximo de desplazamiento por generación | Curva de movimiento y tabla final | Misma semilla, RNG Python, topología y versión | Valores históricos reportados discrepan de una reproducción actual | Disponible parcialmente |
| Reparaciones | `ConvergenceTrace`, `reports/PSO-02-convergence-diagnostics.md` | Diagnóstico persistible | Conteo de proyecciones/normalizaciones por generación | Serie y total de reparaciones | Misma definición de `last_repaired` | No existe para el artefacto histórico | Disponible parcialmente |
| Causa de terminación | `ConvergenceTrace`, `tests/test_pso02.py` | Test y diagnóstico | `patience`/`max_iterations`, iteración y espera | Badge de causa y tabla de iteraciones | Traza con esquema 1 | Configuración persistida no declara `max_iterations`; artefacto no tiene diagnósticos | Disponible parcialmente |
| Penalización y fitness | `src/pso/fitness_function.py`, `scripts/decompose_fitness.py`, reportes PSO-02.5 | Código, cálculo derivado y reporte | Riesgo, distancia al target y `lambda * diferencia` | Curvas apiladas riesgo/penalización y tabla de descomposición | Misma matriz, alpha, penalty y target | Descomposición histórica no está en `.psodata`; algunos reportes usan `50` y otros `500` | Disponible parcialmente |
| Comparación Ring/Global | `artifacts/experiments.psodata`, `src/pso/topology.py` | Datos persistidos y código | 30 targets, pesos, fitness, métricas y 20 seeds por topología | Superposición de fronteras y diferencias por target | Activos, ventana, objetivo, parámetros y seeds comparables | No atribuye causalidad ni superioridad global | Disponible |
| Comparación CVaR/MaxDrawdown | `artifacts/experiments.psodata`, `src/pso/fitness_function.py` | Datos persistidos y código | Fitness y métricas para ambos objetivos | Tabla comparativa y curvas separadas | No mezclar fitness de objetivos distintos sin etiqueta | Drawdown conserva discrepancia log/simple | Disponible |
| Sphere y óptimo conocido | `tests/test_pso03.py`, `reports/PSO-03-reference-validation.md` | Test, referencia y resultados numéricos | Fitness, pesos uniformes, semillas, iteraciones | Tabla observado vs esperado y error | Misma función sintética, dimensión y tolerancia | No valida funciones financieras | Disponible |
| Mínima varianza long-only | `tests/test_pso03.py`, `reports/PSO-03-reference-validation.md` | Referencia independiente y experimento | Pesos de referencia, valor, gaps y factibilidad por semilla | Barras de gap y tabla de pesos | Misma covarianza, restricciones y objetivo puro | Adaptador de prueba, no CVaR penalizado | Disponible |
| CVaR manual | `tests/test_pso03.py`, `tests/test_pso04.py` | Test numérico manual | Percentil, cola, signos, penalización y resultado | Tabla de fórmula, esperado y obtenido | Misma muestra y alpha | Valida convención implementada, no validez académica universal | Disponible |
| Retornos y frecuencia | `src/utils.py`, `reports/PSO-04-*`, `tests/test_pso04.py` | Código, test y revisión | `Close`, log returns, `1d/1wk/1mo`, `dropna` | Diagrama de transformación y metadatos de frecuencia | No comparar frecuencias sin normalización | No se verificaron datos reales, duplicados, precios no positivos ni outliers | Disponible con observaciones |
| Drawdown | `src/finance.py`, `src/pso/fitness_function.py`, `reports/PSO-04-R-independent-review.md` | Código, test y auditoría | Fórmula `cumprod(1+r)`, MDD positivo y discrepancia | Fórmula y advertencia, no ranking financiero fuerte | Solo comparar con misma convención de entrada | No representa una riqueza logarítmica exacta ni una política de rebalanceo definida | Disponible parcialmente |
| Anualización | `src/finance.py`, `src/ui/tabs/analysis.py`, `reports/PSO-04-*` | Código y revisión | Factor 252, fórmula y etiqueta de UI | Tabla de unidad/convención y warning | Misma frecuencia y factor explícito | Interpretación de `1wk/1mo` pendiente | Disponible parcialmente |
| Trazabilidad del artefacto | `src/persistence.py`, `artifacts/experiments.psodata` | Esquema y datos persistidos | Configuración, seeds, arrays, Parquet, pesos e historiales | Panel de procedencia y esquema | Verificar presencia/ausencia de cada archivo antes de graficar | Falta `max_iterations` explícito y faltan diagnósticos | Disponible |
| Tests solo aprobados | `tests/*.py`, reportes | Resultado de test | En algunos casos solo existe el estado OK | Tabla de cobertura con “sin valor numérico persistido” | No convertir PASS en resultado experimental | No todos los tests conservan entradas/salidas detalladas | Disponible parcialmente |

## 6. Secciones y visualizaciones recomendadas

### Prioridad 1 — alta utilidad y baja incertidumbre

1. **Resumen de validación.** Tarjetas de estado para PSO-01, PSO-01.1,
   PSO-02, PSO-03 y PSO-04, separando `aprobado`, `aprobado con
   observaciones`, `no recuperable del artefacto` y `pendiente`. Cada tarjeta
   debe enlazar a su reporte y mostrar si la revisión independiente existe.
2. **Fuentes y procedencia.** Panel de solo lectura con ruta del artefacto,
   fecha de archivo, activos, ventana, intervalo, alpha, configuraciones,
   número de targets, semillas y presencia/ausencia de diagnósticos.
3. **Fronteras históricas.** Curvas de fitness, CVaR, MaxDrawdown, retorno
   medio y volatilidad por target, con configuraciones separadas y una tabla
   de valores subyacentes.
4. **Réplicas por semilla.** Distribuciones de fitness y métricas por target,
   usando las tablas `seed_*`; mostrar media, desviación, mínimo y máximo como
   cálculos derivados claramente etiquetados.
5. **Validación matemática.** Tablas observed/expected/error para Sphere,
   mínima varianza y CVaR manual, alimentadas por tests/reportes, sin
   presentarlas como ejecución del artefacto de mercado.

### Prioridad 2 — alto valor, disponibilidad parcial

6. **Convergencia por ejecución.** Usar `convergence_*.npy` históricos para
   `gbest`; habilitar diversidad, movimiento y terminación solo cuando exista
   `diagnostic_histories`.
7. **Diagnóstico de estancamiento.** Para trazas PSO-02 disponibles, mostrar
   cuatro curvas coordinadas: `gbest`, diversidad, movimiento y distancia al
   target. Añadir una clasificación descriptiva (“estancamiento con
   movimiento”, “concentración”, “sin diagnóstico”), no una causa definitiva.
8. **Descomposición del fitness.** Mostrar riesgo y penalización únicamente
   para reportes/scripts o trazas con parámetros compatibles. En el artefacto
   histórico, si solo existe fitness final, mostrar “no reconstruible”.
9. **Comparación Ring/Global.** Superponer curvas solo cuando la selección
   mantenga el mismo objetivo y metadatos controlados; añadir una tabla de
   variables controladas y variables cambiantes.

### Prioridad 3 — advertencias y contexto académico

10. **Convenciones financieras.** Fórmulas actuales, ejemplos manuales y
    advertencias sobre log/simple, drawdown, frecuencia y anualización.
11. **Limitaciones de evidencia.** Página explícita de campos faltantes,
    discrepancias históricas, tests sin valores, `max_iterations` implícito y
    ausencia de datos de estado inicial.

La sección de “Fuentes y metodología” debe ser independiente. La trazabilidad
es necesaria para interpretar cualquier gráfico y no debe quedar escondida en
una nota de la sección de convergencia.

## 7. Arquitectura mínima propuesta

No se requiere una base de datos, un nuevo formato ni dependencias
adicionales. La aplicación debe ser un punto de entrada separado, por ejemplo:

```text
validation_dashboard.py
dashboard/
  __init__.py
  data_access.py
  schemas.py
  derived_metrics.py
  evidence_status.py
  charts.py
  sections/
    summary.py
    provenance.py
    convergence.py
    comparisons.py
    mathematics.py
    finance.py
    limitations.py
```

### Responsabilidades

- `validation_dashboard.py`: `st.set_page_config`, carga del artefacto local o
  archivo seleccionado, y navegación; no debe llamar al controlador de
  experimentos ni a `run_pso`.
- `data_access.py`: lectura de `.psodata` mediante
  `src.persistence.import_payload_from_bytes` o `load_experiments`, lectura
  de rutas de reportes y detección de campos opcionales; nunca escribir.
- `schemas.py`: tipos internos mínimos para distinguir payload histórico,
  `ConvergenceTrace` disponible, resultados de tests y evidencia de reportes.
- `derived_metrics.py`: cálculos descriptivos en memoria, por ejemplo
  agregados por seed, gaps, diferencias entre curvas y porcentajes. Cada
  salida debe marcarse como `derivada`, no como resultado persistido.
- `evidence_status.py`: clasificación de `Disponible`,
  `Disponible parcialmente` y `No recuperable`, con explicación y ruta.
- `charts.py`: gráficos sobre DataFrames/arrays ya cargados; no calcular
  resultados llamando al optimizador.
- `sections/*`: presentación separada por responsabilidad.

### Reutilización recomendada

- Reutilizar `src.persistence.import_payload_from_bytes` para respetar el
  esquema `.psodata` y su compatibilidad legacy.
- Reutilizar `ConvergenceTrace.from_dict` si aparecen diagnósticos JSON.
- Reutilizar `src.finance` solo para cálculos que sean descriptivos de las
  métricas ya persistidas y que conserven sus semánticas documentadas.
- Reutilizar las estructuras `ExperimentsPayload`, `ExperimentResult` y
  `EfficientFrontier` como lectura, no como entrada para ejecutar.
- No reutilizar `run_analysis_pipeline`, `_run_experiments_cached`,
  `run_experiments`, `run_pso` ni la interfaz de `app.py`: todos ellos pueden
  descargar datos, ejecutar PSO o persistir resultados.

La aplicación debe comprobar antes de mostrar cada gráfico que las longitudes,
targets, semillas y esquema sean compatibles. Un archivo histórico sin
diagnósticos debe producir un panel informativo, no una excepción silenciosa
ni valores predeterminados.

## 8. Lagunas de evidencia no resolubles con los datos actuales

1. No se puede reconstruir diversidad, movimiento, reparaciones, retorno al
   target ni causa de terminación de `artifacts/experiments.psodata` porque no
   contiene `diagnostics_*.json`.
2. No se puede recuperar el fitness de la población inicial como una serie
   separada; `convergence_history[0]` es posterior al primer movimiento y la
   diversidad inicial está en otra historia.
3. No se puede probar desde el artefacto que una corrida alcanzó un óptimo
   global ni una frontera eficiente de Markowitz.
4. No se puede atribuir causalmente una diferencia Ring/Global solo a la
   topología si se mezclan objetivos, seeds o metadatos.
5. No se puede medir sensibilidad a `penalty` usando únicamente el `.psodata`;
   la sensibilidad documentada es sintética y no forma parte del artefacto.
6. No se puede reconciliar completamente la discrepancia histórica de
   diversidad/movimiento (`0.165243/0.380720` frente a
   `0.282498/0.586855`) porque faltan la traza histórica, la versión exacta,
   ambos RNG y toda la configuración de origen.
7. No se puede afirmar que el valor `penalty=500` del artefacto sea comparable
   con los diagnósticos de `diagnose_convergence.py`, que usa `CVaR()` y por
   tanto `penalty=50` por defecto.
8. No se puede interpretar MDD como una métrica financiera validada de
   buy-and-hold o de una cartera reequilibrada sin fijar la trayectoria de
   riqueza.
9. No se puede considerar correcta la anualización para `1wk` o `1mo` con la
   información actual; la UI conserva la observación y aplica una convención
   basada en 252.
10. No se puede convertir un resultado `PASS` de un test sin aserciones
    numéricas persistidas en una tabla de resultados observados.
11. No se puede cerrar la trazabilidad completa de `max_iterations`: el valor
    efectivo es 1000 por defecto de `pso()`, pero no forma parte de
    `ExperimentConfig` ni de la configuración persistida.
12. No se puede validar con datos de mercado nuevos sin violar el alcance de
    solo lectura de esta fase.

## 9. Plan de implementación por etapas

### Etapa 1 — Lectura y procedencia

- Cargar `.psodata` sin ejecutar PSO.
- Mostrar esquema, configuración, semillas, tamaños y campos opcionales.
- Implementar estados de evidencia y mensajes para archivos ausentes.
- Validar lectura con el artefacto actual, que carece de diagnósticos.

### Etapa 2 — Resumen y tablas históricas

- Implementar resumen de validación y panel de fuentes.
- Mostrar fronteras, métricas por target y pesos.
- Añadir réplicas por semilla y agregados derivados.
- Etiquetar persistentemente cada tabla como observada o derivada.

### Etapa 3 — Matemática y convenciones

- Presentar resultados de tests/reportes con expected/observed cuando existan.
- Añadir fórmulas de retornos, VaR/CVaR, drawdown y anualización.
- Incorporar warnings de PSO-04 y evitar correcciones silenciosas.

### Etapa 4 — Convergencia disponible

- Graficar `convergence_*.npy` históricos.
- Añadir soporte condicional de `ConvergenceTrace` para artefactos futuros.
- Mostrar generación 0, diversidad inicial y primera generación con etiquetas
  temporales explícitas.

### Etapa 5 — Comparaciones controladas y limitaciones

- Implementar Ring/Global y CVaR/MaxDrawdown con filtros de compatibilidad.
- Mostrar variables controladas/cambiantes antes de cada comparación.
- Integrar la matriz de evidencia y la lista de lagunas.
- Probar que la app no importa ni llama rutas de ejecución del optimizador.

El mayor valor con menor incertidumbre está en las etapas 1 y 2. La
descomposición por generación y el diagnóstico de estancamiento deben esperar
a artefactos con diagnósticos persistidos o presentarse solo como evidencia
sintética claramente rotulada.

## 10. Decisiones que requieren revisión antes de implementar

- Resolver si esta entrega documental se registra como una tarea nueva
  separada del PSO-07 del roadmap o si se renombra antes de comenzar PSO-08.
- Decidir si el dashboard aceptará un `.psodata` seleccionado por el usuario,
  solo el artefacto local, o ambos; en todos los casos debe permanecer
  exclusivamente de lectura.
- Aprobar la convención de etiquetas para generación 0 y para cálculos
  derivados sobre resultados persistidos.
- Decidir qué resultados de tests se consideran aptos para exposición
  académica cuando solo existe `PASS` sin valor numérico.
- Definir si una comparación Ring/Global se presentará como descriptiva o si
  se esperará una revisión metodológica adicional.
- Resolver académicamente las observaciones de PSO-04 sobre drawdown,
  frecuencia, anualización y trayectoria de riqueza antes de presentar
  conclusiones financieras fuertes.
- Determinar si se requiere una nueva generación autorizada de artefactos con
  diagnósticos para habilitar la sección completa de convergencia.

## 11. Criterios de aceptación de esta fase

| Criterio | Estado |
|---|---|
| Inventario de rutas verificadas | Cumplido en las secciones 2 y 3 |
| Matriz de evidencia con las columnas solicitadas | Cumplido en la sección 5 |
| Distinción entre observado, derivado y no recuperable | Cumplido en todo el reporte; explícito en secciones 4, 5 y 8 |
| Propuesta priorizada de secciones y visualizaciones | Cumplido en la sección 6 |
| Arquitectura mínima y funciones reutilizables | Cumplido en la sección 7 |
| Lagunas de evidencia | Cumplido en la sección 8 |
| Plan de implementación por etapas | Cumplido en la sección 9 |
| No implementar la aplicación ni ejecutar experimentos | Cumplido; solo se hicieron lecturas estructurales del repositorio y del `.psodata` |
| Revisión independiente de este reporte | Pendiente |

**Conclusión:** existe evidencia suficiente para comenzar con procedencia,
resumen, tablas históricas, réplicas, validación matemática documentada y
advertencias financieras. La visualización completa de convergencia,
estancamiento y descomposición del fitness no es recuperable desde el
artefacto histórico actual y debe quedar condicionada a diagnósticos
persistidos compatibles, sin ejecutar nuevos experimentos automáticamente.
