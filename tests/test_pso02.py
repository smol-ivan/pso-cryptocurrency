import unittest

import numpy as np
import pandas as pd

from src.experiments import ExperimentConfig, run_experiments
from src.persistence import export_payload_to_bytes, import_payload_from_bytes
from src.pso import GlobalTopology, Inertia, Variance
from src.run_pso import PSOInputData


class TestPSO02Diagnostics(unittest.TestCase):
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

    def _config(self, *, max_iterations: int = 8, patience: int = 10) -> ExperimentConfig:
        # max_iterations is exercised through the optimizer directly below;
        # ExperimentConfig preserves the existing public experiment contract.
        return ExperimentConfig(
            name="diagnostics",
            objective_name="Variance",
            velocity_name="Inertia",
            topology_name="Global",
            fitness_function=Variance(),
            velocity_model=Inertia(c1=0.0, c2=0.0, inertia=1.0),
            topology=GlobalTopology(),
            num_points=1,
            n_swarm=3,
            patience=patience,
            seed=17,
        )

    def test_trace_has_aligned_finite_generation_metrics(self) -> None:
        from src.pso import pso

        result = pso(
            returns_matrix=self.returns,
            swarm_size=3,
            target_value=0.01,
            fitness_function=Variance(),
            velocity_model=Inertia(c1=0.0, c2=0.0, inertia=1.0),
            topology=GlobalTopology(),
            max_iterations=8,
            return_diagnostics=True,
        )
        convergence, diversity, trace = result[2:]

        self.assertEqual(trace.termination_reason, "max_iterations")
        self.assertEqual(trace.iterations_completed, len(convergence))
        self.assertEqual(len(diversity), len(convergence) + 1)
        self.assertEqual(trace.gbest.shape, trace.current_mean.shape)
        self.assertTrue(np.all(np.isfinite(trace.gbest)))
        self.assertTrue(np.all(np.diff(trace.gbest) <= 1e-15))
        np.testing.assert_allclose(trace.movement_mean, 0.0, atol=1e-15)
        np.testing.assert_allclose(trace.diversity, trace.initial_diversity)
        self.assertTrue(np.all(trace.repairs >= 0))
        self.assertTrue(np.all(trace.invalid_values == 0))

    def test_patience_reason_records_completed_iteration_and_wait(self) -> None:
        from src.pso import pso

        result = pso(
            returns_matrix=self.returns,
            swarm_size=3,
            target_value=0.01,
            fitness_function=Variance(),
            velocity_model=Inertia(c1=0.0, c2=0.0, inertia=1.0),
            topology=GlobalTopology(),
            patience=2,
            max_iterations=20,
            return_diagnostics=True,
        )
        trace = result[-1]

        self.assertEqual(trace.termination_reason, "patience")
        self.assertEqual(trace.iterations_completed, 8)
        self.assertEqual(trace.termination_iteration, 7)
        self.assertEqual(trace.patience_wait[-1], 2)
        self.assertEqual(trace.last_significant_improvement[-1], -1)

    def test_diagnostics_round_trip_and_legacy_frontier_compatibility(self) -> None:
        input_data = PSOInputData(
            mean_return=self.returns.mean(axis=0),
            returns_matrix=self.returns,
        )
        result = run_experiments(input_data, [self._config()])[0]
        payload = {
            "assets": ["A", "B", "C"],
            "start_date": "2020-01-01",
            "end_date": "2020-01-05",
            "interval": "1d",
            "alpha": 0.95,
            "returns_matrix": self.returns,
            "returns_index": pd.Index(["a", "b", "c", "d"]),
            "experiments": [result],
            "metrics_by_config": {},
        }

        restored = import_payload_from_bytes(export_payload_to_bytes(payload))
        restored_trace = restored["experiments"][0].frontier.diagnostic_histories[0]
        original_trace = result.frontier.diagnostic_histories[0]
        self.assertEqual(restored_trace.termination_reason, original_trace.termination_reason)
        np.testing.assert_array_equal(restored_trace.gbest, original_trace.gbest)
        np.testing.assert_array_equal(
            restored_trace.movement_mean, original_trace.movement_mean
        )

        legacy = dict(payload)
        legacy["experiments"] = [{
            "config": result.config,
            "frontier": type(result.frontier)(
                target_values=result.frontier.target_values,
                weights=result.frontier.weights,
                best_fitnesses=result.frontier.best_fitnesses,
                convergence_histories=result.frontier.convergence_histories,
            ),
        }]
        imported_legacy = import_payload_from_bytes(export_payload_to_bytes(legacy))
        self.assertIsNone(imported_legacy["experiments"][0].frontier.diagnostic_histories)


if __name__ == "__main__":
    unittest.main()
