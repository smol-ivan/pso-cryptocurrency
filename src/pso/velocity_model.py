from abc import ABC, abstractmethod
from random import Random

import numpy as np

from .particle import Particle


class VelocityModel(ABC):
    def __init__(self, random_generator: Random | None = None) -> None:
        self._random_generator = random_generator or Random()

    def set_random_generator(self, random_generator: Random) -> None:
        self._random_generator = random_generator

    @abstractmethod
    def update(self, particle: Particle, best_reference_position: np.ndarray) -> None:
        """Update particle velocity and position."""
        pass


def _repair_position(position: np.ndarray) -> np.ndarray:
    position = np.asarray(position, dtype=float)
    if position.ndim != 1 or position.size == 0:
        raise ValueError("Position must be a non-empty one-dimensional vector.")
    if not np.all(np.isfinite(position)):
        raise ValueError("Position must contain only finite values.")

    repaired = np.maximum(0, position)
    total_weight = np.sum(repaired)
    if total_weight > 0:
        return repaired / total_weight
    return np.full(position.shape, 1.0 / position.size, dtype=float)


class Inertia(VelocityModel):
    def __init__(self, c1: float = 0.5, c2: float = 1.0, inertia: float = 0.8) -> None:
        super().__init__()
        self.c1 = c1
        self.c2 = c2
        self.inertia = inertia

    def update(self, particle: Particle, best_reference_position: np.ndarray) -> None:
        r1, r2 = self._random_generator.random(), self._random_generator.random()

        new_velocity = (
            (self.inertia * particle.velocity)
            + (self.c1 * r1 * (particle.best_pos - particle.position))
            + (self.c2 * r2 * (best_reference_position - particle.position))
        )

        particle.velocity = new_velocity
        particle.position = _repair_position(particle.position + particle.velocity)


class Constriction(VelocityModel):
    def __init__(self, c1: float = 2.05, c2: float = 2.05) -> None:
        super().__init__()
        self.c1 = c1
        self.c2 = c2
        phi = self.c1 + self.c2
        if phi <= 4:
            raise ValueError("Constriction model requires c1 + c2 > 4.")
        self.chi = 2 / abs(2 - phi - np.sqrt(phi**2 - 4 * phi))

    def update(self, particle: Particle, best_reference_position: np.ndarray) -> None:
        r1, r2 = self._random_generator.random(), self._random_generator.random()
        cognitive = self.c1 * r1 * (particle.best_pos - particle.position)
        social = self.c2 * r2 * (best_reference_position - particle.position)
        new_velocity = self.chi * (particle.velocity + cognitive + social)

        particle.velocity = new_velocity
        particle.position = _repair_position(particle.position + particle.velocity)
