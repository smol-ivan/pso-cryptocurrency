from dataclasses import dataclass

import numpy as np

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pso import CVaR, FitnessFunction, Inertia, RingTopology, Topology, VelocityModel, pso


@dataclass
class EfficientFrontier:
    """Holds all data output from one set of PSO's executions"""

    target_values: np.ndarray
    weights: list[np.ndarray]
    best_fitnesses: np.ndarray


@dataclass
class PSOInputData:
    """Input data required by run_pso."""

    mean_return: np.ndarray
    returns_matrix: np.ndarray


def run_pso(
    input_data: PSOInputData,
    num_points: int = 50,
    n_swarm: int = 100,
    epsilon: float = 1e-5,
    # Dependenties
    fitness_function: FitnessFunction | None = None,
    velocity_model: VelocityModel | None = None,
    topology: Topology | None = None,
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

    # Run pso for each point
    print(f"Ejecutando {num_points} optimizaciones PSO...")
    for i, target in enumerate(target_values):
        # Run pso
        best_fitness, best_position = pso(
                returns_matrix=input_data.returns_matrix,
                swarm_size=n_swarm,
                target_value=target,
                fitness_function=fitness_function,
                velocity_model=velocity_model,
                topology=topology,
                epsilon=epsilon,
                )

        weights_list.append(best_position.copy())
        fitnesses_list.append(best_fitness)

    return EfficientFrontier(
        target_values=target_values,
        weights=weights_list,
        best_fitnesses=np.array(fitnesses_list),
    )
