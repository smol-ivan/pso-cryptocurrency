#[derive(Debug, Clone, PartialEq)]
pub struct Evaluation {
    pub fitness: f64,
    pub expected_return: f64,
    pub risk: f64,
    pub penalty: f64,
    pub shortfall: f64,
    pub feasible: bool,
}

impl Default for Evaluation {
    /// Placeholder for a particle that has no being evaluated yet.
    ///
    /// Only 'fitness' is meaningful (INFINITY, so any real evaluation
    /// improves on it.). The remaining fields are NaN to mark them unknown.
    fn default() -> Self {
        Evaluation {
            fitness: f64::INFINITY,
            expected_return: f64::NAN,
            risk: f64::NAN,
            penalty: f64::NAN,
            shortfall: f64::NAN,
            feasible: false,
        }
    }
}
