# PSO-04 — Validación de convenciones de retornos y riesgo

## Identificación y estado

- **ID:** PSO-04
- **Fecha:** 2026-10-21
- **Rama:** `main`, `ahead 2` respecto de `origin/main`
- **Estado inicial:** pendiente; PSO-03 figura como revisada en el roadmap y
  su implementación y revisión independiente están documentadas.
- **Estado final:** implementada; revisión independiente pendiente.
- **Commit:** no creado.

El estado inicial del árbol incluía cambios de PSO-02/PSO-03, reportes,
scripts y la creación de este prompt. Se conservaron los cambios ajenos y no
se modificó ningún archivo de producción financiero, del PSO, del backtesting
ni de la interfaz.

## Objetivo, alcance y criterios

El objetivo fue establecer qué calcula actualmente el sistema y qué significa
cada magnitud, usando inspección del flujo real y casos manuales reproducibles.

### Incluido

- Obtención de precios, valores faltantes, retornos y frecuencia.
- Construcción del retorno del portafolio.
- VaR, CVaR, percentil, cola, empates y signos.
- Drawdown y maximum drawdown ya existentes.
- Anualización ya existente.
- Relación entre riesgo, retorno esperado, target, distancia y penalización.
- Pruebas independientes y tabla de decisiones.

### Excluido

- Cambios a ecuaciones o métricas de producción.
- Cambios de `alpha`, `penalty`, parámetros PSO, targets o topologías.
- Sustitución de retornos logarítmicos por simples o viceversa.
- Nuevas métricas, backtesting, costos, rebalanceo o rediseño de UI.
- Descargas reales de Yahoo Finance y ejecución interactiva de Streamlit.

## Convenciones observadas

### Retornos y frecuencia

`src/utils.py:7-27` descarga la columna `Close`, calcula:

```python
np.log(close_prices / close_prices.shift(1)).dropna()
```

El primer valor por activo se elimina por `shift(1)` y `dropna()` elimina
cualquier fila que siga conteniendo un valor faltante en alguno de los
activos. Un `DataFrame` vacío produce `ValueError`; no hay imputación,
validación explícita de precios positivos, tratamiento de duplicados u
outliers. El `interval` se pasa directamente a `yfinance`; la matriz
resultante conserva una observación por fila del intervalo descargado. El
código no convierte semanal o mensual a diario y no anualiza el vector de
medias.

`src/utils.py:24-27` define `mean_return` como la media aritmética de los
retornos logarítmicos por observación. `src/run_pso.py:58-81` usa esas medias
para targets y `src/pso/fitness_function.py:24`/`src/finance.py:20-22`
construyen el retorno del portafolio como `returns_matrix @ weights`, por lo
que el rendimiento objetivo, el retorno esperado y el riesgo se expresan en
la misma unidad por observación de la matriz.

No se calcula el retorno simple del portafolio en esa etapa. Para una
observación con activos que rinden `r_i` en términos logarítmicos, el sistema
usa `sum_i w_i r_i`; esto no equivale en general a
`sum_i w_i (exp(r_i)-1)` ni a la riqueza de un portafolio buy-and-hold.

### VaR y CVaR

`src/pso/fitness_function.py:24-35` y `src/finance.py:25-30` usan:

```python
threshold = np.percentile(portfolio_returns, (1 - alpha) * 100)
tail = portfolio_returns[portfolio_returns <= threshold]
```

Así, `alpha` es la masa de confianza nominal y `1-alpha` selecciona el
percentil inferior. CVaR se calcula como la media del retorno de esa cola y
se niega para producir una magnitud de riesgo positiva:

```text
CVaR_return = mean(tail returns)
CVaR risk   = -CVaR_return
```

VaR es `-threshold`. En consecuencia, una pérdida de `0.10` se presenta como
riesgo positivo `0.10`; si el cuantil o la cola son positivos, el signo puede
ser negativo aunque la implementación conserve la misma fórmula. Las
observaciones exactamente iguales al umbral entran en la cola por `<=`.
Interpolación del percentil es la de `numpy.percentile`; no se implementa una
convención histórica discreta alternativa ni una integración continua del
cuantil.

La etiqueta de la interfaz es consistente con el parámetro: `app.py:35`
presenta `CVaR {alpha*100:.0f}%` y `app.py:33-45` selecciona las columnas
`cvar`, `var` y `max_drawdown`. La palabra “CVaR” sigue siendo ambigua entre
retorno medio de cola y pérdida positiva; el código y las tablas usan la
segunda.

### Drawdown

`src/finance.py:9-14`, `src/pso/fitness_function.py:118-124` y
`src/ui/charts.py:382-383,440-441` construyen:

```text
wealth_t = prod_{s <= t} (1 + portfolio_return_s)
running_max_t = max_{u <= t}(wealth_u)
drawdown_t = (wealth_t - running_max_t) / running_max_t
max_drawdown = -min(drawdown_t)
```

La salida es una pérdida positiva, normalmente en `[0, 1)` para retornos
simples válidos y riqueza positiva. La implementación trata la entrada como
retorno simple porque usa `1 + return`; sin embargo, la matriz de producción
contiene retornos logarítmicos. Por tanto, existe una discrepancia confirmada:
la curva calculada no es la riqueza exacta de retornos logarítmicos
acumulados. También se aplica a pesos fijos sobre la secuencia observada; no
hay rebalanceo, costos ni una política buy-and-hold explícita en esta función.

### Anualización

`src/finance.py:194-195` define:

```python
(1 + daily_return) ** periods_per_year - 1
```

El valor por defecto es `252`. `src/ui/tabs/analysis.py:198-204` pasa
`df_metrics["mean_return"]` directamente a `annualized_return`, lo etiqueta
“Daily return” y “Annualized return”, incluso cuando `interval` puede ser
`1wk` o `1mo`. La función por sí sola aplica capitalización de retorno simple;
no convierte primero una media logarítmica mediante `exp`, no anualiza la
volatilidad y no recibe la frecuencia elegida desde la UI.

Esta es una discrepancia de interpretación, no una modificación autorizada:
se anualiza una media de retornos logarítmicos como si fuera retorno simple
diario y se mantiene el factor 252 para todas las frecuencias.

## Relación con la función objetivo

Las clases de `src/pso/fitness_function.py` implementan para CVaR:

```text
portfolio_returns = returns_matrix @ position
expected_return   = mean(portfolio_returns)
risk              = -mean(portfolio_returns[portfolio_returns <= threshold])
fitness           = risk + penalty * abs(expected_return - target_value)
```

VaR usa `risk = -threshold`; las otras funciones sustituyen `risk` por su
propia magnitud. La media, el target y su distancia están en unidades por
observación del retorno logarítmico. El riesgo de CVaR/VaR está expresado
como pérdida positiva derivada de esa misma muestra. La suma es numérica y
comparable dentro de la función implementada, pero la adecuación de la escala
de `penalty` no se decide aquí y pertenece a PSO-06.

## Casos manuales y pruebas

Se añadió `tests/test_pso04.py`. Las expectativas se calcularon antes de
invocar las funciones bajo prueba:

| Caso | Entrada y resultado esperado | Convención verificada |
|---|---|---|
| Precios | `AAA=[100,110,99]`, `BBB=[200,220,242]`; salida `log(P_t/P_{t-1})`, dos filas, primer valor eliminado | Precios `Close`, log returns por observación y `dropna()` |
| Portafolio | `r=[log(1.1),log(0.9)]`, `w=[.25,.75]`; media `0.25log(1.1)+.75log(.9)`; `exp(log(1.1))-1=.1` y no equivale a ponderar simples | Combinación lineal de retornos logarítmicos y distinción frente a simple |
| VaR/CVaR con empate | `[-.2,-.1,-.1,.2]`, `alpha=.5`; percentil `-.1`, cola `<=` de tres valores; VaR `.1`, CVaR `(.2+.1+.1)/3` en fitness y métricas | Cola inferior, interpolación NumPy, inclusión del umbral y signo positivo |
| Drawdown | Retornos simples `[.1,-.2,.1]`; riqueza `[1.1,.88,.968]`; MDD `.2` | Capitalización `1+r`, máximo acumulado y pérdida positiva |
| Anualización | `annualized_return(.01,2)=.0201`; por defecto `(1.01**252)-1` | Capitalización simple y factor predeterminado |
| Fitness | CVaR `.15`, target `.15`, media `0`, penalty `50`; fitness `7.65` | `risk + penalty*abs(expected-target)` |

El loader se prueba con `unittest.mock.patch`; no se accede a Yahoo Finance.
Las pruebas no llaman a la función bajo prueba para construir sus valores
esperados.

## Tabla de decisiones

| Tema | Convención actual | Evidencia en código/pruebas | Alternativas relevantes | Consecuencia académica o interpretativa | Estado |
|---|---|---|---|---|---|
| Retornos de entrada | Log returns de `Close`, por observación | `src/utils.py:17-27`; `test_pso04.py` | Retornos simples, precios ajustados, políticas de datos faltantes | La media y targets son medias logarítmicas de la frecuencia descargada | Confirmado |
| Retorno del portafolio | `R w`, suma ponderada de log returns | `src/finance.py:20`; `test_pso04.py` | Rebalanceo simple, buy-and-hold con riqueza | No equivale automáticamente al retorno simple o a buy-and-hold | Confirmado |
| `alpha` | Confianza nominal; cola en percentil `100(1-alpha)` | `fitness_function.py:25`; `test_pso04.py` | Convenciones discretas/continuas de cuantiles | El resultado depende de interpolación NumPy y tamaño muestral | Confirmado; convención académica requiere aprobación |
| CVaR | Negativo de la media de retornos de cola, pérdida positiva | `fitness_function.py:28-35`; `finance.py:27`; pruebas PSO-03/04 | Media de retorno de cola sin negar; Expected Shortfall de pérdidas | “CVaR” en tablas significa riesgo positivo, no retorno medio | Confirmado |
| Empates de umbral | Se incluyen con `<=` | `fitness_function.py:26`; `test_pso04.py` | Seleccionar exactamente una fracción ordenada | El tamaño efectivo de la cola puede superar `1-alpha` | Confirmado |
| VaR | Negativo del percentil inferior | `fitness_function.py:58-62`; `test_pso04.py` | VaR positivo sobre pérdidas explícitas | Puede ser negativo si el cuantil de retornos es positivo | Confirmado |
| Drawdown | `cumprod(1+r)` sobre retornos tratados como simples | `finance.py:9-14`; charts; prueba manual | `cumprod(exp(log_r))`, precios o riqueza buy-and-hold | Hay discrepancia entre entrada logarítmica y acumulación | Discrepancia detectada |
| Frecuencia | La frecuencia descargada se conserva; sin conversión | `utils.py`, controlador; prueba de loader | Normalizar frecuencia o exigir frecuencia diaria | Targets y riesgos no son comparables entre intervalos sin metadatos | Confirmado; política académica requiere aprobación |
| Anualización | `(1+r)^252-1` sobre media etiquetada diaria | `finance.py:194-195`, `analysis.py:198-204`; prueba | `exp(mean_log*periods)-1`, factor según intervalo | La UI puede sobre/sub-anualizar y mezcla log/simple | Discrepancia detectada |
| Función objetivo | Riesgo positivo + penalización por distancia al target | `fitness_function.py`; prueba PSO-03/04 | Restricción exacta, otra escala o convención de riesgo | La comparabilidad numérica no demuestra adecuación de penalty | Confirmado; sensibilidad requiere PSO-06 |

## Comandos y resultados

### Ejecutados

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_pso04 -v` | **OK**, 6 pruebas pasadas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 22 pruebas pasadas; Streamlit emitió advertencias esperables de caché sin runtime interactivo |
| `./.venv/bin/python -m compileall -q src tests` | **OK** |
| `git diff --check` | **OK** |

### No ejecutados

- Yahoo Finance real, Streamlit interactivo y backtesting con datos históricos.
- Validación de una convención académica alternativa.
- Cambios de producción para resolver las discrepancias log/simple,
  anualización o frecuencia.

## Criterios de aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Fórmulas y tratamiento de retornos documentados | Cumplido | Inspección de `src/utils.py`, `src/finance.py`, `src/run_pso.py` y pruebas |
| VaR/CVaR, signos, cola y empates documentados | Cumplido | Inspección de fitness/métricas y casos manuales |
| Drawdown existente verificado sin añadir métrica | Cumplido | `max_drawdown`, fitness, charts y caso manual |
| Frecuencia y anualización documentadas | Cumplido | Controlador, UI, `annualized_return` y prueba |
| Relación con fitness documentada | Cumplido | Clases de fitness y caso penalizado |
| Tabla de decisiones entregada | Cumplido | Sección anterior |
| No modificar formulación ni producción | Cumplido | Solo `tests/test_pso04.py`, este reporte y roadmap |
| Pruebas ejecutadas y evidencia de resultados | Cumplido | 6 pruebas focalizadas y 22 pruebas completas pasadas; compilación y whitespace OK |
| Revisión independiente | Pendiente | Requerida por el protocolo |

## Limitaciones y siguiente paso

Los tests prueban las convenciones efectivas con datos sintéticos y un loader
mockeado; no prueban la calidad de Yahoo Finance, datos no positivos, zonas
horarias, precios faltantes dentro de la serie ni comparabilidad estadística
entre frecuencias. Las discrepancias log/simple, drawdown y anualización quedan
registradas para decisión académica posterior y no se corrigen unilateralmente.

La revisión independiente detectó inicialmente tres brechas de evidencia:
faltaban aserciones de VaR/CVaR en `calculate_portfolio_metrics`, no se
verificaban los argumentos enviados a `yfinance` y una referencia de líneas de
`app.py` era incorrecta. Se corrigieron en esta misma tarea; la suite focalizada
y la completa se ejecutaron nuevamente con éxito. La revisión independiente
formal sigue pendiente de aprobación posterior.

Siguiente paso: completar la revisión independiente de PSO-04.
