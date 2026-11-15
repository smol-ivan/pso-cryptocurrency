use ndarray::{Array1, Array2};
use serde::{Deserialize, Serialize};

use crate::domain::{Evaluation, Weights};

pub trait RiskMeasure: Send + Sync {
    fn name(&self) -> &'static str;

    fn params(&self) -> serde_json::Value;

    fn risk(&self, portfolio_returns: &Array1<f64>) -> f64;
}

/// Defines the interface for portfolio risk and fitness evaluation.
///
/// Implementations provide a risk measure and a fitness function used
/// by the PSO algorithm to evaluate candidate portfolio allocations.
pub trait FitnessFunction: Send + Sync {
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
    fn get_fitness(
        &self,
        position: &Weights,
        returns: &Array2<f64>,
        target_return: f64,
    ) -> Evaluation;

    fn name(&self) -> &'static str;

    fn params(&self) -> serde_json::Value;
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default)]
pub struct PenaltyParams {
    pub penalty: f64,
    pub eps: f64,
}

impl Default for PenaltyParams {
    fn default() -> Self {
        Self {
            penalty: 50.0,
            eps: 1e-6,
        }
    }
}

pub struct VarianceRisk;

impl RiskMeasure for VarianceRisk {
    fn name(&self) -> &'static str {
        "variance"
    }

    fn params(&self) -> serde_json::Value {
        serde_json::json!({})
    }

    fn risk(&self, portfolio_returns: &Array1<f64>) -> f64 {
        let mean = portfolio_returns.mean().unwrap_or(0.0);

        portfolio_returns
            .mapv(|r| (r - mean).powi(2))
            .mean()
            .unwrap_or(0.0)
    }
}

pub struct PenalizedFitness {
    pub risk: Box<dyn RiskMeasure>,
    pub params: PenaltyParams,
}

impl PenalizedFitness {
    pub fn new(risk: Box<dyn RiskMeasure>, params: PenaltyParams) -> Self {
        Self { risk, params }
    }
}

impl FitnessFunction for PenalizedFitness {
    fn get_fitness(
        &self,
        position: &Weights,
        returns: &Array2<f64>,
        target_return: f64,
    ) -> Evaluation {
        let portfolio_returns = returns.dot(position);
        let expected_return = portfolio_returns.mean().unwrap_or(0.0);
        let risk = self.risk.risk(&portfolio_returns);
        let shortfall = (target_return - expected_return).max(0.0);
        let penalty = self.params.penalty * shortfall;
        let fitness = risk + penalty;

        Evaluation {
            fitness,
            expected_return,
            risk,
            penalty,
            shortfall,
            feasible: shortfall <= self.params.eps && fitness.is_finite(),
        }
    }

    fn name(&self) -> &'static str {
        "penalized"
    }

    fn params(&self) -> serde_json::Value {
        serde_json::json!({
            "penalty": self.params.penalty,
            "eps": self.params.eps,
            "risk": {
                "name": self.risk.name(),
                "params": self.risk.params(),
            },
        })
    }
}
