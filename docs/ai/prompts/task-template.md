# Plantilla — ejecutar una tarea del roadmap

Ejecuta exclusivamente la tarea **`<ID>`** de `docs/ai/ROADMAP.md`.

1. Lee `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`, `docs/ai/ROADMAP.md`, este
   prompt y todos los reportes relacionados.
2. Revisa `git status` y confirma la rama. No descartes cambios existentes.
3. Verifica que las dependencias del ID estén completadas y revisadas. Si no lo
   están, detente y documenta el bloqueo; no implementes una tarea posterior.
4. Confirma en el reporte el objetivo, alcance incluido/excluido y criterios de
   aceptación.
5. Implementa solo lo autorizado por el ID. No corrijas problemas ajenos.
   Durante pruebas o diagnóstico no modifiques función objetivo, parámetros,
   parada, topologías ni ecuaciones financieras sin autorización explícita.
6. Ejecuta comprobaciones pertinentes e informa resultados pasados, fallidos y
   no ejecutados. No inventes comandos ni resultados.
7. Crea `reports/<ID>-<slug>.md` siguiendo `reports/README.md`.
8. Actualiza el estado del roadmap y deja explícita la revisión independiente
   pendiente.
No hagas commit salvo autorización del usuario o del flujo de trabajo.
No hagas commit salvo autorización del usuario o del flujo de trabajo.
