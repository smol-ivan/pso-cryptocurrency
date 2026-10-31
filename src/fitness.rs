use crate::types::Weights;

pub trait FitnessFunction {
    fn calculate_risk(&self, position: &Weights) -> f64;
    fn get_fitness(&self, position: &Weights) -> f64;
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
    fn calculate_risk(&self, position: &Weights) -> f64 {
        // TODO: swarm size value should be know for the calculations
        let n = position.len() as f64;
        if n == 0.0 {
            return 0.0;
        }

        let mean = position.mean().unwrap_or(0.0);
        let var = position.mapv(|x| (x - mean).powi(2)).sum() / n;

        var
    }

    /// As we get the risk raw value, we also give punishment
    /// to those particles that do not meet the target
    ///
    /// TODO: Pending to recieve target value, subject yet to
    /// risk or profit/return
    fn get_fitness(&self, position: &Weights) -> f64 {
        let risk = self.calculate_risk(&position);

        let sum_error = (position.sum() - 1.0).powi(2);

        risk + self.penalty * sum_error
    }
}
