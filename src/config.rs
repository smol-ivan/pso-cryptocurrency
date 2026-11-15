use std::fmt;

use anyhow::{Context, Result, ensure};
use config::{Config, Environment, File, FileFormat};
use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::optimizer::pso::{FitnessConfig, VelocityConfig};

#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct DatabaseConfig {
    #[serde(skip_serializing)]
    pub url: String,
    #[serde(default = "default_max_connections")]
    pub max_connections: u32,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            url: String::new(),
            max_connections: default_max_connections(),
        }
    }
}

impl fmt::Debug for DatabaseConfig {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("DatabaseConfig")
            .field("url", &"<redacted>")
            .field("max_connections", &self.max_connections)
            .finish()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatasetConfig {
    pub tickers: Vec<String>,
    #[serde(with = "time::serde::rfc3339")]
    pub start: OffsetDateTime,
    #[serde(with = "time::serde::rfc3339")]
    pub end: OffsetDateTime,
    #[serde(default = "default_periods_per_year")]
    pub periods_per_year: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PsoConfig {
    pub swarm_size: usize,
    pub iterations: usize,
    pub seed: u64,
    #[serde(default)]
    pub fitness: FitnessConfig,
    #[serde(default)]
    pub velocity: VelocityConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SingleTestConfig {
    pub target_return: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Settings {
    #[serde(default)]
    pub database: DatabaseConfig,
    pub dataset: DatasetConfig,
    pub pso: PsoConfig,
    pub single_test: SingleTestConfig,
}

impl Settings {
    pub fn new(path: &str) -> Result<Self> {
        let database_url = std::env::var("DATABASE_URL").ok();
        Self::from_sources(path, Environment::with_prefix("APP"), database_url)
    }

    pub fn from_sources(
        path: &str,
        environment: Environment,
        database_url: Option<String>,
    ) -> Result<Self> {
        let settings = Config::builder()
            .add_source(File::new(path, FileFormat::Toml).required(true))
            .add_source(environment.separator("__").try_parsing(true))
            .set_override_option("database.url", database_url)?
            .build()
            .with_context(|| format!("failed to load configuration from {path}"))?;

        let settings: Self = settings
            .try_deserialize()
            .context("failed to deserialize application configuration")?;
        settings.validate()?;
        Ok(settings)
    }

    pub fn validate(&self) -> Result<()> {
        ensure!(
            !self.dataset.tickers.is_empty(),
            "dataset.tickers must not be empty"
        );
        ensure!(
            self.dataset.tickers.iter().all(|ticker| !ticker.is_empty()),
            "dataset.tickers must not contain empty strings"
        );
        let mut unique_tickers = self.dataset.tickers.clone();
        unique_tickers.sort();
        unique_tickers.dedup();
        ensure!(
            unique_tickers.len() == self.dataset.tickers.len(),
            "dataset.tickers must not contain duplicates"
        );
        ensure!(
            self.dataset.start < self.dataset.end,
            "dataset.start must be before dataset.end"
        );
        ensure!(
            self.dataset.periods_per_year.is_finite() && self.dataset.periods_per_year > 0.0,
            "dataset.periods_per_year must be finite and greater than zero"
        );
        ensure!(
            self.pso.swarm_size >= 2,
            "pso.swarm_size must be at least 2"
        );
        ensure!(
            self.pso.iterations >= 1,
            "pso.iterations must be at least 1"
        );
        ensure!(
            self.database.max_connections >= 1,
            "database.max_connections must be at least 1"
        );
        ensure!(
            self.pso.fitness.penalty.is_finite() && self.pso.fitness.penalty >= 0.0,
            "pso.fitness.penalty must be finite and non-negative"
        );
        ensure!(
            self.pso.fitness.eps.is_finite() && self.pso.fitness.eps >= 0.0,
            "pso.fitness.eps must be finite and non-negative"
        );
        ensure!(
            self.pso.velocity_params().c1.is_finite(),
            "pso.velocity.c1 must be finite"
        );
        ensure!(
            self.pso.velocity_params().c2.is_finite(),
            "pso.velocity.c2 must be finite"
        );
        ensure!(
            self.pso.velocity_params().inertia.is_finite(),
            "pso.velocity.inertia must be finite"
        );
        ensure!(
            self.single_test.target_return.is_finite(),
            "single_test.target_return must be finite"
        );
        Ok(())
    }

    pub fn effective_config_json(&self) -> serde_json::Value {
        serde_json::json!({
            "dataset": self.dataset,
            "pso": self.pso,
            "single_test": self.single_test,
        })
    }
}

impl PsoConfig {
    fn velocity_params(&self) -> &crate::optimizer::pso::InertiaParams {
        match &self.velocity {
            VelocityConfig::Inertia(params) => params,
        }
    }
}

fn default_max_connections() -> u32 {
    2
}

fn default_periods_per_year() -> f64 {
    365.0
}
