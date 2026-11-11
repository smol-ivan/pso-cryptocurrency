use anyhow::Result;
use serde::{Deserialize, Serialize};

use config::{Config, Environment, File};
use time::OffsetDateTime;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct VarianceParams {
    pub penalty: f64,
    pub eps: f64,
}

impl Default for VarianceParams {
    /// Creates a variance params with a default penalty of 50.0.
    // TODO: Evaluate penalty sensitivity across different return scales
    // and dataset frequencies.
    fn default() -> Self {
        Self {
            penalty: 50.0,
            eps: 1e-6,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct InertiaParams {
    /// Cognitive acceleration coefficient.
    pub c1: f64,

    /// Social acceleration coefficient.
    pub c2: f64,

    /// Inertia weight controlling the influence of the previous velocity.
    pub inertia: f64,
}

impl Default for InertiaParams {
    /// Creates an inertia-based velocity model with default coefficients.
    ///
    /// The default configuration uses:
    /// - Cognitive coefficient: 0.5.
    /// - Social coefficient: 0.9.
    /// - Inertia weight: 0.8.
    fn default() -> Self {
        InertiaParams {
            c1: 0.5,
            c2: 0.9,
            inertia: 0.8,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum RiskConfig {
    Variance,
}

impl Default for RiskConfig {
    fn default() -> Self {
        Self::Variance
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum FitnessConfig {
    Penalized {
        #[serde(default = "default_penalty")]
        penalty: f64,
        #[serde(default = "default_eps")]
        eps: f64,
        #[serde(default)]
        risk: RiskConfig,
    },
}

impl Default for FitnessConfig {
    fn default() -> Self {
        Self::Penalized {
            penalty: 50.0,
            eps: 1e-6,
            risk: RiskConfig::default(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum VelocityConfig {
    Inertia {
        #[serde(default = "default_c1")]
        c1: f64,
        #[serde(default = "default_c2")]
        c2: f64,
        #[serde(default = "default_inertia")]
        inertia: f64,
    },
}

impl Default for VelocityConfig {
    fn default() -> Self {
        Self::Inertia {
            c1: 0.5,
            c2: 0.9,
            inertia: 0.8,
        }
    }
}

impl From<VelocityConfig> for InertiaParams {
    fn from(value: VelocityConfig) -> Self {
        match value {
            VelocityConfig::Inertia { c1, c2, inertia } => Self { c1, c2, inertia },
        }
    }
}

#[derive(Deserialize, Debug)]
pub struct PsoConfig {
    // database_url: String,
    pub tickers: Vec<String>,
    #[serde(with = "time::serde::rfc3339")]
    pub start: OffsetDateTime,
    #[serde(with = "time::serde::rfc3339")]
    pub end: OffsetDateTime,
    pub swarm_size: usize,
    pub target_return: f64,
    pub iterations: usize,
    pub seed: u64,

    #[serde(default)]
    pub fitness: FitnessConfig,
    #[serde(default)]
    pub velocity: VelocityConfig,
}

#[derive(Deserialize, Debug)]
pub struct Settings {
    pub database_url: String,
    pub pso: PsoConfig,
}

impl Settings {
    pub fn new() -> Result<Self> {
        // dotenv::dotenv().ok();

        let settings = Config::builder()
            .add_source(File::with_name("config"))
            .add_source(Environment::default().separator("__").try_parsing(true))
            .build()?;

        Ok(settings.try_deserialize()?)
    }
}

fn default_penalty() -> f64 {
    50.0
}

fn default_eps() -> f64 {
    1e-6
}

fn default_c1() -> f64 {
    0.5
}

fn default_c2() -> f64 {
    0.9
}

fn default_inertia() -> f64 {
    0.8
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use config::FileFormat;

    use super::*;

    fn base_config() -> &'static str {
        r#"
database_url = "postgres://localhost/test"

[pso]
tickers = ["BTC"]
start = 2024-01-01T00:00:00Z
end = 2024-01-02T00:00:00Z
swarm_size = 3
target_return = 0.01
iterations = 10
seed = 42
"#
    }

    #[test]
    fn deserializes_tagged_fitness_and_velocity_sections() {
        let toml = format!(
            "{}\n[pso.fitness]\ntype = \"penalized\"\npenalty = 75.0\neps = 0.00001\n\n[pso.fitness.risk]\ntype = \"variance\"\n\n[pso.velocity]\ntype = \"inertia\"\nc1 = 0.6\nc2 = 1.1\ninertia = 0.7\n",
            base_config()
        );
        let settings: Settings = Config::builder()
            .add_source(File::from_str(&toml, FileFormat::Toml))
            .build()
            .unwrap()
            .try_deserialize()
            .unwrap();

        assert_eq!(
            settings.pso.fitness,
            FitnessConfig::Penalized {
                penalty: 75.0,
                eps: 0.00001,
                risk: RiskConfig::Variance,
            }
        );
        assert_eq!(
            settings.pso.velocity,
            VelocityConfig::Inertia {
                c1: 0.6,
                c2: 1.1,
                inertia: 0.7,
            }
        );
    }

    #[test]
    fn defaults_fitness_and_velocity_when_sections_are_missing() {
        let settings: Settings = Config::builder()
            .add_source(File::from_str(base_config(), FileFormat::Toml))
            .build()
            .unwrap()
            .try_deserialize()
            .unwrap();

        assert_eq!(settings.pso.fitness, FitnessConfig::default());
        assert_eq!(settings.pso.velocity, VelocityConfig::default());
    }

    #[test]
    fn parses_numeric_environment_override() {
        let mut values = HashMap::new();
        values.insert("PSO__TARGET_RETURN".to_owned(), "0.07".to_owned());
        let settings: Settings = Config::builder()
            .add_source(File::from_str(base_config(), FileFormat::Toml))
            .add_source(
                Environment::default()
                    .separator("__")
                    .try_parsing(true)
                    .source(Some(values)),
            )
            .build()
            .unwrap()
            .try_deserialize()
            .unwrap();

        assert_eq!(settings.pso.target_return, 0.07);
    }
}
