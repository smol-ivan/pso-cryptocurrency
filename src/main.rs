mod domain;
mod market_data;
mod optimizer;

use optimizer::pso::Pso;
use time::macros::datetime;
use tokio;

use crate::market_data::repository::save_assets;
use crate::market_data::{dataset::build, provider::download};

use anyhow::Result;
use sqlx::postgres::{PgPool, PgPoolOptions};
use std::env;

#[tokio::main]
async fn main() -> Result<()> {
    println!("Hello, world!");
    // let pso = Pso::default();
    // pso.optimization();
    let start = datetime!(2024-1-1 0:00:00.00 UTC);
    let end = datetime!(2024-1-10 23:59:59.99 UTC);
    let tickers = vec!["NVDA".to_string(), "AAPL".to_string()];
    // let res = download(start, end, &tickers).await?;
    // println!("{:#?}", res)
    let database_url = env::var("DATABASE_URL")?;

    // let conn = PgConnection::connect(database_url.as_str());
    let pool = PgPoolOptions::new()
        .max_connections(2)
        .connect(database_url.as_str())
        .await
        .unwrap();

    // save_assets(&pool, &res).await?;
    //
    let dataset = build(&pool, &tickers, start, end).await?;

    println!("Activos {:?}", dataset.assets);
    println!("Dimensiones {:?}", dataset.returns.dim());
    println!("Retornos {:#?}", dataset.returns);
    println!("Fechas {:?}", dataset.timestamps.len());

    Ok(())
}
