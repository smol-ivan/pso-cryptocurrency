use ndarray::{Array2, array};
use pso_cryptocurrency::domain::Evaluation;
use pso_cryptocurrency::optimizer::pso::{
    FitnessFunction, PenalizedFitness, PenaltyParams, RiskMeasure, VarianceRisk,
};

/// The composed implementation retains the previous population-variance calculation.
#[test]
fn penalized_variance_matches_legacy_evaluation() {
    let returns: Array2<f64> = array![
        [0.01, 0.02, -0.01],
        [0.03, -0.02, 0.04],
        [-0.01, 0.01, 0.02],
        [0.02, 0.03, -0.03],
    ];
    let weights = array![0.2, 0.5, 0.3];
    let fitness = PenalizedFitness::new(
        Box::new(VarianceRisk),
        PenaltyParams {
            penalty: 50.0,
            eps: 1e-6,
        },
    );

    let portfolio_returns = returns.dot(&weights);
    let expected_return = portfolio_returns.mean().unwrap_or(0.0);
    let risk = portfolio_returns
        .mapv(|value| (value - expected_return).powi(2))
        .mean()
        .unwrap_or(0.0);
    let shortfall = (0.02 - expected_return).max(0.0);
    let penalty = 50.0 * shortfall;
    let expected = Evaluation {
        fitness: risk + penalty,
        expected_return,
        risk,
        penalty,
        shortfall,
        feasible: shortfall <= 1e-6,
    };

    assert_eq!(fitness.get_fitness(&weights, &returns, 0.02), expected);
}

/// Both component layers report the values that will be used at runtime.
#[test]
fn params_report_effective_values() {
    let risk = VarianceRisk;
    assert_eq!(risk.name(), "variance");
    assert_eq!(risk.params(), serde_json::json!({}));

    let fitness = PenalizedFitness::new(
        Box::new(risk),
        PenaltyParams {
            penalty: 25.0,
            eps: 0.0001,
        },
    );
    assert_eq!(
        fitness.params(),
        serde_json::json!({
            "penalty": 25.0,
            "eps": 0.0001,
            "risk": {
                "name": "variance",
                "params": {},
            },
        })
    );
}
