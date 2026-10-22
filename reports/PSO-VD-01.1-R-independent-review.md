# PSO-VD-01.1-R — Revisión independiente del cierre de observaciones

## Veredicto general

**Aprobado con observaciones.**

PSO-VD-01.1 mejora de forma material la justicia experimental de la
comparación Ring/Global y corrige la debilidad de la prueba de importación:
ahora existen tres pares con semillas comunes y la importación se comprueba en
un subproceso limpio. La suite también prueba el flujo principal de Streamlit,
la repetición, la ausencia de artefactos en un directorio temporal y la
ejecución sin dependencia de los puntos de acceso de red comprobados.

No obstante, el cierre no es completo. Si una ejecución iniciada desde
`Ejecutar validación` o `Repetir validación` lanza una excepción, el código no
limpia `st.session_state["validation_results"]`; una ejecución posterior
fallida puede dejar visibles resultados de una ejecución anterior como si
fueran actuales. Las pruebas no ejercitan esta ruta. Por ello VD-R-04 queda
**parcialmente resuelto** y se registra un nuevo hallazgo de severidad media.
El dashboard sí es utilizable como herramienta explicativa de validación
sintética, siempre que no se presente como prueba de superioridad de
topologías, convergencia global o validez financiera.

## Identificación, estado y alcance

- **ID revisado:** PSO-VD-01.1-R
- **Fecha:** 2026-10-21
- **Rama:** `main`
- **Estado inicial:** `main...origin/main [ahead 3]`
- **Objetivo:** determinar independientemente si PSO-VD-01.1 resolvió
  `VD-R-01` a `VD-R-04` y preservó la validez del dashboard sintético.
- **Alcance incluido:** revisión de código, pruebas, reportes, regresiones
  matemáticas focalizadas, aislamiento de red/persistencia, importación fresca,
  ejecución de Streamlit y estado del repositorio.
- **Alcance excluido:** cambios de código, correcciones, actualización del
  roadmap, commits, navegador interactivo completo, datos de mercado,
  backtesting y lectura/escritura de `.psodata`.

El archivo `reports/PSO-VD-01-implementation.md` solicitado como reporte
anterior no existe en el estado inspeccionado. Se contrastó el informe
disponible `reports/PSO-VD-01-validation-dashboard.md`, el cierre
`reports/PSO-VD-01.1-closeout.md`, el informe original
`reports/PSO-VD-01-R-independent-review.md` y el código actual. La ausencia del
reporte de implementación se considera una limitación de trazabilidad, no se
rellenó con suposiciones.

## Estado inicial y final del repositorio

### Estado inicial

El árbol ya estaba modificado antes de esta revisión:

```text
## main...origin/main [ahead 3]
 M docs/ai/ROADMAP.md
?? reports/PSO-VD-01-R-independent-review.md
?? reports/PSO-VD-01-validation-dashboard.md
?? reports/PSO-VD-01.1-closeout.md
?? tests/test_validation_dashboard.py
?? validation_dashboard.py
?? validation_dashboard_logic.py
```

El único cambio rastreado era la adición preexistente de la sección PSO-VD-01
en `docs/ai/ROADMAP.md`. Los archivos del dashboard, sus pruebas y reportes
estaban sin seguimiento y se conservaron. El informe anterior no fue editado.

### Estado final

El estado final conserva los mismos cambios preexistentes y añade únicamente
este informe solicitado como archivo sin seguimiento. No se modificaron
`validation_dashboard.py`, `validation_dashboard_logic.py`, las pruebas,
`src/`, `app.py` ni `docs/ai/ROADMAP.md`. No se creó ningún commit.

## Metodología y comandos ejecutados

Se inspeccionaron las instrucciones de `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`, `docs/ai/WORK_PROTOCOL.md` y `reports/README.md`, además
de los reportes relacionados. Se contrastaron las afirmaciones del cierre con
las líneas actuales de lógica, UI y pruebas. Los comandos ejecutados fueron:

| Comando | Resultado |
|---|---|
| `git status --short --branch` | **OK**, estado inicial y final documentados |
| `git diff --stat`, `git diff --name-status` | **OK**, distinguió el diff rastreado preexistente de archivos sin seguimiento |
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 7/7 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 29/29 pruebas |
| `./.venv/bin/python -m unittest tests.test_pso03 tests.test_pso04 -v` | **OK**, 10/10 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `./.venv/bin/python -c 'import validation_dashboard; import validation_dashboard_logic; print("imports-ok")'` | **OK**, sin ejecución de la suite |
| `git diff --check` | **OK** para el diff rastreado |
| `./.venv/bin/streamlit run validation_dashboard.py --server.headless true --server.port 8502` | **OK**, servidor inició |
| `curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8502/` | **OK**, respondió HTML HTTP; proceso detenido al terminar |
| Sondeo `rg` de red y persistencia en los archivos del dashboard | **OK**, no aparecen descargas, `yfinance`, `.psodata` ni escrituras |
| Inspección AST/control de flujo del manejo de errores | **OK**, confirmó que no hay limpieza antes de una excepción |

Las pruebas de Streamlit emitieron advertencias de ejecución sin
`ScriptRunContext` y deprecación futura de `use_container_width`; no fueron
fallos. No se accedió a Internet ni se descargaron datos de mercado.

## Resultados reproducibles

### VD-R-01 — Comparación Ring/Global

**Estado: resuelto para el alcance declarado, con una limitación estadística
correctamente mantenida.**

`validation_dashboard_logic.py:189-200` itera sobre
`CONVERGENCE_SEEDS = (101, 102, 103)` y ejecuta, para cada semilla, Ring y
Global con la misma matriz sintética `sphere_returns`, tamaño de enjambre,
modelo Inertia, parámetros, tolerancias, paciencia y límite de iteraciones.
Solo se sustituye la topología (`RingTopology()` frente a
`GlobalTopology()`). Cada resultado conserva su propia semilla, traza, fitness,
diversidad, movimiento, reparaciones y motivo de terminación en
`convergence["runs"]`.

La prueba `test_convergence_uses_paired_seeds_and_fixed_configuration`
(`tests/test_validation_dashboard.py:71-81`) comprueba las semillas comunes,
el número de réplicas y la configuración devuelta. La UI traza cada corrida
real con nombre de topología y semilla (`validation_dashboard.py:16-30`) y
explica que el emparejamiento mejora el control experimental pero no prueba
superioridad general (`validation_dashboard.py:159-162`). No hay ganador
declarado ni resumen estadístico ficticio. Se informa explícitamente el número
de semillas `101–103` (`validation_dashboard.py:64-68`).

Esto hace la comparación más justa y permite comparar diferencias dentro de
cada par. Tres pares no constituyen una prueba de superioridad estadística
general; esa limitación está correctamente declarada y no se mantiene como
defecto separado.

### VD-R-02 — Importación fresca

**Estado: resuelto.**

La prueba `test_fresh_import_does_not_execute_pso`
(`tests/test_validation_dashboard.py:16-38`) ejecuta un nuevo intérprete con
`subprocess.run(..., check=True)`, fija `PYTHONPATH`, importa `src.pso`,
reemplaza `src.pso.pso` por una función que falla y después importa
`validation_dashboard_logic`. Comprueba además la salida `fresh import ok`.
Un error o código de salida distinto de cero hace fallar la prueba; no depende
de un módulo cacheado en el proceso de unittest.

La importación de `validation_dashboard_logic.py:12` solo enlaza el símbolo
`pso`; la ejecución ocurre dentro de `run_validation_suite()`, no durante la
importación. `validation_dashboard.py:196-197` protege `main()` con
`if __name__ == "__main__"`. La prueba detectaría una ejecución de PSO durante
la importación porque el símbolo parcheado lanzaría `AssertionError`.

La prueba no detecta toda posible actividad ajena a `pso` durante la
importación, pero sí cubre la regresión concreta indicada por VD-R-02 y las
superficies de importación relevantes.

### VD-R-03 — Persistencia y acceso a red

**Estado: resuelto proporcionalmente a la garantía declarada.**

`run_validation_suite()` declara y cumple un resultado en memoria
(`validation_dashboard_logic.py:104-105`). La prueba
`test_suite_has_no_repository_persistence_or_network_requirement`
(`tests/test_validation_dashboard.py:52-69`) ejecuta desde un directorio
temporal, cambia `HOME`, compara el directorio antes/después y hace fallar
las llamadas a `socket.create_connection` y `urllib.request.urlopen`.
El sondeo estático no encontró `yfinance`, `requests`, `httpx`, lectura de
`artifacts/experiments.psodata` ni métodos de escritura en los archivos del
dashboard. La suite completa también pasó sin red.

La evidencia distingue tres afirmaciones que no deben confundirse:

1. **No depender de la red:** demostrado para la ejecución probada; las
   pruebas corren sin conexión y el código no importa un cliente de mercado.
2. **Comprobar que no se intenta acceder a la red:** parcialmente demostrado
   mediante los dos puntos bloqueados y la inspección estática.
3. **Bloquear todo acceso de red:** no demostrado ni pretendido por la prueba;
   llamadas directas a otros APIs de socket o clientes no parcheados no quedan
   cubiertas.

El informe de cierre declara expresamente esta limitación. No constituye un
defecto adicional mientras el dashboard mantenga su código actual y no se
afirme una garantía global de sandbox.

### VD-R-04 — Interfaz Streamlit

**Estado: parcialmente resuelto.**

Las pruebas `AppTest` ejercitan el flujo principal:

- estado inicial sin `validation_results` y mensaje pendiente
  (`tests/test_validation_dashboard.py:83-90`);
- ejecución solo después del botón y almacenamiento en
  `st.session_state` (`:90-96`);
- repetición que reemplaza el objeto de resultados (`:98-109`);
- diagnóstico con longitudes y valores finitos, evitando ceros ficticios
  (`:111-121`).

La aplicación conserva y recupera resultados desde sesión
(`validation_dashboard.py:70-82`), muestra datos de las ejecuciones reales y
no ejecuta PSO al cargar. El smoke test HTTP solo confirma que Streamlit
inicia y responde; no se considera prueba interactiva completa del navegador.
No se ejecutó inspección visual manual, tal como reconoce el cierre.

Se mantiene una brecha funcional importante: la asignación de resultados
ocurre solo después de que `run_validation_suite()` retorna
(`validation_dashboard.py:72-75` y `:80-83`). Si esa llamada lanza una
excepción después de que ya existe un resultado anterior, el flujo se
interrumpe antes de reemplazarlo o limpiarlo; el valor antiguo permanece en
`st.session_state` y en un rerun puede seguir siendo renderizado por
`results = st.session_state.validation_results` (`:76-86`). La revisión
confirmó esta ruta mediante inspección de control de flujo; no existe una
prueba que la fuerce.

### E — Regresiones y validez del dashboard

**Resultado: sin regresión demostrada en el alcance ejecutado.**

- `tests.test_pso03`: 10/10 pruebas pasaron; se preservan Sphere, la
  referencia independiente de mínima varianza y los casos sintéticos de
  validación matemática cubiertos por esa suite.
- `tests.test_pso04`: incluido en las 10/10; se preservan las convenciones
  manuales de VaR/CVaR verificadas por el proyecto.
- La implementación sigue usando Sphere con óptimo uniforme
  (`validation_dashboard_logic.py:37-41`), la matriz de covarianza fija y la
  enumeración independiente de soportes (`:90-101`), y el caso manual CVaR
  (`:179-187`).
- La reproducibilidad sigue usando generadores locales por semilla
  (`:67-84`); la suite comprueba igualdad de fitness, pesos y traza para
  semilla 777 (`:226-250`).
- La traza de convergencia usa diagnósticos reales del optimizador y la UI
  etiqueta la abscisa como posterior al movimiento
  (`validation_dashboard.py:35`, `:159-162`).
- El dashboard se identifica como sintético y niega explícitamente descargas,
  carga de `.psodata`, superioridad financiera y validación de backtesting
  (`validation_dashboard.py:45-53`).
- No se modificaron el optimizador, las topologías, las funciones financieras,
  `app.py` ni la aplicación principal.

Estas comprobaciones no prueban convergencia global, optimalidad global de
CVaR penalizado ni validez financiera; el dashboard no afirma esas
propiedades.

## Estado de hallazgos originales

| ID | Severidad original | Estado actual | Evidencia y conclusión |
|---|---|---|---|
| VD-R-01 | Media | **Resuelto** | Tres pares Ring/Global con semillas 101, 102 y 103; misma matriz y configuración por par; resultados conservados por semilla; limitación de superioridad general explícita. |
| VD-R-02 | Baja | **Resuelto** | Subproceso limpio, `check=True`, salida inspeccionada y PSO parcheado antes de importar la lógica. |
| VD-R-03 | Baja | **Resuelto proporcionalmente** | Directorio temporal sin artefactos, suite sin red y dos puntos de acceso bloqueados; no se afirma bloqueo global de toda red posible. |
| VD-R-04 | Baja | **Parcialmente resuelto** | `AppTest` cubre estado inicial, ejecución explícita y reemplazo; falta la ruta de error y existe riesgo demostrado de conservar resultados obsoletos. |

## Nuevos hallazgos

### VD-NEW-01 — Resultados obsoletos tras error de ejecución

- **Severidad:** **Media**
- **Estado:** abierto
- **Evidencia:** `validation_dashboard.py:72-75` y `:80-83` asignan el nuevo
  resultado solo si `run_validation_suite()` termina correctamente. Si la
  llamada falla con una excepción y ya había un valor en
  `st.session_state["validation_results"]`, no hay limpieza, marcador de
  invalidez ni mensaje que impida que el rerun siguiente vuelva a presentar el
  objeto anterior (`:76-86`).
- **Impacto:** una falla real de una repetición puede quedar ocultada por
  resultados de una ejecución anterior. Esto compromete la coherencia entre el
  estado de la interfaz y la ejecución que el usuario acaba de solicitar.
- **Recomendación:** hacer explícita la transición de estado antes de ejecutar
  o marcar el resultado anterior como inválido, manejar el error con el patrón
  de notificación usado por el proyecto y añadir una prueba `AppTest` que
  inyecte una excepción en una ejecución posterior y compruebe que no se
  muestran resultados antiguos como actuales.

No se identificaron hallazgos críticos o altos. La falta del reporte
`PSO-VD-01-implementation.md` es una limitación documental de trazabilidad, no
un defecto funcional demostrado.

## Limitaciones y comprobaciones no ejecutadas

1. No se ejecutó interacción de navegador ni revisión visual manual; el smoke
   test HTTP no equivale a una prueba de navegador.
2. No se bloqueó exhaustivamente toda API de red posible; se comprobó la
   ejecución sin red y se bloquearon `socket.create_connection` y
   `urllib.request.urlopen`.
3. No se evaluaron datos reales, Yahoo Finance, backtesting, costos,
   rebalanceo ni persistencia `.psodata`.
4. No se demostró superioridad estadística entre Ring y Global: hay tres pares
   emparejados, no un estudio estadístico amplio.
5. `git diff --check` cubrió el diff rastreado; los archivos nuevos no estaban
   incluidos en el diff de Git al inicio. La sintaxis de todos los archivos
   Python relevantes sí se comprobó con `py_compile`.
6. Falta el reporte histórico con nombre
   `reports/PSO-VD-01-implementation.md`; el cierre disponible fue evaluado
   directamente contra el código y las pruebas.

## Criterios de aceptación de esta revisión

| Criterio | Estado | Evidencia |
|---|---|---|
| Revisar estado inicial, diffs y preservar cambios previos | Cumplido | `git status`, diff de roadmap y estado final |
| Contrastar cierre con código y pruebas | Cumplido | Inspección de lógica, UI, tests y reportes |
| Verificar comparación emparejada Ring/Global | Cumplido con observación | 3 semillas comunes; no se afirma superioridad general |
| Verificar importación fresca | Cumplido | Subproceso limpio 7/7 |
| Verificar persistencia y red | Cumplido proporcionalmente | Prueba temporal, hooks de red e inspección estática |
| Verificar interfaz Streamlit | Parcial | `AppTest` y smoke HTTP; falta ruta de error y navegador |
| Comprobar regresiones matemáticas y financieras focalizadas | Cumplido | PSO-03/PSO-04, 10/10 |
| Ejecutar suite específica y completa | Cumplido | 7/7 y 29/29 |
| Ejecutar sintaxis, `git diff --check` e inspección final | Cumplido | Comandos registrados |
| No modificar código ni crear commit | Cumplido | Solo se creó este informe |

## Conclusión

La comparación Ring/Global ahora es experimentalmente más justa: cada par usa
la misma semilla, matriz, función objetivo y configuración, y conserva sus
resultados reales. Esa mejora permite una comparación descriptiva emparejada,
pero no autoriza afirmar superioridad general ni convergencia global.

Las pruebas de importación fresca detectan la regresión que pretenden
prevenir. Las pruebas de aislamiento demuestran que la suite funciona sin
red, sin artefactos locales y sin depender de `.psodata`, pero no son un
bloqueo universal de red. Las pruebas `AppTest` cubren el flujo normal de
estado y repetición, aunque no detectan el caso importante de error con
resultados antiguos.

Las correcciones preservaron los casos matemáticos sintéticos y las
convenciones focalizadas de VaR/CVaR; la suite completa y las pruebas de
PSO-03/PSO-04 pasaron. En consecuencia, **el dashboard puede utilizarse ante
los asesores como herramienta explicativa de validación sintética**, con la
condición de presentar claramente sus límites. Antes de considerarlo cerrado
como evidencia de interfaz, debe resolverse `VD-NEW-01` y añadirse su prueba
de regresión. No se modificó código, no se actualizó el roadmap y no se creó
un commit durante esta revisión.
