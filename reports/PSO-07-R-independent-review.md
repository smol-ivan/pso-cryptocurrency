# PSO-07-R — Revisión independiente del inventario de evidencia

## 1. Identificación, alcance y estado

- **Fecha:** 2026-10-21.
- **Rama:** `main`, `ahead 2` respecto de `origin/main`.
- **Reporte revisado:** `reports/PSO-07-dashboard-evidence-inventory.md`.
- **Objetivo:** verificar la fidelidad del inventario, resolver la discrepancia
  de historiales y evaluar la viabilidad de un dashboard estrictamente de
  solo lectura.
- **Modo:** revisión documental y estructural, sin modificar producción,
  pruebas, scripts, artefactos o interfaz; sin commits.

El roadmap usa PSO-07 para “Diseñar experimentos reproducibles”, mientras que
la solicitud actual usa PSO-07 para inventario y dashboard. La ambigüedad se
mantiene documentada; no se cambió el estado del roadmap ni se renombraron
tareas.

## 2. Archivos inspeccionados

Se revisaron:

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `docs/ai/WORK_PROTOCOL.md`
- `docs/ai/prompts/README.md`
- `reports/README.md`
- `reports/PSO-07-dashboard-evidence-inventory.md`
- `src/persistence.py`
- `src/models/state.py`
- `src/experiments.py`
- `src/run_pso.py`
- `src/finance.py`
- `src/controllers/experiment_controller.py`
- `src/pso/optimizer.py`
- `tests/test_pso01.py` a `tests/test_pso04.py`
- `reports/PSO-01*`, `reports/PSO-02*`, `reports/PSO-03*` y
  `reports/PSO-04*`, incluidas las revisiones independientes
- `artifacts/experiments.psodata`

## 3. Métodos de comprobación y limitaciones

Se hicieron únicamente lecturas y cálculos descriptivos sobre el ZIP
persistido:

| Comprobación | Resultado |
|---|---|
| Estado del árbol | `main...origin/main [ahead 2]`; cambios preexistentes conservados |
| Tipo de artefacto | ZIP `.psodata`; no contiene `experiments.pkl` |
| Conteo de rutas `convergence_*.npy` | 2.520 |
| Separación por nivel | 120 en fronteras principales y 2.400 en `seeds/` |
| Comparación principal contra réplica 0 | 120 de 120 historiales coinciden byte a byte a nivel de array |
| Targets principales contra réplica 0 | 4 de 4 configuraciones coinciden exactamente |
| Pesos principales contra réplica 0 | 4 de 4 configuraciones coinciden exactamente |
| Tablas principales contra filas `seed_index=0` | Coinciden exactamente en las 9 columnas métricas |
| Diagnósticos JSON | 0 archivos `diagnostics_*.json` |
| Ejecuciones nuevas | Ninguna |

No se ejecutaron tests, PSO, scripts diagnósticos, Streamlit, Yahoo Finance ni
backtesting. Los valores numéricos de Sphere, mínima varianza y CVaR se
contrastaron contra reportes y fuentes de test, no se regeneraron.

## 4. Resultado de la investigación de los 2.520 historiales

### 4.1 Conteo exacto

El inventario cuenta correctamente el contenido físico del archivo:

\[
4 \text{ configuraciones} \times 30 \text{ targets} \times
(1 \text{ frontera principal} + 20 \text{ réplicas}) = 2.520.
\]

La cuenta esperada de ejecuciones de réplicas es:

\[
4 \times 30 \times 20 = 2.400.
\]

La diferencia de 120 no corresponde a una réplica adicional ni a entradas
auxiliares. Es la frontera principal de cada configuración:

| Configuración | Principal | Réplicas anidadas | Total físico |
|---|---:|---:|---:|
| `CVaR | Inertia | Ring` | 30 | 600 | 630 |
| `CVaR | Inertia | Global` | 30 | 600 | 630 |
| `MaxDrawdown | Inertia | Ring` | 30 | 600 | 630 |
| `MaxDrawdown | Inertia | Global` | 30 | 600 | 630 |
| **Total** | **120** | **2.400** | **2.520** |

### 4.2 Por qué existe la duplicación

`run_experiments()` construye `seed_results`, asigna:

```python
frontier = seed_results[0]
frontier.seed_results = seed_results
```

Por tanto, la frontera principal es el mismo objeto lógico que la réplica de
índice 0. `export_payload_to_bytes()` escribe primero `frontier` en
`experiments/<i>/` y después vuelve a escribir todos los elementos de
`frontier.seed_results` en `experiments/<i>/seeds/<seed_index>/`.

La comprobación del artefacto confirma que para cada configuración:

- `experiments/<i>/convergence_<j>.npy` coincide exactamente con
  `experiments/<i>/seeds/0/convergence_<j>.npy`;
- `target_values.npy` coincide con la réplica 0;
- `weights.npy` coincide con la réplica 0;
- `best_fitnesses.npy` también representa la misma frontera principal y
  réplica 0;
- las nueve columnas métricas de `dataframes/<config>.parquet` coinciden con
  las filas `seed_index=0` de `dataframes/seed_<config>.parquet`.

**Conclusión:** la discrepancia está explicada y no es un error de ejecución.
Sí es un riesgo de interpretación: un lector que cuente todos los archivos
como ejecuciones independientes duplicará la réplica 0 y calculará
distribuciones sesgadas.

### 4.3 Estructura interna y semántica

Cada historial persistido tiene forma `(n_generaciones, 2)` y almacena las
columnas `[iteration, gbest]`. Las longitudes varían por target y
configuración; no representan un tensor rectangular ni una réplica
inexistente. La primera fila usa el índice temporal de la historia de
convergencia, que en la implementación se registra después del primer
movimiento de la población. No representa el mejor fitness inicial separado.

La relación física es determinista:

```text
configuración i
  target/portfolio index j
    frontera principal: experiments/i/convergence_j.npy
    réplica s:          experiments/i/seeds/s/convergence_j.npy
```

No existe un manifiesto por historial con campos redundantes como
`config_name`, `target`, `seed` y `schema_version`. La relación puede
reconstruirse porque `metadata.json`, `config.json`, `target_values.npy` y
las posiciones de `point_index` están disponibles, pero no debe depender de
un `glob` plano ni de la numeración global de archivos.

## 5. Semillas y comparaciones Ring/Global

### 5.1 Semillas persistidas

La política de código es `seed = config.seed + seed_index`. El artefacto
contiene:

| Configuración | Semilla base | Semillas efectivas |
|---|---:|---|
| CVaR / Inertia / Ring | 42 | 42–61 |
| CVaR / Inertia / Global | 43 | 43–62 |
| MaxDrawdown / Inertia / Ring | 44 | 44–63 |
| MaxDrawdown / Inertia / Global | 45 | 45–64 |

La semilla efectiva se almacena en `metadata.json` como `seed_values`.
`seed_metrics_by_config` conserva `seed_index`, no la semilla efectiva. Por
ello, la asociación correcta para una tabla por semilla es:

```text
effective_seed = metadata.experiments[config_index].seed_values[seed_index]
```

La tabla por semilla no es autosuficiente si se extrae sin el metadata del
artefacto.

### 5.2 Asociación entre semilla, target, métricas e historial

Dentro de una configuración, la asociación es verificable por dos índices:

- `seed_index` identifica la réplica y `seed_values[seed_index]` su semilla;
- `portfolio_index` identifica el target en `target_values` y el archivo
  `convergence_<portfolio_index>.npy`.

Las métricas por semilla tienen 30 filas por `seed_index`, con
`portfolio_index`, `target_return` y métricas. Los historiales anidados usan
el mismo índice de target y la misma configuración/seed del path. Esta
relación es exacta para el artefacto inspeccionado, pero es una convención de
estructura, no un identificador persistido dentro del `.npy`.

La frontera principal corresponde a `seed_index=0`, no a una corrida
independiente adicional. Un dashboard debe marcarla como alias de la réplica
0 o excluirla de los agregados por réplica.

### 5.3 Seeds comunes Ring/Global

Ring CVaR usa 42–61 y Global CVaR usa 43–62. Por tanto, las semillas comunes
son 43–61. Para MaxDrawdown, las semillas comunes son 45–63.

Las semillas comunes tienen índices distintos entre configuraciones:

- CVaR: Ring `seed_index=1..19` corresponde a Global
  `seed_index=0..18`;
- MaxDrawdown: Ring `seed_index=1..19` corresponde a Global
  `seed_index=0..18`.

El dashboard puede construir comparaciones pareadas por semilla efectiva
uniendo `seed_values`, no uniendo directamente `seed_index`.

### 5.4 Variables controladas y variables cambiantes

En el artefacto, Ring y Global dentro del mismo objetivo comparten:

- activos, ventana, intervalo y matriz de retornos;
- 30 targets y el mismo vector de `target_values`;
- modelo Inertia;
- `n_swarm=100`;
- `rtol=1e-4`, `atol=1e-8`, paciencia 10;
- `alpha=0.95`, `penalty=500`;
- `c1=1.7`, `c2=1.7`, `inertia=0.8`.

Cambian la topología y la semilla base/configuración. Al emparejar por semilla
efectiva, la semilla deja de ser una diferencia entre la pareja. Así, las
comparaciones pareadas Ring/Global para CVaR y para MaxDrawdown son válidas
como comparaciones descriptivas de la topología en las semillas comunes.

No son válidas como prueba de superioridad global, causalidad financiera o
frontera eficiente. Tampoco debe compararse el primer resultado de Ring con el
primer resultado de Global como si usaran la misma semilla: usan 42 y 43, o
44 y 45, respectivamente.

## 6. Integridad y semántica del artefacto

Las afirmaciones estructurales del inventario se verificaron:

| Elemento | Resultado |
|---|---|
| Activos | `BTC-USD`, `ETH-USD`, `SOL-USD`, `ADA-USD` |
| Ventana e intervalo | `2020-01-01` a `2024-01-01`, `1d` |
| Alpha | `0.95` |
| Retornos de optimización | matriz persistida con 1.360 filas y 4 columnas |
| Retornos de backtesting | matriz persistida con 1.017 filas y 4 columnas |
| Configuraciones | 4, exactamente las descritas |
| Targets | 30 por configuración; los targets son iguales entre las cuatro |
| Pesos | 30 filas × 4 activos por frontera y por réplica |
| Métricas principales | 30 filas × 9 columnas métricas por configuración |
| Métricas por semilla | 600 filas × 12 columnas por configuración |
| Convergencia | 30 historias principales y 20 × 30 historias anidadas |
| Diagnósticos | Ausentes en todo el archivo |

La configuración persistida conserva objetivo, velocidad, topología, targets,
tamaño del enjambre, tolerancias, paciencia, seed base, seed count y
parámetros de fitness/modelo/topología. No conserva `max_iterations`; su valor
efectivo queda implícito en el default `1000` de `pso()`.

`src/persistence.py` lee historiales mediante un bucle creciente de
`convergence_<point_index>.npy` y se detiene en el primer índice ausente. Esto
funciona para el artefacto actual, cuyos índices son contiguos, pero un lector
de dashboard debe validar continuidad, cantidad esperada y forma antes de
graficar. El lector también deja `diagnostic_histories=None` cuando no
encuentra diagnósticos; esa ausencia debe mostrarse explícitamente.

El campo `diagnostics_schema_version` aparece en el metadata del exportador,
pero la ausencia de archivos de diagnóstico significa que no hay una traza
diagnóstica que consumir. No debe confundirse la declaración de esquema con
la existencia de diagnósticos.

## 7. Trazabilidad de la evidencia matemática

### Sphere

Los reportes de PSO-03 y su revisión independiente conservan valores
numéricos por semillas 11–15: fitness final, iteraciones, motivo y criterio
de pesos cercanos al vector uniforme. El test define el caso, el óptimo
uniforme y las aserciones, pero no escribe una tabla de resultados. El
dashboard puede mostrar los números del reporte como evidencia histórica
documentada y debe indicar que no provienen del `.psodata` de mercado.

### Mínima varianza long-only

El reporte conserva la referencia independiente:

```text
w* = [0.6461538462, 0.2051282051, 0.1487179487]
f* = 0.027897435897435898
```

También conserva resultados PSO por cinco semillas, gaps relativos y pesos.
La referencia es una enumeración de conjuntos activos para una matriz de
covarianza de prueba; no es la función CVaR penalizada del artefacto histórico.
Debe mostrarse como benchmark sintético independiente, no como validación
financiera del archivo persistido.

### CVaR manual

Los reportes y tests conservan el caso `alpha=0.50`, cola inferior, empates
con `<=`, riesgo positivo `0.15` y fitness penalizado `7.65`. Es evidencia
numérica de la convención implementada. No demuestra que CVaR sea la
convención financiera académica correcta ni que el PSO encuentre su óptimo.

### Reproducibilidad, factibilidad y reparación

Los reportes y tests conservan aserciones y descripciones de:

- suma de pesos uno, no negatividad y finitud;
- reparación uniforme del vector nulo;
- aislamiento de generadores y semillas de réplicas;
- igualdad de resultados dentro de la versión actual.

Cuando el reporte incluye valores concretos, pueden presentarse directamente.
Cuando el repositorio solo conserva `PASS`/`OK` o aserciones sin salida
numérica, el dashboard debe mostrar “prueba aprobada; resultado numérico no
persistido”. No debe ejecutar el test para llenar esa tabla.

## 8. Evaluación de la propuesta de dashboard

### 8.1 Lectura del `.psodata`

`import_payload_from_bytes()` abre el ZIP en modo lectura, lee bytes, arrays,
Parquet y JSON, y construye objetos en memoria. No llama al controlador, no
ejecuta `run_pso()` y no escribe el archivo. Es apropiada como ruta principal
para un dashboard de solo lectura, siempre que se añada validación explícita
del esquema y de las cantidades esperadas.

`load_experiments()` también lee el `.psodata` local sin escribir. Sin embargo,
si no existe el `.psodata`, puede abrir `artifacts/experiments.pkl` mediante
`pickle`. Para un dashboard que admita archivos seleccionados por el usuario,
no debe usarse ese fallback con archivos no confiables. La ruta segura de
diseño es aceptar el formato ZIP `.psodata`, inspeccionar sus entradas y
rechazar formatos legacy no necesarios para esta aplicación.

### 8.2 Punto de entrada y superficies que deben excluirse

El punto de entrada independiente puede cargar `import_payload_from_bytes`
directamente. Debe evitar:

- `app.py`;
- `run_analysis_pipeline`;
- `_run_experiments_cached`;
- `run_experiments`;
- `run_pso`;
- `save_experiments`;
- `load_crypto_returns`.

Estas rutas pueden ejecutar optimizaciones, descargar datos o persistir
resultados. `src.finance` contiene funciones descriptivas puras, pero su uso
debe limitarse a recalcular en memoria magnitudes cuyo significado esté
documentado; no debe utilizarse para sustituir silenciosamente las métricas
persistidas ni para corregir drawdown/anualización.

### 8.3 Cálculos derivados

Son seguros y trazables en memoria:

- medias, desviaciones, mínimos y máximos de las tablas por semilla;
- diferencias pareadas por target y semilla efectiva;
- gaps de benchmarks ya documentados;
- conteos, longitudes y comprobaciones de factibilidad de pesos persistidos;
- descomposición descriptiva solo si están disponibles `risk`, target,
  alpha, penalty y los pesos compatibles.

No son seguros como reconstrucción histórica:

- causa de terminación cuando solo existe `convergence_history`;
- diversidad, movimiento o reparaciones ausentes;
- fitness inicial antes del primer movimiento;
- seed efectiva si se separa la tabla de `metadata.json`;
- sensibilidad a penalty no contenida en el artefacto.

### 8.4 Historiales huérfanos y esquemas incompatibles

El dashboard debe rechazar o marcar como incompleto cualquier caso en que:

- falte `config.json`, `target_values.npy`, `weights.npy` o
  `best_fitnesses.npy`;
- los tamaños no coincidan con `num_points`;
- falte un índice intermedio de `convergence_<i>.npy`;
- el historial no tenga dos columnas o sus iteraciones no sean coherentes;
- `seed_values` no tenga la misma longitud que `seed_frontiers`;
- una tabla por semilla no tenga `seed_index`, `portfolio_index` o
  `target_return`;
- aparezcan diagnósticos con un esquema desconocido;
- una comparación carezca de metadatos comunes.

La respuesta debe ser un mensaje explícito de evidencia no disponible, no una
serie vacía presentada como resultado ni un valor default inventado.

## 9. Matriz de afirmaciones del inventario

| Afirmación del inventario | Estado de revisión | Evidencia y precisión |
|---|---|---|
| El artefacto es ZIP `.psodata` | **Verificada** | Estructura ZIP y `metadata.json` inspeccionados |
| Hay 4 configuraciones | **Verificada** | Cuatro entradas de `metadata["experiments"]` y cuatro `config.json` |
| Hay 30 targets por configuración | **Verificada** | `target_values.npy` y Parquet tienen 30 filas |
| Hay 20 réplicas por configuración | **Verificada** | 20 `seed_frontiers` y 20 valores por `seed_values` |
| Las semillas son 42–61, 43–62, 44–63 y 45–64 | **Verificada** | Metadata y regla `seed + seed_index` |
| Hay 2.520 historiales | **Verificada con aclaración** | 120 principales + 2.400 anidados; 120 son duplicados lógicos de seed 0 |
| Los 2.520 representan 2.520 ejecuciones independientes | **No verificada / incorrecta** | La frontera principal es `seed_results[0]` y coincide con `seeds/0` |
| No hay diagnósticos JSON | **Verificada** | Cero `diagnostics_*.json` |
| Las tablas por semilla tienen semillas efectivas explícitas | **Verificada parcialmente** | Las tablas solo tienen `seed_index`; el seed efectivo está en metadata |
| Los historiales se pueden asociar por configuración, target y seed | **Verificada parcialmente** | Asociación exacta por path/metadata/índice; no hay manifest embebido por `.npy` |
| Ring/Global usan exactamente las mismas semillas por posición | **No verificada** | Las bases difieren; solo son pareables tras unir por seed efectiva |
| Ring/Global tienen solo topología como diferencia al emparejar seeds | **Verificada para comparación descriptiva** | Objetivo, modelo, parámetros y datos coinciden; la semilla se iguala por join |
| Las tablas principales son independientes de las tablas por semilla | **No verificada / incorrecta** | Coinciden exactamente con `seed_index=0` |
| Se pueden mostrar curvas históricas de `gbest` | **Verificada** | Historias `(iteration, gbest)` persistidas |
| Se puede mostrar diversidad/movimiento/terminación del artefacto | **No verificada** | Faltan `diagnostics_*.json` |
| Sphere, mínima varianza y CVaR tienen números en reportes | **Verificada** | Reportes PSO-03 y revisión independiente conservan tablas/valores |
| Todos los tests ofrecen resultados numéricos persistidos | **No verificada** | Varias pruebas solo dejan aserciones y estado OK |
| `import_payload_from_bytes` es lectura sin ejecución de PSO | **Verificada** | La ruta solo lee ZIP y construye objetos |
| `load_experiments` es apropiada sin reservas para archivos externos | **Verificada parcialmente** | Fallback a pickle requiere restringir formato o confianza |

## 10. Hallazgos clasificados

| ID | Severidad | Archivo/ubicación | Evidencia concreta | Impacto | Recomendación mínima |
|---|---|---|---|---|---|
| PSO-07-R-01 | **Medio** | `src/experiments.py:66-69`, `src/persistence.py:244-258` | `frontier = seed_results[0]`; el exportador escribe la frontera principal y luego todas las réplicas. Los 120 historiales principales coinciden con `seeds/0`. | Un conteo plano de 2.520 duplica 120 ejecuciones y sesga agregados o distribuciones. | Tratar `experiments/<i>/` como alias de seed 0; contar réplicas solo bajo `seeds/`; mostrar ambos niveles con etiquetas distintas. |
| PSO-07-R-02 | **Medio** | `metadata.json`, tablas `seed_*`, `src/finance.py:74-82` | `seed_values` está en metadata, pero Parquet conserva solo `seed_index`; Ring y Global tienen bases distintas. | Un dashboard que una por `seed_index` afirmará pareamiento incorrecto y asignará semillas equivocadas. | Resolver siempre `effective_seed` desde metadata y emparejar por seed efectiva, no por índice. |
| PSO-07-R-03 | **Medio** | `src/persistence.py:226-239`, `src/run_pso.py:23-27` | Los `.npy` no contienen configuración, target ni seed; la relación se infiere por path e índice. | Un lector que mezcle archivos por nombre global puede asociar una curva con otra ejecución. | Mantener una clave interna `(config_index, seed_index, portfolio_index)` y validar targets, tamaños y continuidad antes de graficar. |
| PSO-07-R-04 | **Medio** | `src/persistence.py:417-432` | `load_experiments()` cae a `pickle.load()` si falta `.psodata`. | La aplicación seguiría siendo “solo lectura” en escritura, pero no sería una ruta segura para archivos externos no confiables. | Para el dashboard, aceptar únicamente ZIP `.psodata` o usar el fallback solo con artefactos locales confiables y advertencia explícita. |
| PSO-07-R-05 | **Medio** | `src/persistence.py:326-350`, `src/pso/optimizer.py` | La lectura de historiales se detiene en el primer índice ausente y el artefacto no conserva `max_iterations` ni diagnóstico inicial. | Un esquema incompleto puede producir una historia truncada o una interpretación temporal excesiva sin error explícito. | Validar cantidad/continuidad/forma y etiquetar `gbest[0]` como post-movimiento; no inferir causa de parada. |
| PSO-07-R-06 | **Bajo** | `reports/PSO-07-dashboard-evidence-inventory.md`, sección de comparaciones | El inventario declara Ring/Global disponibles y controlados, pero no explicita que sus semillas base difieren ni que la tabla principal es seed 0. | Puede inducir comparaciones visuales no pareadas aunque el diseño general advierte controlar metadatos. | Añadir al diseño la tabla de semillas comunes y la regla de join por seed efectiva. |
| PSO-07-R-07 | **Bajo** | Tests PSO-01 a PSO-04 y reportes | Los tests contienen aserciones, pero no todos preservan outputs numéricos fuera de los reportes. | Un panel “resultado del test” puede sugerir más detalle del disponible. | Mostrar estado PASS separado de valores observados; usar reportes solo cuando contengan el número. |

No se encontró un defecto que impida construir el dashboard completo si se
aplican las restricciones anteriores. Sí existen riesgos medios de doble
conteo, pareamiento de semillas, asociación por índice y manejo de formatos
externos. Son riesgos de lectura/interpretación, no evidencia de que el PSO
haya producido ejecuciones incorrectas.

## 11. Recomendaciones mínimas para el dashboard

1. Cargar el artefacto mediante `import_payload_from_bytes()` y aceptar solo
   el ZIP `.psodata` en la primera versión.
2. Construir un catálogo interno explícito por configuración, semilla efectiva
   y target:
   `(config_name, effective_seed, portfolio_index, target_value)`.
3. Excluir `experiments/<i>/` de los agregados por réplica o marcarlo como
   alias exacto de `seed_index=0`.
4. Enriquecer las tablas por semilla con `effective_seed` desde metadata antes
   de cualquier gráfica o comparación.
5. Permitir comparación pareada Ring/Global únicamente para semillas comunes:
   CVaR 43–61 y MaxDrawdown 45–63.
6. Mostrar comparaciones no pareadas como distribuciones descriptivas, no como
   experimentos controlados por semilla.
7. Graficar `gbest` solo con las dos columnas persistidas; habilitar
   diversidad, movimiento, reparaciones y terminación únicamente cuando haya
   una `ConvergenceTrace` compatible.
8. Añadir validaciones de continuidad, shape, longitud, targets, weights,
   tablas y metadata antes de renderizar.
9. Mostrar advertencias sobre `max_iterations` implícito, generación 0
   post-movimiento y ausencia de fitness inicial separado.
10. Mantener separadas las evidencias sintéticas de PSO-03 de las métricas del
    artefacto de mercado.
11. No importar el controlador de experimentos ni llamar rutas de ejecución o
    persistencia desde el punto de entrada.

## 12. Criterios de aceptación

| Criterio | Estado |
|---|---|
| Resolver o dejar explícita la discrepancia 2.400/2.520 | Cumplido: 120 principales duplican seed 0; 2.400 réplicas anidadas |
| Clasificar comparaciones Ring/Global | Cumplido: pareadas solo tras unir por seed efectiva; descriptivas en los demás casos |
| Comprobar trazabilidad config/target/seed/historial | Cumplido con límite: relación por path/metadata/índice, no manifest embebido |
| Contrastar afirmaciones del inventario | Cumplido en la matriz de la sección 9 |
| Evaluar efectos secundarios de lectura | Cumplido: ZIP es lectura; fallback pickle requiere restricción |
| Verificar que no se generó evidencia nueva | Cumplido: no se ejecutaron PSO, tests, scripts ni descargas |
| Reporte independiente sin tocar producción | Cumplido; solo se creó este archivo |

## 13. Veredicto

**Aprobado con observaciones.**

El inventario es fiel en sus conteos físicos, configuraciones, dimensiones,
metadatos principales y ausencia de diagnósticos. La discrepancia de 2.520
historiales queda explicada como 120 fronteras principales duplicadas
lógicamente respecto de `seed_index=0`, no como una quinta réplica ni como
ejecuciones adicionales. Las tablas, pesos y historiales pueden relacionarse
de forma reproducible si el lector conserva el contexto de configuración,
seed efectiva y `portfolio_index`.

La implementación del dashboard puede comenzar para procedencia, tablas,
fronteras, réplicas y `gbest`, siempre que se evite el doble conteo y se
emparejen Ring/Global por semilla efectiva. Las visualizaciones de diversidad,
movimiento, reparaciones y causa de terminación deben quedar deshabilitadas o
marcadas como no recuperables para el artefacto actual. La evidencia
matemática puede presentarse desde los reportes, separando números históricos
documentados de tests cuyo único resultado conservado es `PASS`.

No se requiere corregir producción ni regenerar el artefacto para iniciar una
primera versión de solo lectura. Antes de presentar conclusiones académicas
fuertes, deben mantenerse las advertencias sobre `max_iterations`, generación
0, convenciones financieras y la procedencia sintética de PSO-03.
