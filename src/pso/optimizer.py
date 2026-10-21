import random
from dataclasses import dataclass
from numbers import Real
from typing import Any, List

import numpy as np

from .fitness_function import FitnessFunction
from .particle import Particle
from .topology import Topology
from .velocity_model import VelocityModel


@dataclass
class ConvergenceTrace:
    """Stable, aggregate diagnostics captured after each completed generation."""

    schema_version: int
    iterations_completed: int
    termination_reason: str
    termination_iteration: int | None
    initial_diversity: float
    iterations: np.ndarray
    gbest: np.ndarray
    current_best: np.ndarray
    current_mean: np.ndarray
    current_median: np.ndarray
    current_std: np.ndarray
    pbest_mean: np.ndarray
    pbest_std: np.ndarray
    improvement: np.ndarray
    tolerance: np.ndarray
    patience_wait: np.ndarray
    last_significant_improvement: np.ndarray
    diversity: np.ndarray
    diversity_max_distance: np.ndarray
    diversity_relative: np.ndarray
    movement_mean: np.ndarray
    movement_max: np.ndarray
    repairs: np.ndarray
    invalid_values: np.ndarray
    weight_sum_min: np.ndarray
    weight_sum_max: np.ndarray
    best_mean_return: np.ndarray
    best_target_difference: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in self.__dict__.items():
            result[name] = value.tolist() if isinstance(value, np.ndarray) else value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConvergenceTrace":
        array_fields = {
            "iterations", "gbest", "current_best", "current_mean",
            "current_median", "current_std", "pbest_mean", "pbest_std",
            "improvement", "tolerance", "patience_wait",
            "last_significant_improvement", "diversity",
            "diversity_max_distance", "diversity_relative", "movement_mean",
            "movement_max", "repairs", "invalid_values", "weight_sum_min",
            "weight_sum_max", "best_mean_return", "best_target_difference",
        }
        converted = dict(data)
        for field in array_fields:
            converted[field] = np.asarray(converted.get(field, []), dtype=float)
        return cls(**converted)


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
    return_diagnostics: bool = False,
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
    initial_diversity = diversity_history[0]
    iterations: list[int] = []
    current_best: list[float] = []
    current_mean: list[float] = []
    current_median: list[float] = []
    current_std: list[float] = []
    pbest_mean: list[float] = []
    pbest_std: list[float] = []
    improvements: list[float] = []
    tolerances: list[float] = []
    patience_waits: list[int] = []
    last_significant: list[int] = []
    diversities: list[float] = []
    diversity_max_distances: list[float] = []
    movements: list[float] = []
    movement_maxes: list[float] = []
    repairs: list[int] = []
    invalid_values: list[int] = []
    weight_sum_mins: list[float] = []
    weight_sum_maxes: list[float] = []
    best_mean_returns: list[float] = []
    best_target_differences: list[float] = []
    last_significant_iteration = -1
    termination_reason = "max_iterations"
    termination_iteration: int | None = None

    for iteration in range(max_iterations):
        previous_positions = np.asarray([particle.position.copy() for particle in swarm])
        current_fitnesses: list[float] = []
        generation_repairs = 0
        for idx, particle in enumerate(swarm):
            best_reference = topology.get_best_particle(idx, swarm)
            velocity_model.update(particle, best_reference.best_pos)
            generation_repairs += int(velocity_model.last_repaired)
            new_fitness = fitness_function.evaluate(
                particle.position, returns_matrix, target_value
            )
            _validate_fitness(new_fitness)
            current_fitnesses.append(float(new_fitness))

            if new_fitness < particle.best_val:
                particle.best_val = new_fitness
                particle.best_pos = particle.position.copy()

        best_iteration_particle = min(swarm, key=lambda current: current.best_val)
        if best_iteration_particle.best_val < best_global_value:
            best_global_position = best_iteration_particle.best_pos.copy()
            best_global_value = best_iteration_particle.best_val

        convergence_history.append((iteration, best_global_value))
        diversity_history.append(_swarm_diversity(swarm))
        positions = np.asarray([particle.position for particle in swarm])
        distances = np.linalg.norm(positions - positions.mean(axis=0), axis=1)
        movement_distances = np.linalg.norm(positions - previous_positions, axis=1)
        pbest_values = np.asarray([particle.best_val for particle in swarm], dtype=float)
        improvement = abs(best_global_value - prev_best_value)
        tolerance = atol + rtol * abs(best_global_value)
        if improvement >= tolerance:
            last_significant_iteration = iteration
        iterations.append(iteration)
        current_best.append(float(np.min(current_fitnesses)))
        current_mean.append(float(np.mean(current_fitnesses)))
        current_median.append(float(np.median(current_fitnesses)))
        current_std.append(float(np.std(current_fitnesses)))
        pbest_mean.append(float(np.mean(pbest_values)))
        pbest_std.append(float(np.std(pbest_values)))
        improvements.append(float(improvement))
        tolerances.append(float(tolerance))
        patience_waits.append(convergence_wait)
        last_significant.append(last_significant_iteration)
        diversities.append(float(distances.mean()))
        diversity_max_distances.append(float(distances.max()))
        movements.append(float(movement_distances.mean()))
        movement_maxes.append(float(movement_distances.max()))
        repairs.append(generation_repairs)
        velocities = np.asarray([particle.velocity for particle in swarm])
        invalid_values.append(
            int(
                np.size(positions) - np.isfinite(positions).sum()
                + np.size(velocities) - np.isfinite(velocities).sum()
                + len(current_fitnesses) - np.isfinite(current_fitnesses).sum()
            )
        )
        sums = positions.sum(axis=1)
        weight_sum_mins.append(float(sums.min()))
        weight_sum_maxes.append(float(sums.max()))
        best_returns = float((returns_matrix @ best_global_position).mean())
        best_mean_returns.append(best_returns)
        best_target_differences.append(abs(best_returns - target_value))

        # Convergencia temprana
        if iteration > 5 and improvement < tolerance:
            convergence_wait += 1
            patience_waits[-1] = convergence_wait
            if convergence_wait >= patience:
                termination_reason = "patience"
                termination_iteration = iteration
                break
        else:
            convergence_wait = 0
        patience_waits[-1] = convergence_wait
        
        prev_best_value = best_global_value

    if termination_iteration is None and convergence_history:
        termination_iteration = int(convergence_history[-1][0])
    trace = ConvergenceTrace(
        schema_version=1,
        iterations_completed=len(convergence_history),
        termination_reason=termination_reason,
        termination_iteration=termination_iteration,
        initial_diversity=float(initial_diversity),
        iterations=np.asarray(iterations, dtype=float),
        gbest=np.asarray([row[1] for row in convergence_history], dtype=float),
        current_best=np.asarray(current_best, dtype=float),
        current_mean=np.asarray(current_mean, dtype=float),
        current_median=np.asarray(current_median, dtype=float),
        current_std=np.asarray(current_std, dtype=float),
        pbest_mean=np.asarray(pbest_mean, dtype=float),
        pbest_std=np.asarray(pbest_std, dtype=float),
        improvement=np.asarray(improvements, dtype=float),
        tolerance=np.asarray(tolerances, dtype=float),
        patience_wait=np.asarray(patience_waits, dtype=float),
        last_significant_improvement=np.asarray(last_significant, dtype=float),
        diversity=np.asarray(diversities, dtype=float),
        diversity_max_distance=np.asarray(diversity_max_distances, dtype=float),
        diversity_relative=np.asarray(
            [value / initial_diversity if initial_diversity > 0 else np.nan for value in diversities],
            dtype=float,
        ),
        movement_mean=np.asarray(movements, dtype=float),
        movement_max=np.asarray(movement_maxes, dtype=float),
        repairs=np.asarray(repairs, dtype=float),
        invalid_values=np.asarray(invalid_values, dtype=float),
        weight_sum_min=np.asarray(weight_sum_mins, dtype=float),
        weight_sum_max=np.asarray(weight_sum_maxes, dtype=float),
        best_mean_return=np.asarray(best_mean_returns, dtype=float),
        best_target_difference=np.asarray(best_target_differences, dtype=float),
    )
    result = (
        best_global_value,
        best_global_position,
        np.asarray(convergence_history, dtype=float),
        np.asarray(diversity_history, dtype=float),
    )
    return (*result, trace) if return_diagnostics else result


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
