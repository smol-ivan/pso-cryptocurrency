import argparse

import numpy as np

from crypto_data import *
from pso import OptimizationMode, pso
from utils import *


def main():
    parser = argparse.ArgumentParser(
        prog="psoCVaR",
        description="Portfolio Optimization using PSO with CVaR risk measure",
    )
    parser.add_argument("--n_swarm", "-n", default=100, type=int)
    parser.add_argument("--iter", "-i", default=200, type=int)
    parser.add_argument("--C1", type=float, default=0.5)
    parser.add_argument("--C2", type=float, default=0.5)

    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in OptimizationMode],
        default=OptimizationMode.MINIMIZE_RISK.value,
    )

    parser.add_argument("--target_value", type=float)

    parser.add_argument("--limits_return", action="store_true")
    parser.add_argument("--limits_risk", action="store_true")
    parser.add_argument("--save-result", action="store_true")
    parser.add_argument(
        "--returns-source",
        choices=["historical", "garch"],
        default="historical",
        help="Fuente de retornos usada por PSO",
    )
    parser.add_argument(
        "--n-scenarios",
        default=5000,
        type=int,
        help="Escenarios simulados por activo cuando --returns-source=garch",
    )
    parser.add_argument(
        "--garch-seed",
        type=int,
        default=None,
        help="Semilla para hacer reproducible la simulación GARCH",
    )

    args = parser.parse_args()

    # 🔹 Activos (por ahora fijos aquí)
    # assets = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "USDT-USD"]
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]

    # 🔹 Cargar retornos históricos
    mean_return, returns_matrix = load_crypto_returns(assets)

    if args.returns_source == "garch":
        mean_return, returns_matrix = simulate_garch_returns(
            returns_matrix,
            n_scenarios=args.n_scenarios,
            random_state=args.garch_seed,
        )

    if args.limits_return:
        get_limits_return_target(mean_return)
        return
    if args.limits_risk:
        get_limits_risk_target(returns_matrix)
        return

    if args.target_value is None:
        print("Error: --target_value se necesita para ejecutar el pso")
        print("Ignorar si se usta --limits_*")
        return

    best_fitness, best_position = pso(
        mean_return,
        returns_matrix,
        args.iter,
        args.n_swarm,
        OptimizationMode(args.mode),
        args.C1,
        args.C2,
        args.target_value,
    )

    # 🔹 Calcular métricas finales
    portfolio_returns = returns_matrix @ best_position
    portfolio_mean = portfolio_returns.mean()

    alpha = 0.95
    var_threshold = np.percentile(portfolio_returns, (1 - alpha) * 100)
    cvar = portfolio_returns[portfolio_returns <= var_threshold].mean()
    portfolio_risk = -cvar

    print("\n===== RESULTADOS =====")
    print(f"Mejor posicion: {best_position}")
    print(f"Retorno promedio: {portfolio_mean * 100:.2f}%")
    print(f"CVaR (95%): {portfolio_risk * 100:.2f}%")
    print(f"Suma de pesos: {best_position.sum():.4f}")

    if args.save_result:
        # Set last weights on the utils function so it can write the companion CSV
        try:
            from utils import save_result_csv as _save

            setattr(_save, "_last_weights", best_position.tolist())
        except Exception:
            pass

        save_result_csv(
            args.mode,
            args.target_value,
            portfolio_risk,
            portfolio_mean,
            args.returns_source,
        )


if __name__ == "__main__":
    main()
