# PSO-02 — Instrumentación y diagnóstico de convergencia

Ejecuta **PSO-02** y solo PSO-02.

Lee primero `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`,
`reports/PSO-01-invariants-reproducibility.md` y los reportes relacionados.
Confirma que PSO-01 esté implementada y revisada; si no, detente.

## Objetivo

Instrumentar por generación el estado suficiente para distinguir convergencia
real, pérdida de diversidad, tolerancia/paciencia, degeneración de reparación y
límite máximo de iteraciones.

## Alcance incluido

- Estadísticas de fitness actual y mejores por partícula.
- `gbest`, mejora, tolerancia, contador de paciencia, diversidad y tamaño de
  historial.
- Iteración final y motivo explícito de terminación.
- Pruebas de forma, monotonicidad y compatibilidad/persistencia documentada.
- Reporte y actualización del roadmap.

## Alcance excluido

No cambies la función objetivo, la dinámica, los parámetros, las tolerancias,
la condición de parada ni la política de reparación. No optimices la UI ni
interpretes resultados financieros todavía.

## Aceptación

- La instrumentación no altera el resultado matemático de una corrida.
- Las trazas distinguen `max_iterations` de `patience`.
- Se documenta la diferencia de longitudes entre historiales si se conserva.
- Se prueba qué ocurre al persistir y restaurar los datos.
- El reporte enumera evidencia ejecutada y no ejecutada.

Crea `reports/PSO-02-convergence-diagnostics.md` y deja pendiente la revisión
independiente.
