"""In-memory validation cases used by the independent Streamlit dashboard."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from src.pso import GlobalTopology, Inertia, RingTopology, pso
from src.pso.fitness_function import CVaR, FitnessFunction
from src.utils import load_crypto_returns


SPHERE_OPTIMUM = np.full(4, 0.25)
MIN_VARIANCE_COVARIANCE = np.array(
    [[0.04, 0.01, 0.00], [0.01, 0.09, 0.02], [0.00, 0.02, 0.16]],
    dtype=float,
)
MIN_VARIANCE_WEIGHTS = np.array([0.6461538462, 0.2051282051, 0.1487179487])
MIN_VARIANCE_VALUE = 0.027897435897435898
VALIDATION_SEEDS = (11, 12, 13, 14, 15)
CONVERGENCE_SEEDS = (101, 102, 103)
PSO_SETTINGS = {
    "swarm_size": 30,
    "max_iterations": 120,
    "rtol": 1e-4,
    "atol": 1e-8,
    "patience": 10,
    "inertia_c1": 1.7,
    "inertia_c2": 1.7,
    "inertia": 0.8,
}
MARKET_ASSETS = ("BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD")
MARKET_START = "2020-01-01"
MARKET_END = "2024-01-01"
MARKET_INTERVAL = "1d"
MARKET_ALPHA = 0.95
MARKET_PENALTY = 50.0
MARKET_SEEDS = (42, 43, 44)
MARKET_TARGETS = ("minimum", "intermediate")
MARKET_PSO_SETTINGS = {
    "swarm_size": 100,
    "max_iterations": 1000,
    "rtol": 1e-4,
    "atol": 1e-8,
    "patience": 10,
    "inertia_c1": 1.7,
    "inertia_c2": 1.7,
    "inertia": 0.8,
    "frontier_points_reference": 30,
}


class SimplexSphere(FitnessFunction):
    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        return float(np.sum((position - SPHERE_OPTIMUM) ** 2))


class FixedCovarianceVariance(FitnessFunction):
    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        return float(position @ MIN_VARIANCE_COVARIANCE @ position)


@dataclass
class PSORun:
    fitness: float
    position: np.ndarray
    trace: Any


def _run(
    *,
    returns_matrix: np.ndarray,
    fitness_function: FitnessFunction,
    seed: int,
    topology: Any,
    swarm_size: int = PSO_SETTINGS["swarm_size"],
    max_iterations: int = PSO_SETTINGS["max_iterations"],
) -> PSORun:
    result = pso(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=0.0,
        fitness_function=fitness_function,
        velocity_model=Inertia(
            c1=PSO_SETTINGS["inertia_c1"],
            c2=PSO_SETTINGS["inertia_c2"],
            inertia=PSO_SETTINGS["inertia"],
        ),
        topology=topology,
        rtol=PSO_SETTINGS["rtol"],
        atol=PSO_SETTINGS["atol"],
        patience=PSO_SETTINGS["patience"],
        max_iterations=max_iterations,
        random_generator=np.random.default_rng(seed),
        python_random_generator=random.Random(seed),
        return_diagnostics=True,
    )
    fitness, position, _, _, trace = result
    return PSORun(float(fitness), position.copy(), trace)


def _reference_minimum_variance() -> tuple[np.ndarray, float]:
    candidates: list[tuple[np.ndarray, float]] = []
    for mask in range(1, 1 << MIN_VARIANCE_COVARIANCE.shape[0]):
        support = [i for i in range(3) if mask & (1 << i)]
        sub_covariance = MIN_VARIANCE_COVARIANCE[np.ix_(support, support)]
        unconstrained = np.linalg.solve(sub_covariance, np.ones(len(support)))
        support_weights = unconstrained / unconstrained.sum()
        if np.all(support_weights >= -1e-12):
            weights = np.zeros(3)
            weights[support] = support_weights
            candidates.append((weights, float(weights @ MIN_VARIANCE_COVARIANCE @ weights)))
    return min(candidates, key=lambda candidate: candidate[1])


def run_validation_suite() -> dict[str, Any]:
    """Execute all fixed validation cases and return only in-memory results."""
    started = time.perf_counter()
    sphere_returns = np.zeros((2, 4), dtype=float)
    variance_returns = np.zeros((2, 3), dtype=float)

    sphere_runs = [
        _run(
            returns_matrix=sphere_returns,
            fitness_function=SimplexSphere(),
            seed=seed,
            topology=GlobalTopology(),
        )
        for seed in VALIDATION_SEEDS
    ]
    first_sphere = sphere_runs[0]
    all_weights = np.asarray([run.position for run in sphere_runs])
    finite = bool(np.all(np.isfinite(all_weights)))
    nonnegative = bool(np.all(all_weights >= -1e-12))
    sums = all_weights.sum(axis=1)
    sums_ok = bool(np.allclose(sums, 1.0, atol=1e-12))
    feasibility = {
        "weights": first_sphere.position,
        "all_finite": finite,
        "nonnegative": nonnegative,
        "weight_sums": sums,
        "sums_ok": sums_ok,
        "ok": finite and nonnegative and sums_ok,
    }

    sphere_rows = [
        {
            "seed": seed,
            "fitness": run.fitness,
            "distance": float(np.linalg.norm(run.position - SPHERE_OPTIMUM)),
            "iterations": run.trace.iterations_completed,
            "termination": run.trace.termination_reason,
        }
        for seed, run in zip(VALIDATION_SEEDS, sphere_runs)
    ]
    sphere_ok = all(
        row["fitness"] <= 1e-4 and row["distance"] <= 2e-2 for row in sphere_rows
    )

    reference_weights, reference_value = _reference_minimum_variance()
    variance_runs = [
        _run(
            returns_matrix=variance_returns,
            fitness_function=FixedCovarianceVariance(),
            seed=seed,
            topology=GlobalTopology(),
            max_iterations=300,
        )
        for seed in VALIDATION_SEEDS
    ]
    variance_rows = []
    for seed, run in zip(VALIDATION_SEEDS, variance_runs):
        gap = (run.fitness - reference_value) / reference_value
        variance_rows.append(
            {
                "seed": seed,
                "fitness": run.fitness,
                "relative_gap": float(gap),
                "iterations": run.trace.iterations_completed,
                "termination": run.trace.termination_reason,
                "weights": run.position,
            }
        )
    variance_ok = all(
        row["relative_gap"] < 1e-4
        and np.all(row["weights"] >= -1e-12)
        and np.isclose(np.sum(row["weights"]), 1.0, atol=1e-12)
        for row in variance_rows
    )

    manual_returns = np.array([[-0.2], [-0.1], [0.1], [0.2]], dtype=float)
    manual_fitness = CVaR(alpha=0.50, penalty=50.0)
    calculated_cvar = manual_fitness.evaluate(np.array([1.0]), manual_returns, 0.0)
    penalized_fitness = manual_fitness.evaluate(
        np.array([1.0]), manual_returns, 0.15
    )
    manual_ok = np.isclose(calculated_cvar, 0.15) and np.isclose(
        penalized_fitness, 7.65
    )

    convergence_runs = {"Ring": [], "Global": []}
    for seed in CONVERGENCE_SEEDS:
        for name, topology in (
            ("Ring", RingTopology()),
            ("Global", GlobalTopology()),
        ):
            run = _run(
                returns_matrix=sphere_returns,
                fitness_function=SimplexSphere(),
                seed=seed,
                topology=topology,
            )
            convergence_runs[name].append(
                {
                    "seed": seed,
                    "gbest": run.trace.gbest,
                    "iterations": run.trace.iterations,
                    "diversity": run.trace.diversity,
                    "movement_mean": run.trace.movement_mean,
                    "repairs": run.trace.repairs,
                    "termination": run.trace.termination_reason,
                    "iterations_completed": run.trace.iterations_completed,
                    "fitness": run.fitness,
                }
            )
    convergence = {
        "seeds": CONVERGENCE_SEEDS,
        "runs": convergence_runs,
    }
    convergence_ok = all(
        diagnostic["iterations_completed"] > 0
        and len(diagnostic["iterations"]) == len(diagnostic["gbest"])
        and np.all(np.isfinite(diagnostic["gbest"]))
        for runs in convergence_runs.values()
        for diagnostic in runs
    )

    reproducible_a = _run(
        returns_matrix=sphere_returns,
        fitness_function=SimplexSphere(),
        seed=777,
        topology=GlobalTopology(),
    )
    reproducible_b = _run(
        returns_matrix=sphere_returns,
        fitness_function=SimplexSphere(),
        seed=777,
        topology=GlobalTopology(),
    )
    reproducible = {
        "same_seed": 777,
        "fitness_equal": bool(np.isclose(reproducible_a.fitness, reproducible_b.fitness)),
        "weights_equal": bool(
            np.array_equal(reproducible_a.position, reproducible_b.position)
        ),
        "trace_equal": bool(np.array_equal(reproducible_a.trace.gbest, reproducible_b.trace.gbest)),
    }
    reproducible["ok"] = all(
        reproducible[key] for key in ("fitness_equal", "weights_equal", "trace_equal")
    )

    return {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": time.perf_counter() - started,
        "settings": dict(PSO_SETTINGS),
        "seeds": VALIDATION_SEEDS,
        "feasibility": feasibility,
        "sphere": {
            "optimum": SPHERE_OPTIMUM,
            "rows": sphere_rows,
            "ok": sphere_ok,
        },
        "minimum_variance": {
            "reference_weights": reference_weights,
            "reference_value": reference_value,
            "documented_weights": MIN_VARIANCE_WEIGHTS,
            "documented_value": MIN_VARIANCE_VALUE,
            "rows": variance_rows,
            "ok": variance_ok,
        },
        "manual_cvar": {
            "expected_cvar_risk": 0.15,
            "calculated_cvar_risk": calculated_cvar,
            "expected_penalized_fitness": 7.65,
            "calculated_penalized_fitness": penalized_fitness,
            "ok": manual_ok,
        },
        "convergence": convergence,
        "convergence_ok": convergence_ok,
        "reproducibility": reproducible,
        "summary": {
            "cases": 6,
            "passed": sum(
                bool(value)
                for value in (
                    feasibility["ok"],
                    sphere_ok,
                    variance_ok,
                    manual_ok,
                    convergence_ok,
                    reproducible["ok"],
                )
            ),
            "incomplete": 0,
        },
    }


def _validate_market_returns(
    mean_return: np.ndarray,
    returns_matrix: np.ndarray,
    returns_index: Any,
) -> tuple[np.ndarray, np.ndarray]:
    means = np.asarray(mean_return, dtype=float)
    matrix = np.asarray(returns_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("La matriz de retornos recuperada no es bidimensional y no vacía.")
    if means.shape != (matrix.shape[1],):
        raise ValueError("La media de retornos no coincide con las columnas recuperadas.")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(means)):
        raise ValueError("Los retornos recuperados deben ser finitos.")
    if len(returns_index) != matrix.shape[0]:
        raise ValueError("El índice temporal no coincide con las observaciones.")
    return means, matrix


def _market_run(
    *,
    returns_matrix: np.ndarray,
    target_value: float,
    seed: int,
    topology_name: str,
) -> dict[str, Any]:
    topology = RingTopology() if topology_name == "Ring" else GlobalTopology()
    fitness = CVaR(alpha=MARKET_ALPHA, penalty=MARKET_PENALTY)
    result = pso(
        returns_matrix=returns_matrix,
        swarm_size=MARKET_PSO_SETTINGS["swarm_size"],
        target_value=target_value,
        fitness_function=fitness,
        velocity_model=Inertia(
            c1=MARKET_PSO_SETTINGS["inertia_c1"],
            c2=MARKET_PSO_SETTINGS["inertia_c2"],
            inertia=MARKET_PSO_SETTINGS["inertia"],
        ),
        topology=topology,
        rtol=MARKET_PSO_SETTINGS["rtol"],
        atol=MARKET_PSO_SETTINGS["atol"],
        patience=MARKET_PSO_SETTINGS["patience"],
        max_iterations=MARKET_PSO_SETTINGS["max_iterations"],
        random_generator=np.random.default_rng(seed),
        python_random_generator=random.Random(seed),
        return_diagnostics=True,
    )
    best_fitness, best_position, _, _, trace = result
    portfolio_returns = returns_matrix @ best_position
    risk = float(CVaR(alpha=MARKET_ALPHA, penalty=0.0).evaluate(
        best_position, returns_matrix, target_value
    ))
    mean_value = float(portfolio_returns.mean())
    target_gap = abs(mean_value - target_value)
    penalty_component = MARKET_PENALTY * target_gap
    return {
        "seed": seed,
        "topology": topology_name,
        "fitness": float(best_fitness),
        "weights": np.asarray(best_position, dtype=float),
        "max_weight": float(np.max(best_position)),
        "weights_near_vertices": int(np.sum(best_position >= 0.95)),
        "target": float(target_value),
        "mean_return": mean_value,
        "target_gap": float(target_gap),
        "target_gap_history": trace.best_target_difference,
        "cvar": risk,
        "penalty_component": float(penalty_component),
        "fitness_components_sum": float(risk + penalty_component),
        "iterations": trace.iterations,
        "gbest": trace.gbest,
        "diversity": trace.diversity,
        "diversity_relative": trace.diversity_relative,
        "movement_mean": trace.movement_mean,
        "movement_max": trace.movement_max,
        "repairs": trace.repairs,
        "weight_sum_min": trace.weight_sum_min,
        "weight_sum_max": trace.weight_sum_max,
        "invalid_values": trace.invalid_values,
        "termination": trace.termination_reason,
        "termination_iteration": trace.termination_iteration,
        "iterations_completed": trace.iterations_completed,
        "initial_diversity": trace.initial_diversity,
    }


def run_market_diagnostic(
    *,
    data_loader=load_crypto_returns,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Download and diagnose the fixed market experiment only when called."""
    started = time.perf_counter()
    mean_return, returns_matrix, returns_index = data_loader(
        list(MARKET_ASSETS),
        start=MARKET_START,
        end=MARKET_END,
        interval=MARKET_INTERVAL,
    )
    loaded_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    means, matrix = _validate_market_returns(mean_return, returns_matrix, returns_index)
    target_values = {
        "minimum": float(means.min()),
        "intermediate": float((means.min() + means.max()) / 2.0),
    }
    runs = {target_name: {"Ring": [], "Global": []} for target_name in MARKET_TARGETS}
    for target_name, target_value in target_values.items():
        for seed in MARKET_SEEDS:
            for topology_name in runs[target_name]:
                runs[target_name][topology_name].append(
                    _market_run(
                        returns_matrix=matrix,
                        target_value=target_value,
                        seed=seed,
                        topology_name=topology_name,
                    )
                )
    return {
        "retrieved_at": loaded_at,
        "assets": list(MARKET_ASSETS),
        "requested_start": MARKET_START,
        "requested_end": MARKET_END,
        "available_start": str(returns_index[0]),
        "available_end": str(returns_index[-1]),
        "interval": MARKET_INTERVAL,
        "observations": int(matrix.shape[0]),
        "asset_count": int(matrix.shape[1]),
        "mean_returns": means,
        "target_values": target_values,
        "target_range": (float(means.min()), float(means.max())),
        "settings": dict(MARKET_PSO_SETTINGS),
        "seeds": MARKET_SEEDS,
        "runs": runs,
        "elapsed_seconds": time.perf_counter() - started,
    }


def evaluate_extreme_cases() -> list[dict[str, Any]]:
    """Return explicit expected outcomes for diagnostic simplex edge cases."""
    cases = [
        ("zero_vector", "invalid", "Reparar a uniforme o rechazar explícitamente"),
        ("negative_weights", "extreme_valid_input", "Eliminar negativos y normalizar"),
        ("sum_not_one", "extreme_valid_input", "Normalizar tras recortar"),
        ("simplex_vertices", "valid", "Conservar factibilidad"),
        ("target_minimum", "valid", "Puede alcanzarse en un extremo"),
        ("target_maximum", "valid", "Puede alcanzarse en un extremo"),
        ("target_intermediate", "valid", "Evaluar brecha y riesgo"),
        ("target_outside_range", "difficult_optimization", "No recortar el objetivo"),
        ("concentrated_weights", "extreme_valid_input", "Medir concentración"),
        ("stable_initial_fitness", "difficult_optimization", "No llamarlo fallo sin métricas"),
        ("constant_returns", "difficult_optimization", "Esperar riesgo degenerado"),
        ("exact_repeat", "valid", "Reproducibilidad con misma semilla"),
    ]
    return [
        {"case": name, "classification": classification, "expected": expected}
        for name, classification, expected in cases
    ]
