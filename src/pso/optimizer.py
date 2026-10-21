import random
from numbers import Real
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
    random_generator: np.random.Generator | None = None,
) -> List[Particle]:
    _validate_returns_matrix(returns_matrix)
    _validate_swarm_size(swarm_size)
    _validate_target(target_value)
    random_generator = random_generator or np.random.default_rng()
    n_assets = returns_matrix.shape[1]
    swarm: List["Particle"] = []
    for _ in range(swarm_size):
        position = random_generator.random(n_assets)
        position_sum = np.sum(position)
        if position_sum > 0:
            position /= position_sum
        velocity = np.zeros(n_assets)
        fitness = fitness_function.evaluate(position, returns_matrix, target_value)
        _validate_fitness(fitness)
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
    random_generator: np.random.Generator | None = None,
    python_random_generator: random.Random | None = None,
):
    """
    PSO with early stopping on convergence.
    
    Args:
        rtol: Relative improvement threshold for convergence detection.
        atol: Absolute improvement threshold for convergence detection.
        patience: Consecutive iterations below the tolerance before stopping.
        max_iterations: Maximum number of iterations before stopping.
    """
    _validate_optimizer_inputs(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=target_value,
        rtol=rtol,
        atol=atol,
        patience=patience,
        max_iterations=max_iterations,
    )
    random_generator = random_generator or np.random.default_rng()
    python_random_generator = python_random_generator or random.Random()
    velocity_model.set_random_generator(python_random_generator)
    swarm = initialize_swarm(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=target_value,
        fitness_function=fitness_function,
        random_generator=random_generator,
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
            _validate_fitness(new_fitness)

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


def _validate_target(target_value: float) -> None:
    _validate_finite_scalar(target_value, "target_value")


def _validate_finite_scalar(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
        raise ValueError(f"{name} must be a finite real number.")


def _validate_fitness(fitness: float) -> None:
    if isinstance(fitness, bool) or not isinstance(fitness, Real) or not np.isfinite(fitness):
        raise ValueError("Fitness evaluation must return a finite real number.")


def _validate_tolerance(name: str, value: float) -> None:
    _validate_finite_scalar(value, name)
    if value < 0:
        raise ValueError(f"{name} must be finite and non-negative.")


def _validate_optimizer_inputs(
    *,
    returns_matrix: np.ndarray,
    swarm_size: int,
    target_value: float,
    rtol: float,
    atol: float,
    patience: int,
    max_iterations: int,
) -> None:
    _validate_returns_matrix(returns_matrix)
    _validate_swarm_size(swarm_size)
    _validate_target(target_value)
    if not isinstance(patience, int) or isinstance(patience, bool) or patience <= 0:
        raise ValueError("patience must be a positive integer.")
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer.")
    _validate_tolerance("rtol", rtol)
    _validate_tolerance("atol", atol)


def _validate_returns_matrix(returns_matrix: np.ndarray) -> None:
    if not isinstance(returns_matrix, np.ndarray):
        raise ValueError("returns_matrix must be a NumPy array.")
    if returns_matrix.ndim != 2 or returns_matrix.shape[0] == 0 or returns_matrix.shape[1] == 0:
        raise ValueError("returns_matrix must be a non-empty two-dimensional array.")
    if not np.all(np.isfinite(returns_matrix)):
        raise ValueError("returns_matrix must contain only finite values.")


def _validate_swarm_size(swarm_size: int) -> None:
    if not isinstance(swarm_size, int) or isinstance(swarm_size, bool) or swarm_size <= 0:
        raise ValueError("swarm_size must be a positive integer.")
