# Reporte Técnico: PSO Cryptocurrency Portfolio Optimization

> Generado automáticamente por revisión exhaustiva del repositorio `pso-cryptocurrency`.

---

## 1. Estructura general del repositorio

```
pso-cryptocurrency/
├── app.py                        # Punto de entrada del dashboard Streamlit
├── pyproject.toml                # Dependencias y metadatos del proyecto (uv)
├── artifacts/
│   └── experiments.psodata      # Resultados persistidos (formato ZIP propietario)
└── src/
    ├── __init__.py
    ├── experiments.py            # Dataclasses ExperimentConfig/Result y orquestador run_experiments()
    ├── finance.py                # Cálculo de métricas financieras y helpers de DataFrames
    ├── main.py                   # Script vacío/placeholder (96 bytes, sin contenido relevante)
    ├── persistence.py            # Serialización/deserialización de resultados a .psodata
    ├── run_pso.py                # Wrapper que ejecuta PSO N veces para construir la frontera eficiente
    ├── utils.py                  # Descarga de datos de mercado vía yfinance
    ├── controllers/
    │   └── experiment_controller.py  # Pipeline completo: datos → experimentos → payload + persistencia
    ├── models/
    │   └── state.py              # Dataclass ExperimentsPayload (estado global de la sesión)
    ├── pso/
    │   ├── fitness_function.py   # Funciones fitness (CVaR, VaR, Semivariance, Variance, MaxDrawdown)
    │   ├── optimizer.py          # Algoritmo PSO core: initialize_swarm() + pso()
    │   ├── particle.py           # Dataclass Particle (posición, velocidad, best_pos, best_val)
    │   ├── topology.py           # Topologías: GlobalTopology, RingTopology
    │   └── velocity_model.py     # Modelos de velocidad: Inertia, Constriction
    └── ui/
        ├── charts.py             # Constructores de figuras Plotly (todas las gráficas)
        ├── colors.py             # Mapa de colores por criptomoneda
        ├── metrics.py            # Re-exporta funciones de finance.py al namespace de ui
        └── tabs/
            ├── analysis.py       # Tab "Individual Analysis": frontera + backtesting + pesos
            └── comparison.py     # Tab "Comparison": fronteras superpuestas de todas las configs
```

---

## 2. Núcleo del algoritmo PSO

### Clases/funciones principales

| Archivo            | Símbolo              | Rol                                                             |
| ------------------ | -------------------- | --------------------------------------------------------------- |
| `pso/particle.py`  | `Particle`           | Dataclass con `position`, `velocity`, `best_pos`, `best_val`    |
| `pso/optimizer.py` | `initialize_swarm()` | Inicializa partículas con pesos aleatorios normalizados (sum=1) |
| `pso/optimizer.py` | `pso()`              | Loop principal del algoritmo                                    |
| `run_pso.py`       | `run_pso()`          | Ejecuta `pso()` para cada punto target de la frontera eficiente |
| `experiments.py`   | `run_experiments()`  | Itera sobre `ExperimentConfig` y llama a `run_pso()`            |

### Inyección de dependencias

Tres interfaces abstractas (`ABC`) con `@abstractmethod`:

| Interfaz          | Archivo               | Método abstracto                                           |
| ----------------- | --------------------- | ---------------------------------------------------------- |
| `FitnessFunction` | `fitness_function.py` | `evaluate(position, returns_matrix, target_value) → float` |
| `Topology`        | `topology.py`         | `get_best_particle(particle_index, swarm) → Particle`      |
| `VelocityModel`   | `velocity_model.py`   | `update(particle, best_reference_position) → None`         |

### Funciones fitness disponibles

| Clase          | Fórmula/Lógica                                                                           | Parámetros propios |
| -------------- | ---------------------------------------------------------------------------------------- | ------------------ |
| `CVaR`         | `risk = -mean(returns ≤ VaR_threshold)`; `fitness = risk + penalty *                     | E[R] - target      | `   | `alpha=0.95`, `penalty=50.0` |
| `VaR`          | `risk = -percentile(returns, (1-alpha)*100)`; `fitness = risk + penalty *                | E[R] - target      | `   | `alpha=0.95`, `penalty=50.0` |
| `Semivariance` | `risk = mean((R_t - E[R])² para R_t < E[R])`; `fitness = semivar + penalty *             | E[R] - target      | `   | `penalty=50.0`               |
| `Variance`     | `risk = Var(R_portfolio)`; `fitness = var + penalty *                                    | E[R] - target      | `   | `penalty=50.0`               |
| `MaxDrawdown`  | `risk = max((peak - trough)/peak)` sobre retornos acumulados; `fitness = mdd + penalty * | E[R] - target      | `   | `penalty=50.0`               |

**Nota**: Todas las fitness comparten la misma estructura `risk + penalty * |E[R] - target|`. Los retornos del portafolio se calculan como `returns_matrix @ position` (producto matricial).

### Topologías disponibles

| Clase                         | Descripción                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GlobalTopology`              | **Global best (gbest)**: referencia = la mejor partícula de todo el enjambre                                                                     |
| `RingTopology(k_neighbors=1)` | **Ring/Local best (lbest)**: referencia = la mejor partícula en una vecindad circular de ±k vecinos. Por defecto k=1 (vecindad de 3 partículas). |

### Modelos de velocidad disponibles

| Clase          | Fórmula                                                         | Parámetros propios                |
| -------------- | --------------------------------------------------------------- | --------------------------------- |
| `Inertia`      | `v = w*v + c1*r1*(pbest-x) + c2*r2*(gbest-x)`                   | `c1=0.5`, `c2=1.0`, `inertia=0.8` |
| `Constriction` | `v = χ * (v + c1*r1*(pbest-x) + c2*r2*(gbest-x))` donde `χ = 2/ | 2-φ-√(φ²-4φ)                      | `, `φ = c1+c2` | `c1=2.05`, `c2=2.05` (requiere c1+c2 > 4) |

Ambos modelos aplican post-procesamiento de posición: `clip(0)` + normalización sum=1 para mantener pesos válidos de portafolio.

### Parámetros configurables del PSO

| Parámetro                         | Tipo      | Default en código                              | Rango en UI                                |
| --------------------------------- | --------- | ---------------------------------------------- | ------------------------------------------ |
| `swarm_size` / `n_swarm`          | int       | 100                                            | 20–200                                     |
| `max_iterations`                  | int       | 1000                                           | — (no expuesto en UI)                      |
| `epsilon` (early stop)            | float     | 1e-5                                           | editable (number_input)                    |
| `num_points` (puntos de frontera) | int       | 30                                             | 10–100                                     |
| `c1` (cognitivo)                  | float     | 1.7 (UI) / 0.5 (Inertia) / 2.05 (Constriction) | 0.5–3.0                                    |
| `c2` (social)                     | float     | 1.7 (UI) / 1.0 (Inertia) / 2.05 (Constriction) | 0.5–3.0                                    |
| `inertia` / `w`                   | float     | 0.8                                            | 0.4–1.0                                    |
| `alpha` (CVaR/VaR)                | float     | 0.95                                           | 0.80–0.99                                  |
| `penalty`                         | float     | 500.0 (UI) / 50.0 (clases)                     | 1.0–5000.0                                 |
| `seed`                            | int\|None | 42 (base)                                      | 0–10,000,000; configurable por experimento |

**Early stopping**: se para si `|best_global_value_t - best_global_value_{t-1}| < epsilon` y `iteration > 5`.

### Registro de convergencia

**No existe registro por iteración.** El `pso()` retorna únicamente `(best_global_value, best_global_position)` al final. `EfficientFrontier` almacena:

- `target_values: np.ndarray` — valores target de retorno para cada punto de la frontera
- `weights: list[np.ndarray]` — pesos óptimos por punto
- `best_fitnesses: np.ndarray` — valor fitness final del gbest por punto

No hay historial de convergencia (fitness por iteración), ni historial de posición del gbest, ni métricas de diversidad del enjambre.

---

## 3. Datos y preprocesamiento

### Fuente de datos

- **API**: `yfinance` (Yahoo Finance), descarga en tiempo real al correr el experimento.
- Los resultados se cachean con `@st.cache_data` durante la sesión de Streamlit.

### Activos disponibles

Los activos por defecto son `["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]`. El usuario puede seleccionar cualquier subconjunto de estos cuatro en la UI. Soporte para otros tickers de yfinance no está bloqueado a nivel código, pero el mapa de colores `colors.py` solo tiene paleta predefinida para estos cuatro.

### Rango de fechas

- **Defecto en UI**: `2020-01-01` a `2024-01-01` (ventana de 4 años)
- El usuario puede cambiar libremente start/end date.
- El backtesting se corre automáticamente desde `end_date` hasta `datetime.now().date()`.

### Transformaciones de datos

```python
returns = np.log(close_prices / close_prices.shift(1)).dropna()
```

- Se usan **log-retornos diarios** (o según el intervalo seleccionado).
- Se descarta la primera fila (NaN del shift).
- No hay normalización adicional.
- `mean_return = returns_matrix.mean(axis=0)` — media por activo, usada para definir los límites de la frontera.

### Frecuencia de datos

El usuario elige entre `"1d"` (diaria), `"1wk"` (semanal), `"1mo"` (mensual).  
**Default**: `"1d"` (diaria).

---

## 4. Dashboard (Streamlit)

### Estructura del app

App de una sola página (`app.py`) con sidebar de configuración y dos tabs principales.

### Sidebar

| Sección            | Qué hace el usuario                                      |
| ------------------ | -------------------------------------------------------- |
| 📂 Gestor de Datos | Cargar archivo `.psodata` para modo análisis (read-only) |
| Assets             | Selección multiselect de criptomonedas                   |
| Market data        | Fechas start/end, intervalo temporal                     |
| PSO                | Frontier points, swarm size, epsilon, seed               |
| Objectives         | Selección de función(es) fitness, alpha, penalty         |
| Velocity models    | Selección de modelo(s), c1, c2, inertia (w)              |
| Topologies         | Selección de topología(s)                                |

El sistema genera experimentos para todas las combinaciones (producto cartesiano) de objectives × velocities × topologies.

### Tab "📊 Comparison"

**Una sola gráfica**: `build_comparison_frontier_chart`

- **Tipo**: scatter con líneas, una traza por configuración
- **Eje X**: métrica de riesgo seleccionada globalmente (CVaR, VaR, Variance, Semivariance, Max Drawdown, o Desviación estándar)
- **Eje Y**: retorno esperado medio (`mean_return`)
- **Interpretación**: permite comparar visualmente las fronteras eficientes de todas las configuraciones; cada punto es un portafolio óptimo para un target de retorno dado.

### Tab "🔎 Individual Analysis"

| Elemento                               | Datos usados                            | Ejes / Contenido                                                            | Interpretación                                                              |
| -------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Selectbox config                       | Lista de experimentos                   | —                                                                           | El usuario elige qué configuración analizar en detalle                      |
| **Frontier chart**                     | `df_metrics` de la config               | X: riesgo elegido; Y: `mean_return`; color: `sharpe_ratio` (escala Viridis) | Muestra la frontera eficiente de esa config; el color indica calidad Sharpe |
| **Portfolio multiselect**              | `frontier.weights`, `df_metrics`        | Lista desplegable con `mean_return` y riesgo por portafolio                 | Permite seleccionar N portafolios de la frontera para analizar              |
| **Asset color legend**                 | `assets`                                | Cuadros de colores HTML                                                     | Referencia visual de colores por activo                                     |
| **Portfolio composition (pie charts)** | `frontier.weights[idx]`                 | Labels: activos; Values: pesos                                              | Composición del portafolio seleccionado                                     |
| **Métricas inline**                    | `df_metrics.iloc[idx]`                  | `st.metric`: daily return, annualized return                                | Retorno diario y anualizado `(1+r)^252 - 1`                                 |
| **Portfolio weights table**            | `frontier.weights`                      | Tabla: activos × portafolios seleccionados (en %)                           | Pesos exactos de cada portafolio                                            |
| **Cumulative return (backtesting)**    | `bt_returns_matrix`, `bt_returns_index` | X: fecha (desde end_date hasta hoy); Y: retorno acumulado %                 | Rendimiento out-of-sample de los portafolios seleccionados                  |

### Persistencia de resultados

- **Auto-guardado**: después de cada ejecución, el payload completo se guarda en `artifacts/experiments.psodata` (formato ZIP con JSON + npy + parquet).
- **Auto-carga**: al iniciar la app, se carga automáticamente `experiments.psodata` si existe.
- **Importar/Exportar**: el usuario puede exportar un `.psodata` vía botón de descarga, y cargarlo manualmente en otra sesión.
- **Legacy**: hay compatibilidad de lectura con el formato antiguo `experiments.pkl` (pickle).
- Los datos **no se pierden** al recargar la app si `artifacts/experiments.psodata` existe.

---

## 5. Métricas actualmente calculadas

### Métricas del portafolio resultante

Calculadas en `finance.calculate_portfolio_metrics()` para cada punto de la frontera:

| Métrica             | Fórmula                                                          | Dónde se calcula      |
| ------------------- | ---------------------------------------------------------------- | --------------------- |
| `mean_return`       | `mean(R_t @ w)` — media aritmética de retornos                   | `finance.py`          |
| `volatility`        | `std(R_t @ w)`                                                   | `finance.py`          |
| `variance`          | `var(R_t @ w)`                                                   | `finance.py`          |
| `cvar`              | `-mean(R_t @ w : R_t ≤ percentile(R, (1-α)×100))`                | `finance.py`          |
| `var`               | `-percentile(R_t @ w, (1-α)×100)`                                | `finance.py`          |
| `semivariance`      | `mean((R_t - E[R])² : R_t < E[R])`                               | `finance.py`          |
| `max_drawdown`      | `max((peak - trough)/peak)` sobre retornos acumulados compuestos | `finance.py`          |
| `sharpe_ratio`      | `mean_return / volatility`                                       | `finance.py`          |
| `annualized_return` | `(1 + daily_return)^252 - 1`                                     | `finance.py` (helper) |

### Métricas del proceso de optimización

| Métrica          | Descripción                                                   | Dónde                              |
| ---------------- | ------------------------------------------------------------- | ---------------------------------- |
| `best_fitnesses` | Valor fitness final del gbest por cada punto target           | `EfficientFrontier.best_fitnesses` |
| `fitness`        | Columna añadida al DataFrame de métricas (= `best_fitnesses`) | `build_metrics_dataframe()`        |

**No existe** ninguna métrica de convergencia por iteración, diversidad del enjambre, ni velocidad media de partículas.

### Métricas de comparación entre configuraciones

Calculadas en `finance.build_summary_dataframe()` para el tab de comparación:

| Campo                   | Descripción                                                                  |
| ----------------------- | ---------------------------------------------------------------------------- |
| `selected_mean_return`  | Retorno del portafolio seleccionado (por criterio Best Sharpe o índice fijo) |
| `selected_cvar`         | CVaR del portafolio seleccionado                                             |
| `selected_max_drawdown` | Max Drawdown del portafolio seleccionado                                     |
| `selected_volatility`   | Volatilidad del portafolio seleccionado                                      |
| `selected_sharpe_ratio` | Sharpe del portafolio seleccionado                                           |
| `selected_fitness`      | Valor fitness del portafolio seleccionado                                    |

Hay también una función `build_experiment_summary()` en `experiments.py` que calcula `best_mean_return`, `best_cvar`, `best_max_drawdown`, `best_sharpe_ratio`, `best_fitness` (mejores de toda la frontera), pero **no se usa actualmente en el dashboard**.

---

## 6. Pruebas y validación

- **No existen tests automatizados** en el repositorio (no hay carpeta `tests/`, no hay archivos `test_*.py` ni `*_test.py`).
- **Validación out-of-sample**: existe un mecanismo de backtesting implícito. Al correr experimentos, la app descarga automáticamente datos desde `end_date` hasta `datetime.now()` (período no visto por el PSO). Estos datos se almacenan en `bt_returns_matrix` / `bt_returns_index` y se grafican en el tab de análisis como "Rendimiento en Backtesting (Retorno Acumulado %)".
- **Sin train-test split explícito** para la optimización: todo el período de entrenamiento (`start_date` → `end_date`) se usa directamente para alimentar al PSO. No hay validación cruzada ni splits múltiples.

---

## 7. Dependencias y stack técnico

| Librería    | Versión mínima | Uso                                                                  |
| ----------- | -------------- | -------------------------------------------------------------------- |
| `numpy`     | ≥2.4.4         | Álgebra lineal, operaciones sobre arrays (returns, pesos, fitnesses) |
| `pandas`    | ≥3.0.2         | DataFrames de métricas, índices de fechas, manejo de retornos        |
| `plotly`    | ≥6.7.0         | Todas las gráficas del dashboard (scatter, pie, lines)               |
| `streamlit` | ≥1.57.0        | Framework del dashboard web + gestión de sesión + caché              |
| `yfinance`  | ≥1.3.0         | Descarga de precios históricos desde Yahoo Finance                   |

**Runtime**: Python ≥3.12. Gestor de entornos: `uv` (lockfile `uv.lock`).

Librerías estándar usadas: `abc`, `dataclasses`, `io`, `json`, `zipfile`, `pathlib`, `itertools`, `colorsys`, `random`.

---

## 8. Estado aparente de completitud

### Partes completas y funcionales

- Núcleo PSO con las 5 funciones fitness, 2 topologías, 2 modelos de velocidad.
- Pipeline completo: descarga → optimización → métricas → dashboard → persistencia.
- Backtesting out-of-sample automático.
- Exportación/importación de resultados en `.psodata`.
- Modo lectura (read-only) al cargar archivo externo.

### Partes incompletas o con indicios de trabajo en progreso

| Indicador                                                                     | Detalle                                                                                                                                                    |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main.py`                                                                 | Archivo de 96 bytes prácticamente vacío; sin contenido funcional. Parece placeholder.                                                                      |
| `build_experiment_summary()` en `experiments.py`                              | Función implementada pero **no usada en ningún lugar** del dashboard (código muerto).                                                                      |
| `build_summary_dataframe()` y `build_multi_point_dataframe()` en `finance.py` | Implementadas pero **no invocadas** desde ningún tab activo. `ComparisonChartsData` y `MultiPointChartsData` tampoco se usan en los tabs actuales.         |
| `_risk_axes` en `app.py` incluye `"VaR"` como opción de eje                   | Pero la métrica `"var"` no está incluida en `build_summary_dataframe()`, que sí incluye `selected_cvar` pero no `selected_var`. Inconsistencia potencial.  |
| Sin historial de convergencia                                                 | El `pso()` no registra fitness por iteración ni diversidad. La sección de métricas del proceso es mínima.                                                  |
| Sin tests automatizados                                                       | Código sin cobertura de pruebas.                                                                                                                           |
| `pyproject.toml` description                                                  | `"Add your description here"` — sin completar.                                                                                                             |
| README                                                                        | Extremadamente escueto (13 líneas); sin documentación de uso, parámetros ni decisiones de diseño.                                                          |
| `colors.py` solo tiene 4 activos predefinidos                                 | Si el usuario añade un activo distinto a BTC/ETH/SOL/ADA, se genera un color HSV automático que puede no ser reproducible de forma estable entre sesiones. |

---

## Preguntas abiertas

1. **Elección de log-retornos**: ¿La decisión de usar log-retornos en lugar de retornos aritméticos fue deliberada (por propiedades estadísticas)? Las funciones fitness operan directamente sobre estos log-retornos, lo que afecta la interpretación de CVaR y Sharpe.
   R1. Habia leido que para estos casos log-retornos era clave, pero no tenia conocimiento de que afectara la interpretacion

2. **`max_iterations=1000` hardcodeado**: En `optimizer.py`, `max_iterations=1000` es el default pero en `ExperimentConfig` no hay campo para exponerlo. ¿Es intencional que el usuario no pueda cambiar este parámetro desde la UI?
   R2. En una instancia temprana del algoritmo, se usaban solo iteraciones, pero pase a usar convergencia (lo cual no se si esta bien hecha ya que recuerdo veia que convergia rapido, pero no se si dependa de la monedas que uso y el rango de datos o de mi implementacion)

3. **Normalización de la frontera**: Los target_values de la frontera se definen como `linspace(mean_return.min(), mean_return.max())` sobre los retornos medios _por activo_, no sobre los retornos del portafolio. ¿Es esta la definición intencional de los límites?
   R3. Aqui me agarras algo confundido, porque habia leido en un libro que definia basicamente dos tipos de problemas que salian del modelo de markowitz, ya sea optimizar maximizando el retorno del portafolio esperado dada una reestricion de varianza del portafolio o optimizar minimizando la varianza dada una reestriccion del retorno del portafolio esperado, y la verdad no recuerdo cual es el que use (si es que aplica aqui)

4. **`build_summary_dataframe()` y código muerto**: Hay funciones implementadas pero no usadas en el dashboard (comparación de punto único, tabla de resumen). ¿Son trabajo en progreso para features futuras, o han sido reemplazadas?
   R4. Si no mal recuerdo creo que fueron reemplazadas, porque habia una version un poco diferente a lo que esta ahora.

5. **Activos soportados**: El código permite cualquier ticker de yfinance en teoría, pero ¿hay restricciones de diseño (por ejemplo, la paleta de colores solo cubre 4 activos, o se asume siempre exactamente 4)?
   R5. No hay reestriccion sobre un minimo o maximo, entonces creo que habria que ver que pasa cuando hay mas de 4

6. **Criterio de selección "Best Sharpe" vs índice fijo**: `build_summary_dataframe()` tiene un parámetro `comparison_mode` con opciones `"Best Sharpe"` y un índice fijo. ¿Cuál de estos modos es el canónico para el análisis final de tesis?
   R6. La verdad tendria que considerar bien las implicaciones de cada uno antes de escoger ahora

7. **Reproducibilidad con seeds**: El seed se asigna por config como `base_seed + config_index`. Con `@st.cache_data`, si el usuario cambia solo el seed, ¿se invalida el caché y se re-corre correctamente?
   R7. Hasta donde tengo entendido no hay invalidacion, y se tendria que correr de nuevo para ver el cambio del seed o cualquier otra configuracion

8. **Interpretación del Sharpe**: La fórmula `mean_return / volatility` no descuenta la tasa libre de riesgo. ¿Es esto intencional para simplificación, o se planea añadirla?
   R8. En su momento por simpleza lo deje asi, pero no conozco la implicacion de esto bien entonces

9. **Formato `.psodata`**: Es un ZIP personalizado. ¿Hay planes de documentar el formato o mantener compatibilidad hacia atrás entre versiones?
   R9. El formato solo lo use porque trabajo en varios dispositivos, y cuando tuviera bien todo, quiero trabajar sobre los mismos resultados, entonces no pienso documentarlo de momento

10. **`run_pso.py` como script standalone**: El archivo tiene lógica de `sys.path` para ejecutarse directamente (`if __package__ is None`). ¿Se usa así durante desarrollo/debugging?
    R10. En una etapa temprana usaba solo cli para probar mientras desarrollaba el algoritmo
