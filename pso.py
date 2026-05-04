from typing import List

import numpy as np

from models.fitness_function import FitnessFunction
from models.particle import Particle
from models.topology import Topology
from models.velocity_model import VelocityModel


def initialize_swarm(
    returns_matrix: np.ndarray,
    swarm_size: int,
    target_value: float,
    fitness_function: FitnessFunction,
) -> List[Particle]:
    n_assets = returns_matrix.shape[1]
    swarm: List["Particle"] = []
    for _ in range(swarm_size):
        position = np.random.rand(n_assets)
        position_sum = np.sum(position)
        if position_sum > 0:
            position /= position_sum
        velocity = np.zeros(n_assets)
        fitness = fitness_function.evaluate(position, returns_matrix, target_value)
        swarm.append(Particle(position, velocity, fitness))
    return swarm


def pso(
    returns_matrix: np.ndarray,
    iterations: int,
    swarm_size: int,
    target_value: float,
    fitness_function: FitnessFunction,
    velocity_model: VelocityModel,
    topology: Topology,
):
    swarm = initialize_swarm(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=target_value,
        fitness_function=fitness_function,
    )

    best_initial_particle = min(swarm, key=lambda particle: particle.best_val)
    best_global_position = best_initial_particle.best_pos.copy()
    best_global_value = best_initial_particle.best_val

    for _ in range(iterations):
        for idx, particle in enumerate(swarm):
            best_reference = topology.get_best_particle(idx, swarm)
            velocity_model.update(particle, best_reference.best_pos)
            new_fitness = fitness_function.evaluate(
                particle.position, returns_matrix, target_value
            )

            if new_fitness < particle.best_val:
                particle.best_val = new_fitness
                particle.best_pos = particle.position.copy()

        best_iteration_particle = min(swarm, key=lambda current: current.best_val)
        if best_iteration_particle.best_val < best_global_value:
            best_global_position = best_iteration_particle.best_pos.copy()
            best_global_value = best_iteration_particle.best_val

    return best_global_value, best_global_position
