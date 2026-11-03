use ndarray::{Array1, Array2};

use crate::domain::Weights;

/// Defines the interface for portfolio risk and fitness evaluation.
///
/// Implementations provide a risk measure and a fitness function used
/// by the PSO algorithm to evaluate candidate portfolio allocations.
pub trait FitnessFunction {
    /// Calculates the portfolio risk from its historical returns.
    ///
    /// # Arguments
    ///
    /// * `portfolio_returns` - Historical returns of the portfolio.
    ///
    /// # Returns
    ///
    /// A scalar value representing the portfolio risk.
    fn calculate_risk(&self, portfolio_returns: Array1<f64>) -> f64;

    /// Evaluates a portfolio allocation against a target return.
    ///
    /// # Arguments
    ///
    /// * `position` - Portfolio weights assigned to each asset.
    /// * `returns` - Historical asset returns, with observations as rows
    ///   and assets as columns.
    /// * `target_return` - Minimum expected portfolio return.
    ///
    /// # Returns
    ///
    /// A fitness value representing the portfolio risk combined with
    /// any penalty for failing to meet the target return.
    fn get_fitness(&self, position: &Weights, returns: &Array2<f64>, target_return: f64) -> f64;
}

/// Portfolio fitness function based on variance minimization.
///
/// The fitness value combines portfolio variance with a penalty for
/// failing to achieve the specified target return.
pub struct Variance {
    /// Penalty coefficient applied when the target return is not met.
    pub penalty: f64,
}

impl Default for Variance {
    /// Creates a variance fitness function with a default penalty of 50.0.
    // TODO: Evaluate penalty sensitivity across different return scales
    // and dataset frequencies.
    fn default() -> Self {
        Self { penalty: 50. }
    }
}

impl FitnessFunction for Variance {
    /// Calculates the portfolio variance from its historical returns.
    ///
    /// Variance is computed as the mean squared deviation of portfolio
    /// returns from their arithmetic mean.
    ///
    /// # Arguments
    ///
    /// * `portfolio_returns` - Historical portfolio returns.
    ///
    /// # Returns
    ///
    /// The population variance of the portfolio returns.
    fn calculate_risk(&self, portfolio_returns: Array1<f64>) -> f64 {
        // TODO: This could cause problems in edge cases
        let mean = portfolio_returns.mean().unwrap_or(0.0);

        portfolio_returns
            .mapv(|r| (r - mean).powi(2))
            .mean()
            .unwrap_or(0.0)
    }

    // Evaluates a portfolio allocation using variance and a target return penalty.
    ///
    /// Portfolio returns are calculated by multiplying the asset return matrix
    /// by the portfolio weight vector. The fitness value combines portfolio
    /// variance with a penalty proportional to any shortfall below the
    /// target return.
    ///
    /// The penalty is one-sided: portfolio allocations exceeding the target
    /// return receive no additional penalty.
    ///
    /// The fitness function is designed for minimization.
    ///
    /// # Arguments
    ///
    /// * `position` - Portfolio weight vector.
    /// * `returns` - Historical asset return matrix.
    /// * `target_return` - Minimum expected portfolio return.
    ///
    /// # Returns
    ///
    /// Portfolio variance plus the weighted target return shortfall penalty.
    // TODO: Validate matrix dimensions, empty inputs, and non-finite values.
    // TODO: Review error handling for invalid portfolio allocations.
    fn get_fitness(&self, position: &Weights, returns: &Array2<f64>, target_return: f64) -> f64 {
        // R * w
        let portfolio_returns = returns.dot(position);
        // expected return
        let expected_return = portfolio_returns.mean().unwrap_or(0.0);

        let risk = self.calculate_risk(portfolio_returns);

        let return_shortfall = (target_return - expected_return).max(0.0);

        risk + self.penalty * return_shortfall
    }
}
