#!/bin/bash

# gen_frontier.sh: Generate efficient frontier for crypto CVaR version
# Usage: ./gen_frontier.sh <mode>
# Example: ./gen_frontier.sh minimize_risk

#!/bin/bash

# gen_frontier.sh: Generate efficient frontier and optionally run backtest
# Usage: ./gen_frontier.sh <mode> [--run-backtest] [--clean]
#   mode: minimize_risk | maximize_return
#   --run-backtest: after generating frontier, run backtest pipeline
#   --clean: remove results/ and graficas/ (then exit)

MODE=$1
shift || true

RUN_BACKTEST=false
CLEAN=false

for arg in "$@"; do
    case "$arg" in
        --run-backtest)
            RUN_BACKTEST=true
            ;;
        --clean)
            CLEAN=true
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

if [ "$CLEAN" = true ]; then
    echo "Cleaning results/ and graficas/"
    rm -rf results/ graficas/
    echo "Clean complete"
    exit 0
fi

if [ -z "$MODE" ]; then
    echo "Usage: $0 <mode> [--run-backtest] [--clean]"
    echo "Example: $0 minimize_risk --run-backtest"
    exit 1
fi

# Validate mode
if [ "$MODE" != "minimize_risk" ] && [ "$MODE" != "maximize_return" ]; then
    echo "Error: mode must be 'minimize_risk' or 'maximize_return'"
    exit 1
fi

# Ensure we use the virtualenv python if available
if [ -d ".venv/bin" ]; then
    PYBIN="$(pwd)/.venv/bin/python"
else
    PYBIN="python3"
fi

# PSO parameters
N_SWARM=100
ITER=200
C1=1.7
C2=1.7
NUM_POINTS=50

echo "Generating frontier for mode=$MODE (crypto CVaR version)"

# Get limits
if [ "$MODE" = "minimize_risk" ]; then
    LIMITS=$($PYBIN main.py --limits_return 2>/dev/null | grep -E "L_INF|L_SUP")
    TARGET_TYPE="return"
else
    LIMITS=$($PYBIN main.py --limits_risk 2>/dev/null | grep -E "L_INF|L_SUP")
    TARGET_TYPE="risk"
fi

# Parse limits
L_INF=$(echo "$LIMITS" | grep "L_INF" | awk -F= '{print $2}')
L_SUP=$(echo "$LIMITS" | grep "L_SUP" | awk -F= '{print $2}')

if [ -z "$L_INF" ] || [ -z "$L_SUP" ]; then
    echo "Error: could not parse limits"
    exit 1
fi

echo "Target $TARGET_TYPE limits: $L_INF to $L_SUP"

STEP=$($PYBIN - <<EOF
L_INF = float("$L_INF")
L_SUP = float("$L_SUP")
NUM_POINTS = $NUM_POINTS
print((L_SUP - L_INF) / (NUM_POINTS - 1))
EOF
)

# Clear previous results
if [ "$MODE" = "minimize_risk" ]; then
    FILENAME="results/min_return_crypto.csv"
else
    FILENAME="results/max_risk_crypto.csv"
fi

if [ -f "$FILENAME" ]; then
    rm "$FILENAME"
fi

echo "Running $NUM_POINTS PSO optimizations..."

for ((i = 0; i < NUM_POINTS; i++)); do
    CURRENT=$($PYBIN - <<EOF
L_INF = float("$L_INF")
STEP = float("$STEP")
i = $i
print(L_INF + i * STEP)
EOF
    )

    echo "  [$((i + 1))/$NUM_POINTS] Target=$CURRENT"

    $PYBIN main.py \
        --mode "$MODE" \
        --target_value "$CURRENT" \
        --n_swarm $N_SWARM \
        --iter $ITER \
        --C1 $C1 \
        --C2 $C2 \
        --save-result >/dev/null 2>&1
done

echo "Done! Results saved to $FILENAME"

if [ "$RUN_BACKTEST" = true ]; then
    echo "Running backtest pipeline..."
    if [ "$MODE" = "minimize_risk" ]; then
        WEIGHTS_CSV="results/min_return_crypto_weights.csv"
    else
        WEIGHTS_CSV="results/max_risk_crypto_weights.csv"
    fi

    $PYBIN backtest.py --weights-csv "$WEIGHTS_CSV" --assets BTC-USD ETH-USD SOL-USD ADA-USD --out results/backtest
    echo "Backtest complete. Outputs in results/backtest/"
fi

echo "All done."
