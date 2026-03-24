# pso-cryptocurrency

Optimización de portafolio de criptomonedas con PSO bajo restricción/objetivo de CVaR.

## Ejecución

```bash
python main.py --mode minimize_risk --target_value 0.001
```

## Retornos históricos vs escenarios GARCH

Por defecto el PSO usa retornos históricos (`T x N`).  
Si se activa `--returns-source garch`, el flujo cambia a:

1. Descargar retornos históricos
2. Ajustar un GARCH(1,1) por activo
3. Simular `S` escenarios por activo
4. Usar la matriz simulada (`S x N`) dentro del PSO y del cálculo de CVaR

Ejemplo:

```bash
python main.py \
  --mode minimize_risk \
  --target_value 0.001 \
  --returns-source garch \
  --n-scenarios 8000
```

## Salidas separadas por modo

Los archivos ahora se organizan por fuente de retorno:

```text
outputs/
  historical/
    results/
    graficas/
  garch/
    results/
    graficas/
```

- Los CSV de optimización se guardan en `outputs/<returns_source>/results`.
- Las gráficas se guardan en `outputs/<returns_source>/graficas`.

## Automatización

### Ejecutar ambos modos (uno y luego el otro)

```bash
# 1) Histórico
./gen_frontier.sh minimize_risk historical
python graphit.py --returns-source historical

# 2) GARCH
./gen_frontier.sh minimize_risk garch
python graphit.py --returns-source garch
```

### Ejecutar solo un modo (por separado)

Solo histórico:

```bash
./gen_frontier.sh minimize_risk historical
python graphit.py --returns-source historical
```

Solo garch:

```bash
./gen_frontier.sh minimize_risk garch
python graphit.py --returns-source garch
```
