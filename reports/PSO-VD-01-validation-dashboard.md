# PSO-VD-01 — Dashboard independiente de validación

## Identificación y estado

- **ID:** PSO-VD-01
- **Fecha:** 2026-10-21
- **Rama:** `main`, con cambios preexistentes conservados
- **Estado:** implementada; revisión independiente pendiente
- **Commit:** no creado

La tarea implementa una interfaz Streamlit separada para ejecutar casos
sintéticos de validación bajo una acción explícita. No modifica `app.py`, el
optimizador, las funciones financieras ni los resultados persistidos.

## Alcance

### Incluido

- Entry point independiente `validation_dashboard.py`.
- Módulo puro `validation_dashboard_logic.py` para ejecutar y procesar casos
  en memoria.
- Casos de factibilidad, Sphere sobre el simplex, mínima varianza
  long-only, VaR/CVaR manual, convergencia Ring/Global y reproducibilidad.
- Estado de sesión para conservar resultados y botón explícito para repetir.
- Tablas, gráficas Plotly y advertencias que distinguen datos calculados de
  referencias y limitaciones.
- Pruebas automatizadas de importación, ejecución controlada, diagnósticos y
  ausencia de escritura persistente.

### Excluido

- Rediseño o importación de la interfaz principal.
- Descargas de Yahoo Finance, backtesting y lectura de `.psodata`.
- Persistencia de resultados, artefactos o informes durante la ejecución.
- Cambios en objetivos, ecuaciones, topologías, parámetros de producción o
  convenciones financieras.
- Afirmaciones de superioridad financiera u optimalidad global general.

## Cambios realizados

`validation_dashboard_logic.py` fija los casos y las semillas en código y
llama directamente a `pso` únicamente cuando `run_validation_suite()` es
invocada. Usa `ConvergenceTrace` para mostrar las métricas realmente
disponibles: iteraciones registradas, `gbest`, diversidad, movimiento,
reparaciones y motivo de terminación. La primera fila se identifica en la UI
como posterior al movimiento de la población.

`validation_dashboard.py` no ejecuta casos al importarse. Al abrirse muestra
un estado vacío y solo ejecuta tras `Ejecutar validación`; los resultados se
guardan en `st.session_state` y se exploran mediante pestañas sin repetir el
PSO. `Repetir validación` es la única acción que vuelve a ejecutar los casos.

Los parámetros principales son 30 partículas, Inertia con `c1=c2=1.7`,
`w=0.8`, `rtol=1e-4`, `atol=1e-8`, paciencia 10 y límite explícito de 120
iteraciones para los casos generales. El benchmark de mínima varianza usa
300 iteraciones para conservar el criterio documentado de PSO-03. Las
semillas están declaradas en el módulo.

## Evidencia y criterios

| Criterio | Estado | Evidencia |
|---|---|---|
| La página no ejecuta PSO al cargar/importar | Cumplido automáticamente | `main()` protegido y `test_importing_logic_does_not_execute_pso` |
| La ejecución requiere botón explícito | Cumplido por diseño | `validation_dashboard.py` |
| Los resultados sobreviven reruns normales | Cumplido por diseño | `st.session_state["validation_results"]` |
| Repetición explícita | Cumplido | Botón `Repetir validación` |
| Sin `.psodata`, red ni persistencia | Cumplido por diseño y prueba de escritura | `test_suite_does_not_write_results_or_use_persisted_artifacts` |
| Factibilidad long-only | Cumplido | Pesos finitos, no negativos y suma aproximadamente uno |
| Sphere con óptimo uniforme | Cumplido | Fitness, distancia, semillas y criterio `1e-4` |
| Mínima varianza independiente | Cumplido | Enumeración de caras del simplex y brecha relativa `<1e-4` |
| VaR/CVaR manual | Cumplido para la convención actual | Riesgo `0.15` y fitness `7.65` |
| Convergencia y diagnósticos disponibles | Cumplido | Curvas Ring/Global y tabla de traza |
| Reproducibilidad acotada | Cumplido | Fitness, pesos y `gbest` con semilla 777 |
| Verificación visual interactiva | No ejecutada | Requiere iniciar una sesión Streamlit manual |

## Comandos ejecutados

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 4 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 26 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `./.venv/bin/python -c 'import validation_dashboard; print("dashboard import ok")'` | **OK**, importación sin ejecución |
| `git diff --check` | **OK** |

Las advertencias de Streamlit durante `unittest` indican que no existe un
runtime interactivo y usa almacenamiento de caché en memoria; no constituyen
fallos. No se ejecutó una comprobación visual o interactiva de la página.

## Limitaciones y riesgos

1. Los benchmarks son sintéticos y no validan datos de mercado, backtesting ni
   superioridad financiera.
2. La convención manual de CVaR refleja exactamente la implementación actual;
   no se presenta como convención universal.
3. La gráfica compara corridas Ring y Global con semillas distintas
   (`101` y `102`), por lo que la diferencia es descriptiva del caso ejecutado,
   no una demostración universal de superioridad.
4. El dashboard no muestra motivo de terminación si la traza no lo proporciona;
   en la implementación actual sí está disponible.
5. La revisión independiente y la comprobación visual de Streamlit permanecen
   pendientes.

## Siguiente paso

Realizar revisión independiente de solo lectura del diff, pruebas y reporte.
Después de esa revisión podrá decidirse si el dashboard es apto para
incorporarse al flujo académico de presentación.
