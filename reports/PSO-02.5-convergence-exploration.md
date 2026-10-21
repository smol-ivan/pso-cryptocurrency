# PSO-02.5 — Exploración diagnóstica de convergencia (pre-PSO-03)

## Identificación y propósito

- **ID informal:** PSO-02.5 (exploración previa a PSO-03; no tarea formal del roadmap)
- **Fecha:** 2026-10-21
- **Rama:** `main`
- **Objetivo:** hacer observable el comportamiento real del PSO antes de
  entrar a la validación con referencias sintéticas (PSO-03). No modifica
  `src/` ni tests existentes.
- **Motivación:** la hipótesis del usuario era que en configuraciones de bajo
  riesgo/poca ganancia el algoritmo "ya en la primera iteración encuentra el
  máximo global". Esta exploración busca caracterizar qué está pasando
  realmente y separar las causas posibles.

## Herramienta creada

`scripts/diagnose_convergence.py` — script standalone que:

- Ejecuta `pso()` con `return_diagnostics=True` en dos escenarios.
- Imprime tablas descriptivas por target: gbest, diversidad, movimiento,
  reparaciones, distancia al target, motivo de terminación.
- Muestra la progresión por etapas (N snapshots distribuidos) y flags
  automáticos de diagnóstico.
- Compara múltiples semillas para el mismo target.
- No toca tests ni `src/`.

Uso:
```
./.venv/bin/python scripts/diagnose_convergence.py --scenario synthetic
./.venv/bin/python scripts/diagnose_convergence.py --scenario realistic
./.venv/bin/python scripts/diagnose_convergence.py --scenario all
```

## Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `./.venv/bin/python scripts/diagnose_convergence.py --scenario synthetic` | OK, sin errores |
| `./.venv/bin/python scripts/diagnose_convergence.py --scenario realistic` | OK, sin errores |
| `./.venv/bin/python -m unittest discover -s tests -v` | **12/12 verdes** (sin regresión) |

## Hallazgos del escenario "realista" (200 obs × 4 activos)

### Caso target bajo (bajo riesgo / baja ganancia esperada)

El target mínimo corresponde a la media de retornos del activo menos rentable
de la matriz. Resultado con CVaR / Inertia / Global, seeds 10–50:

```
 Semilla     gbest_final   iters           motivo   div_final   mov_final
────────  ──────────────  ──────  ───────────────  ──────────  ──────────
      10      0.04280204      16         patience    0.000000    0.000000
      20      0.04280204      16         patience    0.000000    0.000000
      30      0.04280204      16         patience    0.000000    0.000000
      40      0.04280204      16         patience    0.000000    0.000000
      50      0.04280204      16         patience    0.000000    0.000000
```

**Observaciones respaldadas:**

1. **`gbest` idéntico en todas las semillas.** Todas convergen al mismo valor
   `0.04280204` independientemente de la semilla. Esto no es robustez — es una
   señal de que el espacio de búsqueda tiene una solución trivialmente
   dominante para ese target.

2. **Colapso total de diversidad (div_final = 0.0).** La población entera
   colapsa en un único punto del simplex. Movimiento también cero. El algoritmo
   no está explorando en absoluto después del colapso.

3. **Solo 16 iteraciones.** La barrera de las 6 iteraciones de gracia impide
   que termine antes (patience no cuenta hasta iter > 5), pero el gbest deja
   de mejorar prácticamente desde el principio. La progresión muestra que la
   mejora ocurre entre iter 0 y ~3, y después el gbest es plano.

4. **El mismo comportamiento se repite en el target alto** para CVaR/Constriction/Ring:
   gbest idéntico en todas las semillas, colapso total, 16 iteraciones.

### Causa más probable

La **penalización es tan dominante** para ciertos targets que cualquier
portafolio que minimice `penalty * |retorno_medio - target|` gana sin
importar la semilla. Con `penalty=50`, una diferencia de 0.01 en retorno
genera un costo de 0.5, mucho mayor que el riesgo puro (CVaR del orden de
0.02). El primer portafolio que "acierta" el target captura el mínimo y la
población colapsa hacia él.

Esto explica el comportamiento visto en Streamlit: **no es que el PSO encuentre
el óptimo global en la primera iteración — es que la penalización domina el
espacio y hace trivial el problema para ese target.**

### Contraste con targets intermedios

Para targets en el medio del rango, el comportamiento es distinto:

- Más iteraciones (50–90 en el escenario realista).
- Diversidad que decrece gradualmente pero no llega a cero.
- Mejora sostenida de gbest durante varias etapas.
- Semillas producen gbest distintos (variabilidad real).

Esto sugiere que el algoritmo sí funciona razonablemente para targets donde
la penalización no domina absolutamente.

## Interpretación y limitaciones

- Esta exploración usa una matriz sintética fija (semilla 42), no datos reales
  de Yahoo Finance. Los patrones pueden diferir con datos de mercado.
- No se afirma que ningún valor sea óptimo financiero ni que la convergencia
  sea correcta matemáticamente.
- El colapso total (div=0, mov=0) debe distinguirse de la convergencia a un
  óptimo: aquí es concentración por dominancia de penalización, no prueba de
  que el portafolio encontrado sea el de mínimo riesgo real.
- La invariancia respecto de la semilla es una señal de diagnóstico, no un
  resultado financiero.

## Preguntas que quedan abiertas (para PSO-03)

1. ¿El portafolio al que colapsa es realmente el de mínima varianza long-only?
   PSO-03 lo comprobará con una referencia analítica.
2. ¿El colapso ocurre con datos de mercado reales (matriz de Streamlit)?
   Requiere ejecutar el script con retornos de Yahoo Finance.
3. ¿La penalización `lambda=50` es adecuada para el rango de retornos de
   criptomonedas? Pendiente para PSO-06.
4. ¿Qué pasa si se reduce la penalización o se elimina? No autorizado en este
   alcance.

## Siguiente paso

Avanzar a PSO-03 con este diagnóstico como contexto: el harness sintético
debe incluir un caso de mínima varianza long-only con solución analítica
conocida para verificar si el portafolio al que colapsa es correcto o no.
