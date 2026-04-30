from abc import ABC, abstractmethod
from typing import List

import numpy as np

from models.particle import Particle


class Topologia(ABC):
    @abstractmethod
    def get_best_particle(self, idx_particle: int, swarm: List["Particle"]):
        """Devuelve la posicion de la particula dentro del 'vecindario'"""
        pass


class TopologiaAnillo(Topologia):
    def __init__(self, k_vecinos: int = 1) -> np.ndarray:
        # k=1 particula solo habla con uno por izq y der
        self.k = k_vecinos

    def get_best_particle(self, idx_particle: int, swarm: List["Particle"]):
        n = len(swarm)
        vecindario = []

        for i in range(-self.k, self.k + 1):
            idx_vecino = (idx_particle + i) % n
            vecindario.append(swarm[idx_vecino])

        best_vecino = min(vecindario, key=lambda p: p.best_val)
        return best_vecino
