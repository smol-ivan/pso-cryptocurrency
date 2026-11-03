mod domain;
mod market_data;
mod optimizer;

use optimizer::pso::Pso;
use time::OffsetDateTime;
use time::macros::datetime;
use tokio;

use crate::market_data::repository::save_assets;
use crate::market_data::{dataset::build, provider::download};
use crate::optimizer::pso::{InertiaM, Variance, VelocityModel};

use anyhow::{Ok, Result};
use sqlx::postgres::{PgPool, PgPoolOptions};

use serde::Deserialize;

use config::{Config, ConfigError, Environment, File};

#[derive(Deserialize, Debug)]
struct PsoConfig {
    // database_url: String,
    tickers: Vec<String>,
    #[serde(with = "time::serde::rfc3339")]
    start: OffsetDateTime,
    #[serde(with = "time::serde::rfc3339")]
    end: OffsetDateTime,
    swarm_size: usize,
    target_return: f64,
}

#[derive(Deserialize, Debug)]
struct Settings {
    database_url: String,
    pso: PsoConfig,
}

impl Settings {
    fn new() -> Result<Self> {
        // dotenv::dotenv().ok();

        let settings = Config::builder()
            .add_source(config::File::with_name("config"))
            .add_source(config::Environment::default())
            .build()?;

        Ok(settings.try_deserialize()?)
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let settings = Settings::new()?;
    let start = settings.pso.start;
    let end = settings.pso.end;
    let tickers = settings.pso.tickers;
    // // println!("{:#?}", res)

    let pool = PgPoolOptions::new()
        .max_connections(2)
        .connect(settings.database_url.as_str())
        .await
        .unwrap();

    let res = download(start, end, &tickers).await?;
    save_assets(&pool, &res).await?;
    let dataset = build(&pool, &tickers, start, end).await?;

    // println!("Activos {:?}", dataset.assets);
    // println!("Dimensiones {:?}", dataset.returns.dim());
    println!("Retornos {:#?}", dataset.returns);
    println!(
        "Target return bounds: {:#?}",
        dataset.target_return_bounds()
    );
    // println!("Fechas {:?}", dataset.timestamps.len());
    let fitness_function = Box::new(Variance::default());
    let velocity_model = Box::new(InertiaM::default());
    let returns = dataset.returns;
    let dimensions = dataset.assets.len();
    let swarm_size = settings.pso.swarm_size;
    let target_return = settings.pso.target_return;

    let pso = Pso::new(
        fitness_function,
        velocity_model,
        dimensions,
        swarm_size,
        returns,
        target_return,
    );

    // pso.optimization();

    Ok(())
}
