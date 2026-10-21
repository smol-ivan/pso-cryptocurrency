# Instrucciones para agentes

Estas instrucciones aplican a cualquier agente que trabaje en este repositorio.

## Antes de trabajar

1. Lee `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md` y `docs/ai/ROADMAP.md`.
2. Lee los reportes relacionados con el ID asignado y conserva los reportes de
   tareas existentes; no los sobrescribas.
3. Revisa `git status`, confirma la rama de trabajo y verifica las dependencias
   del ID elegido.
4. Confirma el objetivo, el alcance autorizado y los criterios de aceptación
   antes de editar.

## Reglas de ejecución

- Trabaja exclusivamente dentro del alcance del ID autorizado.
- En tareas de pruebas o diagnóstico no modifiques la función objetivo, los
  parámetros, las condiciones de parada, las topologías ni las ecuaciones
  financieras, salvo autorización explícita.
- No corrijas problemas ajenos por iniciativa propia. Regístralos como riesgos
  o tareas futuras.
- No sobrescribas trabajo existente ni descartes cambios del usuario.
- Evita dependencias, abstracciones y complejidad innecesarias.
- No incluyas secretos, credenciales ni datos sensibles.
- Ejecuta las pruebas y comprobaciones pertinentes; informa tanto las
  ejecutadas como las que no pudieron ejecutarse.
- Al terminar, crea o actualiza el reporte de la tarea y actualiza el roadmap.
- No marques una tarea como completada sin criterios de aceptación y evidencia
  suficiente. La revisión independiente pendiente debe seguir figurando como
  pendiente.
- Si el problema excede el alcance, documenta el hallazgo y propone una tarea
  futura; no amplíes unilateralmente el trabajo.

## Documentos de referencia

- Contexto técnico: [`docs/ai/PROJECT_CONTEXT.md`](docs/ai/PROJECT_CONTEXT.md)
- Plan operativo: [`docs/ai/ROADMAP.md`](docs/ai/ROADMAP.md)
- Protocolo: [`docs/ai/WORK_PROTOCOL.md`](docs/ai/WORK_PROTOCOL.md)
- Convención de reportes: [`reports/README.md`](reports/README.md)
