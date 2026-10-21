# Contexto técnico del proyecto

## Propósito

El repositorio contiene un prototipo académico para explorar la optimización
de portafolios de criptomonedas mediante Particle Swarm Optimization (PSO).
La aplicación permite comparar objetivos de riesgo, modelos de velocidad y
topologías, y visualizar pesos, métricas, convergencia y un backtesting
posterior. El objetivo inmediato es validar la implementación del PSO y su
reproducibilidad antes de extraer conclusiones financieras o mejorar la
interfaz.

Este documento describe el estado observado en el código. No certifica que la
formulación implementada sea matemáticamente correcta.

## Arquitectura confirmada

| Módulo | Responsabilidad observada |
|---|---|
| `app.py` | Entrada Streamlit, configuración, carga/exportación y pestañas. |
| `src/controllers/experiment_controller.py` | Validación de UI, descarga/cache, construcción de configuraciones, ejecución, métricas, backtesting y persistencia. |
| `src/utils.py` | Descarga de precios `Close` mediante `yfinance` y cálculo de retornos. |
| `src/experiments.py` | Configuración de experimentos y réplicas por semilla. |
| `src/run_pso.py` | Malla de targets y ejecución de un PSO por target. |
| `src/pso/optimizer.py` | Inicialización, iteraciones, `pbest`, `gbest`, convergencia y diversidad. |
| `src/pso/particle.py` | Posición, velocidad y mejores valores de una partícula. |
| `src/pso/fitness_function.py` | CVaR, VaR, varianza, semivarianza y máximo drawdown penalizados. |
| `src/pso/velocity_model.py` | Modelos Inertia y Constriction y reparación de posiciones. |
| `src/pso/topology.py` | Topologías Ring y Global. |
| `src/finance.py` | Métricas y tablas financieras. |
| `src/models/state.py`, `src/persistence.py` | Payload de resultados y formato `.psodata`. |
| `src/ui/` | Gráficas y pestañas de comparación/análisis. |

## Flujo de datos confirmado

1. La UI recibe activos, fechas, intervalo, parámetros PSO, objetivo,
   velocidad, topología y semillas.
2. `load_crypto_returns()` descarga precios de cierre desde Yahoo Finance,
   calcula `log(close / close.shift(1))` y elimina filas con `NaN`.
3. El controlador construye el producto cartesiano de configuraciones y llama
   a `run_experiments()`.
4. Cada configuración ejecuta `run_pso()`, que crea una malla entre la media
   mínima y máxima de los activos y llama a `pso()` para cada target.
5. Se calculan métricas para la primera frontera de cada configuración; las
   réplicas multi-seed se conservan para estadísticas adicionales.
6. Se intenta cargar un período posterior desde `end_date` hasta la fecha
   actual y se guarda el resultado en `artifacts/experiments.psodata`.
7. Streamlit presenta comparación, análisis individual, convergencia, pesos y
   rendimiento acumulado.

## Datos y activos

Está confirmado que la UI ofrece `BTC-USD`, `ETH-USD`, `SOL-USD`, `ADA-USD`,
`XRP-USD`, `BNB-USD`, `DOGE-USD`, `AVAX-USD`, `DOT-USD`, `LINK-USD`, `LTC-USD`,
`BCH-USD`, `XLM-USD` y `UNI-USD`; los cuatro primeros son los valores por
defecto. Las fechas por defecto son `2020-01-01` a `2024-01-01` y los
intervalos disponibles son `1d`, `1wk` y `1mo`. La semántica inclusiva o
exclusiva de `end` no está validada en este repositorio.

La transformación confirmada usa precios `Close`, retornos logarítmicos,
`dropna()` y una matriz `T x N`. No están documentadas ni implementadas de
forma explícita políticas para duplicados, precios no positivos, outliers,
imputación, sesgo de supervivencia o zona horaria.

## Representación y restricciones observadas

Una partícula contiene un vector de pesos, un vector de velocidad, `best_pos` y
`best_val`. La inicialización usa `np.random.rand()` y normaliza posiciones.
Los modelos de velocidad recortan componentes negativas y normalizan si la
suma resultante es positiva.

La intención observable es:

\[
w_i \ge 0,\qquad \sum_i w_i = 1.
\]

Esto corresponde a un portafolio long-only y totalmente invertido, sin
apalancamiento, cortos, turnover, cardinalidad, límites individuales ni
costos. Si la posición recortada suma cero, el código actual la conserva como
vector nulo; esto es un hallazgo de auditoría, no un contrato deseado.

## Formulación implementada, sin validarla

Los targets se generan entre la menor y mayor media histórica por activo. Las
funciones de fitness tienen la forma observada:

\[
F(w;\tau) = R(w) + \lambda|\bar r_p-\tau|.
\]

`R` puede ser CVaR histórico, VaR histórico, varianza, semivarianza o máximo
drawdown. La media del portafolio es la media de `returns_matrix @ weights`.
Por tanto, el target se trata como penalización blanda; no hay una igualdad
exacta de retorno objetivo ni una demostración de que la salida sea una
frontera eficiente clásica de Markowitz.

La velocidad Inertia usa inercia y términos cognitivo/social. Constriction usa
el factor `chi` y exige `c1 + c2 > 4`. Ring usa la partícula y sus vecinos
circulares; Global usa el mejor `pbest` de la población. El máximo observado
es `1000` iteraciones y la parada usa `rtol`, `atol` y paciencia después de la
sexta iteración. El motivo de terminación no se devuelve explícitamente.

## Métricas y backtesting observados

Se calculan retorno medio, volatilidad, varianza, semivarianza, VaR, CVaR,
máximo drawdown y Sharpe simplificado. CVaR y VaR usan percentiles de retornos
logarítmicos y una convención de signo que convierte el cuantil inferior en
riesgo positivo; sus propiedades financieras todavía requieren validación.
El drawdown usa `cumprod(1 + portfolio_returns)`, cuya compatibilidad con
retornos logarítmicos es una cuestión pendiente.

El backtesting usa pesos fijos sobre datos descargados desde `end_date` hasta
la fecha actual. No hay reoptimización, comisiones, slippage, límites de
liquidez ni rebalanceo explícito. La UI anualiza con 252 períodos aun cuando
se selecciona una frecuencia semanal o mensual.

## Aleatoriedad y persistencia

`run_experiments()` fija `np.random.seed(seed)`, mientras que los modelos de
velocidad usan `random.random()`. El reporte histórico documenta que la semilla
declarada no controla toda la trayectoria. La persistencia `.psodata` conserva
arrays, tablas, configuraciones, pesos e historiales de convergencia; la
diversidad se calcula, pero el reporte histórico indica que no se serializa.

## Evidencia, hipótesis y pendientes

### Hechos respaldados por código o reportes

- La aplicación y el flujo modular descritos arriba existen.
- No hay directorio de pruebas automatizadas ni configuración declarada de
  pytest, Ruff, mypy o cobertura.
- La reproducibilidad completa con la semilla actual no está garantizada.
- La reparación puede producir una posición nula.
- La auditoría histórica registró sondeos locales, pero no experimentos
  financieros nuevos en esta preparación.

### Hipótesis que no deben tratarse como conclusiones

- Una convergencia rápida podría ser convergencia real, pérdida de diversidad,
  dominancia de la penalización, reparación degenerada o efecto de semillas.
- Las curvas pueden ser útiles para explorar configuraciones, pero no se ha
  demostrado que sean fronteras eficientes de Markowitz.
- La calidad de las métricas depende de la muestra, la cola y la convención de
  retornos; no se ha establecido un protocolo académico suficiente.

### Cuestiones pendientes

- Contrato de reproducibilidad y generador aleatorio único.
- Política para posiciones nulas, entradas no finitas y dimensiones inválidas.
- Instrumentación del motivo de parada y estadísticas por generación.
- Comparación contra funciones sintéticas y mínima varianza long-only.
- Convenciones de retornos, anualización, VaR/CVaR, drawdown y backtesting.
- Ventanas temporales, costos, rebalanceo y criterio de estabilidad entre
  semillas.

## Reportes relacionados

- [Reporte de esta preparación](../../reports/PSO-00-documentation-foundation.md)
- [Depuración de documentación heredada](../../reports/PSO-00-documentation-cleanup.md)
