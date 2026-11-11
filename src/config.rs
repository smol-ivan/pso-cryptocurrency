use anyhow::Result;
use serde::{Deserialize, Serialize};

use config::Config;
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
    pub fitness: VarianceParams,
    #[serde(default)]
    pub velocity: InertiaParams,
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
            .add_source(config::File::with_name("config"))
            .add_source(config::Environment::default())
            .build()?;

        Ok(settings.try_deserialize()?)
    }
}
