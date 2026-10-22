import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from streamlit.testing.v1 import AppTest

import validation_dashboard
from validation_dashboard_logic import CONVERGENCE_SEEDS, run_validation_suite


class TestValidationDashboard(unittest.TestCase):
    def test_fresh_import_does_not_execute_pso(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        script = """
import src.pso

def fail_if_called(*args, **kwargs):
    raise AssertionError("PSO executed during import")

src.pso.pso = fail_if_called
import validation_dashboard_logic
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
        self.assertEqual([button.label for button in app.button], [
            "Ejecutar validación",
            "Repetir validación",
        ])

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


if __name__ == "__main__":
    unittest.main()
