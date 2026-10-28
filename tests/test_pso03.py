import inspect
import random
import unittest

import numpy as np

from src.services.experiment_service import build_experiment_configs
from src.pso import FitnessFunction, GlobalTopology, Inertia, Variance, pso
from src.pso.fitness_function import CVaR


class SimplexSphere(FitnessFunction):
    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        uniform = np.full(position.size, 1.0 / position.size)
        return float(np.sum((position - uniform) ** 2))


class FixedCovarianceVariance(FitnessFunction):
    def __init__(self, covariance: np.ndarray) -> None:
        self.covariance = covariance

    def evaluate(
        self, position: np.ndarray, returns_matrix: np.ndarray, target_value: float
    ) -> float:
        return float(position @ self.covariance @ position)


def long_only_minimum_variance(covariance: np.ndarray) -> tuple[np.ndarray, float]:
    """Enumerate KKT candidates for every non-empty active set."""
    n_assets = covariance.shape[0]
    candidates: list[tuple[np.ndarray, float]] = []
    for mask in range(1, 1 << n_assets):
        support = [index for index in range(n_assets) if mask & (1 << index)]
        sub_covariance = covariance[np.ix_(support, support)]
        unconstrained = np.linalg.solve(
            sub_covariance, np.ones(len(support), dtype=float)
        )
        support_weights = unconstrained / unconstrained.sum()
        if np.all(support_weights >= -1e-12):
            weights = np.zeros(n_assets, dtype=float)
            weights[support] = support_weights
            value = float(weights @ covariance @ weights)
            candidates.append((weights, value))
    return min(candidates, key=lambda candidate: candidate[1])


class TestPSO03ReferenceValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.covariance = np.array(
            [
                [0.04, 0.01, 0.00],
                [0.01, 0.09, 0.02],
                [0.00, 0.02, 0.16],
            ],
            dtype=float,
        )
        self.synthetic_returns = np.zeros((2, 3), dtype=float)

    def test_simplex_sphere_reaches_known_uniform_optimum(self) -> None:
        for seed in (11, 12, 13, 14, 15):
            with self.subTest(seed=seed):
                result = pso(
                    returns_matrix=np.zeros((2, 4), dtype=float),
                    swarm_size=30,
                    target_value=0.0,
                    fitness_function=SimplexSphere(),
                    velocity_model=Inertia(c1=1.7, c2=1.7, inertia=0.8),
                    topology=GlobalTopology(),
                    max_iterations=200,
                    random_generator=np.random.default_rng(seed),
                    python_random_generator=random.Random(seed),
                    return_diagnostics=True,
                )
                fitness, position, _, _, trace = result
                self.assertLessEqual(fitness, 1e-4)
                np.testing.assert_allclose(
                    position, np.full(4, 0.25), atol=1e-2
                )
                self.assertTrue(np.all(np.diff(trace.gbest) <= 1e-15))
                self.assertTrue(np.all(np.isfinite(trace.gbest)))

    def test_long_only_minimum_variance_matches_independent_reference(self) -> None:
        reference_weights, reference_value = long_only_minimum_variance(
            self.covariance
        )
        np.testing.assert_allclose(
            reference_weights, [0.6461538462, 0.2051282051, 0.1487179487], atol=1e-9
        )
        self.assertAlmostEqual(reference_value, 0.027897435897435898, places=14)

        observed_gaps = []
        for seed in (11, 12, 13, 14, 15):
            with self.subTest(seed=seed):
                fitness, position, convergence, _ = pso(
                    returns_matrix=self.synthetic_returns,
                    swarm_size=50,
                    target_value=0.0,
                    fitness_function=FixedCovarianceVariance(self.covariance),
                    velocity_model=Inertia(c1=1.7, c2=1.7, inertia=0.8),
                    topology=GlobalTopology(),
                    max_iterations=300,
                    random_generator=np.random.default_rng(seed),
                    python_random_generator=random.Random(seed),
                )
                observed_gaps.append((fitness - reference_value) / reference_value)
                self.assertTrue(np.all(position >= 0))
                self.assertAlmostEqual(float(position.sum()), 1.0, places=12)
                self.assertTrue(np.all(np.isfinite(position)))
                self.assertTrue(np.all(np.diff(convergence[:, 1]) <= 1e-15))
        self.assertLess(max(observed_gaps), 1e-4)

    def test_cvar_matches_manual_tail_and_penalty_calculation(self) -> None:
        returns = np.array([[-0.2], [-0.1], [0.1], [0.2]], dtype=float)
        fitness = CVaR(alpha=0.50, penalty=50.0)

        # Percentile at 50% is 0.0; the two lower-tail observations have mean
        # -0.15, so positive CVaR risk is 0.15.
        self.assertAlmostEqual(
            fitness.evaluate(np.array([1.0]), returns, target_value=0.0),
            0.15,
            places=14,
        )
        self.assertAlmostEqual(
            fitness.evaluate(np.array([1.0]), returns, target_value=0.15),
            7.65,
            places=14,
        )

    def test_streamlit_reference_profile_reaches_config_objects(self) -> None:
        configs = build_experiment_configs(
            ["CVaR"],
            ["Inertia"],
            ["Ring", "Global"],
            alpha=0.95,
            penalty=500.0,
            c1=1.7,
            c2=1.7,
            inertia=0.8,
            num_points=30,
            n_swarm=100,
            rtol=1e-4,
            atol=1e-8,
            patience=10,
            base_seed=42,
            seed_count=1,
        )

        self.assertEqual([config.topology_name for config in configs], ["Ring", "Global"])
        for config_index, config in enumerate(configs):
            self.assertEqual(config.num_points, 30)
            self.assertEqual(config.n_swarm, 100)
            self.assertEqual(config.rtol, 1e-4)
            self.assertEqual(config.atol, 1e-8)
            self.assertEqual(config.patience, 10)
            self.assertEqual(config.seed, 42 + config_index)
            self.assertEqual(config.seed_count, 1)
            self.assertIsInstance(config.fitness_function, CVaR)
            self.assertEqual(config.fitness_function.alpha, 0.95)
            self.assertEqual(config.fitness_function.penalty, 500.0)
            self.assertEqual(config.velocity_model.c1, 1.7)
            self.assertEqual(config.velocity_model.c2, 1.7)
            self.assertEqual(config.velocity_model.inertia, 0.8)

        self.assertEqual(inspect.signature(pso).parameters["max_iterations"].default, 1000)
        self.assertNotIn("max_iterations", config.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
