use ndarray::{Array2, array};
use ndarray_rand::rand::SeedableRng;
use ndarray_rand::rand::rngs::StdRng;
use pso_cryptocurrency::domain::{Evaluation, Weights};
use pso_cryptocurrency::optimizer::pso::{
    FitnessFunction, InertiaM, InertiaParams, PenalizedFitness, PenaltyParams, Pso, VarianceRisk,
};

struct LegacyVariance {
    penalty: f64,
    eps: f64,
}

impl FitnessFunction for LegacyVariance {
    fn get_fitness(
        &self,
        position: &Weights,
        returns: &Array2<f64>,
        target_return: f64,
    ) -> Evaluation {
        let portfolio_returns = returns.dot(position);
        let expected_return = portfolio_returns.mean().unwrap_or(0.0);
        let risk = portfolio_returns
            .mapv(|value| (value - expected_return).powi(2))
            .mean()
            .unwrap_or(0.0);
        let shortfall = (target_return - expected_return).max(0.0);
        let penalty = self.penalty * shortfall;

        Evaluation {
            fitness: risk + penalty,
            expected_return,
            risk,
            penalty,
            shortfall,
            feasible: shortfall <= self.eps,
        }
    }

    fn name(&self) -> &'static str {
        "variance"
    }

    fn params(&self) -> serde_json::Value {
        serde_json::json!({
            "penalty": self.penalty,
            "eps": self.eps,
        })
    }
}

/// A fixed seed produces the same best fitness before and after composition.
#[test]
fn replacement_preserves_seeded_optimization_result() {
    let returns = array![
        [0.01, 0.02, -0.01],
        [0.03, -0.02, 0.04],
        [-0.01, 0.01, 0.02],
        [0.02, 0.03, -0.03],
    ];
    let velocity = InertiaParams {
        c1: 0.5,
        c2: 0.9,
        inertia: 0.8,
    };

    let mut legacy_pso = Pso::new(
        Box::new(LegacyVariance {
            penalty: 50.0,
            eps: 1e-6,
        }),
        Box::new(InertiaM::new(velocity.clone())),
        3,
        5,
        returns.clone(),
        0.02,
        10,
        StdRng::seed_from_u64(7),
    );
    let mut replacement_pso = Pso::new(
        Box::new(PenalizedFitness::new(
            Box::new(VarianceRisk),
            PenaltyParams {
                penalty: 50.0,
                eps: 1e-6,
            },
        )),
        Box::new(InertiaM::new(velocity)),
        3,
        5,
        returns,
        0.02,
        10,
        StdRng::seed_from_u64(7),
    );

    let legacy_best = legacy_pso.optimization().unwrap();
    let replacement_best = replacement_pso.optimization().unwrap();

    assert_eq!(
        legacy_best.best_eval.fitness,
        replacement_best.best_eval.fitness
    );
}
