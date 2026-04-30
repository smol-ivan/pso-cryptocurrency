from abc import ABC, abstractmethod

import numpy as np


class FuncionObjetivo(ABC):
    @abstractmethod
    def evaluar(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        """Calcular el valor fitness de una particula"""
        pass


class CVaR(FuncionObjetivo):
    def __init__(self, alpha: float = 0.95, penalty: float = 1e6) -> None:
        self.alpha = alpha
        self.penalty = penalty

    def evaluar(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:

        # Retornos del portafolio para todos los dias
        portafolio_returns = returns_matrix @ position

        # VaR (Percentil de la cola izquierda)
        var_threshold = np.percentile(portafolio_returns, (1 - self.alpha) * 100)

        # Cola de perdidas
        tails_losses = portafolio_returns[portafolio_returns <= var_threshold]

        # CVaR = promedio de la cola
        cvar = tails_losses.mean()
        p_return = portafolio_returns.mean()

        # CVaR es negativo (maneja perdidas)
        risk = -cvar

        fitness = risk

        if p_return < target_value:
            diff = target_value - p_return
            fitness += self.penalty * (diff**2)

        return fitness
