from abc import ABC, abstractmethod

import numpy as np


class FitnessFunction(ABC):
    @abstractmethod
    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        """Compute the fitness value of a particle."""
        pass


class CVaR(FitnessFunction):
    def __init__(self, alpha: float = 0.95, penalty: float = 50.0) -> None:
        self.alpha = alpha
        self.penalty = penalty

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        # Portfolio returns across all time periods.
        portfolio_returns = returns_matrix @ position
        var_threshold = np.percentile(portfolio_returns, (1 - self.alpha) * 100)
        tail_losses = portfolio_returns[portfolio_returns <= var_threshold]

        cvar = tail_losses.mean()
        expected_return = portfolio_returns.mean()

        # CVaR from returns is negative in loss tails; convert to positive risk.
        risk = -cvar

        # Trade-off: minimiza riesgo, pero considera distancia al target
        # Si retorno es exactamente el target, penalty = 0
        # Si se aleja, aumenta linealmente
        target_diff = abs(expected_return - target_value)
        fitness = risk + self.penalty * target_diff

        return fitness


class VaR(FitnessFunction):
    """Value at Risk (VaR) based fitness.

    Risk is computed as the (1-alpha) percentile of portfolio returns and converted
    to a positive number (higher = worse). The fitness trades off risk and distance
    from the target return using the same penalty formulation as CVaR.
    """
    def __init__(self, alpha: float = 0.95, penalty: float = 50.0) -> None:
        self.alpha = alpha
        self.penalty = penalty

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        portfolio_returns = returns_matrix @ position
        var_threshold = np.percentile(portfolio_returns, (1 - self.alpha) * 100)

        # Convert to positive risk (VaR is a negative return at the chosen quantile)
        risk = -var_threshold
        expected_return = portfolio_returns.mean()

        target_diff = abs(expected_return - target_value)
        fitness = float(risk + self.penalty * target_diff)
        return fitness


class Semivariance(FitnessFunction):
    """Semivariance-based fitness.

    Semivariance is computed as the mean squared negative deviations from the
    portfolio mean. It is returned as a positive risk measure.
    """
    def __init__(self, penalty: float = 50.0) -> None:
        self.penalty = penalty

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        portfolio_returns = returns_matrix @ position
        expected_return = portfolio_returns.mean()
        negative_dev = portfolio_returns[portfolio_returns < expected_return] - expected_return
        semivar = float(np.mean(negative_dev ** 2)) if negative_dev.size > 0 else 0.0

        target_diff = abs(expected_return - target_value)
        fitness = float(semivar + self.penalty * target_diff)
        return fitness


class Variance(FitnessFunction):
    """Variance-based fitness (population variance of portfolio returns)."""
    def __init__(self, penalty: float = 50.0) -> None:
        self.penalty = penalty

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        portfolio_returns = returns_matrix @ position
        var = float(np.var(portfolio_returns))
        expected_return = portfolio_returns.mean()

        target_diff = abs(expected_return - target_value)
        fitness = float(var + self.penalty * target_diff)
        return fitness


class MaxDrawdown(FitnessFunction):
    def __init__(self, penalty: float = 50.0) -> None:
        self.penalty = penalty

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        portfolio_returns = returns_matrix @ position
        expected_return = portfolio_returns.mean()

        cumulative_returns = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = -drawdowns.min()

        target_diff = abs(expected_return - target_value)
        fitness = float(max_drawdown + self.penalty * target_diff)
        return fitness
