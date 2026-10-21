# PSO-01 — Invariantes, entradas y reproducibilidad

Ejecuta **PSO-01** y solo PSO-01.

Lee primero `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`,
`docs/ai/ROADMAP.md`, `reports/PSO-00-documentation-foundation.md`,
`reports/PSO-00-documentation-cleanup.md` y los reportes relacionados.
Confirma que `PSO-00-R` esté resuelta; si está pendiente o bloqueada, detente.

## Objetivo

Crear evidencia determinista sobre validación de entradas, pesos no negativos,
presupuesto completo, dimensiones, valores finitos, casos límite y control de
todas las fuentes aleatorias. Define y documenta la política aprobada para
posición nula antes de implementarla.

## Alcance incluido

- Tests focalizados del núcleo PSO, fitness, topologías, velocidades y
  orquestación de semillas.
- Corrección mínima y autorizada de RNG o reparación solo si es necesaria para
  cumplir el contrato aprobado.
- Reporte y actualización del roadmap.

## Alcance excluido

No cambies función objetivo, penalty, parámetros, topologías, condiciones de
parada, ecuaciones financieras, interfaz ni resultados financieros. No añadas
dependencias sin aprobación explícita.

## Aceptación

- Los casos válidos comprueban no negatividad y suma de pesos.
- Los casos inválidos tienen comportamiento explícito y probado.
- La reproducibilidad se define con una política concreta y se prueba con la
  misma configuración y semilla.
- Se separan fallos esperados del comportamiento corregido.
- El reporte incluye comandos y resultados reales; el roadmap marca revisión
  independiente pendiente.

Usa `reports/README.md`, crea `reports/PSO-01-invariants-reproducibility.md`
y no hagas commit sin autorización.
