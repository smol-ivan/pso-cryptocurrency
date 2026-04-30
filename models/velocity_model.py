from abc import ABC, abstractmethod
from random import random

import numpy as np

from models.particle import Particle


class ModeloVelocidad(ABC):
    @abstractmethod
    def actualizar(self, particula: Particle, mejor_g_pos: np.ndarray):
        """Acualiza la velocidad y posicion de la particula"""
        pass


class Inercia(ModeloVelocidad):
    def __init__(self, c1: float = 0.5, c2: float = 1.0, inercia: float = 0.8) -> None:
        self.c1 = c1
        self.c2 = c2
        self.inercia = inercia

    def actualizar(self, particula: Particle, mejor_g_pos: np.ndarray):
        r1, r2 = random(), random()

        nueva_velocidad = (
            (self.inercia * particula.velocity)
            + (self.c1 * r1 * (particula.best_pos - particula.position))
            + (self.c2 * r2 * (mejor_g_pos - particula.position))
        )

        particula.velocity = nueva_velocidad
        nueva_posicion = particula.position + particula.velocity

        # Normalización para mantener los pesos del portafolio (suma = 1)
        nueva_posicion = np.maximum(0, nueva_posicion)
        total_weight = np.sum(nueva_posicion)
        if total_weight > 0:
            nueva_posicion /= total_weight

        particula.position = nueva_posicion
