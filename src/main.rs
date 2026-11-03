mod config;
mod domain;
mod market_data;
mod optimizer;

use config::Settings;
use optimizer::pso::Pso;
use time::OffsetDateTime;
use time::macros::datetime;
use tokio;

use crate::market_data::repository::save_assets;
use crate::market_data::{dataset::build, provider::download};
use crate::optimizer::pso::{InertiaM, Variance, VelocityModel};

use anyhow::{Ok, Result};
use sqlx::postgres::{PgPool, PgPoolOptions};




#[tokio::main]
async fn main() -> Result<()> {
    let settings = Settings::new()?;
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
