use clap::Parser;
use ndarray_rand::rand::SeedableRng;
use ndarray_rand::rand::rngs::StdRng;

use pso_cryptocurrency::config::Settings;
use pso_cryptocurrency::market_data::repository::save_assets;
use pso_cryptocurrency::market_data::{dataset::build, provider::download};
use pso_cryptocurrency::optimizer::pso::Pso;

use anyhow::{Context, Result};
use sqlx::postgres::PgPoolOptions;

mod cli;

use crate::cli::{Cli, Commands};
#[tokio::main]
async fn main() -> Result<()> {
    let args = Cli::parse();
    let settings = Settings::new(&args.config)?;

    // TODO: We need a health check to db
    let pool = PgPoolOptions::new()
        .max_connections(settings.database.max_connections)
        .connect(settings.database.url.as_str())
        .await
        .context("failed to connect to the database")?;

    match args.command.unwrap_or(Commands::OptimizeSingleTest {
        target_return: None,
        seed: None,
    }) {
        Commands::UpdateDb => {
            println!("Applying database update");
            let assets = download(
                settings.dataset.start,
                settings.dataset.end,
                &settings.dataset.tickers,
            )
            .await?;
            save_assets(&pool, &assets).await?;
            println!("Database is updated withour any error");
        }
        Commands::TargetBounds => {
            let dataset = build(
                &pool,
                &settings.dataset.tickers,
                settings.dataset.start,
                settings.dataset.end,
            )
            .await?;
            println!("Target return bounds");
            println!("MIN: {:?}", dataset.target_return_bounds()?.0);
            println!("MAX: {:?}", dataset.target_return_bounds()?.1);
        }

        Commands::OptimizeSingleTest {
            target_return,
            seed,
        } => {
            let dataset = build(
                &pool,
                &settings.dataset.tickers,
                settings.dataset.start,
                settings.dataset.end,
            )
            .await?;
            let target_return = target_return.unwrap_or(settings.single_test.target_return);
            let seed = seed.unwrap_or(settings.pso.seed);
            let rng = StdRng::seed_from_u64(seed);

            let mut pso = Pso::new(
                settings.pso.fitness.build(),
                settings.pso.velocity.build(),
                dataset.assets.len(),
                settings.pso.swarm_size,
                dataset.returns,
                target_return,
                settings.pso.iterations,
                rng,
            );

            println!(
                "Starting PSO optimization with target return: {:?}, seed: {}",
                target_return, seed
            );
            let best_p = pso.optimization()?;
        }
    };

    Ok(())
}
