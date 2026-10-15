from typing import List

import numpy as np

from .fitness_function import FitnessFunction
from .particle import Particle
from .topology import Topology
from .velocity_model import VelocityModel


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
    swarm_size: int,
    target_value: float,
    fitness_function: FitnessFunction,
    velocity_model: VelocityModel,
    topology: Topology,
    rtol: float = 1e-4,
    atol: float = 1e-8,
    patience: int = 10,
    max_iterations: int = 1000,
):
    """
    PSO with early stopping on convergence.
    
    Args:
        rtol: Relative improvement threshold for convergence detection.
        atol: Absolute improvement threshold for convergence detection.
        patience: Consecutive iterations below the tolerance before stopping.
        max_iterations: Maximum number of iterations before stopping.
    """
    swarm = initialize_swarm(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=target_value,
        fitness_function=fitness_function,
    )

    best_initial_particle = min(swarm, key=lambda particle: particle.best_val)
    best_global_position = best_initial_particle.best_pos.copy()
    best_global_value = best_initial_particle.best_val
    prev_best_value = best_global_value
    convergence_history: list[tuple[int, float]] = []
    diversity_history = [_swarm_diversity(swarm)]
    convergence_wait = 0

    for iteration in range(max_iterations):
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

        convergence_history.append((iteration, best_global_value))
        diversity_history.append(_swarm_diversity(swarm))

        # Convergencia temprana
        improvement = abs(best_global_value - prev_best_value)
        tolerance = atol + rtol * abs(best_global_value)
        if iteration > 5 and improvement < tolerance:
            convergence_wait += 1
            if convergence_wait >= patience:
                break
        else:
            convergence_wait = 0
        
        prev_best_value = best_global_value

    return (
        best_global_value,
        best_global_position,
        np.asarray(convergence_history, dtype=float),
        np.asarray(diversity_history, dtype=float),
    )


def _swarm_diversity(swarm: list[Particle]) -> float:
    positions = np.asarray([particle.position for particle in swarm])
    centroid = positions.mean(axis=0)
    distances = np.linalg.norm(positions - centroid, axis=1)
    return float(distances.mean())
