# Prompts reutilizables

Estos prompts son autocontenidos para una conversación nueva. El agente debe
leer el repositorio y los reportes antes de actuar; el prompt no reemplaza
`AGENTS.md` ni el roadmap.

| Archivo | Uso |
|---|---|
| `task-template.md` | Plantilla general para una tarea del roadmap. |
| `independent-review-template.md` | Revisión de solo lectura de una tarea terminada. |
| `PSO-01.md` | Invariantes, entradas, restricciones y reproducibilidad. |
| `PSO-02.md` | Instrumentación y diagnóstico de convergencia. |
| `PSO-03.md` | Funciones de referencia y comparación independiente. |

Todos los prompts exigen confirmar dependencias, alcance, criterios, pruebas,
reporte y actualización del roadmap. Las tareas posteriores quedan bloqueadas
si una dependencia está bloqueada o su revisión independiente sigue pendiente.
