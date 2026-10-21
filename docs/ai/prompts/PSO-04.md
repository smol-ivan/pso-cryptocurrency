# PSO-04 — Validación de convenciones financieras

## Rol y objetivo

Actúa como agente de auditoría técnica y matemática de un proyecto académico de optimización de portafolios de criptomonedas mediante Particle Swarm Optimization (PSO).

El objetivo es auditar las convenciones financieras que utiliza actualmente el proyecto, verificar las implementaciones con casos manuales reproducibles y documentar las decisiones necesarias para interpretar correctamente los resultados.

Esta tarea continúa el roadmap después de PSO-03, cuya implementación y revisión independiente fueron aprobadas con observaciones.

**No se busca modificar todavía las métricas financieras ni cambiar la formulación del problema.** Primero hay que establecer con evidencia qué calcula el sistema y qué significa cada resultado.

## 1. Preparación y protocolo obligatorio

Antes de modificar archivos:

1. Lee `AGENTS.md`.
2. Lee `docs/ai/PROJECT_CONTEXT.md`, `docs/ai/ROADMAP.md` y `docs/ai/WORK_PROTOCOL.md`.
3. Consulta `docs/ai/prompts/README.md`, `reports/README.md` y las plantillas de tareas o reportes pertinentes.
4. Revisa los reportes de PSO-03 y su revisión independiente, además de los reportes previos relevantes para la función objetivo y la generación de retornos.
5. Inspecciona el estado actual de Git, incluidos los archivos modificados, no rastreados y commits existentes.

Respeta los cambios previos del usuario y del proyecto. No descartes, sobrescribas ni reformatees cambios ajenos a esta tarea.

Si los documentos establecen un protocolo específico que difiere de estas instrucciones, identifica la diferencia y sigue el protocolo del repositorio.

## 2. Alcance de la auditoría

Inspecciona el código fuente real y sigue el flujo desde la obtención de precios hasta el cálculo de retornos, las métricas financieras, la función objetivo y los resultados que consume la interfaz.

Como mínimo, revisa los siguientes puntos.

### A. Retornos

Determina con precisión:

- Cómo se obtienen los precios y qué tratamiento reciben los valores faltantes.
- Si los retornos son logarítmicos, simples o ambos.
- Las fórmulas utilizadas y el orden de las operaciones.
- Qué representa un retorno de un portafolio y cómo se construye a partir de los retornos de los activos y sus pesos.
- Qué frecuencia tienen los datos: diaria, semanal u otra.
- Si los retornos se expresan por observación, se anualizan o se convierten a otra escala.
- Si se mezclan magnitudes o frecuencias incompatibles en algún punto.

Comprueba especialmente si el rendimiento objetivo y el rendimiento reportado tienen exactamente la misma definición y frecuencia.

No des por hecho que el uso de retornos logarítmicos implica que el rendimiento de un portafolio puede interpretarse automáticamente como un retorno simple.

### B. VaR y CVaR

Inspecciona la implementación completa, incluida `src/pso/fitness_function.py` y cualquier clase, función o interfaz que configure estas métricas.

Documenta:

- Qué representa `alpha` y cómo se transforma en el percentil utilizado.
- Si se trabaja con retornos o pérdidas y cuál es el signo de cada magnitud.
- Cómo se selecciona la cola de la distribución.
- Cómo se calcula VaR, si está implementado.
- Cómo se calcula CVaR, incluyendo el tratamiento de observaciones iguales al umbral.
- Qué sucede si la cola seleccionada contiene observaciones repetidas en el umbral.
- Si el cálculo corresponde a una convención empírica reconocible y qué diferencias existen con otras convenciones.
- Cómo se transforma CVaR en la magnitud de riesgo utilizada por la función objetivo.

Distingue cuidadosamente entre:
- CVaR expresado como retorno medio de la cola inferior.
- CVaR expresado como pérdida positiva.
- Riesgo definido como el negativo del retorno medio de la cola.

No los trates como términos intercambiables sin explicar la convención.

Verifica también si el nombre de la métrica, su implementación y su presentación en la interfaz son consistentes.

### C. Drawdown y Maximum Drawdown

Determina si estas métricas están implementadas actualmente, si aparecen únicamente en documentación o si no existen en el código.

Si están implementadas, verifica:

- Cómo se construye la curva de capital o riqueza.
- Si utiliza precios, retornos simples o retornos logarítmicos.
- Cómo se calcula el máximo histórico o máximo acumulado.
- La fórmula del drawdown y del Maximum Drawdown.
- Los signos, unidades y rangos posibles del resultado.
- Si se presupone una inversión buy-and-hold, pesos fijos o rebalanceo.

Si no están implementadas, documenta su ausencia sin crear una implementación nueva.

No añadas una métrica nueva como parte de esta tarea.

### D. Anualización y frecuencia

Identifica todas las conversiones de frecuencia o anualización que realmente ocurren en el proyecto.

Para cada una, documenta:

- Magnitud de entrada.
- Fórmula aplicada.
- Frecuencia asumida.
- Magnitud de salida.
- Justificación o limitaciones de esa convención.

Distingue entre anualizar una media de retornos logarítmicos, convertirla a una tasa de rendimiento simple y anualizar volatilidad. No supongas que todas estas operaciones utilizan la misma fórmula.

Si no existe anualización, indícalo expresamente. No introduzcas factores anuales nuevos por conveniencia.

## 3. Casos manuales y pruebas

Crea pruebas pequeñas e independientes que permitan comprobar las convenciones actuales con resultados calculables a mano.

Incluye, cuando sea pertinente:

1. **Retornos:** una serie pequeña de precios positivos cuyo retorno simple y logarítmico puedan calcularse manualmente.
2. **Conversión de retornos:** comprobar la relación entre retorno logarítmico y simple para una observación.
3. **VaR/CVaR:** una serie corta con retornos positivos y negativos, un `alpha` conocido y una cola fácil de verificar.
4. **Empates en el umbral:** comprobar qué observaciones entran en la cola cuando varios valores son iguales al percentil.
5. **Signos:** confirmar qué valor se considera pérdida positiva y cómo se transforma en riesgo dentro de la función objetivo.
6. **Drawdown:** si ya existe la implementación, una curva de capital pequeña que contenga un máximo, una caída y una recuperación parcial.
7. **Frecuencia y anualización:** si existen conversiones, verificar sus resultados con ejemplos numéricos sencillos.

Cada prueba debe especificar:
- Datos de entrada.
- Resultado esperado calculado independientemente.
- Resultado obtenido por el código.
- Criterio de aceptación.
- Convención que está verificando.

No construyas las expectativas llamando a la misma función que se está probando.

Las pruebas deben comprobar el comportamiento real del proyecto, no imponer silenciosamente una convención financiera alternativa. Si una implementación contradice la convención elegida para el caso de prueba, documenta la discrepancia y determina si es un error, una diferencia convencional o una decisión aún no resuelta.

## 4. Relación con la función objetivo y el optimizador

Examina cómo las convenciones financieras alimentan la función objetivo actual:

`fitness = risk + penalty * abs(expected_return - target_return)`

Confirma la expresión real en el código y señala cualquier diferencia.

Documenta las unidades y la interpretación de cada término, incluyendo:

- Riesgo calculado.
- Rendimiento esperado.
- Rendimiento objetivo.
- Distancia absoluta al objetivo.
- Penalización.
- Fitness resultante.

Comprueba si ambos términos que se suman son comparables en escala y qué implicaciones tiene esto para interpretar la penalización.

**No concluyas que una penalización concreta es adecuada o inadecuada solo por su valor numérico.** Esta tarea debe aclarar las magnitudes que intervienen; el estudio experimental de sensibilidad corresponde a PSO-06.

No cambies el algoritmo PSO, los parámetros, la penalización ni el intervalo de objetivos.

## 5. Decisiones que deben quedar explícitas

Entrega una tabla de decisiones con, como mínimo, estas columnas:

- Tema.
- Convención que usa actualmente el proyecto.
- Evidencia en código o pruebas.
- Alternativas relevantes.
- Consecuencia académica o interpretativa.
- Estado: confirmado, discrepancia detectada o requiere aprobación del usuario.

Presta especial atención a las decisiones que no deben tomarse unilateralmente:

- Convención académica de VaR/CVaR y significado de `alpha`.
- Uso de retornos logarítmicos o simples en cada etapa.
- Frecuencia de los objetivos y resultados.
- Si se necesita anualización y para qué magnitudes.
- Convención de drawdown, si corresponde.
- Cualquier discrepancia entre las ecuaciones documentadas, el código y las etiquetas de la interfaz.

Puedes recomendar una convención con argumentos matemáticos y académicos, pero no cambies la formulación vigente sin autorización.

## 6. Restricciones

No realices ninguna de estas acciones en PSO-04:

- Cambiar la función objetivo o las ecuaciones financieras en producción.
- Cambiar `alpha`, `penalty`, parámetros del PSO o generación de objetivos.
- Cambiar el uso de retornos logarítmicos por retornos simples, o viceversa.
- Añadir VaR, CVaR, drawdown o anualización si no están implementados.
- Modificar el backtesting, introducir costos o diseñar reglas de rebalanceo.
- Rediseñar la interfaz.

