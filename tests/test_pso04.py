import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.finance import annualized_return, calculate_portfolio_metrics, max_drawdown
from src.pso.fitness_function import CVaR, VaR
from src.utils import load_crypto_returns


class TestPSO04FinancialConventions(unittest.TestCase):
    def test_price_loader_returns_observation_log_returns_and_drops_first_row(self) -> None:
        prices = pd.DataFrame(
            {
                "AAA": [100.0, 110.0, 99.0],
                "BBB": [200.0, 220.0, 242.0],
            },
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )
        with patch("src.utils.yf.download", return_value={"Close": prices}) as download:
            mean_return, returns_matrix, returns_index = load_crypto_returns(
                ["AAA", "BBB"], start="2024-01-01", end="2024-01-04", interval="1d"
            )

        download.assert_called_once_with(
            ["AAA", "BBB"],
            start="2024-01-01",
            end="2024-01-04",
            interval="1d",
            progress=False,
        )
        expected = np.log(prices / prices.shift(1)).dropna()
        np.testing.assert_allclose(returns_matrix, expected.to_numpy())
        np.testing.assert_allclose(mean_return, expected.mean(axis=0).to_numpy())
        self.assertEqual(list(returns_index), list(expected.index))

    def test_portfolio_return_is_weighted_sum_of_asset_log_returns(self) -> None:
        returns = np.array([[np.log(1.1), np.log(0.9)]], dtype=float)
        metrics = calculate_portfolio_metrics(
            returns_matrix=returns,
            weights=np.array([0.25, 0.75]),
            cvar_alpha=0.5,
        )

        expected_log_return = 0.25 * np.log(1.1) + 0.75 * np.log(0.9)
        self.assertAlmostEqual(metrics["mean_return"], expected_log_return, places=14)
        self.assertAlmostEqual(
            np.exp(np.log(1.1)) - 1,
            0.1,
            places=14,
        )
        self.assertNotAlmostEqual(
            np.exp(expected_log_return) - 1,
            0.25 * 0.1 + 0.75 * -0.1,
            places=4,
        )

    def test_var_and_cvar_use_lower_percentile_and_include_threshold_ties(self) -> None:
        returns = np.array([[-0.2], [-0.1], [-0.1], [0.2]], dtype=float)
        position = np.array([1.0])

        cvar = CVaR(alpha=0.5, penalty=0.0).evaluate(position, returns, 0.0)
        var = VaR(alpha=0.5, penalty=0.0).evaluate(position, returns, 0.0)
        metrics = calculate_portfolio_metrics(
            returns_matrix=returns,
            weights=position,
            cvar_alpha=0.5,
        )

        # The 50th percentile is -0.1; <= includes both tied threshold values.
        self.assertAlmostEqual(cvar, (0.2 + 0.1 + 0.1) / 3, places=14)
        self.assertAlmostEqual(var, 0.1, places=14)
        self.assertAlmostEqual(metrics["cvar"], (0.2 + 0.1 + 0.1) / 3, places=14)
        self.assertAlmostEqual(metrics["var"], 0.1, places=14)

    def test_finance_metrics_use_positive_loss_signs_and_simple_return_drawdown(self) -> None:
        returns = np.array([[0.1], [-0.2], [0.1]], dtype=float)

        # Wealth is [1.1, 0.88, 0.968], so the maximum drawdown is 20%.
        self.assertAlmostEqual(max_drawdown(returns[:, 0]), 0.2, places=14)

    def test_annualization_is_simple_return_compounding_with_252_periods_by_default(
        self,
    ) -> None:
        self.assertAlmostEqual(annualized_return(0.01, periods_per_year=2), 0.0201)
        self.assertAlmostEqual(annualized_return(0.01), (1.01**252) - 1)

    def test_fitness_combines_positive_cvar_risk_and_per_period_target_penalty(self) -> None:
        returns = np.array([[-0.2], [-0.1], [0.1], [0.2]], dtype=float)
        fitness = CVaR(alpha=0.5, penalty=50.0).evaluate(
            np.array([1.0]), returns, target_value=0.15
        )

        # Mean return is 0.0, lower-tail risk is 0.15, and the target gap is
        # 0.15 in the same per-observation log-return units.
        self.assertAlmostEqual(fitness, 0.15 + 50.0 * 0.15, places=14)


if __name__ == "__main__":
    unittest.main()
