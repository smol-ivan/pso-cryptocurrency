from collections.abc import Sequence

import numpy as np
import pandas as pd

from .experiments import ExperimentResult


def max_drawdown(portfolio_returns: np.ndarray) -> float:
    cumulative_returns = np.cumprod(1 + portfolio_returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - running_max) / running_max
    return float(-drawdowns.min())


def calculate_portfolio_metrics(
    returns_matrix: np.ndarray, weights: np.ndarray, cvar_alpha: float = 0.95
) -> dict[str, float]:
    """Calculate metrics for a single portfolio."""
    portfolio_returns = returns_matrix @ weights

    mean_return = float(portfolio_returns.mean())
    volatility = float(portfolio_returns.std())

    var_threshold = np.percentile(portfolio_returns, (1 - cvar_alpha) * 100)
    tail_losses = portfolio_returns[portfolio_returns <= var_threshold]
    cvar = float(-tail_losses.mean())

    sharpe_ratio = mean_return / volatility if volatility > 0 else 0.0

    return {
        "mean_return": mean_return,
        "cvar": cvar,
        "max_drawdown": max_drawdown(portfolio_returns),
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
    }


def build_metrics_dataframe(
    returns_matrix: np.ndarray,
    weights_list: list[np.ndarray],
    cvar_alpha: float,
    fitness_values: np.ndarray | None = None,
) -> pd.DataFrame:
    metrics_list = [
        calculate_portfolio_metrics(returns_matrix, weights, cvar_alpha=cvar_alpha)
        for weights in weights_list
    ]
    df_metrics = pd.DataFrame(metrics_list)
    if fitness_values is not None:
        df_metrics["fitness"] = fitness_values
    return df_metrics


def build_summary_dataframe(
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    comparison_mode: str,
    fixed_portfolio_index: int = 1,
) -> pd.DataFrame:
    summary_rows = []
    for experiment in experiments:
        df = metrics_by_config[experiment.config.name]
        if comparison_mode == "Best Sharpe":
            selected_idx = int(df["sharpe_ratio"].idxmax())
        else:
            selected_idx = fixed_portfolio_index - 1

        summary_rows.append(
            {
                "name": experiment.config.name,
                "objective": experiment.config.objective_name,
                "velocity": experiment.config.velocity_name,
                "topology": experiment.config.topology_name,
                "selected_portfolio": selected_idx + 1,
                "selected_target_return": float(experiment.frontier.target_values[selected_idx]),
                "selected_mean_return": float(df.loc[selected_idx, "mean_return"]),
                "selected_cvar": float(df.loc[selected_idx, "cvar"]),
                "selected_max_drawdown": float(df.loc[selected_idx, "max_drawdown"]),
                "selected_volatility": float(df.loc[selected_idx, "volatility"]),
                "selected_sharpe_ratio": float(df.loc[selected_idx, "sharpe_ratio"]),
                "selected_fitness": float(df.loc[selected_idx, "fitness"]),
            }
        )
    return pd.DataFrame(summary_rows)


def build_multi_point_dataframe(
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    selected_point_indices: Sequence[int],
) -> pd.DataFrame:
    points_rows = []
    for experiment in experiments:
        df_metrics = metrics_by_config[experiment.config.name]
        for point_index in selected_point_indices:
            idx = point_index - 1
            points_rows.append(
                {
                    "name": experiment.config.name,
                    "portfolio_index": point_index,
                    "target_return": float(experiment.frontier.target_values[idx]),
                    "mean_return": float(df_metrics.loc[idx, "mean_return"]),
                    "cvar": float(df_metrics.loc[idx, "cvar"]),
                    "max_drawdown": float(df_metrics.loc[idx, "max_drawdown"]),
                    "volatility": float(df_metrics.loc[idx, "volatility"]),
                }
            )

    return pd.DataFrame(points_rows)


def spaced_frontier_indices(total_points: int, count: int) -> list[int]:
    """Select indices distributed across the frontier, including endpoints."""
    if count <= 0 or total_points <= 0:
        return []

    count = min(count, total_points)
    if count == 1:
        return [0]

    spaced = np.linspace(0, total_points - 1, count)
    unique_indices = sorted({int(round(value)) for value in spaced})

    if len(unique_indices) < count:
        for idx in range(total_points):
            if idx not in unique_indices:
                unique_indices.append(idx)
            if len(unique_indices) == count:
                break
        unique_indices = sorted(unique_indices)

    return unique_indices


def annualized_return(daily_return: float, periods_per_year: int = 252) -> float:
    return (1 + daily_return) ** periods_per_year - 1


def build_weights_table(
    assets: list[str], weights: list[np.ndarray], selected_indices: list[int]
) -> pd.DataFrame:
    weights_data = {f"Port. {idx + 1}": weights[idx] for idx in selected_indices}
    return pd.DataFrame(weights_data, index=assets)
