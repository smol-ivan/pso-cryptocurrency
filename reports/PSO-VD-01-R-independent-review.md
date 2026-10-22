# PSO-VD-01-R — Revisión independiente del dashboard de validación

## Veredicto

**Aprobado con observaciones.**

El dashboard ejecuta casos sintéticos reproducibles, aislados de la interfaz
principal, sin descargas ni persistencia accidental. Los cálculos revisados
coinciden con las fórmulas y convenciones actualmente implementadas en
producción. No obstante, la comparación Ring/Global no es un experimento
controlado porque usa semillas diferentes, y la suite del dashboard no prueba
de forma suficiente la interfaz Streamlit ni el aislamiento de importación en
un proceso limpio. Por tanto, es apto como herramienta explicativa de
propiedades sintéticas concretas, pero no como evidencia de superioridad entre
topologías ni como validación financiera.

## Identificación, estado inicial y alcance

- **ID revisado:** PSO-VD-01-R
- **Fecha:** 2026-10-21
- **Rama:** `main`
- **Estado inicial:** `main...origin/main [ahead 3]`
- **Cambios preexistentes conservados:** `docs/ai/ROADMAP.md` modificado y
  `validation_dashboard.py`, `validation_dashboard_logic.py`,
  `tests/test_validation_dashboard.py` y
  `reports/PSO-VD-01-validation-dashboard.md` sin seguimiento.
- **Objetivo:** revisar de forma independiente la corrección, reproducibilidad,
  aislamiento y explicabilidad del dashboard PSO-VD-01.

Se incluyó la revisión estática y dinámica de los cuatro archivos del
dashboard, las pruebas relacionadas, el optimizador, los modelos de velocidad,
las topologías, las funciones de riesgo, el controlador de producción y la
interfaz principal. Se excluyeron cambios de código, correcciones, descargas
de mercado, experimentos con Yahoo Finance, lectura o escritura de
`.psodata`, commits y actualizaciones del roadmap. No se alteraron el
optimizador, la interfaz principal, las funciones financieras, las pruebas
existentes ni el roadmap.

## Metodología y comandos

Se contrastaron las afirmaciones del reporte `PSO-VD-01-validation-dashboard.md`
con el código fuente y las pruebas. También se recalcularon la referencia de
mínima varianza, los autovalores de la covarianza y los casos manuales de
VaR/CVaR. Los comandos ejecutados fueron:

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 4 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 26 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| Importación de `validation_dashboard` y `validation_dashboard_logic` | **OK** |
| Importación fresca con `sys.modules` limpiado y PSO/ suite bloqueados | **OK**, no hubo ejecución durante la importación |
| `git diff --check` | **OK** |
| `streamlit run validation_dashboard.py --server.headless true --server.port 8502` y `curl http://127.0.0.1:8502/` | **OK**, servidor inició y respondió HTTP |
| Recomputación independiente de referencia, autovalores y VaR/CVaR | **OK** |
| `git status --short --branch` y diff de archivos de producción | Sin cambios nuevos durante la revisión |

La suite completa emitió advertencias normales de Streamlit por ejecutarse sin
runtime interactivo y usar almacenamiento de caché en memoria. No se accedió a
Internet ni se descargaron datos.

## Resultados reproducibles

### Integridad y aislamiento

- `app.py` y los módulos de producción no aparecen en el diff de la tarea; el
  diff observado del roadmap fue preexistente.
- `validation_dashboard_logic.py` solo importa `pso` y lo invoca dentro de
  `run_validation_suite()` (líneas 103-104); no ejecuta pruebas al importar.
- `validation_dashboard.py` protege `main()` con `if __name__ == "__main__"`
  (líneas 196-197). La ejecución se dispara únicamente mediante el botón
  (líneas 68-80).
- Los resultados se guardan en `st.session_state` y la repetición sobrescribe
  explícitamente ese valor; no se observó persistencia en archivos.
- El módulo no importa `yfinance`, `src.persistence`, `artifacts` ni
  `experiments.psodata`.
- La comprobación fresca de importación bloqueó tanto `pso` como
  `run_validation_suite` y no detectó llamadas.

### Factibilidad

La suite ejecuta cinco semillas, comprueba finitud, no negatividad y suma
unitaria para todas las posiciones obtenidas (líneas 118-130). La reparación
de producción recorta valores negativos y normaliza, con reasignación uniforme
si la suma recortada es cero (`src/pso/velocity_model.py:20-36`). Los criterios
detectan valores no finitos, pesos negativos y sumas distintas de uno dentro
de la tolerancia.

La comprobación no cubre entradas inválidas deliberadas ni límites
individuales, apalancamiento, cortos, cardinalidad o costos; esas restricciones
no forman parte del contrato actual del optimizador. El caso verifica la
salida producida, no una demostración exhaustiva de todos los estados
posibles.

### Sphere sobre el simplex

`SimplexSphere` minimiza exactamente
\(\sum_i(w_i-0.25)^2\) (líneas 36-40). Bajo \(w_i\geq0\) y
\(\sum_iw_i=1\), el óptimo teórico es
\((0.25,0.25,0.25,0.25)\), que es la referencia usada. El criterio exige
fitness `<= 1e-4` y distancia `<= 2e-2` para cada semilla (líneas 133-145).

La ejecución independiente produjo:

| Semilla | Fitness | Distancia | Iteraciones | Terminación |
|---:|---:|---:|---:|---|
| 11 | 4.1752715954e-06 | 0.00204335 | 18 | patience |
| 12 | 1.7676513989e-06 | 0.00132953 | 29 | patience |
| 13 | 3.6732731276e-09 | 0.00006061 | 85 | patience |
| 14 | 1.6263430555e-06 | 0.00127528 | 37 | patience |
| 15 | 1.2189781400e-08 | 0.00011041 | 54 | patience |

Esto demuestra aproximación al óptimo conocido en esas cinco corridas. No
demuestra convergencia global, ausencia de mínimos alternativos, ni
optimalidad para otras semillas o configuraciones.

### Referencia independiente de mínima varianza

La matriz usada es

\[
\Sigma =
\begin{bmatrix}
0.04&0.01&0.00\\
0.01&0.09&0.02\\
0.00&0.02&0.16
\end{bmatrix}.
\]

Sus autovalores recalculados fueron aproximadamente
`[0.03794968, 0.08668599, 0.16536433]`, por lo que es definida positiva.
La referencia enumera todos los soportes no vacíos, resuelve
\(\Sigma_S^{-1}\mathbf{1}/(\mathbf{1}^\top\Sigma_S^{-1}\mathbf{1})\),
descarta pesos negativos y selecciona el menor valor factible (líneas
89-100). El resultado independiente fue:

- Pesos: `[0.646153846154, 0.205128205128, 0.148717948718]`
- Varianza: `0.027897435897436`

Las cinco corridas PSO quedaron por debajo de una brecha relativa de `1e-4`:

| Semilla | Fitness | Brecha relativa | Iteraciones |
|---:|---:|---:|---:|
| 11 | 0.027897610715 | 6.2664e-06 | 22 |
| 12 | 0.027899135502 | 6.0923e-05 | 16 |
| 13 | 0.027897865298 | 1.5392e-05 | 16 |
| 14 | 0.027897911955 | 1.7065e-05 | 16 |
| 15 | 0.027897691757 | 9.1714e-06 | 23 |

La referencia no usa PSO. Este resultado valida el benchmark cuadrático
sintético, no la función CVaR ni una frontera financiera.

### VaR/CVaR

Para retornos `[-0.2, -0.1, 0.1, 0.2]`, `alpha=0.50` y peso unitario:

- Percentil inferior de NumPy al 50%: `0.0`.
- Cola seleccionada por `<=`: `[-0.2, -0.1]`.
- Media de cola: `-0.15`.
- Riesgo positivo: `-CVaR = 0.15`.
- Con target `0.15`, retorno medio `0` y penalty `50`: `0.15 + 50*0.15 = 7.65`.

La recomputación coincidió con `0.15` y `7.65`. La implementación usa cola
inferior de retornos logarítmicos, incluye empates del umbral y convierte el
riesgo a signo positivo (`src/pso/fitness_function.py:15-40`). Es consistente
con las pruebas de producción `tests/test_pso04.py`, pero es una convención
del proyecto, no una definición universal de CVaR.

El dashboard no afirma validar VaR/CVaR con datos de mercado: muestra
explícitamente que el caso es manual y sintético (`validation_dashboard.py:140-155`).

### Diagnóstico de convergencia

Las dos corridas usan la misma matriz cero, función Sphere, tamaño de enjambre,
modelo Inertia, tolerancias, paciencia y límite de iteraciones; solo cambian
topología y semilla (`validation_dashboard_logic.py:188-208`). La traza real
del optimizador registra `gbest`, diversidad, movimiento, reparaciones y
terminación después de cada movimiento (`src/pso/optimizer.py:172-244`).
La interfaz etiqueta la abscisa como posterior al movimiento y explica que la
primera fila no es una instantánea inicial (`validation_dashboard.py:32-36`,
`159-162`).

La ejecución produjo:

| Topología | Semilla | Filas | Terminación | Diversidad inicial registrada | Movimiento medio inicial | Reparaciones acumuladas |
|---|---:|---:|---|---:|---:|---:|
| Ring | 101 | 39 | patience | 0.1861343 | 0.1814763 | 840 |
| Global | 102 | 77 | patience | 0.0747407 | 0.2760423 | 1750 |

Los valores proceden de las ejecuciones reales y no se rellenan con ceros.
Sin embargo, las semillas son distintas; por ello la gráfica es descriptiva
de esas dos corridas y no permite atribuir las diferencias exclusivamente a la
topología. Tampoco una curva horizontal demostraría por sí sola convergencia
global.

### Reproducibilidad

Con semilla `777`, misma matriz, topología, parámetros y generadores locales,
la suite obtuvo:

```text
fitness_equal=True
weights_equal=True
trace_equal=True
```

La lógica usa `np.random.default_rng(seed)` y `random.Random(seed)` por
ejecución (líneas 66-83), y la interfaz reemplaza los resultados de sesión al
repetir (líneas 78-81). Esto respalda reproducibilidad dentro de esta versión
del código. `created_at` y `elapsed_seconds` son naturalmente variables y no
forman parte de la comparación.

## Hallazgos

| ID | Severidad | Estado | Evidencia e impacto | Recomendación |
|---|---|---|---|---|
| VD-R-01 | **Media** | Defecto de diseño experimental | Ring usa semilla 101 y Global 102 (`validation_dashboard_logic.py:188-198`). La salida puede cambiar por la semilla además de la topología; una comparación visual no identifica el efecto causal de Ring frente a Global. | Usar semillas emparejadas para ambas topologías y, preferiblemente, reportar varias réplicas por semilla con estadísticas. Mantener la etiqueta descriptiva mientras no se cambie. |
| VD-R-02 | **Baja** | Brecha de prueba | `test_importing_logic_does_not_execute_pso` importa el módulo en `tests/test_validation_dashboard.py:10-13`, pero el módulo ya fue importado en la línea 6; `__import__` puede devolver la instancia cacheada y la prueba podría pasar sin verificar una importación fresca. | Limpiar `sys.modules` o ejecutar la comprobación en un subproceso limpio. La inspección directa y la prueba independiente realizada en esta revisión sí encontraron el comportamiento esperado. |
| VD-R-03 | **Baja** | Cobertura incompleta | La prueba de no persistencia solo parchea `Path.write_bytes` y `Path.write_text` (`tests/test_validation_dashboard.py:27-33`), y no prueba todos los mecanismos posibles de I/O ni la ausencia de red. El código revisado no contiene rutas de escritura, `yfinance` ni lectura de `.psodata`. | Mantener la inspección estática y ampliar la prueba con un entorno temporal/red bloqueada si se necesita una garantía automatizada más fuerte. |
| VD-R-04 | **Baja** | Cobertura no ejecutada | No hay pruebas automatizadas de los botones, `st.session_state`, selección de pestañas ni contenido visual. El smoke test confirmó que Streamlit inicia y responde, pero no sustituyó una interacción de navegador. | Añadir una prueba de componente o una comprobación manual documentada si la interfaz se convierte en evidencia de presentación. |

VD-R-02 a VD-R-04 son brechas de pruebas o verificabilidad, no evidencia de
que el dashboard ejecute PSO indebidamente, persista resultados o muestre datos
de mercado. No se identificaron defectos demostrados en las fórmulas del
benchmark Sphere, la referencia cuadrática o el caso manual CVaR.

## Mejoras opcionales

- Mostrar explícitamente en la pestaña de convergencia que Ring/Global usa
  semillas diferentes y que la comparación no es causal.
- Mostrar la matriz de covarianza y los límites/tolerancias junto con las
  referencias, para facilitar una reproducción manual.
- Añadir casos negativos deliberados para comprobar que criterios de
  factibilidad rechazan posiciones no finitas, negativas o no normalizadas.
- Separar en el resumen el número de categorías evaluadas del número total de
  ejecuciones PSO, actualmente resumido como seis categorías
  (`validation_dashboard_logic.py:270-284`).

Estas propuestas no se clasifican como defectos técnicos bloqueantes porque
la implementación ya declara que los casos son sintéticos y que no prueban
superioridad financiera.

## Limitaciones

1. No se ejecutó interacción de navegador ni inspección visual final; solo se
   realizó una inspección estática y un smoke test HTTP de Streamlit.
2. No se descargaron datos ni se evaluaron ventanas reales de mercado,
   backtesting, costos, rebalanceo o persistencia `.psodata`.
3. La revisión no demuestra convergencia global del PSO ni optimalidad global
   de la función CVaR penalizada.
4. La comparación Ring/Global queda limitada por las semillas diferentes.
5. No se modificaron parámetros, fórmulas, criterios, código de producción,
   pruebas existentes ni roadmap; el único archivo nuevo de esta revisión es
   este informe solicitado.

## Criterios de aceptación de la revisión

| Criterio | Estado | Evidencia |
|---|---|---|
| Contrastar el reporte con código y pruebas | Cumplido | Revisión de archivos y resultados reproducidos |
| Verificar aislamiento de la interfaz principal y producción | Cumplido | Diff de producción sin cambios de esta revisión; imports y código |
| Reproducir pruebas específicas y suite completa | Cumplido | 4/4 y 26/26 pruebas |
| Recalcular casos matemáticos relevantes | Cumplido | Sphere, covarianza, referencia y VaR/CVaR |
| Revisar trazas Ring/Global y primera fila | Cumplido con observación | Código de `ConvergenceTrace`, resultados y etiquetas UI |
| Verificar reproducibilidad y estado de interfaz | Parcial | Reproducibilidad lógica confirmada; interacción de navegador no ejecutada |
| No modificar el proyecto principal | Cumplido | Sin cambios en producción, pruebas existentes o roadmap |
| Separar defectos de mejoras opcionales | Cumplido | Hallazgos VD-R-01..04 y sección separada |

## Integridad del repositorio y conclusión

El estado final conservó los cambios iniciales del árbol: el roadmap ya estaba
modificado y los archivos de PSO-VD-01 ya estaban sin seguimiento. Durante la
revisión no se modificaron esos archivos ni ningún módulo de producción. Se
creó únicamente `reports/PSO-VD-01-R-independent-review.md` como entregable
solicitado; no se creó commit.

La respuesta a la pregunta central es: **sí, un tercero puede ejecutar el
dashboard y entender qué evidencia aportan sus casos sintéticos, con las
limitaciones declaradas; no puede usarlo todavía para sostener una comparación
controlada entre Ring y Global, convergencia global, validez financiera o
evidencia visual interactiva completa**. Antes de ampliarlo como instrumento
académico conviene emparejar semillas y fortalecer las pruebas de importación,
persistencia y estado de Streamlit. No se requiere cambiar el optimizador ni
las fórmulas para cerrar esta revisión.

