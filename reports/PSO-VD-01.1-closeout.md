# PSO-VD-01.1 — Cierre de observaciones del dashboard de validación

## Identificación y estado inicial

- **ID:** PSO-VD-01.1
- **Fecha:** 2026-10-21
- **Rama:** `main`
- **Estado inicial:** `main...origin/main [ahead 3]`
- **Cambios preexistentes conservados:** `docs/ai/ROADMAP.md` modificado y los
  archivos de PSO-VD-01, incluida la revisión independiente, sin seguimiento.
- **Commit:** no creado.

El objetivo fue cerrar las observaciones `VD-R-01` a `VD-R-04` de
`reports/PSO-VD-01-R-independent-review.md`, sin cambiar el optimizador, las
funciones financieras, `app.py`, el roadmap ni los artefactos históricos.

## Cambios realizados

### VD-R-01 — Comparación Ring/Global

`validation_dashboard_logic.py` ahora ejecuta tres pares fijos de corridas con
semillas comunes `101`, `102` y `103`. En cada par se conservan los mismos
datos sintéticos, tamaño del enjambre, modelo Inertia, parámetros, tolerancias,
paciencia y máximo de iteraciones; el único factor cambiado es la topología.
Los resultados individuales permanecen disponibles bajo
`results["convergence"]["runs"]`, agrupados por topología y semilla.

`validation_dashboard.py` muestra el selector de semilla emparejada y explica
que el emparejamiento mejora el control experimental, pero no demuestra por sí
solo la superioridad general de Ring o Global. La interfaz no declara una
topología ganadora.

### VD-R-02 — Importación fresca

`tests/test_validation_dashboard.py` sustituyó la importación cacheada por una
prueba en un subproceso limpio. El subproceso reemplaza el punto de entrada
`src.pso.pso` por un fallo explícito antes de importar
`validation_dashboard_logic`; la importación solo pasa si no ejecuta PSO y
produce `fresh import ok`.

### VD-R-03 — Persistencia y red

La prueba ejecuta `run_validation_suite()` desde un directorio temporal,
comprueba que no aparecen archivos nuevos y bloquea los puntos de acceso
`socket.create_connection` y `urllib.request.urlopen`. La comprobación
demuestra que la suite no necesita esos mecanismos de red ni crea artefactos
en la ejecución probada; no pretende demostrar que cualquier acceso de red
posible del proceso quede globalmente bloqueado. La prueba tampoco usa ni lee
`artifacts/experiments.psodata`.

### VD-R-04 — Interfaz Streamlit

Se añadieron pruebas con `streamlit.testing.v1.AppTest` para:

- estado inicial sin `validation_results` y con el aviso de resultados
  pendientes;
- ejecución únicamente después de pulsar `Ejecutar validación`;
- almacenamiento del resultado en `st.session_state`;
- aparición de `Repetir validación` después de ejecutar;
- reemplazo del objeto de resultados tras repetir la validación y conservación
  de la misma configuración de semillas.

Estas pruebas cubren el flujo funcional y el estado de ejecución. No son una
validación visual completa del navegador; no se realizó inspección visual
manual ni prueba de navegador.

## Configuración y evidencia de reproducibilidad

La configuración efectiva de las comparaciones Ring/Global fue:

| Parámetro | Valor |
|---|---:|
| `swarm_size` | 30 |
| `max_iterations` | 120 |
| `rtol` | `1e-4` |
| `atol` | `1e-8` |
| `patience` | 10 |
| `inertia_c1` | 1.7 |
| `inertia_c2` | 1.7 |
| `inertia` | 0.8 |
| Semillas comunes | 101, 102, 103 |

La comprobación independiente produjo:

```text
paired_seeds=True
ring_global_only_topology=True
reproducible_suite=True
logic_reproducibility={
  'same_seed': 777,
  'fitness_equal': True,
  'weights_equal': True,
  'trace_equal': True,
  'ok': True
}
```

La prueba de importación fresca produjo `fresh-import-ok`.

## Pruebas y comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest tests.test_validation_dashboard -v` | **OK**, 7 pruebas |
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 29 pruebas |
| `./.venv/bin/python -m py_compile validation_dashboard.py validation_dashboard_logic.py tests/test_validation_dashboard.py` | **OK** |
| `git diff --check` | **OK** |
| Comprobación independiente de semillas/configuración/reproducibilidad | **OK** |
| Comprobación de importación fresca en subproceso | **OK** |
| `streamlit.testing.v1.AppTest` para estado, ejecución y repetición | **OK**, incluido en las 7 pruebas |
| Inspección de `git status --short --branch` y diff | **OK**, sin cambios de producción o roadmap creados por esta tarea |

La suite completa emitió advertencias normales de Streamlit por ejecutarse sin
runtime interactivo y por la deprecación futura de `use_container_width`; no
fueron fallos. No se descargaron datos de mercado ni se usó
`artifacts/experiments.psodata`.

## Archivos modificados por esta tarea

- `validation_dashboard_logic.py`: semillas emparejadas y resultados
  individuales de convergencia.
- `validation_dashboard.py`: visualización de las corridas emparejadas,
  selector de semilla y limitación experimental explícita.
- `tests/test_validation_dashboard.py`: importación fresca, aislamiento,
  emparejamiento/reproducibilidad y pruebas funcionales con `AppTest`.
- `reports/PSO-VD-01.1-closeout.md`: este informe.

No se modificaron `app.py`, `src/`, las funciones financieras, las topologías,
los modelos de velocidad, `artifacts/experiments.psodata` ni
`docs/ai/ROADMAP.md`. No se creó ningún commit.

## Limitaciones y estado de los hallazgos

| Hallazgo | Estado de implementación | Evidencia o limitación restante |
|---|---|---|
| VD-R-01 | Tratado | Tres pares con semillas comunes y resultados individuales; no implica superioridad general. |
| VD-R-02 | Tratado | Importación en subproceso limpio con PSO bloqueado durante la importación. |
| VD-R-03 | Tratado proporcionalmente | Directorio temporal sin artefactos y puntos de red usados por la prueba bloqueados; no es una garantía de bloqueo global de toda red posible. |
| VD-R-04 | Tratado proporcionalmente | `AppTest` cubre estado y acciones; la inspección visual/navegador queda no ejecutada. |

Los casos siguen siendo sintéticos y no validan optimalidad global, desempeño
financiero, datos de mercado ni backtesting. La revisión independiente nueva
debe confirmar estos cambios y decidir el estado formal de los hallazgos; este
informe no emite un veredicto de auditoría.

## Estado final

El estado final conserva el cambio preexistente de `docs/ai/ROADMAP.md` y los
archivos históricos de PSO-VD-01/R. La evidencia de trabajo de esta tarea está
lista para una nueva revisión independiente. No se modificaron módulos de
producción, no se alteraron criterios matemáticos o financieros y no se creó
un commit.
