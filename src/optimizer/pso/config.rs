use serde::{Deserialize, Serialize};

use super::{
    FitnessFunction, InertiaM, InertiaParams, PenalizedFitness, PenaltyParams, RiskMeasure,
    VarianceRisk, VelocityModel,
};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum RiskConfig {
    #[default]
    Variance,
}

impl RiskConfig {
    pub fn build(&self) -> Box<dyn RiskMeasure> {
        match self {
            Self::Variance => Box::new(VarianceRisk),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum VelocityConfig {
    Inertia(InertiaParams),
}

impl Default for VelocityConfig {
    fn default() -> Self {
        Self::Inertia(InertiaParams::default())
    }
}

impl VelocityConfig {
    pub fn build(&self) -> Box<dyn VelocityModel> {
        match self {
            Self::Inertia(params) => Box::new(InertiaM::new(params.clone())),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default)]
pub struct FitnessConfig {
    pub penalty: f64,
    pub eps: f64,
    pub risk: RiskConfig,
}

impl Default for FitnessConfig {
    fn default() -> Self {
        Self {
            penalty: 50.0,
            eps: 1e-6,
            risk: RiskConfig::default(),
        }
    }
}

impl FitnessConfig {
    pub fn build(&self) -> Box<dyn FitnessFunction> {
        Box::new(PenalizedFitness::new(
            self.risk.build(),
            PenaltyParams {
                penalty: self.penalty,
                eps: self.eps,
            },
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_component_builders_preserve_effective_parameters() {
        assert_eq!(
            FitnessConfig::default().build().params(),
            serde_json::json!({
                "penalty": 50.0,
                "eps": 1e-6,
                "risk": {
                    "name": "variance",
                    "params": {},
                },
            })
        );
        assert_eq!(
            VelocityConfig::default().build().params(),
            serde_json::json!({
                "c1": 0.5,
                "c2": 0.9,
                "inertia": 0.8,
            })
        );
    }
}
