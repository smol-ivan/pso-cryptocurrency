"""Framework-independent services for configuring and running experiments."""

from __future__ import annotations

from itertools import product

from src.experiments import ExperimentConfig, ExperimentResult, run_experiments
from src.pso import (
    CVaR,
    Constriction,
    GlobalTopology,
    Inertia,
    MaxDrawdown,
    RingTopology,
    Semivariance,
    VaR,
    Variance,
)
from src.run_pso import PSOInputData


def build_experiment_configs(
    selected_objectives: list[str],
    selected_velocities: list[str],
    selected_topologies: list[str],
    *,
    alpha: float,
    penalty: float,
    c1: float,
    c2: float,
    inertia: float,
    num_points: int,
    n_swarm: int,
    rtol: float,
    atol: float,
    patience: int,
    base_seed: int | None,
    seed_count: int = 1,
) -> list[ExperimentConfig]:
    """Build the Cartesian product of the selected PSO configurations."""
    configs: list[ExperimentConfig] = []

    for config_index, (objective_name, velocity_name, topology_name) in enumerate(
        product(selected_objectives, selected_velocities, selected_topologies)
    ):
        if objective_name == "CVaR":
            fitness_function = CVaR(alpha=alpha, penalty=penalty)
        elif objective_name == "VaR":
            fitness_function = VaR(alpha=alpha, penalty=penalty)
        elif objective_name == "Variance":
            fitness_function = Variance(penalty=penalty)
        elif objective_name == "Semivariance":
            fitness_function = Semivariance(penalty=penalty)
        else:
            fitness_function = MaxDrawdown(penalty=penalty)

        if velocity_name == "Inertia":
            velocity_model = Inertia(c1=c1, c2=c2, inertia=inertia)
        else:
            velocity_model = Constriction(c1=c1, c2=c2)

        topology = (
            RingTopology(k_neighbors=1)
            if topology_name == "Ring"
            else GlobalTopology()
        )
        configs.append(
            ExperimentConfig(
                name=f"{objective_name} | {velocity_name} | {topology_name}",
                objective_name=objective_name,
                velocity_name=velocity_name,
                topology_name=topology_name,
                fitness_function=fitness_function,
                velocity_model=velocity_model,
                topology=topology,
                num_points=num_points,
                n_swarm=n_swarm,
                rtol=rtol,
                atol=atol,
                patience=patience,
                seed=None if base_seed is None else base_seed + config_index,
                seed_count=seed_count,
            )
        )

    return configs


def execute_experiments(
    input_data: PSOInputData,
    configs: list[ExperimentConfig],
) -> list[ExperimentResult]:
    """Execute configured experiments without importing a presentation layer."""
    return run_experiments(input_data=input_data, experiment_configs=configs)
