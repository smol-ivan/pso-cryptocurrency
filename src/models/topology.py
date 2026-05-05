from abc import ABC, abstractmethod
from typing import List

from .particle import Particle


class Topology(ABC):
    @abstractmethod
    def get_best_particle(self, particle_index: int, swarm: List["Particle"]) -> Particle:
        """Return the best particle in the local neighborhood."""
        pass


class RingTopology(Topology):
    def __init__(self, k_neighbors: int = 1) -> None:
        self.neighbors = k_neighbors

    def get_best_particle(self, particle_index: int, swarm: List["Particle"]) -> Particle:
        swarm_size = len(swarm)
        neighborhood: List[Particle] = []

        for offset in range(-self.neighbors, self.neighbors + 1):
            neighbor_index = (particle_index + offset) % swarm_size
            neighborhood.append(swarm[neighbor_index])

        best_neighbor = min(neighborhood, key=lambda particle: particle.best_val)
        return best_neighbor
