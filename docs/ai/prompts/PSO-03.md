# PSO-03 — Referencias sintéticas y mínima varianza

Ejecuta **PSO-03** y solo PSO-03.

Lee primero `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`,
`reports/PSO-01-invariants-reproducibility.md`,
`reports/PSO-02-convergence-diagnostics.md` y todos los reportes relacionados.
Confirma que PSO-01 y PSO-02 estén implementadas y revisadas; si no, detente.

## Objetivo

Validar el comportamiento del algoritmo con funciones sintéticas y comparar,
de forma independiente, el problema de mínima varianza de un portafolio
long-only con presupuesto completo.

## Alcance incluido

- Casos sintéticos con óptimo conocido y problemas restringidos pequeños.
- Referencia independiente para `w >= 0`, `sum(w)=1`, usando el mismo problema,
  matriz y convención temporal.
- Múltiples semillas, factibilidad, gap relativo, monotonicidad de `gbest` y
  valores no finitos.
- Reporte y actualización del roadmap.

## Alcance excluido

No cambies la función objetivo de producción, la frontera, los parámetros, la
interfaz ni las métricas financieras. No compares problemas distintos
silenciosamente: la formulación penalizada y una restricción exacta deben
tratarse como experimentos separados. No añadas un solver externo sin
aprobación.

## Aceptación

- Cada función sintética tiene fórmula, óptimo, tolerancia y semilla
  documentados.
- La referencia de mínima varianza declara cómo obtiene la solución y verifica
  factibilidad.
- Se reportan resultados por semilla y limitaciones.
- Se distingue evidencia del harness de conclusiones sobre datos de mercado.
- El reporte y el roadmap no declaran validez académica más allá de lo medido.

Crea `reports/PSO-03-reference-validation.md` y deja pendiente la revisión
independiente.
