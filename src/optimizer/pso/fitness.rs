use ndarray::{Array1, Array2};

use crate::domain::Weights;

pub trait FitnessFunction {
    fn calculate_risk(&self, portfolio_returns: Array1<f64>) -> f64;
    fn get_fitness(&self, position: &Weights, returns: &Array2<f64>, target_return: f64) -> f64;
}

pub struct Variance {
    pub penalty: f64,
}

impl Default for Variance {
    fn default() -> Self {
        Self { penalty: 50. }
    }
}

impl FitnessFunction for Variance {
    fn calculate_risk(&self, portfolio_returns: Array1<f64>) -> f64 {
        let mean = portfolio_returns.mean().unwrap_or(0.0);

        portfolio_returns
            .mapv(|r| (r - mean).powi(2))
            .mean()
            .unwrap_or(0.0)
    }

    /// As we get the risk raw value, we also give punishment
    /// to those particles that do not meet the target
    ///
    /// TODO: Validate for fault dimensions, empty matrix, infinity values
    fn get_fitness(&self, position: &Weights, returns: &Array2<f64>, target_return: f64) -> f64 {
        // R * w
        let portfolio_returns = returns.dot(position);
        // expected return
        let expected_return = portfolio_returns.mean().unwrap_or(0.0);

        let risk = self.calculate_risk(portfolio_returns);

        let sum_error = (target_return - expected_return).max(0.0);

        risk + self.penalty * sum_error
    }
}
