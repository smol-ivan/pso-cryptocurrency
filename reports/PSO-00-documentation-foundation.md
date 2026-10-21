# PSO-00 — Preparar la base documental

## Objetivo y fecha

- **Objetivo:** preparar el repositorio para trabajo trazable con agentes de IA
  sin modificar la implementación del PSO.
- **Fecha:** 2026-10-20.
- **Estado:** completada; revisión independiente pendiente.

## Estado inicial

La rama era `main`, alineada con `origin/main`, sin cambios mostrados por
`git status --short`. Existían `PROJECT_CONTEXT_REPORT.md`,
`docs/reporte_inicial.md` y `reports/pso_validation_audit.md`. No existían
`AGENTS.md`, `docs/ai/`, prompts para tareas ni pruebas automatizadas
detectadas en el árbol.

## Cambios realizados

Se añadieron:

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `docs/ai/WORK_PROTOCOL.md`
- `docs/ai/prompts/README.md`
- `docs/ai/prompts/task-template.md`
- `docs/ai/prompts/independent-review-template.md`
- `docs/ai/prompts/PSO-01.md`
- `docs/ai/prompts/PSO-02.md`
- `docs/ai/prompts/PSO-03.md`
- `reports/README.md`
- este reporte

No se modificaron archivos de implementación, configuración de ejecución,
dependencias ni reportes históricos.

## Comprobaciones ejecutadas

Se inspeccionaron:

- estado y ramas de Git;
- estructura del repositorio;
- `README.md`, `pyproject.toml`, `app.py` y los módulos de datos, controlador,
  PSO, finanzas, persistencia y UI;
- `PROJECT_CONTEXT_REPORT.md`, `docs/reporte_inicial.md` y
  `reports/pso_validation_audit.md`;
- búsqueda de instrucciones existentes, pruebas y configuración de runners.

No se ejecutaron pruebas del PSO, experimentos financieros, descargas de
Yahoo Finance ni el dashboard, de acuerdo con el alcance de esta tarea.

## Evidencia y límites

La documentación distingue hechos respaldados por el código, hallazgos de
reportes históricos, hipótesis y preguntas pendientes. Los hallazgos relevantes de la documentación heredada se incorporaron al
contexto vigente. La posterior eliminación aprobada de los tres documentos
heredados está registrada en
`reports/PSO-00-documentation-cleanup.md`; este reporte conserva el estado y
las comprobaciones de la preparación original.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| Instrucciones generales para agentes | Cumplido |
| Contexto técnico basado en evidencia | Cumplido |
| Roadmap por fases con IDs, dependencias y aceptación | Cumplido |
| Convención de reportes | Cumplido |
| Protocolo de trabajo | Cumplido |
| Plantillas y prompts PSO-01/02/03 | Cumplido |
| No modificar implementación ni realizar validación nueva | Cumplido |
| Revisión independiente | No verificable todavía |

## Decisiones y siguiente paso

Se adoptó `PSO-00` para la preparación documental y `PSO-00-R` para su
revisión independiente. `PSO-01` no debe comenzar hasta que la revisión de
`PSO-00` esté registrada y no deje contradicciones bloqueantes.
