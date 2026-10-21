# Auditoría técnica y documentación contextual

## 1. Resumen ejecutivo

Este repositorio implementa una aplicación académica para explorar la
optimización de portafolios de criptomonedas mediante Particle Swarm
Optimization (PSO). La interfaz es una aplicación Streamlit (`app.py`) que
descarga precios históricos desde Yahoo Finance, construye una matriz de
rendimientos logarítmicos, ejecuta varias configuraciones de PSO y presenta
fronteras de riesgo-rendimiento, composición, convergencia y un backtesting
posterior.

El estado observado es el de un prototipo experimental funcional, no el de un
motor financiero validado. La separación general entre interfaz, controlador,
finanzas, PSO, persistencia y visualización es clara, y existen mecanismos de
caché, persistencia `.psodata` y corridas multi-seed. Sin embargo, la
formulación actual no impone el retorno objetivo como restricción exacta:
minimiza una métrica de riesgo más una penalización por distancia al objetivo.
Por tanto, las curvas llamadas “fronteras eficientes” deben interpretarse como
soluciones aproximadas de problemas penalizados.

Los principales puntos que requieren investigación antes de usar resultados
como evidencia académica son:

1. La reproducibilidad anunciada no está completamente garantizada: se fija
   `numpy.random`, pero el modelo de velocidad usa también
   `random.random()` sin fijar la semilla de la biblioteca estándar.
2. CVaR, VaR y las demás métricas son estimaciones históricas sobre retornos
   logarítmicos; la interpretación financiera, el tamaño de muestra de cola y
   la convención de signos deben validarse para cada experimento.
3. La penalización `risk + penalty * abs(mean_return - target)` depende de la
   escala arbitraria de `penalty` y no equivale a la restricción clásica de
   Markowitz.
4. No hay pruebas automatizadas ni comparación contra soluciones de referencia
   o problemas sintéticos conocidos.
5. La anualización está fijada a 252 períodos aunque la interfaz permite
   frecuencias diaria, semanal y mensual.

Estas observaciones no demuestran que todos los resultados sean inválidos;
delimitan qué propiedades están implementadas, cuáles son supuestos y cuáles
aún no tienen validación suficiente.

## 2. Stack tecnológico

### Dependencias directas declaradas

Las dependencias están en `pyproject.toml` y se fijan mediante `uv.lock`.

| Tecnología | Uso confirmado |
|---|---|
| Python `>=3.12` | Lenguaje y entorno de ejecución. |
| NumPy | Matrices de rendimientos, álgebra de portafolios, aleatoriedad, estadísticas y arrays persistidos. |
| pandas | Fechas, tablas de métricas, índices, lectura/escritura de Parquet y selección de datos. |
| yfinance | Descarga de precios históricos desde Yahoo Finance. |
| Streamlit | Interfaz, formularios, estado de sesión, caché, mensajes y pestañas. |
| Plotly | Gráficas interactivas de fronteras, convergencia, composición y rendimiento acumulado. |

El lockfile incluye dependencias transitivas de esas herramientas, entre ellas
PyArrow para Parquet, Altair/PyDeck y componentes internos de Streamlit,
`curl-cffi`, `requests` y `peewee` asociados a `yfinance`. No se observan
dependencias de SciPy, cvxpy, scikit-learn, bases de datos ni frameworks de
testing declarados.

### Ejecución documentada

El `README.md` indica:

```sh
uv sync
uv run streamlit run app.py
```

La aplicación requiere conectividad externa durante la descarga de precios
históricos y del período de backtesting. No se observan claves API ni
credenciales en el repositorio.

## 3. Mapa del repositorio

| Ruta | Responsabilidad observada |
|---|---|
| `app.py` | Punto de entrada Streamlit; controles de configuración, carga/exportación de datos y composición de pestañas. |
| `src/controllers/experiment_controller.py` | Orquesta descarga, caché, validación, construcción de configuraciones, ejecución, métricas, backtesting y persistencia. |
| `src/utils.py` | Descarga de precios y conversión a matriz de rendimientos logarítmicos. |
| `src/experiments.py` | Define `ExperimentConfig`/`ExperimentResult` y repite ejecuciones por configuración y semilla. |
| `src/run_pso.py` | Define `PSOInputData`, `EfficientFrontier` y ejecuta un PSO por cada retorno objetivo. |
| `src/pso/optimizer.py` | Inicialización de partículas, ciclo PSO, actualización de mejores posiciones, convergencia y diversidad. |
| `src/pso/particle.py` | Estado mutable de una partícula: posición, velocidad, `best_pos` y `best_val`. |
| `src/pso/fitness_function.py` | Interfaz de aptitud y clases `CVaR`, `VaR`, `Variance`, `Semivariance` y `MaxDrawdown`. |
| `src/pso/velocity_model.py` | Modelos `Inertia` y `Constriction`; actualización de velocidad, posición y reparación de pesos. |
| `src/pso/topology.py` | Topologías `RingTopology` y `GlobalTopology`. |
| `src/finance.py` | Métricas de portafolio, tablas, estadísticas multi-seed, drawdown y anualización. |
| `src/models/state.py` | `ExperimentsPayload`, estructura que transporta y persiste el estado completo. |
| `src/persistence.py` | Serialización ZIP `.psodata` con JSON, NPY y Parquet; lectura de formato legado pickle. |
| `src/ui/charts.py` | Construcción de figuras Plotly y sus DTOs. |
| `src/ui/tabs/analysis.py` | Vista individual, pesos, convergencia, variabilidad y backtesting. |
| `src/ui/tabs/comparison.py` | Comparación entre configuraciones y curvas de convergencia. |
| `src/ui/colors.py`, `src/ui/metrics.py` | Colores de activos y reexportaciones de utilidades de métricas. |
| `src/main.py` | Punto de entrada auxiliar que solo imprime un saludo; no es usado por `app.py`. |
| `artifacts/experiments.psodata` | Estado persistido local preferido por la aplicación. |
| `data/*.psodata` | Artefacto exportado adicional. |
| `docs/*.md` | Informes previos de planeación y evolución, útiles como contexto histórico pero secundarios al código actual. |

No se detectaron ciclos de importación evidentes. `src/run_pso.py` contiene
un ajuste de `sys.path` para ejecución directa, señal de que también se ha
considerado ejecutar ese módulo fuera del paquete normal.

## 4. Arquitectura y flujo de ejecución

### Flujo principal

1. `app.main()` configura la página y recupera, si existe, el payload
   persistido desde `artifacts/experiments.psodata`.
2. El sidebar permite seleccionar activos, fechas, frecuencia, tamaño del
   enjambre, puntos de frontera, criterios de convergencia, semilla,
   objetivos, modelo de velocidad y topología (`app.py`).
3. Al enviar el formulario, `run_analysis_pipeline()` valida entradas.
4. `_load_crypto_returns_cached()` descarga y almacena en caché los datos.
5. `_run_experiments_cached()` construye el producto cartesiano de objetivo,
   velocidad y topología, y delega en `run_experiments()`.
6. `run_experiments()` ejecuta una frontera por configuración y, si procede,
   réplicas por semilla.
7. Cada `run_pso()` crea `num_points` problemas PSO, uno por retorno objetivo.
8. Cada `pso()` inicializa el enjambre y itera hasta convergencia o
   `max_iterations=1000`.
9. El controlador calcula métricas para los pesos encontrados, intenta cargar
   un período posterior de backtesting y construye `ExperimentsPayload`.
10. El payload se guarda localmente y se coloca en `st.session_state`.
11. `render_comparison_tab()` muestra las configuraciones y
    `render_analysis_tab()` muestra la configuración elegida.

### Responsabilidades y acoplamiento

La interfaz no calcula directamente la aptitud ni actualiza partículas; esas
responsabilidades están en `src/pso`. El controlador sí concentra muchas
responsabilidades: validación, caché, adquisición de datos, construcción de
experimentos, métricas, backtesting y persistencia. Esa concentración es un
acoplamiento de orquestación, no evidencia por sí sola de un error. Separarla
solo sería útil si se necesita probar esas etapas aisladamente o introducir
fuentes de datos y protocolos de evaluación distintos.

Streamlit usa `st.cache_data` para datos y ejecución, y
`st.session_state` para el payload y el modo de solo lectura. No se usa una
base de datos ni un mecanismo de persistencia remoto. La carga de un archivo
`.psodata` cambia el estado a modo análisis y deshabilita nuevos experimentos
hasta recargar la página.

El manejo de errores del pipeline devuelve mensajes de texto al usuario. En
la UI también existen capturas amplias alrededor de importación y exportación;
son adecuadas para evitar que la vista falle, pero pueden ocultar el tipo
concreto de error al diagnóstico.

## 5. Flujo de datos financieros

### Origen y selección

Los activos están codificados en `app.py`. Los valores por defecto son
`BTC-USD`, `ETH-USD`, `SOL-USD` y `ADA-USD`; también hay diez pares adicionales
de Yahoo Finance disponibles para seleccionar. Las fechas por defecto son
2020-01-01 a 2024-01-01 y la frecuencia por defecto es `1d`. La descarga usa
`yf.download(...)[ "Close" ]`.

La fecha final se entrega a Yahoo Finance tal como la recibe el pipeline. El
repositorio no documenta una validación independiente de la semántica
inclusiva/exclusiva de esa fecha.

### Transformaciones observadas

En `src/utils.py`:

1. Se obtiene el precio de cierre (`Close`), no una serie ajustada.
2. Se calcula:

   \[
   r_{t,i} = \log\left(\frac{P_{t,i}}{P_{t-1,i}}\right)
   \]

3. Se aplica `dropna()` a la tabla de rendimientos.
4. Se devuelve `returns_matrix` con forma \(T \times N\), la media por activo
   y el índice temporal.

No hay tratamiento explícito de duplicados, precios no positivos, valores
faltantes antes de la transformación, outliers, winsorización o imputación.
El `dropna()` elimina filas incompletas después del cálculo y por tanto
alinea los activos mediante intersección de fechas observadas. Esto es
coherente con una matriz común, pero reduce la muestra si algún activo tiene
huecos. Tampoco se calcula una matriz de covarianza en el código observado;
las funciones de riesgo se calculan directamente sobre los retornos de
portafolio.

La selección de activos y el período provienen del usuario. El repositorio no
incluye un universo histórico de activos ni un control específico para sesgo
de supervivencia, selección retrospectiva, cambios de liquidez o
disponibilidad histórica. En criptomonedas, la cotización continua 24/7 y las
convenciones de zona horaria de Yahoo Finance también requieren validación
experimental.

### Entrenamiento y backtesting

El período seleccionado se usa para optimizar y medir las métricas principales.
Luego el controlador intenta descargar desde `end_date` hasta la fecha actual.
El backtesting usa los pesos ya obtenidos, sin reoptimización, costos de
transacción, slippage, comisiones, límites de liquidez ni rebalanceo
explícito. Por ello es una evaluación posterior simple de buy-and-hold con
pesos fijos, no una simulación completa de una estrategia ejecutable.

## 6. Modelo matemático

### Variable de decisión y restricciones

Cada partícula es un vector de \(N\) pesos:

\[
\mathbf{w}=(w_1,\ldots,w_N).
\]

La inicialización genera componentes uniformes aleatorias y las normaliza.
Durante la actualización de velocidad se aplica:

```text
w_i <- max(0, w_i)
w <- w / sum(w), si sum(w) > 0
```

La intención es imponer:

\[
w_i \geq 0,\qquad \sum_{i=1}^{N} w_i = 1.
\]

Esto representa un portafolio long-only, totalmente invertido, sin
apalancamiento, ventas cortas ni límites individuales distintos de cero. Los
pesos cero sí están permitidos. No hay restricciones de turnover, cardinalidad,
concentración, liquidez ni exposición por activo.

Si después del recorte la suma fuese cero, el código no repara la posición ni
lanza un error; deja el vector en cero. Con la dinámica actual ese caso puede
ser infrecuente, pero constituye una ruta que no satisface la restricción de
inversión total y debe validarse.

### Retorno esperado

El “retorno esperado” utilizado por el algoritmo es la media histórica de los
retornos logarítmicos del portafolio:

\[
\bar r_p = \frac{1}{T}\sum_{t=1}^{T} r_{p,t},
\qquad
r_{p,t} = \mathbf r_t^\top \mathbf w.
\]

No se anualiza dentro del PSO. La interfaz muestra una anualización posterior
con \((1+\bar r_p)^{252}-1\), aunque esa cifra es apropiada solo para la
frecuencia diaria y además trata la media logarítmica como si fuera un retorno
simple.

### Qué significa la “frontera”

`run_pso()` toma como objetivos una malla entre la menor y la mayor media por
activo:

\[
\tau_j \in
\operatorname{linspace}\left(\min_i \bar r_i,\max_i \bar r_i,
\text{num\_points}\right).
\]

Para cada \(\tau_j\), el PSO minimiza una aptitud de riesgo más penalización.
No existe una restricción de igualdad
\(\bar r_p=\tau_j\) ni un solver de optimización restringida. Por tanto, la
salida es una colección de soluciones penalizadas parametrizadas por un
objetivo, no una frontera eficiente clásica demostrada.

La formulación clásica de Markowitz basada en
\(\mathbf w^\top\Sigma\mathbf w\) no está implementada como tal porque no se
construye ni se usa una matriz de covarianza en el núcleo actual. La varianza
se calcula como la varianza empírica de \(r_{p,t}\), que es equivalente a la
forma cuadrática solo bajo la misma convención de datos y sin otros términos:

\[
\operatorname{Var}(r_p) =
\operatorname{Var}(\mathbf R\mathbf w).
\]

## 7. Implementación PSO

### Representación y estado

`Particle` almacena `position`, `velocity`, `best_pos` y `best_val`.
`initialize_swarm()` crea `swarm_size` partículas con posiciones normalizadas
y velocidad inicial cero. La aptitud inicial se evalúa antes de comenzar las
iteraciones.

### Actualización

Con inercia:

\[
\mathbf v_{t+1} =
w\mathbf v_t+
c_1r_1(\mathbf p_i-\mathbf x_t)+
c_2r_2(\mathbf g_i-\mathbf x_t),
\]

\[
\mathbf x_{t+1}=\operatorname{repair}(\mathbf x_t+\mathbf v_{t+1}).
\]

`best_reference` procede de la topología. `RingTopology(k_neighbors=1)`
considera la partícula, su vecino anterior y su vecino siguiente con
envoltura circular. `GlobalTopology` usa el mejor `best_val` de todo el
enjambre.

El modelo de constricción usa:

\[
\chi =
\frac{2}{\left|2-\phi-\sqrt{\phi^2-4\phi}\right|},
\quad \phi=c_1+c_2,
\]

y exige \(\phi>4\). La UI valida esa condición al seleccionar el modelo.

Después de actualizar una partícula se evalúa su nueva posición. Si mejora,
se actualiza su `pbest`. Al final de la iteración se actualiza el `gbest`
global. No se observan límites de velocidad ni límites superiores de posición
antes de la normalización.

### Terminación y trazas

El máximo es 1000 iteraciones. Desde después de la iteración 5, se compara la
mejora absoluta del `gbest` con:

\[
\text{tolerance}=\text{atol}+\text{rtol}\,|\text{gbest}|.
\]

Si la mejora permanece debajo del umbral durante `patience` iteraciones, se
detiene. Se guardan historiales de `gbest` y de diversidad media, aunque la
persistencia actual no conserva la diversidad.

La diversidad es la distancia euclidiana media de las posiciones al centroide
del enjambre. Es un indicador descriptivo; no se usa como criterio de parada.

### Aleatoriedad y reproducibilidad

`run_experiments()` llama a `np.random.seed(seed)`, lo que controla la
inicialización de posiciones. Sin embargo, `Inertia.update()` y
`Constriction.update()` importan `random` de la biblioteca estándar y usan
`random()`. Esa segunda fuente no se inicializa con la misma semilla. La
opción de UI “Use reproducible seeds” y la documentación del README, por
tanto, no garantizan reproducibilidad completa del PSO en el estado actual.
Las semillas de las réplicas se derivan como `config.seed + seed_index`, y la
semilla inicial de cada configuración se deriva de `base_seed + config_index`.

## 8. Función de aptitud y modelo de riesgo

Todas las clases minimizan:

\[
F(\mathbf w;\tau)=R(\mathbf w)+
\lambda|\bar r_p-\tau|,
\]

donde \(\lambda\) es `penalty`, por defecto 50 en las clases y 500 desde la
UI, y \(R\) es la métrica elegida. La penalización es lineal y no se escala
automáticamente con las unidades de riesgo o retorno.

### CVaR

Para `alpha=0.95`, se calcula el percentil inferior del 5%:

\[
q_\alpha=\operatorname{percentile}(r_p,(1-\alpha)100).
\]

Después se toma la media de los escenarios con \(r_{p,t}\leq q_\alpha\) y se
cambia el signo:

\[
\widehat{\operatorname{CVaR}}_\alpha =
-\operatorname{mean}\{r_{p,t}:r_{p,t}\leq q_\alpha\}.
\]

Es una estimación histórica empírica sobre retornos de portafolio. No es una
formulación paramétrica ni una optimización lineal de CVaR. El número efectivo
de observaciones de cola depende de \(T\); no hay intervalo de confianza ni
tratamiento especial para muestras pequeñas. Si todos los retornos son
positivos, el valor puede resultar negativo bajo esta convención, lo que
requiere decidir si se interpreta como “pérdida esperada” o como métrica de
riesgo firmemente no negativa.

`src/finance.py` calcula la misma regla para presentar métricas, por lo que la
aptitud CVaR y la métrica mostrada son conceptualmente consistentes en datos y
signos.

### VaR

\[
\widehat{\operatorname{VaR}}_\alpha=-q_\alpha.
\]

Se minimiza VaR más la misma penalización. Como ocurre con CVaR, es un
percentil histórico de retornos logarítmicos, no una pérdida monetaria ni una
medida con horizonte monetario explícito.

### Varianza y semivarianza

La varianza usa la varianza poblacional de los retornos de portafolio:

\[
\widehat{\sigma_p^2}=\frac1T\sum_t(r_{p,t}-\bar r_p)^2.
\]

La semivarianza usa solo desviaciones por debajo de la media del portafolio:

\[
\widehat{SV}=\operatorname{mean}\left[
(r_{p,t}-\bar r_p)^2\mid r_{p,t}<\bar r_p
\right].
\]

No se usa un objetivo externo como cero o una tasa libre de riesgo.

### Máximo drawdown

Se construye la riqueza acumulada como:

\[
C_t=\prod_{s\leq t}(1+r_{p,s}),
\quad
D_t=\frac{C_t-\max_{u\leq t}C_u}{\max_{u\leq t}C_u},
\quad
MDD=-\min_tD_t.
\]

La implementación usa retornos logarítmicos directamente dentro de
\(1+r\). Para pérdidas suficientemente grandes, o cuando se desee una
interpretación estricta de riqueza, conviene validar la compatibilidad de esta
convención con los retornos logarítmicos de entrada.

### Métricas adicionales

Se calculan volatilidad (`std`), Sharpe simplificado
\(\bar r_p/\sigma_p\), retorno medio, VaR, CVaR, varianza, semivarianza y
drawdown. No se observa tasa libre de riesgo, annualización del Sharpe, beta,
tracking error ni costos.

## 9. Interfaz y resultados

La interfaz permite seleccionar:

- activos, fechas y frecuencia `1d`, `1wk` o `1mo`;
- puntos de frontera, tamaño de enjambre, `rtol`, `atol` y paciencia;
- semilla reproducible y corridas multi-seed;
- objetivo de riesgo;
- parámetros \(c_1\), \(c_2\), inercia;
- topología Ring o Global.

La vista de comparación presenta una curva por configuración, usando el riesgo
seleccionado en el eje X y `mean_return` en Y. La vista individual presenta:

- frontera de la configuración;
- convergencia del `gbest`;
- variabilidad entre semillas, si existe;
- tabla de pesos;
- composición por activo;
- retorno diario y retorno anualizado;
- rendimiento acumulado del período de backtesting.

Las curvas se ordenan visualmente por la métrica de riesgo elegida. El orden
visual no cambia los pesos ni la optimización. El backtesting toma la matriz
posterior y los pesos de la primera frontera de cada configuración; las
réplicas multi-seed no tienen backtesting separado.

Un punto a tener presente es que el eje o etiqueta “Retorno esperado” muestra
la media histórica de retornos logarítmicos. La cifra “Annualized return”
usa siempre 252 períodos, incluso si el usuario seleccionó una frecuencia
semanal o mensual.

## 10. Pruebas y reproducibilidad

No se encontraron directorios ni archivos de pruebas automatizadas. Tampoco se
observan benchmarks, fixtures financieros, pruebas de restricciones, tests de
métricas, validación contra un solver de referencia o experimentos sintéticos
con solución conocida.

La evidencia disponible es:

- el código fuente y sus docstrings;
- los artefactos `.psodata`, que contienen matrices, tablas, configuraciones,
  pesos e historiales;
- documentación previa en `docs/`;
- un análisis sintáctico local de los módulos Python, que fue correcto durante
  esta auditoría.

La opción multi-seed mejora la observabilidad de variabilidad, pero no
constituye por sí sola una validación estadística. Con la fuente de aleatoriedad
dual descrita arriba, incluso su modo reproducible debe corregirse o
documentarse como parcialmente reproducible antes de usarlo como protocolo
experimental.

No existe separación automática entre entrenamiento, validación y prueba:
hay un período de optimización y un período posterior de backtesting, pero no
se calculan métricas agregadas, intervalos de confianza, rebalances ni
comparaciones con benchmarks simples como equal-weight.

## 11. Hallazgos técnicos

| Prioridad | Hallazgo | Evidencia | Impacto | Estado | Recomendación |
|---|---|---|---|---|---|
| **Alto** | La reproducibilidad no controla todas las fuentes aleatorias. | `src/experiments.py:41-44` fija NumPy; `src/pso/velocity_model.py:4,23,53` usa `random()`. | Dos corridas con la misma semilla declarada pueden producir trayectorias y pesos distintos. | **Confirmado** | Unificar el generador aleatorio o pasar explícitamente un RNG a inicialización y velocidad; después probar igualdad de resultados. |
| **Alto** | Los retornos objetivo se aproximan mediante penalización, no mediante restricción exacta. | `src/run_pso.py:52-57,66-78`; `src/pso/fitness_function.py:34-38`. | La salida puede no alcanzar cada `target_value`; llamar a la colección “frontera eficiente” puede sobreinterpretar el resultado. | **Confirmado** | Medir el error `abs(mean_return-target)` y documentar el problema como penalizado; comparar con una formulación restringida. |
| **Alto** | No hay validación automatizada de la formulación financiera ni del PSO. | No existen archivos de tests; `pyproject.toml` no declara framework de pruebas. | No hay evidencia reproducible de factibilidad, corrección de CVaR ni calidad frente a una referencia. | **Confirmado como ausencia** | Añadir pruebas focalizadas y problemas sintéticos antes de extraer conclusiones académicas. |
| **Alto** | Anualización fija a 252 períodos para cualquier intervalo. | `src/finance.py:194-195`; llamada en `src/ui/tabs/analysis.py:198-200`. | La UI puede reportar cifras mal interpretadas para `1wk` y `1mo`. | **Confirmado** | Parametrizar períodos por año según `interval` y distinguir retornos simples/logarítmicos. |
| **Alto** | La calidad estadística de CVaR/VaR depende del tamaño de cola y de la muestra histórica. | `src/pso/fitness_function.py:25-29,58-65`; `src/finance.py:25-30`. | Con muestras pequeñas o colas discretas, el riesgo puede ser inestable; no hay incertidumbre ni sensibilidad a alpha. | **Confirmado como limitación** | Reportar número de observaciones de cola, realizar sensibilidad de alpha y documentar el horizonte. |
| **Medio** | La reparación deja una posición nula si todas las componentes actualizadas se recortan a cero. | `src/pso/velocity_model.py:34-40,59-65`. | Una partícula puede dejar de satisfacer \(\sum w_i=1\), con métricas degeneradas. | **Probable; requiere reproducir la ruta** | Añadir una política explícita de reparación y una aserción de factibilidad. |
| **Medio** | Se descarga `Close` sin política explícita de datos faltantes, duplicados o ajustes. | `src/utils.py`, `yf.download(...)[\"Close\"]`, `dropna()`. | La muestra efectiva y las métricas pueden cambiar por alineación completa; no se documenta control de calidad. | **Confirmado como ausencia** | Registrar dimensiones, fechas eliminadas y reglas de limpieza; validar la semántica de Yahoo Finance. |
| **Medio** | El backtesting es buy-and-hold simple y usa la fecha actual. | `src/controllers/experiment_controller.py` en el bloque `backtest_start/end`; `src/ui/charts.py` en `_build_backtesting_returns_figure`. | Resultados no congelados, sin costos ni rebalances; las ejecuciones no son estrictamente comparables a lo largo del tiempo. | **Confirmado** | Fijar ventanas de evaluación y especificar política de rebalanceo y costos. |
| **Medio** | `diversity_histories` se calcula pero no se serializa ni se restaura. | `src/run_pso.py` y `src/persistence.py`, donde se guardan historiales de convergencia pero no diversidad. | Se pierde una señal experimental al recargar un `.psodata`. | **Confirmado** | Persistirla o declarar explícitamente que es solo de sesión. |
| **Medio** | El controlador concentra muchas etapas y captura excepciones amplias en la UI. | `src/controllers/experiment_controller.py`; `app.py` bloques de importación/exportación. | Puede dificultar pruebas unitarias y diagnóstico de fallos de datos o serialización. | **Confirmado como diseño** | Separar solo las fronteras que necesiten pruebas independientes y conservar mensajes con contexto. |
| **Bajo** | `src/main.py` no es un punto de entrada real de la aplicación. | `src/main.py:1-6` frente a `README.md` y `app.py`. | Puede confundir a futuros mantenedores, pero no cambia la ejecución documentada. | **Confirmado** | Documentar su carácter auxiliar o retirarlo solo si se decide explícitamente. |

## 12. Mejoras propuestas

Las siguientes propuestas están ordenadas por valor para la validez del
experimento, no por conveniencia de refactorización.

### Prioridad 1: validez y reproducibilidad

1. Definir una política única de aleatoriedad y probar que una ejecución con la
   misma configuración y semilla produce los mismos pesos, aptitudes e
   historiales.
2. Registrar por punto de frontera el retorno alcanzado, el error frente al
   target, el número de iteraciones y el estado de factibilidad.
3. Validar las métricas con casos sintéticos pequeños: retornos constantes,
   pérdidas conocidas, cola conocida, drawdown manual y un portafolio de un
   solo activo.
4. Comparar al menos contra equal-weight, mínima varianza y una implementación
   independiente de la métrica elegida.

### Prioridad 2: protocolo financiero

1. Definir formalmente si se trabaja con retornos logarítmicos o simples y
   mantener la convención en drawdown, anualización y reportes.
2. Parametrizar frecuencia de anualización, horizonte de riesgo, alpha y
   tamaño mínimo de muestra de cola.
3. Congelar ventanas de entrenamiento y prueba para evitar que el backtesting
   dependa de la fecha de ejecución.
4. Documentar limpieza de datos, fechas, zona horaria, faltantes, activos
   disponibles históricamente y sesgo de supervivencia.
5. Añadir costos, liquidez y rebalanceo únicamente si el objetivo académico
   pretende aproximar una estrategia implementable.

### Prioridad 3: formulación y experimentación

1. Medir si la penalización realmente mantiene los retornos cerca de cada
   target y estudiar sensibilidad de `penalty`.
2. Si se necesita una frontera de Markowitz estricta, comparar con una
   formulación que imponga la restricción de retorno y con un método de
   referencia. No debe asumirse que sustituir el PSO mejora automáticamente
   la investigación: primero hay que establecer el punto de comparación.
3. Hacer explícita la reparación de pesos y probar extremos como un activo,
   activos idénticos, retornos todos iguales y enjambre pequeño.
4. Conservar diversidad en `.psodata` si se utilizará como evidencia de
   convergencia.

### Prioridad 4: mantenibilidad y rendimiento

El flujo está razonablemente vectorizado: la evaluación principal usa
`returns_matrix @ position`. El costo dominante esperado es el producto de
`num_points × n_swarm × iterations × configurations × seeds`, más las
descargas. No hay mediciones que permitan afirmar un cuello de botella
concreto. Antes de optimizar, conviene instrumentar duración por punto y
configuración, y luego evaluar precálculos o reducción de copias.

La arquitectura actual no requiere una reescritura. Las mejoras de claridad
con mayor retorno serían contratos de datos explícitos, funciones de
validación pequeñas, semillas/RNG explícitos y pruebas del núcleo sin
Streamlit.

## 13. Preguntas abiertas

1. ¿La fecha `end` debe incluirse o excluirse en el protocolo de datos?
2. ¿Los resultados académicos deben interpretar la media de retornos
   logarítmicos como retorno esperado o convertirla a retorno simple?
3. ¿CVaR significa pérdida monetaria, pérdida porcentual simple o el negativo
   de un retorno logarítmico?
4. ¿Qué tamaño mínimo de muestra y cuántas observaciones de cola se consideran
   suficientes para cada alpha?
5. ¿Debe el retorno objetivo ser una restricción exacta o se acepta el
   compromiso penalizado actual?
6. ¿Qué definición de semivarianza se desea: debajo de la media, debajo de
   cero o debajo de una tasa objetivo?
7. ¿El backtesting debe ser buy-and-hold, con rebalanceo periódico o con una
   política definida por el experimento?
8. ¿Qué costos de transacción, slippage y restricciones de liquidez deben
   modelarse?
9. ¿Se necesita un universo histórico de activos para controlar supervivencia y
   disponibilidad?
10. ¿El artefacto `.psodata` es evidencia reproducible que debe versionarse,
    o solo caché local?
11. ¿Debe conservarse `diversity_histories` para análisis posteriores?
12. ¿Qué criterio independiente definirá que dos fronteras o semillas son
    suficientemente estables?

## 14. Glosario

| Término | Significado en este repositorio |
|---|---|
| `assets` | Lista de identificadores Yahoo Finance, por ejemplo `BTC-USD`. |
| `returns_matrix` | Matriz \(T\times N\) de rendimientos logarítmicos por fecha y activo. |
| `mean_return` | Media histórica por activo en `PSOInputData`; también media de retornos del portafolio en métricas. |
| `PSOInputData` | Par de entradas `mean_return` y `returns_matrix` para construir la malla de targets y evaluar partículas. |
| `position` | Vector de pesos actual de una partícula. |
| `pbest` / `best_pos` | Mejor posición histórica de una partícula según su aptitud. |
| `gbest` | Mejor `best_val` observado por el enjambre o vecindario. |
| `fitness` | Riesgo seleccionado más penalización de distancia al retorno objetivo. Menor es mejor. |
| `target_value` | Punto de la malla entre la media mínima y máxima de los activos. |
| `EfficientFrontier` | Contenedor de targets, pesos, fitness e historiales producidos por `run_pso()`. |
| `ExperimentConfig` | Combinación de objetivo, velocidad, topología, parámetros y semillas. |
| `RingTopology` | Vecindario circular de la partícula, ella misma y un vecino a cada lado. |
| `GlobalTopology` | Referencia al mejor `pbest` de todo el enjambre. |
| `Inertia` | Actualización PSO con inercia y componentes cognitiva/social. |
| `Constriction` | Actualización PSO con factor \(\chi\) y condición \(c_1+c_2>4\). |
| `CVaR` | Media negativa de retornos en la cola inferior definida por `alpha`. |
| `VaR` | Negativo del percentil inferior de retornos. |
| `Semivariance` | Media de desviaciones cuadráticas por debajo de la media del portafolio. |
| `MaxDrawdown` | Pérdida máxima desde un máximo acumulado calculada sobre \(1+r\). |
| `metrics_by_config` | DataFrame de métricas para los pesos de la primera frontera de cada configuración. |
| `seed_metrics_by_config` | Métricas por punto y réplica cuando se ejecutan varias semillas. |
| `.psodata` | Archivo ZIP con metadata JSON, arrays NPY, DataFrames Parquet y fronteras serializadas. |
| `ExperimentsPayload` | Estado completo usado por Streamlit, persistencia y pestañas. |

## 15. Contexto breve para futuras consultas

El repositorio `pso-cryptocurrency` es una aplicación Streamlit (`app.py`)
para experimentar con portafolios long-only de criptomonedas descargados desde
Yahoo Finance mediante `yfinance`. `src/utils.py` descarga precios de cierre,
calcula rendimientos logarítmicos y devuelve una matriz \(T\times N\). El
controlador `src/controllers/experiment_controller.py` cachea datos y
experimentos, construye el producto cartesiano de objetivo de riesgo, modelo
de velocidad y topología, calcula métricas, intenta un backtesting posterior y
guarda un `ExperimentsPayload` en `.psodata`.

`src/run_pso.py` genera una malla de targets entre la media mínima y máxima de
los activos y ejecuta un PSO independiente por target. La aptitud implementada
es siempre `risk + penalty * abs(mean_return - target)`, no una restricción
exacta de retorno. Las métricas disponibles son CVaR histórico, VaR histórico,
varianza, semivarianza, máximo drawdown, volatilidad y Sharpe simplificado.
CVaR usa la media de los retornos en la cola inferior; alpha por defecto es
0.95. Los pesos se inicializan y reparan para ser no negativos y sumar uno,
sin posiciones cortas ni apalancamiento.

El PSO (`src/pso/optimizer.py`) mantiene `position`, `velocity`, `pbest` y
`gbest`, ofrece topología Ring o Global, modelos Inertia o Constriction y
termina por tolerancia/paciencia o 1000 iteraciones. Las corridas multi-seed
guardan réplicas y estadísticas, pero la “reproducibilidad” actual es
incompleta porque se fija `numpy.random` y el modelo de velocidad usa además
`random.random()` sin semilla coordinada. No hay pruebas automatizadas ni
validación contra solvers o casos sintéticos. La anualización de la UI usa
252 períodos incluso para frecuencias no diarias. Las principales decisiones
pendientes son la definición formal de retornos/riesgo, la interpretación de
CVaR, la exigencia de retorno objetivo, la política de backtesting y el
protocolo de validación académica.

## AI_HANDOFF_SUMMARY

- **Objetivo:** investigar optimización de portafolios de criptomonedas con PSO
  y visualizar configuraciones, fronteras, convergencia y backtesting.
- **Stack confirmado:** Python 3.12+, NumPy, pandas, yfinance, Streamlit,
  Plotly; `uv` gestiona el entorno y lockfile.
- **Arquitectura:** `app.py` → controlador → `utils.py`/`finance.py` →
  `experiments.py` → `run_pso.py` → `src/pso`; resultados vuelven a
  `ExperimentsPayload`, persistencia `.psodata` y pestañas Plotly.
- **Datos:** precios `Close` de Yahoo Finance; activos por defecto
  BTC/ETH/SOL/ADA; fechas y frecuencia configurables; retornos logarítmicos,
  `dropna()` y matriz alineada por fechas completas.
- **Formulación:** pesos \(w_i\geq0\), suma uno; sin cortos, apalancamiento,
  costos ni límites por activo. Targets entre la media mínima y máxima de los
  activos. Cada target se aproxima por penalización, no por igualdad exacta.
- **PSO:** posiciones y velocidades por activo; pbest/gbest; Ring o Global;
  Inertia o Constriction; tolerancias `rtol=1e-4`, `atol=1e-8`, paciencia 10,
  máximo 1000 iteraciones; UI por defecto 30 puntos y 100 partículas.
- **Riesgo/fitness:** CVaR, VaR, varianza, semivarianza o máximo drawdown más
  `penalty * abs(mean_return-target)`; alpha por defecto 0.95; menor fitness
  es mejor.
- **Resultados:** pesos, métricas, curvas de frontera, convergencia,
  composición, estadísticas multi-seed y backtesting posterior con pesos
  fijos. Las réplicas multi-seed no tienen backtesting separado.
- **Pruebas:** no hay suite automatizada ni benchmark de referencia; solo
  existe evidencia en código, documentación previa y artefactos persistidos.
- **Hallazgos principales:** reproducibilidad incompleta por dos RNG;
  frontera penalizada malinterpret-able como Markowitz clásica; anualización
  fija a 252; calidad de datos y colas CVaR sin protocolo explícito; posible
  posición cero tras reparación; diversidad calculada pero no persistida.
- **Preguntas pendientes:** convención de retorno y signos, horizonte/alpha y
  muestra de CVaR, retorno objetivo exacto vs penalizado, frecuencia de
  anualización, costos/rebalanceo y diseño de validación temporal.
- **Decisiones actuales que no deben suponerse distintas:** la primera
  réplica multi-seed es la frontera principal; el backtesting usa esa frontera;
  `.psodata` es el formato nuevo y se conserva compatibilidad con pickle
  legado; `src/main.py` no es el entrypoint de Streamlit.
