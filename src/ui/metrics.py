import numpy as np
import pandas as pd


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
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
    }


def build_metrics_dataframe(
    returns_matrix: np.ndarray, weights_list: list[np.ndarray], cvar_alpha: float
) -> pd.DataFrame:
    metrics_list = [
        calculate_portfolio_metrics(returns_matrix, weights, cvar_alpha=cvar_alpha)
        for weights in weights_list
    ]
    return pd.DataFrame(metrics_list)


def top_sharpe_indices(df_metrics: pd.DataFrame, count: int) -> list[int]:
    if count <= 0:
        return []
    return df_metrics["sharpe_ratio"].nlargest(count).index.to_list()


def annualized_return(daily_return: float, periods_per_year: int = 252) -> float:
    return (1 + daily_return) ** periods_per_year - 1


def build_weights_table(
    assets: list[str], weights: list[np.ndarray], selected_indices: list[int]
) -> pd.DataFrame:
    weights_data = {f"Port. {idx + 1}": weights[idx] for idx in selected_indices}
    return pd.DataFrame(weights_data, index=assets)
