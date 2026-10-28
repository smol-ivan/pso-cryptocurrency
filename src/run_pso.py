from dataclasses import dataclass
import random

import numpy as np

from src.pso import CVaR, FitnessFunction, Inertia, RingTopology, Topology, VelocityModel, pso
from src.pso.optimizer import ConvergenceTrace


@dataclass
class EfficientFrontier:
    """Holds all data output from one set of PSO's executions"""

    target_values: np.ndarray
    weights: list[np.ndarray]
    best_fitnesses: np.ndarray
    convergence_histories: list[np.ndarray] | None = None
    diversity_histories: list[np.ndarray] | None = None
    diagnostic_histories: list[ConvergenceTrace] | None = None
    seed_results: list["EfficientFrontier"] | None = None
    seed_values: list[int | None] | None = None


@dataclass
class PSOInputData:
    """Input data required by run_pso."""

    mean_return: np.ndarray
    returns_matrix: np.ndarray


def run_pso(
    input_data: PSOInputData,
    num_points: int = 50,
    n_swarm: int = 100,
    rtol: float = 1e-4,
    atol: float = 1e-8,
    patience: int = 10,
    # Dependenties
    fitness_function: FitnessFunction | None = None,
    velocity_model: VelocityModel | None = None,
    topology: Topology | None = None,
    random_generator: np.random.Generator | None = None,
    python_random_generator: random.Random | None = None,
) -> EfficientFrontier:
    if not fitness_function or not velocity_model or not topology:
        fitness_function = CVaR()
        velocity_model = Inertia()
        topology = RingTopology()

    # Set upper and lower bounds
    lim_inf = input_data.mean_return.min()
    lim_sup = input_data.mean_return.max()

    # Points of the frontier
    target_values = np.linspace(lim_inf, lim_sup, num_points)

    weights_list = []
    fitnesses_list = []
    convergence_histories = []
    diversity_histories = []
    diagnostic_histories = []

    # Run pso for each point
    print(f"Ejecutando {num_points} optimizaciones PSO...")
    for i, target in enumerate(target_values):
        # Run pso
        (
            best_fitness,
            best_position,
            convergence_history,
            diversity_history,
            diagnostic_history,
        ) = pso(
                returns_matrix=input_data.returns_matrix,
                swarm_size=n_swarm,
                target_value=target,
                fitness_function=fitness_function,
                velocity_model=velocity_model,
                topology=topology,
                rtol=rtol,
                atol=atol,
                patience=patience,
                random_generator=random_generator,
                python_random_generator=python_random_generator,
                return_diagnostics=True,
                )

        weights_list.append(best_position.copy())
        fitnesses_list.append(best_fitness)
        convergence_histories.append(convergence_history)
        diversity_histories.append(diversity_history)
        diagnostic_histories.append(diagnostic_history)

    return EfficientFrontier(
        target_values=target_values,
        weights=weights_list,
        best_fitnesses=np.array(fitnesses_list),
        convergence_histories=convergence_histories,
        diversity_histories=diversity_histories,
        diagnostic_histories=diagnostic_histories,
    )
