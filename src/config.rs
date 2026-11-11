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
        Self::load(path, Environment::with_prefix("APP"), database_url)
    }

    fn load(path: &str, environment: Environment, database_url: Option<String>) -> Result<Self> {
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

    fn velocity_params_mut(&mut self) -> &mut crate::optimizer::pso::InertiaParams {
        match &mut self.velocity {
            VelocityConfig::Inertia(params) => params,
        }
    }
}

fn default_max_connections() -> u32 {
    2
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;
    use std::fs;

    use super::*;
    use crate::optimizer::pso::{RiskConfig, VelocityConfig};

    fn full_toml() -> &'static str {
        r#"
[database]
max_connections = 5

[dataset]
tickers = ["AAPL", "NVDA"]
start = 2024-01-01T00:00:00Z
end = 2024-01-10T23:59:59Z

[pso]
swarm_size = 45
iterations = 125
seed = 42

[pso.fitness]
penalty = 75.0
eps = 0.00001

[pso.fitness.risk]
kind = "variance"

[pso.velocity]
kind = "inertia"
c1 = 0.6
c2 = 1.1
inertia = 0.7

[single_test]
target_return = 0.01
"#
    }

    fn minimal_toml() -> &'static str {
        r#"
[dataset]
tickers = ["BTC"]
start = 2024-01-01T00:00:00Z
end = 2024-01-02T00:00:00Z

[pso]
swarm_size = 2
iterations = 1
seed = 42

[single_test]
target_return = 0.01
"#
    }

    fn load_text(text: &str, environment: Environment, url: Option<&str>) -> Result<Settings> {
        let path = std::env::temp_dir().join(format!(
            "pso-config-{}-{}.toml",
            std::process::id(),
            unique_suffix()
        ));
        fs::write(&path, text)?;
        let result = Settings::load(path.to_str().unwrap(), environment, url.map(str::to_owned));
        fs::remove_file(path)?;
        result
    }

    fn unique_suffix() -> u128 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    }

    #[test]
    fn deserializes_full_configuration() {
        let settings = load_text(
            full_toml(),
            Environment::default(),
            Some("postgres://secret"),
        )
        .unwrap();

        assert_eq!(settings.database.max_connections, 5);
        assert_eq!(settings.database.url, "postgres://secret");
        assert_eq!(settings.dataset.tickers, ["AAPL", "NVDA"]);
        assert_eq!(settings.pso.swarm_size, 45);
        assert_eq!(settings.pso.fitness.penalty, 75.0);
        assert_eq!(settings.pso.fitness.risk, RiskConfig::Variance);
        assert_eq!(
            settings.pso.velocity,
            VelocityConfig::Inertia(crate::optimizer::pso::InertiaParams {
                c1: 0.6,
                c2: 1.1,
                inertia: 0.7,
            })
        );
    }

    #[test]
    fn uses_defaults_for_minimal_configuration() {
        let settings = load_text(
            minimal_toml(),
            Environment::default(),
            Some("postgres://db"),
        )
        .unwrap();

        assert_eq!(settings.database.max_connections, 2);
        assert_eq!(settings.pso.fitness, FitnessConfig::default());
        assert_eq!(settings.pso.velocity, VelocityConfig::default());
    }

    #[test]
    fn rejects_unknown_kind() {
        let text = minimal_toml().replace(
            "[single_test]",
            "[pso.velocity]\nkind = \"unknown\"\n\n[single_test]",
        );
        let error = load_text(&text, Environment::default(), Some("postgres://db")).unwrap_err();
        assert!(error.to_string().contains("deserialize"));
    }

    #[test]
    fn applies_environment_overrides_without_process_mutation() {
        let mut values = HashMap::new();
        values.insert("APP__PSO__SWARM_SIZE".to_owned(), "50".to_owned());
        values.insert(
            "APP__PSO__FITNESS__RISK__KIND".to_owned(),
            "variance".to_owned(),
        );
        let environment = Environment::with_prefix("APP")
            .separator("__")
            .try_parsing(true)
            .source(Some(values));

        let settings = load_text(minimal_toml(), environment, Some("postgres://db")).unwrap();
        assert_eq!(settings.pso.swarm_size, 50);
        assert_eq!(settings.pso.fitness.risk, RiskConfig::Variance);
    }

    #[test]
    fn effective_json_and_debug_redact_database() {
        let settings = load_text(
            full_toml(),
            Environment::default(),
            Some("postgres://secret"),
        )
        .unwrap();
        let json = settings.effective_config_json();
        assert!(json.get("database").is_none());
        assert!(json.to_string().contains("AAPL"));
        assert!(!json.to_string().contains("postgres://secret"));
        assert!(!format!("{settings:?}").contains("postgres://secret"));
        assert!(format!("{settings:?}").contains("<redacted>"));
    }

    #[test]
    fn loads_a_non_default_path() {
        let settings = load_text(
            minimal_toml(),
            Environment::default(),
            Some("postgres://db"),
        );
        assert!(settings.is_ok());
    }

    #[test]
    fn validates_all_required_constraints() {
        let cases: Vec<(&str, fn(&mut Settings))> = vec![
            ("empty tickers", |s: &mut Settings| {
                s.dataset.tickers.clear()
            }),
            ("empty ticker", |s: &mut Settings| {
                s.dataset.tickers[0].clear()
            }),
            ("duplicate ticker", |s: &mut Settings| {
                s.dataset.tickers.push("BTC".into())
            }),
            ("invalid dates", |s: &mut Settings| {
                s.dataset.end = s.dataset.start
            }),
            ("small swarm", |s: &mut Settings| s.pso.swarm_size = 1),
            ("zero iterations", |s: &mut Settings| s.pso.iterations = 0),
            ("zero connections", |s: &mut Settings| {
                s.database.max_connections = 0
            }),
            ("negative penalty", |s: &mut Settings| {
                s.pso.fitness.penalty = -1.0
            }),
            ("non-finite penalty", |s: &mut Settings| {
                s.pso.fitness.penalty = f64::NAN
            }),
            ("negative eps", |s: &mut Settings| s.pso.fitness.eps = -1.0),
            ("non-finite eps", |s: &mut Settings| {
                s.pso.fitness.eps = f64::INFINITY
            }),
            ("non-finite c1", |s: &mut Settings| {
                s.pso.velocity_params_mut().c1 = f64::NAN
            }),
            ("non-finite c2", |s: &mut Settings| {
                s.pso.velocity_params_mut().c2 = f64::INFINITY
            }),
            ("non-finite inertia", |s: &mut Settings| {
                s.pso.velocity_params_mut().inertia = f64::NEG_INFINITY
            }),
            ("non-finite target", |s: &mut Settings| {
                s.single_test.target_return = f64::NAN
            }),
        ];

        for (name, mutate) in cases {
            let mut settings = load_text(
                minimal_toml(),
                Environment::default(),
                Some("postgres://db"),
            )
            .unwrap();
            mutate(&mut settings);
            assert!(settings.validate().is_err(), "{name} should be rejected");
        }
    }
}
