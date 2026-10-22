import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from streamlit.testing.v1 import AppTest

import validation_dashboard
from validation_dashboard_logic import (
    CONVERGENCE_SEEDS,
    MARKET_SEEDS,
    MARKET_TARGETS,
    evaluate_extreme_cases,
    run_market_diagnostic,
    run_validation_suite,
)


class TestValidationDashboard(unittest.TestCase):
    def test_fresh_import_does_not_execute_pso(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        script = """
import src.pso
import src.utils

def fail_if_called(*args, **kwargs):
    raise AssertionError("PSO executed during import")

src.pso.pso = fail_if_called
src.utils.load_crypto_returns = fail_if_called
import validation_dashboard_logic
import validation_dashboard
print("fresh import ok")
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(repository)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("fresh import ok", completed.stdout)

    def test_suite_uses_fixed_cases_and_returns_passed_results(self) -> None:
        results = run_validation_suite()

        self.assertEqual(results["summary"]["cases"], 6)
        self.assertEqual(results["summary"]["passed"], 6)
        self.assertTrue(results["feasibility"]["ok"])
        self.assertTrue(results["sphere"]["ok"])
        self.assertTrue(results["minimum_variance"]["ok"])
        self.assertTrue(results["manual_cvar"]["ok"])
        self.assertTrue(results["reproducibility"]["ok"])
        self.assertTrue(np.all(np.isfinite(results["feasibility"]["weights"])))

    def test_suite_has_no_repository_persistence_or_network_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory, patch(
            "socket.create_connection",
            side_effect=AssertionError("network access was requested"),
        ), patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("network access was requested"),
        ):
            before = set(Path(temporary_directory).iterdir())
            with patch.dict(os.environ, {"HOME": temporary_directory}):
                original_directory = Path.cwd()
                os.chdir(temporary_directory)
                try:
                    run_validation_suite()
                finally:
                    os.chdir(original_directory)
            after = set(Path(temporary_directory).iterdir())
        self.assertEqual(before, after)

    def test_convergence_uses_paired_seeds_and_fixed_configuration(self) -> None:
        results = run_validation_suite()
        self.assertEqual(tuple(results["convergence"]["seeds"]), CONVERGENCE_SEEDS)
        ring_runs = results["convergence"]["runs"]["Ring"]
        global_runs = results["convergence"]["runs"]["Global"]
        self.assertEqual(
            [run["seed"] for run in ring_runs],
            [run["seed"] for run in global_runs],
        )
        self.assertEqual(len(ring_runs), len(CONVERGENCE_SEEDS))
        self.assertEqual(results["settings"], run_validation_suite()["settings"])

    def test_streamlit_initial_state_and_explicit_execution(self) -> None:
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "validation_dashboard.py")
        )
        app.run()
        self.assertIn("Aún no hay resultados", app.info[1].value)
        self.assertNotIn("summary", app.session_state)
        app.button[0].click().run()
        self.assertIn("validation_results", app.session_state)
        self.assertTrue(app.session_state["validation_results"]["summary"]["passed"])
        self.assertEqual(
            [button.label for button in app.button],
            [
                "Ejecutar validación",
                "Repetir validación",
                "Ejecutar diagnóstico con datos reales",
            ],
        )

    def test_streamlit_repeat_replaces_results(self) -> None:
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "validation_dashboard.py")
        )
        app.run()
        app.button[0].click().run()
        first = app.session_state["validation_results"]
        app.button[1].click().run()
        second = app.session_state["validation_results"]
        self.assertIsNot(first, second)
        self.assertEqual(first["summary"]["passed"], second["summary"]["passed"])
        self.assertEqual(first["convergence"]["seeds"], second["convergence"]["seeds"])

    def test_failed_execution_invalidates_previous_results_and_reports_error(self) -> None:
        state = {}
        errors: list[str] = []
        successful_result = {"summary": {"passed": 6}}

        with patch.object(
            validation_dashboard,
            "st",
            session_state=state,
            error=errors.append,
        ), patch.object(
            validation_dashboard,
            "run_validation_suite",
            side_effect=[successful_result, RuntimeError("synthetic failure")],
        ):
            self.assertTrue(validation_dashboard._execute_validation())
            self.assertIs(state["validation_results"], successful_result)

            self.assertFalse(validation_dashboard._execute_validation())

        self.assertIsNone(state["validation_results"])
        self.assertEqual(errors, ["No se pudo completar la validación: synthetic failure"])

    def test_failed_market_execution_invalidates_previous_results(self) -> None:
        state = {"market_diagnostic_results": {"old": True}}
        errors: list[str] = []
        with patch.object(
            validation_dashboard,
            "st",
            session_state=state,
            error=errors.append,
        ), patch.object(
            validation_dashboard,
            "run_market_diagnostic",
            side_effect=RuntimeError("market failure"),
        ):
            self.assertFalse(validation_dashboard._execute_market_diagnostic())
        self.assertIsNone(state["market_diagnostic_results"])
        self.assertEqual(
            errors, ["No se pudo completar el diagnóstico de mercado: market failure"]
        )

    def test_convergence_contains_available_diagnostics_without_fake_zeros(self) -> None:
        results = run_validation_suite()

        for runs in results["convergence"]["runs"].values():
            for diagnostic in runs:
                self.assertGreater(diagnostic["iterations_completed"], 0)
                self.assertEqual(
                    len(diagnostic["iterations"]), len(diagnostic["gbest"])
                )
                self.assertTrue(np.all(np.isfinite(diagnostic["diversity"])))
                self.assertTrue(np.all(np.isfinite(diagnostic["movement_mean"])))

    def test_market_diagnostic_uses_mocked_loader_and_paired_runs(self) -> None:
        trace = SimpleNamespace(
            iterations=np.array([0.0, 1.0]),
            gbest=np.array([1.0, 0.5]),
            diversity=np.array([0.2, 0.1]),
            diversity_relative=np.array([1.0, 0.5]),
            movement_mean=np.array([0.1, 0.05]),
            movement_max=np.array([0.2, 0.1]),
            repairs=np.array([2.0, 0.0]),
            weight_sum_min=np.array([1.0, 1.0]),
            weight_sum_max=np.array([1.0, 1.0]),
            invalid_values=np.array([0.0, 0.0]),
            best_target_difference=np.array([0.01, 0.0]),
            termination_reason="patience",
            termination_iteration=1,
            iterations_completed=2,
            initial_diversity=0.2,
        )
        calls: list[dict] = []

        def loader(assets, start, end, interval):
            self.assertEqual(assets, ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"])
            self.assertEqual((start, end, interval), ("2020-01-01", "2024-01-01", "1d"))
            return (
                np.array([0.01, 0.02, 0.03, 0.04]),
                np.array([[0.01, 0.02, 0.03, 0.04]] * 5),
                np.arange(5),
            )

        def fake_pso(**kwargs):
            calls.append(kwargs)
            return 1.5, np.full(4, 0.25), np.empty((2, 2)), np.empty(3), trace

        with patch("validation_dashboard_logic.pso", side_effect=fake_pso):
            result = run_market_diagnostic(data_loader=loader, retrieved_at="fixed")

        self.assertEqual(result["retrieved_at"], "fixed")
        self.assertEqual(result["observations"], 5)
        self.assertEqual(result["seeds"], MARKET_SEEDS)
        self.assertEqual(tuple(result["runs"]), MARKET_TARGETS)
        self.assertEqual(result["target_values"]["minimum"], 0.01)
        self.assertEqual(result["target_values"]["intermediate"], 0.025)
        self.assertEqual(len(calls), len(MARKET_SEEDS) * 2 * len(MARKET_TARGETS))
        for target_name in MARKET_TARGETS:
            self.assertEqual(
                [call["topology"].__class__.__name__ for call in calls[
                    (0 if target_name == "minimum" else 6): (6 if target_name == "minimum" else 12)
                ]],
                ["RingTopology", "GlobalTopology"] * len(MARKET_SEEDS),
            )
            for topology_runs in result["runs"][target_name].values():
                self.assertEqual([run["seed"] for run in topology_runs], list(MARKET_SEEDS))
                self.assertEqual(
                    topology_runs[0]["target_gap_history"].tolist(), [0.01, 0.0]
                )

    def test_market_loader_validation_rejects_mismatched_shapes(self) -> None:
        with self.assertRaisesRegex(ValueError, "no coincide"):
            run_market_diagnostic(
                data_loader=lambda assets, start, end, interval: (
                    np.array([0.1]),
                    np.ones((2, 2)),
                    np.arange(2),
                )
            )

    def test_extreme_cases_have_explicit_expectations(self) -> None:
        cases = evaluate_extreme_cases()
        self.assertEqual(len(cases), 12)
        self.assertEqual(cases[0]["classification"], "invalid")
        self.assertEqual(cases[-1]["case"], "exact_repeat")


if __name__ == "__main__":
    unittest.main()
