# PSO-09 — Refactorización estructural

## Identificación y alcance

- **Fecha:** 2026-10-28
- **Rama:** `main`
- **Estado:** implementada con limitación documentada
- **Commit:** no creado
- **Incluido:** separación del servicio de configuración/ejecución de
  experimentos respecto de la lógica específica de Streamlit, corrección de
  la ruta de importación de `src.run_pso.py`, actualización de comandos de
  ejecución y trazabilidad operativa.
- **Excluido:** cambios en funciones objetivo, operadores PSO, parámetros,
  terminación, métricas financieras, interfaces, persistencia, artefactos
  históricos y eliminación de `app.py`.

## Estado inicial

El repositorio ya contenía `src/pso/` como core, `src/finance.py` y
`src/utils.py` como lógica de datos/métricas, `src/experiments.py` y
`src/run_pso.py` como ejecución de experimentos, además de `app.py` y
`src/ui/` como dashboard principal y `validation_dashboard.py` como dashboard
independiente de validación.

El árbol tenía cambios previos del usuario en `docs/ai/PROJECT_CONTEXT.md` y
en la configuración Nix/direnv. No se sobrescribieron ni descartaron.

## Cambios realizados

| Archivo | Cambio |
|---|---|
| `src/services/experiment_service.py` | Nuevo servicio sin importar Streamlit para construir configuraciones y ejecutar lotes de experimentos. |
| `src/services/__init__.py` | API pequeña y explícita del área de servicios. |
| `dashboards/legacy/experiment_controller.py` | Conserva validación, caché y orquestación de la UI legacy, delegando construcción y ejecución al servicio. |
| `dashboards/legacy/ui/` | Componentes, gráficas, colores y pestañas de la interfaz legacy, movidos desde `src/ui/`. |
| `dashboards/validation/` | Entry point y lógica del dashboard de validación, movidos desde la raíz. |
| `dashboards/v2/` | Paquete reservado para la futura interfaz principal v2. |
| `src/run_pso.py` | Eliminado el parche global de `sys.path`; se usa la importación de paquete existente. |
| `README.md` | Documentados los entrypoints principal y de validación y la separación de responsabilidades. |
| `docs/ai/ROADMAP.md` | Registrado PSO-09 y la ausencia preexistente de un entrypoint legacy separado. |

El nuevo servicio solo depende de `src.experiments`, `src.run_pso` y
`src.pso`; no importa `streamlit`, `src.ui` ni ningún dashboard. El controlador
legacy continúa siendo el adaptador de presentación que mantiene la caché
existente. `src/` ya no contiene módulos de interfaz Streamlit.
No se modificaron ecuaciones, defaults ni secuencias de ejecución.

## Entry points

| Aplicación | Comando | Resultado estructural |
|---|---|---|
| Legacy | `uv run streamlit run dashboards/legacy/app.py` | Entry point actual movido desde `app.py`; conserva sus funcionalidades. |
| Revamp / v2 | Pendiente | `dashboards/v2/` queda reservado; no se inventó una interfaz nueva. |
| Validación | `uv run streamlit run dashboards/validation/validation_dashboard.py` | Entry point independiente movido desde `validation_dashboard.py`. |

## Validación ejecutada

| Comando | Resultado |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests -v` | **OK**, 34 pruebas |
| Importación de `src.pso`, `src.experiments`, `src.finance`, `src.persistence` y `src.services.experiment_service` comprobando que `streamlit` no aparezca en `sys.modules` | **OK** |
| `./.venv/bin/python -m py_compile src/services/experiment_service.py src/controllers/experiment_controller.py src/run_pso.py app.py validation_dashboard.py validation_dashboard_logic.py` | **OK** |
| `git diff --check` | No ejecutado como resultado limpio: detecta un espacio en blanco al final de `docs/ai/PROJECT_CONTEXT.md`, archivo con cambio previo del usuario. |

Las pruebas emitieron advertencias normales de Streamlit al ejecutarse fuera de
un runtime interactivo; no produjeron fallos. No se ejecutó una sesión visual
interactiva de cada dashboard ni una descarga real de Yahoo Finance.

## Criterios y limitaciones

- **Cumplido:** `src/` queda libre de imports de Streamlit; la ejecución PSO
  existente y sus resultados de prueba se conservan; los dashboards legacy y
  validation tienen directorios y entrypoints independientes; `v2` queda
  preparado sin duplicar una interfaz inexistente.
- **No verificable:** inicio interactivo de Streamlit en esta ejecución.
- **Pendiente:** implementar la interfaz de `dashboards/v2/` en una tarea
  posterior.

## Siguiente paso

Revisión independiente del diff y decisión explícita sobre cuál interfaz,
si existe fuera de este checkout, debe registrarse como legacy antes de añadir
un tercer entrypoint.
