use sqlx::{PgPool, Row};

async fn insert_experiment(pool: &PgPool) -> Result<i64, sqlx::Error> {
    sqlx::query(
        "INSERT INTO experiments
            (name, tickers, dataset_start, dataset_end, n_observations, dataset_stats, config, algorithm_version)
         VALUES ('test', ARRAY['BTC', 'ETH'], now(), now() + interval '1 day', 2, '{}'::jsonb, '{}'::jsonb, 'test')
         RETURNING id",
    )
    .fetch_one(pool)
    .await
    .map(|row| row.get("id"))
}

async fn insert_run(pool: &PgPool, experiment_id: i64, status: &str) -> Result<i64, sqlx::Error> {
    sqlx::query(
        "INSERT INTO runs
            (experiment_id, seed, target_return, status, finished_at, iterations_requested)
         VALUES ($1, 42, 0.01, $2, now(), 1)
         RETURNING id",
    )
    .bind(experiment_id)
    .bind(status)
    .fetch_one(pool)
    .await
    .map(|row| row.get("id"))
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn rejects_non_finite_completed_results(pool: PgPool) -> Result<(), sqlx::Error> {
    let experiment_id = insert_experiment(&pool).await?;
    for value in [f64::INFINITY, f64::NAN] {
        let result = sqlx::query(
            "INSERT INTO runs
                (experiment_id, seed, target_return, status, finished_at, iterations_requested,
                 final_fitness, final_expected_return, final_risk, final_penalty, final_shortfall,
                 final_feasible, final_weights)
             VALUES ($1, 42, 0.01, 'completed', now(), 1, $2, 0.0, 0.0, 0.0, 0.0, true, ARRAY[1.0]::double precision[])",
        )
        .bind(experiment_id)
        .bind(value)
        .execute(&pool)
        .await;
        assert!(result.is_err());
    }
    Ok(())
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn rejects_failed_run_without_error(pool: PgPool) -> Result<(), sqlx::Error> {
    let experiment_id = insert_experiment(&pool).await?;
    let result = sqlx::query(
        "INSERT INTO runs
            (experiment_id, seed, target_return, status, finished_at, iterations_requested)
         VALUES ($1, 42, 0.01, 'failed', now(), 1)",
    )
    .bind(experiment_id)
    .execute(&pool)
    .await;
    assert!(result.is_err());
    Ok(())
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn accepts_null_non_finite_iteration_statistics(pool: PgPool) -> Result<(), sqlx::Error> {
    let experiment_id = insert_experiment(&pool).await?;
    let run_id = insert_run(&pool, experiment_id, "running").await?;
    sqlx::query(
        "INSERT INTO run_iterations
            (run_id, iteration, gbest_feasible, gbest_position, gbest_improved,
             dist_to_centroid_mean, pairwise_dist_mean, position_std_per_dim,
             velocity_norm_mean, velocity_norm_max, feasible_count, pbest_improved,
             non_finite_count, elapsed_us)
         VALUES ($1, 0, false, ARRAY[1.0]::double precision[], false,
                 0.0, 0.0, ARRAY[0.0]::double precision[], 0.0, 0.0, 0, 0, 1, 0)",
    )
    .bind(run_id)
    .execute(&pool)
    .await?;
    Ok(())
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn rejects_particle_without_parent_iteration(pool: PgPool) -> Result<(), sqlx::Error> {
    let experiment_id = insert_experiment(&pool).await?;
    let run_id = insert_run(&pool, experiment_id, "running").await?;
    let result = sqlx::query(
        "INSERT INTO run_particle_iterations
            (run_id, iteration, particle_id, position, velocity, feasible)
         VALUES ($1, 0, 0, ARRAY[1.0]::double precision[], ARRAY[0.0]::double precision[], false)",
    )
    .bind(run_id)
    .execute(&pool)
    .await;
    assert!(result.is_err());
    Ok(())
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn view_preserves_ticker_order(pool: PgPool) -> Result<(), sqlx::Error> {
    let experiment_id = insert_experiment(&pool).await?;
    let run_id = insert_run(&pool, experiment_id, "running").await?;
    sqlx::query(
        "INSERT INTO run_iterations
            (run_id, iteration, gbest_feasible, gbest_position, gbest_improved,
             dist_to_centroid_mean, pairwise_dist_mean, position_std_per_dim,
             velocity_norm_mean, velocity_norm_max, feasible_count, pbest_improved,
             non_finite_count, elapsed_us)
         VALUES ($1, 0, true, ARRAY[0.25, 0.75]::double precision[], true,
                 0.0, 0.0, ARRAY[0.0, 0.0]::double precision[], 0.0, 0.0, 1, 1, 0, 0)",
    )
    .bind(run_id)
    .execute(&pool)
    .await?;
    sqlx::query(
        "INSERT INTO run_particle_iterations
            (run_id, iteration, particle_id, position, velocity, feasible)
         VALUES ($1, 0, 0, ARRAY[0.25, 0.75]::double precision[], ARRAY[0.0, 0.0]::double precision[], true)",
    )
    .bind(run_id)
    .execute(&pool)
    .await?;

    let rows = sqlx::query(
        "SELECT ticker, weight FROM run_particle_weights
         WHERE run_id = $1 ORDER BY particle_id, ticker",
    )
    .bind(run_id)
    .fetch_all(&pool)
    .await?;
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0].get::<String, _>("ticker"), "BTC");
    assert_eq!(rows[1].get::<String, _>("ticker"), "ETH");
    assert_eq!(rows[0].get::<f64, _>("weight"), 0.25);
    assert_eq!(rows[1].get::<f64, _>("weight"), 0.75);
    Ok(())
}

#[sqlx::test(migrations = "./migrations")]
#[ignore]
async fn results_migration_reverts_and_reapplies(pool: PgPool) -> Result<(), sqlx::Error> {
    let migrator = sqlx::migrate!("./migrations");
    sqlx::query(
        "DROP VIEW run_particle_weights;
         DROP TABLE run_particle_iterations;
         DROP TABLE run_iterations;
         DROP TABLE runs;
         DROP TABLE experiments;",
    )
    .execute(&pool)
    .await?;
    migrator.run(&pool).await?;
    Ok(())
}
