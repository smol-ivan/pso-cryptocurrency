# Roadmap operativo de validación

Este roadmap refleja evidencia del repositorio, no promesas de los agentes.
`completada` significa que existen cambios y evidencia para los criterios
indicados; `revisada` es un estado independiente y puede seguir pendiente.
Una tarea sin revisión independiente no habilita automáticamente sus
dependientes.

## Reglas de actualización

1. Antes de iniciar, registrar el ID, rama, dependencias satisfechas y alcance.
2. Cambiar a `en progreso` solo al comenzar trabajo autorizado.
3. Al terminar, añadir el reporte con comandos, resultados y criterios
   verificables. Separar pruebas pasadas, fallidas y no ejecutadas.
4. Mantener `revisión independiente: pendiente` hasta que un revisor de solo
   lectura examine diff, código, pruebas, resultados y reporte.
5. Si una dependencia falla o queda sin evidencia, marcar `bloqueada` y no
   iniciar tareas posteriores.
6. Registrar decisiones importantes en reportes enlazados; no convertir este
   archivo en un historial narrativo.
7. Marcar `descartada` solo con una razón documentada y aprobación del usuario.

## Estados actuales

### Fase 0 — Preparación y diagnóstico

#### PSO-00 — Preparar la base documental
- **Objetivo:** establecer instrucciones, contexto, roadmap, prompts y protocolo.
- **Justificación:** permitir trabajo trazable desde conversaciones nuevas.
- **Incluye:** documentación de arquitectura real, auditoría histórica, reglas
  de trabajo y convención de reportes.
- **Excluye:** cambios de código, pruebas nuevas y experimentos nuevos.
- **Dependencias:** ninguna.
- **Aceptación:** existen `AGENTS.md`, contexto, roadmap, protocolo y prompts;
  los reportes previos permanecen intactos; hechos, hipótesis y pendientes
  están separados.
- **Evidencia:** diff documental,
  `reports/PSO-00-documentation-foundation.md` y
  `reports/PSO-00-documentation-cleanup.md`.
- **Reporte esperado:** `reports/PSO-00-documentation-foundation.md`.
- **Estado:** completada.
- **Revisión independiente:** aprobada en `reports/PSO-00-R-documentation-review.md`.
- **Riesgos/decisiones:** aprobar si la nomenclatura y el nivel de detalle son
  adecuados para el flujo del proyecto.

#### PSO-00-R — Revisar la base documental
- **Objetivo:** comprobar de forma independiente que la documentación no
  inventa arquitectura, resultados ni tareas completadas.
- **Justificación:** la documentación es la fuente de verdad compartida.
- **Incluye:** revisión de diff, referencias al código, reportes históricos y
  consistencia de dependencias.
- **Excluye:** editar archivos o implementar tareas.
- **Dependencias:** PSO-00.
- **Aceptación:** reporte de revisión con hallazgos y ninguna modificación del
  revisor.
- **Evidencia:** reporte de revisión enlazado.
- **Reporte esperado:** `reports/PSO-00-R-documentation-review.md`.
- **Estado:** aprobada.
- **Riesgos/decisiones:** la referencia provisional usada durante la prueba de
  bloqueo fue retirada; no quedan contradicciones bloqueantes.

### Fase 1 — Pruebas e invariantes del PSO

#### PSO-01 — Validar invariantes y reproducibilidad
- **Objetivo:** probar entradas, pesos, restricciones, semillas y casos límite.
- **Justificación:** la auditoría documenta reproducibilidad incompleta y una
  posible posición nula.
- **Incluye:** tests focalizados y, solo con autorización explícita, la
  corrección mínima del contrato de RNG/reparación.
- **Excluye:** cambiar fitness, parámetros, topologías, parada o métricas.
- **Dependencias:** PSO-00 y PSO-00-R aprobada.
- **Aceptación:** pruebas deterministas para la política aprobada; errores
  explícitos para entradas inválidas; no regresión de pesos válidos; reporte
  de cada caso no verificable.
- **Evidencia:** suite ejecutada, diff y reporte.
- **Reporte esperado:** `reports/PSO-01-invariants-reproducibility.md`.
- **Estado:** implementada; revisión independiente aprobada.
- **Evidencia de revisión:** verificación independiente posterior registrada
  en `reports/PSO-01-invariants-reproducibility.md`.
- **Riesgos/decisiones:** la posición nula usa reasignación uniforme y la
  semilla de experimento controla NumPy y `random`; quedan fuera de PSO-01 las
  convenciones financieras y la instrumentación de convergencia.

### Fase 2 — Diagnóstico de convergencia

#### PSO-02 — Instrumentar la convergencia
- **Objetivo:** registrar estadísticas por generación y motivo real de parada.
- **Justificación:** la UI muestra convergencia, pero no basta para distinguir
  convergencia, colapso o tolerancia.
- **Incluye:** instrumentación y pruebas de trazas.
- **Excluye:** cambiar la función objetivo, dinámica, tolerancias o criterio.
- **Dependencias:** PSO-01 implementada y revisada.
- **Aceptación:** historial documentado con gbest, fitness poblacional,
  diversidad, tolerancia, paciencia, iteración final y motivo; compatibilidad
  o migración explícita de `.psodata`.
- **Evidencia:** pruebas de forma/monotonicidad y ejemplo reproducible.
- **Reporte esperado:** `reports/PSO-02-convergence-diagnostics.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** decidir qué formato persistir y cómo tratar archivos
  históricos sin diversidad.

### Fase 3 — Validación matemática y comparación independiente

#### PSO-03 — Validar referencias sintéticas y mínima varianza
- **Objetivo:** comprobar el comportamiento del PSO en funciones con óptimo
  conocido y comparar mínima varianza long-only contra una referencia
  independiente.
- **Justificación:** aislar el algoritmo de datos de mercado.
- **Incluye:** harness sintético, referencia analítica/numerical y múltiples
  semillas.
- **Excluye:** afirmar validez financiera o cambiar la aplicación.
- **Dependencias:** PSO-01 y PSO-02 implementadas y revisadas.
- **Aceptación:** misma matriz y convención, solución de referencia,
  óptimo conocido, factibilidad, gap relativo, variabilidad y limitaciones.
- **Evidencia:** pruebas/experimentos y reporte reproducibles.
- **Reporte esperado:** `reports/PSO-03-reference-validation.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** aprobar si el harness usa fitness pura de prueba o la
  formulación penalizada actual; definir umbrales y solver permitido.

### Fase 4 — Validación financiera

#### PSO-04 — Validar convenciones de retornos y riesgo
- **Objetivo:** revisar retornos logarítmicos/simples, VaR, CVaR, signos,
  anualización, drawdown y frecuencia.
- **Justificación:** la auditoría identifica ambigüedades de interpretación.
- **Incluye:** casos manuales y decisiones de convención.
- **Excluye:** cambiar métricas sin aprobación.
- **Dependencias:** PSO-03 revisada.
- **Aceptación:** fórmulas, casos conocidos, frecuencia y signos documentados.
- **Evidencia:** pruebas y reporte.
- **Reporte esperado:** `reports/PSO-04-financial-conventions.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** decidir la semántica académica de CVaR y drawdown.

#### PSO-05 — Revisar el backtesting
- **Objetivo:** hacer explícitos ventana, buy-and-hold, costos, rebalanceo y
  supuestos del backtesting.
- **Justificación:** la fecha actual impide comparaciones congeladas.
- **Incluye:** revisión y pruebas de supuestos.
- **Excluye:** añadir estrategia financiera sin autorización.
- **Dependencias:** PSO-04 revisada.
- **Aceptación:** protocolo temporal y limitaciones documentados; métricas
  fuera de muestra reproducibles en una ventana fija.
- **Evidencia:** reporte y datos de prueba.
- **Reporte esperado:** `reports/PSO-05-backtesting-review.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** definir si habrá rebalanceo y costos.

### Fase 5 — Evaluación del modelo y función objetivo

#### PSO-06 — Analizar penalización y sensibilidad
- **Objetivo:** medir distancia al target y sensibilidad a penalty/restricciones.
- **Justificación:** la frontera actual es un problema penalizado.
- **Incluye:** diseño factorial o equivalente y análisis de error.
- **Excluye:** declarar frontera clásica o cambiar ecuaciones sin aprobación.
- **Dependencias:** PSO-03 y PSO-04 revisadas.
- **Aceptación:** trade-offs, rango de targets y sensibilidad reportados.
- **Evidencia:** experimentos multi-seed y reporte.
- **Reporte esperado:** `reports/PSO-06-penalty-sensitivity.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** decidir si se estudiará también una restricción exacta.

### Fase 6 — Experimentos y dashboard

#### PSO-07 — Diseñar experimentos reproducibles
- **Objetivo:** fijar matrices, ventanas, semillas, configuraciones y formato
  de resultados.
- **Justificación:** convertir pruebas aisladas en protocolo académico.
- **Incluye:** plan experimental y esquema de datos.
- **Excluye:** interpretar resultados antes de validar el protocolo.
- **Dependencias:** PSO-05 y PSO-06 revisadas.
- **Aceptación:** protocolo ejecutable, semillas y criterios estadísticos
  definidos.
- **Evidencia:** documento y reporte.
- **Reporte esperado:** `reports/PSO-07-experiment-design.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** definir tamaño de muestra y benchmark.

#### PSO-08 — Visualizar evidencia validada
- **Objetivo:** mostrar convergencia, diversidad y resultados financieros ya
  validados.
- **Justificación:** evitar que la interfaz sugiera conclusiones no probadas.
- **Incluye:** visualizaciones y etiquetas sustentadas por métricas validadas.
- **Excluye:** rediseño general de UI o cambios de algoritmo.
- **Dependencias:** PSO-02, PSO-04 y PSO-07 revisadas.
- **Aceptación:** gráficos trazables a datos persistidos y etiquetas
  consistentes con las convenciones aprobadas.
- **Evidencia:** pruebas de datos/gráficos y reporte.
- **Reporte esperado:** `reports/PSO-08-validated-dashboard.md`.
- **Estado:** pendiente.
- **Riesgos/decisiones:** decidir qué resultados se consideran aptos para
  publicación académica.
