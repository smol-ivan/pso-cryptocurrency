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
    def __init__(self, alpha: float = 0.95, penalty: float = 1e6) -> None:
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

        fitness = risk

        if expected_return < target_value:
            diff = target_value - expected_return
            fitness += self.penalty * (diff**2)

        return fitness
