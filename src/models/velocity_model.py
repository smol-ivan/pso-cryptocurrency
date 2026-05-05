from abc import ABC, abstractmethod
from random import random

import numpy as np

from .particle import Particle


class VelocityModel(ABC):
    @abstractmethod
    def update(self, particle: Particle, best_reference_position: np.ndarray) -> None:
        """Update particle velocity and position."""
        pass


class Inertia(VelocityModel):
    def __init__(self, c1: float = 0.5, c2: float = 1.0, inertia: float = 0.8) -> None:
        self.c1 = c1
        self.c2 = c2
        self.inertia = inertia

    def update(self, particle: Particle, best_reference_position: np.ndarray) -> None:
        r1, r2 = random(), random()

        new_velocity = (
            (self.inertia * particle.velocity)
            + (self.c1 * r1 * (particle.best_pos - particle.position))
            + (self.c2 * r2 * (best_reference_position - particle.position))
        )

        particle.velocity = new_velocity
        new_position = particle.position + particle.velocity

        # Keep non-negative portfolio weights and enforce sum(weights) = 1.
        new_position = np.maximum(0, new_position)
        total_weight = np.sum(new_position)
        if total_weight > 0:
            new_position /= total_weight

        particle.position = new_position
