#!/bin/bash

# gen_frontier.sh: Generate efficient frontier for crypto CVaR version
# Usage: ./gen_frontier.sh <mode>
# Example: ./gen_frontier.sh minimize_risk

MODE=$1

if [ -z "$MODE" ]; then
    echo "Usage: $0 <mode>"
    echo "Example: $0 minimize_risk"
    exit 1
fi

# Validate mode
if [ "$MODE" != "minimize_risk" ] && [ "$MODE" != "maximize_return" ]; then
    echo "Error: mode must be 'minimize_risk' or 'maximize_return'"
    exit 1
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
    # LIMITS=$(python3 main.py --limits_return 2>/dev/null | grep -E "L_INF|L_SUP")
    LIMITS=$(python3 main.py --limits_return 2>/dev/null | grep -E "L_INF|L_SUP")
    TARGET_TYPE="return"
else
    LIMITS=$(python3 main.py --limits_risk 2>/dev/null | grep -E "L_INF|L_SUP")
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
    python3 - <<EOF
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

CURRENT=$L_INF
COUNT=1
for ((i = 0; i < NUM_POINTS; i++)); do
    CURRENT=$(
        python3 - <<EOF
L_INF = float("$L_INF")
STEP = float("$STEP")
i = $i
print(L_INF + i * STEP)
EOF
    )

    echo "  [$((i + 1))/$NUM_POINTS] Target=$CURRENT"

    python3 main.py \
        --mode "$MODE" \
        --target_value "$CURRENT" \
        --n_swarm $N_SWARM \
        --iter $ITER \
        --C1 $C1 \
        --C2 $C2 \
        --save-result >/dev/null 2>&1
done

echo "Done! Results saved to $FILENAME"
