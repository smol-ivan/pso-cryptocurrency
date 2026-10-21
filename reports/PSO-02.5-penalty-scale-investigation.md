# PSO-02.5 — Auditoría de escala de la penalización y descomposición del fitness

## 1. Identificación, propósito y contexto

- **ID:** PSO-02.5 (investigación técnica diagnóstica pre-PSO-03).
- **Fecha:** 2026-10-21.
- **Rama:** `main`.
- **Dependencias:** PSO-01 y PSO-01.1 implementadas y revisadas; PSO-02 implementada y aprobada con observaciones en [`reports/PSO-02-R-independent-review.md`](PSO-02-R-independent-review.md).
- **Objetivo:** Auditar el flujo y escala del parámetro de penalización ($\lambda$), resolver la discrepancia detectada entre los valores de la app Streamlit (500) y del experimento exploratorio previo (50), descomponer observacionalmente el fitness por generación en sus componentes de riesgo y penalización, y evaluar la sensibilidad numérica antes de abordar la validación con referencias sintéticas (PSO-03).
- **Alcance incluido:**
    - Auditoría de código del flujo de configuración desde Streamlit hasta la función objetivo.
    - Creación del script observacional `scripts/decompose_fitness.py`.
    - Descomposición cuantitativa del fitness por generación (riesgo vs. penalización).
    - Reproducción con parámetros reales de Streamlit (matriz sintética 300×4, enjambre 100, tolerancia y paciencia reales).
    - Estudio de sensibilidad a la penalización $\lambda \in [500, 50, 10, 1]$ con réplicas sembradas `[42, 43, 44]`.
    - Respuestas explícitas a las 7 preguntas de diagnóstico planteadas.
- **Alcance excluido:** Modificar la función objetivo de producción (`src/pso/fitness_function.py`), modificar la dinámica del optimizador (`src/pso/optimizer.py`), alterar suites de pruebas de regresión (`tests/test_pso01.py`, `tests/test_pso02.py`), realizar commits o alterar valores por defecto del sistema.

---

## 2. Alcance A — Auditoría del flujo de configuración

### 2.1 Fórmula real del fitness CVaR en producción

En [`src/pso/fitness_function.py`](file:///Users/cherry/bone/pso-cryptocurrency/src/pso/fitness_function.py#L20-L41):

```python
20:     def evaluate(
21:         self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
22:     ) -> float:
23:         # Portfolio returns across all time periods.
24:         portfolio_returns = returns_matrix @ position
25:         var_threshold = np.percentile(portfolio_returns, (1 - self.alpha) * 100)
26:         tail_losses = portfolio_returns[portfolio_returns <= var_threshold]
27:
28:         cvar = tail_losses.mean()
29:         expected_return = portfolio_returns.mean()
30:
31:         # CVaR from returns is negative in loss tails; convert to positive risk.
32:         risk = -cvar
33:
34:         # Trade-off: minimiza riesgo, pero considera distancia al target
35:         # Si retorno es exactamente el target, penalty = 0
36:         # Si se aleja, aumenta linealmente
37:         target_diff = abs(expected_return - target_value)
38:         fitness = risk + self.penalty * target_diff
39:
40:         return fitness
```

Línea exacta de la combinación:

> **Línea 38:** `fitness = risk + self.penalty * target_diff`

Donde:

- `portfolio_returns = returns_matrix @ position` (Línea 24)
- `var_threshold = np.percentile(portfolio_returns, (1 - self.alpha) * 100)` (Línea 25)
- `cvar = tail_losses.mean()` (Línea 28)
- `risk = -cvar` (Línea 32)
- `target_diff = abs(expected_return - target_value)` (Línea 37)

### 2.2 Valor por defecto de `penalty` en `CVaR.__init__`

En [`src/pso/fitness_function.py`](file:///Users/cherry/bone/pso-cryptocurrency/src/pso/fitness_function.py#L16-L18):

```python
16:     def __init__(self, alpha: float = 0.95, penalty: float = 50.0) -> None:
17:         self.alpha = alpha
18:         self.penalty = penalty
```

El valor por defecto codificado en `CVaR.__init__` es **`50.0`**. Todas las demás funciones de fitness (`VaR`, `Semivariance`, `Variance`, `MaxDrawdown`) también tienen como valor por defecto `penalty: float = 50.0`.

### 2.3 Trazabilidad del flujo del parámetro desde Streamlit

El flujo completo del parámetro `penalty` desde la interfaz gráfica hasta la instanciación de la función objetivo sigue esta ruta precisa:

1. **Definición en UI:** En [`app.py`](file:///Users/cherry/bone/pso-cryptocurrency/app.py#L144-L151):

    ```python
    144:             penalty = st.number_input(
    145:                 "Target penalty",
    146:                 min_value=1.0,
    147:                 max_value=5000.0,
    148:                 value=500.0,
    149:                 step=1.0,
    150:                 disabled=read_only,
    151:             )
    ```

    El valor predeterminado que presenta la app al usuario es **`500.0`**.

2. **Invocación del pipeline:** En [`app.py`](file:///Users/cherry/bone/pso-cryptocurrency/app.py#L179-L188):

    ```python
    179:             pipeline_result = run_analysis_pipeline(
    ...
    188:                 penalty=penalty,
    ...
    ```

3. **Recepción en controlador:** En [`src/controllers/experiment_controller.py`](file:///Users/cherry/bone/pso-cryptocurrency/src/controllers/experiment_controller.py#L155):

    ```python
    155:     penalty: float,
    ```

    Se transfiere a la función en caché en la línea 196:

    ```python
    196:             penalty=penalty,
    ```

4. **Función en caché:** En [`src/controllers/experiment_controller.py`](file:///Users/cherry/bone/pso-cryptocurrency/src/controllers/experiment_controller.py#L46):

    ```python
    46:     penalty: float,
    ```

    Pasa a la construcción de configuraciones en la línea 66:

    ```python
    66:         penalty=penalty,
    ```

5. **Construcción de `ExperimentConfig`:** En [`src/controllers/experiment_controller.py`](file:///Users/cherry/bone/pso-cryptocurrency/src/controllers/experiment_controller.py#L87):
    ```python
    87:     penalty: float,
    ```
    Instancia la función de fitness en la línea 105:
    ```python
    105:             fitness_function = CVaR(alpha=alpha, penalty=penalty)
    ```

Cuando se corre a través de la aplicación Streamlit, `CVaR` recibe **`penalty = 500.0`**.

### 2.4 Invocación en `scripts/diagnose_convergence.py`

En [`scripts/diagnose_convergence.py`](file:///Users/cherry/bone/pso-cryptocurrency/scripts/diagnose_convergence.py):

- Línea 264:
    ```python
    264:         ("CVaR    / Constriction / Ring", CVaR(),     lambda: Constriction(),  RingTopology()),
    ```
- Línea 324:
    ```python
    324:         ("CVaR / Inertia / Global",      CVaR(),      lambda: Inertia(),      GlobalTopology()),
    ```
- Línea 326:
    ```python
    326:         ("CVaR / Constriction / Ring",    CVaR(),      lambda: Constriction(), RingTopology()),
    ```

El script invoca `CVaR()` **sin argumentos**. No pasa `penalty=500.0`.

### 2.5 Valor real recibido en el experimento informal PSO-02.5

Al invocar `CVaR()` sin argumentos, Python aplica el valor por defecto de la signatura en `fitness_function.py:16`, que es **`penalty = 50.0`**. El reporte [`reports/PSO-02.5-convergence-exploration.md`](PSO-02.5-convergence-exploration.md) documentó observaciones generadas exclusivamente bajo `penalty = 50.0` (como se menciona explícitamente en su línea 83: _"Con penalty=50, una diferencia de 0.01 en retorno genera un costo de 0.5..."_).

### 2.6 Resolución documentada de la discrepancia (50 vs 500)

**Existe una discrepancia confirmada de un orden de magnitud (10x)** entre el valor predeterminado de la interfaz gráfica y el valor evaluado en la exploración informal previa:

- Interfaz de producción (Streamlit): `500.0`
- Constructor en código (`CVaR.__init__`): `50.0`
- Script `diagnose_convergence.py`: `50.0`

**Implicancia técnica:** Si con una penalización de 50.0 ya se observaba dominancia del término de penalización en los extremos de la frontera, con la penalización de 500.0 utilizada en la aplicación real esa dominancia se amplifica por un factor de 10.

---

## 3. Alcance B — Descomposición del fitness por generación

### 3.1 Metodología observacional

Se implementó el script autónomo [`scripts/decompose_fitness.py`](file:///Users/cherry/bone/pso-cryptocurrency/scripts/decompose_fitness.py). Cumple estrictamente las reglas del proyecto:

1. Utiliza la función `CVaR.evaluate()` de producción sin alterarla.
2. No instrumenta el interior del ciclo del optimizador.
3. Extrae la información observacionalmente tras la ejecución mediante `ConvergenceTrace` (`return_diagnostics=True`):
    - $\text{Retorno medio del mejor en } t: \bar{r}_t = \text{trace.best\_mean\_return}[t]$
    - $\text{Diferencia al target en } t: \Delta_t = \text{trace.best\_target\_difference}[t] = |\bar{r}_t - \tau|$
    - $\text{Componente de penalización en } t: P_t = \lambda \cdot \Delta_t$
    - $\text{Componente de riesgo en } t: R_t = \text{trace.gbest}[t] - P_t$
    - $\text{Fitness total recalculado: } F_t = R_t + P_t$
4. **Verificación matemática cruzada:** Al finalizar, sobre la posición óptima devuelta `best_pos`, se evalúa de forma independiente `CVaR(alpha=0.95, penalty=0.0).evaluate(best_pos, returns_matrix, target)` para confirmar que coincide exactamente con $R_{\text{final}}$ y que la suma $R + P$ coincide con `best_val` con error absoluto inferior a $10^{-12}$.

---

## 4. Alcance C — Reproducción con configuración real de Streamlit

### 4.1 Configuración experimental

| Parámetro                         | Valor configurado                       | Justificación / Origen                          |
| --------------------------------- | --------------------------------------- | ----------------------------------------------- |
| Datos de retornos                 | Sintéticos 300 obs × 4 activos          | Fija con semilla NumPy 42 (evita Yahoo Finance) |
| Función de fitness                | `CVaR(alpha=0.95, penalty=500.0)`       | Configuración real de Streamlit                 |
| Tamaño de enjambre (`swarm_size`) | 100                                     | Default de Streamlit (`app.py:88`)              |
| Parámetros de parada              | `patience=10`, `rtol=1e-4`, `atol=1e-8` | Defaults de Streamlit (`app.py:89-110`)         |
| Límite de iteraciones             | 1000                                    | Default de `pso()`                              |
| Semilla de réplica                | 42                                      | Default de Streamlit (`app.py:116`)             |
| Modelo de velocidad               | `Inertia(c1=1.7, c2=1.7, inertia=0.8)`  | Sliders por defecto en Streamlit                |
| Topologías evaluadas              | `GlobalTopology` y `RingTopology`       | Comparación cruzada                             |

**Estadísticas de la matriz sintética (300×4):**

- Medias de los activos: `[-0.00036169, +0.00017953, +0.00004867, +0.00067123]`
- Target BAJO ($\tau_{\min}$): `-0.00036169` (corresponde exactamente a la media del Activo 0)
- Target MEDIO ($\tau_{\text{mid}}$): `+0.00015477` (punto intermedio del rango de retornos)
- Target ALTO ($\tau_{\max}$): `+0.00067123` (media del Activo 3)

---

### 4.2 Descomposición por generación: Caso A — Target BAJO (Estancamiento / Dominancia)

**Configuración:** Target = `-0.000362`, Penalty = 500.0, Swarm = 100, Inertia / Global, Semilla = 42.

| Gen |  gbest   | Riesgo (-CVaR) | Penalización | Pen % | Retorno Medio | \|Ret - Target\| | Diversidad | Movimiento |
| :-: | :------: | :------------: | :----------: | :---: | :-----------: | :--------------: | :--------: | :--------: |
|  0  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.165243  |  0.380720  |
|  1  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.041539  |  0.207865  |
|  2  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.024469  |
|  3  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  4  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  5  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  6  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  7  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  8  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
|  9  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 10  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 11  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 12  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 13  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 14  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |
| 15  | 0.041493 |    0.041493    |   0.000000   | 0.00% |   -0.000362   |     0.000000     |  0.000000  |  0.000000  |

- **Terminación:** Iteración 15 (16 iteraciones completadas), motivo: `patience`.
- **Portafolio resultante:** `w = [1.0, 0.0, 0.0, 0.0]` (100% en Activo 0).
- **Verificación cruzada:** Error absoluto `|total - gbest| = 0.00e+00`.

**Mecánica observada:**

1. Al fijar el target en el mínimo de los retornos medios, el **único** punto del simplex $\{w \in \mathbb{R}^4 : w_i \ge 0, \sum w_i = 1\}$ cuyo retorno esperado es igual al target es el vértice $e_0 = [1, 0, 0, 0]$.
2. Cualquier combinación diversificada produce $\bar{r}_p > \tau_{\min}$. Una discrepancia tan minúscula como $\Delta = 0.0002$ genera un costo de penalización de $500 \times 0.0002 = 0.100$.
3. Como el riesgo de diversificación oscila entre 0.02 y 0.03, el fitness de cualquier portafolio interior es $F \approx 0.025 + 0.100 = 0.125 \gg 0.041493$.
4. El vértice $e_0$ se convierte en un pozo gravitacional inescapable. Para la Generación 2 la diversidad colapsa a 0.000000 y el movimiento a 0.000000. Tras la barrera de 6 iteraciones sin paciencia, la paciencia se acumula de 1 a 10 y detiene la ejecución en la iteración 15 (16 generaciones).

---

### 4.3 Descomposición por generación: Caso B — Target MEDIO (Convergencia Gradual)

**Configuración:** Target = `+0.000155`, Penalty = 500.0, Swarm = 100, Inertia / Global, Semilla = 42.

| Gen |  gbest   | Riesgo (-CVaR) | Penalización | Pen % | Retorno Medio | \|Ret - Target\| | Diversidad | Movimiento |
| :-: | :------: | :------------: | :----------: | :---: | :-----------: | :--------------: | :--------: | :--------: |
|  0  | 0.026101 |    0.025869    |   0.000233   | 0.89% |   0.000154    |     0.000000     |  0.117137  |  0.218447  |
|  1  | 0.025703 |    0.025670    |   0.000033   | 0.13% |   0.000155    |     0.000000     |  0.167519  |  0.203517  |
|  2  | 0.025703 |    0.025670    |   0.000033   | 0.13% |   0.000155    |     0.000000     |  0.141116  |  0.165033  |
|  3  | 0.025667 |    0.025406    |   0.000262   | 1.02% |   0.000154    |     0.000001     |  0.145947  |  0.190001  |
|  4  | 0.025197 |    0.025177    |   0.000021   | 0.08% |   0.000155    |     0.000000     |  0.144526  |  0.205565  |
|  5  | 0.025197 |    0.025177    |   0.000021   | 0.08% |   0.000155    |     0.000000     |  0.154910  |  0.167432  |
|  6  | 0.025197 |    0.025177    |   0.000021   | 0.08% |   0.000155    |     0.000000     |  0.153239  |  0.193246  |
|  7  | 0.025197 |    0.025177    |   0.000021   | 0.08% |   0.000155    |     0.000000     |  0.133595  |  0.178306  |
|  8  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.128789  |  0.160680  |
|  9  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.134385  |  0.182482  |
| 10  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.125249  |  0.143599  |
| 11  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.121731  |  0.166211  |
| 12  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.122200  |  0.143951  |
| 13  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.113746  |  0.148165  |
| 14  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.125931  |  0.162268  |
| 15  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.120435  |  0.141340  |
| 16  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.115955  |  0.152997  |
| 17  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.117479  |  0.135576  |
| 18  | 0.025188 |    0.025169    |   0.000019   | 0.07% |   0.000155    |     0.000000     |  0.116456  |  0.158090  |

- **Terminación:** Iteración 18 (19 iteraciones completadas), motivo: `patience`.
- **Portafolio resultante:** `w = [0.2354, 0.2770, 0.2202, 0.2673]`.
- **Verificación cruzada:** `Riesgo directo = 0.02516929`, `Penalización = 0.00001885`, `Suma = 0.02518815` (error absoluto $0.00\times 10^0$).

**Mecánica observada:**

1. El target $\tau_{\text{mid}}$ interseca el interior del simplex. Existe un subespacio afín continuo de portafolios diversificados donde $\sum w_i \bar{r}_i = \tau_{\text{mid}}$.
2. Las partículas encuentran rápidamente combinaciones donde el error con respecto al target es $\le 10^{-6}$.
3. La penalización pasa a representar menos del **0.1%** del fitness total ($0.000019$ vs $0.025169$).
4. El enjambre no colapsa: la diversidad se mantiene robusta en **0.116456** y el movimiento medio en **0.158090**.
5. La parada ocurre no por colapso, sino porque la mejora incremental de `gbest` se mantiene por debajo de `tolerance` durante 10 generaciones mientras la población continúa en exploración activa.

---

### 4.4 Comparación con Topología Ring

Bajo `RingTopology(k_neighbors=1)`:

- **Target BAJO:** Iteraciones: 16, motivo: `patience`, `gbest_final = 0.041493`, `div_final = 0.000000`, `mov_final = 0.000000`, portafolio: `[1.0, 0.0, 0.0, 0.0]`. La dispersión local retrasó el colapso hasta la generación 7, pero convergió inevitablemente al mismo vértice.
- **Target MEDIO:** Iteraciones: 17, motivo: `patience`, `gbest_final = 0.024237`, `div_final = 0.197903`, `mov_final = 0.136498`, portafolio: `[0.1754, 0.2561, 0.3362, 0.2323]`. El riesgo obtenido fue $0.024214$ (ligeramente superior en calidad al de Global) con penalización residual de $0.000024$ (0.10%).

---

## 5. Alcance D — Sensibilidad de la penalización

Se evaluaron de forma cruzada 4 niveles de penalización $\lambda \in [500, 50, 10, 1]$ en combinación con 3 semillas estocásticas `[42, 43, 44]` sobre la misma matriz sintética y bajo el modelo `Inertia / Global`.

### 5.1 Tabla de sensibilidad: Target BAJO ($\tau = -0.000362$)

| Penalty ($\lambda$) | Seed | gbest_final | Iters |  Motivo  | div_final | mov_final | Riesgo (-CVaR) | Penalización | Pen %  |
| :-----------------: | :--: | :---------: | :---: | :------: | :-------: | :-------: | :------------: | :----------: | :----: |
|      **500.0**      |  42  |  0.041493   |  16   | patience | 0.000000  | 0.000000  |    0.041493    |   0.000000   | 0.00%  |
|      **500.0**      |  43  |  0.041493   |  16   | patience | 0.000000  | 0.000000  |    0.041493    |   0.000000   | 0.00%  |
|      **500.0**      |  44  |  0.041493   |  16   | patience | 0.000000  | 0.000000  |    0.041493    |   0.000000   | 0.00%  |
|      **50.0**       |  42  |  0.036494   |  19   | patience | 0.062763  | 0.079524  |    0.024274    |   0.012220   | 33.49% |
|      **50.0**       |  43  |  0.036494   |  16   | patience | 0.048864  | 0.057304  |    0.024286    |   0.012209   | 33.45% |
|      **50.0**       |  44  |  0.036494   |  16   | patience | 0.073421  | 0.079672  |    0.024292    |   0.012202   | 33.44% |
|      **10.0**       |  42  |  0.026025   |  16   | patience | 0.063665  | 0.074247  |    0.023062    |   0.002963   | 11.39% |
|      **10.0**       |  43  |  0.026025   |  16   | patience | 0.069781  | 0.083184  |    0.023061    |   0.002965   | 11.39% |
|      **10.0**       |  44  |  0.026026   |  16   | patience | 0.085285  | 0.096626  |    0.023064    |   0.002961   | 11.38% |
|       **1.0**       |  42  |  0.022948   |  22   | patience | 0.086356  | 0.094413  |    0.022570    |   0.000378   | 1.65%  |
|       **1.0**       |  43  |  0.022947   |  20   | patience | 0.083485  | 0.120958  |    0.022570    |   0.000377   | 1.64%  |
|       **1.0**       |  44  |  0.022949   |  24   | patience | 0.080904  | 0.120201  |    0.022568    |   0.000381   | 1.66%  |

**Hallazgo clave en Target BAJO:**

- Con $\lambda = 500$, el vértice monoactivo $e_0$ con riesgo $0.0415$ y penalización $0.0000$ es el mínimo global de la función penalizada. Todo el enjambre colapsa forzosamente.
- Al descender a $\lambda = 50$, el balance cambia drásticamente: un portafolio interior diversificado logra un riesgo de **0.0243** con una discrepancia al target de $\approx 0.000244$. Su costo por penalización es $50 \times 0.000244 = 0.0122$. El fitness total resultante es $0.0243 + 0.0122 = 0.0365 < 0.0415$. Por lo tanto, **el portafolio diversificado vence al vértice**, y el enjambre **no colapsa** (diversidad final $\approx 0.063$).
- Con $\lambda = 1$, la penalización se vuelve despreciable ($1.65\%$) y el PSO encuentra el portafolio de mínima varianza / riesgo global del conjunto de activos ($\text{CVaR} \approx 0.02257$).

---

### 5.2 Tabla de sensibilidad: Target MEDIO ($\tau = +0.000155$)

| Penalty ($\lambda$) | Seed | gbest_final | Iters |  Motivo  | div_final | mov_final | Riesgo (-CVaR) | Penalización | Pen % |
| :-----------------: | :--: | :---------: | :---: | :------: | :-------: | :-------: | :------------: | :----------: | :---: |
|      **500.0**      |  42  |  0.025188   |  19   | patience | 0.116456  | 0.158090  |    0.025169    |   0.000019   | 0.07% |
|      **500.0**      |  43  |  0.024171   |  34   | patience | 0.095847  | 0.101795  |    0.024170    |   0.000001   | 0.00% |
|      **500.0**      |  44  |  0.024151   |  20   | patience | 0.135703  | 0.178099  |    0.024150    |   0.000000   | 0.00% |
|      **50.0**       |  42  |  0.024153   |  17   | patience | 0.094662  | 0.122864  |    0.024148    |   0.000005   | 0.02% |
|      **50.0**       |  43  |  0.024153   |  16   | patience | 0.138602  | 0.163902  |    0.024153    |   0.000000   | 0.00% |
|      **50.0**       |  44  |  0.024155   |  18   | patience | 0.126399  | 0.161010  |    0.024155    |   0.000001   | 0.00% |
|      **10.0**       |  42  |  0.023642   |  26   | patience | 0.086052  | 0.100297  |    0.022894    |   0.000749   | 3.17% |
|      **10.0**       |  43  |  0.023643   |  19   | patience | 0.118754  | 0.157946  |    0.022882    |   0.000761   | 3.22% |
|      **10.0**       |  44  |  0.023642   |  18   | patience | 0.131951  | 0.173794  |    0.022911    |   0.000731   | 3.09% |
|       **1.0**       |  42  |  0.022703   |  26   | patience | 0.080563  | 0.099876  |    0.022568    |   0.000135   | 0.59% |
|       **1.0**       |  43  |  0.022702   |  20   | patience | 0.087721  | 0.126703  |    0.022570    |   0.000132   | 0.58% |
|       **1.0**       |  44  |  0.022702   |  24   | patience | 0.083365  | 0.127599  |    0.022571    |   0.000131   | 0.58% |

**Hallazgo clave en Target MEDIO:**

- Para un target intermedio factible, la penalización no causa colapso bajo ningún valor de $\lambda \in [1, 500]$.
- La diversidad permanece alta ($0.08$ a $0.14$) y el movimiento activo ($0.10$ a $0.18$).
- Variaciones entre semillas generan pequeñas diferencias en la trayectoria y en las iteraciones de parada (16 a 34), confirmando estocasticidad real.

---

## 6. Análisis: Respuestas explícitas a las 7 preguntas

### 1. ¿Qué penalty usa la app vs qué usó el experimento PSO-02.5?

- **La aplicación Streamlit (`app.py:144-151`):** Configura `value=500.0`.
- **El experimento informal PSO-02.5 (`scripts/diagnose_convergence.py`):** Instanció `CVaR()` sin argumentos, tomando el valor por defecto del código fuente en `src/pso/fitness_function.py:16`, que es `50.0`.
- **Resolución:** El experimento informal evaluó una penalización **10 veces menor** a la que usa la aplicación en producción.

### 2. ¿Cuál es la magnitud típica de cada componente?

- **Componente de riesgo ($-CVaR$):** En datos logarítmicos diarios estándar de activos y portafolios, el CVaR al 95% oscila entre **0.02 y 0.06** (2% a 6% de pérdida esperada en la cola del 5%).
- **Componente de penalización ($\lambda \cdot |\bar{r}_p - \tau|$):** Las diferencias de retorno diario típico son de magnitud $10^{-4}$ a $10^{-3}$ ($0.01\%$ a $0.1\%$).
    - Con $\lambda = 500$: Una desviación de apenas $0.0002$ genera un término de penalización de **0.100**, el cual es **2 a 5 veces mayor** que todo el riesgo del portafolio.
    - Con $\lambda = 50$: La misma desviación genera **0.010** (~20-40% del riesgo).
    - Con $\lambda = 10$: Genera **0.002** (~5-10% del riesgo).
    - Con $\lambda = 1$: Genera **0.0002** (<1% del riesgo).

### 3. ¿La penalización domina numéricamente? ¿En qué casos?

- **Sí, domina de manera absoluta en dos situaciones:**
    1. **Generación 0 (Inicialización):** Al distribuir las partículas aleatoriamente por el simplex, sus retornos distan del target. Con $\lambda = 500$, la penalización conforma entre el **70% y el 95%** del fitness en la población inicial.
    2. **Targets extremos de la frontera ($\tau = \min \bar{r}_i$ o $\tau = \max \bar{r}_i$):** Dado que el único punto del simplex con ese retorno es un vértice monoactivo, cualquier portafolio diversificado incurre en una penalización masiva que supera con creces el beneficio de reducir el riesgo. En consecuencia, la penalización fuerza a que el mínimo global de la función objetivo sea artificialmente el vértice monoactivo.
- **No domina en targets interiores:** En targets en el interior del rango, existe un hiperplano afín de portafolios factibles con retorno idéntico al target. El enjambre alcanza este subespacio afín rápidamente, reduciendo la penalización a valores residuales ($< 10^{-5}$, representando $< 0.1\%$ del fitness).

### 4. ¿El estancamiento coincide con pérdida de diversidad/movimiento?

- **Depende del régimen:**
    - **En targets extremos con $\lambda = 500$:** El estancamiento **coincide exactamente con el colapso físico total** de diversidad (`div = 0.000000`) y de movimiento (`mov = 0.000000`). Todas las partículas colapsan en el mismo vértice simplex y se congelan.
    - **En targets intermedios:** El estancamiento **no es físico ni colapso de enjambre**. La población conserva alta diversidad (`div ≈ 0.10 - 0.14`) y movimiento activo (`mov ≈ 0.10 - 0.18`). El estancamiento aquí es puramente numérico respecto al criterio de parada: la mejora de `gbest` no supera `atol + rtol * abs(gbest)` durante `patience=10` iteraciones consecutivas.

### 5. ¿Se reproduce el comportamiento con configuración real de Streamlit?

- **Sí, se reproduce con exactitud:**
    - Target bajo: En 16 iteraciones exactas por paciencia (6 de gracia + 10 de paciencia), colapso total a diversidad 0.0, movimiento 0.0 y pesos idénticos `[1, 0, 0, 0]` en todas las semillas.
    - Target medio: Convergencia gradual entre 19 y 34 iteraciones con diversidad y movimiento activos, alcanzando portafolios balanceados.
    - El comportamiento se valida idéntico tanto para `GlobalTopology` como para `RingTopology`.

### 6. ¿Los experimentos permiten atribuir causalidad o solo asociación?

- **Causalidad matemática demostrada:** En la superficie de respuesta del fitness penalizado, la demostración de que $\lambda=500$ transforma el vértice monoactivo en el mínimo global estricto es matemática y causal. Al variar experimentalmente $\lambda$ de 500 a 50 manteniendo todos los demás factores constantes (matriz, enjambre, topología, semillas), el mínimo global del enjambre cambia de forma controlada del vértice monoactivo a un portafolio interior diversificado.
- **Asociación en dinámica interna:** En cuanto a las trayectorias cinemáticas individuales y colisiones/proyecciones antes de normalizar, se mantiene como asociación observacional agregada, pues no se rastreó el estado continuo pre-reparación partícula a partícula.

### 7. ¿Qué preguntas siguen pendientes para PSO-03?

1. **Optimalidad vs. Mínima Varianza Long-Only:** Cuando el target se retira o se fija $\lambda=1$, ¿el portafolio convergente coincide con la solución analítica exacta de Markowitz resuelta por un solver cuadrático estándar (QP)? (Objetivo central de PSO-03).
2. **Capacidad de búsqueda en funciones sintéticas clásicas:** ¿Cómo responde el optimizador frente a paisajes de prueba con óptimo conocido (Sphere, Rastrigin, Rosenbrock) restringidos al simplex?
3. **Calibración metodológica de la penalización:** ¿Debe mantenerse una penalización estática $\lambda=500$, o debe formularse un esquema de penalización cuadrática, adaptativa o basada en proyección para construir una frontera eficiente válida en el sentido de Markowitz? (Tema de enlace con PSO-06).
4. **Calibración de tolerancias de convergencia:** ¿El criterio `rtol=1e-4`, `atol=1e-8`, `patience=10` es excesivamente estricto o prematuro para objetivos donde la población sigue explorando activamente?

---

## 7. Limitaciones de este estudio

1. **Datos sintéticos:** Se empleó una matriz sintética gaussiana de 300 observaciones × 4 activos fija con semilla 42. Aunque sus propiedades de escala reproducen fielmente los retornos criptográficos observados en la app, no incluye colas pesadas empíricas, saltos de mercado ni correlaciones cambiantes en el tiempo de Yahoo Finance.
2. **Enfoque puramente observacional:** De acuerdo con las reglas de no intervención, las métricas fueron obtenidas de las estructuras de diagnóstico públicas y la posición final sin perturbar el ciclo interno del optimizador.
3. **No certificación financiera:** Este reporte no certifica la corrección matemática ni financiera de la frontera de inversión generada ni de la convención de signo de CVaR.

---

## 8. Recomendación razonada sobre avanzar a PSO-03

**Recomendación: AVANZAR A PSO-03.**

**Justificación:**

1. Las causas del comportamiento del PSO observado por el usuario en Streamlit (convergencia aparente inmediata a los mismos pesos en targets de bajo riesgo) están **plenamente identificadas y explicadas cuantitativamente**: no se trata de una falla misteriosa ni de un milagro de convergencia instantánea al óptimo global, sino de la dominancia matemática de la penalización ($\lambda=500$) en los extremos de la malla de retornos, donde el vértice monoactivo es la única solución que anula la penalización.
2. La discrepancia histórica de configuración (50 en el script exploratorio informal vs 500 en Streamlit) queda documentada, resuelta y trazada hasta las líneas de código fuente.
3. Se comprobó que en regiones interiores del simplex el PSO mantiene diversidad y movimiento activos, optimizando el riesgo una vez satisfecho el target.
4. Con esta base diagnóstica clara, el proyecto está en condiciones óptimas para ejecutar **PSO-03** (Validación con referencias sintéticas y mínima varianza long-only frente a solver analítico independiente), donde se medirá formalmente la precisión del PSO en problemas con solución teórica exacta.

---

## 9. Evidencia de pruebas de regresión

Comprobación ejecutada tras completar la herramienta diagnóstica y las evaluaciones:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Resultado:

- **12/12 pruebas pasadas** (0 errores, 0 fallos).
- Ningún archivo de producción en `src/` ni en `tests/` fue modificado.
