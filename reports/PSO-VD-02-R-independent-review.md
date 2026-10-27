# PSO-VD-02-R — Revisión independiente del diagnóstico de convergencia con datos reales

## 1. Veredicto

**Changes requested**

La implementación es funcional y las pruebas existentes pasan, pero la
evidencia documental y de pruebas no respalda completamente las afirmaciones
del informe PSO-VD-02. Hay una discrepancia material en la penalización
efectiva, los casos extremos solo se catalogan y no se ejecutan, y la interfaz
no muestra todos los parámetros PSO efectivos. No se modificó código durante
esta revisión.

## 2. Estado del repositorio

Estado inicial y final observado:

```text
## main...origin/main [ahead 5]
 M artifacts/experiments.psodata
 M validation_dashboard_logic.py
```

El cambio binario de `artifacts/experiments.psodata` es preexistente y se
conservó. `validation_dashboard_logic.py` contiene un cambio local de
`MARKET_PENALTY` de `500.0` a `50.0`; no fue realizado ni revertido durante
esta revisión. El informe se creó como el único archivo nuevo de esta revisión.
No se modificaron el roadmap, los protocolos, el optimizador, la aplicación
principal ni las funciones financieras. No se creó commit.

## 3. Archivos revisados

Se inspeccionaron:

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `docs/ai/WORK_PROTOCOL.md`
- `docs/ai/prompts/README.md`
- Reportes PSO-VD-01, PSO-VD-01.1-R, PSO-VD-01.2, PSO-VD-01.2-R y PSO-VD-02.
- `validation_dashboard.py`
- `validation_dashboard_logic.py`
- `tests/test_validation_dashboard.py`
- `src/pso/optimizer.py`
- `src/pso/velocity_model.py`
- `src/pso/fitness_function.py`
- `src/utils.py`
- `src/run_pso.py`
- `src/controllers/experiment_controller.py`
- `app.py`

## 4. Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 12 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 34 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `git diff --check` | **OK** |
| `git status --short --branch` | **OK** |

Las advertencias de Streamlit sobre ausencia de `ScriptRunContext` y
`use_container_width` fueron no bloqueantes. No se descargaron datos de Yahoo
Finance ni se ejecutó un experimento real de mercado durante la revisión.

También se ejecutó una comprobación independiente de CVaR con una matriz
pequeña:

```text
portfolio_mean = -0.011
risk = 0.052
target_gap = 0.016
penalty_component = 0.800
manual_total = 0.852
class_total = 0.852
```

La reconstrucción independiente coincide con `CVaR(alpha=0.95,
penalty=50.0)`. Esto verifica la fórmula actual, no la validez financiera
general de la convención.

## 5. Verificación de datos y ejecución

### Carga explícita y ausencia de ejecución al importar

`run_market_diagnostic()` llama a `load_crypto_returns` únicamente al ser
invocado por `_execute_market_diagnostic()`. La ruta inicial del dashboard no
ejecuta PSO ni descarga datos. La prueba de importación fresca reemplaza tanto
`src.pso.pso` como `src.utils.load_crypto_returns` por funciones que fallan;
importar ambos módulos pasa, por lo que no se detecta ejecución automática.

La prueba de mercado usa un cargador simulado y comprueba los activos, fechas,
intervalo, forma de matriz, timestamp proporcionado y seis combinaciones por
target. No prueba la red ni pretende demostrar una descarga real.

### Fechas y observaciones

El resultado conserva y muestra fechas disponibles mediante
`returns_index[0]`/`returns_index[-1]`, además de observaciones y activos. La
validación comprueba que el índice tenga la misma longitud que la matriz y que
las medias coincidan con el número de columnas.

El timestamp `retrieved_at` se genera después de retornar del cargador; no es
un timestamp emitido por Yahoo Finance ni una metadata de recuperación
proporcionada por el cargador. Es una marca local aproximada, no evidencia
independiente de la hora de descarga.

### Comparabilidad Ring/Global

Para cada target, el código reutiliza la misma matriz, target, parámetros y
semillas `42, 43, 44`; solo cambia la instancia de `RingTopology` por
`GlobalTopology`. El orden de ejecución y las semillas se verifican
parcialmente en `test_market_diagnostic_uses_mocked_loader_and_paired_runs`.
No se afirma superioridad de ninguna topología.

## 6. Hallazgos

### PSO-VD-02-R-01 — Penalización efectiva inconsistente con el informe

- **Severidad:** Media
- **Estado:** Abierto
- **Evidencia:** `validation_dashboard_logic.py:42` tiene
  `MARKET_PENALTY = 50.0`, y `_market_run()` usa ese valor al construir
  `CVaR`. La interfaz también muestra ese mismo valor en
  `validation_dashboard.py:78`. En cambio,
  `reports/PSO-VD-02-real-data-convergence.md:49` documenta `500.0`.
- **Impacto:** una ejecución reproducida siguiendo el informe no tendrá el
  mismo fitness, término de penalización ni posiblemente los mismos pesos y
  criterios de parada que la ejecución actual. Esto afecta la trazabilidad y
  puede producir conclusiones incompatibles.
- **Recomendación mínima:** decidir cuál es la configuración autorizada y
  alinear constante, interfaz, pruebas e informe; agregar una aserción que
  compruebe el valor efectivo.

### PSO-VD-02-R-02 — Los casos extremos no se ejecutan

- **Severidad:** Media
- **Estado:** Abierto
- **Evidencia:** `evaluate_extreme_cases()` solo devuelve una lista de nombres,
  clasificación y texto esperado (`validation_dashboard_logic.py:454-473`).
  `test_extreme_cases_have_explicit_expectations` solo comprueba que haya 12
  entradas, que la primera sea `invalid` y que la última sea
  `exact_repeat` (`tests/test_validation_dashboard.py:247-251`).
- **Impacto:** vector cero, pesos negativos, vértices, targets mínimo/máximo,
  target fuera de rango, retornos constantes y reproducibilidad no se
  someten a la implementación que supuestamente se diagnostica. La UI
  presenta el catálogo como “casos extremos sintéticos”, pero no como
  ejecuciones con resultados observados; aun así, el criterio de aceptación
  exigía verificar expectativas explícitas mediante pruebas.
- **Recomendación mínima:** implementar pruebas focalizadas para cada caso
  compatible con las APIs actuales, incluyendo factibilidad, rechazo o
  reparación esperada y reproducibilidad. Mantener los escenarios no
  ejecutables como limitaciones claramente etiquetadas.

### PSO-VD-02-R-03 — Parámetros PSO incompletos en la interfaz

- **Severidad:** Baja
- **Estado:** Abierto
- **Evidencia:** `validation_dashboard.py:70-81` muestra activos, fechas,
  observaciones, intervalo, timestamp, semillas, penalización y dos targets,
  pero no muestra `swarm_size`, `max_iterations`, `rtol`, `atol`, paciencia,
  `c1`, `c2` ni `inertia`, aunque están en `MARKET_PSO_SETTINGS` y el informe
  afirma que se muestran los parámetros PSO efectivos.
- **Impacto:** el usuario no puede reconstruir desde la interfaz toda la
  configuración de una ejecución; además, el límite de 1000 iteraciones queda
  especialmente fácil de omitir.
- **Recomendación mínima:** renderizar `results["settings"]` o una tabla
  explícita de parámetros, y probar que esos valores aparecen en el flujo de
  dashboard.

### PSO-VD-02-R-04 — Reparaciones contabilizadas, pero no descompuestas

- **Severidad:** Baja
- **Estado:** Observación documentada
- **Evidencia:** `optimizer.py` suma `velocity_model.last_repaired` por
  iteración. `_repair_position()` marca reparación cuando el vector cambia
  después de recortar y normalizar. Por ello una normalización de cualquier
  candidato cuya suma no sea exactamente uno cuenta igual que un recorte por
  componente negativo; un vector degenerado se sustituye uniformemente, pero
  no queda identificado por separado. No existe magnitud de corrección.
- **Impacto:** `repairs` es una cuenta real de posiciones modificadas por la
  rutina, pero no permite afirmar cuántas violaciones negativas, sumas
  distintas de uno o vectores cero ocurrieron, ni cuánto se corrigió cada
  partícula. La interfaz sí declara esta limitación y no presenta una
  magnitud inventada.
- **Recomendación mínima:** conservar el contador actual como “posiciones
  modificadas por reparación” y, en una tarea futura separada, instrumentar
  categorías y norma de corrección sin cambiar la estrategia.

## 7. Métricas y momento de medición

La instrumentación de `ConvergenceTrace` es coherente con el optimizador:

- `gbest` es el mejor valor global acumulado después de actualizar y evaluar
  la generación.
- `current_best`, `current_mean`, mediana y desviación son estadísticas de los
  fitness de la generación recién evaluada.
- `diversity` es la distancia euclídea media al centroide después del
  movimiento; `movement_mean/max` compara posiciones nuevas con las previas.
- `best_target_difference` usa el retorno medio del mejor `gbest` y el target.
- `repairs` cuenta posiciones modificadas, no velocidad reparada.
- `termination_reason` proviene del optimizador y distingue `patience` de
  `max_iterations`; no se infiere desde una gráfica.

La UI etiqueta las iteraciones como posteriores al movimiento. No mezcla una
fila inicial ficticia con las iteraciones observadas. La traza permite
examinar estancamiento, pérdida de diversidad, movimiento, brecha y
terminación, pero no demuestra que el resultado sea globalmente óptimo ni
separa causalmente reparación y estancamiento.

La concentración de pesos solo se resume en la mejor solución final mediante
`max_weight` y cantidad de pesos `>= 0.95`. No se mide una frecuencia por
iteración o por toda la población; por tanto, la conclusión permitida es
concentración final observada, no concentración persistente del enjambre.

## 8. Función de fitness y targets

El optimizador usa retornos logarítmicos por observación provenientes de
`load_crypto_returns`, y el retorno de cartera es `returns_matrix @ weights`.
Los targets mínimo e intermedio se calculan a partir de las medias por activo.
El target mínimo está dentro del rango por construcción; no se agregó una
ejecución real de target fuera de rango.

La descomposición implementada es compatible con la fórmula existente:

```text
fitness = CVaR(alpha, penalty=0) + penalty * abs(mean_return - target)
```

La comprobación numérica independiente produjo `0.052 + 50*0.016 = 0.852`,
igual al fitness de la clase. No se modificaron ni se revalidaron drawdown,
anualización u otras convenciones financieras.

## 9. Casos sintéticos y reproducibilidad

Los casos sintéticos PSO-VD-01 continúan pasando y cubren factibilidad,
Sphere, mínima varianza, CVaR manual y repetición. La prueba de mercado
comprueba que ambas topologías reciben el mismo esquema de semillas y que se
generan dos targets.

La cobertura, sin embargo, no verifica explícitamente para cada llamada que el
target, matriz, `swarm_size`, tolerancias y parámetros de velocidad sean
idénticos entre topologías. El código sí los obtiene de los mismos valores;
la prueba podría ser fortalecida para detectar una divergencia accidental.

## 10. Limitaciones experimentales

1. No se ejecutó descarga real contra Yahoo Finance ni se verificaron fechas o
   número de observaciones reales.
2. No se ejecutó el dashboard en navegador ni se probó el botón de mercado con
   `AppTest`; el helper y el cargador mockeado sí se probaron.
3. El informe PSO-VD-02 contiene referencias desactualizadas: documenta
   penalización `500.0` y afirma seis ejecuciones en una sección posterior a la
   ampliación a dos targets, que realmente produce doce.
4. La marca temporal es local y posterior a la llamada del cargador.
5. No se puede atribuir causalidad entre reparaciones, pérdida de diversidad y
   estancamiento con las métricas actuales.
6. No se demuestra optimalidad global, superioridad de Ring/Global ni validez
   financiera completa.

## 11. Confirmación de no modificación

Durante esta revisión no se modificaron el optimizador, las ecuaciones de
velocidad, la reparación, las topologías, la función de fitness, las fórmulas
financieras, `app.py`, el roadmap ni los protocolos. Solo se creó este informe.

## 12. Conclusión

La implementación respalda estas afirmaciones:

- la sección de mercado no descarga ni ejecuta PSO al importar;
- la descarga se inicia mediante una acción explícita;
- el cargador existente y la transformación de retornos se reutilizan;
- se ejecutan targets mínimo e intermedio con semillas compartidas para Ring y
  Global;
- las métricas de traza se presentan con el momento posterior al movimiento;
- la descomposición CVaR/penalización coincide con la función actual;
- los errores invalidan resultados de mercado anteriores.

No quedan respaldadas completamente la configuración documentada, la
verificación de todos los casos extremos ni la afirmación de que todos los
parámetros efectivos se muestran en la interfaz. Por esas razones, el veredicto
es **Changes requested**. Las correcciones recomendadas son acotar y alinear
la configuración efectiva, ejecutar o probar realmente los casos extremos y
mostrar los parámetros completos; ninguna requiere cambiar la matemática del
PSO.
