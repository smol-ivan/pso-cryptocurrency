from dataclasses import dataclass
from datetime import date, datetime
import numpy as np
import pandas as pd
import streamlit as st

from src.finance import build_metrics_dataframe, build_seed_metrics_dataframe
from src.models.state import ExperimentsPayload
from src.persistence import save_experiments
from src.run_pso import PSOInputData
from src.services.experiment_service import (
    build_experiment_configs,
    execute_experiments,
)
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
    rtol: float,
    atol: float,
    patience: int,
    base_seed: int | None,
    multi_seed_enabled: bool,
    seed_count: int,
):
    """Cached version of experiments execution. Uses simple types for hashing."""
    input_data = PSOInputData(mean_return=mean_return, returns_matrix=returns_matrix)
    configs = build_experiment_configs(
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
        rtol=rtol,
        atol=atol,
        patience=patience,
        base_seed=base_seed,
        seed_count=seed_count if multi_seed_enabled else 1,
    )
    return execute_experiments(input_data=input_data, configs=configs)


_build_experiment_configs = build_experiment_configs


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
    rtol: float,
    atol: float,
    patience: int,
    base_seed: int | None,
    multi_seed_enabled: bool = False,
    seed_count: int = 1,
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
            rtol=rtol,
            atol=atol,
            patience=patience,
            base_seed=base_seed,
            multi_seed_enabled=multi_seed_enabled,
            seed_count=seed_count,
        )

        metrics_by_config: dict[str, pd.DataFrame] = {}
        seed_metrics_by_config: dict[str, pd.DataFrame] = {}
        for experiment in experiments:
            metrics_by_config[experiment.config.name] = build_metrics_dataframe(
                returns_matrix=returns_matrix,
                weights_list=experiment.frontier.weights,
                cvar_alpha=alpha,
                fitness_values=experiment.frontier.best_fitnesses,
            )
            if experiment.frontier.seed_results:
                seed_metrics_by_config[experiment.config.name] = build_seed_metrics_dataframe(
                    returns_matrix=returns_matrix,
                    seed_frontiers=experiment.frontier.seed_results,
                    cvar_alpha=alpha,
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
            seed_metrics_by_config=seed_metrics_by_config,
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
