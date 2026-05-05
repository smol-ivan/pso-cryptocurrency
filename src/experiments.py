from dataclasses import dataclass

import numpy as np

from .models.fitness_function import FitnessFunction
from .models.topology import Topology
from .models.velocity_model import VelocityModel
from .run_pso import EfficientFrontier, PSOInputData, run_pso


@dataclass
class ExperimentConfig:
    name: str
    objective_name: str
    velocity_name: str
    topology_name: str
    fitness_function: FitnessFunction
    velocity_model: VelocityModel
    topology: Topology
    num_points: int = 30
    n_swarm: int = 100
    epsilon: float = 1e-5
    seed: int | None = None


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    frontier: EfficientFrontier


def run_experiments(
    input_data: PSOInputData, experiment_configs: list[ExperimentConfig]
) -> list[ExperimentResult]:
    results: list[ExperimentResult] = []
    for config in experiment_configs:
        if config.seed is not None:
            np.random.seed(config.seed)
        frontier = run_pso(
            input_data=input_data,
            num_points=config.num_points,
            n_swarm=config.n_swarm,
            epsilon=config.epsilon,
            fitness_function=config.fitness_function,
            velocity_model=config.velocity_model,
            topology=config.topology,
        )
        results.append(ExperimentResult(config=config, frontier=frontier))
    return results


def build_experiment_summary(
    experiments: list[ExperimentResult], metrics_by_name: dict[str, np.ndarray]
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for experiment in experiments:
        metrics = metrics_by_name[experiment.config.name]
        rows.append(
            {
                "name": experiment.config.name,
                "objective": experiment.config.objective_name,
                "velocity": experiment.config.velocity_name,
                "topology": experiment.config.topology_name,
                "best_mean_return": float(np.max(metrics[:, 0])),
                "best_cvar": float(np.min(metrics[:, 1])),
                "best_max_drawdown": float(np.min(metrics[:, 2])),
                "best_sharpe_ratio": float(np.max(metrics[:, 3])),
                "best_fitness": float(np.min(experiment.frontier.best_fitnesses)),
            }
        )
    return rows
