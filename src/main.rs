mod cli;
mod config;
mod domain;
mod market_data;
mod optimizer;

use clap::Parser;
use config::Settings;
use optimizer::pso::Pso;
use tokio;

use crate::cli::{Cli, Commands};
use crate::market_data::repository::save_assets;
use crate::market_data::{dataset::build, provider::download};
use crate::optimizer::pso::{InertiaM, Variance};

use anyhow::Result;
use sqlx::postgres::PgPoolOptions;

#[tokio::main]
async fn main() -> Result<()> {
    let args = Cli::parse();
    let settings = Settings::new()?;

    // TODO: We need a health check to db
    let pool = PgPoolOptions::new()
        .max_connections(2)
        .connect(settings.database_url.as_str())
        .await
        .unwrap();

    match args.command.unwrap_or(Commands::OptimizeSingleTest {
        target_return: None,
    }) {
        Commands::UpdateDb => {
            println!("Applying database update");
            let assets =
                download(settings.pso.start, settings.pso.end, &settings.pso.tickers).await?;
            save_assets(&pool, &assets).await?;
            println!("Database is updated withour any error");
        }
        Commands::TargetBounds => {
            let dataset = build(
                &pool,
                &settings.pso.tickers,
                settings.pso.start,
                settings.pso.end,
            )
            .await?;
            println!("Target return bounds");
            println!("MIN: {:?}", dataset.target_return_bounds()?.0);
            println!("MAX: {:?}", dataset.target_return_bounds()?.1);
        }

        Commands::OptimizeSingleTest { target_return } => {
            let dataset = build(
                &pool,
                &settings.pso.tickers,
                settings.pso.start,
                settings.pso.end,
            )
            .await?;
            let target_return = target_return.unwrap_or(settings.pso.target_return);

            let pso = Pso::new(
                Box::new(Variance::default()),
                Box::new(InertiaM::default()),
                dataset.assets.len(),
                settings.pso.swarm_size,
                dataset.returns,
                target_return,
            );

            println!(
                "Starting PSO optimization with target return: {:?}",
                target_return
            );
            pso.optimization();
        }
    };

    Ok(())
}
