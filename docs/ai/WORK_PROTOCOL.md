# Protocolo de trabajo con agentes

1. Revisar `git status` y confirmar la rama. Si hay cambios ajenos que
   interfieren, detenerse y pedir instrucciones; no descartarlos.
2. Elegir un ID de `docs/ai/ROADMAP.md` cuyas dependencias estén satisfechas y
   cuya revisión previa no esté pendiente.
3. Leer `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`, el prompt del ID y todos los
   reportes relacionados.
4. Confirmar por escrito en el reporte el ID, objetivo, alcance incluido,
   alcance excluido y criterios de aceptación.
5. Implementar exclusivamente el alcance autorizado. En tareas de pruebas o
   diagnóstico, no cambiar la matemática del PSO sin autorización explícita.
6. Ejecutar pruebas y comprobaciones pertinentes, revisar el diff y separar
   resultados ejecutados de resultados no verificables.
7. Crear o actualizar `reports/<ID>-<slug>.md` con la evidencia completa.
8. Actualizar el estado del ID en el roadmap. Una tarea implementada sigue
   pendiente de revisión hasta que exista evidencia independiente.
9. Solicitar una revisión de solo lectura. El revisor debe usar otra rama o
   worktree si puede coincidir con trabajo en curso; nunca editar los mismos
   archivos simultáneamente.
10. Resolver observaciones o documentar por qué no se resuelven y enlazar el
    reporte de revisión.
11. Registrar el resultado con un commit solo cuando el usuario lo apruebe o el
    flujo autorizado lo permita. No reescribir historial.

## Uso desde una conversación nueva

El agente debe recibir únicamente el ID y el prompt correspondiente, por
ejemplo:

> Ejecuta `PSO-01` usando `docs/ai/prompts/PSO-01.md`. Lee primero `AGENTS.md`,
> `docs/ai/PROJECT_CONTEXT.md`, `docs/ai/ROADMAP.md`, la auditoría y los
> reportes relacionados. Respeta dependencias, alcance y criterios de
> aceptación; crea el reporte y actualiza el roadmap.

Si el ID está bloqueado, su revisión previa está pendiente o falta evidencia,
el agente debe detenerse y documentar el bloqueo en lugar de iniciar la tarea.
