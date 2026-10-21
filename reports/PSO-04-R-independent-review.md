# PSO-04-R — Revisión independiente de convenciones financieras

## Identificación, estado inicial y alcance

- **ID revisado:** PSO-04 — Validación de convenciones de retornos y riesgo.
- **Revisión:** PSO-04-R, independiente y de solo lectura sobre producción y
  pruebas de implementación.
- **Fecha:** 2026-10-21.
- **Rama:** `main`, `ahead 2` respecto de `origin/main`.
- **Estado inicial:** árbol sucio por cambios previos de PSO-02/PSO-03 y PSO-04;
  no había cambios del revisor.
- **Cambios realizados en la revisión:** únicamente este reporte y la
  referencia de estado de PSO-04 en `docs/ai/ROADMAP.md`. No se modificaron
  producción, pruebas de implementación ni reportes existentes. No se creó
  commit.

El alcance incluyó el flujo `Close` → retornos → frontera/fitness → métricas →
interfaz, VaR/CVaR, drawdown, anualización, frecuencia, pruebas manuales y
reproducibilidad de las afirmaciones del reporte de implementación. Se
excluyeron cambios de formulación, decisiones académicas no aprobadas,
descargas reales de Yahoo Finance, ejecución interactiva de Streamlit y
backtesting de mercado.

## Archivos y funciones inspeccionados

- `src/utils.py`: `load_crypto_returns`.
- `src/run_pso.py`: `PSOInputData`, `run_pso`.
- `src/pso/fitness_function.py`: `CVaR`, `VaR`, `MaxDrawdown`.
- `src/finance.py`: `max_drawdown`, `calculate_portfolio_metrics`,
  `annualized_return` y constructores de tablas.
- `src/controllers/experiment_controller.py`: propagación de `interval`,
  configuración de objetivos y construcción de métricas.
- `src/ui/tabs/analysis.py`: etiquetas y llamada a `annualized_return`.
- `src/ui/charts.py`: curvas acumuladas del análisis y backtesting.
- `app.py`: opciones de frecuencia, alpha y etiquetas de riesgo.
- `tests/test_pso04.py`, `tests/test_pso03.py`.
- `reports/PSO-04-financial-conventions.md` y documentación de protocolo.

## Comandos ejecutados y resultados observados

| Comando | Resultado |
|---|---|
| `git status --short --branch` | `main...origin/main [ahead 2]`; cambios previos conservados, sin cambios del revisor al inicio |
| `./.venv/bin/python -m unittest tests.test_pso04 -v` | **OK**, 6 pruebas pasadas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 22 pruebas pasadas; solo advertencias esperables de Streamlit sin runtime |
| `./.venv/bin/python -m compileall -q src tests` | **OK** |
| `git diff --check` | **OK** |
| Recalculo independiente con NumPy | **OK**, sin llamar a las funciones bajo revisión para formar expectativas |

No se ejecutaron Yahoo Finance real, Streamlit interactivo ni backtesting con
datos de mercado. Por tanto, este reporte no afirma haber validado esas
superficies.

## Verificación técnica y matemática

### Retornos, frecuencia y objetivos

`src/utils.py:12-14` descarga `["Close"]` y transmite `assets`, `start`, `end`,
`interval` y `progress=False` a `yfinance`. `src/utils.py:19` calcula
`log(close_t / close_{t-1})` y `dropna()` elimina la primera observación y
cualquier fila que conserve un faltante. `src/utils.py:24-27` conserva una
observación por fila, forma una matriz `T x N` y calcula `mean_return` como la
media aritmética por columna.

`src/controllers/experiment_controller.py:181-188` transmite la frecuencia al
loader tanto para la muestra de optimización como para el período de
backtesting (`:233-239`). No se observa conversión de `1wk` o `1mo` a datos
diarios ni annualización antes de formar las medias. La interfaz ofrece
`1d`, `1wk` y `1mo` en `app.py:55-56`.

`src/run_pso.py:58-61` construye targets entre el mínimo y máximo de esas
medias logarítmicas. `src/pso/fitness_function.py:24` y
`src/finance.py:20` forman el retorno por observación como
`returns_matrix @ weights`; la media y el target sí comparten la unidad de
retorno logarítmico por observación. No se calcula ahí el retorno simple
`sum(w_i (exp(r_i)-1))`.

El caso manual de `tests/test_pso04.py:28-47` es correcto. Para
`r=(log(1.1), log(0.9))` y `w=(0.25,0.75)`, el recálculo independiente da:

| Magnitud | Valor |
|---|---:|
| retorno log ponderado | `-0.05519284179228848` |
| retorno simple reequilibrado `0.25(0.1)+0.75(-0.1)` | `-0.05` |
| `exp(retorno log ponderado)-1` | `-0.05369735634102868` |

Por tanto, el reporte distingue correctamente suma ponderada de log-retornos,
retorno simple de activos y retorno simple de cartera. La precisión necesaria
es que `R w` es una trayectoria sintética definida por el código; por sí sola
no identifica una estrategia autofinanciada concreta.

### VaR y CVaR

`src/pso/fitness_function.py:24-35` y `:57-68`, y
`src/finance.py:25-30`, usan el cuantil inferior
`100(1-alpha)` de los retornos, con la interpolación predeterminada de
`numpy.percentile`. `alpha` funciona como confianza nominal. La cola se
selecciona con `<=`, de modo que todos los empates en el umbral entran en
CVaR. VaR es `-threshold`; CVaR es `-mean(tail)`. La función objetivo suma
esa magnitud de riesgo positiva a
`penalty * abs(mean_return - target)`.

El recálculo independiente del caso `[-0.2,-0.1,-0.1,0.2]`, `alpha=0.5`, da:

- percentil 50: `-0.1`;
- cola `<=`: `[-0.2,-0.1,-0.1]`, tamaño 3 en lugar de exactamente 2;
- VaR: `0.1`;
- CVaR de pérdida: `0.13333333333333333`.

Esto coincide con `tests/test_pso04.py:50-72`, incluidas las aserciones
añadidas a `calculate_portfolio_metrics`. La interpolación y el tamaño
efectivo de la cola dependen de la muestra; no se implementa una convención
discreta alternativa. Esa diferencia es convencional y está correctamente
separada de un defecto de código.

La interfaz construye las etiquetas `CVaR {alpha*100:.0f}%` y selecciona las
columnas `cvar`, `var` y `max_drawdown` en `app.py:32-44`. La etiqueta es
coherente con el alpha recibido, aunque “CVaR” continúa significando aquí una
pérdida positiva derivada de retornos, no el retorno medio de cola sin negar.
El reporte de implementación lo documenta y no presenta una convención
académica alternativa como si ya estuviera aprobada.

### Drawdown: discrepancia confirmada y modelo de inversión

`src/finance.py:9-13`, `src/pso/fitness_function.py:118-123` y
`src/ui/charts.py:382-383,440-441` usan:

```text
wealth_t = prod(1 + portfolio_return_t)
drawdown_t = (wealth_t - running_max_t) / running_max_t
MDD = -min(drawdown_t)
```

La implementación trata su entrada como retorno simple. Sin embargo, la
entrada de producción se origina como log-retorno en `src/utils.py:19` y se
combina mediante `R w` antes de llegar a estas funciones. La discrepancia
descrita en el reporte es, por tanto, real.

El recálculo independiente muestra la diferencia. Para retornos simples
`[0.1,-0.2,0.1]`, la riqueza correcta por productos es
`[1.1,0.88,0.968]` y el MDD es `0.2`, que coincide con el test existente.
Si se reconstruye riqueza desde log-retornos, la forma correcta es
`exp(cumsum(log_returns))`. Aplicar erróneamente `cumprod(1+log_returns)` al
vector equivalente produce aproximadamente
`[1.09531018,0.85089878,0.93199809]` y MDD `0.2231435513`, no `0.2`.

Hay además una precisión conceptual que el reporte debe mantener explícita:
reutilizar los mismos pesos en `returns_matrix @ weights` no prueba “pesos
fijos sin rebalanceo”. Para un modelo buy-and-hold, las ponderaciones de
mercado evolucionan con los precios; para un modelo de pesos constantes
reequilibrado, hay que definir el retorno simple por período y la frecuencia
de reequilibrio. La suma ponderada de log-retornos tampoco equivale
automáticamente a cualquiera de esas dos riquezas. El reporte sí advierte que
no hay una trayectoria buy-and-hold exacta, pero su frase sobre “pesos fijos”
y “no hay rebalanceo” mezcla una parametrización repetida del cálculo con una
estrategia financiera no definida.

Este punto es una discrepancia de interpretación de severidad **media**:
la implementación no se cambia en PSO-04, pero MDD no debe presentarse como
máximo drawdown financiero de una cartera real hasta fijar la trayectoria de
riqueza y la política de rebalanceo.

### Anualización y frecuencia

`src/finance.py:194-195` implementa
`(1 + input) ** periods_per_year - 1`, con default `252`. En
`src/ui/tabs/analysis.py:198-204`, `df_metrics["mean_return"]` se pasa
directamente a esa función, se etiqueta como “Daily return” y se muestra como
“Annualized return”. No se transmite `payload.interval` ni se transforma la
media logarítmica mediante una exponencial.

La afirmación del reporte es reproducible: para entrada `0.01`,
`periods_per_year=2` devuelve `0.0201`, y el default devuelve
`1.01**252 - 1 = 11.274002099240244`. Si la entrada representa una media
logarítmica de `0.01`, una anualización logarítmica alternativa daría
`exp(0.01*252)-1 = 11.428596663577544`; no es la fórmula vigente. Para `1wk`
o `1mo`, mantener 252 observaciones por año no corresponde a la frecuencia
seleccionada. Esta es una discrepancia verificable de unidades/etiquetado,
correctamente reconocida por el reporte y pendiente de decisión académica.

No se debe interpretar la etiqueta como evidencia de que el flujo haya
convertido datos semanales o mensuales a diarios. Tampoco se observó
annualización de volatilidad.

## Correcciones declaradas por el implementador

Las tres correcciones indicadas en `reports/PSO-04-financial-conventions.md`
son verificables:

1. `calculate_portfolio_metrics` ahora tiene aserciones independientes de
   `cvar` y `var` en `tests/test_pso04.py:62-67`.
2. La llamada a `yfinance` y sus argumentos exactos se verifican mediante
   `download.assert_called_once_with(...)` en `tests/test_pso04.py:20-25`.
3. Las referencias a `app.py:32-44` son coherentes con las líneas actuales:
   `_risk_axes` etiqueta CVaR/VaR y selecciona sus columnas.

No se verificaron ejecuciones interactivas, descargas reales ni backtesting,
porque no fueron ejecutados ni se presentan como resultados ejecutados.

## Hallazgos priorizados

| # | Severidad | Evidencia | Hallazgo y consecuencia |
|---|---|---|---|
| 1 | **Media** | `src/utils.py:19`, `src/finance.py:9-13`, `src/pso/fitness_function.py:118-123` | El drawdown consume log-retornos como si fueran simples. El reporte detecta la discrepancia, pero sus pruebas solo cubren el caso simple y no demuestran numéricamente el desvío en la entrada de producción. MDD y curvas acumuladas no son financieramente interpretables sin definir riqueza y estrategia. |
| 2 | **Media** | `src/ui/tabs/analysis.py:198-204`, `src/finance.py:194-195`, `app.py:55-56` | La UI etiqueta media logarítmica por observación como diaria y aplica 252 también para `1wk`/`1mo`. El reporte lo identifica correctamente; queda una incompatibilidad de unidades que impide leer ese resultado como anualización validada. |
| 3 | **Baja** | `tests/test_pso04.py:14-25,74-103` | La cobertura es adecuada para las fórmulas declaradas, pero no prueba explícitamente `1wk`/`1mo`, faltantes, precios no positivos ni el caso de drawdown aplicado a log-retornos. Son limitaciones declaradas, no fallos ocultos ni motivo independiente para cambiar producción. |
| 4 | **Baja** | `src/finance.py:20`, `src/ui/charts.py:382-383,440-441` | La reutilización de `R w` como “portfolio return” deja ambigua la estrategia económica: no es suficiente llamarla buy-and-hold ni “sin rebalanceo”. Debe mantenerse como convención sintética hasta que PSO-05/una decisión académica fije la política. |

No encontré un defecto reproducible en el cálculo vigente de percentil,
empates, signos de VaR/CVaR, propagación de `interval`, generación de targets
o argumentos de `yfinance`. Las diferencias restantes son convenciones o
limitaciones que el reporte de implementación distingue en términos generales.

## Criterios de aceptación de PSO-04

| Criterio | Veredicto independiente | Evidencia |
|---|---|---|
| Fórmulas y tratamiento de retornos documentados | Cumplido con observación | `src/utils.py`, `src/run_pso.py`, `tests/test_pso04.py` |
| VaR/CVaR, alpha, cola, empates y signos | Cumplido | `src/pso/fitness_function.py`, `src/finance.py`, pruebas manuales |
| Drawdown existente verificado sin modificar producción | Cumplido con observación media | Flujo real confirmado; falta un test de contraste log/simple |
| Frecuencia y anualización documentadas | Cumplido con observación media | `src/controllers/experiment_controller.py`, `src/ui/tabs/analysis.py`, `src/finance.py` |
| Relación entre riesgo, target y penalización | Cumplido | `CVaR.evaluate`, caso `7.65` y unidades por observación |
| Pruebas con expectativas independientes | Cumplido para los casos cubiertos | Expectativas numéricas calculadas en el test o por recálculo externo |
| Correcciones declaradas de VaR/CVaR, yfinance y app.py | Verificado | Aserciones y referencias actuales confirmadas |
| No modificar producción, pruebas ni parámetros | Cumplido por esta revisión | Solo reporte independiente y estado del roadmap |
| Suficiente para afirmar una convención financiera académica final | No cumplido | Drawdown, estrategia de cartera y anualización por frecuencia siguen requiriendo decisión |

## Veredicto final

**Aprobado con observaciones.**

PSO-04 está suficientemente sustentado como auditoría de las convenciones
efectivamente implementadas y puede marcarse como revisión independiente
realizada. Las pruebas pasan y las correcciones declaradas son reproducibles.
No obstante, no debe cerrarse la interpretación académica como si ya existiera
un Maximum Drawdown de cartera o una anualización correcta para todas las
frecuencias: el código actual calcula trayectorias basadas en log-retornos
combinados y luego las trata como simples, y la UI aplica 252 a una magnitud
que no está restringida a datos diarios.

Recomendaciones acotadas, sin cambios de producción en esta revisión:

1. En la siguiente tarea financiera, fijar explícitamente si la trayectoria es
   una serie sintética de `R w`, una cartera reequilibrada o buy-and-hold antes
   de interpretar MDD y rendimiento acumulado.
2. Añadir un caso de evidencia que compare `cumprod(1+r_log)` con
   `exp(cumsum(r_log))`, sin cambiar todavía la implementación.
3. Mantener separadas las decisiones de anualización de retornos logarítmicos,
   retornos simples y frecuencia `1d`/`1wk`/`1mo`.

PSO-04 no autoriza por sí sola una corrección de las fórmulas. PSO-05 puede
revisar los supuestos del backtesting y la estrategia; PSO-06 puede estudiar
la sensibilidad de la penalización, sin tratar este veredicto como aprobación
de una convención financiera alternativa.
