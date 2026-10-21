import random
import unittest

import numpy as np

from src.experiments import ExperimentConfig, run_experiments
from src.pso import Constriction, GlobalTopology, Inertia, Variance, pso
from src.pso.particle import Particle
from src.run_pso import PSOInputData


class TestPSO01(unittest.TestCase):
    def setUp(self) -> None:
        self.returns = np.array(
            [
                [0.01, 0.02, -0.01],
                [0.02, -0.01, 0.03],
                [-0.01, 0.01, 0.02],
                [0.03, 0.00, 0.01],
            ],
            dtype=float,
        )

    def test_valid_run_preserves_weight_invariants(self) -> None:
        _, position, convergence, diversity = pso(
            returns_matrix=self.returns,
            swarm_size=4,
            target_value=0.01,
            fitness_function=Variance(),
            velocity_model=Inertia(),
            topology=GlobalTopology(),
            max_iterations=12,
        )

        self.assertTrue(np.all(position >= 0))
        self.assertAlmostEqual(float(position.sum()), 1.0)
        self.assertTrue(np.all(np.isfinite(position)))
        self.assertTrue(np.all(np.diff(convergence[:, 1]) <= 1e-15))
        self.assertEqual(diversity.shape[0], convergence.shape[0] + 1)

    def test_invalid_optimizer_inputs_raise_explicit_errors(self) -> None:
        common = dict(
            swarm_size=2,
            target_value=0.01,
            fitness_function=Variance(),
            velocity_model=Inertia(),
            topology=GlobalTopology(),
        )
        invalid_cases = (
            (np.empty((0, 2)), "returns_matrix"),
            (np.array([0.01, 0.02]), "returns_matrix"),
            (np.array([[0.01, np.nan]]), "returns_matrix"),
        )
        for returns, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    pso(returns_matrix=returns, **common)

        with self.assertRaisesRegex(ValueError, "swarm_size"):
            pso(returns_matrix=self.returns, swarm_size=0, **{k: v for k, v in common.items() if k != "swarm_size"})
        with self.assertRaisesRegex(ValueError, "target_value"):
            pso(returns_matrix=self.returns, target_value=np.inf, **{k: v for k, v in common.items() if k != "target_value"})
        with self.assertRaisesRegex(ValueError, "target_value"):
            pso(returns_matrix=self.returns, target_value="invalid", **{k: v for k, v in common.items() if k != "target_value"})
        with self.assertRaisesRegex(ValueError, "rtol"):
            pso(returns_matrix=self.returns, rtol="invalid", **common)
        with self.assertRaisesRegex(ValueError, "atol"):
            pso(returns_matrix=self.returns, atol="invalid", **common)
        with self.assertRaisesRegex(ValueError, "patience"):
            pso(returns_matrix=self.returns, patience=0, **common)
        with self.assertRaisesRegex(ValueError, "max_iterations"):
            pso(returns_matrix=self.returns, max_iterations=0, **common)

    def test_both_velocity_models_repair_null_negative_and_valid_positions(self) -> None:
        for model in (
            Inertia(c1=0.0, c2=0.0, inertia=1.0),
            Constriction(c1=2.05, c2=2.05),
        ):
            with self.subTest(model=type(model).__name__):
                null_particle = Particle(
                    position=np.array([0.5, 0.5]),
                    velocity=np.array([-1.0, -1.0]),
                    fitness_value=0.0,
                )
                model.update(null_particle, np.array([0.5, 0.5]))
                np.testing.assert_allclose(null_particle.position, [0.5, 0.5])

                negative_particle = Particle(
                    position=np.array([0.25, 0.75]),
                    velocity=np.array([-0.5, 0.0]),
                    fitness_value=0.0,
                )
                model.update(negative_particle, np.array([0.25, 0.75]))
                self.assertTrue(np.all(negative_particle.position >= 0))
                self.assertAlmostEqual(float(negative_particle.position.sum()), 1.0)

                valid_particle = Particle(
                    position=np.array([0.25, 0.75]),
                    velocity=np.zeros(2),
                    fitness_value=0.0,
                )
                model.update(valid_particle, np.array([0.25, 0.75]))
                np.testing.assert_allclose(valid_particle.position, [0.25, 0.75])

    def test_single_asset_run_returns_unit_weight(self) -> None:
        returns = np.array([[0.01], [0.02], [-0.01]], dtype=float)
        _, position, _, _ = pso(
            returns_matrix=returns,
            swarm_size=3,
            target_value=0.01,
            fitness_function=Variance(),
            velocity_model=Constriction(),
            topology=GlobalTopology(),
            max_iterations=3,
            random_generator=np.random.default_rng(7),
            python_random_generator=random.Random(7),
        )
        np.testing.assert_allclose(position, [1.0])

    def test_nonfinite_position_is_rejected_by_both_velocity_models(self) -> None:
        for model in (Inertia(), Constriction()):
            particle = Particle(
                position=np.array([np.nan, 1.0]),
                velocity=np.zeros(2),
                fitness_value=0.0,
            )
            with self.subTest(model=type(model).__name__):
                with self.assertRaisesRegex(ValueError, "finite"):
                    model.update(particle, np.array([0.5, 0.5]))

    def test_experiment_seed_reproduces_all_stochastic_outputs(self) -> None:
        config = ExperimentConfig(
            name="variance | inertia | global",
            objective_name="Variance",
            velocity_name="Inertia",
            topology_name="Global",
            fitness_function=Variance(),
            velocity_model=Inertia(),
            topology=GlobalTopology(),
            num_points=2,
            n_swarm=3,
            seed=123,
        )
        input_data = PSOInputData(
            mean_return=self.returns.mean(axis=0),
            returns_matrix=self.returns,
        )

        first = run_experiments(input_data, [config])[0].frontier
        random.seed(999)
        np.random.seed(999)
        second = run_experiments(input_data, [config])[0].frontier

        np.testing.assert_array_equal(first.target_values, second.target_values)
        np.testing.assert_array_equal(first.best_fitnesses, second.best_fitnesses)
        for first_weights, second_weights in zip(first.weights, second.weights):
            np.testing.assert_array_equal(first_weights, second_weights)
        for first_history, second_history in zip(
            first.convergence_histories, second.convergence_histories
        ):
            np.testing.assert_array_equal(first_history, second_history)

    def test_seeded_experiments_preserve_global_random_states(self) -> None:
        input_data = PSOInputData(
            mean_return=self.returns.mean(axis=0),
            returns_matrix=self.returns,
        )
        config = self._config("seeded", seed=123)
        np.random.seed(456)
        random.seed(789)
        numpy_state_before = np.random.get_state()
        python_state_before = random.getstate()

        run_experiments(input_data, [config])

        numpy_state_after = np.random.get_state()
        python_state_after = random.getstate()
        self._assert_numpy_states_equal(numpy_state_before, numpy_state_after)
        self.assertEqual(python_state_before, python_state_after)

    def test_experiment_order_does_not_change_seeded_results(self) -> None:
        input_data = PSOInputData(
            mean_return=self.returns.mean(axis=0),
            returns_matrix=self.returns,
        )
        forward = run_experiments(
            input_data,
            [self._config("first", seed=10), self._config("second", seed=20)],
        )
        reverse = run_experiments(
            input_data,
            [self._config("second", seed=20), self._config("first", seed=10)],
        )
        forward_by_name = {result.config.name: result.frontier for result in forward}
        reverse_by_name = {result.config.name: result.frontier for result in reverse}
        for name in forward_by_name:
            self._assert_frontiers_equal(forward_by_name[name], reverse_by_name[name])

    def test_replica_seeds_are_traceable_and_reproducible(self) -> None:
        input_data = PSOInputData(
            mean_return=self.returns.mean(axis=0),
            returns_matrix=self.returns,
        )
        config = self._config("replicas", seed=100, seed_count=3)
        first = run_experiments(input_data, [config])[0].frontier
        second = run_experiments(input_data, [config])[0].frontier

        self.assertEqual(first.seed_values, [100, 101, 102])
        self.assertEqual(first.seed_values, second.seed_values)
        for first_replica, second_replica in zip(first.seed_results, second.seed_results):
            self._assert_frontiers_equal(first_replica, second_replica)

    def _config(self, name: str, seed: int, seed_count: int = 1) -> ExperimentConfig:
        return ExperimentConfig(
            name=name,
            objective_name="Variance",
            velocity_name="Inertia",
            topology_name="Global",
            fitness_function=Variance(),
            velocity_model=Inertia(),
            topology=GlobalTopology(),
            num_points=2,
            n_swarm=3,
            seed=seed,
            seed_count=seed_count,
        )

    def _assert_frontiers_equal(self, first, second) -> None:
        np.testing.assert_array_equal(first.target_values, second.target_values)
        np.testing.assert_array_equal(first.best_fitnesses, second.best_fitnesses)
        for first_weights, second_weights in zip(first.weights, second.weights):
            np.testing.assert_array_equal(first_weights, second_weights)
        for first_history, second_history in zip(
            first.convergence_histories, second.convergence_histories
        ):
            np.testing.assert_array_equal(first_history, second_history)

    def _assert_numpy_states_equal(self, first, second) -> None:
        self.assertEqual(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])
        self.assertEqual(first[2:], second[2:])


if __name__ == "__main__":
    unittest.main()
