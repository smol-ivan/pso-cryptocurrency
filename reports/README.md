# Convención de reportes

Los reportes son evidencia de tareas, no sustitutos del código ni del
roadmap. Los reportes históricos existentes se conservan sin sobrescribir.

## Nombres

Usar `reports/<ID>-<slug>.md`, con el ID estable del roadmap y un slug breve en
inglés o español consistente con los reportes existentes. Las revisiones
independientes usan `reports/<ID>-R-<slug>.md`.

## Contenido mínimo

Cada reporte debe incluir:

- ID, objetivo y fecha si puede determinarse.
- Estado inicial, rama y alcance incluido/excluido.
- Cambios realizados y archivos afectados.
- Comandos ejecutados y resultado exacto.
- Pruebas pasadas, fallidas y no ejecutadas.
- Evidencia experimental, distinguiendo observación de interpretación.
- Limitaciones, problemas y preguntas pendientes.
- Criterios de aceptación cumplidos, incumplidos o no verificables.
- Decisiones y justificación.
- Siguiente paso recomendado.

No afirmar que una prueba pasó si no se ejecutó. No registrar secretos,
credenciales, datos personales ni datos sensibles. Un artefacto `.psodata` no
es por sí mismo evidencia de corrección; debe acompañarse de configuración,
semillas, versión del código y procedimiento.
