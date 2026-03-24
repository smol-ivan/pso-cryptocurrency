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
  --n-scenarios 8000 \
  --garch-seed 42
```

> Recomendación: para comparar fronteras de manera consistente en GARCH, usa una semilla fija (`--garch-seed`) para que todos los puntos se evalúen sobre escenarios reproducibles.

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


## Opciones combinadas de `gen_frontier.sh`

El script de frontera soporta en simultáneo:

- `returns_source` (`historical` o `garch`)
- `--run-backtest` para ejecutar backtest al terminar PSO
- `--clean` para limpiar `outputs/` y salir
- uso automático de `./.venv/bin/python` cuando existe

Ejemplos:

```bash
# Frontera + backtest usando histórico
./gen_frontier.sh minimize_risk historical --run-backtest

# Frontera + backtest usando garch
./gen_frontier.sh maximize_return garch --run-backtest

# Limpiar salidas
./gen_frontier.sh minimize_risk --clean
```


## Reproducibilidad del PSO

Para que la frontera sea menos ruidosa entre targets, puedes fijar semilla y usar reinicios:

```bash
python main.py --mode minimize_risk --target_value 0.001 --pso-seed 1234 --restarts 5
```

`gen_frontier.sh` ya envía estos parámetros por defecto para estabilizar la frontera.
