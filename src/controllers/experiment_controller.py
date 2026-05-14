from dataclasses import dataclass
from datetime import date, datetime
from itertools import product

import numpy as np
import pandas as pd
import streamlit as st

from src.experiments import ExperimentConfig, run_experiments
from src.finance import build_metrics_dataframe
from src.models.fitness_function import CVaR, MaxDrawdown
from src.models.state import ExperimentsPayload
from src.models.topology import GlobalTopology, RingTopology
from src.models.velocity_model import Constriction, Inertia
from src.persistence import save_experiments
from src.run_pso import PSOInputData
from src.utils import load_crypto_returns


@dataclass
class AnalysisPipelineResult:
    payload: ExperimentsPayload | None = None
    completed_experiments: int = 0
    validation_error: str | None = None
    error: str | None = None
    backtesting_warning: str | None = None


@st.cache_data
def _load_crypto_returns_cached(
    assets_tuple: tuple[str, ...],
    start: str,
    end: str,
    interval: str,
):
    """Cached version of load_crypto_returns. Assets must be passed as tuple."""
    return load_crypto_returns(list(assets_tuple), start=start, end=end, interval=interval)


@st.cache_data
def _run_experiments_cached(
    mean_return: np.ndarray,
    returns_matrix: np.ndarray,
    selected_objectives_tuple: tuple[str, ...],
    selected_velocities_tuple: tuple[str, ...],
    selected_topologies_tuple: tuple[str, ...],
    alpha: float,
    penalty: float,
    c1: float,
    c2: float,
    inertia: float,
    num_points: int,
    n_swarm: int,
    epsilon: float,
    base_seed: int | None,
):
    """Cached version of experiments execution. Uses simple types for hashing."""
    input_data = PSOInputData(mean_return=mean_return, returns_matrix=returns_matrix)
    configs = _build_experiment_configs(
        list(selected_objectives_tuple),
        list(selected_velocities_tuple),
        list(selected_topologies_tuple),
        alpha=alpha,
        penalty=penalty,
        c1=c1,
        c2=c2,
        inertia=inertia,
        num_points=num_points,
        n_swarm=n_swarm,
        epsilon=epsilon,
        base_seed=base_seed,
    )
    return run_experiments(input_data=input_data, experiment_configs=configs)


def _build_experiment_configs(
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
    epsilon: float,
    base_seed: int | None,
) -> list[ExperimentConfig]:
    configs: list[ExperimentConfig] = []

    for config_index, (objective_name, velocity_name, topology_name) in enumerate(
        product(selected_objectives, selected_velocities, selected_topologies)
    ):
        if objective_name == "CVaR":
            fitness_function = CVaR(alpha=alpha, penalty=penalty)
        else:
            fitness_function = MaxDrawdown(penalty=penalty)

        if velocity_name == "Inertia":
            velocity_model = Inertia(c1=c1, c2=c2, inertia=inertia)
        else:
            velocity_model = Constriction(c1=c1, c2=c2)

        topology = RingTopology(k_neighbors=1) if topology_name == "Ring" else GlobalTopology()
        config_name = f"{objective_name} | {velocity_name} | {topology_name}"

        configs.append(
            ExperimentConfig(
                name=config_name,
                objective_name=objective_name,
                velocity_name=velocity_name,
                topology_name=topology_name,
                fitness_function=fitness_function,
                velocity_model=velocity_model,
                topology=topology,
                num_points=num_points,
                n_swarm=n_swarm,
                epsilon=epsilon,
                seed=None if base_seed is None else base_seed + config_index,
            )
        )

    return configs


def run_analysis_pipeline(
    *,
    assets: list[str],
    start_date: date,
    end_date: date,
    interval: str,
    selected_objectives: list[str],
    selected_velocities: list[str],
    selected_topologies: list[str],
    alpha: float,
    penalty: float,
    c1: float,
    c2: float,
    inertia: float,
    num_points: int,
    n_swarm: int,
    epsilon: float,
    base_seed: int | None,
) -> AnalysisPipelineResult:
    if not assets:
        return AnalysisPipelineResult(validation_error="Select at least one asset.")
    if start_date >= end_date:
        return AnalysisPipelineResult(validation_error="Start date must be before end date.")
    if not selected_objectives or not selected_velocities or not selected_topologies:
        return AnalysisPipelineResult(
            validation_error="Select at least one option in objective, velocity and topology."
        )
    if "Constriction" in selected_velocities and (c1 + c2) <= 4:
        return AnalysisPipelineResult(validation_error="Constriction requires c1 + c2 > 4.")

    try:
        # Use cached version with hashable tuple
        mean_return, returns_matrix, returns_index = _load_crypto_returns_cached(
            tuple(assets),
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=interval,
        )
        
        # Use cached experiments with hashable tuples
        experiments = _run_experiments_cached(
            mean_return=mean_return,
            returns_matrix=returns_matrix,
            selected_objectives_tuple=tuple(selected_objectives),
            selected_velocities_tuple=tuple(selected_velocities),
            selected_topologies_tuple=tuple(selected_topologies),
            alpha=alpha,
            penalty=penalty,
            c1=c1,
            c2=c2,
            inertia=inertia,
            num_points=num_points,
            n_swarm=n_swarm,
            epsilon=epsilon,
            base_seed=base_seed,
        )

        metrics_by_config: dict[str, pd.DataFrame] = {}
        for experiment in experiments:
            metrics_by_config[experiment.config.name] = build_metrics_dataframe(
                returns_matrix=returns_matrix,
                weights_list=experiment.frontier.weights,
                cvar_alpha=alpha,
                fitness_values=experiment.frontier.best_fitnesses,
            )

        bt_returns_matrix = None
        bt_returns_index = None
        backtesting_warning = None
        try:
            backtest_start = end_date
            backtest_end = datetime.now().date()
            if backtest_start < backtest_end:
                _, bt_returns_matrix, bt_returns_index = _load_crypto_returns_cached(
                    tuple(assets),
                    start=backtest_start.isoformat(),
                    end=backtest_end.isoformat(),
                    interval=interval,
                )
        except Exception as error:
            backtesting_warning = str(error)

        payload = ExperimentsPayload(
            assets=assets,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            interval=interval,
            alpha=alpha,
            returns_matrix=returns_matrix,
            returns_index=returns_index,
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            bt_returns_matrix=bt_returns_matrix,
            bt_returns_index=bt_returns_index,
        )
        save_experiments(payload)

        return AnalysisPipelineResult(
            payload=payload,
            completed_experiments=len(experiments),
            backtesting_warning=backtesting_warning,
        )
    except Exception as error:
        return AnalysisPipelineResult(error=str(error))
