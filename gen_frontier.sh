#!/bin/bash

# gen_frontier.sh: Generate efficient frontier and optionally run backtest
# Usage: ./gen_frontier.sh <mode> [returns_source] [--run-backtest] [--clean]
#   mode: minimize_risk | maximize_return
#   returns_source: historical | garch (default: historical)
#   --run-backtest: after generating frontier, run backtest pipeline
#   --clean: remove outputs/ (then exit)

MODE=$1
shift || true

RETURNS_SOURCE="historical"
RUN_BACKTEST=false
CLEAN=false

for arg in "$@"; do
    case "$arg" in
    historical | garch)
        RETURNS_SOURCE="$arg"
        ;;
    --run-backtest)
        RUN_BACKTEST=true
        ;;
    --clean)
        CLEAN=true
        ;;
    *)
        echo "Unknown option: $arg"
        echo "Usage: $0 <mode> [returns_source] [--run-backtest] [--clean]"
        exit 1
        ;;
    esac
done

if [ "$CLEAN" = true ]; then
    echo "Cleaning outputs/"
    rm -rf outputs/
    echo "Clean complete"
    exit 0
fi

if [ -z "$MODE" ]; then
    echo "Usage: $0 <mode> [returns_source] [--run-backtest] [--clean]"
    echo "Example: $0 minimize_risk historical --run-backtest"
    exit 1
fi

if [ "$MODE" != "minimize_risk" ] && [ "$MODE" != "maximize_return" ]; then
    echo "Error: mode must be 'minimize_risk' or 'maximize_return'"
    exit 1
fi

if [ "$RETURNS_SOURCE" != "historical" ] && [ "$RETURNS_SOURCE" != "garch" ]; then
    echo "Error: returns_source must be 'historical' or 'garch'"
    exit 1
fi

# Ensure we use virtualenv python if available
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
GARCH_SEED=42

echo "Generating frontier for mode=$MODE, returns_source=$RETURNS_SOURCE"
if [ "$RETURNS_SOURCE" = "garch" ]; then
    echo "Using fixed garch seed=$GARCH_SEED for reproducible frontier points"
fi

# Get limits
if [ "$MODE" = "minimize_risk" ]; then
    LIMITS=$($PYBIN main.py --limits_return --returns-source "$RETURNS_SOURCE" 2>/dev/null | grep -E "L_INF|L_SUP")
    TARGET_TYPE="return"
else
    LIMITS=$($PYBIN main.py --limits_risk --returns-source "$RETURNS_SOURCE" 2>/dev/null | grep -E "L_INF|L_SUP")
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

STEP=$(
    $PYBIN - <<EOF
L_INF = float("$L_INF")
L_SUP = float("$L_SUP")
NUM_POINTS = $NUM_POINTS
print((L_SUP - L_INF) / (NUM_POINTS - 1))
EOF
)

# Clear previous results (source-aware)
if [ "$MODE" = "minimize_risk" ]; then
    FILENAME="outputs/$RETURNS_SOURCE/results/min_return_crypto.csv"
    WEIGHTS_CSV="outputs/$RETURNS_SOURCE/results/min_return_crypto_weights.csv"
else
    FILENAME="outputs/$RETURNS_SOURCE/results/max_risk_crypto.csv"
    WEIGHTS_CSV="outputs/$RETURNS_SOURCE/results/max_risk_crypto_weights.csv"
fi

mkdir -p "$(dirname "$FILENAME")"

[ -f "$FILENAME" ] && rm "$FILENAME"
[ -f "$WEIGHTS_CSV" ] && rm "$WEIGHTS_CSV"

echo "Running $NUM_POINTS PSO optimizations..."

for ((i = 0; i < NUM_POINTS; i++)); do
    CURRENT=$(
        $PYBIN - <<EOF
L_INF = float("$L_INF")
STEP = float("$STEP")
i = $i
print(L_INF + i * STEP)
EOF
    )

    echo "  [$((i + 1))/$NUM_POINTS] Target=$CURRENT"

    EXTRA_ARGS=""
    if [ "$RETURNS_SOURCE" = "garch" ]; then
        EXTRA_ARGS="--garch-seed $GARCH_SEED"
    fi

    $PYBIN main.py \
        --mode "$MODE" \
        --returns-source "$RETURNS_SOURCE" \
        --target_value "$CURRENT" \
        --n_swarm $N_SWARM \
        --iter $ITER \
        --C1 $C1 \
        --C2 $C2 \
        --n-scenarios 5000 \
        $EXTRA_ARGS \
        --save-result >/dev/null 2>&1
done

echo "Done! Results saved to $FILENAME"

if [ "$RUN_BACKTEST" = true ]; then
    echo "Running backtest pipeline..."
    $PYBIN backtest.py \
        --weights-csv "$WEIGHTS_CSV" \
        --assets BTC-USD ETH-USD SOL-USD ADA-USD \
        --out "outputs/$RETURNS_SOURCE/results/backtest"
    echo "Backtest complete. Outputs in outputs/$RETURNS_SOURCE/results/backtest/"
fi

echo "All done."
