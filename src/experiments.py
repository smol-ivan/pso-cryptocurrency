from dataclasses import dataclass
import random

import numpy as np

from src.pso import FitnessFunction, Topology, VelocityModel
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
    rtol: float = 1e-4
    atol: float = 1e-8
    patience: int = 10
    seed: int | None = None
    seed_count: int = 1


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    frontier: EfficientFrontier


def run_experiments(
    input_data: PSOInputData, experiment_configs: list[ExperimentConfig]
) -> list[ExperimentResult]:
    results: list[ExperimentResult] = []
    for config in experiment_configs:
        seed_count = max(1, config.seed_count)
        seed_results: list[EfficientFrontier] = []
        seed_values: list[int | None] = []
        for seed_index in range(seed_count):
            seed = config.seed + seed_index if config.seed is not None else None
            if seed is not None:
                random_generator = np.random.default_rng(seed)
                python_random_generator = random.Random(seed)
            else:
                random_generator = np.random.default_rng()
                python_random_generator = random.Random()
            seed_results.append(
                run_pso(
                    input_data=input_data,
                    num_points=config.num_points,
                    n_swarm=config.n_swarm,
                    rtol=config.rtol,
                    atol=config.atol,
                    patience=config.patience,
                    fitness_function=config.fitness_function,
                    velocity_model=config.velocity_model,
                    topology=config.topology,
                    random_generator=random_generator,
                    python_random_generator=python_random_generator,
                )
            )
            seed_values.append(seed)
        frontier = seed_results[0]
        if seed_count > 1:
            frontier.seed_results = seed_results
            frontier.seed_values = seed_values
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
