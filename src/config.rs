use anyhow::Result;
use serde::Deserialize;

use config::Config;
use time::OffsetDateTime;

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
