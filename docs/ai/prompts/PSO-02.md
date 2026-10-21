# PSO-02 — Instrumentación y diagnóstico de convergencia

Ejecuta **PSO-02 y solo PSO-02**.

## Contexto y documentación obligatoria

Lee primero:

- `AGENTS.md`
- `docs/ai/PROJECT_CONTEXT.md`
- `docs/ai/ROADMAP.md`
- `docs/ai/WORK_PROTOCOL.md`
- `reports/README.md`
- `reports/PSO-01-invariants-reproducibility.md`
- El reporte de revisión independiente de PSO-01.
- `reports/pso_validation_audit.md` y cualquier otro reporte directamente relacionado con la convergencia.

Verifica el estado real del repositorio, la rama activa, los cambios pendientes y las dependencias de PSO-02.

Confirma que PSO-01 esté implementada y revisada. Si no puedes verificarlo, detente y documenta qué evidencia falta.

No descartes ni sobrescribas cambios preexistentes. Distingue los cambios de esta tarea de los que ya estaban presentes.

## Objetivo

Instrumentar el algoritmo PSO para explicar empíricamente la evolución de la población y la causa de terminación de cada ejecución.

Investiga la convergencia aparentemente temprana observada en algunos experimentos, sin asumir que sea un defecto.

La prioridad es determinar qué está ocurriendo realmente antes de proponer cambios a la dinámica del algoritmo, a la función objetivo o al criterio de parada.

## 1. Diagnóstico inicial del flujo de ejecución

Antes de modificar código:

1. Localiza las rutas por las que se configuran y ejecutan PSO, desde los experimentos y la interfaz hasta el núcleo del optimizador.
2. Determina de dónde provienen `max_iterations`, `patience`, `atol` y `rtol`, qué valores reciben y cómo se propagan.
3. Identifica el criterio de parada implementado, el momento en que se evalúa y el significado exacto del contador de iteraciones.
4. Rastrea cómo se generan, almacenan, serializan, restauran y presentan los historiales.
5. Investiga por qué una ejecución podría mostrar una o dos iteraciones aunque el criterio de parada aparente requerir más evaluaciones.

No infieras una causa a partir de la interfaz o de una gráfica. Verifica el comportamiento en el código y, cuando sea posible, con una ejecución reproducible.

Distingue entre:
- Índice de la última iteración.
- Número de iteraciones ejecutadas.
- Número de registros en cada historial.
- Evaluaciones de la población.
- Iteraciones completadas antes de detenerse.

Documenta las diferencias que existan y cualquier inconsistencia observada.

## 2. Instrumentación por generación

Registra información suficiente para estudiar la evolución del algoritmo, sin almacenar trazas completas de todas las partículas si no son necesarias.

Incluye como mínimo:

### Fitness y convergencia
- Mejor fitness global histórico (`gbest`).
- Mejor fitness actual de la población.
- Media, mediana y desviación estándar del fitness actual.
- Media y dispersión de los mejores fitness personales.
- Mejora del mejor fitness global entre generaciones.
- Tolerancia aplicada y contador de paciencia.
- Número de iteración final y motivo explícito de terminación.

Aclara la diferencia entre fitness actual, mejor fitness personal y mejor fitness global. Documenta la convención de signo y qué significa una mejora en la implementación real.

### Diversidad y restricciones
- Diversidad de posiciones, con definición matemática documentada.
- Distancia máxima de las partículas al centroide, si resulta útil y su coste es razonable.
- Número de posiciones inválidas o no finitas.
- Mínimo y máximo de la suma de pesos.
- Número de posiciones que incumplen las restricciones.
- Frecuencia de reparaciones, únicamente si puede medirse sin alterar la dinámica del algoritmo.

Verifica qué representa cada métrica y en qué momento de la generación se calcula.

### Relación con el objetivo
Si la implementación permite obtener estas métricas sin modificar la función objetivo ni duplicar cálculos relevantes, registra para el mejor portafolio:
- Retorno medio.
- Riesgo utilizado por el modelo.
- Diferencia entre retorno obtenido y retorno objetivo.

No cambies las convenciones financieras existentes. Si estas métricas no pueden obtenerse de forma fiable o económica, documenta la limitación y déjalas fuera de esta fase.

No añadas métricas redundantes sin explicar qué hipótesis ayudan a comprobar.

## 3. Instrumentación y contrato de terminación

Distingue explícitamente entre, al menos:
- `patience`: terminación por falta de mejora según el criterio existente.
- `max_iterations`: terminación por alcanzar el límite de iteraciones.
- Error de validación u otra terminación excepcional, si corresponde.

Respeta el criterio de parada actual. No cambies sus condiciones, tolerancias, parámetros ni precedencia.

Si existen casos en los que varios criterios podrían cumplirse simultáneamente, documenta qué comportamiento establece el código actual.

Las trazas deben permitir reconstruir por qué terminó una ejecución, sin depender de inferencias basadas únicamente en la longitud de un historial.

## 4. Pruebas y ausencia de regresiones

Añade pruebas focalizadas para verificar:

- Forma, longitud y correspondencia de los historiales.
- Valores finitos y consistencia de las estadísticas registradas.
- Monotonicidad del mejor fitness global cuando corresponda según la implementación.
- Correspondencia entre el contador final y las iteraciones realmente ejecutadas.
- Distinción entre terminación por paciencia y por máximo de iteraciones.
- Comportamiento de los historiales en los límites de ejecución relevantes.
- Compatibilidad de los resultados persistidos y restaurados, o documentación explícita de cualquier migración necesaria.

Comprueba que la instrumentación no altere la trayectoria matemática de una corrida. Para una misma configuración y semilla, compara los resultados con la versión anterior cuando sea posible: pesos, fitness, actualizaciones relevantes e historiales existentes.

La instrumentación no debe introducir llamadas aleatorias adicionales ni modificar el estado de los generadores aleatorios. Ten presente la política de reproducibilidad establecida en PSO-01.

Si no es posible demostrar que una comparación es equivalente, explica por qué y delimita qué se pudo verificar.

## 5. Experimentos controlados

Después de validar la instrumentación, realiza una matriz inicial de experimentos reproducibles para estudiar la convergencia.

Incluye, en una escala razonable:

- Objetivos de retorno bajo, intermedio y alto, dentro de los valores admitidos por el proyecto.
- Ambas topologías disponibles.
- Ambos modelos de velocidad.
- Varias semillas independientes.
- Una población pequeña y otra de mayor tamaño.
- Un contraste de tolerancias, manteniendo constantes los demás parámetros.

Antes de ejecutar, documenta:
- Parámetros exactos.
- Semillas utilizadas.
- Número de repeticiones.
- Variables que cambian en cada comparación.
- Pregunta que responde cada experimento.

Empieza con una matriz reducida si la combinación completa resulta costosa. Justifica las selecciones y las limitaciones; no presentes una matriz parcial como si fuera exhaustiva.

No cambies arbitrariamente los parámetros predeterminados del proyecto ni la condición de parada. Los cambios experimentales deben ser explícitos y limitarse a la configuración de las ejecuciones.

## 6. Interpretación de resultados

Clasifica los resultados a partir de la evidencia registrada:

- Convergencia del mejor fitness global.
- Estabilización de los fitness actuales y personales.
- Pérdida de diversidad de posiciones.
- Reparaciones frecuentes o degeneración de posiciones.
- Sensibilidad a la semilla.
- Terminación por paciencia.
- Terminación por máximo de iteraciones.
- Posibles diferencias entre el comportamiento real y lo que muestra la interfaz.

Distingue hechos observados, hipótesis y conclusiones.

No concluyas que una convergencia rápida es incorrecta por sí sola. Tampoco aumentes iteraciones, cambies tolerancias ni modifiques ecuaciones para que las gráficas parezcan más interesantes.

Si la evidencia sugiere un defecto, documenta su reproducción y su impacto. Propón el cambio como una tarea posterior, sin implementarlo en PSO-02.

## 7. Alcance excluido

No cambies:
- La función objetivo, la penalización ni las convenciones financieras.
- Las ecuaciones o dinámica de PSO.
- Los modelos de velocidad o las topologías.
- Los parámetros predeterminados.
- Las tolerancias ni las condiciones de parada.
- La política de reparación de posiciones.
- La lógica de negocio o el diseño del dashboard.

Se permiten únicamente los cambios mínimos necesarios para instrumentar, probar y exponer las nuevas trazas en los resultados experimentales.

No añadas dependencias sin autorización. No realices refactorizaciones ajenas al objetivo.

## 8. Reporte y roadmap

Crea `reports/PSO-02-convergence-diagnostics.md`, siguiendo `reports/README.md`.

El reporte debe incluir:
- Estado inicial del repositorio y alcance realizado.
- Rutas de ejecución y configuración verificadas.
- Instrumentación añadida y definición de cada métrica.
- Pruebas ejecutadas, comandos y resultados reales.
- Experimentos ejecutados, configuración y semillas.
- Tablas o gráficas cuando aporten evidencia.
- Explicación de la convergencia temprana sustentada en resultados.
- Diferencias entre pruebas exitosas, fallos encontrados y aspectos no verificados.
- Limitaciones y preguntas pendientes.
- Recomendaciones para la siguiente tarea, sin implementar cambios fuera de alcance.

Actualiza `docs/ai/ROADMAP.md` con el estado real de PSO-02 y sus dependencias. Deja explícitamente pendiente la revisión independiente.

No marques una prueba, experimento o revisión como completado si no existe evidencia verificable. No hagas commit sin autorización.

## Criterios de aceptación

PSO-02 se considera implementada cuando:
1. Se conoce y documenta el flujo real de configuración, ejecución y presentación de iteraciones.
2. Las trazas permiten distinguir la evolución del fitness, la diversidad y el motivo de terminación.
3. Existen pruebas de consistencia de las métricas y de los historiales.
4. Se ha comprobado que la instrumentación no altera la trayectoria de una corrida, o se documentan con precisión las limitaciones de esa comprobación.
5. Se ha ejecutado y documentado una matriz inicial de experimentos reproducibles.
6. El reporte y el roadmap reflejan exclusivamente el trabajo y la evidencia reales.

Al terminar, presenta un resumen de cambios, pruebas, experimentos, hallazgos, limitaciones y estado de la revisión independiente. No comiences PSO-03.
