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
