# PSO-02 — Instrumentación y diagnóstico experimental de convergencia

## Objetivo

Instrumentar y estudiar el comportamiento del algoritmo Particle Swarm Optimization (PSO) para determinar qué ocurre durante las ejecuciones en las que parece converger en muy pocas iteraciones.

La investigación debe distinguir entre:

- Mejora real del fitness y estabilización de su valor.
- Estancamiento del mejor fitness mientras las partículas continúan moviéndose.
- Pérdida de diversidad o concentración de la población.
- Poblaciones que mantienen diversidad, pero no encuentran mejores soluciones.
- Reparaciones frecuentes de posiciones.
- Terminación por paciencia, máximo de iteraciones u otra condición.
- Diferencias entre las iteraciones reales, las evaluaciones realizadas, el historial registrado y el contador que pueda mostrar la interfaz.

El objetivo es observar, medir y explicar antes de proponer cambios. Un fitness que deja de mejorar no demuestra por sí mismo que el algoritmo esté defectuoso ni que haya encontrado una solución óptima.

## 1. Lectura obligatoria y estado inicial

Antes de modificar archivos, lee:

- `AGENTS.md`.
- `docs/ai/PROJECT_CONTEXT.md`.
- `docs/ai/ROADMAP.md`.
- `docs/ai/WORK_PROTOCOL.md`.
- `reports/README.md`.
- El informe principal de PSO-01.
- El informe de revisión independiente de PSO-01.
- El informe de PSO-01.1, si ya fue implementado y revisado.
- Los informes anteriores que sean necesarios para comprender la función objetivo, la condición de parada y el flujo de experimentos.

Verifica la rama, el estado de Git, los cambios previos, los archivos sin seguimiento y las pruebas disponibles. Preserva el trabajo existente.

Confirma qué tareas están aprobadas, cuáles siguen pendientes de revisión y qué limitaciones deben considerarse antes de iniciar esta fase.

Si PSO-01.1 todavía no está aprobado, no asumas que sus cambios son definitivos. Registra las dependencias relevantes y evita duplicar o sobrescribir trabajo.

## 2. Auditar el flujo real de ejecución

Antes de instrumentar, sigue el flujo completo desde la configuración de la ejecución hasta el algoritmo y la presentación de sus resultados.

Identifica:

- Dónde se configuran `max_iterations`, `patience`, `atol` y `rtol`.
- Cómo llegan esos valores desde la configuración hasta el optimizador.
- En qué momento de cada iteración se evalúa la condición de parada.
- Qué significa exactamente una iteración en la implementación actual.
- Cuándo se evalúa el fitness y cuándo se actualizan los mejores valores personales y globales.
- Cómo se almacenan los historiales y cuándo se añade cada registro.
- Cómo se serializan, guardan y recuperan los resultados.
- Qué campo o cálculo utiliza Streamlit para mostrar el número de iteraciones.
- Si la interfaz muestra un índice, el número de registros, las iteraciones completadas o alguna otra cantidad.
- Si existen diferencias entre una ejecución individual y una ejecución dentro del sistema de experimentos.

Investiga específicamente las ejecuciones que aparentemente terminan en una o dos iteraciones. No atribuyas este comportamiento a una causa sin evidencia.

Distingue, cuando la información esté disponible, entre:

1. Iteraciones completadas.
2. Evaluaciones de fitness.
3. Registros de historial.
4. Iteración del último cambio significativo.
5. Iteración en la que se cumple la condición de parada.

No cambies todavía la condición de parada para prolongar las ejecuciones.

## 3. Definir una estructura de datos de diagnóstico

Antes de añadir numerosas variables al algoritmo, define qué información se necesita, en qué nivel se captura y para qué se utilizará.

Mantén una separación conceptual entre:

### A. Estado interno del PSO

Información necesaria para ejecutar el algoritmo, como posiciones, velocidades, mejores posiciones personales y mejor posición global.

No expongas automáticamente todo este estado en la interfaz ni lo persistas completo si su coste no lo justifica.

### B. Traza de diagnóstico por generación

Información que permite reconstruir y estudiar el comportamiento de una ejecución. Debe estar disponible mediante un contrato de datos estable y suficientemente claro para que una futura versión de Streamlit pueda consumirla sin depender de detalles internos del optimizador.

### C. Métricas derivadas

Estadísticas calculadas a partir de la traza para interpretar convergencia, diversidad, movimiento y terminación.

### D. Metadatos de la ejecución

Como mínimo, cuando estén disponibles:

- Identificador de ejecución.
- Semilla.
- Configuración efectiva utilizada.
- Modelo de velocidad y topología.
- Tamaño de la población.
- Número de activos.
- Parámetros de parada.
- Iteraciones completadas.
- Motivo de terminación.
- Versión del esquema de resultados, si se introduce un esquema versionado.

La estructura concreta debe seguir las convenciones existentes del proyecto. No introduzcas una arquitectura compleja, un sistema de eventos o dependencias nuevas si una estructura de datos sencilla resuelve el problema.

**Importante:** prepara los resultados para que puedan ser consumidos posteriormente por Streamlit y por herramientas de análisis. No rediseñes todavía el dashboard. Evita que las futuras gráficas tengan que reconstruir información a partir de variables privadas o mensajes de depuración.

Evalúa si conviene separar la captura de trazas completas de las métricas resumidas, para limitar el uso de memoria en experimentos grandes. Documenta la decisión y conserva la compatibilidad necesaria con los consumidores existentes.

## 4. Instrumentación por generación

Implementa las métricas siguientes cuando puedan calcularse de forma fiable con el estado disponible.

### 4.1. Evolución del fitness

Registra, con una convención temporal explícita y consistente:

- Mejor fitness histórico global (`gbest`).
- Mejor fitness de la población actual.
- Media, mediana y desviación estándar del fitness de la población actual.
- Media y dispersión del mejor fitness personal de las partículas (`pbest`).
- Mejora del mejor fitness histórico respecto a la generación anterior.
- Valor de tolerancia empleado por la condición de parada, cuando corresponda.
- Contador de paciencia acumulado.
- Última iteración en la que se produjo una mejora significativa.

Documenta si la implementación minimiza o maximiza el fitness y verifica la dirección de todas las comparaciones. No supongas que un fitness menor es siempre mejor sin comprobar el contrato existente.

No confundas el mejor valor histórico con el mejor valor de la población actual. Ambos pueden evolucionar de forma diferente.

### 4.2. Diversidad de posiciones

Define matemáticamente la métrica antes de implementarla.

Como mínimo, considera la distancia media de las posiciones de las partículas al centroide de la población:

\[
\bar{x}_t=\frac{1}{N}\sum_{i=1}^{N}x_{i,t}
\]

\[
D_t=\frac{1}{N}\sum_{i=1}^{N}
\left\|x_{i,t}-\bar{x}_t\right\|_2
\]

Aquí, cada \(x_{i,t}\) es el vector de pesos de una partícula en la generación \(t\), \(N\) es el tamaño de la población y la distancia se calcula en el espacio de los pesos del portafolio.

Añade, si resulta útil y tiene un coste razonable:

- Desviación estándar de los pesos por activo.
- Distancia máxima al centroide.
- Diversidad relativa respecto a la diversidad inicial, siempre que esta sea distinta de cero.

Documenta qué representa cada métrica, sus unidades, sus limitaciones y cómo se comporta cuando la población tiene una única partícula o todas las partículas ocupan la misma posición.

Estas métricas describen la dispersión de la población; no constituyen por sí solas una prueba de convergencia global ni de optimalidad.

### 4.3. Movimiento entre generaciones

La diversidad no es suficiente para saber si las partículas siguen explorando. Una población puede mantener una dispersión parecida mientras todas sus partículas se desplazan; también puede permanecer dispersa aunque apenas se mueva.

Por ello, mide el movimiento de las posiciones entre generaciones.

Considera como mínimo:

\[
M_t=\frac{1}{N}\sum_{i=1}^{N}
\left\|x_{i,t}-x_{i,t-1}\right\|_2
\]

Registra también el desplazamiento máximo de una partícula cuando sea útil.

Define claramente en qué punto de la iteración se captura cada posición. Las posiciones comparadas deben corresponder a fases equivalentes del algoritmo y respetar la política de reparación existente.

No añadas operaciones aleatorias ni alteres el orden de las llamadas al generador aleatorio para obtener estas métricas.

### 4.4. Restricciones y reparación

Siempre que pueda medirse sin modificar la dinámica, registra:

- Cantidad o frecuencia de reparaciones de posiciones.
- Presencia de valores no finitos en los puntos pertinentes.
- Número de partículas con pesos que incumplen las restricciones antes y después de la reparación, cuando ambos estados estén disponibles.
- Desviación mínima y máxima de la suma de pesos respecto a uno, o una estadística equivalente.
- Otros incumplimientos relevantes para el contrato de pesos.

Distingue entre una reparación que corrige una situación excepcional y una reparación que ocurre repetidamente. No concluyas que las reparaciones causan la convergencia prematura sin comprobarlo.

### 4.5. Interpretación financiera del mejor portafolio

Si los datos necesarios ya están disponibles y el cálculo es fiable, registra para el mejor portafolio:

- Rendimiento medio estimado.
- Medida de riesgo utilizada por el proyecto.
- Diferencia respecto al rendimiento objetivo.
- Componentes de la función objetivo que permitan interpretar su valor.

Utiliza exactamente las definiciones y convenciones financieras existentes. No introduzcas una fórmula nueva de riesgo ni cambies el cálculo financiero en esta tarea.

Si estos valores no pueden obtenerse sin ampliar el alcance, documenta qué falta y continúa con las métricas de convergencia que sí puedan medirse.

## 5. Motivo de terminación y semántica de los historiales

La ejecución debe permitir distinguir explícitamente entre, al menos:

- Terminación por paciencia o ausencia de mejora según el criterio actual.
- Terminación por alcanzar el máximo de iteraciones.
- Finalización por otro motivo existente, si aplica.
- Error o entrada inválida, sin presentarlos como una convergencia normal.

Conserva exactamente la condición de parada actual y su semántica. El propósito es registrar de forma explícita por qué terminó la ejecución, no cambiar cuándo termina.

Comprueba y documenta:

- La relación entre iteraciones completadas y longitud de cada historial.
- Si el historial incluye el estado inicial.
- Si los historiales de fitness, diversidad y movimiento tienen la misma longitud o necesitan convenciones diferentes.
- Qué ocurre en ejecuciones de frontera, como la terminación temprana o el tamaño mínimo permitido.
- Si los resultados antiguos pueden cargarse con seguridad y cómo se representan los campos que no existían.

No rellenes datos históricos ausentes con valores inventados. Si no es posible reconstruir una métrica de una ejecución antigua, represéntala como no disponible y documenta esa limitación.

No hagas una migración general de archivos `.psodata` si no es necesaria para cumplir este contrato. Primero identifica el formato real, sus consumidores y la compatibilidad que debe preservarse.

## 6. Pruebas y verificación de que la instrumentación no cambia el PSO

Añade pruebas automatizadas para verificar:

- Dimensiones, tipos y valores finitos de las métricas.
- Coherencia temporal y longitudes de los historiales.
- Monotonicidad del mejor fitness histórico conforme a la convención real de optimización.
- Cálculo de diversidad y movimiento en casos sencillos con resultados conocidos.
- Casos de diversidad nula, movimiento nulo y población mínima admitida.
- Correspondencia entre el motivo de terminación, el contador y las iteraciones completadas.
- Distinción entre terminación por paciencia y por máximo de iteraciones.
- Persistencia y recuperación de los resultados nuevos.
- Compatibilidad con datos anteriores cuando corresponda y existan fixtures o ejemplos verificables.

El registro de métricas no debe cambiar la trayectoria matemática del algoritmo.

Verifica esta propiedad comparando, con datos, configuración y semillas idénticos, la trayectoria de una versión anterior y la instrumentada cuando sea viable. Puedes utilizar una referencia temporal de la versión anterior sin alterar el trabajo actual.

Compara, cuando corresponda:

- Posiciones.
- Valores de fitness.
- Mejores posiciones personales y globales.
- Motivo y momento de terminación.

Si la comparación exacta no es viable, explica por qué, qué evidencia alternativa se utilizó y qué nivel de certeza permite obtener.

Asegúrate de que calcular estadísticas no consume números aleatorios adicionales ni modifica inadvertidamente el estado del algoritmo.

## 7. Diagnóstico experimental inicial

Después de implementar y probar la instrumentación, ejecuta un conjunto inicial de experimentos controlados. No es necesario realizar de inmediato una exploración factorial exhaustiva.

### Fase A: comportamiento base

Mantén fijos los datos, el objetivo de rendimiento y los parámetros restantes. Compara:

- Los modelos de velocidad existentes.
- Las topologías existentes.
- Varias semillas independientes y registradas.
- Una configuración de población de referencia y, si el coste lo permite, otra de mayor tamaño.

Selecciona los valores de configuración a partir de los valores existentes del proyecto. No inventes nuevos valores por defecto. Justifica la cantidad de semillas y el tamaño de las pruebas; si el coste computacional es alto, empieza con una matriz reducida y deja constancia de sus limitaciones.

### Fase B: sensibilidad controlada

A partir de los resultados de la fase A, modifica un factor a la vez cuando exista una pregunta concreta que responder. Considera:

- Distintos niveles de rendimiento objetivo que sean válidos para los datos utilizados.
- Una comparación entre los niveles actuales de tolerancia, únicamente como experimento de diagnóstico.
- Tamaño de población, si la fase A sugiere que la diversidad inicial o el número de partículas puede ser relevante.

No cambies los valores predeterminados del sistema ni sus criterios de parada. Las variaciones de tolerancia son configuraciones experimentales aisladas, no propuestas para modificar el algoritmo.

Registra para cada experimento la configuración efectiva, la semilla, la pregunta que pretende responder, el resultado observado y cualquier limitación. No selecciones solamente las ejecuciones que producen gráficas atractivas.

## 8. Cómo interpretar los resultados

Analiza explícitamente los siguientes escenarios:

1. **El fitness se estanca y las partículas continúan moviéndose.** Comprueba si las partículas exploran posiciones diferentes sin superar sus mejores soluciones personales o el mejor global.
2. **El fitness se estanca y la diversidad disminuye.** Evalúa si la población se concentra mientras deja de encontrar mejoras.
3. **El fitness se estanca, pero la diversidad permanece alta.** Considera si las partículas siguen explorando sin encontrar soluciones que mejoren el objetivo.
4. **El mejor fitness histórico mejora, pero el fitness de la población actual empeora o fluctúa.** Comprueba si la población actual y los mejores históricos están siendo registrados e interpretados correctamente.
5. **La ejecución termina antes de lo esperado.** Contrasta la condición de parada, la paciencia, la tolerancia, el contador y los historiales con los valores de configuración efectivos.
6. **Las ejecuciones con distintas semillas muestran comportamientos distintos.** Cuantifica la variabilidad observada sin asumir que toda diferencia entre semillas indica un defecto.
7. **Las reparaciones son frecuentes o la población presenta valores inválidos.** Determina si el comportamiento se explica por las restricciones, la inicialización o alguna ruta de actualización, sin cambiar todavía la política de reparación.

Separa claramente:

- Observaciones respaldadas por datos.
- Interpretaciones plausibles.
- Hipótesis todavía no comprobadas.
- Pruebas adicionales necesarias.

No declares que una ejecución ha encontrado el óptimo únicamente porque se haya estabilizado el fitness, se haya agotado la paciencia o haya terminado con un valor atractivo.

## 9. Preparación para el futuro dashboard de Streamlit

No rediseñes la interfaz ni implementes un panel de diagnóstico completo en esta tarea.

Sin embargo, asegúrate de que la información obtenida pueda consumirse desde una futura versión de Streamlit sin acoplar el dashboard a variables internas del optimizador.

Propón una separación entre:

- **Resultados principales:** configuración, estado final, pesos óptimos obtenidos, fitness y métricas financieras existentes.
- **Diagnóstico avanzado:** historiales por generación, fitness actual e histórico, diversidad, movimiento, reparaciones y motivo de terminación.
- **Datos de análisis:** resultados por ejecución y semilla, metadatos experimentales y datos suficientes para comparar configuraciones y estudiar la variabilidad.

La propuesta debe indicar qué información conviene conservar por generación, qué información puede calcularse a partir de la traza y qué información no es necesario persistir.

Considera memoria, tamaño de los historiales, compatibilidad de los resultados guardados y facilidad para comparar ejecuciones. Evita guardar repetidamente el estado completo de cada partícula si las métricas agregadas son suficientes para una pregunta concreta.

Si el proyecto ya cuenta con un contrato de resultados, amplíalo de forma compatible en vez de crear una vía paralela innecesaria. No introduzcas dependencias sin autorización.

## 10. Restricciones

No cambies:

- La función objetivo, su penalización ni las ecuaciones financieras.
- Las ecuaciones de movimiento del PSO.
- Los modelos de velocidad ni las topologías.
- Los valores predeterminados de configuración.
- La condición de parada, su tolerancia, la paciencia ni la política de reparación.
- La interpretación de los resultados financieros para favorecer una conclusión.
- El diseño general o la lógica funcional de Streamlit.

Puedes realizar los cambios mínimos necesarios para instrumentar, registrar y exponer los resultados de diagnóstico mediante el contrato de datos. Si detectas un posible defecto que requiere cambiar alguna regla excluida, documenta la evidencia, el impacto y una propuesta de corrección separada; no lo corrijas silenciosamente en esta tarea.

No comiences la siguiente fase de validación matemática o financiera.

## 11. Informe y entregables

Crea:

`reports/PSO-02-convergence-diagnostics.md`

El informe debe incluir:

1. Auditoría del flujo de ejecución y de la interpretación de las iteraciones.
2. Métricas instrumentadas y definiciones matemáticas.
3. Cambios realizados y estructura de datos elegida.
4. Resultados de las pruebas y comprobación de que la instrumentación no altera la trayectoria.
5. Matriz de experimentos, parámetros efectivos, semillas y comandos ejecutados.
6. Resultados y gráficas o tablas que aporten evidencia, si pueden generarse con las herramientas existentes.
7. Interpretación de los escenarios de convergencia y limitaciones.
8. Recomendación sobre qué información conservar para análisis y futura integración con Streamlit.
9. Riesgos pendientes y preguntas que deben pasar a la siguiente fase.

Actualiza `docs/ai/ROADMAP.md` con el estado real de PSO-02 y las tareas pendientes. Deja la revisión independiente explícitamente pendiente.

Ejecuta las pruebas pertinentes, las comprobaciones de sintaxis y `git diff --check`. Registra los comandos y sus resultados reales. Revisa el diff y preserva todos los cambios preexistentes.

No hagas commits sin autorización explícita.

## Criterios de aceptación

PSO-02 queda listo para revisión cuando:

- Se entiende cómo se determina y comunica el motivo de terminación.
- La diferencia entre iteraciones, historiales y evaluaciones está documentada.
- Las métricas de fitness, diversidad y movimiento están definidas y probadas.
- Los resultados distinguen estancamiento del fitness, pérdida de diversidad y movimiento de partículas.
- La instrumentación no cambia la trayectoria matemática del PSO, o sus limitaciones de verificación están explícitamente documentadas.
- Existe evidencia reproducible de un conjunto inicial de experimentos.
- Los resultados pueden consumirse mediante una estructura de datos documentada y preparada para el futuro dashboard.
- Se han separado las conclusiones respaldadas por evidencia de las hipótesis pendientes.

No avances a la validación matemática ni modifiques el algoritmo para forzar más iteraciones. Entrega el informe y deja la revisión independiente pendiente.
