from pathlib import Path

import numpy as np


def get_output_dirs(returns_source):
    base_dir = Path("outputs") / returns_source
    results_dir = base_dir / "results"
    graphs_dir = base_dir / "graficas"

    results_dir.mkdir(parents=True, exist_ok=True)
    graphs_dir.mkdir(parents=True, exist_ok=True)

    return results_dir, graphs_dir


def get_limits_return_target(mean_return):
    minimum = mean_return.min()
    maximum = mean_return.max()
    print(f"L_INF={minimum}")
    print(f"L_SUP={maximum}")


def get_limits_risk_target(returns_matrix, alpha=0.95):
    """
    Calcula límites aproximados de CVaR
    usando portafolios extremos (100% en cada activo)
    """

    n_assets = returns_matrix.shape[1]

    cvars = []

    for i in range(n_assets):
        w = np.zeros(n_assets)
        w[i] = 1.0

        portfolio_returns = returns_matrix @ w
        var_threshold = np.percentile(portfolio_returns, (1 - alpha) * 100)
        cvar = portfolio_returns[portfolio_returns <= var_threshold].mean()

        risk = -cvar  # convertir a positivo
        cvars.append(risk)

    minimum = min(cvars)
    maximum = max(cvars)

    print(f"L_INF={minimum}")
    print(f"L_SUP={maximum}")


def save_result_csv(mode, target_value, risk, portfolio_return, returns_source):
    """
    Guarda resultados en CSV (ahora sin data_file)
    """

    results_dir, _ = get_output_dirs(returns_source)

    if mode == "minimize_risk":
        filename = results_dir / "min_return_crypto.csv"
    else:
        filename = results_dir / "max_risk_crypto.csv"

    file_exists = filename.exists()

    with open(filename, "a") as f:
        if not file_exists:
            f.write("target_value,risk,return\n")

        f.write(f"{target_value},{risk},{portfolio_return}\n")
