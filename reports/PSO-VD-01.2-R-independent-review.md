# PSO-VD-01.2-R — Revisión independiente del manejo de errores del dashboard

## Veredicto

**Approved**

La implementación de PSO-VD-01.2 cierra `VD-NEW-01` dentro del alcance
solicitado. Una ejecución nueva invalida el resultado anterior antes de
comenzar; si `run_validation_suite()` falla, el estado queda en `None`, se
notifica el error y no se muestra éxito ni se ejecuta `st.rerun()` en la ruta
fallida de repetición. Una ejecución exitosa sigue almacenando resultados y
una repetición exitosa los reemplaza.

## Estado del repositorio

### Estado inicial

La revisión comenzó en:

```text
## main...origin/main [ahead 3]
 M docs/ai/ROADMAP.md
?? reports/PSO-VD-01-R-independent-review.md
?? reports/PSO-VD-01-validation-dashboard.md
?? reports/PSO-VD-01.1-R-independent-review.md
?? reports/PSO-VD-01.1-closeout.md
?? reports/PSO-VD-01.2-error-handling.md
?? tests/test_validation_dashboard.py
?? validation_dashboard.py
?? validation_dashboard_logic.py
```

El cambio de `docs/ai/ROADMAP.md`, los archivos del dashboard y los reportes
anteriores eran cambios preexistentes. Se conservaron sin sobrescribir ni
revertir. No existe `reports/PSO-VD-01-implementation.md`; no se hicieron
suposiciones sobre ese archivo ausente.

### Estado final

El árbol final conserva esos cambios y añade únicamente
`reports/PSO-VD-01.2-R-independent-review.md`. No se modificaron código,
pruebas, roadmap ni protocolos durante esta revisión y no se creó ningún
commit.

## Alcance y metodología

Se revisaron:

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/WORK_PROTOCOL.md`
- `reports/PSO-VD-01.1-R-independent-review.md`
- `reports/PSO-VD-01.2-error-handling.md`
- `validation_dashboard.py`
- `validation_dashboard_logic.py`
- `tests/test_validation_dashboard.py`

También se consideró el reporte original del dashboard cuando fue necesario
para entender el comportamiento previo. La revisión fue de solo lectura salvo
la creación de este informe.

## Inspección del código

### Helper de ejecución

`validation_dashboard.py:21-28` define `_execute_validation()`. Su orden de
operaciones es:

1. `st.session_state["validation_results"] = None` antes de invocar la suite.
2. Ejecución de `run_validation_suite()`.
3. Almacenar el nuevo resultado únicamente si la llamada retorna.
4. Capturar la excepción, llamar a `st.error(...)` y devolver `False`.
5. Devolver `True` solo después de una ejecución exitosa.

Por tanto, una excepción no puede dejar el objeto anterior en
`validation_results`, ni puede dejar un resultado parcial porque la asignación
del nuevo objeto ocurre solo después del retorno completo de la suite.

### Ruta `Ejecutar validación`

En `validation_dashboard.py:82-88`, el botón ejecuta el helper dentro del
spinner. El mensaje de éxito de `validation_dashboard.py:86` está condicionado
a `executed`. Si la suite falla, el helper devuelve `False`, se muestra el
mensaje de error desde el helper y no se muestra el mensaje de éxito. Como el
estado queda en `None`, la función retorna en `validation_dashboard.py:87-88`
antes de leer o renderizar resultados.

### Ruta `Repetir validación`

En `validation_dashboard.py:90-95`, la repetición usa el mismo helper. Solo
cuando `executed` es verdadero se llama a `st.rerun()`. En la ruta fallida no
se llama a `st.rerun()` y, al haber quedado el estado en `None`, no se
renderiza el resultado anterior.

No se encontró una ruta alternativa que vuelva a presentar resultados
obsoletos después de una excepción: la lectura para renderizado
(`validation_dashboard.py:90`) ocurre únicamente después de la comprobación
de que `validation_results` no es `None`.

## Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 8/8 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 30/30 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `git diff --check` | **OK** |
| Reproducción directa independiente del flujo éxito→fallo | **OK**, estado final `None` y error notificado |
| `git status --short --branch` e inspección final | **OK**, cambios preexistentes conservados |

Las pruebas de Streamlit emitieron advertencias normales por ejecución sin
`ScriptRunContext` y por la deprecación futura de `use_container_width`; no
fueron fallos.

## Reproducción del defecto corregido

La prueba `test_failed_execution_invalidates_previous_results_and_reports_error`
en `tests/test_validation_dashboard.py:112-133` reemplaza la suite por un
`side_effect` secuencial:

- primera llamada: retorna `successful_result`;
- segunda llamada: lanza `RuntimeError("synthetic failure")`.

La prueba comprueba que:

- la primera ejecución devuelve `True`;
- el resultado exitoso se almacena en el estado;
- la segunda ejecución devuelve `False`;
- el estado final es `None`;
- `st.error` recibe exactamente
  `No se pudo completar la validación: synthetic failure`.

La misma transición se reprodujo fuera del test runner con el resultado:

```text
{
  'first_ok': True,
  'same_first_result': True,
  'second_ok': False,
  'final_state': None,
  'errors': ['No se pudo completar la validación: synthetic failure']
}
```

Esta prueba fallaría con la implementación defectuosa anterior porque no
existía `_execute_validation()` y, más importante, la ruta anterior no
invalidaba el estado antes de llamar a `run_validation_suite()`. Por ello la
prueba discrimina la corrección real y no se limita a comprobar que una
ejecución exitosa continúa funcionando.

## Cobertura de interfaz

### Cobertura directa del helper

La prueba de regresión cubre de forma determinista la transición de estado y
la notificación de error del helper. También verifica implícitamente que la
excepción se maneja de forma controlada y no se propaga al llamador.

### Cobertura con `AppTest`

`test_streamlit_initial_state_and_explicit_execution` comprueba el estado
inicial, la acción explícita y el almacenamiento de resultados.
`test_streamlit_repeat_replaces_results` comprueba que una repetición exitosa
reemplaza el objeto anterior y conserva la configuración esperada.

Estas pruebas ejercitan el flujo normal de la interfaz Streamlit y pasan
después del cambio.

### Cobertura no disponible

No se ejecutó una prueba de navegador ni una inspección visual manual. La
prueba de error no usa `AppTest` para inyectar una excepción dentro de la
ejecución del archivo, porque con la estructura actual la función importada
`run_validation_suite` no se puede sustituir de forma fiable desde el proceso
de `AppTest`. Esto no bloquea el cierre: la prueba directa del helper cubre
precisamente la transición requerida, mientras `AppTest` cubre las rutas
normales de la interfaz. No se atribuye a la revisión cobertura de navegador
ni una prueba integral de Streamlit para la excepción.

## Estado de hallazgos

| ID | Severidad | Estado | Evidencia |
|---|---|---|---|
| `VD-NEW-01` | Media | **Cerrado** | `_execute_validation()` invalida antes de ejecutar, captura el error, deja el estado en `None` y la prueba éxito→fallo pasa. |

No se identificaron nuevos hallazgos relacionados con el objetivo de
PSO-VD-01.2. La ausencia del reporte histórico
`reports/PSO-VD-01-implementation.md` permanece como limitación documental
preexistente, no como defecto del manejo de errores.

## Limitaciones

1. No se ejecutó navegador ni inspección visual manual; no era necesario para
   demostrar el cierre de este defecto de estado.
2. La ruta de error se probó directamente mediante el helper, no mediante una
   interacción `AppTest` completa. La cobertura normal de interfaz sí se
   ejecutó con `AppTest`.
3. No se modificaron ni reevaluaron las matemáticas, semillas, topologías,
   funciones financieras o casos sintéticos, por estar fuera del alcance.

## Conclusión

`VD-NEW-01` queda cerrado. Una ejecución exitosa seguida de una fallida ya no
deja resultados anteriores accesibles como resultados actuales; el usuario
recibe un error explícito y no un mensaje de éxito. Las rutas normales de
ejecución y repetición continúan funcionando, y todas las pruebas solicitadas
pasaron.

PSO-VD-01.2 puede considerarse técnicamente completado, sujeto a las reglas
del proyecto que mantienen la revisión independiente como evidencia separada.
